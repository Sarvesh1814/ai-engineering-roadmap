#!/usr/bin/env python
"""
Unified evaluation CLI for retrieval and generation.
Run: python scripts/evaluate.py [retrieval|generation|all]
"""
import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def run_retrieval_eval():
    from evaluation.retrieval_eval import main as retrieval_main
    print("\n" + "="*50)
    print("RETRIEVAL EVALUATION")
    print("="*50)
    retrieval_main()


def run_generation_eval():
    from evaluation.generation_eval import main as generation_main
    print("\n" + "="*50)
    print("GENERATION EVALUATION")
    print("="*50)
    generation_main()


def main():
    parser = argparse.ArgumentParser(description="Run evaluation suites")
    parser.add_argument(
        "suite",
        choices=["retrieval", "generation", "all"],
        default="all",
        nargs="?",
        help="Which evaluation to run (default: all)"
    )
    args = parser.parse_args()

    if args.suite in ("retrieval", "all"):
        run_retrieval_eval()
    
    if args.suite in ("generation", "all"):
        run_generation_eval()

    print("\n" + "="*50)
    print("EVALUATION COMPLETE")
    print("="*50)


if __name__ == "__main__":
    main()