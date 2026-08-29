from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from src.models.schemas import TierResult, TierStatus

STATIC_KB = {
    "controlplane": "ControlPlane is an AI output-checking gateway.",
    "pydantic": "Pydantic is used for structured data validation in Python.",
    "pii": "PII includes email addresses and phone numbers.",
}


def _normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


@lru_cache(maxsize=1)
def _load_knowledge_base() -> dict[str, str]:
    kb_path = Path(__file__).resolve().parents[1] / "data" / "knowledge_base.json"
    if not kb_path.exists():
        return {}

    with open(kb_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data if isinstance(data, dict) else {}


def _build_aliases(key: str, value: str) -> list[str]:
    aliases = [_normalize(key), _normalize(value)]

    if key == "remote_work_stipend":
        aliases.extend(
            [
                "remote work stipend",
                "home office equipment reimbursement",
                "ergonomic accessories",
                "approved connectivity costs",
                "calendar year",
            ]
        )
    elif key == "remote_work_stipend_expenses":
        aliases.extend(
            [
                "eligible stipend expenses",
                "external monitors webcams headsets",
                "docking stations",
                "internet upgrade fee",
            ]
        )
    elif key == "remote_work_stipend_deadline":
        aliases.extend(
            [
                "reimbursement deadline",
                "submit within 45 days",
                "purchase date",
            ]
        )
    elif key == "it_security_password_rules":
        aliases.extend(
            [
                "password rules",
                "password must be at least 14 characters",
                "uppercase lowercase numbers special characters",
            ]
        )
    elif key == "it_security_mfa":
        aliases.extend(
            [
                "multi factor authentication",
                "mfa",
                "authenticator apps hardware security keys",
                "vpn access email payroll source control",
            ]
        )
    elif key == "it_security_password_rotation":
        aliases.extend(
            [
                "password rotation",
                "password change",
                "compromise suspected",
            ]
        )
    elif key == "mess_management_system":
        aliases.extend(
            [
                "mess management system",
                "meal planning vendor coordination cafeteria",
            ]
        )
    elif key == "mess_management_system_deployment_stack":
        aliases.extend(
            [
                "mess management system deployment stack",
                "react frontend fastapi api",
                "postgresql redis docker kubernetes",
                "production deployments",
            ]
        )
    elif key == "mess_management_system_environments":
        aliases.extend(
            [
                "development staging production environments",
                "staging mirrors production",
                "release validation",
            ]
        )
    elif key == "mess_management_system_release_process":
        aliases.extend(
            [
                "ci cd pipeline",
                "automated tests security scans manual approval",
                "rollback container image",
            ]
        )
    elif key == "mess_management_system_monitoring":
        aliases.extend(
            [
                "application logs api latency dashboards",
                "database health alerts pod restart",
                "on call engineering channel",
            ]
        )

    return [alias for alias in aliases if alias]



def _find_matching_topics(prompt_text: str, knowledge_base: dict[str, str]) -> list[tuple[str, str]]:
    normalized_prompt = _normalize(prompt_text)
    matches: list[tuple[str, str]] = []

    for key, value in knowledge_base.items():
        aliases = _build_aliases(key, value)
        if any(alias in normalized_prompt for alias in aliases):
            matches.append((key, value))

    return matches


def _response_mentions_fact(response_text: str, fact_text: str) -> bool:
    response = _normalize(response_text)
    fact_tokens = [token for token in _normalize(fact_text).split() if len(token) > 2]
    if not fact_tokens:
        return False
    return sum(1 for token in fact_tokens if token in response) >= max(2, len(fact_tokens) // 4)


def verify(text: str, context: Optional[dict[str, Any]] = None) -> TierResult:
    context = context or {}
    prompt_text = context.get("user_prompt") or context.get("prompt") or text

    knowledge_base = dict(STATIC_KB)
    knowledge_base.update(_load_knowledge_base())

    matched_topics = _find_matching_topics(prompt_text, knowledge_base)
    if not matched_topics:
        return TierResult(
            status=TierStatus.not_applicable,
            score=0.0,
            reason="No matching topic was found in the enterprise knowledge base, so RAG verification was not applicable.",
        )

    verified_topics = []
    for key, fact_text in matched_topics:
        if _response_mentions_fact(text, fact_text):
            verified_topics.append(key)

    if verified_topics:
        return TierResult(
            status=TierStatus.pass_,
            score=0.95,
            reason=(
                "Verified the AI response against enterprise knowledge base topic(s): "
                f"{', '.join(verified_topics)}."
            ),
        )

    return TierResult(
        status=TierStatus.fail,
        score=0.2,
        reason=(
            "A matching enterprise topic was found, but the AI response did not sufficiently "
            "align with the ground-truth text in the knowledge base."
        ),
    )
