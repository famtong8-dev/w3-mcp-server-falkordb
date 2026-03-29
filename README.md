# W3 MCP FalkorDB Server

Python MCP server for graph database operations using [FalkorDB](https://www.falkordb.com/) - a high-performance graph database.

**Status:** ✅ Ready for integration with FalkorDB

## Features

- **falkordb_query** - Execute Cypher queries against FalkorDB graphs
- **falkordb_get_nodes** - Retrieve and filter nodes from graphs
- **falkordb_list_graphs** - List available graphs and database information

Supports flexible output formats (Markdown or JSON) with parameterized queries for safety.

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

# Install MCP CLI dependencies
uv pip install 'mcp[cli]'
```

### 4. Configure Environment

Create a `.env` file or export environment variables:

```bash
# FalkorDB
export FALKORDB_URL=http://localhost:6379
export FALKORDB_PASSWORD=  # Optional if using authentication
export FALKORDB_GRAPH=default  # Default graph name

# Or create .env file
cat > .env << EOF
FALKORDB_URL=http://localhost:6379
FALKORDB_PASSWORD=
FALKORDB_GRAPH=default
EOF
```

### 5. Verify Installation

```bash
# Check FalkorDB health
curl http://localhost:6379/health 2>/dev/null || echo "FalkorDB running on port 6379"

# Check Python env
uv run python -c "from mcp.server.fastmcp import FastMCP; print('✓ MCP ready')"
```

### 6. Test with MCP Inspector

```bash
# Start MCP Inspector (interactive web UI)
uv run mcp dev server.py
```

Opens URL like:

```text
http://localhost:6274/?MCP_PROXY_AUTH_TOKEN=...
```

Features:

- ✅ Available tools listed in sidebar
- ✅ Test each tool interactively with JSON input
- ✅ Real-time request/response viewing
- ✅ Server logs and debugging
- ✅ No extra dependencies needed

## Usage

### Option A: MCP Inspector (Development)

Best way to test and debug:

```bash
cd /path/to/w3-mcp-server-falkordb

# Start inspector
uv run mcp dev server.py
```

Opens web UI at `http://localhost:5173`:

- See available tools
- Test each tool with JSON input
- View request/response in real-time
- See server logs

### Option B: Direct Python

```bash
# Run server (stdio mode)
uv run python server.py
```

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
        "FALKORDB_URL": "http://localhost:6379",
        "FALKORDB_GRAPH": "default",
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
        "FALKORDB_URL": "http://localhost:6379",
        "FALKORDB_GRAPH": "default",
        "FALKORDB_PASSWORD": ""
      }
    }
  }
}
```

Then restart Claude Code.

## Tools Documentation

### falkordb_query

Execute a Cypher query against FalkorDB.

**Parameters:**

- `query` (string, required): Cypher query to execute
- `graph` (string): Graph name (default: from FALKORDB_GRAPH env)
- `params` (object, optional): Query parameters/variables for safe parameterized queries
- `response_format` (string): "markdown" or "json" (default: "markdown")

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

**Output:**

Returns query results formatted as Markdown or JSON:

```markdown
## Query Results

Graph: `default`

Found 3 result(s):

### Result 1
- **name**: Alice
- **age**: 30

### Result 2
- **name**: Bob
- **age**: 25
```

---

### falkordb_get_nodes

Get node information from a graph.

**Parameters:**

- `graph` (string): Graph name (default: from FALKORDB_GRAPH env)
- `label` (string, optional): Node label to filter by (e.g., "Person", "Company")
- `limit` (integer, 1-1000): Max nodes to return (default: 10)
- `response_format` (string): "markdown" or "json" (default: "markdown")

**Examples:**

```json
{
  "graph": "default",
  "label": "Person",
  "limit": 5,
  "response_format": "markdown"
}
```

**Output:**

```markdown
## Nodes in Graph 'default'

Label: `Person`

Found 5 node(s):

### Node 1
- **id**: 1
- **name**: Alice
- **email**: alice@example.com
```

---

### falkordb_list_graphs

List all available graphs in FalkorDB.

**Parameters:**

- `response_format` (string): "markdown" or "json" (default: "markdown")

**Example:**

```json
{
  "response_format": "json"
}
```

**Output:**

```json
{
  "status": "connected",
  "default_graph": "default",
  "result": {}
}
```

## Configuration

### FALKORDB_URL

Specifies the URL of your FalkorDB server.

**Default:** `http://localhost:6379`

**Set via:**

1. **Environment variable:**

   ```bash
   export FALKORDB_URL=http://localhost:6379
   uv run python server.py
   ```

2. **.env file:**

   ```bash
   FALKORDB_URL=http://localhost:6379
   ```

3. **In claude_config.json:**

   ```json
   "env": {
     "FALKORDB_URL": "http://localhost:6379"
   }
   ```

### FALKORDB_PASSWORD

Optional authentication password for FalkorDB.

**Default:** Empty (no authentication)

### FALKORDB_GRAPH

Default graph name to use when not specified in queries.

**Default:** `default`

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

### Testing with MCP Inspector

```bash
uv run mcp dev server.py
```

Web UI at `http://localhost:5173` shows:

- Available tools and schemas
- Real-time request/response
- Server logs
- Interactive testing

## Performance Tips

- **Limit parameter**: Use `limit` to control result size and response time
- **Parameterized queries**: Always use `params` for dynamic values to avoid injection
- **Graph selection**: Use specific graph names instead of default when possible
- **Query optimization**: Create appropriate indexes in FalkorDB for frequently queried properties

## Troubleshooting

### FalkorDB connection error

```bash
# Check if FalkorDB is running
curl http://localhost:6379/health

# Start FalkorDB with Docker
docker run -p 6379:6379 falkordb/falkordb:latest
```

### Query syntax error

- Verify Cypher query syntax
- Check FalkorDB documentation for supported syntax
- Test queries in FalkorDB console first

### Graph not found

- Ensure graph exists in FalkorDB
- Check FALKORDB_GRAPH environment variable
- Create graph through FalkorDB CLI or external tools

### MCP module not found

```bash
# Install dependencies
uv sync

# Or manually
pip install mcp pydantic aiohttp
```

### Server hangs on startup

- Check if FalkorDB server is running and accessible
- Verify FALKORDB_URL is correct
- Try: `curl http://localhost:6379/health`

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

- [ ] Support for batch operations
- [ ] Graph creation/deletion tools
- [ ] Node/relationship creation and update tools
- [ ] Relationship traversal utilities
- [ ] Graph statistics and metadata tools
- [ ] Transaction support

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
