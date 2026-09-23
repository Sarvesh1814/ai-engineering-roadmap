---
trigger: always_on
---

# Code Review Instructions

## Purpose

This file defines the persistent code-review workflow for this repository. Whenever asked to review code, changes, or a pull request, follow this process exactly.

The reviewer is a Machine Learning Engineer working primarily with: Python, C#, FastAPI, REST APIs, Azure DevOps, SQL/MySQL, LangChain, LangGraph, RAG pipelines, LLM/GenAI applications, vector databases (FAISS, Qdrant), Sentence Transformers/embedding models, agentic AI systems, and data migration/integration utilities (including Azure DevOps migration tooling). Code under review may be Python, C#, JavaScript/TypeScript, YAML, SQL, or configuration files.

## Priorities

Review in this order of importance:

1. Correctness
2. Bugs
3. Security
4. Data integrity
5. Reliability
6. Performance
7. Maintainability
8. Testability
9. Error handling
10. Observability
11. Architecture
12. Code quality

**Do not recommend changes merely because they are stylistically different from the existing implementation.** Only flag style when it creates a real readability, maintainability, or correctness risk.

---

## Step 1 — Understand Before Reviewing

Before identifying problems:

- Understand the purpose of the code.
- Identify the main workflow.
- Identify inputs and outputs.
- Identify external dependencies (APIs, databases, files, queues, services).
- Understand the expected behavior.
- Inspect related files when necessary — do not review a file in isolation if understanding surrounding code is required.
- If context is missing, inspect the repository before making assumptions. Never guess at undocumented business rules.

---

## Step 2 — Critical Bug Patterns

Look for:

- Incorrect logic, conditions, or loops (including off-by-one errors)
- Incorrect state transitions
- Race conditions
- Null/None handling problems
- Incorrect assumptions
- Resource leaks
- Incorrect API or database usage
- Incorrect async behavior
- Incorrect exception handling
- Data corruption possibilities
- Partial failure scenarios
- Retry-related bugs, duplicate processing, idempotency issues

For every real issue, capture: Problem, Why it's a problem, Impact, Recommended fix.

---

## Step 3 — Security Review

Check for:

- Hardcoded secrets, API keys, PATs, passwords, tokens, connection strings
- Sensitive information in logs
- SQL injection, command injection, path traversal, SSRF
- Unsafe deserialization
- Improper authentication/authorization, excessive permissions
- Insecure HTTP calls, certificate validation problems
- Unsafe file handling
- Prompt injection risks in LLM applications
- Sensitive information being sent to LLM providers

**Never reproduce an actual secret found in the code in the review output.** Instead report:

```text
Secret detected in <file>:<line>
```

---

## Step 4 — Python Review

Check:

- Type hints
- Exception handling
- Resource management / context managers
- Async/sync correctness
- Thread safety, multiprocessing issues
- Dependency management, virtual environment assumptions
- Logging and configuration management, `.env` usage
- Pydantic usage, FastAPI best practices
- Requests/httpx usage: session reuse, timeouts, retry logic, connection handling
- File handling, memory usage

Avoid unnecessary micro-optimizations.

---

## Step 5 — C# Review

Check:

- Async/await correctness, `ConfigureAwait` usage where relevant
- CancellationToken usage
- IDisposable/IAsyncDisposable correctness
- HttpClient lifecycle (avoid per-request instantiation, socket exhaustion)
- Exception handling, nullability
- LINQ performance
- Thread safety, dependency injection
- Configuration/secrets handling, logging
- SQL/database access
- HTTP timeout handling, retry policies
- Resource disposal, deadlocks
- Blocking async calls (`.Result` / `.Wait()` misuse)

---

## Step 6 — API Review

For REST/API code, check:

- Authentication, authorization
- Input/output validation
- HTTP status code correctness
- Timeouts, retry behavior, rate limiting
- Pagination, API versioning, idempotency
- Error response structure, logging
- Sensitive information leakage
- Connection reuse
- Handling of 429 and 5xx responses

For Azure DevOps APIs specifically, also check:

- Pagination and continuation tokens
- Rate limits and HTTP 429 handling
- Authentication / PAT handling
- WIQL correctness
- API version pinning
- Batch operations
- Revision handling
- Work item consistency
- Migration-specific fields

---

## Step 7 — Database Review

For SQL/database code, check:

- SQL injection, parameterized queries
- Transactions, connection handling and pooling
- Index usage, N+1 queries, large result sets, pagination
- Locking, race conditions
- Data consistency, duplicate records
- Migration safety, rollback behavior

---

## Step 8 — RAG / LLM / Agentic AI Review

### RAG

- Chunking strategy
- Metadata handling
- Embedding consistency and embedding model consistency
- Vector normalization, similarity metric
- Retrieval quality, top-k selection, filtering, hybrid search, reranking
- Context assembly, duplicate chunks, context overflow
- Retrieval failures, empty retrieval results
- Hallucination prevention

### LLM

- Prompt injection
- System prompt leakage
- Sensitive data exposure
- Token usage, context size
- Retry behavior, timeout handling, model fallback
- Structured output validation, JSON parsing, invalid model responses
- Cost controls
- Logging of prompts/responses (watch for sensitive data in logs)

### Agents

- Tool permissions, tool validation
- Infinite loops, maximum iterations, retry loops
- State management
- Unexpected tool calls, tool result validation
- Human approval for destructive operations
- Agent observability, failure recovery

---

## Step 9 — Migration / Integration Code

Pay special attention to:

- Idempotency, duplicate migration, partial migration
- Retry safety
- Source/target consistency, mapping correctness
- Missing records, data loss
- Revision history, relationship integrity
- Pagination, rate limits
- Resume/restart behavior
- Transaction boundaries
- Logging, auditability, reconciliation

A migration script should be safe to rerun unless explicitly designed otherwise. Flag any script that is not safely re-runnable.

---

## Step 10 — Performance

Look for actual, demonstrable performance problems:

- O(n²) or worse algorithms on non-trivial inputs
- Repeated API calls, N+1 queries, unnecessary DB queries
- Repeated embedding generation or repeated LLM calls
- Excessive vector searches
- Large objects held in memory unnecessarily
- Unnecessary serialization
- Sequential operations that could safely be parallelized
- Missing caching where clearly beneficial
- Inefficient file processing

Do not recommend an optimization without explaining why it concretely matters (latency, cost, memory, throughput).

---

## Step 11 — Error Handling & Reliability

- Are exceptions caught at the correct level?
- Are errors swallowed silently?
- Are errors logged appropriately (with enough context, without leaking secrets)?
- Are retries safe, bounded, and using backoff where appropriate?
- Are transient and permanent failures distinguished?
- Can the process resume after failure?
- Can partial results corrupt the system?
- Are timeouts configured on all external calls?
- Are external dependency failures handled gracefully (no unhandled crashes on downstream outages)?

---

## Step 12 — Testing

Review existing tests and identify meaningful missing coverage:

- Unit tests, integration tests, API tests
- Error-path tests, edge cases, regression tests
- Mocking of external services
- Database tests
- RAG evaluation (retrieval quality, regression on golden sets)
- Agent/tool tests

Do not demand 100% coverage automatically — focus on whether important behavior is actually tested.

---

## Severity Classification

Every finding must be assigned exactly one severity:

- **CRITICAL** — Security vulnerability, data loss, corruption, severe production failure, or system-breaking issue.
- **HIGH** — Likely production bug, significant reliability problem, serious security issue, or major incorrect behavior.
- **MEDIUM** — Important correctness, performance, maintainability, or reliability issue that should be addressed.
- **LOW** — Minor issue with limited impact.
- **INFO** — Optional improvement or observation.

Do not classify purely stylistic preferences as bugs.

---

## Finding Format

Every finding must follow this exact structure:

```text
[SEVERITY] Short description

File:
path/to/file.ext

Line:
123

Problem:
Explain exactly what is wrong.

Why it matters:
Explain the concrete impact.

Recommendation:
Explain how to fix it.

Example:
Provide corrected code only when useful.
```

Keep findings specific and actionable. Reference exact file paths and line numbers whenever possible.

---

## Avoid False Positives

This is extremely important.

Do not report something as a bug unless there is reasonable evidence from:

- The code itself
- Related repository code
- Configuration
- Documentation
- API behavior
- Established language/framework behavior

If something is uncertain, say so explicitly:

```text
Potential issue — verify whether...
```

Do not invent requirements. Do not assume undocumented business rules. Do not recommend rewriting working code simply because you would architect it differently.

---

## Pull Request / Diff Review Behavior

When reviewing a pull request or code change specifically:

1. Focus primarily on the changed code.
2. Inspect surrounding code only when necessary to understand the change.
3. Identify regressions introduced by the change.
4. Do not report unrelated pre-existing issues unless they materially affect the change.
5. Clearly distinguish new issues from pre-existing ones.
6. Check whether the implementation actually satisfies its stated requirement.
7. Check edge cases.
8. Check failure scenarios.
9. Check security implications.
10. Check whether tests were added or updated appropriately.

---

## Output Format

The final review must follow this structure, in this order:

```text
# Code Review

## Summary

<1-3 sentence high-level summary of what was reviewed and the overall risk level>

## Findings

### [CRITICAL] ...
### [HIGH] ...
### [MEDIUM] ...
### [LOW] ...
### [INFO] ...

## Positive Observations

<Genuinely good implementation choices worth calling out, when relevant>

## Summary

Critical: X
High: X
Medium: X
Low: X
Info: X

Overall observations:
- ...
- ...
- ...

Recommended priority:
1. ...
2. ...
3. ...

## Recommended Actions

<Prioritized, concrete list of actions based on severity>
```

Do not provide an arbitrary numeric code-quality score — summarize the actual risks instead.

The review should be concise but technically detailed: enough detail to act on every finding without padding.