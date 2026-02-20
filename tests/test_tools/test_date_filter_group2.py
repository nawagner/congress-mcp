"""Tests for Group 2 tools — validates date filtering (from_date/to_date only, no sort).

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
from congress_mcp.tools.committees import register_committee_tools
from congress_mcp.tools.committee_meetings import register_committee_meeting_tools
from congress_mcp.tools.committee_prints import register_committee_print_tools
from congress_mcp.tools.committee_reports import register_committee_report_tools
from congress_mcp.tools.crs_reports import register_crs_report_tools
from congress_mcp.tools.laws import register_law_tools
from congress_mcp.tools.nominations import register_nomination_tools

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


# --- Committees ---

@pytest.fixture
async def committee_client():
    config = Config.from_env()
    mcp = FastMCP(name="test-committees")
    register_committee_tools(mcp, config)
    async with Client(transport=mcp) as c:
        yield c


@needs_api_key
async def test_list_committees_with_date_filter(committee_client: Client):
    """list_committees returns results with date range."""
    result = await committee_client.call_tool(
        "list_committees",
        {"from_date": "2023-01-01", "to_date": "2024-12-31", "limit": 3},
    )
    data = parse_result(result)
    assert data["pagination"]["count"] > 0


@needs_api_key
async def test_list_committees_by_chamber_with_date_filter(committee_client: Client):
    """list_committees_by_chamber returns results with date range."""
    result = await committee_client.call_tool(
        "list_committees_by_chamber",
        {"chamber": "house", "from_date": "2023-01-01", "to_date": "2024-12-31", "limit": 3},
    )
    data = parse_result(result)
    assert data["pagination"]["count"] > 0


@needs_api_key
async def test_list_committees_by_congress_with_date_filter(committee_client: Client):
    """list_committees_by_congress accepts date params without error."""
    result = await committee_client.call_tool(
        "list_committees_by_congress",
        {"congress": CONGRESS, "chamber": "house", "from_date": "2023-01-01", "to_date": "2024-12-31", "limit": 3},
    )
    data = parse_result(result)
    assert "pagination" in data


@needs_api_key
async def test_get_committee_bills_with_date_filter(committee_client: Client):
    """get_committee_bills returns results with date range."""
    result = await committee_client.call_tool(
        "get_committee_bills",
        {
            "chamber": "house",
            "committee_code": "hsju00",
            "from_date": "2023-01-01",
            "to_date": "2024-12-31",
            "limit": 3,
        },
    )
    data = parse_result(result)
    assert data["pagination"]["count"] > 0


@needs_api_key
async def test_get_committee_reports_list_with_date_filter(committee_client: Client):
    """get_committee_reports_list returns results with date range."""
    result = await committee_client.call_tool(
        "get_committee_reports_list",
        {
            "chamber": "house",
            "committee_code": "hsju00",
            "from_date": "2023-01-01",
            "to_date": "2024-12-31",
            "limit": 3,
        },
    )
    data = parse_result(result)
    # Some committees may not have reports in the range, just check no error
    assert "pagination" in data


# --- Nominations ---

@pytest.fixture
async def nomination_client():
    config = Config.from_env()
    mcp = FastMCP(name="test-nominations")
    register_nomination_tools(mcp, config)
    async with Client(transport=mcp) as c:
        yield c


@needs_api_key
async def test_list_nominations_with_date_filter(nomination_client: Client):
    """list_nominations returns results with date range."""
    result = await nomination_client.call_tool(
        "list_nominations",
        {"congress": CONGRESS, "from_date": "2023-01-01", "to_date": "2024-12-31", "limit": 3},
    )
    data = parse_result(result)
    assert data["pagination"]["count"] > 0


# --- Laws ---

@pytest.fixture
async def law_client():
    config = Config.from_env()
    mcp = FastMCP(name="test-laws")
    register_law_tools(mcp, config)
    async with Client(transport=mcp) as c:
        yield c


@needs_api_key
async def test_list_laws_with_date_filter(law_client: Client):
    """list_laws returns results with date range."""
    result = await law_client.call_tool(
        "list_laws",
        {"congress": CONGRESS, "from_date": "2023-01-01", "to_date": "2024-12-31", "limit": 3},
    )
    data = parse_result(result)
    assert data["pagination"]["count"] > 0


@needs_api_key
async def test_list_laws_by_type_with_date_filter(law_client: Client):
    """list_laws_by_type returns results with date range."""
    result = await law_client.call_tool(
        "list_laws_by_type",
        {
            "congress": CONGRESS,
            "law_type": "pub",
            "from_date": "2023-01-01",
            "to_date": "2024-12-31",
            "limit": 3,
        },
    )
    data = parse_result(result)
    assert data["pagination"]["count"] > 0


# --- Committee Reports ---

@pytest.fixture
async def report_client():
    config = Config.from_env()
    mcp = FastMCP(name="test-reports")
    register_committee_report_tools(mcp, config)
    async with Client(transport=mcp) as c:
        yield c


@needs_api_key
async def test_list_committee_reports_with_date_filter(report_client: Client):
    """list_committee_reports accepts date params without error."""
    result = await report_client.call_tool(
        "list_committee_reports",
        {"congress": CONGRESS, "report_type": "hrpt", "from_date": "2023-01-01", "to_date": "2024-12-31", "limit": 3},
    )
    data = parse_result(result)
    assert "pagination" in data


# --- Committee Prints ---

@pytest.fixture
async def print_client():
    config = Config.from_env()
    mcp = FastMCP(name="test-prints")
    register_committee_print_tools(mcp, config)
    async with Client(transport=mcp) as c:
        yield c


@needs_api_key
async def test_list_committee_prints_with_date_filter(print_client: Client):
    """list_committee_prints returns results with date range."""
    result = await print_client.call_tool(
        "list_committee_prints",
        {"congress": CONGRESS, "chamber": "house", "from_date": "2023-01-01", "to_date": "2024-12-31", "limit": 3},
    )
    data = parse_result(result)
    assert data["pagination"]["count"] > 0


# --- Committee Meetings ---

@pytest.fixture
async def meeting_client():
    config = Config.from_env()
    mcp = FastMCP(name="test-meetings")
    register_committee_meeting_tools(mcp, config)
    async with Client(transport=mcp) as c:
        yield c


@needs_api_key
async def test_list_committee_meetings_with_date_filter(meeting_client: Client):
    """list_committee_meetings returns results with date range."""
    result = await meeting_client.call_tool(
        "list_committee_meetings",
        {"congress": CONGRESS, "chamber": "house", "from_date": "2023-01-01", "to_date": "2024-12-31", "limit": 3},
    )
    data = parse_result(result)
    assert data["pagination"]["count"] > 0


# --- CRS Reports ---

@pytest.fixture
async def crs_client():
    config = Config.from_env()
    mcp = FastMCP(name="test-crs")
    register_crs_report_tools(mcp, config)
    async with Client(transport=mcp) as c:
        yield c


@needs_api_key
async def test_list_crs_reports_with_date_filter(crs_client: Client):
    """list_crs_reports accepts date params without error."""
    result = await crs_client.call_tool(
        "list_crs_reports",
        {"from_date": "2024-01-01", "to_date": "2024-12-31", "limit": 3},
    )
    data = parse_result(result)
    assert "pagination" in data
