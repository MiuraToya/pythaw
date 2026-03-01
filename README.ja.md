# pythaw

AWS Lambda handler 内の重い初期化処理やコネクションを伴うリソース生成を検出する Python 静的解析ツール。

ハンドラー関数からの関数呼び出しを再帰的に辿り、import 先のファイルも含めて検出する。

## Install

```bash
# pip
pip install pythaw

# uv
uv add pythaw
```

## Quick Start

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

モジュールスコープに移動することで、Lambda のコンテナ再利用時に初期化をスキップできる。

```python
# handler.py (修正後)

client = boto3.client("s3")

def lambda_handler(event, context):
    return client.get_object(Bucket="my-bucket", Key=event["key"])
```

## Usage

```bash
pythaw check <path>                    # ファイルまたはディレクトリをチェック
pythaw check . --format json           # JSON 形式で出力
pythaw check . --format github         # GitHub Actions アノテーション形式
pythaw check . --format sarif          # SARIF 形式（Code Scanning 連携）
pythaw check . --select PW001,PW002    # 特定ルールのみ有効化
pythaw check . --ignore PW003          # 特定ルールを無効化
pythaw check . --exit-zero             # 違反があっても終了コード 0
pythaw check . --statistics            # ルール別違反数を集計表示
pythaw rules                           # ビルトインルール一覧
pythaw rule PW001                      # ルールの詳細説明
```

### 終了コード

| コード | 意味 |
|--------|------|
| 0 | 問題なし |
| 1 | 違反あり |
| 2 | ツールエラー（設定不正等） |

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

## Call Graph Traversal

ハンドラーが呼び出すローカル関数や import 先のモジュールも再帰的に辿り、間接的な違反を検出する。

```
infra/aws.py:4:15: PW001 boto3.client() should be called at module scope
  via handler.py:2:10 → get_client()

Found 1 violation in 1 file.
```

## Suppression

### インライン抑制

行末に `# nopw: <code>` を付けるとその行の違反を抑制できる。カンマ区切りで複数指定可能。

```python
client = boto3.client("s3")  # nopw: PW001
```

### ファイルレベル抑制

ファイル先頭のコメントブロック内に `# pythaw: nocheck` と記述するとファイル全体をスキップする。

```python
# pythaw: nocheck
import boto3

def handler(event, context):
    boto3.client("s3")  # チェックされない
```

## Configuration

`pyproject.toml` の `[tool.pythaw]` セクションで設定を行う。

```toml
[tool.pythaw]
# handler として認識する関数名パターン（fnmatch 形式）
handler_patterns = ["handler", "lambda_handler", "*_handler"]

# 探索対象から除外するパターン
exclude = [".venv", "tests"]

# ファイルパターンごとにルールを無効化
[tool.pythaw.per-file-ignores]
"tests/*" = ["PW001", "PW002"]
"scripts/*" = ["PW001"]
```

## License

[MIT](LICENSE)

## Development

```bash
uv sync                # 依存関係のインストール
uv run pytest          # テスト実行
uv run ruff check .    # リント
uv run ruff format .   # フォーマット
uv run mypy pythaw     # 型チェック
```
