-- ============================================================
-- 腳本名稱 : __Open_Shortcuts
-- 版本     : v1.0
-- 日期     : 2026-04-28
-- 作者     : Cursor + Claude Sonnet 4.6
-- 功能說明 : 以系統預設編輯器開啟 R2O_Shortcuts.txt 熱鍵設定檔。
--            修改完成後，執行 Setup_Shortcuts.lua 將設定寫入各腳本的 @shortcut 行。
-- ============================================================
--
-- @description 開啟 R2O_Shortcuts.txt 熱鍵設定檔

local APPDATA        = os.getenv("APPDATA")
local INSTALL_DIR    = APPDATA .. "\\McNeel\\Rhinoceros\\8.0\\scripts\\LoopFlow_R2O"
local DATA_DIR       = INSTALL_DIR .. "\\Data"
local SHORTCUTS_FILE = DATA_DIR .. "\\R2O_Shortcuts.txt"

os.execute('start "" "' .. SHORTCUTS_FILE .. '"')
print("[Open_Shortcuts] 已開啟: " .. SHORTCUTS_FILE)
