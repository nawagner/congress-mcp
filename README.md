# Congress.gov MCP Server

A Model Context Protocol (MCP) server providing comprehensive access to the official [Congress.gov API (v3)](https://api.congress.gov). Built with [FastMCP](https://gofastmcp.com).

## Features

- **74 Tools** covering all Congress.gov API endpoints
- **8 Resources** for reference data and direct access
- Full async support for efficient concurrent requests
- Auto-pagination for large result sets
- Type-safe parameters with Pydantic validation
- Comprehensive error handling

## Data Available

- **Bills & Resolutions**: HR, S, HJRES, SJRES, HCONRES, SCONRES, HRES, SRES
- **Laws**: Public and private laws
- **Amendments**: House and Senate amendments
- **Members**: Current and historical members of Congress
- **Committees**: Committee membership, reports, prints, and meetings
- **Hearings**: Congressional hearing transcripts
- **Nominations**: Presidential nominations to the Senate
- **Treaties**: Treaty information and status
- **Congressional Record**: Daily and bound editions
- **CRS Reports**: Congressional Research Service reports
- **Roll Call Votes**: House voting records

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/congress-mcp.git
cd congress-mcp

# Install with pip
pip install -e .

# Or install with development dependencies
pip install -e ".[dev]"
```

## Configuration

### API Key

Get your free API key at [api.congress.gov/sign-up](https://api.congress.gov/sign-up/).

Set it as an environment variable:

```bash
export CONGRESS_API_KEY=your_api_key_here
```

Or create a `.env` file:

```bash
cp .env.example .env
# Edit .env with your API key
```

### Optional Settings

```bash
# API base URL (default: https://api.congress.gov/v3)
export CONGRESS_API_BASE_URL=https://api.congress.gov/v3

# Default pagination limit (default: 20)
export CONGRESS_DEFAULT_LIMIT=20

# Maximum pagination limit (default: 250)
export CONGRESS_MAX_LIMIT=250

# Request timeout in seconds (default: 30)
export CONGRESS_TIMEOUT=30.0
```

## Usage

### Claude Code Configuration

**Hosted server (recommended):**

```bash
claude mcp add --scope local --transport http congress-mcp-an https://congress-mcp-an.fastmcp.app/mcp
```

**Local installation:**

```bash
claude mcp add congress-mcp --env CONGRESS_API_KEY=your_api_key
```

### Cursor Configuration

Add to your Cursor MCP settings:

```json
{
  "congress-mcp-an": {
    "url": "https://congress-mcp-an.fastmcp.app/mcp"
  }
}
```

### Codex Configuration

```bash
codex mcp add --url https://congress-mcp-an.fastmcp.app/mcp congress-mcp-an
```

### Running the Server

```bash
# Using the installed command
congress-mcp

# Or using FastMCP directly
fastmcp run src/congress_mcp/server.py
```

## Example Queries

### Bills

```
# List recent bills from the 118th Congress
list_bills(congress=118, limit=10)

# Get a specific bill
get_bill(congress=118, bill_type="hr", bill_number=1)

# Get bill cosponsors
get_bill_cosponsors(congress=118, bill_type="hr", bill_number=1)

# Get bill text versions
get_bill_text(congress=118, bill_type="s", bill_number=1234)
```

### Members

```
# List current members
list_members(current_member=True, limit=50)

# Get member by bioguide ID
get_member(bioguide_id="P000197")

# Get legislation sponsored by a member
get_member_sponsored_legislation(bioguide_id="P000197")

# List members from California
list_members_by_state(state="CA", current_member=True)
```

### Committees

```
# List all committees
list_committees()

# Get House Judiciary Committee
get_committee(chamber="house", committee_code="hsju00")

# Get committee's bills
get_committee_bills(chamber="house", committee_code="hsju00")
```

### Nominations

```
# List nominations in 118th Congress
list_nominations(congress=118)

# Get nomination details
get_nomination(congress=118, nomination_number=1064)

# Get nomination hearings
get_nomination_hearings(congress=118, nomination_number=1064)
```

### Treaties

```
# List treaties
list_treaties(congress=118)

# Get treaty details
get_treaty(congress=118, treaty_number=3)
```

### Votes

```
# List House votes
list_house_votes(congress=118, session=1)

# Get specific vote
get_house_vote(congress=118, session=1, roll_call_number=100)

# Get how members voted
get_house_vote_members(congress=118, session=1, roll_call_number=100)
```

## Resources

Access reference data directly:

```
# API information
congress://api/info

# Bill type codes
congress://enums/bill-types

# Congress number reference
congress://reference/congress-numbers

# Direct bill access
congress://bill/118/hr/1

# Direct member access
congress://member/P000197
```

## Rate Limits

The Congress.gov API allows **5,000 requests per hour** per API key. The server does not implement caching, so plan accordingly for high-volume usage.

## Development

### Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=congress_mcp
```

### Code Quality

```bash
# Format code
ruff format .

# Lint code
ruff check .

# Type check
mypy src/
```

## API Reference

### Congress Numbers

| Congress | Years      | Notes |
|----------|------------|-------|
| 119th    | 2025-2027  | Current |
| 118th    | 2023-2025  | |
| 117th    | 2021-2023  | |
| 116th    | 2019-2021  | |

### Bill Types

| Code | Name | Description |
|------|------|-------------|
| hr | House Bill | General legislation from House |
| s | Senate Bill | General legislation from Senate |
| hjres | House Joint Resolution | Constitutional amendments, continuing resolutions |
| sjres | Senate Joint Resolution | Constitutional amendments, continuing resolutions |
| hconres | House Concurrent Resolution | Congressional sentiment, no force of law |
| sconres | Senate Concurrent Resolution | Congressional sentiment, no force of law |
| hres | House Simple Resolution | House matters only |
| sres | Senate Simple Resolution | Senate matters only |

### Amendment Types

| Code | Description |
|------|-------------|
| hamdt | House Amendment |
| samdt | Senate Amendment |
| suamdt | Senate Unprinted Amendment |

## License

Apache License 2.0 - see [LICENSE](LICENSE) for details.

## Links

- [Congress.gov API Documentation](https://api.congress.gov)
- [Congress.gov API GitHub](https://github.com/LibraryOfCongress/api.congress.gov)
- [FastMCP Documentation](https://gofastmcp.com)
- [MCP Specification](https://modelcontextprotocol.io)
