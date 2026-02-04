"""Communication tools for Congress.gov API."""

from typing import Annotated, Any

from pydantic import Field

from congress_mcp.client import CongressClient
from congress_mcp.config import Config
from congress_mcp.types.enums import HouseCommunicationType, SenateCommunicationType

try:
    from fastmcp import FastMCP
except ImportError:
    FastMCP = Any  # type: ignore[misc, assignment]


def register_communication_tools(mcp: "FastMCP", config: Config) -> None:
    """Register all communication tools with the MCP server."""

    @mcp.tool()
    async def list_house_communications(
        congress: Annotated[int, Field(description="Congress number (e.g., 118)", ge=1, le=200)],
        communication_type: Annotated[
            HouseCommunicationType,
            Field(
                description="Communication type: ec (Executive), pm (Presidential Message), pt (Petition), ml (Memorial)"
            ),
        ],
        limit: Annotated[
            int | None, Field(description="Maximum results to return (1-250)", ge=1, le=250)
        ] = None,
        offset: Annotated[int, Field(description="Starting position for pagination", ge=0)] = 0,
    ) -> dict[str, Any]:
        """List House communications by Congress and type.

        Communication types:
        - ec: Executive Communication
        - pm: Presidential Message
        - pt: Petition
        - ml: Memorial
        """
        async with CongressClient(config) as client:
            return await client.get(
                f"/house-communication/{congress}/{communication_type.value}",
                limit=limit,
                offset=offset,
            )

    @mcp.tool()
    async def get_house_communication(
        congress: Annotated[int, Field(description="Congress number (e.g., 118)", ge=1, le=200)],
        communication_type: Annotated[
            HouseCommunicationType, Field(description="Communication type: ec, pm, pt, or ml")
        ],
        communication_number: Annotated[int, Field(description="Communication number", ge=1)],
    ) -> dict[str, Any]:
        """Get detailed information about a specific House communication.

        Returns communication details including sender, subject,
        and committee referral.
        """
        async with CongressClient(config) as client:
            return await client.get(
                f"/house-communication/{congress}/{communication_type.value}/{communication_number}"
            )

    @mcp.tool()
    async def list_senate_communications(
        congress: Annotated[int, Field(description="Congress number (e.g., 118)", ge=1, le=200)],
        communication_type: Annotated[
            SenateCommunicationType,
            Field(
                description="Communication type: ec (Executive), pom (Petition/Memorial), pm (Presidential Message)"
            ),
        ],
        limit: Annotated[
            int | None, Field(description="Maximum results to return (1-250)", ge=1, le=250)
        ] = None,
        offset: Annotated[int, Field(description="Starting position for pagination", ge=0)] = 0,
    ) -> dict[str, Any]:
        """List Senate communications by Congress and type.

        Communication types:
        - ec: Executive Communication
        - pom: Petition or Memorial
        - pm: Presidential Message
        """
        async with CongressClient(config) as client:
            return await client.get(
                f"/senate-communication/{congress}/{communication_type.value}",
                limit=limit,
                offset=offset,
            )

    @mcp.tool()
    async def get_senate_communication(
        congress: Annotated[int, Field(description="Congress number (e.g., 118)", ge=1, le=200)],
        communication_type: Annotated[
            SenateCommunicationType, Field(description="Communication type: ec, pom, or pm")
        ],
        communication_number: Annotated[int, Field(description="Communication number", ge=1)],
    ) -> dict[str, Any]:
        """Get detailed information about a specific Senate communication.

        Returns communication details including sender, subject,
        and committee referral.
        """
        async with CongressClient(config) as client:
            return await client.get(
                f"/senate-communication/{congress}/{communication_type.value}/{communication_number}"
            )
