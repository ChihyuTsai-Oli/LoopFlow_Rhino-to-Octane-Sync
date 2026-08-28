# LoopFlow R2O Repository Instructions

範圍：本 repo。另須遵守上一層 `E:\_GitHub\AGENTS.md`。

## 開始作業前必讀

AI 必須依序完整讀取：

1. `wip/docs/實作總覽.md`
2. `wip/docs/資料契約.md`
3. `wip/docs/工作流程.md`
4. `wip/docs/開發任務與路徑.md`
5. `wip/docs/系統設定.md`
6. `wip/docs/重構進度.md`

契約細節未盤完或需追溯決策時另讀：`wip/docs/前期規劃/資料生態決策表_三家建議.md`、`wip/docs/rhino指令.md`。`前期規劃/` 其餘檔是原則／過程；與六份正式文件衝突時以六份為準。

公開的 `README*.md` 與 `docs/USER_GUIDE*.md` 是使用者文件，不是重構權威。重構內容在 `wip/`。**跨產品開發順序：先 R2B，再本產品。** 功能切片：Rhino＋Octane Lua 同批。Dropbox 路徑依上一層 `工作檔路徑.md`，不得寫死單機絕對路徑。

## 分支與版本

- `main` 在 2.0 正式發布前維持穩定 1.x。
- `v2-development` 是 2.0 整合分支，不直接承接未分批的大型修改。
- 每項工作從 `v2-development` 建立 `codex/v2-<scope>` 短期分支。
- `main` 原則上凍結；僅在使用者明確要求維護 1.x 時，才建立獨立 hotfix，發布後再同步必要修正至 `v2-development`。
- `v1.0.0` tag 與 Release 永不移動或覆寫。

## 重構模式

- 2.0 採「新版乾淨重建、正式發布時一次切換」，不要求開發中的 v1／v2 指令互相相容。
- `main` 與 v1 payload 作為唯讀參考；2.0 在隔離 `wip/src/`、Rhino／Octane 安裝與測試輸出建立。
- **功能切片**：Rhino producer 與 Octane consumer 同一功能同批交付（Models 消費＝手動置換驗收）。
- 新核心不長期保留 v1 alias、雙寫或 compatibility wrapper；升級集中於獨立 migration 工具。
- 建造過程仍分批提交並做自動／contract 測試；Rhino→Octane 端到端實機測試在主鏈串接完成後集中進行。

## 文件與語言

- 維護、架構、設定、重構與進度文件一律使用繁體中文。
- 對外英文 README／使用指南是發布翻譯；功能事實改變時必須與繁中版本同步。
- 完整責任、Python↔Lua schema、流程、副作用與安全條件寫入 `wip/docs/` 六份正式文件。
- 新增或修改的 Python／Lua docstring、區塊註解與行內註解使用繁體中文；API、識別字、Rhino／Octane 名稱與第三方授權文字維持原文。

## AI 作業流程

**開發節奏：能做就做、需確認再停**（與 R2B 相同）。在已決契約與 `開發任務與路徑.md` 範圍內直接推進；僅在改已決 ED／ECO、凍結使用者可見名稱／檔名、破壞性操作、本機正式 runtime 安裝、或明顯契約衝突時停下來問使用者。細節見該檔「執行規則」。

1. 確認 repo、branch、origin、upstream 與乾淨工作樹；只用 fast-forward pull。
2. 讀取上述六份文件，從 `重構進度.md` 確認目前階段與限制。
3. 建立短期工作分支；功能碼須兩端同批。
4. 每段完成後做自動／contract 測試；主鏈串接後使用隔離 Rhino、Octane、測試 `.3dm`／scene 做端到端驗證。
5. 端到端涵蓋成功、取消、失敗、中斷、來源文件零變更與 last good output。
6. 同步更新六份正式文件中受影響者，再提交、推送短期分支。

使用者不負責操作 Git 或自行推導技術步驟；AI 應直接完成安全、可逆的操作，並以簡短繁體中文回報結果。
