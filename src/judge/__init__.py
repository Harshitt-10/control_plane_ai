"""
judge check tier.

Each tier exposes a single check(response: dict, context: dict) -> TierResult function.
TierResult (see src/scoring/types.py once defined) should report status as one of:
"pass", "fail", or "not_applicable", plus a raw confidence float and any evidence/notes.
"""

def check(response: dict, context: dict) -> dict:
    """
    Run this tier's check against an AI response.

    Args:
        response: the AI-generated response under evaluation (text + metadata)
        context: use case, region, and any retrieved source documents (for rag tier)

    Returns:
        dict with keys: status ("pass" | "fail" | "not_applicable"), confidence (float 0-1),
        notes (str, optional evidence/explanation)
    """
    raise NotImplementedError("TODO: implement judge check")
