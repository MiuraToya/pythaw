from __future__ import annotations

import ast

from pythaw.rules._base import Rule


class Boto3ClientRule(Rule):
    """Detect boto3.client() calls inside handler functions."""

    code = "PW001"
    message = "boto3.client() should be called at module scope"

    what = (
        "Detects `boto3.client()` calls inside Lambda handler functions. "
        "These calls create AWS service clients, which involves HTTP connection "
        "setup and credential resolution."
    )

    why = (
        "Creating a boto3 client inside the handler means it is re-created on "
        "every invocation. Client construction is expensive because it resolves "
        "credentials, discovers endpoints, and sets up HTTP connections. Moving "
        "it to module scope allows AWS Lambda to reuse the client across warm "
        "invocations, avoiding this overhead."
    )

    example = (
        "# NG\n"
        "def handler(event, context):\n"
        "    client = boto3.client('s3')  # Created every invocation\n"
        "\n"
        "# OK\n"
        "client = boto3.client('s3')  # Created once at module load\n"
        "\n"
        "def handler(event, context):\n"
        "    client.get_object(...)\n"
    )

    def check(self, node: ast.Call) -> bool:
        """Return True if *node* is a ``boto3.client(...)`` call."""
        return (
            isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "boto3"
            and node.func.attr == "client"
        )
