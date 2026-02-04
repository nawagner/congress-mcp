"""Custom exceptions for Congress MCP server."""


class CongressAPIError(Exception):
    """Base exception for Congress.gov API errors."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class NotFoundError(CongressAPIError):
    """Resource not found (HTTP 404)."""

    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=404)


class RateLimitError(CongressAPIError):
    """Rate limit exceeded (HTTP 429).

    The Congress.gov API allows 5,000 requests per hour per API key.
    """

    def __init__(self, message: str = "Rate limit exceeded (5,000 requests/hour)") -> None:
        super().__init__(message, status_code=429)


class AuthenticationError(CongressAPIError):
    """Authentication failed (HTTP 401/403)."""

    def __init__(self, message: str = "Invalid or missing API key") -> None:
        super().__init__(message, status_code=401)


class ValidationError(CongressAPIError):
    """Invalid parameter value."""

    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=400)
