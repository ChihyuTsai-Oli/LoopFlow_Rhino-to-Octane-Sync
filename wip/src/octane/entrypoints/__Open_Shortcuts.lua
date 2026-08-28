-- R2O 2.0：打開同資料夾的 R2O_Shortcuts.txt（記事本／預設程式）。
-- 路徑從本腳本所在資料夾推導，不寫死 AppData 安裝目錄。
-- Docs: wip/docs/系統設定.md

local SHORTCUTS_NAME = "R2O_Shortcuts.txt"

local function script_dir()
    local src = debug.getinfo(1, "S").source or ""
    if src:sub(1, 1) == "@" then
        src = src:sub(2)
    end
    src = src:gsub("/", "\\")
    if src:lower():match("%.lua$") then
        local dir = src:match("^(.*)[\\/][^\\/]+$")
        if dir and dir ~= "" then
            return dir
        end
    end
    return nil
end

local function pointer_lua_dir()
    local appdata = os.getenv("APPDATA") or ""
    if appdata == "" then
        return nil
    end
    local path = appdata:gsub("\\", "/") .. "/LoopFlow/R2O/current_project.json"
    local f = io.open(path, "rb")
    if not f then
        return nil
    end
    local raw = f:read("*a")
    f:close()
    local function unescape(s)
        return (s:gsub("\\\\", "\\"))
    end
    local short = raw:match('"config_root_short"%s*:%s*"([^"]*)"')
    local root = raw:match('"config_root"%s*:%s*"([^"]*)"')
    local base = (short and short ~= "") and short or root
    if not base or base == "" then
        return nil
    end
    return unescape(base):gsub("/", "\\") .. "\\lua"
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
                int MultiByteToWideChar(unsigned int, unsigned long, const char*, int, wchar_t*, int);
                void* ShellExecuteW(HWND, const wchar_t*, const wchar_t*, const wchar_t*, const wchar_t*, int);
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

local lua_dir = script_dir() or pointer_lua_dir()
if not lua_dir then
    print("[Open_Shortcuts] Cannot find the lua folder. Run R2O_Camera in Rhino first, or run this script from the workfiles lua folder.")
    return
end

local shortcuts = lua_dir .. "\\" .. SHORTCUTS_NAME
open_file(shortcuts)
print("[Open_Shortcuts] Opened: " .. shortcuts)
print("[Open_Shortcuts] After editing, run __Setup_Shortcuts.lua, then re-scan the Octane script folder.")
