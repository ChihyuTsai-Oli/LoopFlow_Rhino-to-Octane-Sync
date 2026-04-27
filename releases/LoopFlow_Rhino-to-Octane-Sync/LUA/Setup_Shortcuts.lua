-- ============================================================
-- 腳本名稱 : Setup_Shortcuts
-- 版本     : v1.0
-- 日期     : 2026-04-27
-- 作者     : Cursor + Claude Sonnet 4.6
-- 功能說明 : 讀取 R2O_Shortcuts.txt，將熱鍵設定寫入同目錄下各 Lua 腳本的
--            `-- @shortcut` 行，並輸出修改摘要。
--            本腳本自身不設熱鍵。
-- ============================================================
--
-- 【使用說明】
-- 1) 編輯 Data\R2O_Shortcuts.txt，依格式填寫各腳本的熱鍵（留空表示不設熱鍵）。
-- 2) 在 Octane 中執行本腳本，腳本會自動更新各 .lua 的 @shortcut 行。
-- 3) 完成後重新掃描 Octane 腳本目錄，使熱鍵設定生效。
--
-- 【R2O_Shortcuts.txt 格式】
-- 每行格式：腳本名稱（不含 .lua）: 熱鍵（留空表示不設熱鍵）
-- 範例：
--   LiveLink_R2O_Camera: Ctrl + Q
--   LiveLink_R2O_Point:

-- ── 路徑常數（依安裝位置自動推算，不依賴硬編碼） ───────────────────
local APPDATA        = os.getenv("APPDATA")
local INSTALL_DIR    = APPDATA .. "\\McNeel\\Rhinoceros\\8.0\\scripts\\LoopFlow_R2O"
local DATA_DIR       = INSTALL_DIR .. "\\Data"
local LUA_DIR        = INSTALL_DIR .. "\\LUA"
local SHORTCUTS_FILE = DATA_DIR .. "\\R2O_Shortcuts.txt"

-- 讀取 R2O_Shortcuts.txt，回傳 { 腳本名 = 熱鍵字串 } 的 table
local function loadShortcuts()
    local shortcuts = {}
    local f = io.open(SHORTCUTS_FILE, "r")
    if not f then
        print("[Error] 找不到熱鍵設定檔: " .. SHORTCUTS_FILE)
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

-- 讀取單一檔案內容，回傳字串；失敗回傳 nil
local function readFile(path)
    local f = io.open(path, "r")
    if not f then return nil end
    local content = f:read("*all")
    f:close()
    return content
end

-- 寫入單一檔案；成功回傳 true
local function writeFile(path, content)
    local f = io.open(path, "w")
    if not f then return false end
    f:write(content)
    f:close()
    return true
end

-- 將 content 中的 @shortcut 行替換為新的熱鍵值
-- 若原本找不到 @shortcut 行，不修改
local function updateShortcutLine(content, hotkey)
    local newLine = hotkey ~= "" and ("-- @shortcut " .. hotkey) or "-- @shortcut"
    local updated, count = content:gsub("(%-%-[ \t]*@shortcut[^\n]*)", newLine)
    return updated, count
end

-- 列出 LUA_DIR 中所有 .lua 檔（需 Lua 5.1 io 可用時使用 io.popen）
local function listLuaFiles()
    local files = {}
    -- Octane Standalone 使用 LuaJIT；以 io.popen 呼叫 dir 指令列出檔案清單
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
        print("[Warning] 在 " .. LUA_DIR .. " 中找不到任何 .lua 檔案。")
        return
    end

    local selfName = "Setup_Shortcuts"
    local updated_count = 0
    local skipped_count = 0

    print("========================================")
    print("[Setup_Shortcuts] 開始更新熱鍵設定...")

    for _, fname in ipairs(luaFiles) do
        -- 排除自身
        local baseName = fname:match("^(.-)%.lua$") or fname
        if baseName == selfName then
            goto continue
        end

        -- 只更新設定檔中有定義的腳本
        if shortcuts[baseName] == nil then
            print("[Skip] " .. fname .. "（R2O_Shortcuts.txt 中無此項目）")
            skipped_count = skipped_count + 1
            goto continue
        end

        local filePath = LUA_DIR .. "\\" .. fname
        local content = readFile(filePath)
        if not content then
            print("[Error] 無法讀取: " .. filePath)
            goto continue
        end

        local newContent, replaceCount = updateShortcutLine(content, shortcuts[baseName])
        if replaceCount == 0 then
            print("[Skip] " .. fname .. "（找不到 @shortcut 行，略過）")
            skipped_count = skipped_count + 1
        elseif newContent == content then
            print("[NoChange] " .. fname .. "（熱鍵無變更）")
        else
            if writeFile(filePath, newContent) then
                local display = shortcuts[baseName] ~= "" and shortcuts[baseName] or "（無熱鍵）"
                print("[Updated] " .. fname .. " -> " .. display)
                updated_count = updated_count + 1
            else
                print("[Error] 無法寫入: " .. filePath)
            end
        end

        ::continue::
    end

    print("----------------------------------------")
    print(("[Done] 已更新 %d 個腳本，略過 %d 個。"):format(updated_count, skipped_count))
    print("請重新掃描 Octane 腳本目錄，使熱鍵設定生效。")
    print("========================================")
end

main()
