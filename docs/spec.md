# pythaw 仕様書

AWS Lambda の Python ハンドラーで、モジュールスコープに置くべき重い初期化処理がハンドラー関数内に書かれていないかを検出する静的解析 CLI ツール。

## Phase 1（個人開発者向け）

### CLI

```bash
pythaw check <path>      # ファイルまたはディレクトリをチェック
pythaw rules             # ビルトインルール一覧
pythaw rule <CODE>       # ルールの詳細説明（What / Why / Example）
```

### ビルトインルール

boto3 のみ。

| ID    | パターン           | 検出対象           |
|-------|-------------------|-------------------|
| PW001 | `boto3.client()`  | AWS SDK client    |
| PW002 | `boto3.resource()`| AWS SDK resource  |
| PW003 | `boto3.Session()` | AWS SDK session   |

### handler の特定

- トップレベル関数の名前を `fnmatch` でパターンマッチ
- デフォルトパターン: `handler`, `lambda_handler`, `*_handler`
- `pyproject.toml` で変更可能
- handler 内はネストされたクラス・関数も再帰的に検査

### 出力

concise 形式（`file:line:col: code message`）:

```
handler.py:15:4: PW001 boto3.client() should be called at module scope
handler.py:23:8: PW002 boto3.resource() should be called at module scope

Found 2 violations in 1 file.
```

### 終了コード

| コード | 意味 |
|--------|------|
| 0 | 問題なし |
| 1 | 違反あり |
| 2 | ツールエラー（設定不正等） |

### 設定

`pyproject.toml` の `[tool.pythaw]` セクション:

```toml
[tool.pythaw]
handler_patterns = ["handler", "lambda_handler"]
exclude = [".venv", "tests"]

[[tool.pythaw.custom_rules]]
pattern = "mylib.connect"
message = "mylib.connect() should be called at module scope"

[[tool.pythaw.custom_rules]]
pattern = "urllib3.PoolManager"
message = "urllib3.PoolManager() should be called at module scope"
```

### ルール詳細表示

`pythaw rule PW001` で以下を表示:

- **What it does** - 何をチェックするか
- **Why is this bad?** - なぜ問題か（コールドスタートの説明）
- **Example** - NG コード + OK コード

### ファイル検出

- `*.py` を再帰探索
- `.gitignore` 尊重
- `exclude` 設定で除外パターン指定

### エラーハンドリング

- パースエラー（壊れた Python ファイル）→ 報告して他ファイルは続行（終了コード 1）
- 設定エラー（pyproject.toml の不正）→ 即停止（終了コード 2）

---

## Phase 2（CI/チーム向け）

### CLI 追加オプション

```bash
pythaw check --select PW001,PW002   # 特定ルールのみ有効化
pythaw check --ignore PW003         # 特定ルール無効化
pythaw check --format json          # JSON 出力
pythaw check --format github        # GitHub Actions アノテーション
pythaw check --format sarif         # GitHub Code Scanning 連携
pythaw check --exit-zero            # 違反があっても終了コード 0
pythaw check --statistics           # ルール別違反数集計
```

### 追加ビルトインルール

| ID    | パターン               | 検出対象           |
|-------|------------------------|-------------------|
| PW004 | `pymysql.connect()`    | MySQL 接続        |
| PW005 | `psycopg2.connect()`   | PostgreSQL 接続   |
| PW006 | `redis.Redis()`        | Redis 接続        |
| PW007 | `redis.StrictRedis()`  | Redis 接続        |
| PW008 | `httpx.Client()`       | HTTP クライアント  |
| PW009 | `requests.Session()`   | HTTP セッション    |

### インライン抑制

```python
client = boto3.client("s3")  # nopw: PW001
```

### ファイルレベル抑制

```python
# pythaw: nocheck
```

### per-file-ignores

```toml
[tool.pythaw]
per-file-ignores = {"tests/*" = ["PW001"]}
```
