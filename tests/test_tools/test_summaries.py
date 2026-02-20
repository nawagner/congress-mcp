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
from congress_mcp.tools.summaries import _strip_html, register_summary_tools

# Load .env file if present
_env_path = Path(__file__).parent.parent.parent / ".env"
if _env_path.exists():
    for line in _env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

CONGRESS = 118
CURRENT_CONGRESS = 119

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
async def test_list_summaries_without_dates_returns_recent(client: Client):
    """Summaries endpoint returns a small window of recent results without dates."""
    result = await client.call_tool("list_summaries", {"limit": 1})
    data = parse_result(result)
    assert data["pagination"]["count"] > 0


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
async def test_list_summaries_by_congress_without_dates_past_congress(client: Client):
    """Past congress returns 0 summaries without date filters."""
    result = await client.call_tool(
        "list_summaries_by_congress",
        {"congress": CONGRESS, "limit": 1},
    )
    data = parse_result(result)
    assert data["pagination"]["count"] == 0


@needs_api_key
async def test_list_summaries_by_congress_without_dates_current_congress(client: Client):
    """Current congress returns results without date filters."""
    result = await client.call_tool(
        "list_summaries_by_congress",
        {"congress": CURRENT_CONGRESS, "limit": 1},
    )
    data = parse_result(result)
    assert data["pagination"]["count"] > 0


@needs_api_key
async def test_list_summaries_by_type_without_dates_current_congress(client: Client):
    """Current congress returns results by type without date filters."""
    result = await client.call_tool(
        "list_summaries_by_type",
        {"congress": CURRENT_CONGRESS, "bill_type": "hr", "limit": 1},
    )
    data = parse_result(result)
    assert data["pagination"]["count"] > 0


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


# --- _strip_html unit tests ---


def test_strip_html_removes_tags():
    assert _strip_html("<p>Hello <b>world</b></p>") == "Hello world"


def test_strip_html_decodes_entities():
    assert _strip_html("A &amp; B &lt; C") == "A & B < C"


def test_strip_html_handles_empty():
    assert _strip_html("") == ""


# --- search_summaries tests ---
# Use 118th Congress with date filters and bill_type="hr" for reliable results.
# The API only returns a small window without dates, so date filters are essential.


@needs_api_key
async def test_search_summaries_finds_matches(client: Client):
    """search_summaries returns matching summaries for AI-related keyword."""
    result = await client.call_tool(
        "search_summaries",
        {
            "congress": CONGRESS,
            "query": "artificial intelligence",
            "bill_type": "hr",
            "from_date": "2024-01-01",
            "to_date": "2024-12-31",
            "max_matches": 5,
        },
    )
    data = parse_result(result)
    assert data["match_count"] > 0
    assert len(data["matches"]) <= 5
    assert data["query"] == "artificial intelligence"
    assert data["total_summaries_searched"] > 0
    for match in data["matches"]:
        plain = _strip_html(match.get("text", ""))
        assert "artificial intelligence" in plain.lower()


@needs_api_key
async def test_search_summaries_no_matches(client: Client):
    """search_summaries returns empty results for a nonsense keyword.

    Uses current congress without dates (small result set) to avoid
    long pagination when no matches trigger early termination.
    """
    result = await client.call_tool(
        "search_summaries",
        {
            "congress": CURRENT_CONGRESS,
            "query": "xyzzyplugh42",
            "max_matches": 5,
        },
    )
    data = parse_result(result)
    assert data["match_count"] == 0
    assert data["matches"] == []
    assert data["total_summaries_searched"] > 0


@needs_api_key
async def test_search_summaries_case_insensitive(client: Client):
    """search_summaries is case-insensitive."""
    result = await client.call_tool(
        "search_summaries",
        {
            "congress": CONGRESS,
            "query": "ARTIFICIAL INTELLIGENCE",
            "bill_type": "hr",
            "from_date": "2024-01-01",
            "to_date": "2024-12-31",
            "max_matches": 3,
        },
    )
    data = parse_result(result)
    assert data["match_count"] > 0


@needs_api_key
async def test_search_summaries_without_bill_type(client: Client):
    """search_summaries works without bill_type filter (searches all types)."""
    result = await client.call_tool(
        "search_summaries",
        {
            "congress": CONGRESS,
            "query": "artificial intelligence",
            "from_date": "2024-01-01",
            "to_date": "2024-12-31",
            "max_matches": 3,
        },
    )
    data = parse_result(result)
    assert data["match_count"] > 0
    assert data["total_summaries_searched"] > 0


@needs_api_key
async def test_search_summaries_max_matches_respected(client: Client):
    """search_summaries respects max_matches limit."""
    result = await client.call_tool(
        "search_summaries",
        {
            "congress": CONGRESS,
            "query": "health",
            "bill_type": "hr",
            "from_date": "2024-01-01",
            "to_date": "2024-12-31",
            "max_matches": 2,
        },
    )
    data = parse_result(result)
    assert data["match_count"] <= 2


@needs_api_key
async def test_search_summaries_includes_bill_info(client: Client):
    """search_summaries results include bill identifiers for follow-up."""
    result = await client.call_tool(
        "search_summaries",
        {
            "congress": CONGRESS,
            "query": "artificial intelligence",
            "bill_type": "hr",
            "from_date": "2024-01-01",
            "to_date": "2024-12-31",
            "max_matches": 1,
        },
    )
    data = parse_result(result)
    assert data["match_count"] > 0
    match = data["matches"][0]
    assert "bill" in match
