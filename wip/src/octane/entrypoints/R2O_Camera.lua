-- R2O 2.0 Camera：讀指標 → live/camera.json → 恰好一台已 Expand 的 Thin Lens。
-- 預設 real-time（狀態視窗／輪詢）；再跑一次或按 Stop = 關輪詢並套用目前檔。
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

-- ── 路徑／檔案 ────────────────────────────────────────────────────────

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

local function read_file(path)
    local f, err = io.open(path, "rb")
    if not f then
        return nil, err
    end
    local data = f:read("*a")
    f:close()
    return data
end

local function write_file(path, text)
    local dir = path:match("^(.*)/[^/]+$")
    if dir then
        os.execute('mkdir "' .. dir:gsub("/", "\\") .. '" >nul 2>&1')
    end
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
    local f = io.open(path, "rb")
    if not f then
        return false
    end
    f:close()
    return true
end

local function join_path(root, rel)
    root = tostring(root or ""):gsub("\\", "/"):gsub("/+$", "")
    rel = tostring(rel or ""):gsub("\\", "/"):gsub("^/+", "")
    return root .. "/" .. rel
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

local function camera_json_path(pointer)
    return join_path(pointer.config_root, "live/camera.json")
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
    local path = camera_json_path(pointer)
    local raw, read_err = read_file(path)
    if not raw then
        return nil, "camera.json not found: " .. path .. (read_err and (" (" .. tostring(read_err) .. ")") or "")
    end
    local ok, data = pcall(decode_json, raw)
    if not ok or type(data) ~= "table" then
        return nil, "camera.json is not valid JSON (partial write ignored): " .. path
    end
    local verr = validate_camera(data)
    if verr then
        return nil, verr
    end
    return { data = data, text = raw, path = path }
end

local function apply_if_changed(force)
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
    print("[R2O Camera] Applied revision " .. tostring(revision or "?") .. " → " .. loaded.path)
    return true, "applied"
end

local function apply_once()
    return apply_if_changed(true)
end

-- ── 輪詢：狀態視窗 + dispatchGuiEvents（不 sleep 鎖死 UI）────────────
-- Octane 沒有非 GUI timer；腳本結束即停止。ED-19 real-time 因此必須
-- 短暫使用 octane.gui（狀態視窗／事件派送），與 Authoring 工具列分開。

local function sleep_ms(ms)
    local ok, ffi = pcall(require, "ffi")
    if ok and ffi then
        pcall(function()
            if ffi.os == "Windows" then
                ffi.cdef[[ void Sleep(int ms); ]]
                ffi.C.Sleep(ms)
            end
        end)
        return
    end
    local t0 = os.clock()
    while (os.clock() - t0) * 1000 < ms do
    end
end

local function start_realtime()
    write_file(poll_lock_path(), "running\n")
    local stopped = false
    local used_blocking_window = false
    local status_label

    local function set_status(text)
        print("[R2O Camera] " .. text)
        if status_label then
            pcall(function()
                status_label:updateProperties({ text = text })
            end)
        end
    end

    local function request_stop()
        stopped = true
        delete_file(poll_lock_path())
    end

    apply_once()
    set_status("Realtime on. Stop button / close window / run this script again applies once and stops.")

    local has_gui = octane and octane.gui
    if has_gui then
        pcall(function()
            status_label = octane.gui.create({
                type = octane.gui.componentType.LABEL,
                text = "R2O Camera realtime",
                width = 420,
                height = 24,
            })
            local stop_btn = octane.gui.create({
                type = octane.gui.componentType.BUTTON,
                text = "Stop — apply once",
                width = 420,
                height = 28,
            })
            local group = octane.gui.create({
                type = octane.gui.componentType.GROUP,
                rows = 2,
                cols = 1,
                children = { status_label, stop_btn },
            })
            local win_w = 440
            pcall(function()
                win_w = group:getProperties().width or win_w
            end)
            local window = octane.gui.create({
                type = octane.gui.componentType.WINDOW,
                text = "R2O Camera",
                children = { group },
                width = win_w,
                height = 90,
            })

            local function on_gui(comp, event)
                if event == octane.gui.eventType.WINDOW_CLOSE then
                    request_stop()
                    apply_once()
                elseif event == octane.gui.eventType.BUTTON_CLICKED and comp == stop_btn then
                    request_stop()
                    apply_once()
                    pcall(function()
                        window:closeWindow()
                    end)
                end
            end
            pcall(function()
                window:updateProperties({ callback = on_gui })
                stop_btn:updateProperties({ callback = on_gui })
            end)

            local timer_type = octane.gui.componentType.TIMER
            if timer_type then
                local timer = octane.gui.create({
                    type = timer_type,
                    interval = math.floor(POLL_SEC * 1000),
                    callback = function()
                        if stopped or not file_exists(poll_lock_path()) then
                            request_stop()
                            pcall(function()
                                window:closeWindow()
                            end)
                            return
                        end
                        apply_if_changed(false)
                    end,
                })
                pcall(function()
                    timer:updateProperties({ running = true })
                end)
                used_blocking_window = true
                window:showWindow()
            end
        end)
    end

    if used_blocking_window then
        delete_file(poll_lock_path())
        print("[R2O Camera] Realtime off.")
        return
    end

    while (not stopped) and file_exists(poll_lock_path()) do
        apply_if_changed(false)
        if has_gui and octane.gui.dispatchGuiEvents then
            pcall(function()
                octane.gui.dispatchGuiEvents(1)
            end)
        end
        sleep_ms(math.floor(POLL_SEC * 1000))
    end
    apply_once()
    delete_file(poll_lock_path())
    print("[R2O Camera] Realtime off.")
end

local function main()
    if file_exists(poll_lock_path()) then
        delete_file(poll_lock_path())
        apply_once()
        print("[R2O Camera] Realtime off. Applied current file once.")
        return
    end
    start_realtime()
end

main()
