"""Committee report tools for Congress.gov API."""

from typing import Annotated, Any

from pydantic import Field

from congress_mcp.client import CongressClient
from congress_mcp.config import Config
from congress_mcp.types.enums import ReportType

try:
    from fastmcp import FastMCP
except ImportError:
    FastMCP = Any  # type: ignore[misc, assignment]


def register_committee_report_tools(mcp: "FastMCP", config: Config) -> None:
    """Register all committee report tools with the MCP server."""

    @mcp.tool()
    async def list_committee_reports(
        congress: Annotated[int, Field(description="Congress number (e.g., 118)", ge=1, le=200)],
        report_type: Annotated[
            ReportType,
            Field(description="Report type: hrpt (House), srpt (Senate), erpt (Executive)"),
        ],
        limit: Annotated[
            int | None, Field(description="Maximum results to return (1-250)", ge=1, le=250)
        ] = None,
        offset: Annotated[int, Field(description="Starting position for pagination", ge=0)] = 0,
    ) -> dict[str, Any]:
        """List committee reports by Congress and type.

        Report types:
        - hrpt: House Report
        - srpt: Senate Report
        - erpt: Executive Report (Senate only)
        """
        async with CongressClient(config) as client:
            return await client.get(
                f"/committee-report/{congress}/{report_type.value}",
                limit=limit,
                offset=offset,
            )

    @mcp.tool()
    async def get_committee_report(
        congress: Annotated[int, Field(description="Congress number (e.g., 118)", ge=1, le=200)],
        report_type: Annotated[ReportType, Field(description="Report type: hrpt, srpt, or erpt")],
        report_number: Annotated[int, Field(description="Report number", ge=1)],
    ) -> dict[str, Any]:
        """Get detailed information about a specific committee report.

        Returns report details including associated bills, committee,
        and publication information.
        """
        async with CongressClient(config) as client:
            return await client.get(
                f"/committee-report/{congress}/{report_type.value}/{report_number}"
            )

    @mcp.tool()
    async def get_committee_report_text(
        congress: Annotated[int, Field(description="Congress number (e.g., 118)", ge=1, le=200)],
        report_type: Annotated[ReportType, Field(description="Report type: hrpt, srpt, or erpt")],
        report_number: Annotated[int, Field(description="Report number", ge=1)],
    ) -> dict[str, Any]:
        """Get text versions of a committee report.

        Returns links to available text formats (PDF, XML, HTML).
        """
        async with CongressClient(config) as client:
            return await client.get(
                f"/committee-report/{congress}/{report_type.value}/{report_number}/text"
            )
