"""Enumeration types for Congress.gov API parameters.

Enum classes are used for middleware validation error messages.
Literal types are used in tool parameter signatures to produce flat
JSON schemas without ``$ref``/``$defs`` indirection, which improves
compatibility with LLM tool-calling clients.
"""

from enum import Enum
from typing import Literal


class BillType(str, Enum):
    """Bill type codes used in the Congress.gov API.

    Reference: https://www.congress.gov/help/legislative-glossary
    """

    HR = "hr"  # House Bill
    S = "s"  # Senate Bill
    HJRES = "hjres"  # House Joint Resolution
    SJRES = "sjres"  # Senate Joint Resolution
    HCONRES = "hconres"  # House Concurrent Resolution
    SCONRES = "sconres"  # Senate Concurrent Resolution
    HRES = "hres"  # House Simple Resolution
    SRES = "sres"  # Senate Simple Resolution


BillTypeLiteral = Literal["hr", "s", "hjres", "sjres", "hconres", "sconres", "hres", "sres"]


# Sort values for the bill list endpoints, in the ``+`` form they take in API
# URLs. The API itself documents them with a space (``updateDate desc``).
BillSortLiteral = Literal[
    "updateDate+asc",
    "updateDate+desc",
    "introducedDate+asc",
    "introducedDate+desc",
]


class AmendmentType(str, Enum):
    """Amendment type codes.

    HAMDT: House Amendment
    SAMDT: Senate Amendment
    SUAMDT: Senate Unprinted Amendment
    """

    HAMDT = "hamdt"
    SAMDT = "samdt"
    SUAMDT = "suamdt"


AmendmentTypeLiteral = Literal["hamdt", "samdt", "suamdt"]


class Chamber(str, Enum):
    """Congressional chambers."""

    HOUSE = "house"
    SENATE = "senate"


ChamberLiteral = Literal["house", "senate"]


class LawType(str, Enum):
    """Law type codes.

    PUB: Public Law - affects the general public
    PRIV: Private Law - affects specific individuals or entities
    """

    PUB = "pub"
    PRIV = "priv"


LawTypeLiteral = Literal["pub", "priv"]


class ReportType(str, Enum):
    """Committee report type codes.

    HRPT: House Report
    SRPT: Senate Report
    ERPT: Executive Report
    """

    HRPT = "hrpt"
    SRPT = "srpt"
    ERPT = "erpt"


ReportTypeLiteral = Literal["hrpt", "srpt", "erpt"]


class HouseCommunicationType(str, Enum):
    """House communication type codes.

    EC: Executive Communication
    PM: Presidential Message
    PT: Petition
    ML: Memorial
    """

    EC = "ec"
    PM = "pm"
    PT = "pt"
    ML = "ml"


HouseCommunicationTypeLiteral = Literal["ec", "pm", "pt", "ml"]


class SenateCommunicationType(str, Enum):
    """Senate communication type codes.

    EC: Executive Communication
    POM: Petition or Memorial
    PM: Presidential Message
    """

    EC = "ec"
    POM = "pom"
    PM = "pm"


SenateCommunicationTypeLiteral = Literal["ec", "pom", "pm"]


# Controlled list of policy area terms. CRS assigns one to each bill, and bill
# detail responses report it as ``policyArea.name`` (list responses do not).
# Reference: https://www.congress.gov/help/field-values/policy-area
PolicyAreaLiteral = Literal[
    "Agriculture and Food",
    "Animals",
    "Armed Forces and National Security",
    "Arts, Culture, Religion",
    "Civil Rights and Liberties, Minority Issues",
    "Commerce",
    "Congress",
    "Crime and Law Enforcement",
    "Economics and Public Finance",
    "Education",
    "Emergency Management",
    "Energy",
    "Environmental Protection",
    "Families",
    "Finance and Financial Sector",
    "Foreign Trade and International Finance",
    "Government Operations and Politics",
    "Health",
    "Housing and Community Development",
    "Immigration",
    "International Affairs",
    "Labor and Employment",
    "Law",
    "Native Americans",
    "Private Legislation",
    "Public Lands and Natural Resources",
    "Science, Technology, Communications",
    "Social Sciences and History",
    "Social Welfare",
    "Sports and Recreation",
    "Taxation",
    "Transportation and Public Works",
    "Water Resources Development",
]
