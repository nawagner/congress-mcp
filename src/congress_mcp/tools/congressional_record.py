"""Congressional Record tools for Congress.gov API."""

from typing import Annotated, Any

from pydantic import Field

from congress_mcp.client import CongressClient
from congress_mcp.config import Config

try:
    from fastmcp import FastMCP
except ImportError:
    FastMCP = Any  # type: ignore[misc, assignment]


def register_congressional_record_tools(mcp: "FastMCP", config: Config) -> None:
    """Register all Congressional Record tools with the MCP server."""

    @mcp.tool()
    async def list_daily_congressional_record(
        limit: Annotated[
            int | None, Field(description="Maximum results to return (1-250)", ge=1, le=250)
        ] = None,
        offset: Annotated[int, Field(description="Starting position for pagination", ge=0)] = 0,
    ) -> dict[str, Any]:
        """List daily Congressional Record issues.

        The Congressional Record is the official daily record of the
        proceedings and debates of Congress.
        """
        async with CongressClient(config) as client:
            return await client.get(
                "/daily-congressional-record",
                limit=limit,
                offset=offset,
            )

    @mcp.tool()
    async def list_daily_congressional_record_by_volume(
        volume_number: Annotated[int, Field(description="Volume number", ge=1)],
        limit: Annotated[
            int | None, Field(description="Maximum results to return (1-250)", ge=1, le=250)
        ] = None,
        offset: Annotated[int, Field(description="Starting position for pagination", ge=0)] = 0,
    ) -> dict[str, Any]:
        """List daily Congressional Record issues by volume with full details.

        Each Congress typically spans two volumes. Returns full issue
        details including date and sections.
        """
        async with CongressClient(config) as client:
            response = await client.get(
                f"/daily-congressional-record/{volume_number}",
                limit=limit,
                offset=offset,
            )

            def build_endpoint(item: dict[str, Any]) -> str:
                issue_number = item.get("issueNumber", "")
                return f"/daily-congressional-record/{volume_number}/{issue_number}"

            return await client.enrich_list_response(
                response,
                result_key="dailyCongressionalRecord",
                detail_key="dailyCongressionalRecord",
                build_endpoint=build_endpoint,
            )

    @mcp.tool()
    async def get_daily_congressional_record_issue(
        volume_number: Annotated[int, Field(description="Volume number", ge=1)],
        issue_number: Annotated[int, Field(description="Issue number", ge=1)],
    ) -> dict[str, Any]:
        """Get a specific daily Congressional Record issue.

        Returns issue details including date and sections.
        """
        async with CongressClient(config) as client:
            return await client.get(
                f"/daily-congressional-record/{volume_number}/{issue_number}"
            )

    @mcp.tool()
    async def get_daily_congressional_record_articles(
        volume_number: Annotated[int, Field(description="Volume number", ge=1)],
        issue_number: Annotated[int, Field(description="Issue number", ge=1)],
        limit: Annotated[
            int | None, Field(description="Maximum results to return", ge=1, le=250)
        ] = None,
        offset: Annotated[int, Field(description="Starting position for pagination", ge=0)] = 0,
    ) -> dict[str, Any]:
        """Get articles from a daily Congressional Record issue.

        Returns individual articles/entries from the issue including
        floor proceedings, extensions of remarks, and daily digest.
        """
        async with CongressClient(config) as client:
            return await client.get(
                f"/daily-congressional-record/{volume_number}/{issue_number}/articles",
                limit=limit,
                offset=offset,
            )

    @mcp.tool()
    async def list_bound_congressional_record(
        year: Annotated[
            int | None, Field(description="Year (e.g., 2023). If not provided, lists all.", ge=1873)
        ] = None,
        limit: Annotated[
            int | None, Field(description="Maximum results to return (1-250)", ge=1, le=250)
        ] = None,
        offset: Annotated[int, Field(description="Starting position for pagination", ge=0)] = 0,
    ) -> dict[str, Any]:
        """List bound Congressional Record volumes.

        The bound edition is the permanent, hardcover edition of the
        Congressional Record published after each session.
        """
        async with CongressClient(config) as client:
            endpoint = f"/bound-congressional-record/{year}" if year else "/bound-congressional-record"
            return await client.get(endpoint, limit=limit, offset=offset)

    @mcp.tool()
    async def list_bound_congressional_record_by_month(
        year: Annotated[int, Field(description="Year (e.g., 2023)", ge=1873)],
        month: Annotated[int, Field(description="Month (1-12)", ge=1, le=12)],
        limit: Annotated[
            int | None, Field(description="Maximum results to return (1-250)", ge=1, le=250)
        ] = None,
        offset: Annotated[int, Field(description="Starting position for pagination", ge=0)] = 0,
    ) -> dict[str, Any]:
        """List bound Congressional Record entries for a specific month.

        Returns daily entries for the specified month.
        """
        async with CongressClient(config) as client:
            return await client.get(
                f"/bound-congressional-record/{year}/{month}",
                limit=limit,
                offset=offset,
            )

    @mcp.tool()
    async def get_bound_congressional_record_by_date(
        year: Annotated[int, Field(description="Year (e.g., 2023)", ge=1873)],
        month: Annotated[int, Field(description="Month (1-12)", ge=1, le=12)],
        day: Annotated[int, Field(description="Day (1-31)", ge=1, le=31)],
    ) -> dict[str, Any]:
        """Get bound Congressional Record entry for a specific date.

        Returns the record for that day's proceedings.
        """
        async with CongressClient(config) as client:
            return await client.get(f"/bound-congressional-record/{year}/{month}/{day}")
