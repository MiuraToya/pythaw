"""NG: ネストされた関数内で boto3 を呼ぶパターン."""
import boto3


def lambda_handler(event, context):
    """Lambda ハンドラー."""

    def get_client():
        return boto3.client("s3")

    client = get_client()
    return client.list_buckets()
