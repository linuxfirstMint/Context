詳細設計（Detailed Design）

. ゴールと非ゴール

ゴール: 「計画（クラウド AI）→ 安全な実行（ローカル LLM）→ 差分同期 RAG」を一貫化し、常時最新コンテキストで開発タスクを完遂。

非ゴール: 大規模プロジェクトの完全自動開発、CI/CD の置換、プロダクション運用監視。

---

. コンポーネント構成

Orchestrator

役割: ユーザー入力を計画/実行に接続、ツール呼び出し、ログ/トレース集約

I/F: CLI evercontext run --task "..."、Gemini CLI、Ollama Chat、MCP/RAG REST

MCP Server (FastAPI)

役割: ファイル操作の安全ゲートウェイ

ガード: ルート固定、拡張子許可、サイズ上限、UTF-8 制約、監査ログ、trace_id

RAG Server (FastAPI, フェーズ 3)

役割: 差分インデックス更新、検索提供（path/span/score）

Gitingest hook（フェーズ 3）

役割: pre-commit で変更ファイル → 非同期キュー →RAG へ upsert/prune

シーケンス（F1〜F3）

sequenceDiagram
participant User
participant Orchestrator
participant Hermes (Ollama)
participant MCP (FastAPI)
participant RAG (F3+)

User->>Orchestrator: --task "app に Hello World を作成"
Orchestrator->>Hermes (Ollama): system+tools+user(タスク)
Hermes (Ollama)-->>Orchestrator: JSON {thought, tool_calls}
loop tool_calls
Orchestrator->>MCP (FastAPI): POST /write_file (trace_id)
MCP (FastAPI)-->>Orchestrator: {status:"ok", path:"..."}
Orchestrator->>Hermes (Ollama): tool 結果をフィードバック
Hermes (Ollama)-->>Orchestrator: 追加の tool_calls or final_answer
end
Orchestrator-->>User: Final Answer (生成結果/差分/ログ)
Note over Orchestrator,RAG: F3 以降は計画時に /search を呼び補助

---

. API 定義

.1 MCP API（確定：F1 から実装）

POST /list_files

Request: { path: string, extensions?: string[], max_items?: int }

Response: { files: [{name, is_dir, size?}] }

Errors: 404 dir not found, 400 path escapes root

POST /read_file

Request: { path: string }

Response: { content: string }

Errors: 404 not found, 415 not utf-8, 413 too large

POST /write_file

Request: { path: string, content: string, mode: "create"|"overwrite"|"append" }

Response: { status: "ok", path: string }

Errors: 409 exists (create), 400 ext not allowed, 413 too large

> すべてのリクエストに x-trace-id ヘッダ（UUID）を受け取り、監査ログに残す。

.2 Orchestrator ←→ LLM プロトコル（Hermes JSON）

要求: 単一 JSON で出力。キーは ["thought","tool_calls","final_answer"] のみ。

tool_calls: [{ "name": string, "parameters": object }]

例

{
"thought": "app ディレクトリに FastAPI アプリを作る",
"tool_calls": [
{"name":"write_file","parameters":{"path":"./app/main.py","content":"...","mode":"create"}}
],
"final_answer": "main.py を作成しました。"
}

Orchestrator は tool_calls を順次実行し、ツール結果を tool ロールで LLM に返却。

.3 RAG API（F3）

POST /ingest: { paths: string[] } | { diff: {added:[], modified:[], deleted:[], renamed:[{from,to}]}}

POST /prune: { paths: string[] }

POST /search: { query: string, top_k?: number, filters?: { path_prefix?: string } }

Response: { chunks: [{ path, span:"Lx-Ly", text, score }] }

---

. セキュリティ & ポリシー（MCP）

ルート固定: APP_ROOT = cwd（コンテナならプロジェクトルート）

パス正規化: resolve() 後に APP_ROOT prefix を必須

許可拡張子: [".py", ".md", ".txt", ".json", ".yaml", ".yml"]（拡張可能）

サイズ上限: 読み/書きともに 512KB（環境変数で調整）

文字コード: UTF-8 限定

監査: trace_id, method, path, size, status を構造化ログに記録

---

. ログ/可観測性

trace_id（UUID）で 1 タスク全体を紐づけ

ログ粒度：task → plan(JSON) → step(tool_call) → tool_result → diff → final

推奨: 構造化ログ（JSON Lines）、後でダッシュボード化しやすい

---

. 設定/環境変数

EC_APP_ROOT（MCP ルート。未指定は cwd）

EC_ALLOW_EXT（CSV/セミコロン等で拡張子リスト）

EC_MAX_BYTES（既定 512KB）

EC_OLLAMA_ENDPOINT、EC_MODEL_NAME

EC_MCP_URL、EC_RAG_URL（F3）

---

. CLI 仕様（Orchestrator）

evercontext run --task "<自然言語指示>" [--dry-run] [--root ./app]

終了コード

: 成功

: 実行失敗

: ポリシー違反（MCP 4xx）

: LLM JSON 不正（連続失敗）

---

. RAG 設計（F3）

チャンク戦略: 言語別パーサを併用し、**意味境界（関数/クラス/ルーター単位）**優先。補助として固定長トークンチャンク。

キー: path#L{start}-L{end}

埋め込み器: まずは汎用（e5-large 系/mini）→ 必要でコード特化へ切替

改名対応: git diff から renamed: [{from, to}] を受け取り、同一内容の移動は upsert/prune の最小化

---

. 失敗回復（F4）

再試行方針: ネットワーク/LLM フォーマット失敗は 1 回リトライ

自己修復例: pytest 失敗 → ログ解析 → 不足 import 追記 → 再テスト

サーキットブレーカ: 連続失敗回数の上限、部分成功でも中断可

---

. テスト戦略

ユニット: MCP の path/size/UTF-8 検証、Orchestrator プロトコルヘルパ

E2E（F1）: ./app/main.py 生成、冪等、ポリシー拒否、404

E2E（F2）: 同一入力 → 同一計画、依存順序、途中失敗中断

E2E（F3）: 追加/更新/削除/改名のインデックス整合、/search の根拠付与

E2E（F4）: lint/test での自動復旧 1〜2 手の代表例

---

. KPI

F1: 1 タスク成功率、p95 レイテンシ、ポリシー拒否件数

F2: 同一入力 → 同一計画の再現率、部分失敗率

F3: 検索根拠一致率@k、改名反映の正確率

F4: 自動復旧成功率、平均復旧ステップ数
