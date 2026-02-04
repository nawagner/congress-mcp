"""Vote tools for Congress.gov API."""

from typing import Annotated, Any

from pydantic import Field

from congress_mcp.client import CongressClient
from congress_mcp.config import Config

try:
    from fastmcp import FastMCP
except ImportError:
    FastMCP = Any  # type: ignore[misc, assignment]


def register_vote_tools(mcp: "FastMCP", config: Config) -> None:
    """Register all vote tools with the MCP server."""

    @mcp.tool()
    async def list_house_votes(
        congress: Annotated[int, Field(description="Congress number (e.g., 118)", ge=1, le=200)],
        session: Annotated[int, Field(description="Session number (1 or 2)", ge=1, le=2)],
        limit: Annotated[
            int | None, Field(description="Maximum results to return (1-250)", ge=1, le=250)
        ] = None,
        offset: Annotated[int, Field(description="Starting position for pagination", ge=0)] = 0,
    ) -> dict[str, Any]:
        """List House roll call votes for a Congress and session.

        Returns House floor votes with vote number, date, question, and result.
        """
        async with CongressClient(config) as client:
            return await client.get(
                f"/house-vote/{congress}/{session}",
                limit=limit,
                offset=offset,
            )

    @mcp.tool()
    async def get_house_vote(
        congress: Annotated[int, Field(description="Congress number (e.g., 118)", ge=1, le=200)],
        session: Annotated[int, Field(description="Session number (1 or 2)", ge=1, le=2)],
        roll_call_number: Annotated[int, Field(description="Roll call vote number", ge=1)],
    ) -> dict[str, Any]:
        """Get detailed information about a specific House roll call vote.

        Note: This endpoint is in beta and may have limited data.

        Returns vote details including the question, result, date,
        and vote counts (yea/nay/present/not voting).
        """
        async with CongressClient(config) as client:
            return await client.get(
                f"/house-vote/{congress}/{session}/{roll_call_number}"
            )

    @mcp.tool()
    async def get_house_vote_members(
        congress: Annotated[int, Field(description="Congress number (e.g., 118)", ge=1, le=200)],
        session: Annotated[int, Field(description="Session number (1 or 2)", ge=1, le=2)],
        roll_call_number: Annotated[int, Field(description="Roll call vote number", ge=1)],
        limit: Annotated[
            int | None, Field(description="Maximum results to return", ge=1, le=250)
        ] = None,
        offset: Annotated[int, Field(description="Starting position for pagination", ge=0)] = 0,
    ) -> dict[str, Any]:
        """Get individual member votes for a House roll call vote.

        Note: This endpoint is in beta and may have limited data.

        Returns how each member voted (yea, nay, present, or not voting).
        """
        async with CongressClient(config) as client:
            return await client.get(
                f"/house-vote/{congress}/{session}/{roll_call_number}/members",
                limit=limit,
                offset=offset,
            )
