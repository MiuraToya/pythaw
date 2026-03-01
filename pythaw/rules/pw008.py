from __future__ import annotations

import ast

from pythaw.rules._base import Rule


class HttpxClientRule(Rule):
    """Detect httpx.Client() calls inside handler functions."""

    code = "PW008"
    message = "httpx.Client() should be called at module scope"

    what = (
        "Detects `httpx.Client()` calls inside Lambda handler functions. "
        "These calls create HTTP client instances with connection pooling, "
        "which involves resource allocation and configuration."
    )

    why = (
        "Creating an httpx Client inside the handler means its connection pool is "
        "discarded after every invocation. Moving it to module scope allows AWS "
        "Lambda to reuse established TCP/TLS connections across warm invocations, "
        "avoiding repeated handshakes."
    )

    example = (
        "# NG\n"
        "def handler(event, context):\n"
        "    client = httpx.Client()  # Created every invocation\n"
        "\n"
        "# OK\n"
        "client = httpx.Client()  # Created once at module load\n"
        "\n"
        "def handler(event, context):\n"
        "    client.get('https://...')\n"
    )

    def check(self, node: ast.Call) -> bool:
        return (
            isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "httpx"
            and node.func.attr == "Client"
        )
