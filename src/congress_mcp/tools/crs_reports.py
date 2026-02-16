"""CRS Report tools for Congress.gov API."""

from typing import Annotated, Any

from pydantic import Field

from congress_mcp.annotations import READONLY_ANNOTATIONS
from congress_mcp.client import CongressClient
from congress_mcp.config import Config
from congress_mcp.exceptions import CongressAPIError, NotFoundError

try:
    from fastmcp import FastMCP
except ImportError:
    FastMCP = Any  # type: ignore[misc, assignment]


def register_crs_report_tools(mcp: "FastMCP", config: Config) -> None:
    """Register all CRS report tools with the MCP server."""

    @mcp.tool(annotations=READONLY_ANNOTATIONS)
    async def list_crs_reports(
        from_date: Annotated[
            str | None, Field(description="Filter by update date start (YYYY-MM-DD)")
        ] = None,
        to_date: Annotated[
            str | None, Field(description="Filter by update date end (YYYY-MM-DD)")
        ] = None,
        limit: Annotated[
            int | None, Field(description="Maximum results to return (1-250)", ge=1, le=250)
        ] = None,
        offset: Annotated[int, Field(description="Starting position for pagination", ge=0)] = 0,
    ) -> dict[str, Any]:
        """List Congressional Research Service (CRS) reports with full details.

        CRS reports are authoritative, nonpartisan analyses of legislative
        issues prepared for members of Congress. Returns full report details
        including title, authors, summary, and text links.
        """
        async with CongressClient(config) as client:
            params: dict[str, Any] = {}
            if from_date:
                params["fromDateTime"] = f"{from_date}T00:00:00Z"
            if to_date:
                params["toDateTime"] = f"{to_date}T23:59:59Z"
            response = await client.get("/crsreport", params=params, limit=limit, offset=offset)

            def build_endpoint(item: dict[str, Any]) -> str:
                report_number = item.get("reportNumber", "")
                return f"/crsreport/{report_number}"

            return await client.enrich_list_response(
                response,
                result_key="crsReports",
                detail_key="crsReport",
                build_endpoint=build_endpoint,
            )

    @mcp.tool(annotations=READONLY_ANNOTATIONS)
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
            try:
                return await client.get(f"/crsreport/{report_number}")
            except CongressAPIError as e:
                if e.status_code == 500 and "NoneType" in str(e):
                    raise NotFoundError(
                        f"CRS report '{report_number}' not found"
                    ) from e
                raise
