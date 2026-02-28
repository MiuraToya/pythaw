# ADR-0001: pythaw アーキテクチャ設計

- ステータス: 承認
- 日付: 2026-02-28

## コンテキスト

pythaw は AWS Lambda ハンドラー内の重い初期化処理を検出する静的解析 CLI ツールである。
Phase 1 では boto3 の3ルール、Phase 2 では追加ルール・出力形式・フィルタ機能の拡張が予定されている。
保守性と拡張性を両立するアーキテクチャを選定する必要がある。

Ruff（Rust 製リンター）と Mypy（Python 型チェッカー）のアーキテクチャを調査し、pythaw の規模感に適した設計を導出した。

## 決定事項

### ディレクトリ構成

```
pythaw/
├── __init__.py          # バージョン情報
├── cli.py               # CLI エントリポイント
├── config.py            # pyproject.toml 設定読み込み
├── finder.py            # 対象ファイル探索
├── checker.py           # AST 走査 + ルールディスパッチ
├── violation.py         # Violation データクラス
├── rules/
│   ├── __init__.py      # ルールレジストリ
│   ├── _base.py         # Rule ABC
│   ├── pw001.py         # boto3.client()
│   ├── pw002.py         # boto3.resource()
│   └── pw003.py         # boto3.Session()
└── formatters/
    ├── __init__.py      # Formatter レジストリ
    ├── _base.py         # Formatter ABC
    └── concise.py       # concise 形式
```

### 処理フロー

```
cli.py (引数解析)
  → config.py (設定読み込み)
    → finder.py (ファイル収集)
      → checker.py (AST 解析 + ルールディスパッチ)
        → formatters/ (結果出力)
          → 終了コード (0: OK / 1: 違反 / 2: エラー)
```

一方向のパイプライン構造。各モジュールは前段の出力を受け取り、次段に渡すだけ。

## 選定理由

### 1. CLI: argparse（標準ライブラリ）

- **採用理由**: サブコマンド3つ + オプション数個の規模では click / typer 等のフレームワークは過剰。依存ゼロを維持できる
- **比較**: ruff, mypy 等の静的解析ツールも標準ライブラリで CLI を構築している

### 2. ルール: 個別ファイル + ABC + レジストリ

- **採用理由**: Ruff の「1ルール1ファイル + コード登録を一元管理」パターンに倣う。ルール追加時に既存コードへの影響がなく、ファイルを追加してレジストリに登録するだけで完結する
- **不採用案**: Mypy のように checker.py 内にチェックロジックを直書きする方式は、ルール数が増えるとファイルが肥大化する
- **ABC を使う理由**: `code`, `message`, `what`, `why`, `example` を各ルールに強制し、`pythaw rules` / `pythaw rule <CODE>` の出力を統一的に生成できる

### 3. AST 走査: ast.NodeVisitor ベース + ディスパッチ層の分離

- **採用理由**: Python 標準の `ast` モジュールで十分。外部パーサーは不要
- **ディスパッチ層の分離**: Ruff の `analyze/` 層に倣い、checker.py が AST を走査してルールを呼び出す構造とする。個別ルールは純粋な判定ロジックのみを持ち、AST 走査の詳細を知らなくてよい

### 4. 出力: Formatter ABC + 辞書レジストリ

- **採用理由**: Mypy の `ErrorFormatter` ABC + `OUTPUT_CHOICES` 辞書パターンに倣う。Phase 2 で JSON / GitHub Actions / SARIF 形式が追加される想定のため、Formatter を追加してレジストリに登録するだけで拡張できる構造にする

### 5. Violation を独立モジュールにする

- **採用理由**: checker と formatters の両方が Violation に依存する。独立モジュールにすることで循環参照を防ぎ、依存関係を一方向に保つ

## Phase 2 での拡張ポイント

| 拡張内容 | 変更箇所 |
|---|---|
| ルール追加 (PW004〜PW009) | `rules/` にファイル追加 + レジストリ登録 |
| 出力形式追加 (JSON, SARIF) | `formatters/` にファイル追加 + レジストリ登録 |
| `--select` / `--ignore` | `cli.py` にオプション追加 + レジストリでフィルタ |
| インライン抑制 (`# nopw:`) | `checker.py` にコメント解析を追加 |
| カスタムルール | `config.py` で読み込み + 動的にルール生成 |
