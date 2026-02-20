"""Tests for sort parameter on list tools that previously lacked it (issue #14).

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
from congress_mcp.tools.nominations import register_nomination_tools
from congress_mcp.tools.laws import register_law_tools
from congress_mcp.tools.committees import register_committee_tools
from congress_mcp.tools.committee_meetings import register_committee_meeting_tools
from congress_mcp.tools.committee_reports import register_committee_report_tools
from congress_mcp.tools.communications import register_communication_tools
from congress_mcp.tools.votes import register_vote_tools

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
    mcp = FastMCP(name="test-sort-params")
    register_nomination_tools(mcp, config)
    register_law_tools(mcp, config)
    register_committee_tools(mcp, config)
    register_committee_meeting_tools(mcp, config)
    register_committee_report_tools(mcp, config)
    register_communication_tools(mcp, config)
    register_vote_tools(mcp, config)
    async with Client(transport=mcp) as c:
        yield c


@needs_api_key
async def test_list_nominations_with_sort(client: Client):
    """list_nominations accepts sort parameter."""
    result = await client.call_tool(
        "list_nominations",
        {"congress": CONGRESS, "sort": "updateDate+desc", "limit": 3},
    )
    data = parse_result(result)
    assert data["pagination"]["count"] > 0


@needs_api_key
async def test_list_laws_with_sort(client: Client):
    """list_laws accepts sort parameter."""
    result = await client.call_tool(
        "list_laws",
        {"congress": CONGRESS, "sort": "updateDate+desc", "limit": 3},
    )
    data = parse_result(result)
    assert data["pagination"]["count"] > 0


@needs_api_key
async def test_list_laws_by_type_with_sort(client: Client):
    """list_laws_by_type accepts sort parameter."""
    result = await client.call_tool(
        "list_laws_by_type",
        {"congress": CONGRESS, "law_type": "pub", "sort": "updateDate+desc", "limit": 3},
    )
    data = parse_result(result)
    assert data["pagination"]["count"] > 0


@needs_api_key
async def test_list_committees_with_sort(client: Client):
    """list_committees accepts sort parameter."""
    result = await client.call_tool(
        "list_committees",
        {"sort": "updateDate+desc", "limit": 3},
    )
    data = parse_result(result)
    assert data["pagination"]["count"] > 0


@needs_api_key
async def test_list_committees_by_chamber_with_sort(client: Client):
    """list_committees_by_chamber accepts sort parameter."""
    result = await client.call_tool(
        "list_committees_by_chamber",
        {"chamber": "house", "sort": "updateDate+desc", "limit": 3},
    )
    data = parse_result(result)
    assert data["pagination"]["count"] > 0


@needs_api_key
async def test_list_committees_by_congress_with_sort(client: Client):
    """list_committees_by_congress accepts sort parameter."""
    result = await client.call_tool(
        "list_committees_by_congress",
        {"congress": CONGRESS, "chamber": "house", "sort": "updateDate+desc", "limit": 3},
    )
    data = parse_result(result)
    assert data["pagination"]["count"] > 0


@needs_api_key
async def test_list_committee_meetings_with_sort(client: Client):
    """list_committee_meetings accepts sort parameter."""
    result = await client.call_tool(
        "list_committee_meetings",
        {"congress": CONGRESS, "chamber": "house", "sort": "updateDate+desc", "limit": 3},
    )
    data = parse_result(result)
    assert data["pagination"]["count"] > 0


@needs_api_key
async def test_list_committee_reports_with_sort(client: Client):
    """list_committee_reports accepts sort parameter."""
    result = await client.call_tool(
        "list_committee_reports",
        {"congress": CONGRESS, "report_type": "hrpt", "sort": "updateDate+desc", "limit": 3},
    )
    data = parse_result(result)
    assert data["pagination"]["count"] > 0


@needs_api_key
async def test_list_house_communications_with_sort(client: Client):
    """list_house_communications accepts sort parameter."""
    result = await client.call_tool(
        "list_house_communications",
        {"congress": CONGRESS, "communication_type": "ec", "sort": "updateDate+desc", "limit": 3},
    )
    data = parse_result(result)
    assert data["pagination"]["count"] > 0


@needs_api_key
async def test_list_senate_communications_with_sort(client: Client):
    """list_senate_communications accepts sort parameter."""
    result = await client.call_tool(
        "list_senate_communications",
        {"congress": CONGRESS, "communication_type": "ec", "sort": "updateDate+desc", "limit": 3},
    )
    data = parse_result(result)
    assert data["pagination"]["count"] > 0


@needs_api_key
async def test_list_house_votes_with_sort(client: Client):
    """list_house_votes accepts sort parameter."""
    result = await client.call_tool(
        "list_house_votes",
        {"congress": CONGRESS, "session": 1, "sort": "updateDate+desc", "limit": 3},
    )
    data = parse_result(result)
    assert data["pagination"]["count"] > 0
