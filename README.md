# pythaw

AWS Lambda handler 内の重い初期化処理を検出する Python 静的解析ツール。

## Install

```bash
pip install pythaw
```

## Usage

```bash
pythaw check handler.py
```

```
handler.py:15:4: PW001 boto3.client() should be called at module scope

Found 1 violation in 1 file.
```

## Rules

| ID    | 検出対象 |
|-------|---------|
| PW001 | `boto3.client()` |
| PW002 | `boto3.resource()` |
| PW003 | `boto3.Session()` |
