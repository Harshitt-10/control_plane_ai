# ControlPlane.ai

A tiered, policy-driven checking layer for enterprise generative AI responses — evaluating bias,
hallucination risk, and privacy leaks in real time, with confidence scoring and human-in-the-loop
escalation. Built for the Accenture Innovation Challenge 2026 (Round 2, Problem Track 1).

## What this is

Enterprises run generative AI across many use cases at once (customer-facing chatbots, internal
copilots, decision-support tools), each with a different risk and latency profile. A single
one-size-fits-all checker doesn't work well everywhere. ControlPlane.ai routes each AI response
through a set of parallel checks, combines their results into a confidence score, and uses a
per-use-case policy config to decide whether to allow, flag for review, or block the response.

**Scope note:** this system does not claim to solve hallucination detection outright — there is
often no reliable ground truth to check a claim against. Instead, it explicitly tracks *coverage*
(was a claim actually verifiable?) alongside confidence, and degrades conservatively when
verification isn't possible, rather than silently treating "unchecked" the same as "checked and
passed."

## Architecture

```
AI response
    │
    ▼
┌─────────────────────────────────────────┐
│         Parallel check layer             │
│  heuristics   │   RAG verify  │  judge    │
│  (PII, regex) │  (may be N/A) │ (LLM-based)│
└─────────────────────────────────────────┘
    │
    ▼
Confidence scoring engine  (caps score if a tier is not_applicable)
    │
    ▼
Policy engine  (per-use-case thresholds, from config/policies.yaml)
    │
    ▼
Decision: allow / flag_for_review / block
    │
    ▼
Feedback log  (overrides recorded for future threshold tuning)
```

See `docs/architecture.md` for the fuller writeup and design rationale.

## Repo layout

```
src/
  heuristics/   fast rule-based checks (PII regex, anomaly heuristics)
  rag/          retrieval-based verification against a source corpus (when available)
  judge/        AI-as-judge secondary review
  scoring/      confidence scoring engine (combines tier outputs, handles coverage gaps)
  policy/       policy config loader + decision logic (allow/flag/block)
  feedback/     logging of overrides and flagged cases for future tuning
config/
  policies.yaml example per-use-case policy configuration
data/
  simulated/    simulated/sample AI responses used for local testing and demo
tests/          unit tests
docs/           architecture notes, design decisions, open questions
```

## Status

Early scaffold — architecture and interfaces defined, implementation in progress.

## Explicit non-goals (for this prototype)

- Not attempting automated "auto-edit" of flagged responses — see `docs/decisions.md`
- Not claiming a live/online learning loop — the feedback mechanism logs data for offline
  threshold tuning, not automatic retraining
- Not a source of ground truth itself — RAG verification only works where a source corpus exists

## Getting started

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m src.main --input data/simulated/example_responses.json
```
