"""
Confidence scoring engine.

Combines TierResults from heuristics/rag/judge into a single confidence score.
Must explicitly account for "not_applicable" tiers (e.g. RAG with no corpus) rather than
silently dropping their weight -- see docs/decisions.md.
"""

def combine(tier_results: dict) -> dict:
    """
    Args:
        tier_results: {"heuristics": {...}, "rag": {...}, "judge": {...}}
            each value is a TierResult dict as returned by src/<tier>/check()

    Returns:
        dict with keys: confidence (float 0-1), coverage_complete (bool),
        capped_due_to_coverage (bool), explanation (str)
    """
    raise NotImplementedError("TODO: implement scoring logic")
