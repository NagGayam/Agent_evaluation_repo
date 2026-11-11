# Financial MCP Agent

A small Indian-finance RAG and tool-use project for AI evaluation practice.
The selected FABRIC content is not independently verified financial advice.

## Project layout

```text
ingestion/                 Dataset inspection and Chroma ingestion
agent/                     MCP client, MCP server and retrieval
  tools/                   EMI, currency conversion and exchange-rate functions
evaluations/
  datasets/                Future evaluation question sets
  ragas_eval/              Future RAGAS evaluators and experiment runner
data/                      Selected FABRIC records and selection manifest
reports/                   Dataset inspection and selection reports
interview_questions/       Learning notes
settings.py                Shared configuration and root-relative storage paths
```

`.env`, `.venv/`, `chroma_db/` and Python caches are Git-ignored. Existing
Chroma data stays at the project root; this reorganization does not re-ingest it.

## Run from the project root

Use your activated Python environment and install the dependencies:

```powershell
python -m pip install -r requirements.txt
```

Keep credentials in the root `.env`. Configure local Chroma with:

```dotenv
CHROMA_PERSIST_DIRECTORY=chroma_db
CHROMA_COLLECTION_NAME=fabric_qa_small_v1
```

The client uses `OPENAI_API_KEY` and your existing Langfuse configuration.

```powershell
# Inspection (refuses to overwrite an existing report unless --overwrite is used)
python -m ingestion.inspect_dataset

# Validate ingestion input without embedding API calls or Chroma writes
python -m ingestion.ingest --dry-run

# Embed and upsert the selected records (uses the OpenAI API)
python -m ingestion.ingest

# Retrieve stored documents (uses the OpenAI embeddings API)
python -m agent.retrieval "How much of my bank deposit is insured?"

# Run the agent; it launches its MCP server automatically
python -m agent.client
```

For a standalone stdio server, use `python -m agent.mcp_server`. It waits for
an MCP client, rather than accepting ordinary terminal questions. Run package
modules with `-m`; do not execute the nested Python file paths directly.

The demonstration question is currently set in `agent/client.py`. Langfuse
captures the outer run and client-side model/tool calls. Internal server tracing
and evaluation implementations are future work.

Import reusable functions using their package paths:

```python
from agent.retrieval import retrieve
from agent.tools.financial_tools import calculate_emi, convert_currency
from agent.tools.exchange_rates import get_exchange_rate
```
