# LoopFlow R2O — 重構計畫

本文件定義 R2O 2.0 的完整重構邊界、順序與完成條件。它已整合原先外部分析與舊 memo 的有效內容；後續決策直接更新本文件與 `architecture/PROGRESS.md`。

## 產品邊界

### Rhino Producer

Models、Scatter、Point、Camera、Open／Config。負責收集 Rhino 資料、轉換與安全發布。

### Octane LiveLink Consumer

讀取、驗證與套用同步資料，不自行猜 producer 規則。Python↔Lua 以 versioned schema／fixtures 對齊。

### Octane Authoring Tools

Auto Align、Standard Surface conversion、PBR／UV 等是獨立工具。可留同 repo，但不把 authoring 邏輯放入 LiveLink 核心。

## 重構模式裁決

本輪採「2.0 乾淨重建、正式發布時一次切換」：

- `main`、`v1.0.0` 與既有 payload 凍結為舊版參考與回復點。
- 2.0 在隔離 `src/`、Rhino／Octane 安裝、shortcut、scene 與測試輸出建立，不要求開發中的半成品相容 v1。
- 不把 v1 指令逐支包進新架構，也不在核心長期保留 alias、雙寫或 compatibility wrapper。
- 開發仍按 schema、producer、consumer 與功能群分批提交；每段做自動／fixture／contract 測試。
- Models／Scatter／Point／Camera 主鏈接通後，再集中做 Rhino→Octane 端到端實機測試。
- v1 設定、shortcut 或 scene 若需升級，由獨立 migration 工具一次轉換。

## 共同原則

- Rhino Python-first、Octane 維持 Lua，不主動變成 Python＋C#＋Lua 三語言。
- feature-first，不強迫每支 Lua 多層拆檔。
- 命名、Python↔Lua schema、Octane ID 與 shortcut 契約先定義，完成前不建立正式 feature。
- Models／Scatter／Installer P0 安全要求直接納入 2.0 新實作；只有使用者明確要求維護舊版時才另開 1.x hotfix。
- R2B／R2O 只共用安全契約、pipeline 語彙與測試矩陣，不建立跨 repo runtime package。
- `main` 維持穩定 1.x；2.0 的 scripts、data、RHC、shortcut 與輸出完全隔離。
- 2.0 不新增 Octane authoring 功能或同步種類。

## 目標結構

```text
src/
  rhino/
    r2o_rhino/
      bootstrap.py
      command_catalog.py
      features/       # models、scatter、point、camera、diagnostics
      platform/       # Rhino、USD/USDZ、filesystem
      foundation/     # config、path、log、result、atomic publish、version
    entrypoints/
  octane/
    r2o_octane/
      livelink/
      authoring_tools/
      foundation/
schemas/
tests/
docs/
tools/
```

先驗證 Rhino import 與 Octane `require`／reload；不可靠時維持模組化 source，由 build bundle 成 standalone scripts。

## Track 0：來源資料安全

### Models P0

現況風險：

- 來源物件 `MaterialSource` 會被改成 `MaterialFromLayer`，成功後也可能未還原。
- layer／object 狀態只在正常路徑末尾還原，例外可能污染文件。
- 舊 USDZ 先刪除，新匯出失敗會失去 last good。
- material binding postprocess 吞例外，檔案存在仍可能回報成功。

目標 pipeline：

```text
validate
→ collect explicit objects
→ create temporary document/data
→ apply material rules only to temporary source
→ export pending USDZ
→ promote material bindings
→ validate USDZ
→ atomically replace last good
→ structured result
```

### Scatter P0

- 不再把原始 Block 移到原點再移回。
- 使用暫存 instance／document；過渡期若仍修改來源，每個 Block 立即以 `try/finally` 復原。
- 每個 item 有獨立 result；單項失敗不破壞其他項目或 last good USD。

### Installer P0

- 以 PowerShell `Get-Date` 取代 `wmic`，備份名稱包含時間且不碰撞。
- 重複安裝保存 Data／config／shortcut，失敗可 rollback。

## Point／Camera 契約

### Point

- terminal layer name 不作唯一 ID，也不直接插入未 escape Lua 字串。
- 定義 stable type ID、full layer path、display name。
- 正確處理引號、反斜線、換行、中文、emoji、空名稱與同名末層。
- 新格式帶 `schema_version`；舊格式只由 migration scanner／converter 讀取，不在 2.0 LiveLink 長期相容。

### Camera

- 保留現有 atomic write、throttle／content diff。
- config 啟用時快取，設定改變才 reload。
- event lifecycle 與座標／焦距／單位轉換分離。
- consumer 只有 parse + apply 成功後才更新 state。

## Config 拆分

現行 `LiveLink_R2O__Config.py` 同時負責 config、log、exception、atomic write 與 type normalization。新版建造方式：

1. 以 v1 行為建立 fixtures 與安全測試。
2. 在新 `src/` 直接建立 foundation config／logging／atomic_io 與 feature naming。
3. 2.0 feature 只使用新 API，不逐支替換 v1 import。
4. v1 config 轉換由獨立 migration 工具處理。

舊檔保持唯讀參考；禁止直接剪貼後宣稱完成重構。

## Installer、版本與 RHC

- Models 標頭 v1.1 與 Git tag v1.0.0 不一致；2.0 使用單一 version SSOT。只有使用者要求舊版修補時才另決定 `1.0.x` repair release。
- Rhino 8 path 由 build/version config 集中產生或驗證。
- Octane 最低版本需建立 compatibility matrix，不猜數字。
- RHC 中 R2B 殘留另批清理並實機驗證。
- 2.0 RC 通過才合入 `main` 並建立 `v2.0.0`；`v1.0.0` 不移動。

## C# Gate

- Rhino producer 保持 Python；Octane 保持 Lua。
- Camera watcher 若有可重現 lifecycle 問題，可評估整條 Rhino feature 改為 C#。
- USD/USDZ postprocess、schema、Point serializer 仍適合 Python。
- C# 必須完整負責穩定邊界，不作啟動 Python 的 wrapper，且 build／部署／回復成本更低。

## 與 R2B 的局部共用

共用文件與測試語彙：

- validate → explicit source → temporary data → export pending → validate → replace → result。
- error stage、session ID、log、atomic publisher。
- 來源 Rhino 文件零變更 invariant。
- success／cancel／failure／interruption 矩陣。

不共用 USD／3DM exporter、Models payload、Point／Light schema、Blender／Octane consumer、產品 path 或 runtime package。只有兩次真實同步修改證據後才評估 build-time pin／vendor 小 helper。

## Octane Authoring Tools

保留 Auto Align、Standard Surface → Universal、PBR Universal／UV、shortcut open／setup。按 node／material／shortcut 分群，只共用已證明安全的 Octane filesystem／logging helper。2.0 不新增功能。

## 新版建造順序

1. **工作流與依賴盤點**：Rhino Models／Scatter／Point／Camera → Octane LiveLink，列出所有輸入、輸出、檔名、node、state 與失敗條件。
2. **命名與資料契約**：完成 `_R2O_命名與資料契約.md`，鎖定 command、config、Python↔Lua schema、Point identity、Octane node、shortcut 與 version。
3. **Fixtures 與載入 spike**：建立特殊字元、座標、模型、Scatter、Camera fixtures；驗證 Rhino import 與 Octane `require`／reload／bundle 備案。
4. **最小新架構**：建立 `src/`、bootstrap、catalog、foundation、schemas、validator 與 Python／Lua contract tests。
5. **Rhino producer**：依 Models → Scatter → Point → Camera 建立；P0 直接採 temporary data、pending、validate、atomic replace。
6. **Octane consumer**：依 Models／Point／Camera 契約建立 LiveLink，parse + apply 成功才更新 state。
7. **主鏈端到端測試**：以隔離 Rhino／Octane、測試 `.3dm`／scene 驗證正常、取消、失敗、中斷與 last good。
8. **Authoring tools**：在 LiveLink 穩定後整理 namespace、錯誤與 build，不擴充功能。
9. **Migration／Build／切換**：v1 scanner、備份、一次轉換、RHC、compatibility matrix、shortcut、ZIP、hash、RC，最後一次合入 `main` 發布 `v2.0.0`。

每一步都要提交與自動測試；「一次切換」不等於「全部寫完才第一次測試」。

## Git 與環境隔離

- 2.0 工作由 `codex/v2-<scope>` 合入 `v2-development`。
- `main` 原則上凍結；只有使用者明確要求舊版緊急修補時才從 `main` 開 1.x hotfix。
- Dev Rhino scripts／data／RHC、Octane scripts／shortcut 與輸出使用獨立位置。
- migration 只對 1.x 資料副本執行。

## 每批完成門檻

- 一批只處理一個安全問題或一條 feature。
- Python producer 與 Lua consumer 使用同組 fixtures。
- golden workflow、取消、失敗、中斷與資料復原通過。
- Rhino 原文件不變，last good USD／USDZ 仍在。
- schema／path／version 只有一個權威來源。
- docs、progress、測試、shortcut 與 build 資訊同步。
- diff 排除秘密、快取、產物與無關修改。
- commit、push、回復點與實機限制有紀錄。

## 2.0 完成條件

- Models／Scatter 在所有退出路徑不改來源 Rhino 文件。
- last good USD／USDZ 在新輸出驗證前不刪除。
- Point 對特殊字元、中文與同名 layer 有確定結果。
- Camera 保留有效節流並有正確 event／state lifecycle。
- Python／Lua schema、path、version 有 contract tests。
- LiveLink 與 authoring tools 邊界清楚。
- installer 不依賴 `wmic`，可安全重複執行與 rollback。
- Dev 環境與 1.x 隔離，`v1.0.0` 可完整回復。
