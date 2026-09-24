"""Bill-related tools for Congress.gov API."""

from typing import Annotated, Any

from fastmcp.exceptions import ToolError
from pydantic import Field

from congress_mcp.annotations import READONLY_ANNOTATIONS
from congress_mcp.client import CongressClient
from congress_mcp.config import Config
from congress_mcp.types.enums import BillTypeLiteral, PolicyAreaLiteral

try:
    from fastmcp import FastMCP
except ImportError:
    FastMCP = Any  # type: ignore[misc, assignment]

# search_bills sends bill detail requests in batches of at most this many.
# CongressClient.fetch_details_concurrent silently drops endpoints beyond its
# max_concurrent argument (issue #19), so larger batches would skip bills.
_DETAIL_BATCH_SIZE = 25


class _BillSearch:
    """Client-side title and policy area filter over a paged bill list.

    Candidates are evaluated in list order. A title mismatch is settled from
    the list item alone. A candidate that needs the policy area check waits in
    ``pending`` until a batch is full. A batch never holds more candidates than
    ``max_scan`` or ``max_matches`` can still use, so no detail request is
    wasted and each cap is hit exactly rather than overshot.
    """

    def __init__(
        self,
        client: CongressClient,
        congress: int,
        query: str | None,
        policy_area: str | None,
        max_matches: int,
        max_scan: int,
    ) -> None:
        self.client = client
        self.congress = congress
        self.query = query
        self.query_lower = query.lower() if query is not None else None
        self.policy_area = policy_area
        self.max_matches = max_matches
        self.max_scan = max_scan
        self.matches: list[dict[str, Any]] = []
        self.pending: list[dict[str, Any]] = []
        self.failed_endpoints: list[str] = []
        self.bills_scanned = 0
        self.detail_fetches = 0

    def done(self) -> bool:
        """True once max_matches or max_scan has been reached."""
        return len(self.matches) >= self.max_matches or self.detail_fetches >= self.max_scan

    def _batch_limit(self) -> int:
        return min(
            _DETAIL_BATCH_SIZE,
            self.max_scan - self.detail_fetches,
            self.max_matches - len(self.matches),
        )

    async def consider(self, bill: dict[str, Any]) -> None:
        """Evaluate one candidate, or queue it for the policy area check."""
        title = str(bill.get("title") or "")
        if self.query_lower is not None and self.query_lower not in title.lower():
            self.bills_scanned += 1
        elif self.policy_area is None:
            self.bills_scanned += 1
            self.matches.append(bill)
        else:
            self.pending.append(bill)
            if len(self.pending) >= self._batch_limit():
                await self.check_pending()

    async def check_pending(self) -> None:
        """Fetch details for the queued candidates and keep policy area matches."""
        batch, self.pending = self.pending, []
        if not batch:
            return
        endpoints = [
            f"/bill/{self.congress}/{str(bill.get('type', '')).lower()}/{bill.get('number', '')}"
            for bill in batch
        ]
        # RateLimitError and AuthenticationError propagate; other failures
        # come back as None.
        details = await self.client.fetch_details_concurrent(
            endpoints, max_concurrent=len(endpoints)
        )
        self.detail_fetches += len(batch)
        self.bills_scanned += len(batch)
        for bill, endpoint, detail in zip(batch, endpoints, details, strict=True):
            data = (detail or {}).get("bill")
            if not isinstance(data, dict):
                self.failed_endpoints.append(endpoint)
                continue
            policy_area = data.get("policyArea") or {}
            if policy_area.get("name") == self.policy_area:
                self.matches.append({**bill, "policyArea": policy_area})

    async def run(self, endpoint: str, params: dict[str, Any], page_size: int) -> dict[str, Any]:
        """Page through ``endpoint`` until a cap is reached or the list runs out."""
        seen: set[tuple[str, str]] = set()
        total_candidates = 0
        offset = 0
        while not self.done():
            page = await self.client.get(endpoint, params=params, limit=page_size, offset=offset)
            total_candidates = page.get("pagination", {}).get("count", 0)
            bills = page.get("bills", [])
            for bill in bills:
                # Offset paging can repeat a bill when the list shifts between
                # pages; evaluate and count each bill once.
                key = (str(bill.get("type", "")).lower(), str(bill.get("number", "")))
                if key in seen:
                    continue
                seen.add(key)
                await self.consider(bill)
                if self.done():
                    break
            offset += len(bills)
            if not bills or offset >= total_candidates:
                break
        # Candidates still queued when the list ran out. There are fewer of
        # them than either cap can use, so this never overshoots a cap.
        await self.check_pending()

        if self.bills_scanned == total_candidates:
            stop_reason = "exhausted"
        elif len(self.matches) >= self.max_matches:
            stop_reason = "max_matches"
        elif self.detail_fetches >= self.max_scan:
            stop_reason = "max_scan"
        else:
            # The list ran out before every counted candidate was seen: bills
            # were updated while it was being paged, shifting some past us.
            stop_reason = "list_changed"

        result: dict[str, Any] = {
            "matches": self.matches,
            "match_count": len(self.matches),
            "total_candidates": total_candidates,
            "bills_scanned": self.bills_scanned,
            "detail_fetches": self.detail_fetches,
            "stop_reason": stop_reason,
            "search_complete": stop_reason == "exhausted",
            "query": self.query,
            "policy_area": self.policy_area,
        }
        if self.failed_endpoints:
            result["_warnings"] = [
                f"Detail fetch failed for: {endpoint}" for endpoint in self.failed_endpoints
            ]
        return result


def register_bill_tools(mcp: "FastMCP", config: Config) -> None:
    """Register all bill-related tools with the MCP server."""

    @mcp.tool(annotations=READONLY_ANNOTATIONS)
    async def list_bills(
        congress: Annotated[int, Field(description="Congress number (e.g., 118)", ge=1, le=200)],
        limit: Annotated[
            int | None, Field(description="Maximum results to return (1-250)", ge=1, le=250)
        ] = None,
        offset: Annotated[int, Field(description="Starting position for pagination", ge=0)] = 0,
        from_date: Annotated[
            str | None, Field(description="Filter by update date start (YYYY-MM-DD)")
        ] = None,
        to_date: Annotated[
            str | None, Field(description="Filter by update date end (YYYY-MM-DD)")
        ] = None,
        sort: Annotated[
            str | None, Field(description="Sort order: updateDate+asc or updateDate+desc")
        ] = None,
    ) -> dict[str, Any]:
        """List all bills for a specific Congress.

        Returns bills with full details including sponsors, cosponsors,
        committees, actions, and text versions.
        """
        async with CongressClient(config) as client:
            params: dict[str, Any] = {}
            if from_date:
                params["fromDateTime"] = f"{from_date}T00:00:00Z"
            if to_date:
                params["toDateTime"] = f"{to_date}T23:59:59Z"
            if sort:
                params["sort"] = sort

            response = await client.get(
                f"/bill/{congress}",
                params=params,
                limit=limit,
                offset=offset,
            )

            def build_endpoint(item: dict[str, Any]) -> str:
                bill_type = item.get("type", "").lower()
                bill_number = item.get("number", "")
                return f"/bill/{congress}/{bill_type}/{bill_number}"

            return await client.enrich_list_response(
                response,
                result_key="bills",
                detail_key="bill",
                build_endpoint=build_endpoint,
            )

    @mcp.tool(annotations=READONLY_ANNOTATIONS)
    async def list_bills_by_type(
        congress: Annotated[int, Field(description="Congress number (e.g., 118)", ge=1, le=200)],
        bill_type: Annotated[
            BillTypeLiteral,
            Field(
                description="REQUIRED bill type string. Must be one of: hr (House Bill), s (Senate Bill), hjres (House Joint Resolution), sjres (Senate Joint Resolution), hconres (House Concurrent Resolution), sconres (Senate Concurrent Resolution), hres (House Simple Resolution), sres (Senate Simple Resolution). Example: 'hr' for H.R. bills"
            ),
        ],
        from_date: Annotated[
            str | None, Field(description="Filter by update date start (YYYY-MM-DD)")
        ] = None,
        to_date: Annotated[
            str | None, Field(description="Filter by update date end (YYYY-MM-DD)")
        ] = None,
        sort: Annotated[
            str | None, Field(description="Sort order: updateDate+asc or updateDate+desc")
        ] = None,
        limit: Annotated[
            int | None, Field(description="Maximum results to return (1-250)", ge=1, le=250)
        ] = None,
        offset: Annotated[int, Field(description="Starting position for pagination", ge=0)] = 0,
    ) -> dict[str, Any]:
        """List bills filtered by Congress and bill type.

        Returns bills with full details including sponsors, cosponsors,
        committees, actions, and text versions.

        Bill types:
        - hr: House Bill
        - s: Senate Bill
        - hjres: House Joint Resolution
        - sjres: Senate Joint Resolution
        - hconres: House Concurrent Resolution
        - sconres: Senate Concurrent Resolution
        - hres: House Simple Resolution
        - sres: Senate Simple Resolution
        """
        async with CongressClient(config) as client:
            params: dict[str, Any] = {}
            if from_date:
                params["fromDateTime"] = f"{from_date}T00:00:00Z"
            if to_date:
                params["toDateTime"] = f"{to_date}T23:59:59Z"
            if sort:
                params["sort"] = sort
            response = await client.get(
                f"/bill/{congress}/{bill_type}",
                params=params,
                limit=limit,
                offset=offset,
            )

            def build_endpoint(item: dict[str, Any]) -> str:
                bill_number = item.get("number", "")
                return f"/bill/{congress}/{bill_type}/{bill_number}"

            return await client.enrich_list_response(
                response,
                result_key="bills",
                detail_key="bill",
                build_endpoint=build_endpoint,
            )

    @mcp.tool(annotations=READONLY_ANNOTATIONS)
    async def get_bill(
        congress: Annotated[int, Field(description="Congress number (e.g., 118)", ge=1, le=200)],
        bill_type: Annotated[BillTypeLiteral, Field(description="REQUIRED bill type string. Must be one of: hr, s, hjres, sjres, hconres, sconres, hres, sres. Example: 'hr' for H.R. bills")],
        bill_number: Annotated[int, Field(description="Bill number", ge=1)],
    ) -> dict[str, Any]:
        """Get detailed information about a specific bill.

        Returns comprehensive bill data including sponsors, cosponsors,
        committees, actions, related bills, subjects, and text versions.
        """
        async with CongressClient(config) as client:
            return await client.get(f"/bill/{congress}/{bill_type}/{bill_number}")

    @mcp.tool(annotations=READONLY_ANNOTATIONS)
    async def get_bill_actions(
        congress: Annotated[int, Field(description="Congress number", ge=1, le=200)],
        bill_type: Annotated[BillTypeLiteral, Field(description="REQUIRED bill type string. Must be one of: hr, s, hjres, sjres, hconres, sconres, hres, sres. Example: 'hr' for H.R. bills")],
        bill_number: Annotated[int, Field(description="Bill number", ge=1)],
        limit: Annotated[
            int | None, Field(description="Maximum results to return", ge=1, le=250)
        ] = None,
        offset: Annotated[int, Field(description="Starting position for pagination", ge=0)] = 0,
    ) -> dict[str, Any]:
        """Get all legislative actions taken on a bill.

        Actions include committee referrals, floor votes, amendments,
        passage, presidential actions, and becoming law.
        """
        async with CongressClient(config) as client:
            return await client.get(
                f"/bill/{congress}/{bill_type}/{bill_number}/actions",
                limit=limit,
                offset=offset,
            )

    @mcp.tool(annotations=READONLY_ANNOTATIONS)
    async def get_bill_amendments(
        congress: Annotated[int, Field(description="Congress number", ge=1, le=200)],
        bill_type: Annotated[BillTypeLiteral, Field(description="REQUIRED bill type string. Must be one of: hr, s, hjres, sjres, hconres, sconres, hres, sres. Example: 'hr' for H.R. bills")],
        bill_number: Annotated[int, Field(description="Bill number", ge=1)],
        limit: Annotated[
            int | None, Field(description="Maximum results to return", ge=1, le=250)
        ] = None,
        offset: Annotated[int, Field(description="Starting position for pagination", ge=0)] = 0,
    ) -> dict[str, Any]:
        """Get amendments proposed to a bill.

        Returns both House and Senate amendments with their status and actions.
        """
        async with CongressClient(config) as client:
            return await client.get(
                f"/bill/{congress}/{bill_type}/{bill_number}/amendments",
                limit=limit,
                offset=offset,
            )

    @mcp.tool(annotations=READONLY_ANNOTATIONS)
    async def get_bill_committees(
        congress: Annotated[int, Field(description="Congress number", ge=1, le=200)],
        bill_type: Annotated[BillTypeLiteral, Field(description="REQUIRED bill type string. Must be one of: hr, s, hjres, sjres, hconres, sconres, hres, sres. Example: 'hr' for H.R. bills")],
        bill_number: Annotated[int, Field(description="Bill number", ge=1)],
        limit: Annotated[
            int | None, Field(description="Maximum results to return", ge=1, le=250)
        ] = None,
        offset: Annotated[int, Field(description="Starting position for pagination", ge=0)] = 0,
    ) -> dict[str, Any]:
        """Get committees associated with a bill.

        Returns committees that have considered or reported on the bill,
        including subcommittees.
        """
        async with CongressClient(config) as client:
            return await client.get(
                f"/bill/{congress}/{bill_type}/{bill_number}/committees",
                limit=limit,
                offset=offset,
            )

    @mcp.tool(annotations=READONLY_ANNOTATIONS)
    async def get_bill_cosponsors(
        congress: Annotated[int, Field(description="Congress number", ge=1, le=200)],
        bill_type: Annotated[BillTypeLiteral, Field(description="REQUIRED bill type string. Must be one of: hr, s, hjres, sjres, hconres, sconres, hres, sres. Example: 'hr' for H.R. bills")],
        bill_number: Annotated[int, Field(description="Bill number", ge=1)],
        limit: Annotated[
            int | None, Field(description="Maximum results to return", ge=1, le=250)
        ] = None,
        offset: Annotated[int, Field(description="Starting position for pagination", ge=0)] = 0,
    ) -> dict[str, Any]:
        """Get cosponsors of a bill.

        Returns members who have cosponsored the bill with their
        bioguide ID, name, party, and state.
        """
        async with CongressClient(config) as client:
            return await client.get(
                f"/bill/{congress}/{bill_type}/{bill_number}/cosponsors",
                limit=limit,
                offset=offset,
            )

    @mcp.tool(annotations=READONLY_ANNOTATIONS)
    async def get_bill_related_bills(
        congress: Annotated[int, Field(description="Congress number", ge=1, le=200)],
        bill_type: Annotated[BillTypeLiteral, Field(description="REQUIRED bill type string. Must be one of: hr, s, hjres, sjres, hconres, sconres, hres, sres. Example: 'hr' for H.R. bills")],
        bill_number: Annotated[int, Field(description="Bill number", ge=1)],
        limit: Annotated[
            int | None, Field(description="Maximum results to return", ge=1, le=250)
        ] = None,
        offset: Annotated[int, Field(description="Starting position for pagination", ge=0)] = 0,
    ) -> dict[str, Any]:
        """Get bills related to this bill.

        Relationships include identical bills, companion bills, and
        bills with related subject matter.
        """
        async with CongressClient(config) as client:
            return await client.get(
                f"/bill/{congress}/{bill_type}/{bill_number}/relatedbills",
                limit=limit,
                offset=offset,
            )

    @mcp.tool(annotations=READONLY_ANNOTATIONS)
    async def get_bill_subjects(
        congress: Annotated[int, Field(description="Congress number", ge=1, le=200)],
        bill_type: Annotated[BillTypeLiteral, Field(description="REQUIRED bill type string. Must be one of: hr, s, hjres, sjres, hconres, sconres, hres, sres. Example: 'hr' for H.R. bills")],
        bill_number: Annotated[int, Field(description="Bill number", ge=1)],
        limit: Annotated[
            int | None, Field(description="Maximum results to return", ge=1, le=250)
        ] = None,
        offset: Annotated[int, Field(description="Starting position for pagination", ge=0)] = 0,
    ) -> dict[str, Any]:
        """Get legislative subjects assigned to a bill.

        Subjects are policy areas and topics that describe the bill's content.
        """
        async with CongressClient(config) as client:
            return await client.get(
                f"/bill/{congress}/{bill_type}/{bill_number}/subjects",
                limit=limit,
                offset=offset,
            )

    @mcp.tool(annotations=READONLY_ANNOTATIONS)
    async def get_bill_summaries(
        congress: Annotated[int, Field(description="Congress number", ge=1, le=200)],
        bill_type: Annotated[BillTypeLiteral, Field(description="REQUIRED bill type string. Must be one of: hr, s, hjres, sjres, hconres, sconres, hres, sres. Example: 'hr' for H.R. bills")],
        bill_number: Annotated[int, Field(description="Bill number", ge=1)],
        limit: Annotated[
            int | None, Field(description="Maximum results to return", ge=1, le=250)
        ] = None,
        offset: Annotated[int, Field(description="Starting position for pagination", ge=0)] = 0,
    ) -> dict[str, Any]:
        """Get CRS summaries of a bill.

        Summaries are written by the Congressional Research Service and
        describe the bill's content at various stages of the legislative process.
        """
        async with CongressClient(config) as client:
            return await client.get(
                f"/bill/{congress}/{bill_type}/{bill_number}/summaries",
                limit=limit,
                offset=offset,
            )

    @mcp.tool(annotations=READONLY_ANNOTATIONS)
    async def get_bill_text(
        congress: Annotated[int, Field(description="Congress number", ge=1, le=200)],
        bill_type: Annotated[BillTypeLiteral, Field(description="REQUIRED bill type string. Must be one of: hr, s, hjres, sjres, hconres, sconres, hres, sres. Example: 'hr' for H.R. bills")],
        bill_number: Annotated[int, Field(description="Bill number", ge=1)],
        limit: Annotated[
            int | None, Field(description="Maximum results to return", ge=1, le=250)
        ] = None,
        offset: Annotated[int, Field(description="Starting position for pagination", ge=0)] = 0,
    ) -> dict[str, Any]:
        """Get text versions of a bill.

        Returns available text versions (introduced, reported, engrossed, enrolled)
        with links to PDF, XML, and HTML formats.
        """
        async with CongressClient(config) as client:
            return await client.get(
                f"/bill/{congress}/{bill_type}/{bill_number}/text",
                limit=limit,
                offset=offset,
            )

    @mcp.tool(annotations=READONLY_ANNOTATIONS)
    async def get_bill_titles(
        congress: Annotated[int, Field(description="Congress number", ge=1, le=200)],
        bill_type: Annotated[BillTypeLiteral, Field(description="REQUIRED bill type string. Must be one of: hr, s, hjres, sjres, hconres, sconres, hres, sres. Example: 'hr' for H.R. bills")],
        bill_number: Annotated[int, Field(description="Bill number", ge=1)],
        limit: Annotated[
            int | None, Field(description="Maximum results to return", ge=1, le=250)
        ] = None,
        offset: Annotated[int, Field(description="Starting position for pagination", ge=0)] = 0,
    ) -> dict[str, Any]:
        """Get all titles of a bill.

        Bills may have multiple titles including official titles, short titles,
        and popular names.
        """
        async with CongressClient(config) as client:
            return await client.get(
                f"/bill/{congress}/{bill_type}/{bill_number}/titles",
                limit=limit,
                offset=offset,
            )

    @mcp.tool(annotations=READONLY_ANNOTATIONS)
    async def search_bills(
        congress: Annotated[int, Field(description="Congress number (e.g., 118)", ge=1, le=200)],
        query: Annotated[
            str | None,
            Field(
                description=(
                    "Keyword or phrase to find in bill titles (case-insensitive substring "
                    "match). Cheap: needs only list requests. Give query, policy_area, or both."
                ),
                min_length=2,
            ),
        ] = None,
        policy_area: Annotated[
            PolicyAreaLiteral | None,
            Field(
                description=(
                    "Exact Congress.gov policy area name, e.g. 'Health'. Costs one bill detail "
                    "request per candidate checked (capped by max_scan). Combine with query "
                    "so only bills whose title matches are checked."
                ),
            ),
        ] = None,
        bill_type: Annotated[
            BillTypeLiteral | None,
            Field(
                description=(
                    "Optional bill type filter that narrows the candidates: "
                    "hr, s, hjres, sjres, hconres, sconres, hres, sres"
                )
            ),
        ] = None,
        from_date: Annotated[
            str | None,
            Field(
                description=(
                    "Filter by update date start (YYYY-MM-DD). This is the date the bill "
                    "record was last updated, not its introduced date."
                )
            ),
        ] = None,
        to_date: Annotated[
            str | None,
            Field(
                description=(
                    "Filter by update date end (YYYY-MM-DD). This is the date the bill "
                    "record was last updated, not its introduced date."
                )
            ),
        ] = None,
        max_matches: Annotated[
            int,
            Field(
                description=(
                    "Maximum matching bills to return (default 50). The scan stops "
                    "as soon as this many are found."
                ),
                ge=1,
                le=500,
            ),
        ] = 50,
        max_scan: Annotated[
            int,
            Field(
                description=(
                    "Maximum bill detail requests for the policy area check (default 250). "
                    "Each one counts against the API quota of 5,000 requests per hour. "
                    "Has no effect when policy_area is not given."
                ),
                ge=1,
                le=1000,
            ),
        ] = 250,
    ) -> dict[str, Any]:
        """Search a Congress's bills by title keyword and/or policy area.

        The Congress.gov API cannot filter bills by topic, so this tool pages
        through the bill list for the Congress (narrowed by bill_type and the
        from_date/to_date update window) and filters on the client. Provide
        query, policy_area, or both.

        Cost (the API allows 5,000 requests per hour per key):
        - Title search (query) reads 250 bills per list request, so even a
          whole Congress takes well under 100 requests.
        - Policy area search needs one bill detail request per candidate,
          because the bill list does not include policy areas. max_scan caps
          these requests per call. Adding a query makes it much cheaper: only
          bills whose title matches are checked for policy area.

        Each match is the bill's list entry (congress, type, number, title,
        latestAction, url), plus policyArea when policy_area is given. Use
        get_bill for full details.

        Coverage fields in the response:
        - total_candidates: bills in the list for this congress, bill_type
          and date window.
        - bills_scanned: candidates checked against every filter, in list
          order. A title mismatch counts, and so does a failed detail request.
        - detail_fetches: bill detail requests made (never more than max_scan).
        - stop_reason: "max_matches" (max_matches found; more may exist),
          "max_scan" (detail request cap reached before the list ran out),
          "exhausted" (every candidate was checked), or "list_changed" (bills
          were updated while the list was being paged, so some may have been
          skipped; run the search again).
        - search_complete: true only when stop_reason is "exhausted".
        - _warnings: present only when bill detail requests failed; those
          bills were not checked for policy area and cannot appear in matches.

        After "max_scan", raise max_scan or narrow the candidates with
        bill_type, from_date/to_date, or a title query to search further.
        """
        if query is None and policy_area is None:
            raise ToolError(
                "Provide at least one search filter: query (a title keyword) or "
                "policy_area (a policy area name), or both."
            )

        if bill_type:
            endpoint = f"/bill/{congress}/{bill_type}"
        else:
            endpoint = f"/bill/{congress}"

        params: dict[str, Any] = {}
        if from_date:
            params["fromDateTime"] = f"{from_date}T00:00:00Z"
        if to_date:
            params["toDateTime"] = f"{to_date}T23:59:59Z"

        async with CongressClient(config) as client:
            search = _BillSearch(client, congress, query, policy_area, max_matches, max_scan)
            return await search.run(endpoint, params, page_size=config.max_limit)
