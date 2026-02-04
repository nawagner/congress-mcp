"""MCP Tools for Congress.gov API."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp import FastMCP
    from congress_mcp.config import Config


def register_all_tools(mcp: "FastMCP", config: "Config") -> None:
    """Register all Congress.gov API tools with the MCP server."""
    from .bills import register_bill_tools
    from .laws import register_law_tools
    from .amendments import register_amendment_tools
    from .members import register_member_tools
    from .committees import register_committee_tools
    from .committee_reports import register_committee_report_tools
    from .committee_prints import register_committee_print_tools
    from .committee_meetings import register_committee_meeting_tools
    from .hearings import register_hearing_tools
    from .nominations import register_nomination_tools
    from .treaties import register_treaty_tools
    from .congressional_record import register_congressional_record_tools
    from .communications import register_communication_tools
    from .votes import register_vote_tools
    from .summaries import register_summary_tools
    from .congress import register_congress_tools
    from .crs_reports import register_crs_report_tools
    from .house_requirements import register_house_requirement_tools

    register_bill_tools(mcp, config)
    register_law_tools(mcp, config)
    register_amendment_tools(mcp, config)
    register_member_tools(mcp, config)
    register_committee_tools(mcp, config)
    register_committee_report_tools(mcp, config)
    register_committee_print_tools(mcp, config)
    register_committee_meeting_tools(mcp, config)
    register_hearing_tools(mcp, config)
    register_nomination_tools(mcp, config)
    register_treaty_tools(mcp, config)
    register_congressional_record_tools(mcp, config)
    register_communication_tools(mcp, config)
    register_vote_tools(mcp, config)
    register_summary_tools(mcp, config)
    register_congress_tools(mcp, config)
    register_crs_report_tools(mcp, config)
    register_house_requirement_tools(mcp, config)
