"""Committee-related tools for Congress.gov API."""

from typing import Annotated, Any

from pydantic import Field

from congress_mcp.client import CongressClient
from congress_mcp.config import Config
from congress_mcp.types.enums import Chamber

try:
    from fastmcp import FastMCP
except ImportError:
    FastMCP = Any  # type: ignore[misc, assignment]


def register_committee_tools(mcp: "FastMCP", config: Config) -> None:
    """Register all committee-related tools with the MCP server."""

    @mcp.tool()
    async def list_committees(
        limit: Annotated[
            int | None, Field(description="Maximum results to return (1-250)", ge=1, le=250)
        ] = None,
        offset: Annotated[int, Field(description="Starting position for pagination", ge=0)] = 0,
    ) -> dict[str, Any]:
        """List all congressional committees.

        Returns committees from both House and Senate.
        """
        async with CongressClient(config) as client:
            return await client.get("/committee", limit=limit, offset=offset)

    @mcp.tool()
    async def list_committees_by_chamber(
        chamber: Annotated[Chamber, Field(description="Chamber: house or senate")],
        limit: Annotated[
            int | None, Field(description="Maximum results to return (1-250)", ge=1, le=250)
        ] = None,
        offset: Annotated[int, Field(description="Starting position for pagination", ge=0)] = 0,
    ) -> dict[str, Any]:
        """List committees by chamber.

        Returns all committees for the specified chamber.
        """
        async with CongressClient(config) as client:
            return await client.get(
                f"/committee/{chamber.value}",
                limit=limit,
                offset=offset,
            )

    @mcp.tool()
    async def list_committees_by_congress(
        congress: Annotated[int, Field(description="Congress number (e.g., 118)", ge=1, le=200)],
        chamber: Annotated[Chamber, Field(description="Chamber: house or senate")],
        limit: Annotated[
            int | None, Field(description="Maximum results to return (1-250)", ge=1, le=250)
        ] = None,
        offset: Annotated[int, Field(description="Starting position for pagination", ge=0)] = 0,
    ) -> dict[str, Any]:
        """List committees for a specific Congress and chamber.

        Committee membership and structure may vary by Congress.
        """
        async with CongressClient(config) as client:
            return await client.get(
                f"/committee/{congress}/{chamber.value}",
                limit=limit,
                offset=offset,
            )

    @mcp.tool()
    async def get_committee(
        chamber: Annotated[Chamber, Field(description="Chamber: house or senate")],
        committee_code: Annotated[
            str, Field(description="Committee system code (e.g., 'hsju00' for House Judiciary)")
        ],
    ) -> dict[str, Any]:
        """Get detailed information about a specific committee.

        Returns committee details including membership, subcommittees,
        and historical information.
        """
        async with CongressClient(config) as client:
            return await client.get(f"/committee/{chamber.value}/{committee_code}")

    @mcp.tool()
    async def get_committee_by_congress(
        congress: Annotated[int, Field(description="Congress number (e.g., 118)", ge=1, le=200)],
        chamber: Annotated[Chamber, Field(description="Chamber: house or senate")],
        committee_code: Annotated[str, Field(description="Committee system code")],
    ) -> dict[str, Any]:
        """Get committee information for a specific Congress.

        Returns committee composition and details for the specified Congress.
        """
        async with CongressClient(config) as client:
            return await client.get(
                f"/committee/{congress}/{chamber.value}/{committee_code}"
            )

    @mcp.tool()
    async def get_committee_bills(
        chamber: Annotated[Chamber, Field(description="Chamber: house or senate")],
        committee_code: Annotated[str, Field(description="Committee system code")],
        limit: Annotated[
            int | None, Field(description="Maximum results to return", ge=1, le=250)
        ] = None,
        offset: Annotated[int, Field(description="Starting position for pagination", ge=0)] = 0,
    ) -> dict[str, Any]:
        """Get bills associated with a committee.

        Returns bills that have been referred to or reported by the committee.
        """
        async with CongressClient(config) as client:
            return await client.get(
                f"/committee/{chamber.value}/{committee_code}/bills",
                limit=limit,
                offset=offset,
            )

    @mcp.tool()
    async def get_committee_reports_list(
        chamber: Annotated[Chamber, Field(description="Chamber: house or senate")],
        committee_code: Annotated[str, Field(description="Committee system code")],
        limit: Annotated[
            int | None, Field(description="Maximum results to return", ge=1, le=250)
        ] = None,
        offset: Annotated[int, Field(description="Starting position for pagination", ge=0)] = 0,
    ) -> dict[str, Any]:
        """Get reports issued by a committee.

        Returns committee reports including bill reports and oversight reports.
        """
        async with CongressClient(config) as client:
            return await client.get(
                f"/committee/{chamber.value}/{committee_code}/reports",
                limit=limit,
                offset=offset,
            )

    @mcp.tool()
    async def get_committee_nominations(
        committee_code: Annotated[str, Field(description="Senate committee system code")],
        limit: Annotated[
            int | None, Field(description="Maximum results to return", ge=1, le=250)
        ] = None,
        offset: Annotated[int, Field(description="Starting position for pagination", ge=0)] = 0,
    ) -> dict[str, Any]:
        """Get nominations referred to a Senate committee.

        Note: Only Senate committees consider nominations.
        """
        async with CongressClient(config) as client:
            return await client.get(
                f"/committee/senate/{committee_code}/nominations",
                limit=limit,
                offset=offset,
            )

    @mcp.tool()
    async def get_committee_house_communications(
        committee_code: Annotated[str, Field(description="House committee system code")],
        limit: Annotated[
            int | None, Field(description="Maximum results to return", ge=1, le=250)
        ] = None,
        offset: Annotated[int, Field(description="Starting position for pagination", ge=0)] = 0,
    ) -> dict[str, Any]:
        """Get House communications referred to a committee.

        Returns executive communications, presidential messages, petitions,
        and memorials sent to the committee.
        """
        async with CongressClient(config) as client:
            return await client.get(
                f"/committee/house/{committee_code}/house-communication",
                limit=limit,
                offset=offset,
            )

    @mcp.tool()
    async def get_committee_senate_communications(
        committee_code: Annotated[str, Field(description="Senate committee system code")],
        limit: Annotated[
            int | None, Field(description="Maximum results to return", ge=1, le=250)
        ] = None,
        offset: Annotated[int, Field(description="Starting position for pagination", ge=0)] = 0,
    ) -> dict[str, Any]:
        """Get Senate communications referred to a committee.

        Returns executive communications, petitions, memorials, and
        presidential messages sent to the committee.
        """
        async with CongressClient(config) as client:
            return await client.get(
                f"/committee/senate/{committee_code}/senate-communication",
                limit=limit,
                offset=offset,
            )
