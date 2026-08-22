"""
Policy engine.

Loads config/policies.yaml and decides an action (allow / flag_for_review / block)
based on the confidence score and per-use-case thresholds.
"""

def load_policies(path: str = "config/policies.yaml") -> list:
    raise NotImplementedError("TODO: load and parse policies.yaml")


def decide(use_case: str, scoring_result: dict, policies: list) -> dict:
    """
    Returns:
        dict with keys: action ("allow" | "flag_for_review" | "block"), reason (str)
    """
    raise NotImplementedError("TODO: implement policy decision logic")
