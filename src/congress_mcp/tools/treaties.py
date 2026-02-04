"""Treaty tools for Congress.gov API."""

from typing import Annotated, Any

from pydantic import Field

from congress_mcp.client import CongressClient
from congress_mcp.config import Config

try:
    from fastmcp import FastMCP
except ImportError:
    FastMCP = Any  # type: ignore[misc, assignment]


def register_treaty_tools(mcp: "FastMCP", config: Config) -> None:
    """Register all treaty tools with the MCP server."""

    @mcp.tool()
    async def list_treaties(
        congress: Annotated[
            int | None,
            Field(description="Congress number (e.g., 118). If not provided, lists all treaties.", ge=1, le=200),
        ] = None,
        limit: Annotated[
            int | None, Field(description="Maximum results to return (1-250)", ge=1, le=250)
        ] = None,
        offset: Annotated[int, Field(description="Starting position for pagination", ge=0)] = 0,
    ) -> dict[str, Any]:
        """List treaties submitted to the Senate.

        Treaties require a two-thirds vote in the Senate for ratification.
        """
        async with CongressClient(config) as client:
            endpoint = f"/treaty/{congress}" if congress else "/treaty"
            return await client.get(endpoint, limit=limit, offset=offset)

    @mcp.tool()
    async def get_treaty(
        congress: Annotated[int, Field(description="Congress number (e.g., 118)", ge=1, le=200)],
        treaty_number: Annotated[int, Field(description="Treaty number", ge=1)],
    ) -> dict[str, Any]:
        """Get detailed information about a specific treaty.

        Returns treaty details including title, countries, date transmitted,
        and current status.
        """
        async with CongressClient(config) as client:
            return await client.get(f"/treaty/{congress}/{treaty_number}")

    @mcp.tool()
    async def get_treaty_part(
        congress: Annotated[int, Field(description="Congress number (e.g., 118)", ge=1, le=200)],
        treaty_number: Annotated[int, Field(description="Treaty number", ge=1)],
        treaty_suffix: Annotated[
            str,
            Field(description="Treaty part suffix (e.g., 'A', 'B') for partitioned treaties"),
        ],
    ) -> dict[str, Any]:
        """Get information about a specific part of a partitioned treaty.

        Some treaties are divided into multiple parts for separate consideration.
        """
        async with CongressClient(config) as client:
            return await client.get(f"/treaty/{congress}/{treaty_number}/{treaty_suffix}")

    @mcp.tool()
    async def get_treaty_actions(
        congress: Annotated[int, Field(description="Congress number (e.g., 118)", ge=1, le=200)],
        treaty_number: Annotated[int, Field(description="Treaty number", ge=1)],
        treaty_suffix: Annotated[
            str | None,
            Field(description="Treaty part suffix for partitioned treaties"),
        ] = None,
        limit: Annotated[
            int | None, Field(description="Maximum results to return", ge=1, le=250)
        ] = None,
        offset: Annotated[int, Field(description="Starting position for pagination", ge=0)] = 0,
    ) -> dict[str, Any]:
        """Get actions taken on a treaty.

        Actions include receipt, committee referral, hearings,
        committee votes, floor votes, and ratification.
        """
        async with CongressClient(config) as client:
            if treaty_suffix:
                endpoint = f"/treaty/{congress}/{treaty_number}/{treaty_suffix}/actions"
            else:
                endpoint = f"/treaty/{congress}/{treaty_number}/actions"
            return await client.get(endpoint, limit=limit, offset=offset)

    @mcp.tool()
    async def get_treaty_committees(
        congress: Annotated[int, Field(description="Congress number (e.g., 118)", ge=1, le=200)],
        treaty_number: Annotated[int, Field(description="Treaty number", ge=1)],
        limit: Annotated[
            int | None, Field(description="Maximum results to return", ge=1, le=250)
        ] = None,
        offset: Annotated[int, Field(description="Starting position for pagination", ge=0)] = 0,
    ) -> dict[str, Any]:
        """Get committees assigned to a treaty.

        Treaties are typically referred to the Senate Foreign Relations Committee.
        """
        async with CongressClient(config) as client:
            return await client.get(
                f"/treaty/{congress}/{treaty_number}/committees",
                limit=limit,
                offset=offset,
            )
