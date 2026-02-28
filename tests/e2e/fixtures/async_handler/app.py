"""NG: async ハンドラー内で boto3 を呼ぶパターン."""
import boto3


async def handler(event, context):
    """非同期 Lambda ハンドラー."""
    boto3.client("dynamodb")
