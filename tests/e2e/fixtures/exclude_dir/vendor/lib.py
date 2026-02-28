"""OK: vendor/ は exclude で除外される."""
import boto3


def handler(event, context):
    """除外されるハンドラー."""
    boto3.client("s3")
