"""
Entry point: runs an AI response through the full ControlPlane.ai pipeline.

Usage:
    python -m src.main --input data/simulated/example_responses.json
"""
import argparse
import json

from src import heuristics, rag, judge, scoring, policy, feedback


def run_pipeline(response: dict, context: dict, policies: list) -> dict:
    tier_results = {
        "heuristics": heuristics.check(response, context),
        "rag": rag.check(response, context),
        "judge": judge.check(response, context),
    }
    scoring_result = scoring.combine(tier_results)
    decision = policy.decide(context["use_case"], scoring_result, policies)
    feedback.log_case(response, tier_results, scoring_result, decision)
    return {"tier_results": tier_results, "scoring": scoring_result, "decision": decision}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Path to a JSON file of simulated responses")
    parser.add_argument("--policies", default="config/policies.yaml")
    args = parser.parse_args()

    policies = policy.load_policies(args.policies)

    with open(args.input) as f:
        responses = json.load(f)

    for item in responses:
        result = run_pipeline(item["response"], item["context"], policies)
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
