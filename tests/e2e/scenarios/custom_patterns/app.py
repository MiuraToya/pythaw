"""NG: カスタムパターン process_* にマッチするハンドラー."""
import boto3


def process_data(event, context):
    """データ処理ハンドラー."""
    client = boto3.client("s3")
    return client.put_object(Bucket="b", Key="k", Body=event)
