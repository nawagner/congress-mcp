"""Tests for HTTP client functionality."""

import logging
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
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
    @patch("congress_mcp.client.asyncio.sleep", new_callable=AsyncMock)
    async def test_client_handles_429_rate_limit(self, mock_sleep: AsyncMock, config: Config) -> None:
        """429 responses raise RateLimitError after retries exhausted."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.text = "Rate limit exceeded"
        mock_response.headers = {}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client

            async with CongressClient(config) as client:
                with pytest.raises(RateLimitError):
                    await client.get("/bill/118")

            # 1 initial + 3 retries = 4 total calls
            assert mock_client.get.call_count == 4
            assert mock_sleep.call_count == 3

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


class TestConcurrentDetailFetching:
    """Tests for safe_get, fetch_details_concurrent, and enrich_list_response."""

    @pytest.mark.asyncio
    async def test_safe_get_logs_warning_on_api_error(
        self, config: Config, caplog: pytest.LogCaptureFixture
    ) -> None:
        """CongressAPIError (non-rate-limit, non-auth) is caught and logged."""
        ok_response = MagicMock()
        ok_response.status_code = 200
        ok_response.json.return_value = {"bill": {"title": "A bill"}}

        err_response = MagicMock()
        err_response.status_code = 500
        err_response.text = "Internal server error"

        def route(endpoint: str, **kwargs: Any) -> MagicMock:
            if "fail" in endpoint:
                return err_response
            return ok_response

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=route)
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client

            with caplog.at_level(logging.WARNING, logger="congress-mcp.client"):
                async with CongressClient(config) as client:
                    results = await client.fetch_details_concurrent(
                        ["/bill/118/hr/1", "/bill/fail/hr/2"]
                    )

        assert results[0] is not None
        assert results[1] is None
        assert any("/bill/fail/hr/2" in r.message for r in caplog.records)

    @pytest.mark.asyncio
    async def test_safe_get_logs_warning_on_network_error(
        self, config: Config, caplog: pytest.LogCaptureFixture
    ) -> None:
        """httpx.HTTPError is caught and logged."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(
                side_effect=httpx.ConnectError("Connection refused")
            )
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client

            with caplog.at_level(logging.WARNING, logger="congress-mcp.client"):
                async with CongressClient(config) as client:
                    results = await client.fetch_details_concurrent(["/bill/118/hr/1"])

        assert results == [None]
        assert any("/bill/118/hr/1" in r.message for r in caplog.records)

    @pytest.mark.asyncio
    @patch("congress_mcp.client.asyncio.sleep", new_callable=AsyncMock)
    async def test_safe_get_propagates_rate_limit_error(self, mock_sleep: AsyncMock, config: Config) -> None:
        """RateLimitError is NOT caught and propagates to caller."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.text = "Rate limit exceeded"
        mock_response.headers = {}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client

            async with CongressClient(config) as client:
                with pytest.raises(RateLimitError):
                    await client.fetch_details_concurrent(["/bill/118/hr/1"])

    @pytest.mark.asyncio
    async def test_safe_get_propagates_authentication_error(
        self, config: Config
    ) -> None:
        """AuthenticationError is NOT caught and propagates to caller."""
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
                    await client.fetch_details_concurrent(["/bill/118/hr/1"])

    @pytest.mark.asyncio
    async def test_safe_get_propagates_unexpected_exceptions(
        self, config: Config
    ) -> None:
        """Unexpected exceptions (TypeError, etc.) propagate to caller."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=TypeError("unexpected"))
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client

            async with CongressClient(config) as client:
                with pytest.raises(TypeError, match="unexpected"):
                    await client.fetch_details_concurrent(["/bill/118/hr/1"])

    @pytest.mark.asyncio
    async def test_enrich_list_response_adds_warnings_on_failure(
        self, config: Config
    ) -> None:
        """_warnings is added to response when some enrichments fail."""
        ok_response = MagicMock()
        ok_response.status_code = 200
        ok_response.json.return_value = {"bill": {"title": "Good Bill", "summary": "A summary"}}

        err_response = MagicMock()
        err_response.status_code = 500
        err_response.text = "Internal server error"

        def route(endpoint: str, **kwargs: Any) -> MagicMock:
            if "hr/2" in endpoint:
                return err_response
            return ok_response

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=route)
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client

            list_response: dict[str, Any] = {
                "bills": [
                    {"number": "1", "type": "hr"},
                    {"number": "2", "type": "hr"},
                ],
            }

            async with CongressClient(config) as client:
                result = await client.enrich_list_response(
                    list_response=list_response,
                    result_key="bills",
                    detail_key="bill",
                    build_endpoint=lambda item: f"/bill/118/{item['type']}/{item['number']}",
                )

        # First item enriched
        assert result["bills"][0]["title"] == "Good Bill"
        # Second item not enriched (no "title" key from detail)
        assert "title" not in result["bills"][1]
        # Warnings present
        assert "_warnings" in result
        assert len(result["_warnings"]) == 1
        assert "/bill/118/hr/2" in result["_warnings"][0]

    @pytest.mark.asyncio
    async def test_enrich_list_response_no_warnings_when_all_succeed(
        self, config: Config
    ) -> None:
        """_warnings is absent when all enrichments succeed."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"bill": {"title": "A bill", "summary": "A summary"}}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client

            list_response: dict[str, Any] = {
                "bills": [
                    {"number": "1", "type": "hr"},
                    {"number": "2", "type": "hr"},
                ],
            }

            async with CongressClient(config) as client:
                result = await client.enrich_list_response(
                    list_response=list_response,
                    result_key="bills",
                    detail_key="bill",
                    build_endpoint=lambda item: f"/bill/118/{item['type']}/{item['number']}",
                )

        # Both items enriched
        assert result["bills"][0]["title"] == "A bill"
        assert result["bills"][1]["title"] == "A bill"
        # No warnings
        assert "_warnings" not in result


class TestRetryBackoff:
    """Tests for 429 retry with exponential backoff."""

    @pytest.mark.asyncio
    @patch("congress_mcp.client.asyncio.sleep", new_callable=AsyncMock)
    async def test_retry_succeeds_after_transient_429(self, mock_sleep: AsyncMock, config: Config) -> None:
        """Request succeeds after transient 429 responses."""
        rate_limit_response = MagicMock()
        rate_limit_response.status_code = 429
        rate_limit_response.headers = {}

        ok_response = MagicMock()
        ok_response.status_code = 200
        ok_response.json.return_value = {"bills": []}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(
                side_effect=[rate_limit_response, rate_limit_response, ok_response]
            )
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client

            async with CongressClient(config) as client:
                result = await client.get("/bill/118")

            assert result == {"bills": []}
            assert mock_client.get.call_count == 3
            assert mock_sleep.call_count == 2
            mock_sleep.assert_any_call(1.0)
            mock_sleep.assert_any_call(2.0)

    @pytest.mark.asyncio
    @patch("congress_mcp.client.asyncio.sleep", new_callable=AsyncMock)
    async def test_retry_respects_retry_after_header(self, mock_sleep: AsyncMock, config: Config) -> None:
        """Retry-After header value is used as delay."""
        rate_limit_response = MagicMock()
        rate_limit_response.status_code = 429
        rate_limit_response.headers = {"Retry-After": "5"}

        ok_response = MagicMock()
        ok_response.status_code = 200
        ok_response.json.return_value = {"bills": []}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(
                side_effect=[rate_limit_response, ok_response]
            )
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client

            async with CongressClient(config) as client:
                result = await client.get("/bill/118")

            assert result == {"bills": []}
            mock_sleep.assert_called_once_with(5.0)

    @pytest.mark.asyncio
    @patch("congress_mcp.client.asyncio.sleep", new_callable=AsyncMock)
    async def test_no_retry_on_non_429(self, mock_sleep: AsyncMock, config: Config) -> None:
        """Non-429 errors are not retried."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not found"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client

            async with CongressClient(config) as client:
                with pytest.raises(NotFoundError):
                    await client.get("/bill/999/hr/99999")

            assert mock_client.get.call_count == 1
            mock_sleep.assert_not_called()

    @pytest.mark.asyncio
    @patch("congress_mcp.client.asyncio.sleep", new_callable=AsyncMock)
    async def test_retry_with_zero_max_retries(self, mock_sleep: AsyncMock) -> None:
        """With max_retries=0, 429 raises immediately with no sleep."""
        no_retry_config = Config(
            api_key="test_key",
            max_retries=0,
        )

        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client

            async with CongressClient(no_retry_config) as client:
                with pytest.raises(RateLimitError):
                    await client.get("/bill/118")

            assert mock_client.get.call_count == 1
            mock_sleep.assert_not_called()
