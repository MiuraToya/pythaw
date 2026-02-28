"""OK: ハンドラーではないユーティリティファイル."""
import boto3


def process_data(data):
    """データ処理（ハンドラーではない）."""
    client = boto3.client("s3")
    return client.put_object(Bucket="b", Key="k", Body=data)
