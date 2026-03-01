import boto3


def handler(event, context):
    session = boto3.Session()  # error: PW003


# OK: module scope
session = boto3.Session()


def handler_ok(event, context):
    client = session.client("s3")
