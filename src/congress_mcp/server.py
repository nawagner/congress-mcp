"""Congress.gov MCP Server entry point."""

from fastmcp import FastMCP

from congress_mcp.config import Config
from congress_mcp.resources import register_all_resources
from congress_mcp.tools import register_all_tools

# Initialize configuration from environment
config = Config.from_env()

# Create FastMCP server
mcp = FastMCP(
    name="congress-mcp",
    instructions="""
Congress.gov MCP Server provides access to official U.S. Congress data
including bills, laws, amendments, members, committees, hearings,
nominations, treaties, and more.

Key information:
- All legislative data queries require an explicit Congress number
  (e.g., 118 for the 118th Congress, which ran 2023-2025)
- The current Congress is the 119th (2025-2027)
- Rate limit: 5,000 requests per hour per API key
- Data is sourced directly from the official Congress.gov API v3

Available data categories:
- Bills and resolutions (HR, S, HJRES, SJRES, HCONRES, SCONRES, HRES, SRES)
- Laws (public and private)
- Amendments (House and Senate)
- Members of Congress
- Committees and subcommittees
- Committee reports, prints, and meetings
- Hearings
- Nominations
- Treaties
- Congressional Record (daily and bound)
- CRS Reports
- House and Senate communications
- Roll call votes
""",
)

# Register all tools and resources
register_all_tools(mcp, config)
register_all_resources(mcp, config)


def main() -> None:
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
