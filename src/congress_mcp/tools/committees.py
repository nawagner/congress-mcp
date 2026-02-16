"""Committee-related tools for Congress.gov API."""

from typing import Annotated, Any

from pydantic import Field

from congress_mcp.annotations import READONLY_ANNOTATIONS
from congress_mcp.client import CongressClient
from congress_mcp.config import Config
from congress_mcp.types.enums import ChamberLiteral

try:
    from fastmcp import FastMCP
except ImportError:
    FastMCP = Any  # type: ignore[misc, assignment]


def register_committee_tools(mcp: "FastMCP", config: Config) -> None:
    """Register all committee-related tools with the MCP server."""

    @mcp.tool(annotations=READONLY_ANNOTATIONS)
    async def list_committees(
        from_date: Annotated[
            str | None, Field(description="Filter by update date start (YYYY-MM-DD)")
        ] = None,
        to_date: Annotated[
            str | None, Field(description="Filter by update date end (YYYY-MM-DD)")
        ] = None,
        limit: Annotated[
            int | None, Field(description="Maximum results to return (1-250)", ge=1, le=250)
        ] = None,
        offset: Annotated[int, Field(description="Starting position for pagination", ge=0)] = 0,
    ) -> dict[str, Any]:
        """List all congressional committees with full details.

        Returns committees from both House and Senate with membership,
        subcommittees, and historical information.
        """
        async with CongressClient(config) as client:
            params: dict[str, Any] = {}
            if from_date:
                params["fromDateTime"] = f"{from_date}T00:00:00Z"
            if to_date:
                params["toDateTime"] = f"{to_date}T23:59:59Z"
            response = await client.get("/committee", params=params, limit=limit, offset=offset)

            def build_endpoint(item: dict[str, Any]) -> str:
                chamber = item.get("chamber", "").lower()
                system_code = item.get("systemCode", "")
                return f"/committee/{chamber}/{system_code}"

            return await client.enrich_list_response(
                response,
                result_key="committees",
                detail_key="committee",
                build_endpoint=build_endpoint,
            )

    @mcp.tool(annotations=READONLY_ANNOTATIONS)
    async def list_committees_by_chamber(
        chamber: Annotated[ChamberLiteral, Field(description="Chamber: house or senate")],
        from_date: Annotated[
            str | None, Field(description="Filter by update date start (YYYY-MM-DD)")
        ] = None,
        to_date: Annotated[
            str | None, Field(description="Filter by update date end (YYYY-MM-DD)")
        ] = None,
        limit: Annotated[
            int | None, Field(description="Maximum results to return (1-250)", ge=1, le=250)
        ] = None,
        offset: Annotated[int, Field(description="Starting position for pagination", ge=0)] = 0,
    ) -> dict[str, Any]:
        """List committees by chamber with full details.

        Returns all committees for the specified chamber with membership,
        subcommittees, and historical information.
        """
        async with CongressClient(config) as client:
            params: dict[str, Any] = {}
            if from_date:
                params["fromDateTime"] = f"{from_date}T00:00:00Z"
            if to_date:
                params["toDateTime"] = f"{to_date}T23:59:59Z"
            response = await client.get(
                f"/committee/{chamber}",
                params=params,
                limit=limit,
                offset=offset,
            )

            def build_endpoint(item: dict[str, Any]) -> str:
                system_code = item.get("systemCode", "")
                return f"/committee/{chamber}/{system_code}"

            return await client.enrich_list_response(
                response,
                result_key="committees",
                detail_key="committee",
                build_endpoint=build_endpoint,
            )

    @mcp.tool(annotations=READONLY_ANNOTATIONS)
    async def list_committees_by_congress(
        congress: Annotated[int, Field(description="Congress number (e.g., 118)", ge=1, le=200)],
        chamber: Annotated[ChamberLiteral, Field(description="Chamber: house or senate")],
        from_date: Annotated[
            str | None, Field(description="Filter by update date start (YYYY-MM-DD)")
        ] = None,
        to_date: Annotated[
            str | None, Field(description="Filter by update date end (YYYY-MM-DD)")
        ] = None,
        limit: Annotated[
            int | None, Field(description="Maximum results to return (1-250)", ge=1, le=250)
        ] = None,
        offset: Annotated[int, Field(description="Starting position for pagination", ge=0)] = 0,
    ) -> dict[str, Any]:
        """List committees for a specific Congress and chamber with full details.

        Committee membership and structure may vary by Congress.
        """
        async with CongressClient(config) as client:
            params: dict[str, Any] = {}
            if from_date:
                params["fromDateTime"] = f"{from_date}T00:00:00Z"
            if to_date:
                params["toDateTime"] = f"{to_date}T23:59:59Z"
            response = await client.get(
                f"/committee/{congress}/{chamber}",
                params=params,
                limit=limit,
                offset=offset,
            )

            def build_endpoint(item: dict[str, Any]) -> str:
                system_code = item.get("systemCode", "")
                return f"/committee/{congress}/{chamber}/{system_code}"

            return await client.enrich_list_response(
                response,
                result_key="committees",
                detail_key="committee",
                build_endpoint=build_endpoint,
            )

    @mcp.tool(annotations=READONLY_ANNOTATIONS)
    async def get_committee(
        chamber: Annotated[ChamberLiteral, Field(description="Chamber: house or senate")],
        committee_code: Annotated[
            str, Field(description="Committee system code (e.g., 'hsju00' for House Judiciary)")
        ],
    ) -> dict[str, Any]:
        """Get detailed information about a specific committee.

        Returns committee details including membership, subcommittees,
        and historical information.
        """
        async with CongressClient(config) as client:
            return await client.get(f"/committee/{chamber}/{committee_code}")

    @mcp.tool(annotations=READONLY_ANNOTATIONS)
    async def get_committee_by_congress(
        congress: Annotated[int, Field(description="Congress number (e.g., 118)", ge=1, le=200)],
        chamber: Annotated[ChamberLiteral, Field(description="Chamber: house or senate")],
        committee_code: Annotated[str, Field(description="Committee system code")],
    ) -> dict[str, Any]:
        """Get committee information for a specific Congress.

        Returns committee composition and details for the specified Congress.
        """
        async with CongressClient(config) as client:
            return await client.get(
                f"/committee/{congress}/{chamber}/{committee_code}"
            )

    @mcp.tool(annotations=READONLY_ANNOTATIONS)
    async def get_committee_bills(
        chamber: Annotated[ChamberLiteral, Field(description="Chamber: house or senate")],
        committee_code: Annotated[str, Field(description="Committee system code")],
        from_date: Annotated[
            str | None, Field(description="Filter by update date start (YYYY-MM-DD)")
        ] = None,
        to_date: Annotated[
            str | None, Field(description="Filter by update date end (YYYY-MM-DD)")
        ] = None,
        limit: Annotated[
            int | None, Field(description="Maximum results to return", ge=1, le=250)
        ] = None,
        offset: Annotated[int, Field(description="Starting position for pagination", ge=0)] = 0,
    ) -> dict[str, Any]:
        """Get bills associated with a committee.

        Returns bills that have been referred to or reported by the committee.
        """
        async with CongressClient(config) as client:
            params: dict[str, Any] = {}
            if from_date:
                params["fromDateTime"] = f"{from_date}T00:00:00Z"
            if to_date:
                params["toDateTime"] = f"{to_date}T23:59:59Z"
            return await client.get(
                f"/committee/{chamber}/{committee_code}/bills",
                params=params,
                limit=limit,
                offset=offset,
            )

    @mcp.tool(annotations=READONLY_ANNOTATIONS)
    async def get_committee_reports_list(
        chamber: Annotated[ChamberLiteral, Field(description="Chamber: house or senate")],
        committee_code: Annotated[str, Field(description="Committee system code")],
        from_date: Annotated[
            str | None, Field(description="Filter by update date start (YYYY-MM-DD)")
        ] = None,
        to_date: Annotated[
            str | None, Field(description="Filter by update date end (YYYY-MM-DD)")
        ] = None,
        limit: Annotated[
            int | None, Field(description="Maximum results to return", ge=1, le=250)
        ] = None,
        offset: Annotated[int, Field(description="Starting position for pagination", ge=0)] = 0,
    ) -> dict[str, Any]:
        """Get reports issued by a committee.

        Returns committee reports including bill reports and oversight reports.
        """
        async with CongressClient(config) as client:
            params: dict[str, Any] = {}
            if from_date:
                params["fromDateTime"] = f"{from_date}T00:00:00Z"
            if to_date:
                params["toDateTime"] = f"{to_date}T23:59:59Z"
            return await client.get(
                f"/committee/{chamber}/{committee_code}/reports",
                params=params,
                limit=limit,
                offset=offset,
            )

    @mcp.tool(annotations=READONLY_ANNOTATIONS)
    async def get_committee_nominations(
        committee_code: Annotated[str, Field(description="Senate committee system code")],
        limit: Annotated[
            int | None, Field(description="Maximum results to return", ge=1, le=250)
        ] = None,
        offset: Annotated[int, Field(description="Starting position for pagination", ge=0)] = 0,
    ) -> dict[str, Any]:
        """Get nominations referred to a Senate committee.

        Note: Only Senate committees consider nominations.
        """
        async with CongressClient(config) as client:
            return await client.get(
                f"/committee/senate/{committee_code}/nominations",
                limit=limit,
                offset=offset,
            )

    @mcp.tool(annotations=READONLY_ANNOTATIONS)
    async def get_committee_house_communications(
        committee_code: Annotated[str, Field(description="House committee system code")],
        limit: Annotated[
            int | None, Field(description="Maximum results to return", ge=1, le=250)
        ] = None,
        offset: Annotated[int, Field(description="Starting position for pagination", ge=0)] = 0,
    ) -> dict[str, Any]:
        """Get House communications referred to a committee.

        Returns executive communications, presidential messages, petitions,
        and memorials sent to the committee.
        """
        async with CongressClient(config) as client:
            return await client.get(
                f"/committee/house/{committee_code}/house-communication",
                limit=limit,
                offset=offset,
            )

    @mcp.tool(annotations=READONLY_ANNOTATIONS)
    async def get_committee_senate_communications(
        committee_code: Annotated[str, Field(description="Senate committee system code")],
        limit: Annotated[
            int | None, Field(description="Maximum results to return", ge=1, le=250)
        ] = None,
        offset: Annotated[int, Field(description="Starting position for pagination", ge=0)] = 0,
    ) -> dict[str, Any]:
        """Get Senate communications referred to a committee.

        Returns executive communications, petitions, memorials, and
        presidential messages sent to the committee.
        """
        async with CongressClient(config) as client:
            return await client.get(
                f"/committee/senate/{committee_code}/senate-communication",
                limit=limit,
                offset=offset,
            )
