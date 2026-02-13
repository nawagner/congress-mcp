"""Hearing tools for Congress.gov API."""

from typing import Annotated, Any

from pydantic import Field

from congress_mcp.annotations import READONLY_ANNOTATIONS
from congress_mcp.client import CongressClient
from congress_mcp.config import Config
from congress_mcp.types.enums import Chamber

try:
    from fastmcp import FastMCP
except ImportError:
    FastMCP = Any  # type: ignore[misc, assignment]


def register_hearing_tools(mcp: "FastMCP", config: Config) -> None:
    """Register all hearing tools with the MCP server."""

    @mcp.tool(annotations=READONLY_ANNOTATIONS)
    async def list_hearings(
        congress: Annotated[int, Field(description="Congress number (e.g., 118)", ge=1, le=200)],
        chamber: Annotated[
            Chamber | None,
            Field(
                description="Optional chamber filter: 'house' or 'senate'. Omit to get hearings from both chambers."
            ),
        ] = None,
        limit: Annotated[
            int | None, Field(description="Maximum results to return (1-250)", ge=1, le=250)
        ] = None,
        offset: Annotated[int, Field(description="Starting position for pagination", ge=0)] = 0,
    ) -> dict[str, Any]:
        """List congressional hearings for a given Congress.

        Returns published hearing transcripts with full details including
        title, date, committee, and document links.

        Omit chamber to get hearings from both House and Senate.
        """
        async with CongressClient(config) as client:
            endpoint = (
                f"/hearing/{congress}/{chamber.value}" if chamber else f"/hearing/{congress}"
            )
            response = await client.get(endpoint, limit=limit, offset=offset)

            def build_endpoint(item: dict[str, Any]) -> str:
                jacket_number = item.get("jacketNumber", "")
                item_chamber = chamber.value if chamber else item.get("chamber", "").lower()
                return f"/hearing/{congress}/{item_chamber}/{jacket_number}"

            return await client.enrich_list_response(
                response,
                result_key="hearings",
                detail_key="hearing",
                build_endpoint=build_endpoint,
            )

    @mcp.tool(annotations=READONLY_ANNOTATIONS)
    async def get_hearing(
        congress: Annotated[int, Field(description="Congress number (e.g., 118)", ge=1, le=200)],
        chamber: Annotated[Chamber, Field(description="Chamber: house or senate")],
        jacket_number: Annotated[str, Field(description="Hearing jacket number")],
    ) -> dict[str, Any]:
        """Get detailed information about a specific hearing.

        Returns hearing details including title, date, committee,
        witnesses, and links to transcript.
        """
        async with CongressClient(config) as client:
            return await client.get(f"/hearing/{congress}/{chamber.value}/{jacket_number}")
