"""House requirement tools for Congress.gov API."""

from typing import Annotated, Any

from pydantic import Field

from congress_mcp.client import CongressClient
from congress_mcp.config import Config

try:
    from fastmcp import FastMCP
except ImportError:
    FastMCP = Any  # type: ignore[misc, assignment]


def register_house_requirement_tools(mcp: "FastMCP", config: Config) -> None:
    """Register all House requirement tools with the MCP server."""

    @mcp.tool()
    async def list_house_requirements(
        limit: Annotated[
            int | None, Field(description="Maximum results to return (1-250)", ge=1, le=250)
        ] = None,
        offset: Annotated[int, Field(description="Starting position for pagination", ge=0)] = 0,
    ) -> dict[str, Any]:
        """List House requirements.

        House requirements are statutory reporting requirements that
        federal agencies must fulfill by submitting reports to Congress.
        """
        async with CongressClient(config) as client:
            return await client.get("/house-requirement", limit=limit, offset=offset)

    @mcp.tool()
    async def get_house_requirement(
        requirement_number: Annotated[int, Field(description="Requirement number", ge=1)],
    ) -> dict[str, Any]:
        """Get detailed information about a specific House requirement.

        Returns requirement details including the originating statute,
        agency, frequency, and description.
        """
        async with CongressClient(config) as client:
            return await client.get(f"/house-requirement/{requirement_number}")

    @mcp.tool()
    async def get_house_requirement_communications(
        requirement_number: Annotated[int, Field(description="Requirement number", ge=1)],
        limit: Annotated[
            int | None, Field(description="Maximum results to return", ge=1, le=250)
        ] = None,
        offset: Annotated[int, Field(description="Starting position for pagination", ge=0)] = 0,
    ) -> dict[str, Any]:
        """Get communications that match a House requirement.

        Returns executive communications submitted in fulfillment
        of the requirement.
        """
        async with CongressClient(config) as client:
            return await client.get(
                f"/house-requirement/{requirement_number}/matching-communications",
                limit=limit,
                offset=offset,
            )
