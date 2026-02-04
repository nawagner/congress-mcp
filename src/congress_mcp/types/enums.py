"""Enumeration types for Congress.gov API parameters."""

from enum import Enum


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


class AmendmentType(str, Enum):
    """Amendment type codes.

    HAMDT: House Amendment
    SAMDT: Senate Amendment
    SUAMDT: Senate Unprinted Amendment
    """

    HAMDT = "hamdt"
    SAMDT = "samdt"
    SUAMDT = "suamdt"


class Chamber(str, Enum):
    """Congressional chambers."""

    HOUSE = "house"
    SENATE = "senate"


class LawType(str, Enum):
    """Law type codes.

    PUB: Public Law - affects the general public
    PRIV: Private Law - affects specific individuals or entities
    """

    PUB = "pub"
    PRIV = "priv"


class ReportType(str, Enum):
    """Committee report type codes.

    HRPT: House Report
    SRPT: Senate Report
    ERPT: Executive Report
    """

    HRPT = "hrpt"
    SRPT = "srpt"
    ERPT = "erpt"


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


class SenateCommunicationType(str, Enum):
    """Senate communication type codes.

    EC: Executive Communication
    POM: Petition or Memorial
    PM: Presidential Message
    """

    EC = "ec"
    POM = "pom"
    PM = "pm"
