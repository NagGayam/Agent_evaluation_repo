"""Trial RAGAS thresholds; calibrate against reviewed examples."""

THRESHOLD_VERSION = "v1"

THRESHOLDS = {
    "context_precision": 0.80,
    "context_recall": 0.80,
    "faithfulness": 0.90,
    "answer_relevancy": 0.80,
    "answer_correctness": 0.80,
}