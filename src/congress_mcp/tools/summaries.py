"""Summary tools for Congress.gov API."""

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


def register_summary_tools(mcp: "FastMCP", config: Config) -> None:
    """Register all summary tools with the MCP server."""

    @mcp.tool(annotations=READONLY_ANNOTATIONS)
    async def list_summaries(
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
        """List recent bill summaries.

        Summaries are written by the Congressional Research Service (CRS)
        and describe bill content at various legislative stages.

        Note: Date filtering (from_date/to_date) is required to get results.
        Queries without a date range return zero results.
        """
        async with CongressClient(config) as client:
            params: dict[str, Any] = {}
            if from_date:
                params["fromDateTime"] = f"{from_date}T00:00:00Z"
            if to_date:
                params["toDateTime"] = f"{to_date}T23:59:59Z"
            if sort:
                params["sort"] = sort
            return await client.get("/summaries", params=params, limit=limit, offset=offset)

    @mcp.tool(annotations=READONLY_ANNOTATIONS)
    async def list_summaries_by_congress(
        congress: Annotated[int, Field(description="Congress number (e.g., 118)", ge=1, le=200)],
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
        """List bill summaries for a specific Congress.

        Returns CRS summaries for bills introduced in the specified Congress.

        Note: Date filtering (from_date/to_date) is required to get results.
        Queries without a date range return zero results.
        """
        async with CongressClient(config) as client:
            params: dict[str, Any] = {}
            if from_date:
                params["fromDateTime"] = f"{from_date}T00:00:00Z"
            if to_date:
                params["toDateTime"] = f"{to_date}T23:59:59Z"
            if sort:
                params["sort"] = sort
            return await client.get(
                f"/summaries/{congress}",
                params=params,
                limit=limit,
                offset=offset,
            )

    @mcp.tool(annotations=READONLY_ANNOTATIONS)
    async def list_summaries_by_type(
        congress: Annotated[int, Field(description="Congress number (e.g., 118)", ge=1, le=200)],
        bill_type: Annotated[
            BillTypeLiteral,
            Field(description="REQUIRED bill type string. Must be one of: hr, s, hjres, sjres, hconres, sconres, hres, sres. Example: 'hr' for H.R. bills"),
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
        """List bill summaries filtered by Congress and bill type.

        Returns CRS summaries for the specified type of legislation.

        Note: Date filtering (from_date/to_date) is required to get results.
        Queries without a date range return zero results.
        """
        async with CongressClient(config) as client:
            params: dict[str, Any] = {}
            if from_date:
                params["fromDateTime"] = f"{from_date}T00:00:00Z"
            if to_date:
                params["toDateTime"] = f"{to_date}T23:59:59Z"
            if sort:
                params["sort"] = sort
            return await client.get(
                f"/summaries/{congress}/{bill_type}",
                params=params,
                limit=limit,
                offset=offset,
            )
