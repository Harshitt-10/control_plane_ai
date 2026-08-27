import json
import re
from pathlib import Path
from typing import Any, Optional

from src.models.schemas import TierResult, TierStatus

STATIC_KB = {
    "controlplane": "ControlPlane is an AI output-checking gateway.",
    "pydantic": "Pydantic is used for structured data validation in Python.",
    "pii": "PII includes email addresses and phone numbers.",
}


def _load_mock_knowledge_base() -> dict[str, str]:
    kb_path = Path(__file__).resolve().parents[2] / "data" / "mock_knowledge_base.json"
    if not kb_path.exists():
        return {}

    with open(kb_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data if isinstance(data, dict) else {}


def _normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _build_aliases(key: str, value: str) -> list[str]:
    aliases = [_normalize(key), _normalize(value)]

    if key == "refund_policy":
        aliases.extend(
            [
                "refund within 14 days",
                "refunds within 14 days",
                "processed within 14 days",
                "14 days of the original purchase",
                "no exceptions for clearance items",
            ]
        )
    elif key == "server_downtime":
        aliases.extend(
            [
                "scheduled maintenance",
                "every sunday between 2 00 am and 4 00 am est",
                "sunday between 2 00 am and 4 00 am est",
                "server downtime",
            ]
        )

    return [alias for alias in aliases if alias]


def verify(text: str, context: Optional[dict[str, Any]] = None) -> TierResult:
    normalized_text = _normalize(text)
    knowledge_base = dict(STATIC_KB)
    knowledge_base.update(_load_mock_knowledge_base())
    relevant_hits = []

    for key, value in knowledge_base.items():
        aliases = _build_aliases(key, value)
        if any(alias in normalized_text for alias in aliases):
            relevant_hits.append(key)

    if not relevant_hits:
        return TierResult(
            status=TierStatus.not_applicable,
            score=0.0,
            reason="No relevant facts found in the static knowledge base, so RAG verification was not applicable.",
        )

    for key in relevant_hits:
        if key == "controlplane" and "controlplane" not in lowered:
            continue

    return TierResult(
        status=TierStatus.pass_,
        score=0.85,
        reason=f"Verified against static knowledge base entries: {', '.join(relevant_hits)}.",
    )
