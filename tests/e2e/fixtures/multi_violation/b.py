"""NG: handler 内で boto3.resource を呼ぶ."""
import boto3


def lambda_handler(event, context):
    """Lambda ハンドラー."""
    boto3.resource("dynamodb")
