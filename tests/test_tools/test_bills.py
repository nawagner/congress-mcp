"""Tests for bill tools: date filtering and sort on list_bills / list_bills_by_type.

Live tests hit the Congress.gov API via FastMCP's Client transport and
require the CONGRESS_API_KEY environment variable (set in env or .env file).

Offline tests only inspect tool schemas and argument validation, so they use
a placeholder API key and never need network access to pass.

Sort contract (issue #26): both bill list tools accept exactly these client
facing ``sort`` values, or null / omitted:

    updateDate+asc, updateDate+desc, introducedDate+asc, introducedDate+desc

The ordering tests prove the API really applies the requested order. List
items are enriched with the bill detail response, so the checked
``introducedDate`` / ``updateDate`` values are the detail values. Only the
date part (first 10 characters) is compared, because the list level reports
dates while the detail level reports RFC 3339 timestamps.
"""

import json
import os
from pathlib import Path
from typing import Any

import pytest
from fastmcp import FastMCP
from fastmcp.client import Client
from fastmcp.exceptions import ToolError

from congress_mcp.config import Config
from congress_mcp.tools.bills import register_bill_tools

# Load .env file if present
_env_path = Path(__file__).parent.parent.parent / ".env"
if _env_path.exists():
    for line in _env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

CONGRESS = 118

BILL_LIST_TOOLS = ["list_bills", "list_bills_by_type"]

EXPECTED_SORT_VALUES = {
    "updateDate+asc",
    "updateDate+desc",
    "introducedDate+asc",
    "introducedDate+desc",
}

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
    mcp = FastMCP(name="test-bills")
    register_bill_tools(mcp, config)
    async with Client(transport=mcp) as c:
        yield c


@pytest.fixture
async def offline_client():
    """Client for schema and validation checks; never needs a real API key."""
    config = Config(api_key="offline-placeholder-key")
    mcp = FastMCP(name="test-bills-offline")
    register_bill_tools(mcp, config)
    async with Client(transport=mcp) as c:
        yield c


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_tool(client: Client, name: str):
    tools = {tool.name: tool for tool in await client.list_tools()}
    assert name in tools, f"tool {name!r} is not registered"
    return tools[name]


def _resolve_ref(node: dict[str, Any], root: dict[str, Any]) -> dict[str, Any]:
    """Follow a local JSON schema $ref (e.g. '#/$defs/Foo') if present."""
    ref = node.get("$ref")
    if isinstance(ref, str) and ref.startswith("#/"):
        target: Any = root
        for part in ref[2:].split("/"):
            target = target[part]
        return _resolve_ref(target, root)
    return node


def _leaf_schemas(node: dict[str, Any], root: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten anyOf / oneOf branches into their leaf schemas."""
    node = _resolve_ref(node, root)
    branches = node.get("anyOf") or node.get("oneOf")
    if branches:
        leaves: list[dict[str, Any]] = []
        for branch in branches:
            leaves.extend(_leaf_schemas(branch, root))
        return leaves
    return [node]


def _is_null_schema(leaf: dict[str, Any]) -> bool:
    type_ = leaf.get("type")
    return type_ == "null" or (isinstance(type_, list) and "null" in type_)


def _sort_schema_summary(input_schema: dict[str, Any]) -> tuple[list[Any], bool, list[dict]]:
    """Return (enum values, allows null, free-form non-null leaves) for 'sort'."""
    prop = input_schema["properties"]["sort"]
    values: list[Any] = []
    allows_null = False
    free_form: list[dict] = []
    for leaf in _leaf_schemas(prop, input_schema):
        if _is_null_schema(leaf):
            allows_null = True
        if "enum" in leaf:
            for value in leaf["enum"]:
                if value is None:
                    allows_null = True
                else:
                    values.append(value)
        elif "const" in leaf:
            if leaf["const"] is None:
                allows_null = True
            else:
                values.append(leaf["const"])
        elif not _is_null_schema(leaf):
            free_form.append(leaf)
    return values, allows_null, free_form


async def _list_bills(client: Client, tool: str, sort: str, limit: int) -> list[dict[str, Any]]:
    """Call a bill list tool for CONGRESS and return the bills, asserting a full page."""
    args: dict[str, Any] = {"congress": CONGRESS, "sort": sort, "limit": limit}
    if tool == "list_bills_by_type":
        args["bill_type"] = "hr"
    result = await client.call_tool(tool, args)
    data = parse_result(result)
    assert data["pagination"]["count"] > limit, data.get("pagination")
    bills = data["bills"]
    # A full page guarantees the ordering assertions below are never vacuous.
    assert len(bills) == limit, f"expected {limit} bills, got {len(bills)}"
    return bills


def _bill_id(bill: dict[str, Any]) -> tuple[str, str]:
    return (str(bill.get("type", "")).lower(), str(bill.get("number", "")))


def _dates(bills: list[dict[str, Any]], field: str) -> list[str]:
    """Extract the YYYY-MM-DD part of *field* for every bill; none may be missing."""
    dates = []
    for bill in bills:
        value = bill.get(field)
        assert isinstance(value, str) and len(value) >= 10, (
            f"bill {_bill_id(bill)} has no usable {field}: {value!r}"
        )
        dates.append(value[:10])
    return dates


def _assert_non_increasing(dates: list[str], label: str) -> None:
    assert dates == sorted(dates, reverse=True), f"{label} not non-increasing: {dates}"


def _assert_non_decreasing(dates: list[str], label: str) -> None:
    assert dates == sorted(dates), f"{label} not non-decreasing: {dates}"


# ---------------------------------------------------------------------------
# Offline: schema and argument validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("tool_name", BILL_LIST_TOOLS)
async def test_sort_schema_is_enum_of_four_values(offline_client: Client, tool_name: str):
    """sort exposes exactly the four update/introduced date values and stays optional."""
    tool = await _get_tool(offline_client, tool_name)
    schema = tool.inputSchema
    assert "sort" in schema["properties"], f"{tool_name} has no sort parameter"

    values, allows_null, free_form = _sort_schema_summary(schema)

    assert not free_form, (
        f"{tool_name}.sort must be an enum, but its schema also allows free-form "
        f"values: {free_form}"
    )
    assert len(values) == len(set(values)), f"duplicate sort values: {values}"
    assert set(values) == EXPECTED_SORT_VALUES, (
        f"{tool_name}.sort enum is {sorted(values)}, expected {sorted(EXPECTED_SORT_VALUES)}"
    )
    assert "sort" not in schema.get("required", []), f"{tool_name}.sort must be optional"
    assert allows_null, f"{tool_name}.sort must accept null"


@pytest.mark.parametrize("tool_name", BILL_LIST_TOOLS)
async def test_sort_rejects_unknown_value(offline_client: Client, tool_name: str):
    """An unsupported sort value is rejected by argument validation, before any API call."""
    args: dict[str, Any] = {"congress": CONGRESS, "sort": "title+asc", "limit": 1}
    if tool_name == "list_bills_by_type":
        args["bill_type"] = "hr"

    with pytest.raises(ToolError) as exc_info:
        await offline_client.call_tool(tool_name, args)

    message = str(exc_info.value)
    # The error must come from validating the sort argument (it names the
    # parameter and lists the allowed values), not from the network or API.
    assert "403" not in message and "Forbidden" not in message, (
        f"expected a sort validation error, got a network/API error: {message}"
    )
    assert "sort" in message, f"error does not name the sort parameter: {message}"
    assert "introducedDate" in message, f"error does not list the allowed sort values: {message}"


@pytest.mark.parametrize("tool_name", BILL_LIST_TOOLS)
async def test_descriptions_distinguish_update_and_introduced_dates(
    offline_client: Client, tool_name: str
):
    """Docs say from/to_date filter on update date and point recent-introduction queries
    at introducedDate+desc."""
    tool = await _get_tool(offline_client, tool_name)
    props = tool.inputSchema["properties"]

    for date_param in ("from_date", "to_date"):
        description = (props[date_param].get("description") or "").lower()
        assert "update" in description, (
            f"{tool_name}.{date_param} description must say it filters by update date: "
            f"{description!r}"
        )

    sort_description = props["sort"].get("description") or ""
    assert "introduceddate" in sort_description.lower(), (
        f"{tool_name}.sort description must mention introducedDate: {sort_description!r}"
    )
    assert "updatedate" in sort_description.lower(), (
        f"{tool_name}.sort description must still mention updateDate: {sort_description!r}"
    )

    guidance = f"{tool.description or ''}\n{sort_description}".lower()
    assert "recent" in guidance and "introduceddate+desc" in guidance, (
        f"{tool_name} docstring or sort description must tell clients to use "
        f"introducedDate+desc for recently introduced bills"
    )


# ---------------------------------------------------------------------------
# Live: date filter
# ---------------------------------------------------------------------------


@needs_api_key
async def test_list_bills_by_type_with_date_filter(client: Client):
    """list_bills_by_type returns results with date range."""
    result = await client.call_tool(
        "list_bills_by_type",
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
    assert len(data["bills"]) > 0


# ---------------------------------------------------------------------------
# Live: update date sort
# ---------------------------------------------------------------------------


@needs_api_key
async def test_list_bills_by_type_with_sort(client: Client):
    """updateDate+desc returns bills with non-increasing update dates."""
    bills = await _list_bills(client, "list_bills_by_type", "updateDate+desc", limit=5)
    _assert_non_increasing(_dates(bills, "updateDate"), "updateDate (updateDate+desc)")


@needs_api_key
async def test_list_bills_by_type_sort_update_date_asc(client: Client):
    """updateDate+asc returns bills with non-decreasing update dates."""
    bills = await _list_bills(client, "list_bills_by_type", "updateDate+asc", limit=5)
    _assert_non_decreasing(_dates(bills, "updateDate"), "updateDate (updateDate+asc)")


@needs_api_key
async def test_list_bills_by_type_update_date_sort_direction_is_applied(client: Client):
    """asc and desc update-date sorts return opposite ends of the collection.

    If the API ignored the sort, both calls would return the same default
    order and this test would fail.
    """
    asc = await _list_bills(client, "list_bills_by_type", "updateDate+asc", limit=5)
    desc = await _list_bills(client, "list_bills_by_type", "updateDate+desc", limit=5)

    asc_dates = _dates(asc, "updateDate")
    desc_dates = _dates(desc, "updateDate")
    _assert_non_decreasing(asc_dates, "updateDate (updateDate+asc)")
    _assert_non_increasing(desc_dates, "updateDate (updateDate+desc)")

    assert _bill_id(asc[0]) != _bill_id(desc[0]), (
        f"asc and desc returned the same first bill {_bill_id(asc[0])}; sort was ignored"
    )
    assert max(asc_dates) <= min(desc_dates), (
        f"oldest-updated page {asc_dates} overlaps newest-updated page {desc_dates}"
    )


# ---------------------------------------------------------------------------
# Live: introduced date sort
# ---------------------------------------------------------------------------


@needs_api_key
async def test_list_bills_by_type_sort_introduced_date_desc(client: Client):
    """introducedDate+desc returns bills with non-increasing introduced dates."""
    bills = await _list_bills(client, "list_bills_by_type", "introducedDate+desc", limit=5)
    _assert_non_increasing(_dates(bills, "introducedDate"), "introducedDate (introducedDate+desc)")


@needs_api_key
async def test_list_bills_by_type_sort_introduced_date_asc(client: Client):
    """introducedDate+asc returns bills with non-decreasing introduced dates."""
    bills = await _list_bills(client, "list_bills_by_type", "introducedDate+asc", limit=5)
    _assert_non_decreasing(_dates(bills, "introducedDate"), "introducedDate (introducedDate+asc)")


@needs_api_key
@pytest.mark.parametrize("tool_name", BILL_LIST_TOOLS)
async def test_introduced_date_sort_direction_is_applied(client: Client, tool_name: str):
    """asc returns the earliest-introduced bills and desc the latest ones.

    Earliest and latest introductions in a Congress are on different days, so
    the first asc date must be strictly earlier than the first desc date. If
    the API ignored the sort, both calls would return the same default order
    and this test would fail.
    """
    asc = await _list_bills(client, tool_name, "introducedDate+asc", limit=5)
    desc = await _list_bills(client, tool_name, "introducedDate+desc", limit=5)

    asc_dates = _dates(asc, "introducedDate")
    desc_dates = _dates(desc, "introducedDate")
    _assert_non_decreasing(asc_dates, f"{tool_name} introducedDate (introducedDate+asc)")
    _assert_non_increasing(desc_dates, f"{tool_name} introducedDate (introducedDate+desc)")

    assert asc_dates[0] < desc_dates[0], (
        f"{tool_name}: first asc date {asc_dates[0]} is not earlier than first desc "
        f"date {desc_dates[0]}; sort was ignored"
    )
    assert max(asc_dates) <= min(desc_dates), (
        f"{tool_name}: earliest page {asc_dates} overlaps latest page {desc_dates}"
    )
