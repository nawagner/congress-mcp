"""Committee meeting tools for Congress.gov API."""

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


def register_committee_meeting_tools(mcp: "FastMCP", config: Config) -> None:
    """Register all committee meeting tools with the MCP server."""

    @mcp.tool(annotations=READONLY_ANNOTATIONS)
    async def list_committee_meetings(
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
        """List committee meetings by Congress and chamber.

        Returns scheduled and past committee meetings with full details including
        title, date, time, location, committee, agenda, and related documents.
        """
        async with CongressClient(config) as client:
            params: dict[str, Any] = {}
            if from_date:
                params["fromDateTime"] = f"{from_date}T00:00:00Z"
            if to_date:
                params["toDateTime"] = f"{to_date}T23:59:59Z"
            response = await client.get(
                f"/committee-meeting/{congress}/{chamber}",
                params=params,
                limit=limit,
                offset=offset,
            )

            def build_endpoint(item: dict[str, Any]) -> str:
                event_id = item.get("eventId", "")
                return f"/committee-meeting/{congress}/{chamber}/{event_id}"

            return await client.enrich_list_response(
                response,
                result_key="committeeMeetings",
                detail_key="committeeMeeting",
                build_endpoint=build_endpoint,
            )

    @mcp.tool(annotations=READONLY_ANNOTATIONS)
    async def get_committee_meeting(
        congress: Annotated[int, Field(description="Congress number (e.g., 118)", ge=1, le=200)],
        chamber: Annotated[ChamberLiteral, Field(description="Chamber: house or senate")],
        event_id: Annotated[str, Field(description="Meeting event ID")],
    ) -> dict[str, Any]:
        """Get detailed information about a specific committee meeting.

        Returns meeting details including date, time, location, committee,
        agenda, and related documents.
        """
        async with CongressClient(config) as client:
            return await client.get(
                f"/committee-meeting/{congress}/{chamber}/{event_id}"
            )
