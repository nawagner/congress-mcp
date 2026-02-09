#!/usr/bin/env python3
"""Integration test: calls every Congress.gov MCP tool endpoint against the live API.

Produces a markdown report at .context/integration-test-report.md

Usage:
    CONGRESS_API_KEY=your_key python tests/test_integration_live.py
"""

import asyncio
import os
import sys
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Load .env file if present
_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    for line in _env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

from congress_mcp.client import CongressClient
from congress_mcp.config import Config
from congress_mcp.exceptions import CongressAPIError, NotFoundError, RateLimitError

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CONGRESS = 118
LIMIT = 3
DELAY = 0.5  # seconds between API calls
MAX_RETRIES = 3
RETRY_BASE_DELAY = 10  # seconds to wait on rate limit before retry

# Known-good fallback IDs for 118th Congress
FALLBACKS: dict[str, Any] = {
    "bill_type": "hr",
    "bill_number": 1,
    "law_type": "pub",
    "law_number": 1,
    "amendment_type": "samdt",
    "amendment_number": 1,
    "bioguide_id": "P000197",
    "committee_code": "hsju00",
    "senate_committee_code": "ssju00",
    "report_type": "hrpt",
    "report_number": 1,
    "jacket_number": 53397,
    "event_id": 115538,
    "hearing_jacket_number": 53399,
    "nomination_number": 1,
    "treaty_number": 1,
    "volume_number": 170,
    "issue_number": 1,
    "house_comm_number": 1,
    "senate_comm_number": 1,
    "roll_call_number": 1,
    "session": 1,
    "crs_report_number": "R47000",
    "requirement_number": 1,
}


# ---------------------------------------------------------------------------
# Result tracking
# ---------------------------------------------------------------------------

@dataclass
class TestResult:
    tool_name: str
    category: str
    status: str = "SKIP"  # PASS, FAIL, WARN, SKIP
    elapsed_ms: float = 0.0
    notes: str = ""
    error_trace: str = ""


results: list[TestResult] = []


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def extract(response: dict[str, Any] | None, keys: list[str], fallback: Any) -> Any:
    """Safely extract a nested value from an API response, falling back on failure."""
    if response is None:
        return fallback
    try:
        obj: Any = response
        for key in keys:
            if isinstance(obj, list):
                obj = obj[int(key)]
            else:
                obj = obj[key]
        return obj if obj is not None else fallback
    except (KeyError, IndexError, TypeError, ValueError):
        return fallback


async def run_test(
    client: CongressClient,
    tool_name: str,
    category: str,
    endpoint: str,
    *,
    params: dict[str, Any] | None = None,
    limit: int | None = LIMIT,
    expect_error: type[Exception] | None = None,
) -> dict[str, Any] | None:
    """Execute a single API call with rate-limit retry, record timing and status."""
    result = TestResult(tool_name=tool_name, category=category)

    for attempt in range(MAX_RETRIES + 1):
        start = time.monotonic()
        try:
            response = await client.get(endpoint, params=params, limit=limit)
            elapsed = (time.monotonic() - start) * 1000
            result.elapsed_ms = elapsed

            if expect_error:
                result.status = "FAIL"
                result.notes = f"Expected {expect_error.__name__} but got 200 OK"
            else:
                result.status = "PASS"
                result.notes = f"{elapsed:.0f}ms"

            results.append(result)
            await asyncio.sleep(DELAY)
            return response

        except RateLimitError:
            if attempt < MAX_RETRIES:
                wait = RETRY_BASE_DELAY * (attempt + 1)
                print(f"  Rate limited on {tool_name}, waiting {wait}s (attempt {attempt + 1}/{MAX_RETRIES})...")
                await asyncio.sleep(wait)
                continue
            # Exhausted retries
            elapsed = (time.monotonic() - start) * 1000
            result.elapsed_ms = elapsed
            result.status = "FAIL"
            result.notes = "Rate limited after all retries"
            results.append(result)
            await asyncio.sleep(DELAY)
            return None

        except Exception as e:
            elapsed = (time.monotonic() - start) * 1000
            result.elapsed_ms = elapsed

            if expect_error and isinstance(e, expect_error):
                result.status = "PASS"
                result.notes = f"Correctly raised {type(e).__name__}"
            elif isinstance(e, NotFoundError) and not expect_error:
                result.status = "WARN"
                result.notes = "404 Not Found (data may not exist)"
                result.error_trace = str(e)
            else:
                result.status = "FAIL"
                result.notes = f"{type(e).__name__}: {e}"
                result.error_trace = traceback.format_exc()

            results.append(result)
            await asyncio.sleep(DELAY)
            return None

    return None


# ---------------------------------------------------------------------------
# Phase 0: Infrastructure validation
# ---------------------------------------------------------------------------

async def phase0_infrastructure(client: CongressClient) -> None:
    print("Phase 0: Infrastructure validation...")
    await run_test(client, "get_congress", "Congress", f"/congress/{CONGRESS}")
    await run_test(client, "list_congresses", "Congress", "/congress")


# ---------------------------------------------------------------------------
# Phase 1: List endpoints — collect IDs
# ---------------------------------------------------------------------------

async def phase1_list_endpoints(client: CongressClient, ctx: dict[str, Any]) -> None:
    print("Phase 1: List endpoints...")

    # Bills
    resp = await run_test(client, "list_bills", "Bills", f"/bill/{CONGRESS}")
    ctx["bill_type"] = extract(resp, ["bills", "0", "type"], FALLBACKS["bill_type"])
    if isinstance(ctx["bill_type"], str):
        ctx["bill_type"] = ctx["bill_type"].lower()
    ctx["bill_number"] = extract(resp, ["bills", "0", "number"], FALLBACKS["bill_number"])

    await run_test(client, "list_bills_by_type", "Bills", f"/bill/{CONGRESS}/hr")

    # Laws
    resp = await run_test(client, "list_laws", "Laws", f"/law/{CONGRESS}")
    ctx["law_number"] = extract(resp, ["bills", "0", "number"], FALLBACKS["law_number"])

    await run_test(client, "list_laws_by_type", "Laws", f"/law/{CONGRESS}/pub")

    # Amendments
    resp = await run_test(client, "list_amendments", "Amendments", f"/amendment/{CONGRESS}")
    raw_type = extract(resp, ["amendments", "0", "type"], FALLBACKS["amendment_type"])
    if isinstance(raw_type, str):
        ctx["amendment_type"] = raw_type.lower()
    else:
        ctx["amendment_type"] = FALLBACKS["amendment_type"]
    ctx["amendment_number"] = extract(
        resp, ["amendments", "0", "number"], FALLBACKS["amendment_number"]
    )

    await run_test(
        client, "list_amendments_by_type", "Amendments", f"/amendment/{CONGRESS}/samdt"
    )

    # Members
    resp = await run_test(
        client, "list_members", "Members", "/member", params={"currentMember": "true"}
    )
    ctx["bioguide_id"] = extract(resp, ["members", "0", "bioguideId"], FALLBACKS["bioguide_id"])

    await run_test(
        client, "list_members_by_congress", "Members", f"/member/congress/{CONGRESS}"
    )
    await run_test(client, "list_members_by_state", "Members", "/member/CA")
    await run_test(
        client, "list_members_by_state_and_district", "Members", "/member/CA/12"
    )

    # Committees
    resp = await run_test(client, "list_committees", "Committees", "/committee")
    ctx["committee_code"] = extract(
        resp, ["committees", "0", "systemCode"], FALLBACKS["committee_code"]
    )

    resp = await run_test(
        client, "list_committees_by_chamber", "Committees", "/committee/house"
    )
    # Try to extract a house committee code
    house_code = extract(resp, ["committees", "0", "systemCode"], None)
    if house_code:
        ctx["committee_code"] = house_code

    await run_test(
        client, "list_committees_by_congress", "Committees", f"/committee/{CONGRESS}/house"
    )

    # Also get a senate committee code
    resp = await run_test(
        client,
        "list_committees_by_chamber(senate)",
        "Committees",
        "/committee/senate",
    )
    ctx["senate_committee_code"] = extract(
        resp, ["committees", "0", "systemCode"], FALLBACKS["senate_committee_code"]
    )

    # Committee Reports
    resp = await run_test(
        client, "list_committee_reports", "Committee Reports", f"/committee-report/{CONGRESS}/hrpt"
    )
    ctx["report_number"] = extract(
        resp, ["committeeReports", "0", "number"], FALLBACKS["report_number"]
    )

    # Committee Prints
    resp = await run_test(
        client, "list_committee_prints", "Committee Prints", f"/committee-print/{CONGRESS}/house"
    )
    ctx["jacket_number"] = extract(
        resp, ["committeePrints", "0", "jacketNumber"], FALLBACKS["jacket_number"]
    )

    # Committee Meetings
    resp = await run_test(
        client, "list_committee_meetings", "Committee Meetings", f"/committee-meeting/{CONGRESS}/house"
    )
    ctx["event_id"] = extract(
        resp, ["committeeMeetings", "0", "eventId"], FALLBACKS["event_id"]
    )

    # Hearings
    resp = await run_test(
        client, "list_hearings", "Hearings", f"/hearing/{CONGRESS}/house"
    )
    ctx["hearing_jacket_number"] = extract(
        resp, ["hearings", "0", "jacketNumber"], FALLBACKS["hearing_jacket_number"]
    )

    # Nominations
    resp = await run_test(
        client, "list_nominations", "Nominations", f"/nomination/{CONGRESS}"
    )
    ctx["nomination_number"] = extract(
        resp, ["nominations", "0", "number"], FALLBACKS["nomination_number"]
    )

    # Treaties
    resp = await run_test(
        client, "list_treaties", "Treaties", f"/treaty/{CONGRESS}"
    )
    ctx["treaty_number"] = extract(
        resp, ["treaties", "0", "number"], FALLBACKS["treaty_number"]
    )

    # Congressional Record
    resp = await run_test(
        client, "list_daily_congressional_record", "Congressional Record", "/daily-congressional-record"
    )
    ctx["volume_number"] = extract(
        resp, ["dailyCongressionalRecord", "0", "volumeNumber"], FALLBACKS["volume_number"]
    )

    # Known upstream API bug: /bound-congressional-record/{year} returns 500.
    # The bare /bound-congressional-record (no year) works fine.
    await run_test(
        client,
        "list_bound_congressional_record",
        "Congressional Record",
        "/bound-congressional-record/2023",
        expect_error=CongressAPIError,
    )

    # Communications
    resp = await run_test(
        client,
        "list_house_communications",
        "Communications",
        f"/house-communication/{CONGRESS}/ec",
    )
    ctx["house_comm_number"] = extract(
        resp, ["houseCommunications", "0", "number"], FALLBACKS["house_comm_number"]
    )

    resp = await run_test(
        client,
        "list_senate_communications",
        "Communications",
        f"/senate-communication/{CONGRESS}/ec",
    )
    ctx["senate_comm_number"] = extract(
        resp, ["senateCommunications", "0", "number"], FALLBACKS["senate_comm_number"]
    )

    # Votes
    resp = await run_test(
        client, "list_house_votes", "Votes", f"/house-vote/{CONGRESS}/1"
    )
    ctx["roll_call_number"] = extract(
        resp, ["houseVotes", "0", "rollCallNumber"], FALLBACKS["roll_call_number"]
    )

    # Summaries
    await run_test(client, "list_summaries", "Summaries", "/summaries")
    await run_test(
        client, "list_summaries_by_congress", "Summaries", f"/summaries/{CONGRESS}"
    )
    await run_test(
        client, "list_summaries_by_type", "Summaries", f"/summaries/{CONGRESS}/hr"
    )

    # CRS Reports
    resp = await run_test(client, "list_crs_reports", "CRS Reports", "/crsreport")
    ctx["crs_report_number"] = extract(
        resp, ["CRSReports", "0", "reportNumber"], FALLBACKS["crs_report_number"]
    )

    # House Requirements
    resp = await run_test(
        client, "list_house_requirements", "House Requirements", "/house-requirement"
    )
    ctx["requirement_number"] = extract(
        resp, ["houseRequirements", "0", "number"], FALLBACKS["requirement_number"]
    )


# ---------------------------------------------------------------------------
# Phase 2: Detail endpoints — use extracted IDs
# ---------------------------------------------------------------------------

async def phase2_detail_endpoints(client: CongressClient, ctx: dict[str, Any]) -> None:
    print("Phase 2: Detail endpoints...")

    bt = ctx.get("bill_type", FALLBACKS["bill_type"])
    bn = ctx.get("bill_number", FALLBACKS["bill_number"])
    at = ctx.get("amendment_type", FALLBACKS["amendment_type"])
    an = ctx.get("amendment_number", FALLBACKS["amendment_number"])
    bio = ctx.get("bioguide_id", FALLBACKS["bioguide_id"])
    cc = ctx.get("committee_code", FALLBACKS["committee_code"])
    scc = ctx.get("senate_committee_code", FALLBACKS["senate_committee_code"])
    rn = ctx.get("report_number", FALLBACKS["report_number"])
    jn = ctx.get("jacket_number", FALLBACKS["jacket_number"])
    eid = ctx.get("event_id", FALLBACKS["event_id"])
    hjn = ctx.get("hearing_jacket_number", FALLBACKS["hearing_jacket_number"])
    nn = ctx.get("nomination_number", FALLBACKS["nomination_number"])
    tn = ctx.get("treaty_number", FALLBACKS["treaty_number"])
    vn = ctx.get("volume_number", FALLBACKS["volume_number"])
    ln = ctx.get("law_number", FALLBACKS["law_number"])
    hcn = ctx.get("house_comm_number", FALLBACKS["house_comm_number"])
    scn = ctx.get("senate_comm_number", FALLBACKS["senate_comm_number"])
    rcn = ctx.get("roll_call_number", FALLBACKS["roll_call_number"])
    crn = ctx.get("crs_report_number", FALLBACKS["crs_report_number"])
    reqn = ctx.get("requirement_number", FALLBACKS["requirement_number"])

    # --- Bills (10) ---
    await run_test(client, "get_bill", "Bills", f"/bill/{CONGRESS}/{bt}/{bn}")
    await run_test(client, "get_bill_actions", "Bills", f"/bill/{CONGRESS}/{bt}/{bn}/actions")
    await run_test(client, "get_bill_amendments", "Bills", f"/bill/{CONGRESS}/{bt}/{bn}/amendments")
    await run_test(client, "get_bill_committees", "Bills", f"/bill/{CONGRESS}/{bt}/{bn}/committees")
    await run_test(client, "get_bill_cosponsors", "Bills", f"/bill/{CONGRESS}/{bt}/{bn}/cosponsors")
    await run_test(
        client, "get_bill_related_bills", "Bills", f"/bill/{CONGRESS}/{bt}/{bn}/relatedbills"
    )
    await run_test(client, "get_bill_subjects", "Bills", f"/bill/{CONGRESS}/{bt}/{bn}/subjects")
    await run_test(client, "get_bill_summaries", "Bills", f"/bill/{CONGRESS}/{bt}/{bn}/summaries")
    await run_test(client, "get_bill_text", "Bills", f"/bill/{CONGRESS}/{bt}/{bn}/text")
    await run_test(client, "get_bill_titles", "Bills", f"/bill/{CONGRESS}/{bt}/{bn}/titles")

    # --- Laws (1) ---
    await run_test(client, "get_law", "Laws", f"/law/{CONGRESS}/pub/{ln}")

    # --- Amendments (5) ---
    await run_test(
        client, "get_amendment", "Amendments", f"/amendment/{CONGRESS}/{at}/{an}"
    )
    await run_test(
        client, "get_amendment_actions", "Amendments", f"/amendment/{CONGRESS}/{at}/{an}/actions"
    )
    await run_test(
        client,
        "get_amendment_cosponsors",
        "Amendments",
        f"/amendment/{CONGRESS}/{at}/{an}/cosponsors",
    )
    await run_test(
        client,
        "get_amendment_amendments",
        "Amendments",
        f"/amendment/{CONGRESS}/{at}/{an}/amendments",
    )
    await run_test(
        client, "get_amendment_text", "Amendments", f"/amendment/{CONGRESS}/{at}/{an}/text"
    )

    # --- Members (3) ---
    await run_test(client, "get_member", "Members", f"/member/{bio}")
    await run_test(
        client,
        "get_member_sponsored_legislation",
        "Members",
        f"/member/{bio}/sponsored-legislation",
    )
    await run_test(
        client,
        "get_member_cosponsored_legislation",
        "Members",
        f"/member/{bio}/cosponsored-legislation",
    )

    # --- Committees (7) ---
    await run_test(
        client, "get_committee", "Committees", f"/committee/house/{cc}"
    )
    await run_test(
        client,
        "get_committee_by_congress",
        "Committees",
        f"/committee/{CONGRESS}/house/{cc}",
    )
    await run_test(
        client, "get_committee_bills", "Committees", f"/committee/house/{cc}/bills"
    )
    await run_test(
        client,
        "get_committee_reports_list",
        "Committees",
        f"/committee/house/{cc}/reports",
    )
    await run_test(
        client,
        "get_committee_nominations",
        "Committees",
        f"/committee/senate/{scc}/nominations",
    )
    await run_test(
        client,
        "get_committee_house_communications",
        "Committees",
        f"/committee/house/{cc}/house-communication",
    )
    await run_test(
        client,
        "get_committee_senate_communications",
        "Committees",
        f"/committee/senate/{scc}/senate-communication",
    )

    # --- Committee Reports (2) ---
    await run_test(
        client,
        "get_committee_report",
        "Committee Reports",
        f"/committee-report/{CONGRESS}/hrpt/{rn}",
    )
    await run_test(
        client,
        "get_committee_report_text",
        "Committee Reports",
        f"/committee-report/{CONGRESS}/hrpt/{rn}/text",
    )

    # --- Committee Prints (2) ---
    await run_test(
        client,
        "get_committee_print",
        "Committee Prints",
        f"/committee-print/{CONGRESS}/house/{jn}",
    )
    await run_test(
        client,
        "get_committee_print_text",
        "Committee Prints",
        f"/committee-print/{CONGRESS}/house/{jn}/text",
    )

    # --- Committee Meetings (1) ---
    await run_test(
        client,
        "get_committee_meeting",
        "Committee Meetings",
        f"/committee-meeting/{CONGRESS}/house/{eid}",
    )

    # --- Hearings (1) ---
    await run_test(
        client, "get_hearing", "Hearings", f"/hearing/{CONGRESS}/house/{hjn}"
    )

    # --- Nominations (5) ---
    await run_test(
        client, "get_nomination", "Nominations", f"/nomination/{CONGRESS}/{nn}"
    )
    await run_test(
        client, "get_nomination_nominees", "Nominations", f"/nomination/{CONGRESS}/{nn}/1"
    )
    await run_test(
        client,
        "get_nomination_actions",
        "Nominations",
        f"/nomination/{CONGRESS}/{nn}/actions",
    )
    await run_test(
        client,
        "get_nomination_committees",
        "Nominations",
        f"/nomination/{CONGRESS}/{nn}/committees",
    )
    await run_test(
        client,
        "get_nomination_hearings",
        "Nominations",
        f"/nomination/{CONGRESS}/{nn}/hearings",
    )

    # --- Treaties (4) ---
    await run_test(client, "get_treaty", "Treaties", f"/treaty/{CONGRESS}/{tn}")
    await run_test(
        client, "get_treaty_actions", "Treaties", f"/treaty/{CONGRESS}/{tn}/actions"
    )
    await run_test(
        client, "get_treaty_committees", "Treaties", f"/treaty/{CONGRESS}/{tn}/committees"
    )
    # Treaty part may not exist for all treaties — mark as WARN if 404
    await run_test(
        client, "get_treaty_part", "Treaties", f"/treaty/{CONGRESS}/{tn}/A"
    )

    # --- Congressional Record (5) ---
    await run_test(
        client,
        "list_daily_congressional_record_by_volume",
        "Congressional Record",
        f"/daily-congressional-record/{vn}",
    )
    await run_test(
        client,
        "get_daily_congressional_record_issue",
        "Congressional Record",
        f"/daily-congressional-record/{vn}/1",
    )
    await run_test(
        client,
        "get_daily_congressional_record_articles",
        "Congressional Record",
        f"/daily-congressional-record/{vn}/1/articles",
    )
    # Known upstream API bug: /bound-congressional-record/{year}/{month} returns 500.
    await run_test(
        client,
        "list_bound_congressional_record_by_month",
        "Congressional Record",
        "/bound-congressional-record/2023/3",
        expect_error=CongressAPIError,
    )
    await run_test(
        client,
        "get_bound_congressional_record_by_date",
        "Congressional Record",
        "/bound-congressional-record/2023/3/22",
    )

    # --- Communications (2) ---
    await run_test(
        client,
        "get_house_communication",
        "Communications",
        f"/house-communication/{CONGRESS}/ec/{hcn}",
    )
    await run_test(
        client,
        "get_senate_communication",
        "Communications",
        f"/senate-communication/{CONGRESS}/ec/{scn}",
    )

    # --- Votes (2) ---
    await run_test(
        client, "get_house_vote", "Votes", f"/house-vote/{CONGRESS}/1/{rcn}"
    )
    await run_test(
        client,
        "get_house_vote_members",
        "Votes",
        f"/house-vote/{CONGRESS}/1/{rcn}/members",
    )

    # --- CRS Reports (1) ---
    await run_test(client, "get_crs_report", "CRS Reports", f"/crsreport/{crn}")

    # --- House Requirements (2) ---
    await run_test(
        client,
        "get_house_requirement",
        "House Requirements",
        f"/house-requirement/{reqn}",
    )
    await run_test(
        client,
        "get_house_requirement_communications",
        "House Requirements",
        f"/house-requirement/{reqn}/matching-communications",
    )


# ---------------------------------------------------------------------------
# Phase 3: Error handling
# ---------------------------------------------------------------------------

async def phase3_error_handling(client: CongressClient) -> None:
    print("Phase 3: Error handling...")

    await run_test(
        client,
        "get_bill (invalid)",
        "Error Handling",
        "/bill/999/hr/99999",
        expect_error=NotFoundError,
    )
    await run_test(
        client,
        "get_member (invalid)",
        "Error Handling",
        "/member/ZZZZZZZ",
        expect_error=NotFoundError,
    )
    await run_test(
        client,
        "get_law (invalid)",
        "Error Handling",
        "/law/118/pub/99999",
        expect_error=NotFoundError,
    )
    await run_test(
        client,
        "get_nomination (invalid)",
        "Error Handling",
        "/nomination/999/99999",
        expect_error=NotFoundError,
    )
    # Congress.gov API returns 500 (not 404) for invalid CRS reports.
    # The MCP tool layer converts this to NotFoundError, but at the
    # client level it surfaces as CongressAPIError.
    await run_test(
        client,
        "get_crs_report (invalid)",
        "Error Handling",
        "/crsreport/ZZZZZZZ",
        expect_error=CongressAPIError,
    )


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def generate_report(
    start_time: datetime, end_time: datetime, ctx: dict[str, Any]
) -> str:
    duration = (end_time - start_time).total_seconds()
    passed = sum(1 for r in results if r.status == "PASS")
    failed = sum(1 for r in results if r.status == "FAIL")
    warned = sum(1 for r in results if r.status == "WARN")
    total = len(results)

    lines: list[str] = []
    lines.append("# Congress.gov MCP Server - Integration Test Report\n")
    lines.append(f"**Date**: {start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    lines.append(f"**Duration**: {duration:.1f} seconds")
    lines.append(f"**Congress**: {CONGRESS}th (2023-2025)")
    lines.append(f"**API Base**: https://api.congress.gov/v3\n")

    lines.append("## Summary\n")
    lines.append("| Metric | Count |")
    lines.append("|--------|-------|")
    lines.append(f"| Total Tests | {total} |")
    lines.append(f"| Passed | {passed} |")
    lines.append(f"| Failed | {failed} |")
    lines.append(f"| Warnings | {warned} |")
    lines.append(f"| Pass Rate | {passed/total*100:.1f}% |")
    lines.append("")

    # Group results by category
    categories: dict[str, list[TestResult]] = {}
    for r in results:
        categories.setdefault(r.category, []).append(r)

    lines.append("## Results by Category\n")
    for category, cat_results in categories.items():
        cat_passed = sum(1 for r in cat_results if r.status == "PASS")
        cat_total = len(cat_results)
        lines.append(f"### {category} ({cat_passed}/{cat_total} passed)\n")
        lines.append("| # | Tool | Status | Time (ms) | Notes |")
        lines.append("|---|------|--------|-----------|-------|")
        for i, r in enumerate(cat_results, 1):
            status_icon = {"PASS": "PASS", "FAIL": "**FAIL**", "WARN": "WARN", "SKIP": "SKIP"}[
                r.status
            ]
            lines.append(
                f"| {i} | `{r.tool_name}` | {status_icon} | {r.elapsed_ms:.0f} | {r.notes} |"
            )
        lines.append("")

    # Failures detail
    failures = [r for r in results if r.status == "FAIL"]
    if failures:
        lines.append("## Failures\n")
        for r in failures:
            lines.append(f"### `{r.tool_name}` ({r.category})")
            lines.append(f"- **Notes**: {r.notes}")
            if r.error_trace:
                lines.append(f"- **Traceback**:\n```\n{r.error_trace}\n```")
            lines.append("")

    # Warnings detail
    warnings = [r for r in results if r.status == "WARN"]
    if warnings:
        lines.append("## Warnings\n")
        for r in warnings:
            lines.append(f"- `{r.tool_name}` ({r.category}): {r.notes}")
        lines.append("")

    # Extracted IDs
    lines.append("## Extracted IDs Used\n")
    lines.append("| Parameter | Value | Source |")
    lines.append("|-----------|-------|--------|")
    for key, value in sorted(ctx.items()):
        source = "fallback" if value == FALLBACKS.get(key) else "extracted"
        lines.append(f"| {key} | `{value}` | {source} |")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main() -> None:
    try:
        config = Config.from_env()
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    ctx: dict[str, Any] = {}
    start_time = datetime.now(timezone.utc)

    print(f"Starting integration test against live Congress.gov API (Congress {CONGRESS})...")
    print(f"API base: {config.base_url}\n")

    async with CongressClient(config) as client:
        await phase0_infrastructure(client)
        await phase1_list_endpoints(client, ctx)
        await phase2_detail_endpoints(client, ctx)
        await phase3_error_handling(client)

    end_time = datetime.now(timezone.utc)

    report = generate_report(start_time, end_time, ctx)

    report_path = Path(__file__).parent.parent / ".context" / "integration-test-report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report)

    # Print summary
    passed = sum(1 for r in results if r.status == "PASS")
    failed = sum(1 for r in results if r.status == "FAIL")
    warned = sum(1 for r in results if r.status == "WARN")
    total = len(results)

    print(f"\n{'='*60}")
    print(f"Results: {passed} passed, {failed} failed, {warned} warnings, {total} total")
    print(f"Report: {report_path}")
    print(f"Duration: {(end_time - start_time).total_seconds():.1f}s")
    print(f"{'='*60}")

    if failed > 0:
        print("\nFailed tests:")
        for r in results:
            if r.status == "FAIL":
                print(f"  - {r.tool_name}: {r.notes}")

    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    asyncio.run(main())
