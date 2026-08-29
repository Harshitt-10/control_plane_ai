"""
Entry point: runs AI responses through the full ControlPlane.ai pipeline.

Usage:
    python -m src.main --input data/simulated/example_responses.json
    python -m src.main --input data/simulated/example_responses.json --use-case internal_knowledge_assistant
"""
import argparse
import json

from src.chat_pipeline import chat_pipeline


def _dump(obj):
    """Recursively convert Pydantic models to plain dicts for JSON output."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if isinstance(obj, dict):
        return {k: _dump(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_dump(i) for i in obj]
    return obj


def run_pipeline(response: dict, context: dict) -> dict:
    """Run a single response dict through the chat pipeline."""
    text = response.get("text", "")
    use_case = context.get("use_case", "default")
    runtime_context = {**context, "use_case": use_case}
    result = chat_pipeline(text, runtime_context)
    return _dump(result)


def main():
    parser = argparse.ArgumentParser(description="ControlPlane.ai — batch evaluation CLI")
    parser.add_argument("--input", required=True, help="Path to a JSON file of simulated responses")
    parser.add_argument(
        "--use-case",
        default=None,
        help="Override use_case for all items (default: read from each item's context)",
    )
    args = parser.parse_args()

    with open(args.input, encoding="utf-8") as f:
        items = json.load(f)

    for i, item in enumerate(items):
        context = dict(item.get("context", {}))
        if args.use_case:
            context["use_case"] = args.use_case

        print(f"\n--- Item {i + 1} ---")
        result = run_pipeline(item.get("response", {}), context)
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
