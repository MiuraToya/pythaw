from __future__ import annotations

import ast

from pythaw.rules._base import Rule


class Boto3SessionRule(Rule):
    """Detect boto3.Session() calls inside handler functions."""

    code = "PW003"
    message = "boto3.Session() should be called at module scope"

    what = (
        "Detects `boto3.Session()` calls inside Lambda handler functions. "
        "These calls create AWS sessions, which involves credential resolution "
        "and configuration loading."
    )

    why = (
        "Creating a boto3 Session inside the handler means it is re-created on "
        "every invocation. Session construction is expensive because it reads "
        "configuration files and resolves credentials. Moving it to module scope "
        "allows AWS Lambda to reuse the session across warm invocations, avoiding "
        "this overhead."
    )

    example = (
        "# NG\n"
        "def handler(event, context):\n"
        "    session = boto3.Session()  # Created every invocation\n"
        "\n"
        "# OK\n"
        "session = boto3.Session()  # Created once at module load\n"
        "\n"
        "def handler(event, context):\n"
        "    client = session.client('s3')\n"
    )

    def check(self, node: ast.Call) -> bool:
        """Return True if *node* is a ``boto3.Session(...)`` call."""
        return (
            isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "boto3"
            and node.func.attr == "Session"
        )
