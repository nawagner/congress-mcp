"""Bill-related tools for Congress.gov API."""

from typing import Annotated, Any

from pydantic import Field

from congress_mcp.annotations import READONLY_ANNOTATIONS
from congress_mcp.client import CongressClient
from congress_mcp.config import Config
from congress_mcp.types.enums import BillTypeLiteral

try:
    from fastmcp import FastMCP
except ImportError:
    FastMCP = Any  # type: ignore[misc, assignment]


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
