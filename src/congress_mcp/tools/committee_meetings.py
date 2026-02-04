"""Committee meeting tools for Congress.gov API."""

from typing import Annotated, Any

from pydantic import Field

from congress_mcp.client import CongressClient
from congress_mcp.config import Config
from congress_mcp.types.enums import Chamber

try:
    from fastmcp import FastMCP
except ImportError:
    FastMCP = Any  # type: ignore[misc, assignment]


def register_committee_meeting_tools(mcp: "FastMCP", config: Config) -> None:
    """Register all committee meeting tools with the MCP server."""

    @mcp.tool()
    async def list_committee_meetings(
        congress: Annotated[int, Field(description="Congress number (e.g., 118)", ge=1, le=200)],
        chamber: Annotated[Chamber, Field(description="Chamber: house or senate")],
        limit: Annotated[
            int | None, Field(description="Maximum results to return (1-250)", ge=1, le=250)
        ] = None,
        offset: Annotated[int, Field(description="Starting position for pagination", ge=0)] = 0,
    ) -> dict[str, Any]:
        """List committee meetings by Congress and chamber.

        Returns scheduled and past committee meetings including
        hearings, markups, and business meetings.
        """
        async with CongressClient(config) as client:
            return await client.get(
                f"/committee-meeting/{congress}/{chamber.value}",
                limit=limit,
                offset=offset,
            )

    @mcp.tool()
    async def get_committee_meeting(
        congress: Annotated[int, Field(description="Congress number (e.g., 118)", ge=1, le=200)],
        chamber: Annotated[Chamber, Field(description="Chamber: house or senate")],
        event_id: Annotated[str, Field(description="Meeting event ID")],
    ) -> dict[str, Any]:
        """Get detailed information about a specific committee meeting.

        Returns meeting details including date, time, location, committee,
        agenda, and related documents.
        """
        async with CongressClient(config) as client:
            return await client.get(
                f"/committee-meeting/{congress}/{chamber.value}/{event_id}"
            )
