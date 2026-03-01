"""NG: handler 内で boto3.client を呼ぶ."""
import boto3


def handler(event, context):
    """Lambda ハンドラー."""
    boto3.client("s3")
