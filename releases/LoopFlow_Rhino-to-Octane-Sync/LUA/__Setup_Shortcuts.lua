-- ============================================================
-- Script Name  : __Setup_Shortcuts
-- Version           : v1.0
-- Date              : 2026-04-28
-- Author            : Cursor + Claude Sonnet 4.6
-- Description : Reads R2O_Shortcuts.txt and writes the hotkey settings to the
--               `-- @shortcut` line of each Lua script in the same directory,
--               then prints a summary of changes.
--               This script itself has no hotkey assigned.
-- ============================================================
--
-- [Usage]
-- 1) Edit Data\R2O_Shortcuts.txt and fill in hotkeys per script (leave blank for none).
-- 2) Run this script in Octane; it will auto-update the @shortcut line of each .lua file.
-- 3) Re-scan the Octane script directory afterwards to activate the hotkeys.
--
-- [R2O_Shortcuts.txt format]
-- One entry per line: ScriptName (without .lua): Hotkey (leave blank for no hotkey)
-- Example:
--   LiveLink_R2O_Camera: Ctrl + Q
--   LiveLink_R2O_Point:

-- ── Path constants (derived automatically from install location, no hard-coding) ──────────
local APPDATA        = os.getenv("APPDATA")
local INSTALL_DIR    = APPDATA .. "\\McNeel\\Rhinoceros\\8.0\\scripts\\LoopFlow_R2O"
local DATA_DIR       = INSTALL_DIR .. "\\Data"
local LUA_DIR        = INSTALL_DIR .. "\\Lua"
local SHORTCUTS_FILE = DATA_DIR .. "\\R2O_Shortcuts.txt"

-- Read R2O_Shortcuts.txt and return a { scriptName = hotkeyString } table
local function loadShortcuts()
    local shortcuts = {}
    local f = io.open(SHORTCUTS_FILE, "r")
    if not f then
        print("[Error] Shortcut config file not found: " .. SHORTCUTS_FILE)
        return nil
    end
    for line in f:lines() do
        local name, hotkey = line:match("^([^:]+):%s*(.*)")
        if name then
            name    = name:match("^%s*(.-)%s*$")
            hotkey  = hotkey and hotkey:match("^%s*(.-)%s*$") or ""
            if name ~= "" then
                shortcuts[name] = hotkey
            end
        end
    end
    f:close()
    return shortcuts
end

-- Read a single file and return its contents as a string; return nil on failure
local function readFile(path)
    local f = io.open(path, "r")
    if not f then return nil end
    local content = f:read("*all")
    f:close()
    return content
end

-- Write content to a single file; return true on success
local function writeFile(path, content)
    local f = io.open(path, "w")
    if not f then return false end
    f:write(content)
    f:close()
    return true
end

-- Replace the @shortcut line in content with the new hotkey value.
-- If no @shortcut line is found, content is returned unchanged.
local function updateShortcutLine(content, hotkey)
    local newLine = hotkey ~= "" and ("-- @shortcut " .. hotkey) or "-- @shortcut"
    local updated, count = content:gsub("(%-%-[ \t]*@shortcut[^\n]*)", newLine)
    return updated, count
end

-- List all .lua files in LUA_DIR (requires io.popen available in Lua 5.1)
local function listLuaFiles()
    local files = {}
    -- Octane Standalone uses LuaJIT; use io.popen with the dir command to list files
    local cmd = 'dir /b "' .. LUA_DIR .. '\\*.lua" 2>nul'
    local pipe = io.popen(cmd)
    if pipe then
        for fname in pipe:lines() do
            fname = fname:match("^%s*(.-)%s*$")
            if fname ~= "" then
                table.insert(files, fname)
            end
        end
        pipe:close()
    end
    return files
end

local function main()
    local shortcuts = loadShortcuts()
    if not shortcuts then return end

    local luaFiles = listLuaFiles()
    if #luaFiles == 0 then
        print("[Warning] No .lua files found in " .. LUA_DIR .. ".")
        return
    end

    local selfName = "__Setup_Shortcuts"
    local updated_count = 0
    local skipped_count = 0

    print("========================================")
    print("[__Setup_Shortcuts] Applying hotkey settings...")

    for _, fname in ipairs(luaFiles) do
        -- Exclude self
        local baseName = fname:match("^(.-)%.lua$") or fname
        if baseName == selfName then
            goto continue
        end

        -- Only update scripts defined in the config file
        if shortcuts[baseName] == nil then
            print("[Skip] " .. fname .. " (not listed in R2O_Shortcuts.txt)")
            skipped_count = skipped_count + 1
            goto continue
        end

        local filePath = LUA_DIR .. "\\" .. fname
        local content = readFile(filePath)
        if not content then
            print("[Error] Cannot read: " .. filePath)
            goto continue
        end

        local newContent, replaceCount = updateShortcutLine(content, shortcuts[baseName])
        if replaceCount == 0 then
            print("[Skip] " .. fname .. " (@shortcut line not found, skipped)")
            skipped_count = skipped_count + 1
        elseif newContent == content then
            print("[NoChange] " .. fname .. " (hotkey unchanged)")
        else
            if writeFile(filePath, newContent) then
                local display = shortcuts[baseName] ~= "" and shortcuts[baseName] or "(no hotkey)"
                print("[Updated] " .. fname .. " -> " .. display)
                updated_count = updated_count + 1
            else
                print("[Error] Cannot write: " .. filePath)
            end
        end

        ::continue::
    end

    print("----------------------------------------")
    print(("[Done] Updated %d script(s), skipped %d."):format(updated_count, skipped_count))
    print("Re-scan the Octane script directory to activate the hotkeys.")
    print("========================================")
end

main()
