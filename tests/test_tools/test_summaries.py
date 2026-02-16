"""Tests for summary tools — validates date filtering and sort params.

These tests hit the live Congress.gov API via FastMCP's Client transport.
Requires CONGRESS_API_KEY environment variable (set in env or .env file).
"""

import json
import os
from pathlib import Path

import pytest
from fastmcp import FastMCP
from fastmcp.client import Client

from congress_mcp.config import Config
from congress_mcp.tools.summaries import register_summary_tools

# Load .env file if present
_env_path = Path(__file__).parent.parent.parent / ".env"
if _env_path.exists():
    for line in _env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

CONGRESS = 118

needs_api_key = pytest.mark.skipif(
    not os.environ.get("CONGRESS_API_KEY"),
    reason="CONGRESS_API_KEY not set",
)


def parse_result(result) -> dict:
    """Parse CallToolResult.data — handles both str and dict."""
    data = result.data
    return json.loads(data) if isinstance(data, str) else data


@pytest.fixture
async def client():
    config = Config.from_env()
    mcp = FastMCP(name="test-summaries")
    register_summary_tools(mcp, config)
    async with Client(transport=mcp) as c:
        yield c


@needs_api_key
async def test_list_summaries_without_dates_returns_empty(client: Client):
    """Summaries endpoint returns 0 results without date filtering."""
    result = await client.call_tool("list_summaries", {"limit": 1})
    data = parse_result(result)
    assert data["pagination"]["count"] == 0


@needs_api_key
async def test_list_summaries_with_date_filter(client: Client):
    """list_summaries returns results when date range is provided."""
    result = await client.call_tool(
        "list_summaries",
        {"from_date": "2024-01-01", "to_date": "2024-12-31", "limit": 3},
    )
    data = parse_result(result)
    assert data["pagination"]["count"] > 0
    assert len(data["summaries"]) > 0


@needs_api_key
async def test_list_summaries_by_congress_with_date_filter(client: Client):
    """list_summaries_by_congress returns results with date range."""
    result = await client.call_tool(
        "list_summaries_by_congress",
        {"congress": CONGRESS, "from_date": "2024-01-01", "to_date": "2024-12-31", "limit": 3},
    )
    data = parse_result(result)
    assert data["pagination"]["count"] > 0
    assert len(data["summaries"]) > 0


@needs_api_key
async def test_list_summaries_by_type_with_date_filter(client: Client):
    """list_summaries_by_type returns results with date range."""
    result = await client.call_tool(
        "list_summaries_by_type",
        {
            "congress": CONGRESS,
            "bill_type": "hr",
            "from_date": "2024-01-01",
            "to_date": "2024-12-31",
            "limit": 3,
        },
    )
    data = parse_result(result)
    assert data["pagination"]["count"] > 0
    assert len(data["summaries"]) > 0


@needs_api_key
async def test_list_summaries_with_sort(client: Client):
    """list_summaries accepts sort parameter."""
    result = await client.call_tool(
        "list_summaries",
        {
            "from_date": "2024-01-01",
            "to_date": "2024-12-31",
            "sort": "updateDate+desc",
            "limit": 3,
        },
    )
    data = parse_result(result)
    assert data["pagination"]["count"] > 0
    assert len(data["summaries"]) > 0
