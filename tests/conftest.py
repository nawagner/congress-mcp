"""Pytest fixtures for Congress MCP tests."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from congress_mcp.config import Config


@pytest.fixture
def mock_config() -> Config:
    """Provide test configuration."""
    return Config(
        api_key="test_api_key_12345",
        base_url="https://api.congress.gov/v3",
        default_limit=20,
        max_limit=250,
        timeout=30.0,
    )


@pytest.fixture
def mock_bill_response() -> dict[str, Any]:
    """Sample bill API response."""
    return {
        "bill": {
            "congress": 118,
            "type": "HR",
            "number": 1,
            "title": "Lower Energy Costs Act",
            "originChamber": "House",
            "originChamberCode": "H",
            "introducedDate": "2023-01-09",
            "updateDate": "2024-01-15",
            "latestAction": {
                "actionDate": "2023-03-30",
                "text": "Received in the Senate and Read twice and referred to the Committee on Energy and Natural Resources.",
            },
            "sponsors": [
                {
                    "bioguideId": "S001183",
                    "fullName": "Rep. Scalise, Steve [R-LA-1]",
                    "firstName": "Steve",
                    "lastName": "Scalise",
                    "party": "R",
                    "state": "LA",
                }
            ],
        }
    }


@pytest.fixture
def mock_bills_list_response() -> dict[str, Any]:
    """Sample bills list API response."""
    return {
        "bills": [
            {
                "congress": 118,
                "type": "HR",
                "number": 1,
                "title": "Lower Energy Costs Act",
                "latestAction": {"actionDate": "2023-03-30", "text": "Received in Senate."},
            },
            {
                "congress": 118,
                "type": "HR",
                "number": 2,
                "title": "Secure the Border Act of 2023",
                "latestAction": {"actionDate": "2023-05-11", "text": "Passed House."},
            },
        ],
        "pagination": {"count": 100, "next": "/bill/118?offset=20"},
    }


@pytest.fixture
def mock_member_response() -> dict[str, Any]:
    """Sample member API response."""
    return {
        "member": {
            "bioguideId": "P000197",
            "directOrderName": "Nancy Pelosi",
            "invertedOrderName": "Pelosi, Nancy",
            "partyName": "Democratic",
            "state": "California",
            "district": 11,
            "currentMember": True,
            "terms": [
                {
                    "congress": 118,
                    "chamber": "House of Representatives",
                    "startYear": 2023,
                    "endYear": 2025,
                }
            ],
        }
    }


@pytest.fixture
def mock_httpx_response() -> MagicMock:
    """Create a mock httpx response."""

    def _create_response(
        status_code: int = 200, json_data: dict[str, Any] | None = None, text: str = ""
    ) -> MagicMock:
        response = MagicMock()
        response.status_code = status_code
        response.text = text
        response.json = MagicMock(return_value=json_data or {})
        return response

    return _create_response


@pytest.fixture
def mock_async_client(mock_httpx_response: MagicMock) -> AsyncMock:
    """Create a mock async HTTP client."""
    client = AsyncMock()
    client.get = AsyncMock()
    client.aclose = AsyncMock()
    return client
