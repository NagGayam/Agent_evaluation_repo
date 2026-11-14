"""Run DeepEval agent cases and log detailed decisions to Langfuse.

    python -m evaluations.deepeval.run_experiment --limit 1
    python -m evaluations.deepeval.run_experiment --limit 10

Makes paid agent and judge API calls. Fixture cases use an evaluation-only MCP
server. Each case executes the agent once, then both metrics score that execution.
"""

import argparse
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
import json
import math
import sys

from agent.settings import ROOT
from agent.client import run_agent
from deepeval.test_case import ToolCall
from langfuse import Evaluation, get_client

from evaluations.deepeval.evaluation import tool_correct_ness, task_completeness
from evaluations.local_results import git_revision, save_results


DATASET_NAME = "DeepEval_Data_set"
THRESHOLD_VERSION = "v1"
THRESHOLDS = {"tool_correctness": 1.0, "task_completeness": 0.8}
langfuse = get_client()


def validate_item(item):
    if not isinstance(item.input, str) or not item.input.strip():
        raise ValueError(f"{item.id}: input must be a nonblank string")
    expected = item.expected_output
    if not isinstance(expected, dict) or not isinstance(expected.get("expected_tools"), list):
        raise ValueError(f"{item.id}: expected_tools must be a list (possibly empty)")
    if not isinstance(expected.get("completion_requirements"), str) or not expected["completion_requirements"].strip():
        raise ValueError(f"{item.id}: missing completion requirements")
    for tool in expected["expected_tools"]:
        ToolCall(**tool)
    metadata = item.metadata or {}
    if metadata.get("tool_match_policy", "exact") != "exact":
        raise ValueError("This runner supports the exact tool-match policy only")
    if type(metadata.get("check_tool_order", False)) is not bool:
        raise ValueError("check_tool_order must be Boolean")
    mode = metadata.get("execution_mode", "normal")
    if mode not in ("normal", "fixture"):
        raise ValueError(f"Unsupported execution mode: {mode}")
    if mode == "fixture":
        fixtures = metadata.get("tool_fixtures")
        if not isinstance(fixtures, list) or not fixtures:
            raise ValueError("Fixture mode requires tool_fixtures")
        for fixture in fixtures:
            if fixture.get("tool_name") != "get_exchange_rate" or not isinstance(fixture.get("input_parameters"), dict):
                raise ValueError("Only explicit exchange-rate fixtures are supported")
            if fixture.get("behavior") == "return":
                if not isinstance(fixture.get("output"), dict):
                    raise ValueError("Return fixture requires an output dictionary")
            elif fixture.get("behavior") == "raise":
                if fixture.get("exception_type") not in ("ValueError", "RuntimeError") or not isinstance(fixture.get("message"), str):
                    raise ValueError("Invalid exception fixture")
            else:
                raise ValueError("Fixture behavior must be return or raise")


async def agent_task(*, item, **kwargs):
    metadata = item.metadata or {}
    label = metadata.get("local_id", item.id)
    print(f"\nCase {label}: {item.input}", flush=True)
    config = None
    if metadata.get("execution_mode") == "fixture":
        config = {"mcpServers": {"financial": {
            "command": sys.executable,
            "args": ["-m", "evaluations.deepeval.mcp_test_server"],
            "cwd": str(ROOT),
            "env": {"FINANCIAL_EVAL_FIXTURES": json.dumps(metadata["tool_fixtures"])},
        }}}
    try:
        output = await run_agent(item.input, server_config=config)
        print("Actual tools:", json.dumps(output["tool_calls"], ensure_ascii=False))
        print("Answer:", output["response"])
        # Keep fixture provenance visible without feeding it to the model prompt.
        output["execution_mode"] = metadata.get("execution_mode", "normal")
        return output
    except Exception as exc:
        return {"execution_error": f"{type(exc).__name__}: {exc}"}


async def evaluate_item(*, input, output, expected_output, metadata=None, **kwargs):
    metadata = metadata or {}
    evaluations = []
    statuses = {}
    details = {"threshold_version": THRESHOLD_VERSION,
               "reference_review_status": metadata.get("reference_review_status", "unknown"),
               "expected_tools": expected_output["expected_tools"],
               "completion_requirements": expected_output["completion_requirements"],
               "check_tool_order": metadata.get("check_tool_order", False)}

    for name, threshold in THRESHOLDS.items():
        score_metadata = {**details, "threshold": threshold}
        try:
            if output.get("execution_error"):
                raise ValueError(output["execution_error"])
            if name == "tool_correctness":
                actual = [ToolCall(name=call["name"], input_parameters=call["args"])
                          for call in output["tool_calls"]]
                result = await tool_correct_ness(
                    input, [ToolCall(**tool) for tool in expected_output["expected_tools"]],
                    agent_response={"agent_response": output["response"], "actual_tools": actual},
                    check_order=metadata.get("check_tool_order", False),
                )
            else:
                result = await task_completeness(
                    input, output["response"], expected_output["completion_requirements"],
                    tool_results={"calls": output["tool_calls"],
                                  "results": output.get("tool_results", []),
                                  "errors": output.get("tool_errors", [])},
                )
            score = float(result["Score"])
            if not math.isfinite(score) or not 0 <= score <= 1:
                raise ValueError(f"Invalid metric score: {score}")
            passed = score >= threshold
            status = "PASS" if passed else "FAIL"
            reason = result.get("Reason") or "No explanation returned by the metric"
            evaluations.extend([
                Evaluation(name=name, value=score, comment=reason, metadata=score_metadata),
                Evaluation(name=f"{name}_pass", value=passed, data_type="BOOLEAN",
                           comment=reason, metadata=score_metadata),
            ])
        except Exception as exc:
            status = "ERROR"
            reason = f"{type(exc).__name__}: {exc}"
        statuses[name] = status
        evaluations.append(Evaluation(name=f"{name}_status", value=status,
                                      data_type="CATEGORICAL", comment=reason, metadata=score_metadata))
        print(f"{name}: {status} — {reason}", flush=True)

    status = "ERROR" if "ERROR" in statuses.values() else "PASS" if all(s == "PASS" for s in statuses.values()) else "FAIL"
    evaluations.append(Evaluation(name="item_status", value=status, data_type="CATEGORICAL",
                                  metadata={"threshold_version": THRESHOLD_VERSION}))
    return evaluations


def summarize(item_results, scheduled_count):
    missing = max(0, scheduled_count - len(item_results))
    counts = {"PASS": 0, "FAIL": 0, "ERROR": missing}
    metric_counts = {name: {"PASS": 0, "FAIL": 0, "ERROR": missing} for name in THRESHOLDS}
    for item in item_results:
        scores = {score.name: score.value for score in item.evaluations}
        status = scores.get("item_status", "ERROR")
        counts[status if status in counts else "ERROR"] += 1
        for name in THRESHOLDS:
            status = scores.get(f"{name}_status", "ERROR")
            metric_counts[name][status if status in counts else "ERROR"] += 1
    results = [Evaluation(name=f"items_{status.lower()}", value=count) for status, count in counts.items()]
    results.extend([Evaluation(name="items_scheduled", value=scheduled_count),
                    Evaluation(name="item_pass_rate", value=counts["PASS"] / scheduled_count)])
    for name, values in metric_counts.items():
        results.extend(Evaluation(name=f"{name}_{status.lower()}_count", value=count)
                       for status, count in values.items())
        results.append(Evaluation(name=f"{name}_pass_rate", value=values["PASS"] / scheduled_count))
    print(f"\nSummary ({scheduled_count} scheduled): {counts}")
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, choices=range(1, 11), default=1, metavar="1-10")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "results" / "deepeval",
                        help="Directory for local JSON results (default: results/deepeval)")
    args = parser.parse_args()
    try:
        dataset = langfuse.get_dataset(DATASET_NAME)
        items = sorted(dataset.items, key=lambda item: (item.metadata or {}).get("local_id", item.id))[:args.limit]
        if not items:
            raise ValueError("DeepEval dataset is empty")
        for item in items:
            validate_item(item)
        run_name = "deepeval-agent-v1-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        started_at = datetime.now(timezone.utc).isoformat()
        revision = git_revision()
        result = langfuse.run_experiment(
            name="DeepEval agent baseline", run_name=run_name, data=items,
            description="Tool correctness and task-completeness G-Eval; draft test cases",
            task=agent_task, evaluators=[evaluate_item], max_concurrency=1,
            run_evaluators=[lambda *, item_results, **kwargs: summarize(item_results, len(items))],
            metadata={"deepeval_version": version("deepeval"), "judge_model": "gpt-4.1-mini",
                      "threshold_version": THRESHOLD_VERSION, "thresholds": json.dumps(THRESHOLDS),
                      "item_count": str(len(items)), "fixture_support": "exchange-rate-only-v1"},
        )
        print(f"Langfuse experiment: {result.experiment_url}")
        saved_path = save_results(
            result, items, started_at=started_at, revision=revision,
            thresholds=THRESHOLDS, threshold_version=THRESHOLD_VERSION,
            dataset_name=DATASET_NAME, output_dir=args.output_dir,
        )
        print(f"Local results: {saved_path}")
        return result
    finally:
        langfuse.flush()


if __name__ == "__main__":
    main()
