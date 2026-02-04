"""CRS Report tools for Congress.gov API."""

from typing import Annotated, Any

from pydantic import Field

from congress_mcp.client import CongressClient
from congress_mcp.config import Config

try:
    from fastmcp import FastMCP
except ImportError:
    FastMCP = Any  # type: ignore[misc, assignment]


def register_crs_report_tools(mcp: "FastMCP", config: Config) -> None:
    """Register all CRS report tools with the MCP server."""

    @mcp.tool()
    async def list_crs_reports(
        limit: Annotated[
            int | None, Field(description="Maximum results to return (1-250)", ge=1, le=250)
        ] = None,
        offset: Annotated[int, Field(description="Starting position for pagination", ge=0)] = 0,
    ) -> dict[str, Any]:
        """List Congressional Research Service (CRS) reports.

        CRS reports are authoritative, nonpartisan analyses of legislative
        issues prepared for members of Congress. Topics cover a wide range
        of public policy areas.
        """
        async with CongressClient(config) as client:
            return await client.get("/crsreport", limit=limit, offset=offset)

    @mcp.tool()
    async def get_crs_report(
        report_number: Annotated[
            str, Field(description="CRS report number (e.g., 'R47000', 'RL33614')")
        ],
    ) -> dict[str, Any]:
        """Get detailed information about a specific CRS report.

        Returns report details including title, authors, summary,
        publication date, and links to full text.

        Report number formats:
        - R#####: General reports
        - RL#####: Reports (older format)
        - RS#####: Short reports
        - IF#####: In Focus briefs
        """
        async with CongressClient(config) as client:
            return await client.get(f"/crsreport/{report_number}")
