"""
SQLite in-memory database tools for workflow agents.

Provides relational database capabilities for structuring and querying data.
"""

import json
import sqlite3

from claude_agent_sdk import tool

# Global connection (initialized on first use)
_sqlite_conn = None


def get_connection():
    """Get or create SQLite in-memory connection."""
    global _sqlite_conn
    if _sqlite_conn is None:
        _sqlite_conn = sqlite3.connect(":memory:")
        _sqlite_conn.row_factory = sqlite3.Row  # Return rows as dicts
    return _sqlite_conn


@tool(
    "sqlite_execute",
    "Execute SQL query on in-memory SQLite database. Supports DDL (CREATE TABLE, etc.) and DML (INSERT, UPDATE, DELETE, SELECT). Returns query results as JSON.",
    {"sql": str, "params": list},
)
async def sqlite_execute(args):
    """Execute SQL query on SQLite database."""
    try:
        sql = args.get("sql", "")
        params = args.get("params", [])

        # Handle case where params might be a JSON string
        if isinstance(params, str):
            try:
                params = json.loads(params)
            except (json.JSONDecodeError, ValueError):
                # If it's not valid JSON, treat as empty list
                params = []

        # Ensure params is a list
        if not isinstance(params, list):
            params = []

        if not sql:
            return {
                "content": [{"type": "text", "text": "Error: SQL query is required"}],
                "isError": True,
            }

        conn = get_connection()
        cursor = conn.cursor()

        # Execute query with parameters
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)

        # Commit if it's a write operation
        if (
            sql.strip()
            .upper()
            .startswith(("INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "ALTER"))
        ):
            conn.commit()
            affected_rows = cursor.rowcount
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Query executed successfully. Affected rows: {affected_rows}",
                    }
                ]
            }

        # Fetch results for SELECT queries
        rows = cursor.fetchall()
        columns = [description[0] for description in cursor.description]

        # Convert rows to list of dicts
        results = [dict(zip(columns, row)) for row in rows]

        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {"rows": results, "count": len(results)}, indent=2
                    ),
                }
            ]
        }

    except sqlite3.Error as e:
        return {
            "content": [{"type": "text", "text": f"SQLite error: {str(e)}"}],
            "isError": True,
        }
    except Exception as e:
        return {
            "content": [{"type": "text", "text": f"Error: {str(e)}"}],
            "isError": True,
        }


@tool(
    "sqlite_get_schema",
    "Get schema information for all tables in SQLite database. Returns table names and their CREATE TABLE statements.",
    {},
)
async def sqlite_get_schema(args):
    """Get schema information from SQLite database."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Get all tables
        cursor.execute(
            "SELECT name, sql FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = cursor.fetchall()

        if not tables:
            return {
                "content": [
                    {"type": "text", "text": "No tables found. Database is empty."}
                ]
            }

        schema_info = [
            {"table": table[0], "create_statement": table[1]} for table in tables
        ]

        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {"tables": schema_info, "count": len(schema_info)}, indent=2
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
    """Return list of SQLite tools."""
    return [sqlite_execute, sqlite_get_schema]
