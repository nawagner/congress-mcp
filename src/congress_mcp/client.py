"""Async HTTP client with authentication and auto-pagination for Congress.gov API."""

import asyncio
from typing import Any

import httpx

from .config import Config
from .exceptions import (
    AuthenticationError,
    CongressAPIError,
    NotFoundError,
    RateLimitError,
)


class CongressClient:
    """Async HTTP client for Congress.gov API.

    Handles authentication, error handling, and auto-pagination.

    Usage:
        async with CongressClient(config) as client:
            result = await client.get("/bill/118")
    """

    def __init__(self, config: Config) -> None:
        self.config = config
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "CongressClient":
        self._client = httpx.AsyncClient(
            base_url=self.config.base_url,
            timeout=self.config.timeout,
            headers={"Accept": "application/json"},
        )
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        if self._client:
            await self._client.aclose()

    async def get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Make an authenticated GET request to the Congress.gov API.

        Args:
            endpoint: API endpoint path (e.g., "/bill/118")
            params: Optional query parameters
            limit: Maximum results to return (1-250)
            offset: Starting position for pagination

        Returns:
            JSON response as a dictionary

        Raises:
            NotFoundError: Resource not found (404)
            RateLimitError: Rate limit exceeded (429)
            AuthenticationError: Invalid API key (401/403)
            CongressAPIError: Other API errors
        """
        if self._client is None:
            raise RuntimeError("Client not initialized. Use 'async with' context manager.")

        params = dict(params) if params else {}
        params["api_key"] = self.config.api_key
        params["format"] = "json"

        if limit is not None:
            params["limit"] = min(limit, self.config.max_limit)
        params["offset"] = offset

        response = await self._client.get(endpoint, params=params)

        if response.status_code == 404:
            raise NotFoundError(f"Resource not found: {endpoint}")
        if response.status_code == 429:
            raise RateLimitError()
        if response.status_code in (401, 403):
            raise AuthenticationError()
        if response.status_code != 200:
            raise CongressAPIError(
                f"API error {response.status_code}: {response.text}",
                status_code=response.status_code,
            )

        return response.json()

    async def get_all(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        max_results: int | None = None,
    ) -> dict[str, Any]:
        """Get all results with auto-pagination.

        Fetches multiple pages until all results are retrieved or max_results is reached.

        Args:
            endpoint: API endpoint path
            params: Optional query parameters
            max_results: Maximum total results to return (None for all)

        Returns:
            Dictionary with 'results' list and 'count' of total results
        """
        params = dict(params) if params else {}
        all_results: list[dict[str, Any]] = []
        offset = 0
        batch_size = min(max_results or self.config.max_limit, self.config.max_limit)

        while True:
            response = await self.get(
                endpoint,
                params=params,
                limit=batch_size,
                offset=offset,
            )

            # Extract results from response (API uses various top-level keys)
            results = self._extract_results(response)
            all_results.extend(results)

            # Check if we have enough or reached the end
            if max_results and len(all_results) >= max_results:
                all_results = all_results[:max_results]
                break

            pagination = response.get("pagination", {})
            total_count = pagination.get("count", 0)

            if offset + batch_size >= total_count or not results:
                break

            offset += batch_size

        return {"results": all_results, "count": len(all_results)}

    def _extract_results(self, response: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract results list from API response.

        The API returns results in various top-level keys depending on the endpoint.
        """
        # Check for common result keys
        result_keys = [
            "bills",
            "amendments",
            "members",
            "committees",
            "nominations",
            "treaties",
            "hearings",
            "reports",
            "summaries",
            "laws",
            "communications",
            "houseCommunications",
            "senateCommunications",
            "committeeMeetings",
            "committeePrints",
            "committeeReports",
            "congressionalRecord",
            "dailyCongressionalRecord",
            "boundCongressionalRecord",
            "houseRequirements",
            "crsReports",
            "houseVotes",
            "congresses",
            "results",
        ]

        for key in result_keys:
            if key in response:
                value = response[key]
                if isinstance(value, list):
                    return value

        return []

    async def fetch_details_concurrent(
        self,
        endpoints: list[str],
        max_concurrent: int = 25,
    ) -> list[dict[str, Any]]:
        """Fetch multiple detail endpoints concurrently.

        Args:
            endpoints: List of API endpoint paths to fetch
            max_concurrent: Maximum number of concurrent requests (default: 25)

        Returns:
            List of successful responses (failed requests are omitted)
        """
        # Limit to max_concurrent endpoints
        endpoints_to_fetch = endpoints[:max_concurrent]

        async def safe_get(endpoint: str) -> dict[str, Any] | None:
            """Fetch endpoint, returning None on error."""
            try:
                return await self.get(endpoint)
            except Exception:
                return None

        tasks = [safe_get(endpoint) for endpoint in endpoints_to_fetch]
        results = await asyncio.gather(*tasks)

        # Filter out None results (failed fetches)
        return [r for r in results if r is not None]

    async def enrich_list_response(
        self,
        list_response: dict[str, Any],
        result_key: str,
        detail_key: str,
        build_endpoint: callable,
        max_concurrent: int = 25,
    ) -> dict[str, Any]:
        """Enrich a list response by fetching details for each item.

        Args:
            list_response: The original list API response
            result_key: Key containing the list items (e.g., "hearings")
            detail_key: Key in detail response containing the item data (e.g., "hearing")
            build_endpoint: Function that takes a list item and returns the detail endpoint
            max_concurrent: Maximum concurrent detail fetches (default: 25)

        Returns:
            The list response with items enriched with detail data
        """
        items = list_response.get(result_key, [])
        if not items:
            return list_response

        # Build endpoints for each item
        endpoints = [build_endpoint(item) for item in items[:max_concurrent]]

        # Fetch all details concurrently
        details = await self.fetch_details_concurrent(endpoints, max_concurrent)

        # Create a map of endpoint -> detail data for merging
        detail_map: dict[str, dict[str, Any]] = {}
        for endpoint, detail_response in zip(endpoints, details):
            if detail_response and detail_key in detail_response:
                detail_map[endpoint] = detail_response[detail_key]

        # Merge detail data into list items
        enriched_items = []
        for i, item in enumerate(items):
            if i < len(endpoints) and endpoints[i] in detail_map:
                # Merge detail data into the item (detail data takes precedence)
                enriched_item = {**item, **detail_map[endpoints[i]]}
            else:
                enriched_item = item
            enriched_items.append(enriched_item)

        # Return updated response
        list_response[result_key] = enriched_items
        return list_response
