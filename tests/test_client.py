"""Tests for HTTP client functionality."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from congress_mcp.client import CongressClient
from congress_mcp.config import Config
from congress_mcp.exceptions import (
    AuthenticationError,
    CongressAPIError,
    NotFoundError,
    RateLimitError,
)


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


class TestCongressClient:
    """Tests for CongressClient."""

    @pytest.mark.asyncio
    async def test_client_adds_api_key_to_requests(self, config: Config) -> None:
        """API key is added to all requests."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"bills": []}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client

            async with CongressClient(config) as client:
                await client.get("/bill/118")

            # Verify api_key was in params
            call_args = mock_client.get.call_args
            assert call_args.kwargs["params"]["api_key"] == "test_key"
            assert call_args.kwargs["params"]["format"] == "json"

    @pytest.mark.asyncio
    async def test_client_handles_404_not_found(self, config: Config) -> None:
        """404 responses raise NotFoundError."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not found"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client

            async with CongressClient(config) as client:
                with pytest.raises(NotFoundError) as exc_info:
                    await client.get("/bill/999/hr/99999")

            assert "not found" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_client_handles_429_rate_limit(self, config: Config) -> None:
        """429 responses raise RateLimitError."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.text = "Rate limit exceeded"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client

            async with CongressClient(config) as client:
                with pytest.raises(RateLimitError):
                    await client.get("/bill/118")

    @pytest.mark.asyncio
    async def test_client_handles_401_authentication(self, config: Config) -> None:
        """401 responses raise AuthenticationError."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client

            async with CongressClient(config) as client:
                with pytest.raises(AuthenticationError):
                    await client.get("/bill/118")

    @pytest.mark.asyncio
    async def test_client_handles_500_server_error(self, config: Config) -> None:
        """500 responses raise CongressAPIError."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client

            async with CongressClient(config) as client:
                with pytest.raises(CongressAPIError) as exc_info:
                    await client.get("/bill/118")

            assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_client_respects_limit_parameter(self, config: Config) -> None:
        """Limit parameter is passed to request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"bills": []}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client

            async with CongressClient(config) as client:
                await client.get("/bill/118", limit=50)

            call_args = mock_client.get.call_args
            assert call_args.kwargs["params"]["limit"] == 50

    @pytest.mark.asyncio
    async def test_client_enforces_max_limit(self, config: Config) -> None:
        """Limit is capped at max_limit."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"bills": []}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client

            async with CongressClient(config) as client:
                await client.get("/bill/118", limit=500)  # Above max_limit of 250

            call_args = mock_client.get.call_args
            assert call_args.kwargs["params"]["limit"] == 250

    @pytest.mark.asyncio
    async def test_client_passes_offset_parameter(self, config: Config) -> None:
        """Offset parameter is passed to request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"bills": []}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client

            async with CongressClient(config) as client:
                await client.get("/bill/118", offset=100)

            call_args = mock_client.get.call_args
            assert call_args.kwargs["params"]["offset"] == 100

    @pytest.mark.asyncio
    async def test_client_context_manager_closes_client(self, config: Config) -> None:
        """Client is properly closed when exiting context manager."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client

            async with CongressClient(config) as client:
                await client.get("/bill/118")

            mock_client.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_client_not_initialized_error(self, config: Config) -> None:
        """Raises error when used without context manager."""
        client = CongressClient(config)
        with pytest.raises(RuntimeError, match="not initialized"):
            await client.get("/bill/118")
