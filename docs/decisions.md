# Design decisions

Running log of deliberate scope and design choices, so the reasoning isn't lost and doesn't need
re-litigating mid-build. Add to this as decisions are made.

## Auto-edit was cut from scope

Considered having the system automatically rewrite flagged content (e.g. redact PII inline).
Decided against a general auto-edit tier: an automated editor that modifies AI output without
review introduces its own unaudited point of failure. The three response tiers are `allow`,
`flag_for_review`, `block`. If time permits, a narrow, deterministic PII-redaction rule could be
added later — but it is explicitly out of scope for the base build.

## Coverage is tracked separately from confidence

Each check tier reports one of `pass`, `fail`, `not_applicable` — not just a pass/fail confidence
number. RAG verification in particular will often be `not_applicable` when no source corpus exists
for a claim. The scoring engine must not silently drop that tier's weight and let the remaining
tiers produce a normal-looking score. Instead, `not_applicable` on the verification tier caps the
maximum achievable confidence, and the output should explicitly say the claim was "unverified,"
not just report a number.

## AI-as-judge is not ground truth

The judge tier is a second LLM call, not a source of truth. Pitch and docs should be precise about
this: the system doesn't "detect hallucinations," it identifies when a response can't be verified
and routes conservatively. Overstating this distinction is a credibility risk in Q&A.

## Feedback loop is offline logging, not online learning

For this prototype, "learns from feedback" means: overrides and flagged cases are logged with
enough context to support later threshold retuning (manual or scripted, offline). It is not a
claim of live/automatic model retraining.

## Open questions (not yet decided)

- Exact confidence scoring formula (weighted average vs. max-of-risks vs. something else)
- What triggers escalation from `flag_for_review` to `block` vs. leaving it for a human
- How much of the policy config schema to finalize now vs. let evolve during implementation
