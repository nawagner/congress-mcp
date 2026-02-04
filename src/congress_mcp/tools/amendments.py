"""Amendment-related tools for Congress.gov API."""

from typing import Annotated, Any

from pydantic import Field

from congress_mcp.client import CongressClient
from congress_mcp.config import Config
from congress_mcp.types.enums import AmendmentType

try:
    from fastmcp import FastMCP
except ImportError:
    FastMCP = Any  # type: ignore[misc, assignment]


def register_amendment_tools(mcp: "FastMCP", config: Config) -> None:
    """Register all amendment-related tools with the MCP server."""

    @mcp.tool()
    async def list_amendments(
        congress: Annotated[int, Field(description="Congress number (e.g., 118)", ge=1, le=200)],
        limit: Annotated[
            int | None, Field(description="Maximum results to return (1-250)", ge=1, le=250)
        ] = None,
        offset: Annotated[int, Field(description="Starting position for pagination", ge=0)] = 0,
    ) -> dict[str, Any]:
        """List all amendments for a specific Congress.

        Returns House and Senate amendments with basic metadata.
        """
        async with CongressClient(config) as client:
            return await client.get(
                f"/amendment/{congress}",
                limit=limit,
                offset=offset,
            )

    @mcp.tool()
    async def list_amendments_by_type(
        congress: Annotated[int, Field(description="Congress number (e.g., 118)", ge=1, le=200)],
        amendment_type: Annotated[
            AmendmentType,
            Field(
                description="Amendment type: hamdt (House), samdt (Senate), suamdt (Senate Unprinted)"
            ),
        ],
        limit: Annotated[
            int | None, Field(description="Maximum results to return (1-250)", ge=1, le=250)
        ] = None,
        offset: Annotated[int, Field(description="Starting position for pagination", ge=0)] = 0,
    ) -> dict[str, Any]:
        """List amendments filtered by type.

        Amendment types:
        - hamdt: House Amendment
        - samdt: Senate Amendment
        - suamdt: Senate Unprinted Amendment
        """
        async with CongressClient(config) as client:
            return await client.get(
                f"/amendment/{congress}/{amendment_type.value}",
                limit=limit,
                offset=offset,
            )

    @mcp.tool()
    async def get_amendment(
        congress: Annotated[int, Field(description="Congress number (e.g., 118)", ge=1, le=200)],
        amendment_type: Annotated[
            AmendmentType, Field(description="Amendment type: hamdt, samdt, or suamdt")
        ],
        amendment_number: Annotated[int, Field(description="Amendment number", ge=1)],
    ) -> dict[str, Any]:
        """Get detailed information about a specific amendment.

        Returns amendment details including the bill being amended,
        sponsor, purpose, and latest action.
        """
        async with CongressClient(config) as client:
            return await client.get(
                f"/amendment/{congress}/{amendment_type.value}/{amendment_number}"
            )

    @mcp.tool()
    async def get_amendment_actions(
        congress: Annotated[int, Field(description="Congress number", ge=1, le=200)],
        amendment_type: Annotated[AmendmentType, Field(description="Amendment type")],
        amendment_number: Annotated[int, Field(description="Amendment number", ge=1)],
        limit: Annotated[
            int | None, Field(description="Maximum results to return", ge=1, le=250)
        ] = None,
        offset: Annotated[int, Field(description="Starting position for pagination", ge=0)] = 0,
    ) -> dict[str, Any]:
        """Get all actions taken on an amendment.

        Actions include submission, consideration, votes, and adoption/rejection.
        """
        async with CongressClient(config) as client:
            return await client.get(
                f"/amendment/{congress}/{amendment_type.value}/{amendment_number}/actions",
                limit=limit,
                offset=offset,
            )

    @mcp.tool()
    async def get_amendment_cosponsors(
        congress: Annotated[int, Field(description="Congress number", ge=1, le=200)],
        amendment_type: Annotated[AmendmentType, Field(description="Amendment type")],
        amendment_number: Annotated[int, Field(description="Amendment number", ge=1)],
        limit: Annotated[
            int | None, Field(description="Maximum results to return", ge=1, le=250)
        ] = None,
        offset: Annotated[int, Field(description="Starting position for pagination", ge=0)] = 0,
    ) -> dict[str, Any]:
        """Get cosponsors of an amendment.

        Returns members who have cosponsored the amendment.
        """
        async with CongressClient(config) as client:
            return await client.get(
                f"/amendment/{congress}/{amendment_type.value}/{amendment_number}/cosponsors",
                limit=limit,
                offset=offset,
            )

    @mcp.tool()
    async def get_amendment_amendments(
        congress: Annotated[int, Field(description="Congress number", ge=1, le=200)],
        amendment_type: Annotated[AmendmentType, Field(description="Amendment type")],
        amendment_number: Annotated[int, Field(description="Amendment number", ge=1)],
        limit: Annotated[
            int | None, Field(description="Maximum results to return", ge=1, le=250)
        ] = None,
        offset: Annotated[int, Field(description="Starting position for pagination", ge=0)] = 0,
    ) -> dict[str, Any]:
        """Get amendments to an amendment (second-degree amendments).

        Returns any amendments that have been proposed to modify this amendment.
        """
        async with CongressClient(config) as client:
            return await client.get(
                f"/amendment/{congress}/{amendment_type.value}/{amendment_number}/amendments",
                limit=limit,
                offset=offset,
            )

    @mcp.tool()
    async def get_amendment_text(
        congress: Annotated[int, Field(description="Congress number", ge=1, le=200)],
        amendment_type: Annotated[AmendmentType, Field(description="Amendment type")],
        amendment_number: Annotated[int, Field(description="Amendment number", ge=1)],
    ) -> dict[str, Any]:
        """Get text versions of an amendment.

        Note: Amendment text is available starting from the 117th Congress.
        Returns links to available text formats.
        """
        async with CongressClient(config) as client:
            return await client.get(
                f"/amendment/{congress}/{amendment_type.value}/{amendment_number}/text"
            )
