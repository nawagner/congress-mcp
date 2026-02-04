"""Nomination tools for Congress.gov API."""

from typing import Annotated, Any

from pydantic import Field

from congress_mcp.client import CongressClient
from congress_mcp.config import Config

try:
    from fastmcp import FastMCP
except ImportError:
    FastMCP = Any  # type: ignore[misc, assignment]


def register_nomination_tools(mcp: "FastMCP", config: Config) -> None:
    """Register all nomination tools with the MCP server."""

    @mcp.tool()
    async def list_nominations(
        congress: Annotated[int, Field(description="Congress number (e.g., 118)", ge=1, le=200)],
        limit: Annotated[
            int | None, Field(description="Maximum results to return (1-250)", ge=1, le=250)
        ] = None,
        offset: Annotated[int, Field(description="Starting position for pagination", ge=0)] = 0,
    ) -> dict[str, Any]:
        """List presidential nominations for a specific Congress.

        Returns nominations submitted to the Senate for confirmation,
        including judicial, executive, and military nominations.
        """
        async with CongressClient(config) as client:
            return await client.get(
                f"/nomination/{congress}",
                limit=limit,
                offset=offset,
            )

    @mcp.tool()
    async def get_nomination(
        congress: Annotated[int, Field(description="Congress number (e.g., 118)", ge=1, le=200)],
        nomination_number: Annotated[int, Field(description="Nomination number", ge=1)],
    ) -> dict[str, Any]:
        """Get detailed information about a specific nomination.

        Returns nomination details including nominee(s), position,
        organization, and current status.
        """
        async with CongressClient(config) as client:
            return await client.get(f"/nomination/{congress}/{nomination_number}")

    @mcp.tool()
    async def get_nomination_nominees(
        congress: Annotated[int, Field(description="Congress number (e.g., 118)", ge=1, le=200)],
        nomination_number: Annotated[int, Field(description="Nomination number", ge=1)],
        ordinal: Annotated[
            int,
            Field(description="Position of nominee within the nomination (1 for first nominee)", ge=1),
        ],
    ) -> dict[str, Any]:
        """Get information about a specific nominee within a nomination.

        Some nominations (especially military promotions) contain multiple
        nominees. Use this to get details about a specific nominee.
        """
        async with CongressClient(config) as client:
            return await client.get(f"/nomination/{congress}/{nomination_number}/{ordinal}")

    @mcp.tool()
    async def get_nomination_actions(
        congress: Annotated[int, Field(description="Congress number (e.g., 118)", ge=1, le=200)],
        nomination_number: Annotated[int, Field(description="Nomination number", ge=1)],
        limit: Annotated[
            int | None, Field(description="Maximum results to return", ge=1, le=250)
        ] = None,
        offset: Annotated[int, Field(description="Starting position for pagination", ge=0)] = 0,
    ) -> dict[str, Any]:
        """Get actions taken on a nomination.

        Actions include receipt, committee referral, hearings,
        committee votes, floor votes, and confirmation/rejection.
        """
        async with CongressClient(config) as client:
            return await client.get(
                f"/nomination/{congress}/{nomination_number}/actions",
                limit=limit,
                offset=offset,
            )

    @mcp.tool()
    async def get_nomination_committees(
        congress: Annotated[int, Field(description="Congress number (e.g., 118)", ge=1, le=200)],
        nomination_number: Annotated[int, Field(description="Nomination number", ge=1)],
        limit: Annotated[
            int | None, Field(description="Maximum results to return", ge=1, le=250)
        ] = None,
        offset: Annotated[int, Field(description="Starting position for pagination", ge=0)] = 0,
    ) -> dict[str, Any]:
        """Get committees assigned to a nomination.

        Returns Senate committees that have jurisdiction over the nomination.
        """
        async with CongressClient(config) as client:
            return await client.get(
                f"/nomination/{congress}/{nomination_number}/committees",
                limit=limit,
                offset=offset,
            )

    @mcp.tool()
    async def get_nomination_hearings(
        congress: Annotated[int, Field(description="Congress number (e.g., 118)", ge=1, le=200)],
        nomination_number: Annotated[int, Field(description="Nomination number", ge=1)],
        limit: Annotated[
            int | None, Field(description="Maximum results to return", ge=1, le=250)
        ] = None,
        offset: Annotated[int, Field(description="Starting position for pagination", ge=0)] = 0,
    ) -> dict[str, Any]:
        """Get printed hearings related to a nomination.

        Returns published hearing transcripts for the nomination.
        """
        async with CongressClient(config) as client:
            return await client.get(
                f"/nomination/{congress}/{nomination_number}/hearings",
                limit=limit,
                offset=offset,
            )
