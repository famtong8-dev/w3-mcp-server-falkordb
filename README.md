# W3 MCP FalkorDB Server

MCP server for graph database operations using [FalkorDB](https://www.falkordb.com/) - a high-performance graph database via Redis protocol.

**Status:** ✅ Production Ready

## Features

- **falkordb_query** - Execute parameterized Cypher queries with JSON/Markdown/RAW output formats
- **falkordb_get_nodes** - Retrieve and filter nodes by label with configurable limits
- **falkordb_list_graphs** - List all available graphs and their accessibility status

All tools support multiple output formats (JSON, Markdown, RAW) for flexible integration with different clients.

## Quick Start

### 1. Prerequisites Setup

#### FalkorDB Server

```bash
# Using Docker (Recommended)
docker run -p 6379:6379 falkordb/falkordb:latest

# Or using docker-compose
docker-compose up -d
```

Or install locally: [FalkorDB Quick Start](https://docs.falkordb.com/quickstart)

### 2. Clean Setup (Important!)

```bash
cd /path/to/w3-mcp-server-falkordb

# Remove old lockfile and venv
rm -rf uv.lock .venv venv

# Unset old environment variable
unset VIRTUAL_ENV
```

### 3. Install Dependencies

```bash
# Install Python dependencies (using uv)
uv sync

# (Optional) Install MCP CLI for dev inspector
uv pip install 'mcp[cli]'
```

### 4. Configure Environment

Create a `.env` file or export environment variables:

```bash
# FalkorDB (supports redis://, http://, and https:// schemes)
export FALKORDB_URL=redis://localhost:6379
export FALKORDB_PASSWORD=  # Optional if using authentication

# Or create .env file
cat > .env << EOF
FALKORDB_URL=redis://localhost:6379
FALKORDB_PASSWORD=
EOF
```

### 5. Verify Installation

```bash
# Check FalkorDB health
curl http://localhost:6379/health 2>/dev/null || echo "FalkorDB running on port 6379"

# Check Python env
uv run python -c "from mcp.server.fastmcp import FastMCP; print('✓ MCP ready')"
```

### 6. Test with MCP Dev Inspector (Optional)

For interactive testing with a web UI:

```bash
# Start MCP dev inspector (requires MCP CLI)
uv run mcp dev server.py
```

Opens URL like: `http://localhost:5173`

Features:

- ✅ Available tools listed with schemas
- ✅ Test each tool interactively with JSON input
- ✅ Real-time request/response viewing
- ✅ Server logs and debugging

**Note:** If you just want to run the server for Claude Code integration, use `uv run python server.py` instead.

## Usage

### Option A: Direct Python (Recommended)

Simplest way to run the server:

```bash
cd /path/to/w3-mcp-server-falkordb

# Run server (stdio mode)
uv run python server.py
```

### Option B: MCP Dev Inspector (Development)

Best way to test and debug interactively:

```bash
cd /path/to/w3-mcp-server-falkordb

# Start MCP dev inspector (requires MCP CLI)
uv run mcp dev server.py
```

Opens web UI at `http://localhost:5173`:

- See available tools and schemas
- Test each tool with JSON input
- View request/response in real-time
- See server logs

### Option C: Claude Code Integration

#### Method 1: From PyPI (When Published)

```bash
pip install w3-mcp-server-falkordb
# or
uv pip install w3-mcp-server-falkordb
```

Edit `~/.claude/claude_config.json`:

```json
{
  "mcpServers": {
    "falkordb": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--with", "w3-mcp-server-falkordb", "w3-mcp-server-falkordb"],
      "env": {
        "FALKORDB_URL": "redis://localhost:6379",
        "FALKORDB_PASSWORD": ""
      }
    }
  }
}
```

#### Method 2: From Local Source

Edit `~/.claude/claude_config.json`:

```json
{
  "mcpServers": {
    "falkordb": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "server.py"],
      "cwd": "/path/to/w3-mcp-server-falkordb",
      "env": {
        "FALKORDB_URL": "redis://localhost:6379",
        "FALKORDB_PASSWORD": ""
      }
    }
  }
}
```

Then restart Claude Code.

## Tools Documentation

### Tool Behavior & Safety

| Tool | Read-Only | Idempotent | Safe |
| --- | --- | --- | --- |
| **falkordb_query** | ❌ No (supports writes) | ❌ No | ⚠️ Use params for safety |
| **falkordb_get_nodes** | ✅ Yes (read-only) | ✅ Yes | ✅ Safe |
| **falkordb_list_graphs** | ✅ Yes (read-only) | ✅ Yes | ✅ Safe |

### falkordb_query

Execute a Cypher query against FalkorDB with optional parameterization.

**Parameters:**

- `query` (string, required): Cypher query to execute
- `graph` (string, required): Graph name to query
- `params` (object, optional): Query parameters/variables ($name, $value, etc.)
- `response_format` (string): "json", "markdown", or "raw" (default: "json")

**Examples:**

```json
{
  "query": "MATCH (n:Person) RETURN n.name, n.age LIMIT 10",
  "graph": "default",
  "response_format": "markdown"
}
```

```json
{
  "query": "MATCH (n:Person {name: $name}) RETURN n",
  "graph": "default",
  "params": {"name": "Alice"},
  "response_format": "json"
}
```

**Output (Markdown):**

```markdown
## Query Results

Graph: `default`
Status: ✓ Success

### Results — 2 row(s)

Columns: `name, age`

**Row 1:**
- **name:** `Alice`
- **age:** `30`

**Row 2:**
- **name:** `Bob`
- **age:** `25`
```

**Output (JSON):**

```json
{
  "success": true,
  "data": {
    "columns": ["name", "age"],
    "rows": [
      {"name": "Alice", "age": 30},
      {"name": "Bob", "age": 25}
    ],
    "count": 2,
    "stats": ["took 1.5 ms"]
  },
  "graph": "default"
}
```

---

### falkordb_get_nodes

Get node information from a graph with optional label filtering.

**Parameters:**

- `graph` (string, required): Graph name to query
- `label` (string, optional): Node label to filter by (e.g., "Person", "Company")
- `limit` (integer, 1-1000): Max nodes to return (default: 10)
- `response_format` (string): "json" or "markdown" (default: "json")

**Examples:**

```json
{
  "graph": "default",
  "label": "Person",
  "limit": 5,
  "response_format": "markdown"
}
```

**Output (Markdown):**

```markdown
## Nodes in Graph 'default'

🏷️  Label Filter: `Person`
📊 Limit: 5

✓ Found 5 node(s):

### Node 1
- **id:** `1`
- **name:** `Alice`
- **email:** `alice@example.com`
```

**Output (JSON):**

```json
{
  "success": true,
  "data": {
    "columns": ["n"],
    "rows": [
      {"n": {"id": 1, "name": "Alice", "email": "alice@example.com"}},
      {"n": {"id": 2, "name": "Bob", "email": "bob@example.com"}}
    ],
    "count": 2,
    "stats": []
  },
  "graph": "default"
}
```

---

### falkordb_list_graphs

List all available graphs in FalkorDB instance.

**Parameters:**

- `response_format` (string): "json" or "markdown" (default: "json")

**Example:**

```json
{
  "response_format": "json"
}
```

**Output (JSON):**

```json
{
  "url": "redis://localhost:6379",
  "status": "connected",
  "graphs": [
    {"name": "default", "status": "accessible"},
    {"name": "myapp", "status": "accessible"}
  ],
  "total_count": 2
}
```

**Output (Markdown):**

```markdown
## FalkorDB Graphs

🔗 Server: `redis://localhost:6379`
✓ Status: Connected
📊 Total Graphs: 2

### Available Graphs

1. **default** - ✓ accessible
2. **myapp** - ✓ accessible
```

## Configuration

### FALKORDB_URL

Specifies the connection URL for your FalkorDB server (supports http://, https://, and redis:// schemes).

**Default:** `redis://localhost:6379`

**Set via:**

1. **Environment variable:**

   ```bash
   export FALKORDB_URL=redis://localhost:6379
   uv run python server.py
   ```

2. **.env file:**

   ```bash
   FALKORDB_URL=redis://localhost:6379
   ```

3. **In claude_config.json:**

   ```json
   "env": {
     "FALKORDB_URL": "redis://localhost:6379"
   }
   ```

### FALKORDB_PASSWORD

Optional authentication password for FalkorDB.

**Default:** Empty (no authentication)

## Project Structure

```text
w3-mcp-server-falkordb/
├── server.py              # MCP server entry point
├── pyproject.toml         # Project config
├── .env.example           # Environment variables template
├── README.md              # This file
├── docker-compose.yml     # Docker setup (optional)
└── tests/
    └── test_mcp_server.py # Integration tests (optional)
```

## How It Works

### Architecture

```text
MCP Client (Claude, IDE, etc.)
    ↓
MCP Server (server.py)
    ↓
FalkorDB: graph queries
```

### Query Flow

1. **User provides Cypher query**
2. **Query is sent to FalkorDB**
3. **Results are formatted** and returned
4. **Output is displayed** in requested format

## Examples

### Query for nodes

```python
# Via Claude/MCP interface
falkordb_query(
    query="MATCH (n:Person) WHERE n.age > 25 RETURN n.name, n.age",
    graph="default",
    response_format="markdown"
)
```

### Get all Person nodes

```python
# Via Claude/MCP interface
falkordb_get_nodes(
    graph="default",
    label="Person",
    limit=20,
    response_format="json"
)
```

### Parameterized query (safe)

```python
# Via Claude/MCP interface
falkordb_query(
    query="MATCH (n:Person {email: $email}) RETURN n",
    graph="default",
    params={"email": "user@example.com"},
    response_format="json"
)
```

## Development

### Run tests

```bash
pytest tests/
```

### Code formatting

```bash
black server.py
ruff check server.py
```

### Interactive Testing

For development and debugging, use MCP dev inspector:

```bash
uv run mcp dev server.py
```

Web UI at `http://localhost:5173` provides:

- Tool definitions and JSON schemas
- Interactive tool testing
- Real-time request/response logs
- Server output and errors

## Performance Tips

- **Limit parameter**: Use `limit` to control result size and response time
- **Parameterized queries**: Always use `params` for dynamic values to avoid injection
- **Graph selection**: Use specific graph names instead of default when possible
- **Query optimization**: Create appropriate indexes in FalkorDB for frequently queried properties

## Troubleshooting

### FalkorDB connection error

```bash
# Check if FalkorDB is running
redis-cli ping

# Or test with curl (if HTTP endpoint available)
curl http://localhost:6379/

# Start FalkorDB with Docker
docker run -p 6379:6379 falkordb/falkordb:latest
```

### Query syntax error

- Verify Cypher query syntax
- Check FalkorDB documentation for supported syntax
- Test queries in FalkorDB console first

### Graph not found

- Ensure the graph exists in FalkorDB
- Verify you are specifying the correct `graph` parameter in your query
- Create graph through FalkorDB CLI or external tools if it doesn't exist

### Module import errors

```bash
# Clean reinstall
rm -rf .venv uv.lock
uv sync

# Verify installation
uv run python -c "from mcp.server.fastmcp import FastMCP; print('✓ MCP installed')"
```

### Server hangs on startup

- Check if FalkorDB server is running: `redis-cli ping`
- Verify FALKORDB_URL is correct (supports redis://, http://, https://)
- Try: `redis-cli -p 6379 ping`
- Check firewall/network connectivity to the FalkorDB server

## Cypher Query Examples

### Create nodes

```cypher
CREATE (p:Person {name: 'Alice', age: 30})
CREATE (c:Company {name: 'Tech Corp'})
```

### Create relationships

```cypher
MATCH (p:Person {name: 'Alice'})
MATCH (c:Company {name: 'Tech Corp'})
CREATE (p)-[:WORKS_AT]->(c)
```

### Query with filters

```cypher
MATCH (p:Person)
WHERE p.age > 25 AND p.age < 35
RETURN p.name, p.age
ORDER BY p.age DESC
LIMIT 10
```

### Complex queries

```cypher
MATCH (p:Person)-[:WORKS_AT]->(c:Company)
RETURN p.name, c.name, count(*) as employee_count
GROUP BY p.name, c.name
```

## Future Enhancements

- [ ] Node/Relationship creation tools
- [ ] Node/Relationship update and delete tools
- [ ] Batch operation support
- [ ] Graph creation/deletion utilities
- [ ] Transaction and rollback support
- [ ] Query performance metrics and analysis

## References

- [FalkorDB Documentation](https://docs.falkordb.com/)
- [Cypher Query Language](https://neo4j.com/developer/cypher/)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [FastMCP](https://github.com/anthropics/mcp-fastmcp)

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

For issues and questions, please visit:

- [GitHub Issues](https://github.com/famtong8-dev/w3-mcp-server-falkordb/issues)
- [FalkorDB Community](https://falkordb.com/community)
