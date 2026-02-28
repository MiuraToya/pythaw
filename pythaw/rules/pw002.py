from __future__ import annotations

import ast

from pythaw.rules._base import Rule


class Boto3ResourceRule(Rule):
    """Detect boto3.resource() calls inside handler functions."""

    code = "PW002"
    message = "boto3.resource() should be called at module scope"

    what = (
        "Detects `boto3.resource()` calls inside Lambda handler functions. "
        "These calls create AWS high-level resource objects, which involves "
        "HTTP connection setup and credential resolution."
    )

    why = (
        "Creating a boto3 resource inside the handler means it is re-created on "
        "every invocation. Moving it to module scope allows AWS Lambda to reuse "
        "the resource across warm invocations, significantly reducing cold-start "
        "latency."
    )

    example = (
        "# NG\n"
        "def handler(event, context):\n"
        "    s3 = boto3.resource('s3')  # Created every invocation\n"
        "\n"
        "# OK\n"
        "s3 = boto3.resource('s3')  # Created once at module load\n"
        "\n"
        "def handler(event, context):\n"
        "    s3.Bucket('my-bucket').download_file(...)\n"
    )

    def check(self, node: ast.Call) -> bool:
        return (
            isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "boto3"
            and node.func.attr == "resource"
        )
