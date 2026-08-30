from __future__ import annotations
import argparse
import json
from pathlib import Path
from .app import run_question

def token_f1(prediction: str, reference: str) -> float:
    predicted, expected = prediction.lower().split(), reference.lower().split()
    common = sum(min(predicted.count(word), expected.count(word)) for word in set(predicted))
    if not predicted or not expected or not common:
        return 0.0
    precision, recall = common / len(predicted), common / len(expected)
    return 2 * precision * recall / (precision + recall)

def evaluate(path: Path) -> dict:
    examples = json.loads(path.read_text(encoding="utf-8"))
    results = []
    for item in examples:
        output = run_question(item["question"], identity="evaluation")
        results.append({"question": item["question"], "route_correct": output.get("doc_type") == item["namespace"],
                        "grounded": output.get("hallucination_result") == "grounded",
                        "f1": token_f1(output.get("generation", ""), item["reference"])})
    count = len(results) or 1
    return {"examples": len(results), "route_accuracy": sum(r["route_correct"] for r in results) / count,
            "grounded_rate": sum(r["grounded"] for r in results) / count,
            "mean_token_f1": sum(r["f1"] for r in results) / count, "results": results}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", type=Path)
    args = parser.parse_args()
    print(json.dumps(evaluate(args.dataset), indent=2))
