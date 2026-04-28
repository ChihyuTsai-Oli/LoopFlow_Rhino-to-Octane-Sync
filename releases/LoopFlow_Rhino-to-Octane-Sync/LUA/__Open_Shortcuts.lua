-- ============================================================
-- Script Name  : __Open_Shortcuts
-- Version           : v1.0
-- Date              : 2026-04-28
-- Author            : Cursor + Claude Sonnet 4.6
-- Description : Opens R2O_Shortcuts.txt in the system default editor.
--               After editing, run __Setup_Shortcuts.lua to apply the
--               shortcuts to the @shortcut line of each script.
-- ============================================================
--
-- @description Open R2O_Shortcuts.txt hotkey config file

local APPDATA        = os.getenv("APPDATA")
local INSTALL_DIR    = APPDATA .. "\\McNeel\\Rhinoceros\\8.0\\scripts\\LoopFlow_R2O"
local DATA_DIR       = INSTALL_DIR .. "\\Data"
local SHORTCUTS_FILE = DATA_DIR .. "\\R2O_Shortcuts.txt"

os.execute('start "" "' .. SHORTCUTS_FILE .. '"')
print("[Open_Shortcuts] Opened: " .. SHORTCUTS_FILE)
