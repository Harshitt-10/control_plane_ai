"""
Feedback logging.

Logs flagged/overridden cases with enough context (response, tier results, score,
decision, human override if any) to support later offline threshold tuning.
Not an online/live learning mechanism -- see docs/decisions.md.
"""

def log_case(response: dict, tier_results: dict, scoring_result: dict, decision: dict, override: dict = None) -> None:
    raise NotImplementedError("TODO: implement feedback logging (e.g. append to data/feedback_log.jsonl)")
