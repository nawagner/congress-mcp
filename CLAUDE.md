# Congress MCP Server

## Project Overview

MCP server providing access to U.S. Congress data via the [Congress.gov API v3](https://api.congress.gov/). Built with FastMCP and Pydantic.

## Tech Stack

- **Framework**: FastMCP >= 2.0.0 — [Docs](https://gofastmcp.com), [LLM reference](https://gofastmcp.com/llms.txt)
- **Validation**: Pydantic >= 2.0.0
- **HTTP Client**: httpx >= 0.27.0
- **Python**: 3.12+
- **Package Manager**: uv

## Key Directories

- `src/congress_mcp/` — Main source
  - `server.py` — Entry point, creates FastMCP instance
  - `client.py` — HTTP client with auth, pagination, and concurrent enrichment
  - `types/enums.py` — 7 enum types (BillType, Chamber, AmendmentType, etc.)
  - `tools/` — 18 modules, ~90 tool endpoints
  - `exceptions.py` — Custom exception hierarchy
- `tests/` — pytest test suite

## Common Commands

```bash
uv run pytest tests/              # Run all tests
uv run pytest tests/ -v           # Verbose test output
uv run python -m congress_mcp     # Start the MCP server
```

## FastMCP Patterns

- Tools use `@mcp.tool()` decorator with `Annotated[Type, Field(description=...)]`
- `ToolError` from `fastmcp.exceptions` controls error messages sent to LLM clients
- Middleware via `mcp.add_middleware()` can intercept tool calls with `on_call_tool`
- Enums: clients send values (`"hr"`), not names (`"HR"`); functions receive enum members
