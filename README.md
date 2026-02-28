# pythaw

AWS Lambda handler 内の重い初期化処理を検出する Python 静的解析ツール。

## Install

```bash
pip install pythaw
```

## Example

```python
# handler.py

def lambda_handler(event, context):
    # NG: handler 内で boto3 クライアントを生成すると
    #     毎回初期化が走り、ウォームスタートの恩恵を受けられない
    client = boto3.client("s3")
    return client.get_object(Bucket="my-bucket", Key=event["key"])
```

```bash
$ pythaw check handler.py
handler.py:6:14: PW001 boto3.client() should be called at module scope

Found 1 violation in 1 file.
```

モジュールスコープに移動することで、Lambda のコンテナ再利用時に初期化をスキップできます。

```python
# handler.py (修正後)

client = boto3.client("s3")

def lambda_handler(event, context):
    return client.get_object(Bucket="my-bucket", Key=event["key"])
```

## Rules

| ID    | 検出対象 |
|-------|---------|
| PW001 | `boto3.client()` |
| PW002 | `boto3.resource()` |
| PW003 | `boto3.Session()` |
