from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Optional

from src.engine.confidence import calculate_confidence
from src.engine.policy import decide, load_policy_config
from src.models.schemas import EvalRequest, FinalDecision, ScoringResult, TierResult, TierStatus
from src.tiers.ai_judge import evaluate as judge_evaluate
from src.tiers.heuristics import check as heuristics_check
from src.tiers.rag_verifier import verify as rag_verify


def _dump_model(model: Any) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


async def _run_tier(fn, text: str, context: dict[str, Any]) -> TierResult:
    return await asyncio.to_thread(fn, text, context)


async def evaluate_request(request: EvalRequest, config_path: "str | Path" = "config.yaml") -> dict[str, Any]:
    config = load_policy_config(config_path)
    request_data = _dump_model(request)

    tier_tasks = {
        "heuristics": _run_tier(heuristics_check, request.ai_response, request_data),
        "rag": _run_tier(rag_verify, request.ai_response, request_data),
        "judge": _run_tier(judge_evaluate, request.ai_response, request_data),
    }
    tier_results = await asyncio.gather(*tier_tasks.values())
    tier_map = dict(zip(tier_tasks.keys(), tier_results))

    overall_confidence = calculate_confidence(tier_map)
    has_flags = any(result.status == TierStatus.fail for result in tier_map.values())
    decision: FinalDecision = decide(
        request.use_case,
        overall_confidence,
        config=config,
        has_flags=has_flags,
    )

    output = {
        "request": request_data,
        "tier_results": {name: _dump_model(result) for name, result in tier_map.items()},
        "overall_confidence": overall_confidence.final_confidence,
        "decision": _dump_model(decision),
    }

    if decision.action.value != "allow":
        await _append_feedback_log(output)

    return output


async def _append_feedback_log(entry: dict[str, Any], path: "str | Path" = "feedback_log.json") -> None:
    log_path = Path(path)
    existing: list[dict[str, Any]] = []

    if log_path.exists():
        try:
            existing_data = json.loads(log_path.read_text(encoding="utf-8"))
            if isinstance(existing_data, list):
                existing = existing_data
        except json.JSONDecodeError:
            existing = []

    existing.append(entry)
    log_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")


async def main() -> None:
    sample = EvalRequest(
        user_prompt="Summarize this document.",
        ai_response="Contact me at jane@example.com or call 555-123-4567.",
        use_case="customer_support_chatbot",
    )
    result = await evaluate_request(sample)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
