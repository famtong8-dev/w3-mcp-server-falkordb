#!/usr/bin/env python3
"""MCP server for graph database operations with FalkorDB."""

import json
import os
import sys
import asyncio
from enum import Enum
from typing import Optional, Any, Dict, List
from contextlib import asynccontextmanager
from urllib.parse import urlparse

from mcp.server.fastmcp import FastMCP, Context
from pydantic import BaseModel, Field, field_validator, ConfigDict

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

# Configuration from environment variables
FALKORDB_URL = os.environ.get("FALKORDB_URL", "redis://localhost:6379")
FALKORDB_PASSWORD = os.environ.get("FALKORDB_PASSWORD", "")


def parse_redis_url(url: str) -> tuple:
    """Parse Redis/FalkorDB URL to host and port."""
    # Handle both redis:// and http:// URLs
    if url.startswith("http://"):
        url = url.replace("http://", "redis://")
    if url.startswith("https://"):
        url = url.replace("https://", "redis://")

    if not url.startswith("redis://"):
        url = f"redis://{url}"

    parsed = urlparse(url)
    host = parsed.hostname or "localhost"
    port = parsed.port or 6379
    password = parsed.password or FALKORDB_PASSWORD or None

    return host, port, password


def parse_falkordb_result(result: Any) -> Dict[str, Any]:
    """Parse FalkorDB GRAPH.QUERY result format.

    FalkorDB returns: [columns, rows, stats]
    - columns: list of column names
    - rows: list of row data (each row is a list)
    - stats: list of execution stats
    """
    if not isinstance(result, (list, tuple)) or len(result) < 2:
        return {"raw": result}

    columns = result[0] if isinstance(result[0], list) else []
    rows = result[1] if len(result) > 1 and isinstance(result[1], list) else []
    stats = result[2] if len(result) > 2 else None

    # Convert rows to dicts if we have columns
    if columns and rows:
        formatted_rows = []
        for row in rows:
            if isinstance(row, (list, tuple)):
                row_dict = {columns[i]: row[i] if i < len(row) else None for i in range(len(columns))}
                formatted_rows.append(row_dict)
            else:
                formatted_rows.append(row)
        return {
            "columns": columns,
            "rows": formatted_rows,
            "stats": stats,
            "count": len(formatted_rows)
        }

    return {"raw": result}


async def execute_query(graph: str, query: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Execute a Cypher query against FalkorDB using Redis protocol."""
    if not REDIS_AVAILABLE:
        raise ValueError("redis package not installed. Install with: pip install redis")

    client = None
    try:
        host, port, password = parse_redis_url(FALKORDB_URL)

        # Connect to FalkorDB via Redis protocol
        if password:
            redis_url = f"redis://:{password}@{host}:{port}"
        else:
            redis_url = f"redis://{host}:{port}"

        client = await redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=10,
            socket_keepalive=True,
        )

        # Execute Cypher query using FalkorDB GRAPH.QUERY command
        # Format: GRAPH.QUERY <graph_name> "<query_string>"
        # Returns: [columns, rows, stats]
        try:
            result = await client.execute_command("GRAPH.QUERY", graph, query)
        except Exception as cmd_error:
            # Try alternative format
            error_msg = str(cmd_error)
            if "ERR unknown command" in error_msg or "ERR wrong number of arguments" in error_msg:
                raise ValueError(f"FalkorDB command error: {error_msg}")
            raise

        # Parse the result
        parsed_result = parse_falkordb_result(result)

        return {
            "success": True,
            "data": parsed_result,
            "graph": graph,
            "__raw__": result,  # Internal only, not serialized
        }

    except Exception as e:
        raise ValueError(f"Failed to execute query on FalkorDB at {FALKORDB_URL}: {str(e)}")
    finally:
        if client:
            await client.aclose()


@asynccontextmanager
async def app_lifespan(app):
    """Manage FalkorDB connection lifecycle."""
    if not REDIS_AVAILABLE:
        print("⚠ Warning: redis package not installed. Install with: pip install redis", file=sys.stderr)
        yield {}
        return

    # Test connection
    try:
        host, port, password = parse_redis_url(FALKORDB_URL)
        print(f"🔗 Testing FalkorDB connection at {host}:{port}...", file=sys.stderr)

        if password:
            redis_url = f"redis://:{password}@{host}:{port}"
        else:
            redis_url = f"redis://{host}:{port}"

        client = await redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=5,
        )

        try:
            # Test ping
            pong = await client.ping()
            print(f"✓ FalkorDB is responding (ping: {pong})", file=sys.stderr)
            print(f"✓ FalkorDB connection is ready for queries", file=sys.stderr)
        finally:
            await client.aclose()

    except Exception as e:
        print(f"⚠ Warning: Could not verify FalkorDB connection: {e}", file=sys.stderr)

    yield {}


mcp = FastMCP("falkordb_mcp", lifespan=app_lifespan)


class ResponseFormat(str, Enum):
    """Output format options."""
    MARKDOWN = "markdown"
    JSON = "json"
    RAW = "raw"


class QueryInput(BaseModel):
    """Input for executing Cypher queries."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    query: str = Field(
        ...,
        description="Cypher query to execute",
        min_length=1,
        max_length=10000,
    )
    graph: str = Field(
        ...,
        description="Graph name to query (required)",
        min_length=1,
        max_length=255,
    )
    params: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Query parameters (variables)",
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.JSON,
        description="Output format: 'markdown', 'json', or 'raw'",
    )

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Query cannot be empty")
        return v.strip()

    @field_validator("graph")
    @classmethod
    def validate_graph(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Graph name cannot be empty")
        return v.strip()


class ListGraphsInput(BaseModel):
    """Input for listing graphs."""
    model_config = ConfigDict(extra="forbid")

    response_format: ResponseFormat = Field(
        default=ResponseFormat.JSON,
        description="Output format: 'markdown', 'json', or 'raw'",
    )


class GetNodesInput(BaseModel):
    """Input for getting node information."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    graph: str = Field(
        ...,
        description="Graph name to query (required)",
        min_length=1,
        max_length=255,
    )
    label: Optional[str] = Field(
        default=None,
        description="Node label to filter by (optional)",
        max_length=255,
    )
    limit: int = Field(
        default=10,
        description="Maximum number of nodes to return",
        ge=1,
        le=1000,
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.JSON,
        description="Output format: 'markdown', 'json', or 'raw'",
    )

    @field_validator("graph")
    @classmethod
    def validate_graph(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Graph name cannot be empty")
        return v.strip()


@mcp.tool(
    name="falkordb_query",
    annotations={
        "title": "Execute Cypher Query",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def falkordb_query(params: QueryInput, ctx: Context) -> str:
    """Execute a Cypher query against FalkorDB.

    Sends a Cypher query to FalkorDB and returns results in the specified format.
    Supports parameterized queries for safety and flexibility.

    Args:
        params (QueryInput): Validated parameters:
            - query (str): Cypher query to execute
            - graph (str): Graph name (required)
            - params (dict): Query parameters/variables
            - response_format (str): 'json', 'markdown', or 'raw'

    Returns:
        str: Formatted query results

    Examples:
        - Query: "MATCH (n:Person) RETURN n.name LIMIT 10"
        - Parameterized: "MATCH (n:Person {name: $name}) RETURN n"
        - With filter: Create index, match patterns, return results

    Errors:
        - Syntax error: "Invalid Cypher syntax"
        - Graph not found: "Graph 'xyz' does not exist"
        - Connection error: "Cannot connect to FalkorDB"
    """
    try:
        await ctx.info(f"Executing query on graph '{params.graph}'...")
        await ctx.info(f"Query: {params.query[:100]}...")

        result = await execute_query(params.graph, params.query, params.params)

        # Handle RAW format - return the unmodified server response
        if params.response_format == ResponseFormat.RAW:
            return json.dumps({
                "data": result.get("__raw__"),
                "graph": params.graph,
                "query": params.query
            }, indent=2, default=str)

        if params.response_format == ResponseFormat.JSON:
            # Remove internal fields before serializing
            clean_result = {k: v for k, v in result.items() if not k.startswith("__")}
            return json.dumps(clean_result, indent=2, default=str)
        else:
            # Markdown format
            markdown = f"## Query Results\n\n"
            markdown += f"Graph: `{params.graph}`\n"
            markdown += f"Status: {'✓ Success' if result.get('success') else '✗ Failed'}\n\n"

            if isinstance(result, dict) and result.get("success"):
                data = result.get("data", {})

                # Check for parsed FalkorDB result format
                if isinstance(data, dict) and "rows" in data:
                    rows = data.get("rows", [])
                    count = data.get("count", 0)
                    columns = data.get("columns", [])
                    stats = data.get("stats")

                    if count == 0:
                        markdown += "ℹ️  No results found."
                    else:
                        markdown += f"### Results — {count} row(s)\n\n"
                        if columns:
                            markdown += f"Columns: `{', '.join(columns)}`\n\n"

                        for i, row in enumerate(rows[:10], 1):
                            markdown += f"**Row {i}:**\n"
                            if isinstance(row, dict):
                                for k, v in row.items():
                                    if isinstance(v, (dict, list)):
                                        markdown += f"- **{k}:**\n  ```json\n  {json.dumps(v, indent=2, default=str)}\n  ```\n"
                                    elif v is None:
                                        markdown += f"- **{k}:** (null)\n"
                                    else:
                                        markdown += f"- **{k}:** `{v}`\n"
                            else:
                                markdown += f"- {row}\n"
                            markdown += "\n"

                        if count > 10:
                            markdown += f"ℹ️  Showing 10 of {count} results. Use LIMIT to show fewer.\n"

                        if stats:
                            markdown += f"\n### Execution Stats\n"
                            for stat in stats:
                                markdown += f"- {stat}\n"
                else:
                    # Fallback for raw data
                    if not data or (isinstance(data, (dict, list)) and len(data) == 0):
                        markdown += "ℹ️  No results found."
                    else:
                        markdown += f"```json\n{json.dumps(data, indent=2, default=str)}\n```\n"
            else:
                error_msg = result.get("message", "Unknown error")
                markdown += f"❌ Error: {error_msg}\n"

            return markdown

    except Exception as e:
        await ctx.error(f"Query execution failed: {type(e).__name__}: {e}")
        return json.dumps({
            "error": "Query execution failed",
            "message": str(e),
            "type": type(e).__name__
        })


@mcp.tool(
    name="falkordb_get_nodes",
    annotations={
        "title": "Get Node Information",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def falkordb_get_nodes(params: GetNodesInput, ctx: Context) -> str:
    """Get node information from a graph.

    Retrieves nodes from the specified graph, optionally filtered by label.
    Returns node IDs, labels, and properties.

    Args:
        params (GetNodesInput): Validated parameters:
            - graph (str): Graph name (required)
            - label (str): Optional node label filter
            - limit (int): Max nodes to return (1-1000, default: 10)
            - response_format (str): 'json' or 'markdown'

    Returns:
        str: Formatted list of nodes with metadata

    Errors:
        - Graph not found: "Graph 'xyz' does not exist"
        - Connection error: "Cannot connect to FalkorDB"
    """
    try:
        await ctx.info(f"Fetching nodes from graph '{params.graph}'...")

        # Build query
        if params.label:
            query = f"MATCH (n:{params.label}) RETURN n LIMIT {params.limit}"
        else:
            query = f"MATCH (n) RETURN n LIMIT {params.limit}"

        result = await execute_query(params.graph, query)

        if params.response_format == ResponseFormat.JSON:
            return json.dumps(result, indent=2, default=str)
        else:
            # Markdown format
            markdown = f"## Nodes in Graph '{params.graph}'\n\n"
            if params.label:
                markdown += f"🏷️  Label Filter: `{params.label}`\n"
            markdown += f"📊 Limit: {params.limit}\n\n"

            if isinstance(result, dict) and result.get("success"):
                data = result.get("data", [])
                if isinstance(data, (list, tuple)):
                    if len(data) == 0:
                        markdown += "ℹ️  No nodes found."
                        if params.label:
                            markdown += f" Try a different label or remove the filter."
                    else:
                        markdown += f"✓ Found {len(data)} node(s):\n\n"
                        for i, node in enumerate(data, 1):
                            markdown += f"### Node {i}\n"
                            if isinstance(node, dict):
                                for key, value in node.items():
                                    if isinstance(value, dict):
                                        markdown += f"- **{key}:**\n  ```json\n  {json.dumps(value, indent=2, default=str)}\n  ```\n"
                                    elif isinstance(value, list):
                                        markdown += f"- **{key}:** [{len(value)} items]\n"
                                    elif value is None:
                                        markdown += f"- **{key}:** (null)\n"
                                    else:
                                        markdown += f"- **{key}:** `{value}`\n"
                            elif isinstance(node, (list, tuple)):
                                for j, item in enumerate(node):
                                    markdown += f"- Column {j}: `{item}`\n"
                            else:
                                markdown += f"- {node}\n"
                            markdown += "\n"
                else:
                    markdown += "### Raw Data\n\n"
                    markdown += f"```json\n{json.dumps(data, indent=2, default=str)}\n```\n"
            else:
                error_msg = result.get("message", "Unknown error")
                markdown += f"❌ Error: {error_msg}\n"

            return markdown

    except Exception as e:
        await ctx.error(f"Failed to get nodes: {type(e).__name__}: {e}")
        return json.dumps({
            "error": "Failed to get nodes",
            "message": str(e),
            "type": type(e).__name__
        })


@mcp.tool(
    name="falkordb_list_graphs",
    annotations={
        "title": "List Available Graphs",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def falkordb_list_graphs(params: ListGraphsInput, ctx: Context) -> str:
    """List all available graphs in FalkorDB.

    Retrieves information about all graphs currently stored in the FalkorDB instance.

    Args:
        params (ListGraphsInput): Validated parameters:
            - response_format (str): 'markdown' or 'json'

    Returns:
        str: Formatted list of graphs

    Errors:
        - Connection error: "Cannot connect to FalkorDB"
    """
    try:
        await ctx.info("Fetching available graphs from FalkorDB...")

        if not REDIS_AVAILABLE:
            raise ValueError("redis package not installed")

        host, port, password = parse_redis_url(FALKORDB_URL)

        if password:
            redis_url = f"redis://:{password}@{host}:{port}"
        else:
            redis_url = f"redis://{host}:{port}"

        client = await redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=10,
        )

        try:
            # Try to list graphs using SCAN command to find graph keys
            # FalkorDB stores graphs as Redis keys
            graphs = []
            cursor = 0
            pattern = "*"

            # Use SCAN to iterate through keys
            while True:
                cursor, keys = await client.scan(cursor=cursor, match=pattern, count=100)

                # Filter keys that look like graph keys (exclude internal Redis keys)
                for key in keys:
                    if not key.startswith("_"):  # Exclude internal keys
                        graphs.append(key)

                if cursor == 0:
                    break

            # Try to get stats for each graph
            graph_details = []
            for graph_name in graphs[:50]:  # Limit to first 50 to avoid too much output
                try:
                    result = await client.execute_command("GRAPH.QUERY", graph_name, "RETURN 1 AS test")
                    graph_details.append({
                        "name": graph_name,
                        "status": "accessible"
                    })
                except:
                    # Graph key exists but might not be a valid graph
                    graph_details.append({
                        "name": graph_name,
                        "status": "inaccessible"
                    })

            graph_info = {
                "url": FALKORDB_URL,
                "status": "connected",
                "graphs": graph_details,
                "total_count": len(graphs)
            }

            if params.response_format == ResponseFormat.JSON:
                return json.dumps(graph_info, indent=2, default=str)
            else:
                markdown = "## FalkorDB Graphs\n\n"
                markdown += f"🔗 Server: `{FALKORDB_URL}`\n"
                markdown += f"✓ Status: Connected\n"
                markdown += f"📊 Total Graphs: {len(graph_details)}\n\n"

                if graph_details:
                    markdown += "### Available Graphs\n\n"
                    for i, graph in enumerate(graph_details, 1):
                        status_icon = "✓" if graph["status"] == "accessible" else "⚠"
                        markdown += f"{i}. **{graph['name']}** - {status_icon} {graph['status']}\n"
                else:
                    markdown += "ℹ️ No graphs found in FalkorDB.\n"

                return markdown

        finally:
            await client.aclose()

    except Exception as e:
        await ctx.error(f"Failed to list graphs: {type(e).__name__}: {e}")
        return json.dumps({
            "error": "Failed to list graphs",
            "message": str(e),
            "type": type(e).__name__
        })


def main():
    """Entry point for the MCP server."""
    try:
        mcp.run()
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
