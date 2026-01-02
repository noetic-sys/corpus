"""
Kuzu graph database tools for workflow agents.

Provides graph database capabilities for modeling and querying connected data.
"""

import json
from pathlib import Path

import kuzu
from claude_agent_sdk import tool

# Global database connection (initialized on first use)
_kuzu_db = None
_kuzu_conn = None


def get_database():
    """Get or create Kuzu graph database."""
    global _kuzu_db
    if _kuzu_db is None:
        # Store Kuzu database in scratch directory
        db_path = Path("/workspace/scratch/.kuzu_db")
        db_path.mkdir(parents=True, exist_ok=True)
        _kuzu_db = kuzu.Database(str(db_path))
    return _kuzu_db


def get_connection():
    """Get or create Kuzu connection."""
    global _kuzu_conn
    if _kuzu_conn is None:
        _kuzu_conn = kuzu.Connection(get_database())
    return _kuzu_conn


@tool(
    "kuzu_execute",
    "Execute Cypher query on in-memory Kuzu graph database. Supports node/relationship creation, queries, and graph operations. Returns query results as JSON.",
    {"cypher": str},
)
async def kuzu_execute(args):
    """Execute Cypher query on Kuzu graph database."""
    try:
        cypher = args.get("cypher", "")

        if not cypher:
            return {
                "content": [
                    {"type": "text", "text": "Error: Cypher query is required"}
                ],
                "isError": True,
            }

        conn = get_connection()
        result = conn.execute(cypher)

        # Check if query returns results
        if result.has_next():
            rows = []
            while result.has_next():
                row = result.get_next()
                rows.append(row)

            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {"rows": rows, "count": len(rows)}, indent=2
                        ),
                    }
                ]
            }
        else:
            # Query executed but no results (e.g., CREATE, MERGE)
            return {
                "content": [
                    {"type": "text", "text": "Query executed successfully. No results."}
                ]
            }

    except Exception as e:
        return {
            "content": [{"type": "text", "text": f"Kuzu error: {str(e)}"}],
            "isError": True,
        }


@tool(
    "kuzu_get_schema",
    "Get schema information for Kuzu graph database. Returns node tables, relationship tables, and their properties.",
    {},
)
async def kuzu_get_schema(args):
    """Get schema information from Kuzu graph database."""
    try:
        conn = get_connection()

        # Get all tables (nodes and relationships)
        result = conn.execute("CALL show_tables() RETURN *;")
        tables = []
        while result.has_next():
            row = result.get_next()
            tables.append(row)

        if not tables:
            return {
                "content": [
                    {"type": "text", "text": "No tables found. Database is empty."}
                ]
            }

        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {"tables": tables, "count": len(tables)}, indent=2
                    ),
                }
            ]
        }

    except Exception as e:
        return {
            "content": [{"type": "text", "text": f"Error: {str(e)}"}],
            "isError": True,
        }


def get_tools():
    """Return list of Kuzu tools."""
    return [kuzu_execute, kuzu_get_schema]
