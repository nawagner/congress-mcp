"""Law-related tools for Congress.gov API."""

from typing import Annotated, Any

from pydantic import Field

from congress_mcp.annotations import READONLY_ANNOTATIONS
from congress_mcp.client import CongressClient
from congress_mcp.config import Config
from congress_mcp.types.enums import LawTypeLiteral

try:
    from fastmcp import FastMCP
except ImportError:
    FastMCP = Any  # type: ignore[misc, assignment]


def register_law_tools(mcp: "FastMCP", config: Config) -> None:
    """Register all law-related tools with the MCP server."""

    @mcp.tool(annotations=READONLY_ANNOTATIONS)
    async def list_laws(
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
        """List all laws enacted by a specific Congress with full details.

        Returns both public and private laws with originating bill info,
        enactment dates, and text links.
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
                f"/law/{congress}",
                params=params,
                limit=limit,
                offset=offset,
            )

            def build_endpoint(item: dict[str, Any]) -> str:
                law_type = item.get("type", "").lower()
                law_number = item.get("number", "")
                return f"/law/{congress}/{law_type}/{law_number}"

            return await client.enrich_list_response(
                response,
                result_key="laws",
                detail_key="law",
                build_endpoint=build_endpoint,
            )

    @mcp.tool(annotations=READONLY_ANNOTATIONS)
    async def list_laws_by_type(
        congress: Annotated[int, Field(description="Congress number (e.g., 118)", ge=1, le=200)],
        law_type: Annotated[
            LawTypeLiteral,
            Field(description="Law type: pub (Public Law) or priv (Private Law)"),
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
        """List laws filtered by type with full details.

        Law types:
        - pub: Public Law - laws that affect the general public
        - priv: Private Law - laws that affect specific individuals or entities
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
                f"/law/{congress}/{law_type}",
                params=params,
                limit=limit,
                offset=offset,
            )

            def build_endpoint(item: dict[str, Any]) -> str:
                law_number = item.get("number", "")
                return f"/law/{congress}/{law_type}/{law_number}"

            return await client.enrich_list_response(
                response,
                result_key="laws",
                detail_key="law",
                build_endpoint=build_endpoint,
            )

    @mcp.tool(annotations=READONLY_ANNOTATIONS)
    async def get_law(
        congress: Annotated[int, Field(description="Congress number (e.g., 118)", ge=1, le=200)],
        law_type: Annotated[LawTypeLiteral, Field(description="Law type: pub or priv")],
        law_number: Annotated[int, Field(description="Law number", ge=1)],
    ) -> dict[str, Any]:
        """Get detailed information about a specific law.

        Returns law details including the originating bill, enactment date,
        and links to the full text.
        """
        async with CongressClient(config) as client:
            return await client.get(f"/law/{congress}/{law_type}/{law_number}")
