フェーズ設計（Phased Plan）

フェーズ 1：ローカル実行基盤（MVP）

目標: 単一明確指示 → ローカルでファイル生成/編集完遂

タスク

MCP: /list_files, /read_file, /write_file（安全境界込み）

Orchestrator: Hermes 擬似 FC ループ、trace_id、JSON 耐性、終了コード

CLI: evercontext run --task ...

E2E: Hello World 生成、冪等、ポリシー拒否、404

完了条件（DoD）

--task "app に FastAPI Hello World" → ./app/main.py 生成

回目も成功（overwrite）、ログと終了コードが正しい

---

フェーズ 2：ハイブリッド連携（Gemini 計画 →Hermes 実行）

目標: 曖昧指示 → 計画 JSON→ 順次実行

タスク

gemini-cli 呼び出し（タイムアウト/再試行）

計画 JSON スキーマ v1 固定（tasks[], depends_on, on_error）

計画 → 実行の検証/中断/ロールバック方針

E2E: 「TODO アプリ雛形」の計画 → 実行 → 生成

完了条件

同一入力で同一計画

途中失敗で中断し、状態破綻なし

---

フェーズ 3：RAG 導入（差分同期 × 検索）

目標: 既存コード参照前提の追加・修正

タスク

RAG Server: /ingest, /prune, /search

gitingest フック: pre-commit→ 非同期キュー → インデクサ

チャンク/埋め込み設計、改名/削除の正確反映

E2E: 「User 参照 →Product 追加」タスクで参照根拠が RAG から供給

完了条件

追加/更新/削除/改名の整合が 1 コミットで反映

/search が path/span/score を返し、生成根拠ログに残る

---

フェーズ 4：自律性向上（ツール拡張・自己修復）

目標: 複合タスク中のエラーを自己修復しながら完遂

タスク

ツール拡張: run.lint, run.test, run.format, run.http

失敗 → 復旧ループ（原因推定 → 修正提案 → 再試行）

サーキットブレーカ/ロールバック

E2E: 「新 API 追加して全テストパス」まで一連成功

完了条件

代表的な lint/test 失敗で、1〜2 手の自動修復が成功

---

ロードマップ目安（例）

W1–W2: F1 実装 & E2E 通過

W3–W4: F2 計画 JSON/実行、中断/再試行

W5–W6: F3 RAG 差分同期、検索根拠ログ

W7–W8: F4 自己修復ループ、ツール拡張

---

必要なら、この設計を GitHub Issues（チェックリスト化） と OpenAPI スキーマ に落としてお渡しします。
次の一手は、F1 の E2E を回しつつ F2 の計画 JSON スキーマ v1 を固定してしまうのがオススメです。
