"""Static MCP resources for Congress.gov API reference data."""

import json
from typing import Any

from congress_mcp.config import Config
from congress_mcp.types.enums import (
    AmendmentType,
    BillType,
    Chamber,
    HouseCommunicationType,
    LawType,
    ReportType,
    SenateCommunicationType,
)

try:
    from fastmcp import FastMCP
except ImportError:
    FastMCP = Any  # type: ignore[misc, assignment]


def register_static_resources(mcp: "FastMCP", config: Config) -> None:
    """Register static reference resources with the MCP server."""

    @mcp.resource("congress://api/info")
    def api_info() -> str:
        """Congress.gov API information and configuration.

        Provides API version, base URL, rate limits, and server configuration.
        """
        return json.dumps(
            {
                "name": "Congress.gov API",
                "version": "v3",
                "base_url": config.base_url,
                "rate_limit": "5,000 requests per hour",
                "default_limit": config.default_limit,
                "max_limit": config.max_limit,
                "documentation": "https://api.congress.gov",
                "github": "https://github.com/LibraryOfCongress/api.congress.gov",
                "sign_up": "https://api.congress.gov/sign-up/",
            },
            indent=2,
        )

    @mcp.resource("congress://enums/bill-types")
    def bill_types() -> str:
        """Reference list of valid bill type codes.

        Use these codes when querying bills and summaries.
        """
        return json.dumps(
            {
                bill_type.value: {
                    "name": bill_type.name,
                    "description": {
                        "hr": "House Bill - Legislation originating in the House",
                        "s": "Senate Bill - Legislation originating in the Senate",
                        "hjres": "House Joint Resolution - Used for constitutional amendments and continuing resolutions",
                        "sjres": "Senate Joint Resolution - Used for constitutional amendments and continuing resolutions",
                        "hconres": "House Concurrent Resolution - Expresses congressional sentiment, no force of law",
                        "sconres": "Senate Concurrent Resolution - Expresses congressional sentiment, no force of law",
                        "hres": "House Simple Resolution - Addresses House matters only",
                        "sres": "Senate Simple Resolution - Addresses Senate matters only",
                    }.get(bill_type.value, bill_type.name),
                }
                for bill_type in BillType
            },
            indent=2,
        )

    @mcp.resource("congress://enums/amendment-types")
    def amendment_types() -> str:
        """Reference list of valid amendment type codes."""
        return json.dumps(
            {
                amd_type.value: {
                    "name": amd_type.name,
                    "description": {
                        "hamdt": "House Amendment",
                        "samdt": "Senate Amendment",
                        "suamdt": "Senate Unprinted Amendment",
                    }.get(amd_type.value, amd_type.name),
                }
                for amd_type in AmendmentType
            },
            indent=2,
        )

    @mcp.resource("congress://enums/chambers")
    def chambers() -> str:
        """Reference list of congressional chambers."""
        return json.dumps(
            {
                chamber.value: {
                    "name": chamber.name,
                    "description": {
                        "house": "House of Representatives (435 voting members)",
                        "senate": "Senate (100 members, 2 per state)",
                    }.get(chamber.value, chamber.name),
                }
                for chamber in Chamber
            },
            indent=2,
        )

    @mcp.resource("congress://enums/law-types")
    def law_types() -> str:
        """Reference list of law type codes."""
        return json.dumps(
            {
                law_type.value: {
                    "name": law_type.name,
                    "description": {
                        "pub": "Public Law - Affects the general public",
                        "priv": "Private Law - Affects specific individuals or entities",
                    }.get(law_type.value, law_type.name),
                }
                for law_type in LawType
            },
            indent=2,
        )

    @mcp.resource("congress://enums/report-types")
    def report_types() -> str:
        """Reference list of committee report type codes."""
        return json.dumps(
            {
                report_type.value: {
                    "name": report_type.name,
                    "description": {
                        "hrpt": "House Report",
                        "srpt": "Senate Report",
                        "erpt": "Executive Report (Senate only)",
                    }.get(report_type.value, report_type.name),
                }
                for report_type in ReportType
            },
            indent=2,
        )

    @mcp.resource("congress://enums/house-communication-types")
    def house_communication_types() -> str:
        """Reference list of House communication type codes."""
        return json.dumps(
            {
                comm_type.value: {
                    "name": comm_type.name,
                    "description": {
                        "ec": "Executive Communication - From executive branch agencies",
                        "pm": "Presidential Message - From the President",
                        "pt": "Petition - From citizens or organizations",
                        "ml": "Memorial - Formal statements from state legislatures",
                    }.get(comm_type.value, comm_type.name),
                }
                for comm_type in HouseCommunicationType
            },
            indent=2,
        )

    @mcp.resource("congress://enums/senate-communication-types")
    def senate_communication_types() -> str:
        """Reference list of Senate communication type codes."""
        return json.dumps(
            {
                comm_type.value: {
                    "name": comm_type.name,
                    "description": {
                        "ec": "Executive Communication - From executive branch agencies",
                        "pom": "Petition or Memorial - From citizens, organizations, or state legislatures",
                        "pm": "Presidential Message - From the President",
                    }.get(comm_type.value, comm_type.name),
                }
                for comm_type in SenateCommunicationType
            },
            indent=2,
        )

    @mcp.resource("congress://reference/congress-numbers")
    def congress_numbers() -> str:
        """Reference for recent Congress numbers and their date ranges."""
        return json.dumps(
            {
                "119": {"years": "2025-2027", "start": "2025-01-03", "end": "2027-01-03"},
                "118": {"years": "2023-2025", "start": "2023-01-03", "end": "2025-01-03"},
                "117": {"years": "2021-2023", "start": "2021-01-03", "end": "2023-01-03"},
                "116": {"years": "2019-2021", "start": "2019-01-03", "end": "2021-01-03"},
                "115": {"years": "2017-2019", "start": "2017-01-03", "end": "2019-01-03"},
                "114": {"years": "2015-2017", "start": "2015-01-06", "end": "2017-01-03"},
                "113": {"years": "2013-2015", "start": "2013-01-03", "end": "2015-01-03"},
                "note": "Each Congress begins on January 3 of odd-numbered years and lasts two years. The first Congress began in 1789.",
            },
            indent=2,
        )
