import json
import uuid
from typing import Any

from langgraph.graph import StateGraph, END
from langchain_core.messages import SystemMessage, HumanMessage

from config import get_llm, get_settings, get_logger, set_context, clear_context, log_stage
from config.metrics import queries_total, retrieval_latency, reranking_latency, generation_latency, end_to_end_latency, no_solution_rate, low_confidence_rate, average_retrieved_tickets, active_requests
from resolver.state import ResolverState
from retrieval import Retriever


UNDERSTAND_PROMPT = """You are a ServiceNow problem understanding agent. Parse the user's problem into structured fields for retrieval. Extract ONLY what is explicitly stated.

Rules:
1. Never infer technologies, error codes, or entities not mentioned.
2. If a field has no evidence, use [] (list) or null (single value).
3. Preserve error codes, field names, product names, and config keys verbatim.
4. intent must be one of: troubleshooting, how-to, root-cause-analysis, configuration, performance, security, unknown.

Output format: reason first, then extract. Return ONLY this JSON object — no markdown, no extra text:

{
  "reasoning": "1 sentence: what the user is asking and which parts map to which fields",
  "problem": "core issue statement (1-2 sentences, user's words)",
  "entities": ["technical entity", ...],
  "error_codes": ["ERROR_CODE", ...],
  "technology": ["platform/product", ...],
  "intent": "troubleshooting | how-to | root-cause-analysis | configuration | performance | security | unknown"
}"""


GENERATE_PROMPT = """You are a ServiceNow ticket resolution assistant. Answer
using ONLY the supplied knowledge-base evidence below. You have no other
knowledge of this system, its errors, or its fixes.

Rules (violating any of these is a failure):
1. Never invent a solution or a step not supported by the evidence.
2. Every technical claim (error code, step, config value) must trace to a
   specific ticket_id in the evidence — if you can't cite one, drop the claim.
3. If the evidence doesn't reliably solve the problem, set status to
   "no_reliable_solution" — do not offer a partial or best-effort guess.
4. Preserve error codes, field names, and configuration fields verbatim —
   do not normalize casing or reformat them.
5. Prefer solutions from the most relevant/highest-scoring tickets when
   evidence conflicts; note the conflict in solution if it matters.
6. Separate confirmed fixes from recommendations you're inferring are
   related — label anything not explicitly confirmed-working in the source
   as a recommendation, not a fix.
7. Never state or imply a solution is guaranteed to work.
8. next_steps must include any follow-up/verification/preventive actions
   present in the evidence — do not drop them for brevity.

Confidence rubric (confidence is a float 0-1, not a guess):
- 0.8-1.0: a ticket's evidence directly matches the error/symptom AND has a confirmed resolution
- 0.4-0.79: relevant tickets found but symptom match is partial, or the fix wasn't explicitly confirmed
- 0.0-0.39: only tangentially related evidence — this should usually pair with status "no_reliable_solution"

Output format: reason first, then answer. Return ONLY this JSON object — no
markdown fences, no text before or after it:

{
  "reasoning": "1-3 sentences: which evidence is relevant and why, or why it's insufficient",
  "problem_understanding": {
    "technology": ["string", ...],
    "error_codes": ["string", ...],
    "entities": ["string", ...]
  },
  "solution": "string or null",
  "next_steps": ["string", ...],
  "relevant_ticket_ids": ["string", ...],
  "confidence": 0.0,
  "sources": [{"ticket_id": "string", "score": 0.0}],
  "status": "resolved" | "no_reliable_solution"
}

Evidence:
{evidence}"""


NO_EVIDENCE_RESPONSE = {
    "status": "no_reliable_solution",
    "solution": None,
    "next_steps": [],
    "relevant_ticket_ids": [],
    "confidence": 0.0,
    "sources": [],
    "problem_understanding": {"technology": [], "error_codes": [], "entities": []},
}


class ResolverAgent:
    def __init__(self):
        self.settings = get_settings()
        self.logger = get_logger("resolver")

        try:
            self.llm = get_llm()
            self.logger.info("LLM initialized successfully")
        except Exception as e:
            self.logger.error("Failed to initialize LLM", extra={"metadata": {"error": str(e), "error_type": type(e).__name__}})
            raise

        try:
            self.retriever = Retriever()
            self.retriever.connect()
            self.logger.info("Retriever connected successfully")
        except Exception as e:
            self.logger.error("Failed to connect retriever", extra={"metadata": {"error": str(e), "error_type": type(e).__name__}})
            raise

        try:
            from retrieval.reranker import Reranker
            self.reranker = Reranker()
            self.logger.info("Reranker initialized successfully")
        except Exception as e:
            self.logger.error("Failed to initialize reranker", extra={"metadata": {"error": str(e), "error_type": type(e).__name__}})
            raise

        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(ResolverState)

        workflow.add_node("understand", self._understand)
        workflow.add_node("retrieve", self._retrieve)
        workflow.add_node("rerank", self._rerank)
        workflow.add_node("evidence_builder", self._evidence_builder)
        workflow.add_node("verify", self._verify)
        workflow.add_node("generate", self._generate)
        workflow.add_node("fallback", self._fallback)

        workflow.set_entry_point("understand")

        workflow.add_edge("understand", "retrieve")
        workflow.add_edge("retrieve", "rerank")
        workflow.add_edge("rerank", "evidence_builder")
        workflow.add_edge("evidence_builder", "verify")

        workflow.add_conditional_edges(
            "verify",
            self._verify_routing,
            {
                "generate": "generate",
                "fallback": "fallback",
                "retrieve": "retrieve",
            },
        )

        workflow.add_edge("generate", END)
        workflow.add_edge("fallback", END)

        return workflow.compile()

    def _understand(self, state: ResolverState) -> ResolverState:
        query = state["query"]
        request_id = state.get("request_id", str(uuid.uuid4()))

        set_context(request_id=request_id, stage="understand")

        self.logger.info(f"Understanding query: {query[:100]}")

        messages = [
            SystemMessage(content=UNDERSTAND_PROMPT),
            HumanMessage(content=query),
        ]

        try:
            response = self.llm.invoke(messages)
        except Exception as e:
            self.logger.error("LLM invocation failed in understand stage", extra={"metadata": {"error": str(e), "error_type": type(e).__name__}})
            # Fallback to basic parsing
            parsed = {
                "problem": query,
                "entities": [],
                "error_codes": [],
                "technology": [],
                "intent": "troubleshooting",
            }
        else:
            try:
                parsed = json.loads(response.content)
            except json.JSONDecodeError:
                parsed = {
                    "problem": query,
                    "entities": [],
                    "error_codes": [],
                    "technology": [],
                    "intent": "troubleshooting",
                }

        state["normalized_query"] = parsed.get("problem", query)
        state["entities"] = parsed.get("entities", [])
        state["error_codes"] = parsed.get("error_codes", [])
        state["technology"] = parsed.get("technology", [])
        state["intent"] = parsed.get("intent", "troubleshooting")
        state["request_id"] = request_id

        clear_context()
        return state

    def _retrieve(self, state: ResolverState) -> ResolverState:
        query = state["normalized_query"]
        request_id = state["request_id"]

        set_context(request_id=request_id, stage="retrieve")

        with retrieval_latency.time():
            response = self.retriever.retrieve(query)

        state["retrieved_chunks"] = [
            {
                "id": chunk.id,
                "score": chunk.score,
                "payload": chunk.payload,
            }
            for ticket in response.tickets
            for chunk in ticket.chunks
        ]

        queries_total.inc()
        average_retrieved_tickets.set(len(response.tickets))

        self.logger.info(f"Retrieved {len(state['retrieved_chunks'])} chunks from {len(response.tickets)} tickets")

        clear_context()
        return state

    def _rerank(self, state: ResolverState) -> ResolverState:
        query = state["normalized_query"]
        request_id = state["request_id"]

        set_context(request_id=request_id, stage="rerank")

        from retrieval.hybrid import HybridRetrievalResult

        hybrid_results = [
            HybridRetrievalResult(
                id=c["id"],
                score=c["score"],
                payload=c["payload"],
            )
            for c in state["retrieved_chunks"]
        ]

        # Use the shared reranker instance — avoids loading CrossEncoder on every request
        with reranking_latency.time():
            reranked = self.reranker.rerank(query, hybrid_results)

        state["reranked_chunks"] = [
            {
                "id": r.id,
                "score": r.score,
                "payload": r.payload,
            }
            for r in reranked
        ]

        self.logger.info(f"Reranked to {len(state['reranked_chunks'])} chunks")

        clear_context()
        return state

    def _evidence_builder(self, state: ResolverState) -> ResolverState:
        request_id = state["request_id"]
        set_context(request_id=request_id, stage="evidence_builder")

        from collections import defaultdict

        ticket_chunks = defaultdict(list)
        for chunk in state["reranked_chunks"]:
            ticket_id = chunk["payload"].get("ticket_id", "unknown")
            ticket_chunks[ticket_id].append(chunk)

        evidence = []
        relevant_tickets = []

        for ticket_id, chunks in ticket_chunks.items():
            relevant_tickets.append(ticket_id)

            problem = None
            root_cause = None
            resolution = None
            next_steps = None

            for chunk in chunks:
                ct = chunk["payload"].get("chunk_type")
                if ct == "problem" and not problem:
                    problem = chunk["payload"].get("problem")
                elif ct == "root_cause" and not root_cause:
                    root_cause = chunk["payload"].get("root_cause")
                elif ct == "resolution" and not resolution:
                    resolution = chunk["payload"].get("resolution")
                elif ct == "next_steps" and not next_steps:
                    next_steps = chunk["payload"].get("next_steps")

            if resolution or root_cause:
                evidence.append({
                    "ticket_id": ticket_id,
                    "problem": problem,
                    "root_cause": root_cause,
                    "resolution": resolution,
                    "next_steps": next_steps,
                    "chunks": chunks[:3],
                })

        state["evidence"] = evidence
        state["relevant_tickets"] = relevant_tickets[:self.settings.retrieval_final_ticket_count]

        self.logger.info(f"Built evidence from {len(evidence)} tickets")

        clear_context()
        return state

    def _verify(self, state: ResolverState) -> ResolverState:
        request_id = state["request_id"]
        set_context(request_id=request_id, stage="verify")

        evidence = state["evidence"]
        has_resolution = any(e.get("resolution") for e in evidence)
        has_root_cause = any(e.get("root_cause") for e in evidence)

        if has_resolution or has_root_cause:
            state["status"] = "sufficient_evidence"
        else:
            state["status"] = "insufficient_evidence"

        clear_context()
        return state

    def _verify_routing(self, state: ResolverState) -> str:
        if state["status"] == "sufficient_evidence":
            return "generate"
        elif state["status"] == "insufficient_evidence":
            return "fallback"
        return "retrieve"

    def _generate(self, state: ResolverState) -> ResolverState:
        request_id = state["request_id"]
        set_context(request_id=request_id, stage="generate")

        evidence_str = json.dumps(state["evidence"], indent=2)

        messages = [
            SystemMessage(content=GENERATE_PROMPT.format(evidence=evidence_str)),
            HumanMessage(content=state["query"]),
        ]

        try:
            with generation_latency.time():
                response = self.llm.invoke(messages)
        except Exception as e:
            self.logger.error("LLM invocation failed in generate stage", extra={"metadata": {"error": str(e), "error_type": type(e).__name__}})
            parsed = NO_EVIDENCE_RESPONSE
        else:
            try:
                parsed = json.loads(response.content)
            except json.JSONDecodeError:
                parsed = NO_EVIDENCE_RESPONSE

        state["solution"] = parsed.get("solution", "")
        state["next_steps"] = parsed.get("next_steps", [])
        state["relevant_ticket_ids"] = parsed.get("relevant_ticket_ids", state["relevant_tickets"])
        state["confidence"] = parsed.get("confidence", 0.5)
        state["sources"] = parsed.get("sources", [])
        state["problem_understanding"] = parsed.get("problem_understanding", {})
        state["status"] = parsed.get("status", "resolved")

        if state["status"] == "no_reliable_solution" or state["confidence"] < 0.5:
            no_solution_rate.inc()
        if state["confidence"] < 0.5:
            low_confidence_rate.inc()

        self.logger.info(f"Generated solution with confidence {state['confidence']}")

        clear_context()
        return state

    def _fallback(self, state: ResolverState) -> ResolverState:
        state.update(NO_EVIDENCE_RESPONSE)
        no_solution_rate.inc()
        self.logger.warning("No reliable solution found")
        return state

    def resolve(self, problem: str, request_id: str = None) -> dict:
        request_id = request_id or str(uuid.uuid4())

        with end_to_end_latency.time():
            active_requests.inc()
            initial_state = ResolverState(
                query=problem,
                normalized_query="",
                entities=[],
                error_codes=[],
                technology=[],
                intent="",
                retrieved_chunks=[],
                reranked_chunks=[],
                relevant_tickets=[],
                evidence=[],
                solution="",
                next_steps=[],
                confidence=0.0,
                status="",
                request_id=request_id,
            )

            try:
                final_state = self.graph.invoke(initial_state)
            finally:
                active_requests.dec()

        return {
            "request_id": request_id,
            "status": final_state.get("status", "no_reliable_solution"),
            "problem_understanding": final_state.get("problem_understanding", {}),
            "solution": final_state.get("solution"),
            "next_steps": final_state.get("next_steps", []),
            "relevant_ticket_ids": final_state.get("relevant_ticket_ids", []),
            "confidence": final_state.get("confidence", 0.0),
            "sources": final_state.get("sources", []),
        }