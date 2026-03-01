# pythaw

AWS Lambda handler 内の重い初期化処理やコネクションを伴うリソース生成を検出する Python 静的解析ツール。

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

## Call Graph Tracking

handler から呼び出されるローカル関数・クラスを再帰的に追跡し、間接的な違反も検出します。

| パターン | 例 |
|---------|---|
| 同一ファイルの関数呼び出し | `helper()` |
| モジュール経由の関数呼び出し | `infra.get_client()` |
| クラスメソッド呼び出し | `AwsProvider.get_client()` |
| クラスのインスタンス化 (`__init__`) | `S3Client()` |
| import 先のファイルへの追跡 | `from infra import get_client` |

```bash
$ pythaw check handler.py
infra/client.py:15:15: PW001 boto3.client() should be called at module scope
  → handler.py:5:13 AwsProvider.get_client()
```

`→` 行は handler からの呼び出し経路（call chain）を示します。

## Rules

| ID    | 検出対象 |
|-------|---------|
| PW001 | `boto3.client()` |
| PW002 | `boto3.resource()` |
| PW003 | `boto3.Session()` |
| PW004 | `pymysql.connect()` |
| PW005 | `psycopg2.connect()` |
| PW006 | `redis.Redis()` |
| PW007 | `redis.StrictRedis()` |
| PW008 | `httpx.Client()` |
| PW009 | `requests.Session()` |
