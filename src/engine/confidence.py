from __future__ import annotations

from collections.abc import Mapping
from typing import Iterable

from src.models.schemas import TierResult, TierStatus


def calculate_confidence(tier_results):
    """
    Calculate an overall confidence score from tier results.

    Only tiers with pass or fail statuses are counted. Tiers marked
    not_applicable are ignored completely.
    """
    if isinstance(tier_results, Mapping):
        results = list(tier_results.values())
    else:
        results = list(tier_results)

    applicable = [
        result
        for result in results
        if result.status in (TierStatus.pass_, TierStatus.fail)
    ]
    if not applicable:
        return 0.0

    score_sum = sum(float(result.score) for result in applicable)
    return round(score_sum / len(applicable), 4)
