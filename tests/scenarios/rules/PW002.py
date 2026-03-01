import boto3


def handler(event, context):
    s3 = boto3.resource("s3")  # error: PW002


# OK: module scope
s3 = boto3.resource("s3")


def handler_ok(event, context):
    s3.Bucket("my-bucket").download_file("key", "/tmp/file")
