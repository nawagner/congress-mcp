"""Tests for auto-pagination functionality."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from congress_mcp.client import CongressClient
from congress_mcp.config import Config


@pytest.fixture
def config() -> Config:
    """Test configuration."""
    return Config(
        api_key="test_key",
        base_url="https://api.congress.gov/v3",
        default_limit=20,
        max_limit=250,
        timeout=30.0,
    )


class TestPagination:
    """Tests for auto-pagination in CongressClient."""

    @pytest.mark.asyncio
    async def test_get_all_single_page(self, config: Config) -> None:
        """Single page of results is returned correctly."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "bills": [{"number": i} for i in range(50)],
            "pagination": {"count": 50},
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client

            async with CongressClient(config) as client:
                result = await client.get_all("/bill/118")

            assert len(result["results"]) == 50
            assert result["count"] == 50

    @pytest.mark.asyncio
    async def test_get_all_multiple_pages(self, config: Config) -> None:
        """Multiple pages are fetched and combined."""
        # First page: 250 items (max), total count 400
        # Second page: 150 items
        responses = [
            {
                "bills": [{"number": i} for i in range(250)],
                "pagination": {"count": 400},
            },
            {
                "bills": [{"number": i} for i in range(250, 400)],
                "pagination": {"count": 400},
            },
        ]

        call_count = 0

        def make_response() -> MagicMock:
            nonlocal call_count
            response = MagicMock()
            response.status_code = 200
            response.json.return_value = responses[min(call_count, len(responses) - 1)]
            call_count += 1
            return response

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=lambda *args, **kwargs: make_response())
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client

            async with CongressClient(config) as client:
                result = await client.get_all("/bill/118")

            assert len(result["results"]) == 400
            assert result["count"] == 400
            assert call_count == 2

    @pytest.mark.asyncio
    async def test_get_all_respects_max_results(self, config: Config) -> None:
        """Pagination stops at max_results."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "bills": [{"number": i} for i in range(250)],
            "pagination": {"count": 500},
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client

            async with CongressClient(config) as client:
                result = await client.get_all("/bill/118", max_results=100)

            assert len(result["results"]) == 100
            assert result["count"] == 100

    @pytest.mark.asyncio
    async def test_get_all_handles_empty_results(self, config: Config) -> None:
        """Empty results are handled correctly."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "bills": [],
            "pagination": {"count": 0},
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client

            async with CongressClient(config) as client:
                result = await client.get_all("/bill/118")

            assert len(result["results"]) == 0
            assert result["count"] == 0

    @pytest.mark.asyncio
    async def test_extract_results_various_keys(self, config: Config) -> None:
        """Results are extracted from various API response keys."""
        test_cases = [
            ("bills", [{"id": 1}]),
            ("members", [{"id": 2}]),
            ("amendments", [{"id": 3}]),
            ("committees", [{"id": 4}]),
        ]

        for key, expected_data in test_cases:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                key: expected_data,
                "pagination": {"count": 1},
            }

            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.get = AsyncMock(return_value=mock_response)
                mock_client.aclose = AsyncMock()
                mock_client_class.return_value = mock_client

                async with CongressClient(config) as client:
                    result = await client.get_all("/test")

                assert result["results"] == expected_data, f"Failed for key: {key}"

    @pytest.mark.asyncio
    async def test_get_all_passes_params(self, config: Config) -> None:
        """Additional parameters are passed through to requests."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "bills": [],
            "pagination": {"count": 0},
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client

            async with CongressClient(config) as client:
                await client.get_all(
                    "/bill/118",
                    params={"sort": "updateDate+desc"},
                )

            call_args = mock_client.get.call_args
            assert call_args.kwargs["params"]["sort"] == "updateDate+desc"
