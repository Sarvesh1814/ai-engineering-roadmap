import json
from pathlib import Path
from typing import Any
from dataclasses import dataclass

from config import get_llm
from resolver.graph import ResolverAgent
from retrieval import Retriever


@dataclass
class GenerationMetrics:
    faithfulness: float
    answer_relevance: float
    citation_correctness: float
    completeness: float
    hallucination_rate: float
    total_evaluated: int


FAITHFULNESS_PROMPT = """You are an expert evaluator. Assess whether the GENERATED ANSWER is FAITHFUL to the PROVIDED EVIDENCE.

EVIDENCE (from retrieved tickets):
{evidence}

GENERATED ANSWER:
{answer}

Question: Is every technical claim, resolution step, and specific detail in the answer directly supported by the evidence?
- Score 1.0: Fully faithful - every claim traceable to evidence
- Score 0.5: Partially faithful - some claims supported, others not clearly supported
- Score 0.0: Not faithful - significant claims unsupported or contradicted

Return ONLY a JSON object: {{"score": <float>, "reasoning": "<brief>"}}"""


RELEVANCE_PROMPT = """You are an expert evaluator. Assess whether the GENERATED ANSWER addresses the USER'S PROBLEM.

USER PROBLEM:
{query}

GENERATED ANSWER:
{answer}

Question: Does the answer directly address the user's problem with relevant resolution steps?
- Score 1.0: Highly relevant - directly solves the stated problem
- Score 0.5: Partially relevant - addresses some aspects but misses key elements
- Score 0.0: Not relevant - generic, off-topic, or doesn't solve the problem

Return ONLY a JSON object: {{"score": <float>, "reasoning": "<brief>"}}"""


CITATION_PROMPT = """You are an expert evaluator. Check CITATION CORRECTNESS.

CITED TICKET IDs IN ANSWER:
{cited_tickets}

ACTUALLY RETRIEVED TICKET IDs:
{retrieved_tickets}

Question: Are all cited ticket IDs actually present in the retrieved set?
- Score 1.0: All citations correct and present in retrieved set
- Score 0.5: Some citations correct, others not in retrieved set
- Score 0.0: Most/all citations hallucinated or not retrieved

Return ONLY a JSON object: {{"score": <float>, "reasoning": "<brief>"}}"""


COMPLETENESS_PROMPT = """You are an expert evaluator. Assess COMPLETENESS of the answer relative to evidence.

EVIDENCE (key resolution info from retrieved tickets):
{evidence}

GENERATED ANSWER:
{answer}

Question: Does the answer include all key resolution steps, root causes, and next steps present in the evidence?
- Score 1.0: Complete - all key information from evidence captured
- Score 0.5: Partial - some key info missing
- Score 0.0: Incomplete - major resolution details missing

Return ONLY a JSON object: {{"score": <float>, "reasoning": "<brief>"}}"""


HALLUCINATION_PROMPT = """You are an expert evaluator. Detect HALLUCINATION in the generated answer.

EVIDENCE:
{evidence}

GENERATED ANSWER:
{answer}

Question: Does the answer contain technical details (error codes, field names, config values, commands) NOT present in the evidence?
- Score 0.0: No hallucination - all technical details grounded
- Score 0.5: Minor hallucination - some ungrounded details
- Score 1.0: Major hallucination - significant invented technical content

Return ONLY a JSON object: {{"score": <float>, "reasoning": "<brief>"}}"""


class GenerationEvaluator:
    def __init__(self):
        self.llm = get_llm()
        self.agent = ResolverAgent()
        self.retriever = Retriever()
        self.retriever.connect()

    def _invoke_judge(self, prompt: str) -> dict:
        from langchain_core.messages import HumanMessage
        response = self.llm.invoke([HumanMessage(content=prompt)])
        try:
            return json.loads(response.content)
        except json.JSONDecodeError:
            return {"score": 0.0, "reasoning": "Failed to parse judge response"}

    def evaluate_single(self, query: str) -> dict[str, float]:
        """Evaluate generation quality for a single query."""
        result = self.agent.resolve(query)
        
        answer = result.get("solution", "") or ""
        next_steps = result.get("next_steps", [])
        if next_steps:
            answer += "\n\nNext Steps:\n" + "\n".join(f"{i+1}. {s}" for i, s in enumerate(next_steps))
        
        cited_tickets = result.get("relevant_ticket_ids", [])
        evidence_data = result.get("sources", [])
        
        evidence_text = "\n\n".join([
            f"Ticket {e['ticket_id']} (score: {e['score']:.2f})" 
            for e in evidence_data
        ]) if evidence_data else "No evidence retrieved"
        
        retrieved_tickets = [e['ticket_id'] for e in evidence_data]

        scores = {}
        
        faithfulness = self._invoke_judge(
            FAITHFULNESS_PROMPT.format(evidence=evidence_text, answer=answer)
        )
        scores["faithfulness"] = faithfulness.get("score", 0.0)
        
        relevance = self._invoke_judge(
            RELEVANCE_PROMPT.format(query=query, answer=answer)
        )
        scores["answer_relevance"] = relevance.get("score", 0.0)
        
        citation = self._invoke_judge(
            CITATION_PROMPT.format(
                cited_tickets=", ".join(cited_tickets) or "None",
                retrieved_tickets=", ".join(retrieved_tickets) or "None"
            )
        )
        scores["citation_correctness"] = citation.get("score", 0.0)
        
        completeness = self._invoke_judge(
            COMPLETENESS_PROMPT.format(evidence=evidence_text, answer=answer)
        )
        scores["completeness"] = completeness.get("score", 0.0)
        
        hallucination = self._invoke_judge(
            HALLUCINATION_PROMPT.format(evidence=evidence_text, answer=answer)
        )
        scores["hallucination_rate"] = hallucination.get("score", 0.0)
        
        return scores

    def evaluate_dataset(self, queries: list[str]) -> GenerationMetrics:
        """Evaluate generation quality across multiple queries."""
        all_scores = {k: [] for k in ["faithfulness", "answer_relevance", "citation_correctness", "completeness", "hallucination_rate"]}
        
        for i, query in enumerate(queries):
            print(f"  Evaluating {i+1}/{len(queries)}: {query[:60]}...")
            try:
                scores = self.evaluate_single(query)
                for k, v in scores.items():
                    all_scores[k].append(v)
            except Exception as e:
                print(f"    Error: {e}")
                for k in all_scores:
                    all_scores[k].append(0.0)
        
        return GenerationMetrics(
            faithfulness=sum(all_scores["faithfulness"]) / len(all_scores["faithfulness"]),
            answer_relevance=sum(all_scores["answer_relevance"]) / len(all_scores["answer_relevance"]),
            citation_correctness=sum(all_scores["citation_correctness"]) / len(all_scores["citation_correctness"]),
            completeness=sum(all_scores["completeness"]) / len(all_scores["completeness"]),
            hallucination_rate=sum(all_scores["hallucination_rate"]) / len(all_scores["hallucination_rate"]),
            total_evaluated=len(queries),
        )


def load_test_queries(path: str = "evaluation/golden_dataset.json") -> list[str]:
    """Load queries from golden dataset."""
    with open(path) as f:
        data = json.load(f)
    return [item["query"] for item in data]


def main():
    print("[+] Loading test queries...")
    queries = load_test_queries()
    print(f"[+] Loaded {len(queries)} queries")
    
    print("[+] Initializing evaluator...")
    evaluator = GenerationEvaluator()
    
    print("[+] Running generation evaluation...")
    metrics = evaluator.evaluate_dataset(queries)
    
    print("\n[+] Generation Evaluation Results:")
    print(f"  Faithfulness:        {metrics.faithfulness:.3f}")
    print(f"  Answer Relevance:    {metrics.answer_relevance:.3f}")
    print(f"  Citation Correctness: {metrics.citation_correctness:.3f}")
    print(f"  Completeness:        {metrics.completeness:.3f}")
    print(f"  Hallucination Rate:  {metrics.hallucination_rate:.3f} (lower is better)")
    print(f"  Total Evaluated:     {metrics.total_evaluated}")
    
    output = {
        "faithfulness": metrics.faithfulness,
        "answer_relevance": metrics.answer_relevance,
        "citation_correctness": metrics.citation_correctness,
        "completeness": metrics.completeness,
        "hallucination_rate": metrics.hallucination_rate,
        "total_evaluated": metrics.total_evaluated,
    }
    
    out_path = Path("evaluation/generation_metrics.json")
    out_path.write_text(json.dumps(output, indent=2))
    print(f"\n[+] Metrics saved to {out_path}")


if __name__ == "__main__":
    main()