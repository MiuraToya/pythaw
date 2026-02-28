"""NG: handler 内で boto3.client を呼ぶパターン."""
import boto3


def handler(event, context):
    """Lambda ハンドラー."""
    client = boto3.client("s3")
    return client.list_buckets()
