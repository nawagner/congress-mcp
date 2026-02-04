"""Configuration management for Congress MCP server."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    """Server configuration loaded from environment variables."""

    api_key: str
    base_url: str = "https://api.congress.gov/v3"
    default_limit: int = 20
    max_limit: int = 250
    timeout: float = 30.0

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables.

        Required:
            CONGRESS_API_KEY: Your Congress.gov API key

        Optional:
            CONGRESS_API_BASE_URL: API base URL (default: https://api.congress.gov/v3)
            CONGRESS_DEFAULT_LIMIT: Default pagination limit (default: 20)
            CONGRESS_MAX_LIMIT: Maximum pagination limit (default: 250)
            CONGRESS_TIMEOUT: Request timeout in seconds (default: 30.0)

        Raises:
            ValueError: If CONGRESS_API_KEY is not set.
        """
        api_key = os.environ.get("CONGRESS_API_KEY")
        if not api_key:
            raise ValueError(
                "CONGRESS_API_KEY environment variable is required. "
                "Get your API key at https://api.congress.gov/sign-up/"
            )

        return cls(
            api_key=api_key,
            base_url=os.environ.get("CONGRESS_API_BASE_URL", cls.base_url),
            default_limit=int(os.environ.get("CONGRESS_DEFAULT_LIMIT", str(cls.default_limit))),
            max_limit=int(os.environ.get("CONGRESS_MAX_LIMIT", str(cls.max_limit))),
            timeout=float(os.environ.get("CONGRESS_TIMEOUT", str(cls.timeout))),
        )
