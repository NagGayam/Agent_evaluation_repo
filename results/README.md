# Local evaluation results

DeepEval now saves each completed experiment to `results/deepeval/<run-name>.json`.
No scores have been generated or copied here yet.

```powershell
python -m evaluations.deepeval.run_experiment --limit 1
```

The same agent execution and metric judgments feed Langfuse and the local file;
saving does not make extra model requests. The runner still loads its dataset
from Langfuse, so local output storage does not make evaluation offline.

Each file includes UTC timestamps, Git revision/dirty state, package versions,
models, thresholds, selected dataset versions/content hash, experiment link,
questions, expected outcomes, actual outputs/tool evidence, scores, reasons,
per-item decisions, and summary counts. Pass rates use every scheduled item as
the denominator; missing results count as ERROR and have null scores/pass flags.

Files are created only after the experiment returns. Item failures are included;
an interrupted process or failure before the experiment returns does not produce
a report. Unique run names and exclusive creation preserve earlier baselines.

Review outputs and traces before committing them; include only suitable demo
data. RAGAS local export and Promptfoo export are separate follow-up work.
