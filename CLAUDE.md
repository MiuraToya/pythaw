# CLAUDE.md

## プロジェクト概要

pythaw は、AWS Lambda の Python ハンドラー内にある重い初期化処理を検出する静的解析 CLI ツール。
詳細な仕様は [docs/spec.md](docs/spec.md)、技術設計は [docs/design.md](docs/design.md) を参照。

## 期待する役割
- 静的解析ツールのスペシャリストとして、ASTのベストプラクティスや一般的なアプローチを用いて設計・実装をサポートする。

## 開発コマンド

```bash
# 依存関係のインストール
uv sync

# CLI実行
uv run pythaw check <path>

# テスト実行
uv run pytest

# リント
uv run ruff check .

# 型チェック
uv run mypy pythaw
```

## コミットメッセージ規約

```
<type>: <subject>
```

**type:**
- `feat:` 新機能
- `fix:` バグ修正
- `docs:` ドキュメント変更
- `refactor:` リファクタリング
- `test:` テスト追加・修正
- `chore:` その他（CI/CD, 依存関係、設定ファイル等）

**subject:** 50文字以内、文末ピリオドなし
