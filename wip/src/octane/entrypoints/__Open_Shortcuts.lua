-- R2O 2.0：打開同資料夾的 R2O_Shortcuts.txt（記事本／預設程式）。
-- 路徑：優先 debug.getinfo；失敗則備援「文件\LoopFlow\Rhino to OctaneRender Sync\lua」。
-- 不寫死 AppData。Docs: wip/docs/系統設定.md

local SHORTCUTS_NAME = "R2O_Shortcuts.txt"
local PRODUCT_LUA_REL = "Documents\\LoopFlow\\Rhino to OctaneRender Sync\\lua"
local MB_OK = 0x00000000
local MB_ICONERROR = 0x00000010
local MB_ICONINFORMATION = 0x00000040

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

local _win_ready = false
local function ensure_win()
    local ok, ffi = pcall(require, "ffi")
    if not ok or not ffi or ffi.os ~= "Windows" then
        return nil, "win32 ffi unavailable"
    end
    if not _win_ready then
        local cdef_ok = pcall(function()
            ffi.cdef[[
                typedef void* HWND;
                typedef unsigned int UINT;
                int MultiByteToWideChar(unsigned int, unsigned long, const char*, int, wchar_t*, int);
                void* ShellExecuteW(HWND, const wchar_t*, const wchar_t*, const wchar_t*, const wchar_t*, int);
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
    local w_caption = utf8_to_wide(ffi, tostring(caption or "R2O Open Shortcuts"))
    if w_text and w_caption then
        ffi.C.MessageBoxW(nil, w_text, w_caption, flags or MB_OK)
    end
end

local function open_file(path)
    local win = path:gsub("/", "\\")
    local ffi = ensure_win()
    if ffi then
        local wverb = utf8_to_wide(ffi, "open")
        local wpath = utf8_to_wide(ffi, win)
        if wverb and wpath then
            local shell32 = ffi.load("shell32")
            shell32.ShellExecuteW(nil, wverb, wpath, nil, nil, 1)
            return true
        end
    end
    os.execute('start "" "' .. win .. '"')
    return true
end

local lua_dir, source_kind = resolve_lua_dir()
if not lua_dir then
    message_box(
        "找不到 R2O_Shortcuts.txt。\n\n請在 Rhino 執行 ROOpen，確認「文件\\LoopFlow\\Rhino to OctaneRender Sync\\lua」已有腳本與熱鍵表，再重掃 Octane 腳本資料夾。",
        "R2O Open Shortcuts",
        MB_OK + MB_ICONERROR
    )
    return
end

local shortcuts = lua_dir .. "\\" .. SHORTCUTS_NAME
if not file_exists(shortcuts) then
    message_box(
        "熱鍵表不存在：\n" .. shortcuts,
        "R2O Open Shortcuts",
        MB_OK + MB_ICONERROR
    )
    return
end

open_file(shortcuts)
message_box(
    "已開啟熱鍵表：\n" .. shortcuts .. "\n\n路徑來源：" .. tostring(source_kind) ..
    "\n\n編輯後請跑 __Setup_Shortcuts.lua，再重掃 Octane 腳本資料夾。",
    "R2O Open Shortcuts",
    MB_OK + MB_ICONINFORMATION
)
print("[Open_Shortcuts] Opened: " .. shortcuts .. " (" .. tostring(source_kind) .. ")")
print("[Open_Shortcuts] After editing, run __Setup_Shortcuts.lua, then re-scan the Octane script folder.")
