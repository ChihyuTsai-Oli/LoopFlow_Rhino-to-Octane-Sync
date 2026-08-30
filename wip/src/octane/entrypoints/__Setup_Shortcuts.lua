-- R2O 2.0：讀同資料夾 R2O_Shortcuts.txt，寫入各 LiveLink 腳本的 -- @shortcut。
-- 路徑從本腳本所在資料夾推導，不寫死 AppData 安裝目錄。
-- 中文路徑：stdio 失敗則 CreateFileW。Docs: wip/docs/系統設定.md

local SHORTCUTS_NAME = "R2O_Shortcuts.txt"
local SKIP = {
    __Setup_Shortcuts = true,
    __Open_Shortcuts = true,
}

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
                typedef unsigned long DWORD;
                typedef int BOOL;
                int MultiByteToWideChar(unsigned int, DWORD, const char*, int, wchar_t*, int);
                HANDLE CreateFileW(const wchar_t*, DWORD, DWORD, void*, DWORD, DWORD, HANDLE);
                BOOL ReadFile(HANDLE, void*, DWORD, DWORD*, void*);
                BOOL WriteFile(HANDLE, const void*, DWORD, DWORD*, void*);
                BOOL CloseHandle(HANDLE);
                DWORD GetFileSize(HANDLE, DWORD*);
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
    local lua_dir = script_dir()
    if not lua_dir then
        print("[__Setup_Shortcuts] Cannot find the lua folder. Point Octane Script directory at the folder that contains this script.")
        return
    end

    local shortcuts, order = load_shortcuts(join(lua_dir, SHORTCUTS_NAME))
    if not shortcuts then
        return
    end

    local updated_count = 0
    local skipped_count = 0

    print("========================================")
    print("[__Setup_Shortcuts] Applying hotkeys in: " .. lua_dir)

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
                else
                    if write_file(filePath, newContent) then
                        local display = shortcuts[baseName] ~= "" and shortcuts[baseName] or "(no hotkey)"
                        print("[Updated] " .. fname .. " -> " .. display)
                        updated_count = updated_count + 1
                    else
                        print("[Error] Cannot write: " .. filePath)
                    end
                end
            end
        end
    end

    print("----------------------------------------")
    print(("[Done] Updated %d script(s), skipped %d."):format(updated_count, skipped_count))
    print("Re-scan the Octane script folder to activate the hotkeys.")
    print("After a new copy of the lua folder, run this script again.")
    print("========================================")
end

main()
