import json
from pathlib import Path
from typing import Any

from retrieval import Retriever


def load_golden_dataset(path: str = "evaluation/golden_dataset.json") -> list[dict[str, Any]]:
    with open(path, "r") as f:
        return json.load(f)


def evaluate_retrieval(golden_dataset: list[dict[str, Any]], retriever: Retriever) -> dict[str, float]:
    metrics = {
        "recall_at_1": 0.0,
        "recall_at_3": 0.0,
        "recall_at_5": 0.0,
        "recall_at_10": 0.0,
        "mrr": 0.0,
        "total_queries": len(golden_dataset),
    }

    recall_counts = {1: 0, 3: 0, 5: 0, 10: 0}
    mrr_sum = 0.0

    for item in golden_dataset:
        query = item["query"]
        expected_ids = set(item["expected_ticket_ids"])

        response = retriever.retrieve(query)

        retrieved_ids = [t.ticket_id for t in response.tickets]

        for k in [1, 3, 5, 10]:
            top_k = retrieved_ids[:k]
            if expected_ids & set(top_k):
                recall_counts[k] += 1

        for i, rid in enumerate(retrieved_ids, 1):
            if rid in expected_ids:
                mrr_sum += 1.0 / i
                break

    metrics["recall_at_1"] = recall_counts[1] / len(golden_dataset)
    metrics["recall_at_3"] = recall_counts[3] / len(golden_dataset)
    metrics["recall_at_5"] = recall_counts[5] / len(golden_dataset)
    metrics["recall_at_10"] = recall_counts[10] / len(golden_dataset)
    metrics["mrr"] = mrr_sum / len(golden_dataset)

    return metrics


def main():
    print("[+] Loading golden dataset...")
    golden = load_golden_dataset()
    print(f"[+] Loaded {len(golden)} queries")

    print("[+] Initializing retriever...")
    retriever = Retriever()
    retriever.connect()

    print("[+] Running evaluation...")
    metrics = evaluate_retrieval(golden, retriever)

    print("\n[+] Evaluation Results:")
    print(f"  Recall@1:  {metrics['recall_at_1']:.3f}")
    print(f"  Recall@3:  {metrics['recall_at_3']:.3f}")
    print(f"  Recall@5:  {metrics['recall_at_5']:.3f}")
    print(f"  Recall@10: {metrics['recall_at_10']:.3f}")
    print(f"  MRR:       {metrics['mrr']:.3f}")

    output_path = Path("evaluation/retrieval_metrics.json")
    with output_path.open("w") as f:
        json.dump(metrics, f, indent=2)
    print(f"\n[+] Metrics saved to {output_path}")


if __name__ == "__main__":
    main()