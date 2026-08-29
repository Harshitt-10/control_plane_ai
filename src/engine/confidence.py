from __future__ import annotations

from collections.abc import Mapping

from src.models.schemas import ScoringResult, TierStatus

# Maximum confidence when one or more tiers returned not_applicable.
# Keeps the score below the typical "allow" threshold so unverified
# responses are never silently approved.
_COVERAGE_CAP = 0.75


def calculate_confidence(tier_results) -> ScoringResult:
    """
    Calculate a confidence score from tier results, honouring the coverage rule:
    - All not_applicable  → score 0.0, coverage_complete False
    - Any not_applicable  → score capped at _COVERAGE_CAP, coverage_complete False
    - All pass/fail       → simple average, coverage_complete True
    """
    if isinstance(tier_results, Mapping):
        results = list(tier_results.values())
    else:
        results = list(tier_results)

    applicable = [
        r for r in results if r.status in (TierStatus.pass_, TierStatus.fail)
    ]
    not_applicable = [r for r in results if r.status == TierStatus.not_applicable]
    coverage_complete = len(not_applicable) == 0

    if not applicable:
        return ScoringResult(
            final_confidence=0.0,
            coverage_complete=False,
            explanation=(
                "All tiers returned not_applicable; no evidence is available "
                "to assess the response."
            ),
        )

    raw_score = round(sum(float(r.score) for r in applicable) / len(applicable), 4)

    if not coverage_complete:
        capped = round(min(raw_score, _COVERAGE_CAP), 4)
        skipped = [r.reason for r in not_applicable]
        explanation = (
            f"Raw score {raw_score} capped to {capped} because "
            f"{len(not_applicable)} tier(s) were not_applicable "
            f"(coverage incomplete). Skipped: {'; '.join(skipped)}"
        )
        return ScoringResult(
            final_confidence=capped,
            coverage_complete=False,
            explanation=explanation,
        )

    return ScoringResult(
        final_confidence=raw_score,
        coverage_complete=True,
        explanation=(
            f"All {len(applicable)} tier(s) evaluated. "
            f"Average score: {raw_score}."
        ),
    )
