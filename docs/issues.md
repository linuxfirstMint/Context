✅ GitHub Issues（作成用リスト）

> 使い方: 各項目を新規 Issue としてコピー。
> ラベル例: phase:F1 / phase:F2 / phase:F3 / phase:F4、area:orchestrator / area:mcp / area:rag / area:ci、type:feature / type:test / type:docs

) F1-01: MCP Server 基本 API ＋安全境界

Labels: phase:F1, area:mcp, type:feature
概要: FastAPI で /list_files /read_file /write_file を実装。ルート固定・拡張子制限・サイズ上限・UTF-8 限定・trace_id 対応。
受け入れ基準:

ルート外パス（../）で 400

許可外拡張子で 400

KB 超過で 413

/list_files フィルタ（extensions, max_items）動作
完了の定義:

OpenAPI（自動生成）が表示できる（/docs）

単体テストが緑

---

) F1-02: Orchestrator 最小ループ（Hermes 擬似 Function Call）

Labels: phase:F1, area:orchestrator, type:feature
概要: Hermes 3 (Ollama) から {"thought","tool_calls","final_answer"} JSON を受け、tool_calls を MCP に順次適用。
受け入れ基準:

JSON フェンス抽出で整形、1 回まで再試行

trace_id 生成し MCP へ x-trace-id 送付

失敗時の終了コード: 1=exec_fail, 2=policy, 3=json
完了の定義: 手動で --task 実行 →./app/main.py 生成

---

) F1-03: CLI & 終了コード規約

Labels: phase:F1, area:orchestrator, type:feature
概要: evercontext run --task "..." を提供。終了コード 0/1/2/3 を実装。
受け入れ基準: CLI 引数・help 表示・終了コードの整合
完了: README に使用例追記

---

) F1-04: E2E テスト（Hello World 生成）

Labels: phase:F1, area:test, type:test
概要: pytest で ./app/main.py 生成、冪等、ポリシー拒否、404 を検証。
受け入れ基準: すべてのテストが緑
完了: task e2e:f1 が成功

---

) F2-01: Gemini 計画 JSON（v1）スキーマ固定

Labels: phase:F2, area:orchestrator, type:spec
概要: 計画 JSON のスキーマ（tasks/depends_on/on_error）を確定し、検証を導入。
受け入れ基準: スキーマに合わない計画は拒否（わかりやすいエラー）
完了: サンプル計画（TODO 雛形）がスキーマ検証を通過

---

) F2-02: 計画 → 実行の順次実行＆中断

Labels: phase:F2, area:orchestrator, type:feature
概要: depends_on の順序を守り、途中失敗で中断/再計画をサポート。
受け入れ基準: 同一入力 → 同一計画、途中失敗時は中断し状態破綻なし
完了: E2E（TODO 雛形）緑

---

) F3-01: RAG Server /ingest /prune /search

Labels: phase:F3, area:rag, type:feature
概要: 差分更新に対応した RAG API を実装。/search は path/span/score を返す。
受け入れ基準: 追加/更新/削除/改名の反映が 1 コミットで整合
完了: /search が根拠付きで返す

---

) F3-02: gitingest フック（差分 → 非同期キュー）

Labels: phase:F3, area:rag, type:feature
概要: pre-commit で変更ファイル一覧を取得 → 非同期デーモンで upsert/prune 実行。
受け入れ基準: コミット時に RAG が最新化、コミット遅延は最小
完了: ログで反映を確認

---

) F4-01: ツール拡張（lint/test/format/http）

Labels: phase:F4, area:orchestrator, type:feature
概要: run.lint run.test run.format run.http API/プロトコル追加。
受け入れ基準: 代表タスクで呼び出し成功、結果が構造化ログに残る

---

) F4-02: 自己修復ループ（失敗 → 原因推定 → 修正 → 再試行）

Labels: phase:F4, area:orchestrator, type:feature
概要: pytest 失敗のログを解析し、最小修正提案を打って再試行。
受け入れ基準: 代表ケースで 1〜2 手の修復が成功
完了: E2E（新 API 追加 → 全テスト緑）達成

おまけ：gh CLI 一括作成サンプル

# 例: F1-01

gh issue create \
 --title "F1-01: MCP Server 基本 API ＋安全境界" \
 --label "phase:F1,area:mcp,type:feature" \
 --body-file - <<'EOF'
FastAPI で `/list_files` `/read_file` `/write_file` を実装。ルート固定・拡張子制限・サイズ上限・UTF-8 限定・trace_id 対応。

**受け入れ基準**

- ルート外パス（../）で 400
- 許可外拡張子で 400
- 512KB 超過で 413
- `/list_files` フィルタ（extensions, max_items）動作

**完了の定義**

- OpenAPI（/docs）が表示
- 単体テスト緑
  EOF
