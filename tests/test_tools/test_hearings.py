"""Tests for hearing tools — validates list_hearings with and without chamber.

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
from congress_mcp.tools.hearings import register_hearing_tools

# Load .env file if present (same pattern as test_integration_live.py)
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


@pytest.fixture
async def client():
    config = Config.from_env()
    mcp = FastMCP(name="test-hearings")
    register_hearing_tools(mcp, config)
    async with Client(transport=mcp) as c:
        yield c


@needs_api_key
async def test_list_hearings_without_chamber(client: Client):
    """list_hearings should work with only congress (no chamber)."""
    result = await client.call_tool(
        "list_hearings", {"congress": CONGRESS, "limit": 3}
    )
    data = json.loads(result.data)
    assert "hearings" in data
    assert len(data["hearings"]) > 0


@needs_api_key
async def test_list_hearings_with_chamber(client: Client):
    """list_hearings should still work when chamber is provided (backward compat)."""
    result = await client.call_tool(
        "list_hearings", {"congress": CONGRESS, "chamber": "house", "limit": 3}
    )
    data = json.loads(result.data)
    assert "hearings" in data
    assert len(data["hearings"]) > 0


@needs_api_key
async def test_list_hearings_with_senate_chamber(client: Client):
    """list_hearings should work with chamber='senate'."""
    result = await client.call_tool(
        "list_hearings", {"congress": CONGRESS, "chamber": "senate", "limit": 3}
    )
    data = json.loads(result.data)
    assert "hearings" in data
    assert len(data["hearings"]) > 0


@needs_api_key
async def test_list_hearings_without_chamber_enriches_details(client: Client):
    """When chamber is omitted, enrichment should still fetch hearing details."""
    result = await client.call_tool(
        "list_hearings", {"congress": CONGRESS, "limit": 2}
    )
    data = json.loads(result.data)
    hearings = data["hearings"]
    assert len(hearings) > 0
    first = hearings[0]
    assert "jacketNumber" in first
