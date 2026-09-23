---
description: Perform a thorough, senior-level code review
---

---
description: Comprehensive, repository-aware code review of changed files or the current diff, following codereview.md rules. Covers correctness, security, reliability, performance, and technology-specific checks for Python, C#, APIs, SQL, Azure DevOps, RAG/LLM, and agentic AI code. Produces a structured findings report.
---

# Code Review Workflow

Perform a thorough, senior-level code review. Follow every stage below in order. Do not skip straight to writing findings.

## Stage 1 — Load Review Rules

1. Look for `codereview.md` in the repository root (check common locations if not found there).
2. If found, read it fully and treat it as the primary rule set for severity, scope, format, and false-positive avoidance — everything below builds on it.
3. If `codereview.md` does not exist, continue using this workflow's built-in methodology, and state explicitly in the final report that the repository-specific rules file was not found.

## Stage 2 — Repository Discovery

4. Inspect the repository structure at a high level. Do not read every file — only what's relevant to the change.
5. Identify: languages/frameworks in use, application type, entry points, config files, dependency manifests (`pyproject.toml`, `requirements.txt`, `package.json`, `*.csproj`, `*.sln`), test directories, API layers, database layers, and any AI/ML or agentic components.
6. Check for `README.md`, `Dockerfile`, `docker-compose.yml`, `.env.example`, `appsettings.json`, and similar files for context on how the system is intended to run.

## Stage 3 — Identify What's Being Reviewed

7. Determine scope in this priority order: (a) git diff / uncommitted changes, (b) current branch vs. base branch, (c) user-selected files, (d) relevant recent commits.
8. If no git information is available, review only the files the user explicitly pointed to.
9. Before reviewing, establish: what changed, why it likely changed, what behavior should change, and what behavior must remain unchanged. Do not report findings until this is clear.

## Stage 4 — Impact Analysis

10. For each changed file, identify: affected functions/classes/components, their callers, their dependencies, downstream effects, any APIs or database operations touched, config changes, and related existing tests.
11. Trace the chain: changed function → who calls it → what it calls → what data it modifies → what external systems are affected.
12. Inspect surrounding/related code whenever needed to judge correctness — but don't scan the whole repo unnecessarily.

## Stage 5 — Systematic Review (apply codereview.md priority order)

13. Review in this order: Correctness → Security → Data integrity → Reliability → Performance → Maintainability → Testing → Style.
14. Look specifically for: logic bugs, incorrect assumptions, unhandled edge cases, null/None handling issues, incorrect API usage, incorrect state handling, concurrency issues and race conditions, resource leaks, error-handling gaps, retry/idempotency problems, data consistency issues, security vulnerabilities, and real performance problems.

## Stage 6 — Technology-Specific Checks

Apply whichever of these are relevant to the files under review:

15. **Python** — async/sync correctness, exception handling, context managers, HTTP client usage (timeouts, retries, session reuse), type hints, Pydantic/FastAPI usage, dependency and config management, logging.
16. **C#** — async/await correctness (including blocking `.Result`/`.Wait()` misuse), `HttpClient` lifecycle, `CancellationToken` usage, `IDisposable`/`IAsyncDisposable`, dependency injection, nullability, LINQ performance, SQL access, thread safety.
17. **SQL** — injection risk, parameterization, transactions, indexing, locking, query efficiency, duplicate or inconsistent data.
18. **REST APIs** — authentication, authorization, input/output validation, status codes, timeouts, retries, rate limiting, pagination, idempotency, error-response structure.
19. **Azure DevOps integrations** — REST API usage, PAT security, pagination/continuation tokens, HTTP 429 handling, WIQL correctness, work item and revision consistency, source/target mapping correctness for migrations.
20. **RAG / LLM / Agentic AI** — prompt injection, sensitive-data exposure to model providers, hallucination risk, chunking and embedding consistency, vector search and reranking correctness, context-window/token handling, structured-output validation, tool permissions and validation, agent loop bounds (max iterations, retry loops), human approval on destructive tool actions, observability.

## Stage 7 — Validate Every Finding

21. Before reporting an issue, check: the surrounding code, how the function/class is called, relevant configuration, existing tests, and any in-repo documentation — to confirm it's a real issue and not intentional behavior.
22. Never report a speculative issue as a confirmed bug. If uncertain, phrase it as: `Potential issue — verify whether...`
23. Do not invent requirements or assume undocumented business rules.

## Stage 8 — Test Coverage Check

24. Check whether the change has adequate tests: existing tests still valid, new tests for new behavior, edge cases, error paths, and (where relevant) RAG/agent evaluation coverage.
25. Only flag missing coverage when it represents meaningful risk — do not demand tests for trivial changes.

## Stage 9 — Focused Security Pass

26. Scan specifically for hardcoded secrets, API keys, PATs, passwords, tokens, and connection strings; secrets leaking into logs; SQL/command injection; path traversal; SSRF; unsafe deserialization; authentication/authorization gaps; prompt injection; and unsafe tool execution in agentic code.
27. Never print an actual discovered secret in the report — report only `Secret detected in <file>:<line>`.

## Stage 10 — Migration / Data-Integrity Pass (when applicable)

28. If the repository or change touches migration or integration code, additionally check: source→target mapping correctness, duplicate or partial processing, resume/retry safety, idempotency, revision history and relationship integrity, transaction boundaries, audit logging, and reconciliation.
29. Give extra scrutiny to any code capable of modifying or deleting production data. Do not execute destructive operations (`DELETE`, `DROP`, `UPDATE`, file/work-item deletion, deployments) to validate a finding — reason about them statically instead, checking for confirmation gates, scoping, dry-run support, and rollback.

## Stage 11 — Compile Findings

30. Only report findings with real, demonstrable impact — skip theoretical or purely stylistic points.
31. Use this exact format per finding:

```text
### [SEVERITY] Short description

**File:** `path/to/file.ext`
**Line:** 123

**Problem:**
...

**Impact:**
...

**Recommendation:**
...
```

32. Severity is one of `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `INFO` — as defined in `codereview.md`. Never assign an overall numeric quality score.

## Stage 12 — Produce the Final Report

33. Output the report in this exact structure:

```markdown
# Code Review

## Summary
<what was reviewed and the overall state of the change>

## Findings
### [CRITICAL] ...
### [HIGH] ...
### [MEDIUM] ...
### [LOW] ...

## Positive Observations
<genuinely good implementation decisions, if any>

## Test Coverage
<what tests exist, what meaningful coverage may still be missing>

## Recommended Actions
1. ...
2. ...
3. ...

## Files Reviewed
- ...
```

34. If nothing meaningful was found, state plainly: `No significant correctness, security, reliability, or performance issues were identified.` Do not manufacture findings to fill the report.

## Operating Constraints

- Review only — do not modify files, run destructive commands, or refactor unrelated code unless explicitly asked.
- Do not rewrite the codebase or suggest architecture changes just because you'd have designed it differently.
- Do not report pre-existing, unrelated issues unless they materially affect the reviewed change.
- Prefer reviewing the actual diff over treating the whole repository as new code, but follow call chains and related files whenever needed to judge correctness.