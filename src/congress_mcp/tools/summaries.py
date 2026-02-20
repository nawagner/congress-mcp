"""Summary tools for Congress.gov API."""

import logging
import re
from typing import Annotated, Any

import httpx
from pydantic import Field

from congress_mcp.annotations import READONLY_ANNOTATIONS
from congress_mcp.client import CongressClient
from congress_mcp.config import Config
from congress_mcp.types.enums import BillTypeLiteral

try:
    from fastmcp import FastMCP
except ImportError:
    FastMCP = Any  # type: ignore[misc, assignment]

logger = logging.getLogger(__name__)

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_HTML_ENTITIES = {
    "&amp;": "&",
    "&lt;": "<",
    "&gt;": ">",
    "&quot;": '"',
    "&#39;": "'",
    "&nbsp;": " ",
}


def _strip_html(text: str) -> str:
    """Remove HTML tags and decode common entities from summary text."""
    clean = _HTML_TAG_RE.sub("", text)
    for entity, char in _HTML_ENTITIES.items():
        clean = clean.replace(entity, char)
    return clean


def register_summary_tools(mcp: "FastMCP", config: Config) -> None:
    """Register all summary tools with the MCP server."""

    @mcp.tool(annotations=READONLY_ANNOTATIONS)
    async def list_summaries(
        from_date: Annotated[
            str | None, Field(description="Filter by update date start (YYYY-MM-DD)")
        ] = None,
        to_date: Annotated[
            str | None, Field(description="Filter by update date end (YYYY-MM-DD)")
        ] = None,
        sort: Annotated[
            str | None, Field(description="Sort order: updateDate+asc or updateDate+desc")
        ] = None,
        limit: Annotated[
            int | None, Field(description="Maximum results to return (1-250)", ge=1, le=250)
        ] = None,
        offset: Annotated[int, Field(description="Starting position for pagination", ge=0)] = 0,
    ) -> dict[str, Any]:
        """List recent bill summaries.

        Summaries are written by the Congressional Research Service (CRS)
        and describe bill content at various legislative stages.

        Tip: Without date filters, only a small window of recent results is returned.
        Provide from_date/to_date for comprehensive results.
        """
        async with CongressClient(config) as client:
            params: dict[str, Any] = {}
            if from_date:
                params["fromDateTime"] = f"{from_date}T00:00:00Z"
            if to_date:
                params["toDateTime"] = f"{to_date}T23:59:59Z"
            if sort:
                params["sort"] = sort
            return await client.get("/summaries", params=params, limit=limit, offset=offset)

    @mcp.tool(annotations=READONLY_ANNOTATIONS)
    async def list_summaries_by_congress(
        congress: Annotated[int, Field(description="Congress number (e.g., 118)", ge=1, le=200)],
        from_date: Annotated[
            str | None, Field(description="Filter by update date start (YYYY-MM-DD)")
        ] = None,
        to_date: Annotated[
            str | None, Field(description="Filter by update date end (YYYY-MM-DD)")
        ] = None,
        sort: Annotated[
            str | None, Field(description="Sort order: updateDate+asc or updateDate+desc")
        ] = None,
        limit: Annotated[
            int | None, Field(description="Maximum results to return (1-250)", ge=1, le=250)
        ] = None,
        offset: Annotated[int, Field(description="Starting position for pagination", ge=0)] = 0,
    ) -> dict[str, Any]:
        """List bill summaries for a specific Congress.

        Returns CRS summaries for bills introduced in the specified Congress.

        Tip: Without date filters, only the current Congress returns results.
        For past Congresses, provide from_date/to_date.
        """
        async with CongressClient(config) as client:
            params: dict[str, Any] = {}
            if from_date:
                params["fromDateTime"] = f"{from_date}T00:00:00Z"
            if to_date:
                params["toDateTime"] = f"{to_date}T23:59:59Z"
            if sort:
                params["sort"] = sort
            return await client.get(
                f"/summaries/{congress}",
                params=params,
                limit=limit,
                offset=offset,
            )

    @mcp.tool(annotations=READONLY_ANNOTATIONS)
    async def list_summaries_by_type(
        congress: Annotated[int, Field(description="Congress number (e.g., 118)", ge=1, le=200)],
        bill_type: Annotated[
            BillTypeLiteral,
            Field(description="REQUIRED bill type string. Must be one of: hr, s, hjres, sjres, hconres, sconres, hres, sres. Example: 'hr' for H.R. bills"),
        ],
        from_date: Annotated[
            str | None, Field(description="Filter by update date start (YYYY-MM-DD)")
        ] = None,
        to_date: Annotated[
            str | None, Field(description="Filter by update date end (YYYY-MM-DD)")
        ] = None,
        sort: Annotated[
            str | None, Field(description="Sort order: updateDate+asc or updateDate+desc")
        ] = None,
        limit: Annotated[
            int | None, Field(description="Maximum results to return (1-250)", ge=1, le=250)
        ] = None,
        offset: Annotated[int, Field(description="Starting position for pagination", ge=0)] = 0,
    ) -> dict[str, Any]:
        """List bill summaries filtered by Congress and bill type.

        Returns CRS summaries for the specified type of legislation.

        Tip: Without date filters, only the current Congress returns results.
        For past Congresses, provide from_date/to_date.
        """
        async with CongressClient(config) as client:
            params: dict[str, Any] = {}
            if from_date:
                params["fromDateTime"] = f"{from_date}T00:00:00Z"
            if to_date:
                params["toDateTime"] = f"{to_date}T23:59:59Z"
            if sort:
                params["sort"] = sort
            return await client.get(
                f"/summaries/{congress}/{bill_type}",
                params=params,
                limit=limit,
                offset=offset,
            )

    @mcp.tool(annotations=READONLY_ANNOTATIONS)
    async def search_summaries(
        congress: Annotated[int, Field(description="Congress number (e.g., 118)", ge=1, le=200)],
        query: Annotated[
            str,
            Field(
                description="Keyword or phrase to search for in summary text (case-insensitive)",
                min_length=2,
            ),
        ],
        bill_type: Annotated[
            BillTypeLiteral | None,
            Field(
                description="Optional bill type filter: hr, s, hjres, sjres, hconres, sconres, hres, sres"
            ),
        ] = None,
        from_date: Annotated[
            str | None, Field(description="Filter by update date start (YYYY-MM-DD)")
        ] = None,
        to_date: Annotated[
            str | None, Field(description="Filter by update date end (YYYY-MM-DD)")
        ] = None,
        max_matches: Annotated[
            int,
            Field(description="Maximum matching summaries to return (default 50)", ge=1, le=500),
        ] = 50,
    ) -> dict[str, Any]:
        """Search bill summaries by keyword with automatic pagination.

        Fetches all summaries for the specified Congress and filters by keyword
        against the summary text. Handles pagination internally so the caller
        does not need to page through results manually.

        The search is case-insensitive and matches against the plain text
        content of each summary (HTML tags are stripped before matching).

        Tip: Provide bill_type to narrow results and speed up the search.
        For past Congresses, from_date/to_date are required for the API
        to return results.
        """
        async with CongressClient(config) as client:
            if bill_type:
                endpoint = f"/summaries/{congress}/{bill_type}"
            else:
                endpoint = f"/summaries/{congress}"

            params: dict[str, Any] = {}
            if from_date:
                params["fromDateTime"] = f"{from_date}T00:00:00Z"
            if to_date:
                params["toDateTime"] = f"{to_date}T23:59:59Z"

            query_lower = query.lower()
            matches: list[dict[str, Any]] = []
            total_searched = 0
            offset = 0
            batch_size = config.max_limit

            search_complete = True

            while True:
                try:
                    response = await client.get(
                        endpoint,
                        params=params,
                        limit=batch_size,
                        offset=offset,
                    )
                except httpx.HTTPError as exc:
                    logger.warning("HTTP error during search pagination: %s", exc)
                    search_complete = False
                    break

                summaries = response.get("summaries", [])
                total_searched += len(summaries)

                for summary in summaries:
                    text = summary.get("text", "")
                    plain_text = _strip_html(text)
                    if query_lower in plain_text.lower():
                        matches.append(summary)
                        if len(matches) >= max_matches:
                            break

                if len(matches) >= max_matches:
                    break

                pagination = response.get("pagination", {})
                total_count = pagination.get("count", 0)

                if offset + batch_size >= total_count or not summaries:
                    break

                offset += batch_size

            return {
                "matches": matches,
                "match_count": len(matches),
                "total_summaries_searched": total_searched,
                "search_complete": search_complete,
                "query": query,
            }
