from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Union

import yaml

from src.models.schemas import DecisionAction, FinalDecision, ScoringResult


@dataclass(frozen=True)
class PolicyProfile:
    strictness: str
    thresholds: dict[str, float]
    actions: dict[str, str]


def load_policy_config(path: "str | Path" = "config.yaml") -> dict[str, Any]:
    config_path = Path(path)
    if not config_path.is_absolute() and config_path.as_posix() == "config.yaml":
        config_path = Path(__file__).resolve().parents[2] / "config.yaml"

    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _resolve_profile(config: dict[str, Any], use_case: str) -> Optional[PolicyProfile]:
    use_cases = config.get("use_cases", {})
    profile = use_cases.get(use_case)
    if not profile:
        return None
    return PolicyProfile(
        strictness=profile.get("strictness", "medium"),
        thresholds=profile.get("thresholds", {}),
        actions=profile.get("actions", {"pass": "allow", "review": "flag", "critical": "block"}),
    )


def decide(
    use_case: str,
    confidence: Union[float, ScoringResult],
    config: Optional[dict[str, Any]] = None,
    has_flags: bool = False,
) -> FinalDecision:
    config = config or load_policy_config()
    profile = _resolve_profile(config, use_case)

    # Accept either a bare float (from orchestrator.py) or a ScoringResult object
    if isinstance(confidence, ScoringResult):
        score = confidence.final_confidence
    else:
        score = float(confidence)

    if profile is None:
        action = DecisionAction.flag if has_flags else DecisionAction.allow
        return FinalDecision(action=action, final_confidence=score)

    # Derive pass/block thresholds from config. The per-use-case config has
    # individual tier thresholds (heuristics, rag, judge). For the combined
    # score we use: pass = min of all thresholds (conservative), and
    # block = lowest threshold when strictness is strict.
    tier_thresholds = profile.thresholds
    if tier_thresholds:
        # Most conservative: require all tiers to clear their threshold.
        pass_threshold = min(tier_thresholds.values())
        # Flag/block split: use the average as the midpoint.
        avg_threshold = sum(tier_thresholds.values()) / len(tier_thresholds)
    else:
        pass_threshold = 0.8
        avg_threshold = 0.5

    # Map config action names to DecisionAction
    action_map = {
        k: DecisionAction(v) for k, v in profile.actions.items()
        if v in DecisionAction._value2member_map_
    }
    allow_action = action_map.get("pass", DecisionAction.allow)
    flag_action = action_map.get("review", DecisionAction.flag)
    block_action = action_map.get("critical", DecisionAction.block)

    if has_flags:
        # Flagged content: block on strict + low confidence, else flag
        action = (
            block_action
            if profile.strictness == "strict" and score < avg_threshold
            else flag_action
        )
    else:
        if score >= pass_threshold:
            action = allow_action
        elif score >= avg_threshold:
            action = flag_action
        else:
            action = block_action if profile.strictness == "strict" else flag_action

    return FinalDecision(action=action, final_confidence=score)
