import requests


def handler(event, context):
    session = requests.Session()  # error: PW009


# OK: module scope
session = requests.Session()


def handler_ok(event, context):
    session.get("https://example.com")
