"""Promptfoo Python provider for our financial MCP agent.

Promptfoo awaits call_api(). Its prompt is passed unchanged to run_agent().
The answer is the output; tool execution evidence is returned as metadata.
This adapter is single-turn. Selected tests use a controlled MCP test server.
"""

import logging
from pathlib import Path
import sys


# Promptfoo loads this file by path, so make project imports independent of cwd.
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent.client import run_agent, langfuse


async def call_api(prompt: str, options: dict, context: dict) -> dict:
    """Run the agent once and return Promptfoo's output/error response format.

    context.vars can select a named test fixture; options is currently unused.
    Tool-level failures remain evidence for assertions to inspect. A failure of
    the agent itself is a provider error, never a successful refusal response.
    """
    if not isinstance(prompt, str) or not prompt.strip():
        return {"error": "Agent input must be a nonblank string"}

    try:
        fixture_case = (context.get("vars") or {}).get("fixture_case")
        server_config = None
        if fixture_case:
            if fixture_case not in {"rate_injection", "document_injection", "rate_failure"}:
                raise ValueError("Unknown Promptfoo fixture case")
            server_config = {"mcpServers": {"financial": {
                "command": sys.executable,
                "args": ["-m", "evaluations.promptfoo.mcp_test_server"],
                "cwd": str(ROOT),
                "env": {"PROMPTFOO_FIXTURE_CASE": fixture_case},
            }}}
        result = await run_agent(prompt, server_config=server_config)
        answer = result["response"]
        if not isinstance(answer, str) or not answer.strip():
            raise ValueError("Agent returned an empty or non-text answer")

        return {
            "output": answer,
            "metadata": {
                "trace_id": result["trace_id"],
                "tool_calls": result["tool_calls"],
                "tool_results": result["tool_results"],
                "tool_errors": result["tool_errors"],
                "retrieved_context_ids": result["retrieved_context_ids"],
                "retrieved_contexts": result["retrieved_contexts"],
                "fixture_case": fixture_case,
            },
        }
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}
    finally:
        try:
            langfuse.flush()
        except Exception:
            # Logging goes to stderr, leaving the provider response intact.
            logging.getLogger(__name__).warning("Could not flush Langfuse traces")
