"""Shared tool annotations for Congress.gov MCP tools."""

# All Congress.gov tools are read-only API queries.
READONLY_ANNOTATIONS = {
    "readOnlyHint": True,
    "destructiveHint": False,
    "idempotentHint": True,
    "openWorldHint": True,
}
