"""Simple financial MCP server with four tools."""

from mcp.server import MCPServer

from retrieval import retrieve
from get_exchange_rate import get_exchange_rate as fetch_exchange_rate
from financial_tools import (
    calculate_emi as compute_emi,
    convert_currency as compute_conversion,
)


server = MCPServer("financial_mcp")


@server.tool()
def search_financial_knowledge(question: str, top_k: int = 3) -> list[dict]:
    """Search Indian financial Q&A and return relevant documents with sources.

    Dataset answers are not independently verified or necessarily current.
    Lower cosine distance means a closer match, not guaranteed correctness.
    """
    return retrieve(question=question, top_k=top_k)


@server.tool()
def get_exchange_rate(base_currency: str, target_currency: str) -> dict:
    """Fetch a reference exchange rate for currency codes such as USD and INR.

    Returns target units per base unit and the rate date, not a live bank quote.
    """
    return fetch_exchange_rate(base_currency, target_currency)


@server.tool()
def calculate_emi(
    principal: float,
    annual_interest_rate: float,
    tenure_months: int,
) -> dict:
    """Calculate monthly EMI, total repayment and total interest.

    Annual interest is a percentage: 10 means 10%. Tenure is in months.
    Assumes fixed interest, monthly payments and no additional fees.
    """
    return compute_emi(principal, annual_interest_rate, tenure_months)


@server.tool()
def convert_currency(amount: float, exchange_rate: float) -> dict:
    """Convert using target units per source unit, excluding bank fees.

    Get the rate from the user or get_exchange_rate; this tool only calculates.
    """
    return compute_conversion(amount, exchange_rate)


if __name__ == "__main__":
    # Keep stdout for MCP messages; use stderr for any diagnostic logging.
    server.run(transport="stdio")
