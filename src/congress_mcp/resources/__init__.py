"""MCP Resources for Congress.gov API."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp import FastMCP
    from congress_mcp.config import Config


def register_all_resources(mcp: "FastMCP", config: "Config") -> None:
    """Register all Congress.gov API resources with the MCP server."""
    from .static import register_static_resources
    from .dynamic import register_dynamic_resources

    register_static_resources(mcp, config)
    register_dynamic_resources(mcp, config)
