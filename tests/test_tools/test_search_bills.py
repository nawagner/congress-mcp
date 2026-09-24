"""Tests for the search_bills tool (issue #27): title keyword and policy area search.

The Congress.gov API cannot filter bills by topic server-side, so search_bills
pages through ``/bill/{congress}[/{billType}]`` list results and filters on the
client, like ``search_summaries`` does for summary text. Title matching uses
list items only. Policy area matching needs one bill detail request
(``/bill/{congress}/{type}/{number}``) per candidate, because list items carry
no ``policyArea``.

Tool contract pinned by these tests
===================================

Registered by ``register_bill_tools`` as ``search_bills`` with read-only
annotations and a description that mentions title and policy area search.

Parameters (every parameter has a description; only ``congress`` is required):

- ``congress`` (int)
- ``query`` (str | None, default None): case-insensitive substring matched
  against the bill ``title``. An empty string is rejected.
- ``policy_area`` (str | None, default None): exact match on
  ``policyArea.name``. The JSON schema exposes a flat ``enum`` (no ``$ref``)
  of the 33 controlled Congress.gov policy area names, backed by
  ``PolicyAreaLiteral`` in ``congress_mcp.types.enums``. Other values are
  rejected by validation.
- ``bill_type`` (hr, s, hjres, sjres, hconres, sconres, hres, sres | None),
  ``from_date`` / ``to_date`` (YYYY-MM-DD | None): narrow the candidate list,
  same meaning as on ``list_bills_by_type``.
- ``max_matches`` (int, default 50, minimum 1).
- ``max_scan`` (int, minimum 1, finite maximum no greater than 5000, default
  between 25 and 500): cap on bill detail requests made for the policy area
  check. It does not limit title-only scanning.

At least one of ``query`` / ``policy_area`` is required. Otherwise a
``ToolError`` naming both parameters is raised before any API request. When
both are given, titles are filtered first and only title matches are
detail-fetched.

Response (a dict):

- ``matches``: list of bills satisfying every requested filter. Each has at
  least ``congress``, ``type``, ``number`` and ``title``. When
  ``policy_area`` was requested each match also has ``policyArea.name``.
- ``match_count``: ``len(matches)``, never more than ``max_matches``.
- ``total_candidates``: size of the candidate list the scan draws from (the
  list endpoint's ``pagination.count`` for the congress/bill_type/date window).
- ``bills_scanned``: candidate bills evaluated against every requested
  filter (a title mismatch counts as evaluated). Never more than
  ``total_candidates``.
- ``detail_fetches``: bill detail requests made for the policy area check,
  never more than ``max_scan``. Always 0 when ``policy_area`` is not given.
  Equal to ``bills_scanned`` when only ``policy_area`` is given.
- ``stop_reason``: why scanning stopped, one of

  - ``"max_matches"``: ``match_count == max_matches``;
  - ``"max_scan"``: the detail-fetch cap was hit, ``detail_fetches == max_scan``;
  - ``"exhausted"``: every candidate was evaluated,
    ``bills_scanned == total_candidates``.

- ``search_complete``: True exactly when ``stop_reason == "exhausted"``.
  Note this differs from ``search_summaries``: stopping at ``max_matches``
  is also reported as incomplete, since more matches may exist.
- ``query`` / ``policy_area``: echo of the arguments (None when omitted).
- ``_warnings`` (optional): list of strings naming bill detail endpoints whose
  fetch failed, following ``CongressClient.enrich_list_response``. Present
  only when a detail fetch failed. A failed fetch still counts toward
  ``detail_fetches`` and ``bills_scanned`` but never produces a match.

Offline tests (schema, validation) need no network. Live tests hit the
Congress.gov API through FastMCP's in-process Client transport and require
CONGRESS_API_KEY (from the environment or a .env file). No mocks, per
CLAUDE.md. Live tests assert non-empty results or a verified complete scan so
they cannot pass when the API is unreachable.
"""

import json
import os
from pathlib import Path
from typing import Any, get_args

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
TOOL = "search_bills"

# Bounded update-date window covering the whole 118th Congress and later
# record touch-ups. The API filters on a bill's *latest* updateDate, so a
# window limited to the session years can shrink over time as old bills are
# re-touched; this window keeps candidate counts in the thousands for "hr".
WINDOW = {"from_date": "2023-01-01", "to_date": "2026-06-30"}

# Controlled list from https://www.congress.gov/help/field-values/policy-area
POLICY_AREAS = frozenset(
    {
        "Agriculture and Food",
        "Animals",
        "Armed Forces and National Security",
        "Arts, Culture, Religion",
        "Civil Rights and Liberties, Minority Issues",
        "Commerce",
        "Congress",
        "Crime and Law Enforcement",
        "Economics and Public Finance",
        "Education",
        "Emergency Management",
        "Energy",
        "Environmental Protection",
        "Families",
        "Finance and Financial Sector",
        "Foreign Trade and International Finance",
        "Government Operations and Politics",
        "Health",
        "Housing and Community Development",
        "Immigration",
        "International Affairs",
        "Labor and Employment",
        "Law",
        "Native Americans",
        "Private Legislation",
        "Public Lands and Natural Resources",
        "Science, Technology, Communications",
        "Social Sciences and History",
        "Social Welfare",
        "Sports and Recreation",
        "Taxation",
        "Transportation and Public Works",
        "Water Resources Development",
    }
)

BILL_TYPES = frozenset({"hr", "s", "hjres", "sjres", "hconres", "sconres", "hres", "sres"})
STOP_REASONS = frozenset({"max_matches", "max_scan", "exhausted"})
EXPECTED_PARAMS = frozenset(
    {
        "congress",
        "query",
        "policy_area",
        "bill_type",
        "from_date",
        "to_date",
        "max_matches",
        "max_scan",
    }
)
DEFAULT_MAX_MATCHES = 50

needs_api_key = pytest.mark.skipif(
    not os.environ.get("CONGRESS_API_KEY"),
    reason="CONGRESS_API_KEY not set",
)


def parse_result(result) -> dict:
    """Parse CallToolResult.data, which may be a str or a dict."""
    data = result.data
    return json.loads(data) if isinstance(data, str) else data


@pytest.fixture
async def client():
    # Offline tests never reach the API, so a placeholder key lets them run
    # without CONGRESS_API_KEY. Live tests are skipped without a real key.
    if os.environ.get("CONGRESS_API_KEY"):
        config = Config.from_env()
    else:
        config = Config(api_key="offline-placeholder-key")
    mcp = FastMCP(name="test-search-bills")
    register_bill_tools(mcp, config)
    async with Client(transport=mcp) as c:
        yield c


# --- schema helpers ---


async def _get_tool(client: Client):
    tools = {tool.name: tool for tool in await client.list_tools()}
    assert TOOL in tools, f"{TOOL} is not registered by register_bill_tools"
    return tools[TOOL]


async def _props(client: Client) -> dict[str, Any]:
    tool = await _get_tool(client)
    return tool.inputSchema.get("properties", {})


def _variants(prop: dict[str, Any]) -> list[dict[str, Any]]:
    """Non-null variants of a property schema (unwraps anyOf / oneOf)."""
    for key in ("anyOf", "oneOf"):
        if key in prop:
            return [v for v in prop[key] if v.get("type") != "null"]
    return [prop]


def _enum_values(prop: dict[str, Any]) -> list[Any]:
    values: list[Any] = []
    for variant in _variants(prop):
        values.extend(variant.get("enum", []))
        if "const" in variant:
            values.append(variant["const"])
    return values


def _types(prop: dict[str, Any]) -> set[str]:
    return {v["type"] for v in _variants(prop) if "type" in v}


def _lower_bound(prop: dict[str, Any]) -> int | None:
    for variant in [prop, *_variants(prop)]:
        if "minimum" in variant:
            return variant["minimum"]
        if "exclusiveMinimum" in variant:
            return variant["exclusiveMinimum"] + 1
    return None


def _upper_bound(prop: dict[str, Any]) -> int | None:
    for variant in [prop, *_variants(prop)]:
        if "maximum" in variant:
            return variant["maximum"]
        if "exclusiveMaximum" in variant:
            return variant["exclusiveMaximum"] - 1
    return None


def _assert_not_network_error(message: str) -> None:
    """The error must come from validation, not from an API request."""
    lowered = message.lower()
    assert "403" not in lowered and "forbidden" not in lowered, message
    assert "unknown tool" not in lowered, message


# --- offline tests: registration and schema ---


async def test_search_bills_is_registered_and_documented(client: Client):
    """search_bills is registered, read-only, and documented."""
    tool = await _get_tool(client)
    assert tool.annotations is not None
    assert tool.annotations.readOnlyHint is True
    description = (tool.description or "").lower()
    assert "title" in description
    assert "policy area" in description


async def test_search_bills_schema_required_and_optional_params(client: Client):
    """Only congress is required; all filter and cap params are present."""
    tool = await _get_tool(client)
    schema = tool.inputSchema
    props = schema.get("properties", {})
    assert set(schema.get("required", [])) == {"congress"}
    missing = EXPECTED_PARAMS - set(props)
    assert not missing, f"missing parameters: {sorted(missing)}"
    for name, prop in props.items():
        assert prop.get("description"), f"parameter {name!r} has no description"
    assert "integer" in _types(props["congress"])
    assert "string" in _types(props["query"])
    for name in ("query", "policy_area", "bill_type", "from_date", "to_date"):
        assert props[name].get("default") is None, f"{name} should default to None"


async def test_search_bills_schema_policy_area_enum(client: Client):
    """policy_area exposes a flat enum of the controlled Congress.gov names."""
    props = await _props(client)
    prop = props["policy_area"]
    assert "$ref" not in json.dumps(prop), "policy_area enum should be inlined, not a $ref"
    assert set(_enum_values(prop)) == POLICY_AREAS


async def test_search_bills_schema_bill_type_enum(client: Client):
    """bill_type uses the same enum as the other bill tools."""
    props = await _props(client)
    assert set(_enum_values(props["bill_type"])) == BILL_TYPES


async def test_search_bills_schema_max_matches(client: Client):
    """max_matches defaults to 50 and must be at least 1."""
    props = await _props(client)
    prop = props["max_matches"]
    assert prop.get("default") == DEFAULT_MAX_MATCHES
    assert _lower_bound(prop) == 1


async def test_search_bills_schema_max_scan_bounds(client: Client):
    """max_scan is an optional int with a quota-safe default and bounds."""
    props = await _props(client)
    prop = props["max_scan"]
    assert "integer" in _types(prop)
    assert _lower_bound(prop) == 1
    upper = _upper_bound(prop)
    assert upper is not None, "max_scan needs a maximum"
    assert upper <= 5000, "max_scan maximum must stay within the hourly API quota"
    default = prop.get("default")
    assert isinstance(default, int)
    assert 25 <= default <= 500
    assert default <= upper


def test_policy_area_literal_matches_controlled_list():
    """enums.PolicyAreaLiteral holds exactly the controlled policy area names."""
    from congress_mcp.types import enums

    literal = getattr(enums, "PolicyAreaLiteral", None)
    assert literal is not None, "congress_mcp.types.enums.PolicyAreaLiteral is missing"
    assert set(get_args(literal)) == POLICY_AREAS


# --- offline tests: argument validation (fails before any API call) ---


@pytest.mark.parametrize(
    "args",
    [
        {"congress": CONGRESS},
        {"congress": CONGRESS, "query": None, "policy_area": None},
        {"congress": CONGRESS, "bill_type": "hr", **WINDOW},
    ],
    ids=["only-congress", "explicit-nulls", "other-filters-only"],
)
async def test_search_bills_requires_query_or_policy_area(client: Client, args):
    """Neither query nor policy_area: ToolError naming both parameters."""
    await _get_tool(client)
    with pytest.raises(ToolError) as exc_info:
        await client.call_tool(TOOL, args)
    message = str(exc_info.value)
    _assert_not_network_error(message)
    assert "query" in message
    assert "policy_area" in message


async def test_search_bills_rejects_empty_query(client: Client):
    """An empty query is not a match-all search."""
    await _get_tool(client)
    with pytest.raises(ToolError) as exc_info:
        await client.call_tool(TOOL, {"congress": CONGRESS, "query": ""})
    message = str(exc_info.value)
    _assert_not_network_error(message)
    assert "query" in message


async def test_search_bills_rejects_invalid_policy_area(client: Client):
    """A name outside the controlled list is rejected and valid names are shown."""
    await _get_tool(client)
    with pytest.raises(ToolError) as exc_info:
        await client.call_tool(
            TOOL, {"congress": CONGRESS, "policy_area": "Space Exploration"}
        )
    message = str(exc_info.value)
    _assert_not_network_error(message)
    assert "policy_area" in message
    assert "Health" in message


@pytest.mark.parametrize(
    ("param", "value"),
    [
        ("bill_type", "zz"),
        ("max_matches", 0),
        ("max_scan", 0),
        ("max_scan", 1_000_000),
    ],
)
async def test_search_bills_rejects_out_of_range_args(client: Client, param, value):
    """Invalid bill_type and out-of-bounds caps are rejected by validation."""
    await _get_tool(client)
    args = {"congress": CONGRESS, "query": "veteran", param: value}
    with pytest.raises(ToolError) as exc_info:
        await client.call_tool(TOOL, args)
    message = str(exc_info.value)
    _assert_not_network_error(message)
    assert param in message


# --- live helpers ---


async def _search(client: Client, args: dict[str, Any]) -> dict[str, Any]:
    """Call search_bills and check the response invariants of the contract."""
    await _get_tool(client)
    data = parse_result(await client.call_tool(TOOL, args))

    for key in (
        "matches",
        "match_count",
        "total_candidates",
        "bills_scanned",
        "detail_fetches",
        "stop_reason",
        "search_complete",
        "query",
        "policy_area",
    ):
        assert key in data, f"response is missing {key!r}"

    matches = data["matches"]
    max_matches = args.get("max_matches", DEFAULT_MAX_MATCHES)
    query = args.get("query")
    policy_area = args.get("policy_area")

    assert isinstance(matches, list)
    assert data["match_count"] == len(matches)
    assert data["match_count"] <= max_matches
    assert data["query"] == query
    assert data["policy_area"] == policy_area

    # A live test only counts if every detail fetch succeeded.
    assert not data.get("_warnings"), data.get("_warnings")

    assert data["stop_reason"] in STOP_REASONS
    assert data["search_complete"] is (data["stop_reason"] == "exhausted")
    assert 0 <= data["bills_scanned"] <= data["total_candidates"]
    assert data["detail_fetches"] >= 0
    if data["stop_reason"] == "max_matches":
        assert data["match_count"] == max_matches
    if data["stop_reason"] == "exhausted":
        assert data["bills_scanned"] == data["total_candidates"]

    if policy_area is None:
        assert data["detail_fetches"] == 0, "title-only search must not fetch bill details"
        assert data["stop_reason"] != "max_scan"
    else:
        assert data["detail_fetches"] >= data["match_count"]
        if "max_scan" in args:
            assert data["detail_fetches"] <= args["max_scan"]
            if data["stop_reason"] == "max_scan":
                assert data["detail_fetches"] == args["max_scan"]
        if query is None:
            assert data["detail_fetches"] == data["bills_scanned"]
        else:
            assert data["detail_fetches"] <= data["bills_scanned"]

    for match in matches:
        assert match.get("congress") == args["congress"]
        assert match.get("number")
        if "bill_type" in args:
            assert str(match.get("type", "")).lower() == args["bill_type"]
        if query is not None:
            assert query.lower() in match.get("title", "").lower(), match.get("title")
        if policy_area is not None:
            assert (match.get("policyArea") or {}).get("name") == policy_area, match
    return data


# --- live tests ---


@needs_api_key
async def test_search_bills_query_only_matches_titles(client: Client):
    """query only: every title contains the keyword, no detail fetches."""
    data = await _search(
        client,
        {
            "congress": CONGRESS,
            "query": "veteran",
            "bill_type": "hr",
            **WINDOW,
            "max_matches": 5,
        },
    )
    assert data["match_count"] == 5
    assert data["stop_reason"] == "max_matches"
    assert data["search_complete"] is False
    assert data["detail_fetches"] == 0
    assert data["bills_scanned"] >= 5
    assert data["policy_area"] is None


@needs_api_key
async def test_search_bills_query_is_case_insensitive(client: Client):
    """An upper-case query still matches mixed-case titles."""
    data = await _search(
        client,
        {
            "congress": CONGRESS,
            "query": "VETERAN",
            "bill_type": "hr",
            **WINDOW,
            "max_matches": 2,
        },
    )
    assert data["match_count"] >= 1
    assert data["query"] == "VETERAN"


@needs_api_key
async def test_search_bills_policy_area_only(client: Client):
    """policy_area only: every match has the requested policyArea.name."""
    data = await _search(
        client,
        {
            "congress": CONGRESS,
            "policy_area": "Health",
            "bill_type": "hr",
            **WINDOW,
            "max_matches": 3,
            "max_scan": 40,
        },
    )
    assert data["match_count"] >= 1
    assert data["query"] is None
    assert data["detail_fetches"] >= 1
    assert data["detail_fetches"] == data["bills_scanned"]
    assert data["stop_reason"] in {"max_matches", "max_scan"}


@needs_api_key
async def test_search_bills_query_and_policy_area(client: Client):
    """Both filters: matches satisfy both; only title matches are detail-fetched."""
    data = await _search(
        client,
        {
            "congress": CONGRESS,
            "query": "Medicare",
            "policy_area": "Health",
            "bill_type": "hr",
            **WINDOW,
            "max_matches": 3,
            "max_scan": 10,
        },
    )
    assert data["match_count"] >= 1
    assert data["detail_fetches"] >= 1
    # Title filtering happens first, so far fewer bills are detail-fetched
    # than are scanned.
    assert data["detail_fetches"] < data["bills_scanned"]


@needs_api_key
async def test_search_bills_reports_scan_cap(client: Client):
    """A scan cap below the candidate count stops early and says so.

    max_scan=30 is deliberately above 25 so that detail fetches silently
    truncated to one concurrent batch (issue #19) are caught.
    """
    max_scan = 30
    data = await _search(
        client,
        {
            "congress": CONGRESS,
            "policy_area": "Health",
            "bill_type": "hr",
            **WINDOW,
            "max_scan": max_scan,
        },
    )
    assert data["total_candidates"] > max_scan
    assert data["stop_reason"] == "max_scan"
    assert data["search_complete"] is False
    assert data["detail_fetches"] == max_scan
    assert data["bills_scanned"] == max_scan
    assert data["match_count"] < DEFAULT_MAX_MATCHES


@needs_api_key
async def test_search_bills_exhausts_small_candidate_set(client: Client):
    """No title matches in a small bill type: full scan, zero detail fetches.

    With both filters, a query that matches no title means the policy area
    check never runs, so the whole candidate list costs only list requests.
    """
    data = await _search(
        client,
        {
            "congress": CONGRESS,
            "query": "xyzzyplugh42",
            "policy_area": "Health",
            "bill_type": "sconres",
            **WINDOW,
        },
    )
    assert data["match_count"] == 0
    assert data["matches"] == []
    assert data["total_candidates"] > 0
    assert data["bills_scanned"] == data["total_candidates"]
    assert data["detail_fetches"] == 0
    assert data["stop_reason"] == "exhausted"
    assert data["search_complete"] is True
