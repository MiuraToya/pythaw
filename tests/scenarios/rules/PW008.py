import httpx


def handler(event, context):
    client = httpx.Client()  # error: PW008


# OK: module scope
client = httpx.Client()


def handler_ok(event, context):
    client.get("https://example.com")
