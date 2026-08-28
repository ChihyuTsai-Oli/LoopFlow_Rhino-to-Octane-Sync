-- R2O 2.0 Camera：讀指標 → live/camera.json → 恰好一台已 Expand 的 Thin Lens。
-- 跑腳本會開「R2O Camera」小視窗；視窗開著才 realtime。關閉視窗即停止。
-- 禁止把同步檔當 Lua 程式執行。Docs: wip/docs/工作流程.md

local POLL_SEC = 0.2
local POINTER_REL = "/LoopFlow/R2O/current_project.json"
local POLL_LOCK_REL = "/LoopFlow/R2O/camera_poll.lock"

-- ── 純資料 JSON（不執行程式）──────────────────────────────────────────

local function json_error(msg, i)
    error(msg .. " at index " .. tostring(i))
end

local function decode_json(text)
    local i = 1
    local n = #text

    local function peek()
        return text:sub(i, i)
    end

    local function skip()
        while i <= n and text:sub(i, i):match("[ \t\r\n]") do
            i = i + 1
        end
    end

    local parse_value

    local function parse_string()
        if peek() ~= '"' then
            json_error("expected string", i)
        end
        i = i + 1
        local out = {}
        while i <= n do
            local c = text:sub(i, i)
            if c == '"' then
                i = i + 1
                return table.concat(out)
            end
            if c == "\\" then
                local nch = text:sub(i + 1, i + 1)
                i = i + 2
                local map = {
                    ['"'] = '"',
                    ["\\"] = "\\",
                    ["/"] = "/",
                    b = "\b",
                    f = "\f",
                    n = "\n",
                    r = "\r",
                    t = "\t",
                }
                if nch == "u" then
                    local hex = text:sub(i, i + 3)
                    i = i + 4
                    local code = tonumber(hex, 16) or 0
                    if code < 128 then
                        out[#out + 1] = string.char(code)
                    elseif code < 2048 then
                        out[#out + 1] = string.char(192 + math.floor(code / 64), 128 + (code % 64))
                    else
                        out[#out + 1] = string.char(
                            224 + math.floor(code / 4096),
                            128 + (math.floor(code / 64) % 64),
                            128 + (code % 64)
                        )
                    end
                else
                    out[#out + 1] = map[nch] or nch
                end
            else
                out[#out + 1] = c
                i = i + 1
            end
        end
        json_error("unterminated string", i)
    end

    local function parse_number()
        local s, e = text:find("^-?%d+%.?%d*[eE]?[+-]?%d*", i)
        if not s then
            json_error("expected number", i)
        end
        local token = text:sub(s, e)
        i = e + 1
        return tonumber(token)
    end

    local function parse_array()
        i = i + 1
        skip()
        local arr = {}
        if peek() == "]" then
            i = i + 1
            return arr
        end
        while true do
            arr[#arr + 1] = parse_value()
            skip()
            local c = peek()
            if c == "]" then
                i = i + 1
                return arr
            end
            if c ~= "," then
                json_error("expected comma or ]", i)
            end
            i = i + 1
            skip()
        end
    end

    local function parse_object()
        i = i + 1
        skip()
        local obj = {}
        if peek() == "}" then
            i = i + 1
            return obj
        end
        while true do
            skip()
            local key = parse_string()
            skip()
            if peek() ~= ":" then
                json_error("expected colon", i)
            end
            i = i + 1
            skip()
            obj[key] = parse_value()
            skip()
            local c = peek()
            if c == "}" then
                i = i + 1
                return obj
            end
            if c ~= "," then
                json_error("expected comma or }", i)
            end
            i = i + 1
        end
    end

    parse_value = function()
        skip()
        local c = peek()
        if c == '"' then
            return parse_string()
        end
        if c == "{" then
            return parse_object()
        end
        if c == "[" then
            return parse_array()
        end
        if c == "-" or c:match("%d") then
            return parse_number()
        end
        if text:sub(i, i + 3) == "true" then
            i = i + 4
            return true
        end
        if text:sub(i, i + 4) == "false" then
            i = i + 5
            return false
        end
        if text:sub(i, i + 3) == "null" then
            i = i + 4
            return nil
        end
        json_error("unexpected value", i)
    end

    if text:sub(1, 3) == "\239\187\191" then
        i = 4
    end
    local value = parse_value()
    skip()
    return value
end

-- ── 路徑／檔案（Windows 中文路徑：先 8.3，再 CreateFileW）────────────

local function appdata_path(rel)
    local appdata = os.getenv("APPDATA") or ""
    appdata = appdata:gsub("\\", "/"):gsub("/+$", "")
    return appdata .. rel
end

local function pointer_path()
    return appdata_path(POINTER_REL)
end

local function poll_lock_path()
    return appdata_path(POLL_LOCK_REL)
end

local function join_path(root, rel)
    root = tostring(root or ""):gsub("\\", "/"):gsub("/+$", "")
    rel = tostring(rel or ""):gsub("\\", "/"):gsub("^/+", "")
    return root .. "/" .. rel
end

local function read_file_stdio(path)
    local f, err = io.open(path, "rb")
    if not f then
        return nil, err
    end
    local data = f:read("*a")
    f:close()
    return data
end

local _win_ready = false
local function read_file_win32(path)
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
                BOOL CloseHandle(HANDLE);
                DWORD GetFileSize(HANDLE, DWORD*);
            ]]
        end)
        if not cdef_ok then
            return nil, "win32 cdef failed"
        end
        _win_ready = true
    end
    local winpath = tostring(path or ""):gsub("/", "\\")
    local n = ffi.C.MultiByteToWideChar(65001, 0, winpath, #winpath, nil, 0)
    if n <= 0 then
        return nil, "utf16 convert failed"
    end
    local wpath = ffi.new("wchar_t[?]", n + 1)
    ffi.C.MultiByteToWideChar(65001, 0, winpath, #winpath, wpath, n)
    wpath[n] = 0
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

local function read_file(path)
    local data, err = read_file_stdio(path)
    if data then
        return data
    end
    local win, win_err = read_file_win32(path)
    if win then
        return win
    end
    return nil, err or win_err
end

local function write_file(path, text)
    local f, err = io.open(path, "wb")
    if not f then
        return false, err
    end
    f:write(text or "")
    f:close()
    return true
end

local function delete_file(path)
    os.remove(path)
end

local function file_exists(path)
    local data = read_file(path)
    return data ~= nil
end

-- ── 指標與 camera.json ───────────────────────────────────────────────

local function load_pointer()
    local path = pointer_path()
    local raw, err = read_file(path)
    if not raw then
        return nil, "No project pointer. Run R2O_Camera in Rhino first (saved .3dm). Missing: " .. path
    end
    local ok, data = pcall(decode_json, raw)
    if not ok or type(data) ~= "table" then
        return nil, "Project pointer is not valid JSON: " .. path
    end
    local root = data.config_root
    if type(root) ~= "string" or root:match("^%s*$") then
        return nil, "Project pointer config_root is empty."
    end
    return data
end

local function camera_json_candidates(pointer)
    local paths = {}
    if type(pointer.config_root_short) == "string" and pointer.config_root_short:match("%S") then
        paths[#paths + 1] = join_path(pointer.config_root_short, "live/camera.json")
    end
    paths[#paths + 1] = join_path(pointer.config_root, "live/camera.json")
    return paths
end

local function validate_camera(data)
    if type(data) ~= "table" then
        return "Camera JSON root must be an object"
    end
    if tonumber(data.schema_version) ~= 1 then
        return "Unsupported camera schema_version (need 1)"
    end
    for _, key in ipairs({ "position", "target", "up_vector" }) do
        local v = data[key]
        if type(v) ~= "table" or #v ~= 3 then
            return "Field " .. key .. " must be a numeric [x, y, z] array"
        end
        for i = 1, 3 do
            if type(v[i]) ~= "number" then
                return "Field " .. key .. " must be numeric"
            end
        end
    end
    if type(data.fov_degrees) ~= "number" then
        return "Field fov_degrees must be numeric"
    end
    return nil
end

-- ── Thin Lens：恰好一台已 Expand ─────────────────────────────────────

local function find_expanded_thin_lenses()
    if not octane or not octane.project or not octane.project.getSceneGraph then
        return nil, "Octane scene API is not available."
    end
    local graph = octane.project.getSceneGraph()
    if not graph then
        return nil, "No scene graph."
    end
    local cams = graph:findNodes(octane.NT_CAM_THINLENS, true)
    if cams == nil then
        cams = graph:findNodes(octane.NT_CAM_THINLENS)
    end
    return cams or {}
end

local function require_one_camera()
    local cams, err = find_expanded_thin_lenses()
    if err then
        return nil, err
    end
    local n = #cams
    if n == 0 then
        return nil, "No expanded Thin Lens Camera found. Expand it out of the Render Target as a standalone node."
    end
    if n > 1 then
        return nil, "Found " .. n .. " expanded Thin Lens cameras. Keep exactly one, then run again."
    end
    return cams[1]
end

local function apply_payload(data)
    local cam, err = require_one_camera()
    if not cam then
        return false, err
    end
    cam:setPinValue(octane.P_POSITION, data.position)
    cam:setPinValue(octane.P_TARGET, data.target)
    cam:setPinValue(octane.P_UP, data.up_vector)
    cam:setPinValue(octane.P_FOV, data.fov_degrees)
    return true
end

local last_applied_revision = nil
local last_applied_text = nil
local last_error_msg = nil
local last_error_clock = 0

local function note_error(msg)
    local now = os.clock()
    if msg ~= last_error_msg or (now - last_error_clock) > 5 then
        print("[R2O Camera] " .. msg)
        last_error_msg = msg
        last_error_clock = now
    end
end

local function load_camera_payload()
    local pointer, err = load_pointer()
    if not pointer then
        return nil, err
    end
    local last_err
    for _, path in ipairs(camera_json_candidates(pointer)) do
        local raw, read_err = read_file(path)
        if raw then
            local ok, data = pcall(decode_json, raw)
            if not ok or type(data) ~= "table" then
                return nil, "camera.json is not valid JSON (partial write ignored)"
            end
            local verr = validate_camera(data)
            if verr then
                return nil, verr
            end
            return { data = data, text = raw, path = path }
        end
        last_err = read_err
    end
    return nil, "camera.json not found" .. (last_err and (" (" .. tostring(last_err) .. ")") or "")
end

local function apply_if_changed(force, quiet)
    local loaded, err = load_camera_payload()
    if not loaded then
        note_error(err)
        return false, err
    end
    local revision = tonumber(loaded.data.revision)
    if not force then
        if last_applied_text == loaded.text then
            return true, "unchanged"
        end
        if revision ~= nil and last_applied_revision ~= nil and revision == last_applied_revision then
            return true, "unchanged"
        end
    end
    local ok, apply_err = apply_payload(loaded.data)
    if not ok then
        note_error(apply_err)
        return false, apply_err
    end
    last_applied_revision = revision
    last_applied_text = loaded.text
    if not quiet then
        print("[R2O Camera] Applied revision " .. tostring(revision or "?") .. " → " .. loaded.path)
    end
    return true, "applied"
end

local function apply_once()
    return apply_if_changed(true, false)
end

-- ── 狀態視窗開著時輪詢：Windows SetTimer（showWindow 會幫我們派送訊息）

local function timer_component_type()
    if not (octane and octane.gui and octane.gui.componentType) then
        return nil
    end
    return octane.gui.componentType.TIMER
end

local win_timer = { user32 = nil, id = nil, proc = nil }

local function stop_win_timer()
    if win_timer.user32 and win_timer.id and win_timer.id ~= 0 then
        pcall(function()
            win_timer.user32.KillTimer(nil, win_timer.id)
        end)
    end
    win_timer.id = nil
    if win_timer.proc then
        pcall(function()
            win_timer.proc:free()
        end)
        win_timer.proc = nil
    end
    win_timer.user32 = nil
end

local function start_win_timer(on_tick)
    local ok, ffi = pcall(require, "ffi")
    if not ok or not ffi or ffi.os ~= "Windows" then
        return false
    end
    local loaded, user32 = pcall(ffi.load, "user32")
    if not loaded or not user32 then
        return false
    end
    pcall(function()
        ffi.cdef[[
            typedef void* HWND;
            typedef uint32_t UINT;
            typedef uint64_t UINT_PTR;
            typedef uint32_t DWORD;
            typedef void (__stdcall *TIMERPROC)(HWND, UINT, UINT_PTR, DWORD);
            UINT_PTR SetTimer(HWND, UINT_PTR, UINT, TIMERPROC);
            int KillTimer(HWND, UINT_PTR);
        ]]
    end)
    local busy = false
    local proc = ffi.cast("TIMERPROC", function()
        if busy then
            return
        end
        busy = true
        pcall(on_tick)
        busy = false
    end)
    local id = user32.SetTimer(nil, 0, math.floor(POLL_SEC * 1000), proc)
    if not id or id == 0 then
        pcall(function()
            proc:free()
        end)
        return false
    end
    win_timer.user32 = user32
    win_timer.id = id
    win_timer.proc = proc
    return true
end

local function start_realtime_window()
    if not (octane and octane.gui) then
        return false
    end

    local started = false
    pcall(function()
        local stopped = false
        local status_label = octane.gui.create({
            type = octane.gui.componentType.LABEL,
            text = "Keep this window open for realtime. Close to stop.",
            width = 440,
            height = 24,
        })
        local stop_btn = octane.gui.create({
            type = octane.gui.componentType.BUTTON,
            text = "Stop",
            width = 440,
            height = 28,
        })
        local group = octane.gui.create({
            type = octane.gui.componentType.GROUP,
            rows = 2,
            cols = 1,
            children = { status_label, stop_btn },
        })
        local window = octane.gui.create({
            type = octane.gui.componentType.WINDOW,
            text = "R2O Camera",
            children = { group },
            width = 460,
            height = 90,
        })

        local function request_stop()
            stopped = true
            stop_win_timer()
            delete_file(poll_lock_path())
        end

        local function on_tick()
            if stopped then
                return
            end
            apply_if_changed(false, true)
        end

        local function on_gui(comp, event)
            if event == octane.gui.eventType.WINDOW_CLOSE then
                request_stop()
                apply_if_changed(true, false)
            elseif event == octane.gui.eventType.BUTTON_CLICKED and comp == stop_btn then
                request_stop()
                apply_if_changed(true, false)
                pcall(function()
                    window:closeWindow()
                end)
            end
        end
        window:updateProperties({ callback = on_gui })
        stop_btn:updateProperties({ callback = on_gui })

        write_file(poll_lock_path(), "running\n")
        local polling = start_win_timer(on_tick)
        if not polling then
            local timer_type = timer_component_type()
            if timer_type ~= nil then
                octane.gui.create({
                    type = timer_type,
                    interval = math.floor(POLL_SEC * 1000),
                    callback = on_tick,
                })
                polling = true
            end
        end
        if not polling then
            delete_file(poll_lock_path())
            error("no timer")
        end

        print("[R2O Camera] Realtime on. Keep the R2O Camera window open; close it to stop.")
        started = true
        window:showWindow()
        request_stop()
    end)

    stop_win_timer()
    delete_file(poll_lock_path())
    return started
end

local function main()
    delete_file(poll_lock_path())
    apply_once()
    if start_realtime_window() then
        print("[R2O Camera] Realtime off.")
        return
    end
    print("[R2O Camera] Applied once. Realtime window unavailable; run this script again to apply.")
end

main()
