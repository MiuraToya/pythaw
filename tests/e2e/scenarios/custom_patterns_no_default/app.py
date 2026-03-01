"""OK: デフォルトパターン handler はカスタム設定で無視される."""
import boto3


def handler(event, context):
    """Lambda ハンドラー."""
    boto3.client("s3")
