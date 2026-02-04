"""Committee print tools for Congress.gov API."""

from typing import Annotated, Any

from pydantic import Field

from congress_mcp.client import CongressClient
from congress_mcp.config import Config
from congress_mcp.types.enums import Chamber

try:
    from fastmcp import FastMCP
except ImportError:
    FastMCP = Any  # type: ignore[misc, assignment]


def register_committee_print_tools(mcp: "FastMCP", config: Config) -> None:
    """Register all committee print tools with the MCP server."""

    @mcp.tool()
    async def list_committee_prints(
        congress: Annotated[int, Field(description="Congress number (e.g., 118)", ge=1, le=200)],
        chamber: Annotated[Chamber, Field(description="Chamber: house or senate")],
        limit: Annotated[
            int | None, Field(description="Maximum results to return (1-250)", ge=1, le=250)
        ] = None,
        offset: Annotated[int, Field(description="Starting position for pagination", ge=0)] = 0,
    ) -> dict[str, Any]:
        """List committee prints by Congress and chamber.

        Committee prints are documents published by committees that are
        not reports, such as studies, compilations, and research materials.
        """
        async with CongressClient(config) as client:
            return await client.get(
                f"/committee-print/{congress}/{chamber.value}",
                limit=limit,
                offset=offset,
            )

    @mcp.tool()
    async def get_committee_print(
        congress: Annotated[int, Field(description="Congress number (e.g., 118)", ge=1, le=200)],
        chamber: Annotated[Chamber, Field(description="Chamber: house or senate")],
        jacket_number: Annotated[str, Field(description="Print jacket number")],
    ) -> dict[str, Any]:
        """Get detailed information about a specific committee print.

        Returns print details including title, committee, and publication date.
        """
        async with CongressClient(config) as client:
            return await client.get(
                f"/committee-print/{congress}/{chamber.value}/{jacket_number}"
            )

    @mcp.tool()
    async def get_committee_print_text(
        congress: Annotated[int, Field(description="Congress number (e.g., 118)", ge=1, le=200)],
        chamber: Annotated[Chamber, Field(description="Chamber: house or senate")],
        jacket_number: Annotated[str, Field(description="Print jacket number")],
    ) -> dict[str, Any]:
        """Get text versions of a committee print.

        Returns links to available text formats.
        """
        async with CongressClient(config) as client:
            return await client.get(
                f"/committee-print/{congress}/{chamber.value}/{jacket_number}/text"
            )
