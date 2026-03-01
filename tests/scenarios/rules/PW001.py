import boto3


def handler(event, context):
    client = boto3.client("s3")  # error: PW001


# OK: module scope
client = boto3.client("s3")


def handler_ok(event, context):
    client.get_object(Bucket="b", Key="k")
