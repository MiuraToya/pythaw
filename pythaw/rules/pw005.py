from __future__ import annotations

import ast

from pythaw.rules._base import Rule


class Psycopg2ConnectRule(Rule):
    """Detect psycopg2.connect() calls inside handler functions."""

    code = "PW005"
    message = "psycopg2.connect() should be called at module scope"

    what = (
        "Detects `psycopg2.connect()` calls inside Lambda handler functions. "
        "These calls establish PostgreSQL database connections, which involves "
        "TCP handshake and authentication."
    )

    why = (
        "Creating a PostgreSQL connection inside the handler means a TCP handshake "
        "and database authentication are performed on every invocation. Moving it "
        "to module scope allows AWS Lambda to reuse the connection across warm "
        "invocations, avoiding this overhead."
    )

    example = (
        "# NG\n"
        "def handler(event, context):\n"
        "    conn = psycopg2.connect(dsn='...')  # Created every invocation\n"
        "\n"
        "# OK\n"
        "conn = psycopg2.connect(dsn='...')  # Created once at module load\n"
        "\n"
        "def handler(event, context):\n"
        "    conn.cursor()\n"
    )

    def check(self, node: ast.Call) -> bool:
        return (
            isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "psycopg2"
            and node.func.attr == "connect"
        )
