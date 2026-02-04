"""Dynamic MCP resources with URI templates for Congress.gov data."""

import json
from typing import Any

from congress_mcp.client import CongressClient
from congress_mcp.config import Config

try:
    from fastmcp import FastMCP
except ImportError:
    FastMCP = Any  # type: ignore[misc, assignment]


def register_dynamic_resources(mcp: "FastMCP", config: Config) -> None:
    """Register dynamic resources with URI templates for direct data access."""

    @mcp.resource("congress://bill/{congress}/{bill_type}/{bill_number}")
    async def bill_resource(congress: int, bill_type: str, bill_number: int) -> str:
        """Direct access to bill data by Congress, type, and number.

        Example URIs:
        - congress://bill/118/hr/1
        - congress://bill/117/s/1234
        """
        async with CongressClient(config) as client:
            result = await client.get(f"/bill/{congress}/{bill_type}/{bill_number}")
            return json.dumps(result, indent=2)

    @mcp.resource("congress://member/{bioguide_id}")
    async def member_resource(bioguide_id: str) -> str:
        """Direct access to member data by bioguide ID.

        Example URIs:
        - congress://member/P000197 (Nancy Pelosi)
        - congress://member/M000355 (Mitch McConnell)
        """
        async with CongressClient(config) as client:
            result = await client.get(f"/member/{bioguide_id}")
            return json.dumps(result, indent=2)

    @mcp.resource("congress://committee/{chamber}/{committee_code}")
    async def committee_resource(chamber: str, committee_code: str) -> str:
        """Direct access to committee data by chamber and system code.

        Example URIs:
        - congress://committee/house/hsju00 (House Judiciary)
        - congress://committee/senate/ssfi00 (Senate Finance)
        """
        async with CongressClient(config) as client:
            result = await client.get(f"/committee/{chamber}/{committee_code}")
            return json.dumps(result, indent=2)

    @mcp.resource("congress://nomination/{congress}/{nomination_number}")
    async def nomination_resource(congress: int, nomination_number: int) -> str:
        """Direct access to nomination data.

        Example URIs:
        - congress://nomination/118/1064
        - congress://nomination/117/500
        """
        async with CongressClient(config) as client:
            result = await client.get(f"/nomination/{congress}/{nomination_number}")
            return json.dumps(result, indent=2)

    @mcp.resource("congress://treaty/{congress}/{treaty_number}")
    async def treaty_resource(congress: int, treaty_number: int) -> str:
        """Direct access to treaty data.

        Example URIs:
        - congress://treaty/118/3
        - congress://treaty/117/1
        """
        async with CongressClient(config) as client:
            result = await client.get(f"/treaty/{congress}/{treaty_number}")
            return json.dumps(result, indent=2)

    @mcp.resource("congress://law/{congress}/{law_type}/{law_number}")
    async def law_resource(congress: int, law_type: str, law_number: int) -> str:
        """Direct access to law data.

        Example URIs:
        - congress://law/118/pub/1 (Public Law 118-1)
        - congress://law/117/priv/1 (Private Law 117-1)
        """
        async with CongressClient(config) as client:
            result = await client.get(f"/law/{congress}/{law_type}/{law_number}")
            return json.dumps(result, indent=2)

    @mcp.resource("congress://congress/{congress_number}")
    async def congress_resource(congress_number: int) -> str:
        """Direct access to Congress session data.

        Example URIs:
        - congress://congress/118
        - congress://congress/119
        """
        async with CongressClient(config) as client:
            result = await client.get(f"/congress/{congress_number}")
            return json.dumps(result, indent=2)

    @mcp.resource("congress://crs-report/{report_number}")
    async def crs_report_resource(report_number: str) -> str:
        """Direct access to CRS report data.

        Example URIs:
        - congress://crs-report/R47000
        - congress://crs-report/RL33614
        """
        async with CongressClient(config) as client:
            result = await client.get(f"/crsreport/{report_number}")
            return json.dumps(result, indent=2)
