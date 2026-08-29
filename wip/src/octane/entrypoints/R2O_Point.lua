-- R2O 2.0 Point：讀指標 → live/point.json → 更新群組 R2O_Point 內的 Scatter。
-- 跑一次腳本套用一次即結束。禁止把同步檔當 Lua 程式執行。Docs: wip/docs/工作流程.md
--
-- @description R2O Point
-- @shortcut

local POINTER_REL = "/LoopFlow/R2O/current_project.json"
local NG_NAME = "R2O_Point"
local NODE_PREFIX = "R2O_Point_"
local NODE_SPACING_X = 200
local NODE_START_X = 100
local NODE_START_Y = 200

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

-- ── 指標與 point.json ────────────────────────────────────────────────

local function load_pointer()
    local path = pointer_path()
    local raw, err = read_file(path)
    if not raw then
        return nil, "No project pointer. Run R2O_Point or R2O_Camera in Rhino first (saved .3dm). Missing: " .. path
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

local function point_json_candidates(pointer)
    local paths = {}
    if type(pointer.config_root_short) == "string" and pointer.config_root_short:match("%S") then
        paths[#paths + 1] = join_path(pointer.config_root_short, "live/point.json")
    end
    paths[#paths + 1] = join_path(pointer.config_root, "live/point.json")
    return paths
end

local function node_key_from_type_id(type_id)
    return NODE_PREFIX .. tostring(type_id or ""):gsub("::", "__")
end

local function xform_matrix(flat)
    if type(flat) ~= "table" or #flat ~= 12 then
        return nil
    end
    for i = 1, 12 do
        if type(flat[i]) ~= "number" then
            return nil
        end
    end
    return {
        { flat[1], flat[2], flat[3], flat[4] },
        { flat[5], flat[6], flat[7], flat[8] },
        { flat[9], flat[10], flat[11], flat[12] },
    }
end

local function validate_point(data)
    if type(data) ~= "table" then
        return "Point JSON root must be an object"
    end
    if tonumber(data.schema_version) ~= 1 then
        return "Unsupported point schema_version (need 1)"
    end
    if type(data.items) ~= "table" then
        return "Field items must be an array"
    end
    local seen = {}
    for i, item in ipairs(data.items) do
        if type(item) ~= "table" then
            return "items[" .. i .. "] must be an object"
        end
        local type_id = item.type_id
        if type(type_id) ~= "string" or type_id:match("^%s*$") then
            return "items[" .. i .. "].type_id must be a non-empty string"
        end
        if item.kind ~= "point" and item.kind ~= "block" then
            return "items[" .. i .. "].kind must be point or block"
        end
        if not xform_matrix(item.xform) then
            return "items[" .. i .. "].xform must be 12 numbers"
        end
        local key = node_key_from_type_id(type_id)
        if seen[key] and seen[key] ~= type_id then
            return "Node key collision for " .. key .. " from " .. seen[key] .. " | " .. type_id
        end
        seen[key] = type_id
    end
    return nil
end

local function group_transforms(items)
    local grouped = {}
    local order = {}
    local skipped = 0
    for _, item in ipairs(items) do
        local type_id = item.type_id
        if type(type_id) ~= "string" or type_id:match("^%s*$") then
            skipped = skipped + 1
        else
            local mat = xform_matrix(item.xform)
            if not mat then
                skipped = skipped + 1
            else
                if not grouped[type_id] then
                    grouped[type_id] = {}
                    order[#order + 1] = type_id
                end
                grouped[type_id][#grouped[type_id] + 1] = mat
            end
        end
    end
    return grouped, order, skipped
end

local function find_existing_ng(rootGraph, ngName)
    local existing = rootGraph:findItemsByName(ngName)
    if existing then
        for _, g in ipairs(existing) do
            local props = g:getProperties()
            if props and props.isGraph then
                return g
            end
        end
    end
    return nil
end

local function create_ng(rootGraph, ngName)
    return octane.nodegraph.create{
        type = octane.GT_STANDARD,
        name = ngName,
        graph = rootGraph,
        position = { 100, 100 },
    }
end

local function count_map(map)
    local n = 0
    for _ in pairs(map or {}) do
        n = n + 1
    end
    return n
end

local function find_named_scatter(rootGraph, scatterName)
    if not rootGraph or not scatterName then
        return nil
    end
    local items = rootGraph:findItemsByName(scatterName)
    if not items then
        return nil
    end
    for _, node in ipairs(items) do
        local props = node:getProperties()
        local typ = props and props.type
        if typ == octane.NT_GEO_SCATTER then
            return node
        end
        if node.getNodeType then
            local nt = node:getNodeType()
            if nt == octane.NT_GEO_SCATTER then
                return node
            end
        end
    end
    return items[1]
end

local function find_prefixed_scatters(graph, prefix)
    local result = {}
    if not graph then
        return result
    end
    local all = graph:findNodes(octane.NT_GEO_SCATTER, true)
    if all == nil then
        all = graph:findNodes(octane.NT_GEO_SCATTER)
    end
    if not all then
        return result
    end
    for _, node in ipairs(all) do
        local props = node:getProperties()
        local name = props and props.name
        if (not name or name == "") and node.getName then
            name = node:getName()
        end
        if name and name:sub(1, #prefix) == prefix then
            result[name] = node
        end
    end
    return result
end

local function apply_payload(data)
    if not octane or not octane.project or not octane.project.getSceneGraph then
        return false, "Octane scene API is not available."
    end
    local rootGraph = octane.project.getSceneGraph()
    if not rootGraph then
        return false, "No scene graph."
    end

    local grouped, order, skipped = group_transforms(data.items or {})
    local ngGroup = find_existing_ng(rootGraph, NG_NAME)
    -- 與 1.x 相同：更新從整場找前綴 Scatter（群組 findNodes 第二次常找不到）。
    -- 刪除仍只動群組內，避免碰到使用者自己的節點。
    local existingAll = find_prefixed_scatters(rootGraph, NODE_PREFIX)
    local existingInGroup = find_prefixed_scatters(ngGroup, NODE_PREFIX)
    print("[Found] " .. count_map(existingAll) .. " scatter(s) in scene, " .. count_map(existingInGroup) .. " in group " .. NG_NAME)

    local activeNames = {}
    local newIndex = 0
    local created = 0
    local updated = 0
    local deleted = 0

    for _, type_id in ipairs(order) do
        local transforms = grouped[type_id]
        local scatterName = node_key_from_type_id(type_id)
        activeNames[scatterName] = true
        local scatterNode = existingAll[scatterName] or existingInGroup[scatterName]
        if not scatterNode then
            scatterNode = find_named_scatter(rootGraph, scatterName)
        end
        if scatterNode then
            scatterNode:setAttribute(octane.A_TRANSFORMS, transforms)
            updated = updated + 1
            print("[Update] " .. scatterName .. ": " .. #transforms .. " transform(s)")
        else
            if not ngGroup then
                ngGroup = create_ng(rootGraph, NG_NAME)
                existingInGroup = find_prefixed_scatters(ngGroup, NODE_PREFIX)
            end
            local posX = NODE_START_X + newIndex * NODE_SPACING_X
            scatterNode = octane.node.create{
                type = octane.NT_GEO_SCATTER,
                name = scatterName,
                graphOwner = ngGroup,
                position = { posX, NODE_START_Y },
            }
            scatterNode:setAttribute(octane.A_TRANSFORMS, transforms)
            existingInGroup[scatterName] = scatterNode
            existingAll[scatterName] = scatterNode
            newIndex = newIndex + 1
            created = created + 1
            print("[Create] " .. scatterName .. ": " .. #transforms .. " transform(s) -> " .. NG_NAME)
        end
    end

    for name, node in pairs(existingInGroup) do
        if not activeNames[name] then
            node:destroy()
            deleted = deleted + 1
            print("[Delete] " .. name .. ": type no longer exists in Rhino")
        end
    end

    if skipped > 0 then
        print("[Skip] " .. skipped .. " item(s) with missing type_id or xform")
    end
    print("[R2O Point] Created " .. created .. ", updated " .. updated .. ", deleted " .. deleted .. ".")
    return true
end

local function load_point_payload()
    local pointer, err = load_pointer()
    if not pointer then
        return nil, err
    end
    local last_err
    for _, path in ipairs(point_json_candidates(pointer)) do
        local raw, read_err = read_file(path)
        if raw then
            local ok, data = pcall(decode_json, raw)
            if not ok or type(data) ~= "table" then
                return nil, "point.json is not valid JSON (partial write ignored)"
            end
            local verr = validate_point(data)
            if verr then
                return nil, verr
            end
            return { data = data, text = raw, path = path }
        end
        last_err = read_err
    end
    return nil, "point.json not found" .. (last_err and (" (" .. tostring(last_err) .. ")") or "")
end

local function apply_once()
    local loaded, err = load_point_payload()
    if not loaded then
        print("[R2O Point] " .. err)
        return false
    end
    local ok, apply_err = apply_payload(loaded.data)
    if not ok then
        print("[R2O Point] " .. apply_err)
        return false
    end
    local revision = tonumber(loaded.data.revision)
    print("[R2O Point] Applied revision " .. tostring(revision or "?") .. " → " .. loaded.path)
    print("[R2O Point] Applied once. Run this script again to apply the latest points.")
    return true
end

apply_once()

