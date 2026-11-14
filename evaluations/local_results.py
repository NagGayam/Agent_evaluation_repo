"""Save experiment evidence as portable JSON without additional API calls."""

from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]


def git_revision():
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                capture_output=True, text=True, check=True).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                                    capture_output=True, text=True, check=True).stdout.strip())
        return {"commit": commit, "working_tree_dirty": dirty}
    except (OSError, subprocess.CalledProcessError):
        return {"commit": None, "working_tree_dirty": None}


def _serialize(value):
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"Unsupported result value: {type(value).__name__}")


def save_results(result, scheduled_items, *, started_at, revision, thresholds,
                 threshold_version, dataset_name, output_dir):
    """Include missing SDK results as ERROR and retain the original evidence."""
    completed = {item.item.id: item for item in result.item_results}
    records = []
    counts = {status: 0 for status in ("PASS", "FAIL", "ERROR")}
    metric_counts = {name: dict.fromkeys(counts, 0) for name in thresholds}
    for source in scheduled_items:
        item = completed.get(source.id)
        evaluations = item.evaluations if item else []
        scores = {evaluation.name: evaluation for evaluation in evaluations}
        metrics = {}
        for name, threshold in thresholds.items():
            raw = scores.get(name)
            decision = scores.get(f"{name}_status")
            status = decision.value if decision and decision.value in counts else "ERROR"
            metric_counts[name][status] += 1
            metrics[name] = {
                "score": raw.value if raw else None,
                "threshold": threshold, "status": status,
                "passed": status == "PASS" if status != "ERROR" else None,
                "reason": (decision.comment if decision else None) or
                          (raw.comment if raw else None) or "Metric result missing",
            }
        statuses = [metric["status"] for metric in metrics.values()]
        status = "ERROR" if "ERROR" in statuses else "FAIL" if "FAIL" in statuses else "PASS"
        counts[status] += 1
        records.append({
            "dataset_item_id": source.id, "local_id": (source.metadata or {}).get("local_id"),
            "input": source.input, "expected_output": source.expected_output,
            "metadata": source.metadata or {},
            "output": item.output if item else {"execution_error": "No item result returned by experiment SDK"},
            "trace_id": item.trace_id if item else None,
            "item_status": status, "metrics": metrics,
        })
    total = len(scheduled_items)
    # Hash the actual selected hosted items, not a potentially different local file.
    snapshot = [{"id": item.id, "input": item.input,
                 "expected_output": item.expected_output, "metadata": item.metadata}
                for item in scheduled_items]
    dataset_hash = hashlib.sha256(json.dumps(snapshot, sort_keys=True, ensure_ascii=False,
                                            default=_serialize).encode("utf-8")).hexdigest()
    payload = {
        "schema_version": 1, "suite": "deepeval", "run_name": result.run_name,
        "started_at": started_at, "finished_at": datetime.now(timezone.utc).isoformat(),
        "code": revision,
        "configuration": {
            "agent_model": "gpt-4.1-mini", "agent_temperature": 0,
            "judge_model": "gpt-4.1-mini", "threshold_version": threshold_version,
            "thresholds": thresholds, "max_concurrency": 1,
            "packages": {name: version(name) for name in ("deepeval", "langfuse", "langchain", "langchain-openai")},
        },
        "dataset": {"name": dataset_name, "selected_item_count": total,
                    "selected_items_sha256": dataset_hash,
                    "versions": sorted({str((item.metadata or {}).get("dataset_version", "unknown"))
                                        for item in scheduled_items})},
        "langfuse": {"experiment_id": result.experiment_id, "experiment_url": result.experiment_url},
        "summary": {"scheduled": total, "returned": len(result.item_results),
                    "items": {**counts, "pass_rate": counts["PASS"] / total},
                    "metrics": {name: {**values, "pass_rate": values["PASS"] / total}
                                for name, values in metric_counts.items()}},
        "items": records,
    }
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / f"{result.run_name}.json"
    # Exclusive creation prevents accidentally replacing a previous baseline.
    content = json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False, default=_serialize)
    with destination.open("x", encoding="utf-8") as handle:
        handle.write(content + "\n")
    return destination
