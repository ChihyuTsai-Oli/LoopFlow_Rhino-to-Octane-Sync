-- R2O 2.0：讀同資料夾 R2O_Shortcuts.txt，寫入各 LiveLink 腳本的 -- @shortcut。
-- 路徑：優先 debug.getinfo；失敗則備援「文件\LoopFlow\Rhino to OctaneRender Sync\lua」。
-- 不寫死 AppData。中文路徑：stdio 失敗則 CreateFileW。Docs: wip/docs/系統設定.md

local SHORTCUTS_NAME = "R2O_Shortcuts.txt"
local PRODUCT_LUA_REL = "Documents\\LoopFlow\\Rhino to OctaneRender Sync\\lua"
local MB_OK = 0x00000000
local MB_ICONERROR = 0x00000010
local MB_ICONINFORMATION = 0x00000040
local SKIP = {
    __Setup_Shortcuts = true,
    __Open_Shortcuts = true,
}

local function file_exists(path)
    local f = io.open(path, "rb")
    if not f then
        return false
    end
    f:close()
    return true
end

local function dir_from_source(src)
    if type(src) ~= "string" or src == "" then
        return nil
    end
    if src:sub(1, 1) == "@" then
        src = src:sub(2)
    end
    src = src:gsub("^%s+", ""):gsub("%s+$", ""):gsub("/", "\\")
    if src == "" or src == "[C]" or src == "stdin" then
        return nil
    end
    if not src:lower():match("%.lua$") then
        return nil
    end
    local dir = src:match("^(.*)[\\/][^\\/]+$")
    if dir and dir ~= "" then
        return dir:gsub("[\\/]+$", "")
    end
    return nil
end

local function documents_lua_dir()
    local profile = os.getenv("USERPROFILE")
    if not profile or profile == "" then
        return nil
    end
    return (profile .. "\\" .. PRODUCT_LUA_REL):gsub("[\\/]+$", "")
end

-- 回傳 lua 資料夾；須含 R2O_Shortcuts.txt。
local function resolve_lua_dir()
    for level = 1, 8 do
        local info = debug.getinfo(level, "S")
        if info and info.source then
            local dir = dir_from_source(info.source)
            if dir and file_exists(dir .. "\\" .. SHORTCUTS_NAME) then
                return dir, "script"
            end
        end
    end
    local fallback = documents_lua_dir()
    if fallback and file_exists(fallback .. "\\" .. SHORTCUTS_NAME) then
        return fallback, "documents"
    end
    return nil, nil
end

local function join(dir, name)
    return tostring(dir):gsub("[\\/]+$", "") .. "\\" .. name
end

local function read_stdio(path)
    local f, err = io.open(path, "rb")
    if not f then
        return nil, err
    end
    local data = f:read("*a")
    f:close()
    return data
end

local function write_stdio(path, content)
    local f = io.open(path, "wb")
    if not f then
        return false
    end
    f:write(content)
    f:close()
    return true
end

local _win_ready = false
local function ensure_win()
    local ok, ffi = pcall(require, "ffi")
    if not ok or not ffi or ffi.os ~= "Windows" then
        return nil, "win32 ffi unavailable"
    end
    if not _win_ready then
        local cdef_ok = pcall(function()
            ffi.cdef[[
                typedef void* HANDLE;
                typedef void* HWND;
                typedef unsigned long DWORD;
                typedef unsigned int UINT;
                typedef int BOOL;
                int MultiByteToWideChar(unsigned int, DWORD, const char*, int, wchar_t*, int);
                HANDLE CreateFileW(const wchar_t*, DWORD, DWORD, void*, DWORD, DWORD, HANDLE);
                BOOL ReadFile(HANDLE, void*, DWORD, DWORD*, void*);
                BOOL WriteFile(HANDLE, const void*, DWORD, DWORD*, void*);
                BOOL CloseHandle(HANDLE);
                DWORD GetFileSize(HANDLE, DWORD*);
                int MessageBoxW(HWND, const wchar_t*, const wchar_t*, UINT);
            ]]
        end)
        if not cdef_ok then
            return nil, "win32 cdef failed"
        end
        _win_ready = true
    end
    return ffi
end

local function utf8_to_wide(ffi, text)
    local n = ffi.C.MultiByteToWideChar(65001, 0, text, #text, nil, 0)
    if n <= 0 then
        return nil
    end
    local w = ffi.new("wchar_t[?]", n + 1)
    ffi.C.MultiByteToWideChar(65001, 0, text, #text, w, n)
    w[n] = 0
    return w
end

local function message_box(text, caption, flags)
    local ffi = ensure_win()
    if not ffi then
        print(tostring(caption or "R2O") .. ": " .. tostring(text or ""))
        return
    end
    local w_text = utf8_to_wide(ffi, tostring(text or ""))
    local w_caption = utf8_to_wide(ffi, tostring(caption or "R2O Setup Shortcuts"))
    if w_text and w_caption then
        ffi.C.MessageBoxW(nil, w_text, w_caption, flags or MB_OK)
    end
end

local function read_win32(path)
    local ffi, err = ensure_win()
    if not ffi then
        return nil, err
    end
    local wpath = utf8_to_wide(ffi, tostring(path):gsub("/", "\\"))
    if not wpath then
        return nil, "utf16 convert failed"
    end
    local generic_read = ffi.cast("DWORD", 0x80000000)
    local share = ffi.cast("DWORD", 7)
    local open_existing = ffi.cast("DWORD", 3)
    local handle = ffi.C.CreateFileW(wpath, generic_read, share, nil, open_existing, 0x80, nil)
    if handle == nil or handle == ffi.cast("HANDLE", ffi.cast("intptr_t", -1)) then
        return nil, "CreateFileW failed"
    end
    local size = tonumber(ffi.C.GetFileSize(handle, nil))
    if not size or size < 0 or size > 4000000 then
        ffi.C.CloseHandle(handle)
        return nil, "bad file size"
    end
    if size == 0 then
        ffi.C.CloseHandle(handle)
        return ""
    end
    local buf = ffi.new("uint8_t[?]", size)
    local readn = ffi.new("DWORD[1]")
    local ok_read = ffi.C.ReadFile(handle, buf, size, readn, nil)
    ffi.C.CloseHandle(handle)
    if ok_read == 0 then
        return nil, "ReadFile failed"
    end
    return ffi.string(buf, tonumber(readn[0]))
end

local function write_win32(path, content)
    local ffi, err = ensure_win()
    if not ffi then
        return false, err
    end
    local wpath = utf8_to_wide(ffi, tostring(path):gsub("/", "\\"))
    if not wpath then
        return false, "utf16 convert failed"
    end
    local generic_write = ffi.cast("DWORD", 0x40000000)
    local create_always = ffi.cast("DWORD", 2)
    local handle = ffi.C.CreateFileW(wpath, generic_write, 0, nil, create_always, 0x80, nil)
    if handle == nil or handle == ffi.cast("HANDLE", ffi.cast("intptr_t", -1)) then
        return false, "CreateFileW write failed"
    end
    local data = tostring(content)
    local written = ffi.new("DWORD[1]")
    local ok_write = ffi.C.WriteFile(handle, data, #data, written, nil)
    ffi.C.CloseHandle(handle)
    return ok_write ~= 0
end

local function read_file(path)
    local data, err = read_stdio(path)
    if data then
        return data
    end
    local win, win_err = read_win32(path)
    if win then
        return win
    end
    return nil, err or win_err
end

local function write_file(path, content)
    if write_stdio(path, content) then
        return true
    end
    return write_win32(path, content)
end

local function load_shortcuts(path)
    local raw, err = read_file(path)
    if not raw then
        print("[Error] Shortcut config file not found: " .. path .. (err and (" (" .. tostring(err) .. ")") or ""))
        return nil
    end
    local shortcuts = {}
    local order = {}
    for line in (raw .. "\n"):gmatch("(.-)\r?\n") do
        local trimmed = line:match("^%s*(.-)%s*$") or ""
        if trimmed ~= "" and not trimmed:match("^#") then
            local name, hotkey = trimmed:match("^([^:]+):%s*(.*)")
            if name then
                name = name:match("^%s*(.-)%s*$")
                hotkey = hotkey and hotkey:match("^%s*(.-)%s*$") or ""
                if name ~= "" then
                    if shortcuts[name] == nil then
                        order[#order + 1] = name
                    end
                    shortcuts[name] = hotkey
                end
            end
        end
    end
    return shortcuts, order
end

local function update_shortcut_line(content, hotkey)
    local new_line = hotkey ~= "" and ("-- @shortcut " .. hotkey) or "-- @shortcut"
    local updated, count = content:gsub("(%-%-[ \t]*@shortcut[^\n]*)", new_line, 1)
    return updated, count
end

local function main()
    local lua_dir, source_kind = resolve_lua_dir()
    if not lua_dir then
        message_box(
            "找不到 R2O_Shortcuts.txt。\n\n請在 Rhino 執行 ROOpen，確認「文件\\LoopFlow\\Rhino to OctaneRender Sync\\lua」已有腳本與熱鍵表，再重掃 Octane 腳本資料夾。",
            "R2O Setup Shortcuts",
            MB_OK + MB_ICONERROR
        )
        return
    end

    local shortcuts_path = join(lua_dir, SHORTCUTS_NAME)
    local shortcuts, order = load_shortcuts(shortcuts_path)
    if not shortcuts then
        message_box(
            "無法讀取熱鍵表：\n" .. shortcuts_path,
            "R2O Setup Shortcuts",
            MB_OK + MB_ICONERROR
        )
        return
    end

    local updated_count = 0
    local skipped_count = 0
    local unchanged_count = 0

    print("========================================")
    print("[__Setup_Shortcuts] Applying hotkeys in: " .. lua_dir .. " (" .. tostring(source_kind) .. ")")

    for _, baseName in ipairs(order) do
        if SKIP[baseName] then
            skipped_count = skipped_count + 1
        else
            local fname = baseName .. ".lua"
            local filePath = join(lua_dir, fname)
            local content, read_err = read_file(filePath)
            if not content then
                print("[Skip] " .. fname .. " (not found" .. (read_err and (": " .. tostring(read_err)) or "") .. ")")
                skipped_count = skipped_count + 1
            else
                local newContent, replaceCount = update_shortcut_line(content, shortcuts[baseName])
                if replaceCount == 0 then
                    print("[Skip] " .. fname .. " (@shortcut line not found)")
                    skipped_count = skipped_count + 1
                elseif newContent == content then
                    print("[NoChange] " .. fname .. " (hotkey unchanged)")
                    unchanged_count = unchanged_count + 1
                else
                    if write_file(filePath, newContent) then
                        local display = shortcuts[baseName] ~= "" and shortcuts[baseName] or "(no hotkey)"
                        print("[Updated] " .. fname .. " -> " .. display)
                        updated_count = updated_count + 1
                    else
                        print("[Error] Cannot write: " .. filePath)
                        skipped_count = skipped_count + 1
                    end
                end
            end
        end
    end

    print("----------------------------------------")
    print(("[Done] Updated %d script(s), skipped %d, unchanged %d."):format(updated_count, skipped_count, unchanged_count))
    print("Re-scan the Octane script folder to activate the hotkeys.")
    print("After a new copy of the lua folder, run this script again.")
    print("========================================")

    message_box(
        ("完成。\n\n已更新：%d\n略過：%d\n未變：%d\n\n資料夾：\n%s\n路徑來源：%s\n\n請重掃 Octane 腳本資料夾以啟用熱鍵。"):format(
            updated_count, skipped_count, unchanged_count, lua_dir, tostring(source_kind)
        ),
        "R2O Setup Shortcuts",
        MB_OK + MB_ICONINFORMATION
    )
end

main()
