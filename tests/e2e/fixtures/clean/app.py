"""OK: モジュールレベルで boto3.client を呼ぶパターン."""
import boto3

client = boto3.client("s3")


def handler(event, context):
    """Lambda ハンドラー."""
    return client.get_object(Bucket="b", Key="k")
