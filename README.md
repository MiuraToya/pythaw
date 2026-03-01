# pythaw

[日本語ドキュメント](README.ja.md)

A Python static analysis tool that detects heavy initialization and connection-establishing resource creation inside AWS Lambda handlers.

It recursively follows function calls from handler functions—including across imported files—to catch indirect violations.

## Requirements

Python 3.10 - 3.14 — matching the actively supported AWS Lambda Python runtimes.

## Install

```bash
# pip
pip install pythaw

# uv
uv add pythaw
```

## Quick Start

```python
# handler.py

def lambda_handler(event, context):
    # BAD: Creating a boto3 client inside the handler
    #      runs initialization on every invocation,
    #      losing the benefit of warm starts.
    client = boto3.client("s3")
    return client.get_object(Bucket="my-bucket", Key=event["key"])
```

```
$ pythaw check handler.py
infra/aws.py:7:15: PW001 boto3.client() should be called at module scope
  → handler.py:5:11 process()
    → service.py:5:13 S3Provider.get_client()

Found 1 violation in 1 file.
```

Move the client to module scope so Lambda container reuse skips the initialization:

```python
# handler.py (fixed)

client = boto3.client("s3")

def lambda_handler(event, context):
    return client.get_object(Bucket="my-bucket", Key=event["key"])
```

```
$ pythaw check handler.py
All checks passed!
```

## Usage

```bash
pythaw check <path>                    # Check a file or directory
pythaw check . --format json           # JSON output
pythaw check . --format github         # GitHub Actions annotation format
pythaw check . --format sarif          # SARIF format (Code Scanning integration)
pythaw check . --select PW001,PW002    # Enable only specific rules
pythaw check . --ignore PW003          # Disable specific rules
pythaw check . --exit-zero             # Always exit with code 0
pythaw check . --statistics            # Show per-rule violation counts
pythaw rules                           # List built-in rules
pythaw rule PW001                      # Show rule details
```

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | No violations found |
| 1 | Violations found |
| 2 | Tool error (invalid config, etc.) |

## Rules

| ID    | Detects |
|-------|---------|
| PW001 | `boto3.client()` |
| PW002 | `boto3.resource()` |
| PW003 | `boto3.Session()` |
| PW004 | `pymysql.connect()` |
| PW005 | `psycopg2.connect()` |
| PW006 | `redis.Redis()` |
| PW007 | `redis.StrictRedis()` |
| PW008 | `httpx.Client()` |
| PW009 | `requests.Session()` |

## Call Graph Traversal

pythaw recursively follows local function calls and imported modules from the handler, detecting indirect violations across files.

### Supported patterns

| Pattern | Example |
|---------|---------|
| Same-file function call | `helper()` |
| Module-qualified function call | `infra.get_client()` |
| Class method call | `AwsProvider.get_client()` |
| Class instantiation (`__init__`) | `S3Client()` |
| Cross-file import tracking | `from infra import get_client` |

> **Note:** Instance method calls via variables (e.g. `obj = Cls(); obj.method()`) are not tracked — this would require data-flow analysis beyond the current scope.

```
infra/aws.py:4:15: PW001 boto3.client() should be called at module scope
  → handler.py:2:10 get_client()

Found 1 violation in 1 file.
```

## Suppression

### Inline suppression

Append `# nopw: <code>` to a line to suppress that violation. Multiple codes can be comma-separated.

```python
client = boto3.client("s3")  # nopw: PW001
```

### File-level suppression

Add `# pythaw: nocheck` in the leading comment block to skip the entire file.

```python
# pythaw: nocheck
import boto3

def handler(event, context):
    boto3.client("s3")  # not checked
```

## Configuration

Configure via the `[tool.pythaw]` section in `pyproject.toml`.

```toml
[tool.pythaw]
# Function name patterns recognized as handlers (fnmatch syntax)
handler_patterns = ["handler", "lambda_handler", "*_handler"]

# Patterns to exclude from scanning
exclude = [".venv", "tests"]

# Disable specific rules per file pattern
[tool.pythaw.per-file-ignores]
"tests/*" = ["PW001", "PW002"]
"scripts/*" = ["PW001"]
```

## License

[MIT](LICENSE)
