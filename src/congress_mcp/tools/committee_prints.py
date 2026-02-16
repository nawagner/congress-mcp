"""Committee print tools for Congress.gov API."""

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


def register_committee_print_tools(mcp: "FastMCP", config: Config) -> None:
    """Register all committee print tools with the MCP server."""

    @mcp.tool(annotations=READONLY_ANNOTATIONS)
    async def list_committee_prints(
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
        """List committee prints by Congress and chamber with full details.

        Committee prints are documents published by committees that are
        not reports, such as studies, compilations, and research materials.
        """
        async with CongressClient(config) as client:
            params: dict[str, Any] = {}
            if from_date:
                params["fromDateTime"] = f"{from_date}T00:00:00Z"
            if to_date:
                params["toDateTime"] = f"{to_date}T23:59:59Z"
            response = await client.get(
                f"/committee-print/{congress}/{chamber}",
                params=params,
                limit=limit,
                offset=offset,
            )

            def build_endpoint(item: dict[str, Any]) -> str:
                jacket_number = item.get("jacketNumber", "")
                return f"/committee-print/{congress}/{chamber}/{jacket_number}"

            return await client.enrich_list_response(
                response,
                result_key="committeePrints",
                detail_key="committeePrint",
                build_endpoint=build_endpoint,
            )

    @mcp.tool(annotations=READONLY_ANNOTATIONS)
    async def get_committee_print(
        congress: Annotated[int, Field(description="Congress number (e.g., 118)", ge=1, le=200)],
        chamber: Annotated[ChamberLiteral, Field(description="Chamber: house or senate")],
        jacket_number: Annotated[str, Field(description="Print jacket number")],
    ) -> dict[str, Any]:
        """Get detailed information about a specific committee print.

        Returns print details including title, committee, and publication date.
        """
        async with CongressClient(config) as client:
            return await client.get(
                f"/committee-print/{congress}/{chamber}/{jacket_number}"
            )

    @mcp.tool(annotations=READONLY_ANNOTATIONS)
    async def get_committee_print_text(
        congress: Annotated[int, Field(description="Congress number (e.g., 118)", ge=1, le=200)],
        chamber: Annotated[ChamberLiteral, Field(description="Chamber: house or senate")],
        jacket_number: Annotated[str, Field(description="Print jacket number")],
    ) -> dict[str, Any]:
        """Get text versions of a committee print.

        Returns links to available text formats.
        """
        async with CongressClient(config) as client:
            return await client.get(
                f"/committee-print/{congress}/{chamber}/{jacket_number}/text"
            )
