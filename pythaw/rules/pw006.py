from __future__ import annotations

import ast

from pythaw.rules._base import Rule


class RedisRule(Rule):
    """Detect redis.Redis() calls inside handler functions."""

    code = "PW006"
    message = "redis.Redis() should be called at module scope"

    what = (
        "Detects `redis.Redis()` calls inside Lambda handler functions. "
        "These calls create Redis client connections, which involves "
        "TCP handshake and connection pool setup."
    )

    why = (
        "Creating a Redis client inside the handler means it is re-created on "
        "every invocation. Moving it to module scope allows AWS Lambda to reuse "
        "the client across warm invocations, significantly reducing cold-start "
        "latency."
    )

    example = (
        "# NG\n"
        "def handler(event, context):\n"
        "    r = redis.Redis(host='...')  # Created every invocation\n"
        "\n"
        "# OK\n"
        "r = redis.Redis(host='...')  # Created once at module load\n"
        "\n"
        "def handler(event, context):\n"
        "    r.get('key')\n"
    )

    def check(self, node: ast.Call) -> bool:
        return (
            isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "redis"
            and node.func.attr == "Redis"
        )
