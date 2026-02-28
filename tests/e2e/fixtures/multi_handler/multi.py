"""NG: 複数ハンドラーがあるファイル."""
import boto3


def api_handler(event, context):
    """API 用ハンドラー."""
    boto3.client("s3")


def event_handler(event, context):
    """イベント処理用ハンドラー."""
    session = boto3.Session()
    sqs = session.client("sqs")
