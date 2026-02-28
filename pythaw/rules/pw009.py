from __future__ import annotations

import ast

from pythaw.rules._base import Rule


class RequestsSessionRule(Rule):
    """Detect requests.Session() calls inside handler functions."""

    code = "PW009"
    message = "requests.Session() should be called at module scope"

    what = (
        "Detects `requests.Session()` calls inside Lambda handler functions. "
        "These calls create HTTP session instances with connection pooling, "
        "which involves resource allocation and cookie jar initialization."
    )

    why = (
        "Creating a requests Session inside the handler means it is re-created on "
        "every invocation. Moving it to module scope allows AWS Lambda to reuse "
        "the session and its connection pool across warm invocations, significantly "
        "reducing cold-start latency."
    )

    example = (
        "# NG\n"
        "def handler(event, context):\n"
        "    session = requests.Session()  # Created every invocation\n"
        "\n"
        "# OK\n"
        "session = requests.Session()  # Created once at module load\n"
        "\n"
        "def handler(event, context):\n"
        "    session.get('https://...')\n"
    )

    def check(self, node: ast.Call) -> bool:
        return (
            isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "requests"
            and node.func.attr == "Session"
        )
