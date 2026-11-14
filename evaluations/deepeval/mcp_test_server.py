"""Evaluation-only MCP server with controlled exchange-rate responses.

Fixture data comes from the runner, never from the user's prompt. Unknown rate
calls fail closed instead of falling back to a live API. Production is unchanged.
"""

import json
import os

from agent import mcp_server


fixtures = json.loads(os.environ["FINANCIAL_EVAL_FIXTURES"])
if not isinstance(fixtures, list) or not fixtures:
    raise ValueError("A nonempty exchange-rate fixture list is required")


def fixture_exchange_rate(base_currency: str, target_currency: str) -> dict:
    arguments = {"base_currency": base_currency.strip().upper(),
                 "target_currency": target_currency.strip().upper()}
    for fixture in fixtures:
        if fixture["tool_name"] != "get_exchange_rate" or fixture["input_parameters"] != arguments:
            continue
        if fixture["behavior"] == "return":
            return fixture["output"]
        if fixture["behavior"] == "raise":
            exception = {"RuntimeError": RuntimeError, "ValueError": ValueError}[fixture["exception_type"]]
            raise exception(fixture["message"])
        raise ValueError("Unknown fixture behavior")
    raise ValueError(f"No configured rate fixture for {arguments}")


# The registered tool resolves this module-level function when invoked.
mcp_server.fetch_exchange_rate = fixture_exchange_rate

if __name__ == "__main__":
    mcp_server.server.run(transport="stdio")
