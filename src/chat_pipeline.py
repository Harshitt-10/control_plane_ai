from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Optional

from src.engine.confidence import calculate_confidence
from src.engine.groq_client import get_groq_client
from src.engine.policy import decide, load_policy_config
from src.feedback import log_case
from src.models.schemas import TierStatus
from src.tiers import heuristics_check, rag_verify, ai_judge as judge_evaluate_fn

_STOPWORDS = {
    "the",
    "and",
    "for",
    "what",
    "when",
    "with",
    "from",
    "that",
    "this",
    "are",
    "can",
    "buy",
    "about",
    "into",
    "your",
    "you",
    "may",
    "how",
    "what",
    "policy",
    "rules",
    "stipends",
    "work",
    "remote",
}


def _normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


@lru_cache(maxsize=1)
def _load_local_facts() -> dict[str, str]:
    candidates = [
        Path(__file__).resolve().parent / "data" / "knowledge_base.json",
        Path(__file__).resolve().parents[1] / "data" / "mock_knowledge_base.json",
    ]

    for path in candidates:
        if not path.exists():
            continue
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return {str(k): str(v) for k, v in data.items()}
    return {}


def _tokenize(text: str) -> set[str]:
    tokens = _normalize(text).split()
    return {token for token in tokens if len(token) > 2 and token not in _STOPWORDS}


def _topic_root(key: str) -> str:
    if key.startswith("remote_work_stipend"):
        return "remote_work_stipend"
    if key.startswith("it_security_"):
        return "it_security"
    if key.startswith("mess_management_system"):
        return "mess_management_system"
    return key.split("_")[0]


def search_local_facts(query: str, limit: int = 5) -> list[dict[str, str]]:
    facts = _load_local_facts()
    query_tokens = _tokenize(query)
    ranked: list[tuple[int, str, str]] = []

    for key, value in facts.items():
        haystack = _normalize(f"{key} {value}")
        score = sum(1 for token in query_tokens if token in haystack)
        if score:
            ranked.append((score, key, value))

    ranked.sort(key=lambda item: (-item[0], item[1]))
    if not ranked:
        return []

    best_key = ranked[0][1]
    best_root = _topic_root(best_key)
    topic_matches = [
        {"key": key, "fact": value}
        for _, key, value in ranked
        if _topic_root(key) == best_root
    ]
    return topic_matches[:limit]



def _build_context_snippet(facts: Iterable[dict[str, str]]) -> str:
    lines = []
    for item in facts:
        lines.append(f"- {item['key']}: {item['fact']}")
    return "\n".join(lines) if lines else "- No relevant facts were found."


def generate_grounded_response(user_prompt: str, facts: list[dict[str, str]]) -> str:
    client = get_groq_client()
    context_snippet = _build_context_snippet(facts)

    if client is None:
        if facts:
            first_fact = facts[0]["fact"]
            return (
                f"Based on the available internal facts, the relevant guidance is: {first_fact}"
            )
        return "I could not find relevant internal facts to ground a response."

    prompt = (
        "Determine if the USER PROMPT is a general-knowledge / external question or an internal company-specific question.\n"
        "1. If the prompt is a general knowledge or general external question unrelated to internal company policy or details (e.g. capitals, science, math, general help), answer it directly using your general knowledge.\n"
        "2. If the prompt is about company policies, procedures, systems, or internal operations (e.g., remote work stipend, password rules, internal systems), you MUST ground your response strictly in the FACTS provided below. Do not invent any internal company details. If the facts are insufficient to answer the internal company question, say that the available internal knowledge base does not contain enough information.\n\n"
        f"USER PROMPT:\n{user_prompt}\n\n"
        f"FACTS:\n{context_snippet}\n"
    )

    try:
        response = client.chat.completions.create(
            model=os.getenv("GROQ_CHAT_MODEL", "openai/gpt-oss-20b"),
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an internal enterprise assistant. Answer general knowledge queries directly. "
                        "For company-specific questions, strictly ground your answers in the supplied facts and refuse to answer if the facts are missing or insufficient."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        return (response.choices[0].message.content or "").strip()
    except Exception:
        if facts:
            joined_facts = " ".join(item["fact"] for item in facts[:2])
            return (
                "I could not reach the Groq API, so here is a grounded fallback based on the "
                f"available internal facts: {joined_facts}"
            )
        return "I could not reach the Groq API and no relevant internal facts were found."


def run_governance(response_text: str, context: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    context = context or {}
    tier_results = {
        "heuristics": heuristics_check(response_text, context),
        "rag": rag_verify(response_text, context),
        "judge": judge_evaluate_fn(response_text, context),
    }
    scoring_result = calculate_confidence(tier_results)
    policy_config = load_policy_config(context.get("policy_path", "config.yaml"))
    use_case = context.get("use_case", "default")
    decision = decide(
        use_case,
        scoring_result,
        policy_config,
        has_flags=any(result.status == TierStatus.fail for result in tier_results.values()),
    )
    return {
        "tier_results": tier_results,
        "scoring": scoring_result,
        "decision": decision,
    }


def chat_pipeline(user_prompt: str, context: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    context = context or {}
    facts = search_local_facts(user_prompt, limit=context.get("retrieval_limit", 5))
    draft = generate_grounded_response(user_prompt, facts)
    governance = run_governance(draft, context)

    try:
        log_case(
            response={"text": draft, "user_prompt": user_prompt},
            tier_results=governance["tier_results"],
            scoring_result=governance["scoring"],
            decision=governance["decision"],
        )
    except NotImplementedError:
        pass

    return {
        "user_prompt": user_prompt,
        "retrieved_facts": facts,
        "draft_response": draft,
        **governance,
    }
