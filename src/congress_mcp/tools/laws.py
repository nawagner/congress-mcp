"""Law-related tools for Congress.gov API."""

from typing import Annotated, Any

from pydantic import Field

from congress_mcp.client import CongressClient
from congress_mcp.config import Config
from congress_mcp.types.enums import LawType

try:
    from fastmcp import FastMCP
except ImportError:
    FastMCP = Any  # type: ignore[misc, assignment]


def register_law_tools(mcp: "FastMCP", config: Config) -> None:
    """Register all law-related tools with the MCP server."""

    @mcp.tool()
    async def list_laws(
        congress: Annotated[int, Field(description="Congress number (e.g., 118)", ge=1, le=200)],
        limit: Annotated[
            int | None, Field(description="Maximum results to return (1-250)", ge=1, le=250)
        ] = None,
        offset: Annotated[int, Field(description="Starting position for pagination", ge=0)] = 0,
    ) -> dict[str, Any]:
        """List all laws enacted by a specific Congress.

        Returns both public and private laws with basic metadata.
        """
        async with CongressClient(config) as client:
            return await client.get(
                f"/law/{congress}",
                limit=limit,
                offset=offset,
            )

    @mcp.tool()
    async def list_laws_by_type(
        congress: Annotated[int, Field(description="Congress number (e.g., 118)", ge=1, le=200)],
        law_type: Annotated[
            LawType,
            Field(description="Law type: pub (Public Law) or priv (Private Law)"),
        ],
        limit: Annotated[
            int | None, Field(description="Maximum results to return (1-250)", ge=1, le=250)
        ] = None,
        offset: Annotated[int, Field(description="Starting position for pagination", ge=0)] = 0,
    ) -> dict[str, Any]:
        """List laws filtered by type.

        Law types:
        - pub: Public Law - laws that affect the general public
        - priv: Private Law - laws that affect specific individuals or entities
        """
        async with CongressClient(config) as client:
            return await client.get(
                f"/law/{congress}/{law_type.value}",
                limit=limit,
                offset=offset,
            )

    @mcp.tool()
    async def get_law(
        congress: Annotated[int, Field(description="Congress number (e.g., 118)", ge=1, le=200)],
        law_type: Annotated[LawType, Field(description="Law type: pub or priv")],
        law_number: Annotated[int, Field(description="Law number", ge=1)],
    ) -> dict[str, Any]:
        """Get detailed information about a specific law.

        Returns law details including the originating bill, enactment date,
        and links to the full text.
        """
        async with CongressClient(config) as client:
            return await client.get(f"/law/{congress}/{law_type.value}/{law_number}")
