"""Member-related tools for Congress.gov API."""

from typing import Annotated, Any

from pydantic import Field

from congress_mcp.annotations import READONLY_ANNOTATIONS
from congress_mcp.client import CongressClient
from congress_mcp.config import Config

try:
    from fastmcp import FastMCP
except ImportError:
    FastMCP = Any  # type: ignore[misc, assignment]


def register_member_tools(mcp: "FastMCP", config: Config) -> None:
    """Register all member-related tools with the MCP server."""

    @mcp.tool(annotations=READONLY_ANNOTATIONS)
    async def list_members(
        from_date: Annotated[
            str | None, Field(description="Filter by update date start (YYYY-MM-DD)")
        ] = None,
        to_date: Annotated[
            str | None, Field(description="Filter by update date end (YYYY-MM-DD)")
        ] = None,
        sort: Annotated[
            str | None, Field(description="Sort order: updateDate+asc or updateDate+desc")
        ] = None,
        limit: Annotated[
            int | None, Field(description="Maximum results to return (1-250)", ge=1, le=250)
        ] = None,
        offset: Annotated[int, Field(description="Starting position for pagination", ge=0)] = 0,
        current_member: Annotated[
            bool | None, Field(description="Filter by current membership status")
        ] = None,
    ) -> dict[str, Any]:
        """List all members of Congress with full details.

        Returns member data including biographical info, party affiliation,
        terms served, leadership positions, and committee assignments.
        """
        async with CongressClient(config) as client:
            params: dict[str, Any] = {}
            if current_member is not None:
                params["currentMember"] = str(current_member).lower()
            if from_date:
                params["fromDateTime"] = f"{from_date}T00:00:00Z"
            if to_date:
                params["toDateTime"] = f"{to_date}T23:59:59Z"
            if sort:
                params["sort"] = sort
            response = await client.get("/member", params=params, limit=limit, offset=offset)

            def build_endpoint(item: dict[str, Any]) -> str:
                bioguide_id = item.get("bioguideId", "")
                return f"/member/{bioguide_id}"

            return await client.enrich_list_response(
                response,
                result_key="members",
                detail_key="member",
                build_endpoint=build_endpoint,
            )

    @mcp.tool(annotations=READONLY_ANNOTATIONS)
    async def get_member(
        bioguide_id: Annotated[
            str, Field(description="Member bioguide ID (e.g., 'P000197' for Nancy Pelosi)")
        ],
    ) -> dict[str, Any]:
        """Get detailed information about a specific member of Congress.

        Returns biographical data, party affiliation, terms served,
        leadership positions, and committee assignments.
        """
        async with CongressClient(config) as client:
            return await client.get(f"/member/{bioguide_id}")

    @mcp.tool(annotations=READONLY_ANNOTATIONS)
    async def get_member_sponsored_legislation(
        bioguide_id: Annotated[str, Field(description="Member bioguide ID")],
        limit: Annotated[
            int | None, Field(description="Maximum results to return", ge=1, le=250)
        ] = None,
        offset: Annotated[int, Field(description="Starting position for pagination", ge=0)] = 0,
    ) -> dict[str, Any]:
        """Get legislation sponsored by a member.

        Returns bills and resolutions where the member is the primary sponsor.
        """
        async with CongressClient(config) as client:
            return await client.get(
                f"/member/{bioguide_id}/sponsored-legislation",
                limit=limit,
                offset=offset,
            )

    @mcp.tool(annotations=READONLY_ANNOTATIONS)
    async def get_member_cosponsored_legislation(
        bioguide_id: Annotated[str, Field(description="Member bioguide ID")],
        limit: Annotated[
            int | None, Field(description="Maximum results to return", ge=1, le=250)
        ] = None,
        offset: Annotated[int, Field(description="Starting position for pagination", ge=0)] = 0,
    ) -> dict[str, Any]:
        """Get legislation cosponsored by a member.

        Returns bills and resolutions where the member is a cosponsor.
        """
        async with CongressClient(config) as client:
            return await client.get(
                f"/member/{bioguide_id}/cosponsored-legislation",
                limit=limit,
                offset=offset,
            )

    @mcp.tool(annotations=READONLY_ANNOTATIONS)
    async def list_members_by_congress(
        congress: Annotated[int, Field(description="Congress number (e.g., 118)", ge=1, le=200)],
        from_date: Annotated[
            str | None, Field(description="Filter by update date start (YYYY-MM-DD)")
        ] = None,
        to_date: Annotated[
            str | None, Field(description="Filter by update date end (YYYY-MM-DD)")
        ] = None,
        sort: Annotated[
            str | None, Field(description="Sort order: updateDate+asc or updateDate+desc")
        ] = None,
        limit: Annotated[
            int | None, Field(description="Maximum results to return", ge=1, le=250)
        ] = None,
        offset: Annotated[int, Field(description="Starting position for pagination", ge=0)] = 0,
        current_member: Annotated[
            bool | None, Field(description="Filter by current membership status")
        ] = None,
    ) -> dict[str, Any]:
        """List members who served in a specific Congress with full details.

        Use current_member=true to get only current serving members,
        or current_member=false for historical members.
        """
        async with CongressClient(config) as client:
            params: dict[str, Any] = {}
            if current_member is not None:
                params["currentMember"] = str(current_member).lower()
            if from_date:
                params["fromDateTime"] = f"{from_date}T00:00:00Z"
            if to_date:
                params["toDateTime"] = f"{to_date}T23:59:59Z"
            if sort:
                params["sort"] = sort
            response = await client.get(
                f"/member/congress/{congress}",
                params=params,
                limit=limit,
                offset=offset,
            )

            def build_endpoint(item: dict[str, Any]) -> str:
                bioguide_id = item.get("bioguideId", "")
                return f"/member/{bioguide_id}"

            return await client.enrich_list_response(
                response,
                result_key="members",
                detail_key="member",
                build_endpoint=build_endpoint,
            )

    @mcp.tool(annotations=READONLY_ANNOTATIONS)
    async def list_members_by_state(
        state: Annotated[str, Field(description="Two-letter state code (e.g., 'CA', 'NY', 'TX')")],
        from_date: Annotated[
            str | None, Field(description="Filter by update date start (YYYY-MM-DD)")
        ] = None,
        to_date: Annotated[
            str | None, Field(description="Filter by update date end (YYYY-MM-DD)")
        ] = None,
        sort: Annotated[
            str | None, Field(description="Sort order: updateDate+asc or updateDate+desc")
        ] = None,
        limit: Annotated[
            int | None, Field(description="Maximum results to return", ge=1, le=250)
        ] = None,
        offset: Annotated[int, Field(description="Starting position for pagination", ge=0)] = 0,
        current_member: Annotated[
            bool | None, Field(description="Filter by current membership status")
        ] = None,
    ) -> dict[str, Any]:
        """List members from a specific state with full details.

        Returns both senators and representatives from the state.
        """
        async with CongressClient(config) as client:
            params: dict[str, Any] = {}
            if current_member is not None:
                params["currentMember"] = str(current_member).lower()
            if from_date:
                params["fromDateTime"] = f"{from_date}T00:00:00Z"
            if to_date:
                params["toDateTime"] = f"{to_date}T23:59:59Z"
            if sort:
                params["sort"] = sort
            response = await client.get(
                f"/member/{state.upper()}",
                params=params,
                limit=limit,
                offset=offset,
            )

            def build_endpoint(item: dict[str, Any]) -> str:
                bioguide_id = item.get("bioguideId", "")
                return f"/member/{bioguide_id}"

            return await client.enrich_list_response(
                response,
                result_key="members",
                detail_key="member",
                build_endpoint=build_endpoint,
            )

    @mcp.tool(annotations=READONLY_ANNOTATIONS)
    async def list_members_by_state_and_district(
        state: Annotated[str, Field(description="Two-letter state code (e.g., 'CA')")],
        district: Annotated[
            int, Field(description="Congressional district number (0 for at-large)", ge=0)
        ],
        from_date: Annotated[
            str | None, Field(description="Filter by update date start (YYYY-MM-DD)")
        ] = None,
        to_date: Annotated[
            str | None, Field(description="Filter by update date end (YYYY-MM-DD)")
        ] = None,
        sort: Annotated[
            str | None, Field(description="Sort order: updateDate+asc or updateDate+desc")
        ] = None,
        limit: Annotated[
            int | None, Field(description="Maximum results to return", ge=1, le=250)
        ] = None,
        offset: Annotated[int, Field(description="Starting position for pagination", ge=0)] = 0,
        current_member: Annotated[
            bool | None, Field(description="Filter by current membership status")
        ] = None,
    ) -> dict[str, Any]:
        """List representatives from a specific congressional district with full details.

        District 0 represents at-large representatives.
        Use list_members_by_state for senators.
        """
        async with CongressClient(config) as client:
            params: dict[str, Any] = {}
            if current_member is not None:
                params["currentMember"] = str(current_member).lower()
            if from_date:
                params["fromDateTime"] = f"{from_date}T00:00:00Z"
            if to_date:
                params["toDateTime"] = f"{to_date}T23:59:59Z"
            if sort:
                params["sort"] = sort
            response = await client.get(
                f"/member/{state.upper()}/{district}",
                params=params,
                limit=limit,
                offset=offset,
            )

            def build_endpoint(item: dict[str, Any]) -> str:
                bioguide_id = item.get("bioguideId", "")
                return f"/member/{bioguide_id}"

            return await client.enrich_list_response(
                response,
                result_key="members",
                detail_key="member",
                build_endpoint=build_endpoint,
            )
