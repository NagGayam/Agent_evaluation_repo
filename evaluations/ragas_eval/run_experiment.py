"""Run up to 30 Langfuse dataset items and attach their five RAGAS scores.

    python -m evaluations.ragas_eval.run_experiment

Makes paid model/embedding requests. Each invocation creates a fresh named
experiment; references remain draft until independently reviewed.
"""

from datetime import datetime, timezone
import argparse
import json
import math

# Load root .env before SDK initialization.
from agent import settings  # noqa: F401
from agent.client import run_agent
from langfuse import Evaluation, get_client

from evaluations.ragas_eval.evaluators import RagasEvaluators
from evaluations.ragas_eval.thresholds import THRESHOLDS, THRESHOLD_VERSION


DATASET_NAME = "RAGAS_data_set"
langfuse = get_client()


async def _agent_task(*, item, **kwargs):
    """The SDK links this execution to the original Langfuse dataset item."""
    if not isinstance(item.input, dict) or not isinstance(item.expected_output, dict):
        raise ValueError("Dataset input and expected_output must be dictionaries")
    question = item.input.get("user_input")
    reference = item.expected_output.get("reference")
    if not isinstance(question, str) or not question.strip():
        raise ValueError("Dataset item is missing a nonblank user_input")
    if not isinstance(reference, str) or not reference.strip():
        raise ValueError("Dataset item is missing a nonblank reference answer")
    print(f"Dataset item: {item.id}\nQuestion: {question}")
    if (item.metadata or {}).get("reference_review_status") != "approved":
        print("Reference is not approved; scores do not establish financial accuracy.")
    result = await run_agent(question)
    print(f"Answer: {result['response']}\nTrace ID: {result['trace_id']}")
    print("Retrieved record IDs:", result["retrieved_context_ids"])
    print("Tool calls:", json.dumps(result.get("tool_calls", []), ensure_ascii=False))
    if result.get("tool_errors"):
        print("Tool errors:", json.dumps(result["tool_errors"], ensure_ascii=False))
    return result


METRIC_NAMES = (
    "context_precision", "context_recall", "faithfulness",
    "answer_relevancy", "answer_correctness",
)


def validate_thresholds():
    if set(THRESHOLDS) != set(METRIC_NAMES):
        raise ValueError("Thresholds must contain exactly the five RAGAS metric names")
    if not isinstance(THRESHOLD_VERSION, str) or not THRESHOLD_VERSION.strip():
        raise ValueError("THRESHOLD_VERSION must be nonblank")
    for name, value in THRESHOLDS.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError(f"Invalid threshold for {name}: expected a finite number in [0, 1]")


async def agent_task(*, item, **kwargs):
    try:
        return await _agent_task(item=item, **kwargs)
    except Exception as exc:
        # Keep failed cases in the experiment and let the evaluator label ERROR.
        error = f"{type(exc).__name__}: {exc}"
        print(f"Agent execution ERROR for {item.id}: {error}")
        return {"execution_error": error}


async def ragas_scores(*, input, output, expected_output, metadata=None, **kwargs):
    """Keep raw scores, decisions and errors separate for each metric."""
    evaluations = []
    statuses = {}
    score_metadata = {"threshold_version": THRESHOLD_VERSION,
                      "reference_review_status": (metadata or {}).get("reference_review_status", "unknown")}

    def record_error(name, error):
        statuses[name] = "ERROR"
        evaluations.append(Evaluation(
            name=f"{name}_status", value="ERROR", data_type="CATEGORICAL",
            comment=error, metadata={**score_metadata, "threshold": THRESHOLDS[name]},
        ))
        print(f"{name}: ERROR - {error}")

    try:
        if output.get("execution_error"):
            raise ValueError(output["execution_error"])
        question = input["user_input"]
        reference = expected_output["reference"]
        answer = output["response"]
        contexts = output["retrieved_contexts"]
        if not isinstance(answer, str) or not answer.strip():
            raise ValueError("Agent did not return a nonblank text answer")

        async with RagasEvaluators() as scorers:
            calls = [
                ("context_precision", scorers.context_precision, (question, reference, contexts)),
                ("context_recall", scorers.context_recall, (question, reference, contexts)),
                ("faithfulness", scorers.faithfulness_metric, (question, answer, contexts)),
                ("answer_relevancy", scorers.answer_relevancy, (question, answer)),
                ("answer_correctness", scorers.answer_correctness, (question, answer, reference)),
            ]
            for name, evaluator, arguments in calls:
                print(f"Scoring {name}...", flush=True)
                try:
                    if name in METRIC_NAMES[:3] and len(contexts) != len(output["retrieved_context_ids"]):
                        raise ValueError("Retrieved contexts and IDs are not aligned")
                    score = float(await evaluator(*arguments))
                    if not math.isfinite(score):
                        raise ValueError("Evaluator returned a nonfinite score")
                except Exception as exc:
                    record_error(name, f"{type(exc).__name__}: {exc}")
                    continue
                threshold = THRESHOLDS[name]
                passed = score >= threshold
                status = "PASS" if passed else "FAIL"
                statuses[name] = status
                details = {**score_metadata, "threshold": threshold}
                evaluations.extend([
                    Evaluation(name=name, value=score, metadata=details),
                    Evaluation(name=f"{name}_pass", value=passed, data_type="BOOLEAN", metadata=details),
                    Evaluation(name=f"{name}_status", value=status, data_type="CATEGORICAL", metadata=details),
                ])
                print(f"{name}: {score:.4f} / threshold {threshold:.2f} -> {status}")
    except Exception as exc:
        # Setup, execution or cleanup failure: retain any completed metric results.
        error = f"{type(exc).__name__}: {exc}"
        for name in METRIC_NAMES:
            if name not in statuses:
                record_error(name, error)
        evaluations.append(Evaluation(name="evaluation_error", value="ERROR",
                                      data_type="CATEGORICAL", comment=error))
        statuses["evaluation_error"] = "ERROR"

    item_status = ("ERROR" if "ERROR" in statuses.values()
                   else "PASS" if all(statuses.get(name) == "PASS" for name in METRIC_NAMES)
                   else "FAIL")
    evaluations.append(Evaluation(name="item_status", value=item_status,
                                  data_type="CATEGORICAL", metadata=score_metadata))
    print(f"Item status: {item_status}")
    return evaluations


def summarize_run(item_results, scheduled_count):
    """All scheduled cases remain in the denominator, including missing results."""
    item_counts = {"PASS": 0, "FAIL": 0, "ERROR": max(0, scheduled_count - len(item_results))}
    metric_counts = {name: {"PASS": 0, "FAIL": 0, "ERROR": 0} for name in METRIC_NAMES}
    fully_scored = 0
    for item in item_results:
        scores = {evaluation.name: evaluation.value for evaluation in item.evaluations}
        status = scores.get("item_status", "ERROR")
        item_counts[status if status in item_counts else "ERROR"] += 1
        fully_scored += all(name in scores for name in METRIC_NAMES)
        for name in METRIC_NAMES:
            status = scores.get(f"{name}_status", "ERROR")
            metric_counts[name][status if status in ("PASS", "FAIL", "ERROR") else "ERROR"] += 1
    missing = max(0, scheduled_count - len(item_results))
    results = [Evaluation(name=f"items_{status.lower()}", value=count)
               for status, count in item_counts.items()]
    results.extend([
        Evaluation(name="items_scheduled", value=scheduled_count),
        Evaluation(name="items_fully_scored", value=fully_scored),
        Evaluation(name="item_pass_rate", value=item_counts["PASS"] / scheduled_count),
    ])
    for name, counts in metric_counts.items():
        counts["ERROR"] += missing
        results.extend(Evaluation(name=f"{name}_{status.lower()}_count", value=count)
                       for status, count in counts.items())
        results.append(Evaluation(name=f"{name}_pass_rate", value=counts["PASS"] / scheduled_count))
    print(f"Run summary ({scheduled_count} scheduled): {item_counts}")
    return results

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=30, choices=range(1, 31), metavar="1-30",
                        help="Maximum dataset items to run (default: 30)")
    args = parser.parse_args()
    validate_thresholds()
    try:
        dataset = langfuse.get_dataset(DATASET_NAME)
        if not dataset.items:
            raise ValueError(f"Dataset {DATASET_NAME!r} has no items")
        items = sorted(dataset.items, key=lambda item: (item.metadata or {}).get("local_id", item.id))[:args.limit]
        run_name = "ragas-baseline-v1-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        print(f"Experiment: {run_name}")
        print(f"Running {len(items)} items sequentially; up to {len(items) * 5} metric scores.")
        result = langfuse.run_experiment(
            name="RAGAS baseline v1",
            run_name=run_name,
            description="Financial MCP agent baseline with five RAGAS metrics per item",
            data=items,
            task=agent_task,
            evaluators=[ragas_scores],
            run_evaluators=[lambda *, item_results, **kwargs: summarize_run(item_results, len(items))],
            max_concurrency=1,
            metadata={"ragas_version": "0.4.3", "judge_model": "gpt-4.1-mini",
                      "embedding_model": "text-embedding-3-small", "item_count": str(len(items)), "threshold_version": THRESHOLD_VERSION, "thresholds": json.dumps(THRESHOLDS, sort_keys=True)},
        )
        print(f"Experiment completed: {result.run_name}")
        print(f"Langfuse experiment: {result.experiment_url}")
        fully_scored = sum(set(METRIC_NAMES).issubset({score.name for score in item.evaluations}) for item in result.item_results)
        print(f"Items with all five scores: {fully_scored}/{len(items)}")
        print("Inspect items missing scores for task/evaluator errors; rerunning repeats API usage.")
        return result
    finally:
        langfuse.flush()


if __name__ == "__main__":
    main()
