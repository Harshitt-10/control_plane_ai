from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import yaml

from src.models.schemas import DecisionAction, FinalDecision


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
    confidence: float,
    config: Optional[dict[str, Any]] = None,
    has_flags: bool = False,
) -> FinalDecision:
    config = config or load_policy_config()
    profile = _resolve_profile(config, use_case)

    if profile is None:
        action = DecisionAction.flag if has_flags else DecisionAction.allow
        return FinalDecision(action=action, final_confidence=confidence)

    if has_flags:
        action = DecisionAction.block if profile.strictness == "strict" and confidence < 0.6 else DecisionAction.flag
    else:
        if confidence >= 0.8:
            action = DecisionAction.allow
        elif confidence >= 0.5:
            action = DecisionAction.flag
        else:
            action = DecisionAction.block if profile.strictness == "strict" else DecisionAction.flag

    return FinalDecision(action=action, final_confidence=confidence)
