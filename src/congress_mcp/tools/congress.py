"""Congress session tools for Congress.gov API."""

from typing import Annotated, Any

from pydantic import Field

from congress_mcp.client import CongressClient
from congress_mcp.config import Config

try:
    from fastmcp import FastMCP
except ImportError:
    FastMCP = Any  # type: ignore[misc, assignment]


def register_congress_tools(mcp: "FastMCP", config: Config) -> None:
    """Register all Congress session tools with the MCP server."""

    @mcp.tool()
    async def list_congresses(
        limit: Annotated[
            int | None, Field(description="Maximum results to return (1-250)", ge=1, le=250)
        ] = None,
        offset: Annotated[int, Field(description="Starting position for pagination", ge=0)] = 0,
    ) -> dict[str, Any]:
        """List all Congresses.

        Returns information about each Congress including number,
        name, start/end dates, and sessions.

        Note: The 1st Congress began in 1789. Each Congress spans two years.
        """
        async with CongressClient(config) as client:
            return await client.get("/congress", limit=limit, offset=offset)

    @mcp.tool()
    async def get_congress(
        congress: Annotated[int, Field(description="Congress number (e.g., 118)", ge=1, le=200)],
    ) -> dict[str, Any]:
        """Get detailed information about a specific Congress.

        Returns Congress details including:
        - Start and end dates
        - Sessions (each Congress has two sessions)
        - Links to related data

        Reference for Congress numbers:
        - 119th Congress: 2025-2027
        - 118th Congress: 2023-2025
        - 117th Congress: 2021-2023
        """
        async with CongressClient(config) as client:
            return await client.get(f"/congress/{congress}")
