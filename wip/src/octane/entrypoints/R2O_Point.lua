-- R2O 2.0 Point：讀指標 → live/point.json → 建立／更新 Scatter。
-- Scatter 與 Geometry group R2O_Point_Geometry 包在 nodegraph R2O_Point 裡。
-- 圖內自動把 Scatter 接到 Geometry group；NT_OUT_GEOMETRY 露出圖表幾何輸出。
-- 跑一次腳本套用一次即結束。禁止把同步檔當 Lua 程式執行。Docs: wip/docs/工作流程.md
--
-- @description R2O Point
-- @shortcut

local POINTER_REL = "/LoopFlow/R2O/current_project.json"
local NG_NAME = "R2O_Point"
local GEO_GROUP_NAME = "R2O_Point_Geometry"
local OUT_LINKER_NAME = "output"
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

local function node_name(node)
    if not node then
        return nil
    end
    local ok, props = pcall(function()
        return node:getProperties()
    end)
    if ok and type(props) == "table" and type(props.name) == "string" and props.name ~= "" then
        return props.name
    end
    if node.getName then
        local okName, name = pcall(function()
            return node:getName()
        end)
        if okName and type(name) == "string" and name ~= "" then
            return name
        end
    end
    return nil
end

local function same_node(a, b)
    if not a or not b then
        return false
    end
    if a == b then
        return true
    end
    local na = node_name(a)
    local nb = node_name(b)
    return na ~= nil and na == nb
end

local function is_managed_scatter(scatters, node)
    for _, scatter in ipairs(scatters) do
        if same_node(scatter, node) then
            return true
        end
    end
    return false
end

local function item_props(item)
    if not item then
        return nil
    end
    local ok, props = pcall(function()
        return item:getProperties()
    end)
    if ok and type(props) == "table" then
        return props
    end
    return nil
end

local function graph_contains(graph, item)
    if not graph or not item then
        return false
    end
    local props = item_props(item)
    local owner = props and props.graphOwner
    if owner == graph then
        return true
    end
    if owner and node_name(owner) == node_name(graph) then
        return true
    end
    local ok, owned = pcall(function()
        return graph:getOwnedItems()
    end)
    if ok and type(owned) == "table" then
        for _, it in ipairs(owned) do
            if it == item then
                return true
            end
        end
    end
    return false
end

local function find_geometry_group(graph, groupName)
    if not graph then
        return nil
    end
    local existing = graph:findItemsByName(groupName)
    if not existing then
        return nil
    end
    for _, node in ipairs(existing) do
        local props = node:getProperties()
        local typ = props and props.type
        if typ == octane.NT_GEO_GROUP then
            return node
        end
        if node.getNodeType and node:getNodeType() == octane.NT_GEO_GROUP then
            return node
        end
    end
    return nil
end

local function find_geometry_group_anywhere(rootGraph, ng)
    if ng then
        local inside = find_geometry_group(ng, GEO_GROUP_NAME)
        if inside then
            return inside
        end
    end
    return find_geometry_group(rootGraph, GEO_GROUP_NAME)
end

local function create_point_graph(rootGraph)
    local ok, ng = pcall(function()
        return octane.nodegraph.create{
            type = octane.GT_STANDARD,
            name = NG_NAME,
            graph = rootGraph,
            position = { NODE_START_X, NODE_START_Y - 80 },
        }
    end)
    if ok and ng then
        return ng
    end
    return nil, tostring(ng)
end

local function find_output_linker(graph)
    if not graph then
        return nil
    end
    if octane.NT_OUT_GEOMETRY then
        local ok, nodes = pcall(function()
            return graph:findNodes(octane.NT_OUT_GEOMETRY)
        end)
        if ok and type(nodes) == "table" then
            for _, node in ipairs(nodes) do
                return node
            end
        end
    end
    local existing = graph:findItemsByName(OUT_LINKER_NAME)
    if existing then
        for _, node in ipairs(existing) do
            local props = item_props(node)
            local typ = props and props.type
            if typ == octane.NT_OUT_GEOMETRY then
                return node
            end
        end
        return existing[1]
    end
    return nil
end

local function linker_already_connected(linker, target)
    if not linker or not target then
        return false
    end
    local src
    pcall(function()
        src = linker:getConnectedNode("input")
    end)
    if src and same_node(src, target) then
        return true
    end
    pcall(function()
        src = linker:getConnectedNodeIx(1)
    end)
    return src and same_node(src, target)
end

local function ensure_output_linker(graph, geoGroup)
    if not octane.NT_OUT_GEOMETRY then
        return nil, "Octane NT_OUT_GEOMETRY is not available."
    end
    local linker = find_output_linker(graph)
    local created = false
    if not linker then
        linker = octane.node.create{
            type = octane.NT_OUT_GEOMETRY,
            name = OUT_LINKER_NAME,
            graphOwner = graph,
            position = { NODE_START_X, NODE_START_Y - 400 },
        }
        if not linker then
            return nil, "Could not create " .. OUT_LINKER_NAME .. " geometry linker."
        end
        created = true
        print("[Create] " .. NG_NAME .. " / " .. OUT_LINKER_NAME)
    end
    if not linker_already_connected(linker, geoGroup) then
        local ok, err = pcall(function()
            linker:connectTo("input", geoGroup)
        end)
        if not ok then
            ok, err = pcall(function()
                linker:connectToIx(1, geoGroup)
            end)
        end
        if not ok then
            return nil, "Could not connect " .. GEO_GROUP_NAME .. " to graph output: " .. tostring(err)
        end
        print("[Link] " .. GEO_GROUP_NAME .. " -> " .. NG_NAME .. " " .. OUT_LINKER_NAME)
    end
    pcall(function()
        linker:evaluate()
    end)
    return linker, created
end

local function pack_managed_into_graph(rootGraph, existingNg, items)
    if not items or #items == 0 then
        return existingNg
    end
    local ok, packed = pcall(function()
        return rootGraph:group(items)
    end)
    if not ok or not packed then
        print("[Warn] Could not pack nodes into " .. NG_NAME .. ": " .. tostring(packed))
        print("[Info] Wire the scene to the " .. NG_NAME .. " geometry output after this graph exists.")
        return existingNg
    end
    pcall(function()
        packed:updateProperties({
            name = NG_NAME,
            position = { NODE_START_X, NODE_START_Y - 80 },
        })
    end)
    if existingNg and existingNg ~= packed then
        local leftover = true
        pcall(function()
            local owned = existingNg:getOwnedItems()
            if owned and #owned > 0 then
                leftover = false
            end
        end)
        if leftover then
            pcall(function()
                existingNg:destroy()
            end)
            print("[Info] Removed empty leftover " .. NG_NAME .. " graph.")
        end
    end
    print("[Pack] Scatter and " .. GEO_GROUP_NAME .. " are inside " .. NG_NAME)
    return packed
end

-- Geometry group 的輸入是依序的接腳，不是單一具名接腳。空腳回傳 nil。
local function read_pin_source(group, ix)
    local ok, node = pcall(function()
        return group:getConnectedNodeIx(ix)
    end)
    if ok then
        return true, node
    end
    return false, nil
end

local function ensure_geometry_group(rootGraph)
    local group = find_geometry_group(rootGraph, GEO_GROUP_NAME)
    if group then
        return group, false
    end
    group = octane.node.create{
        type = octane.NT_GEO_GROUP,
        name = GEO_GROUP_NAME,
        graphOwner = rootGraph,
        position = { NODE_START_X, NODE_START_Y - 220 },
    }
    return group, true
end

-- 已接上的受管 Scatter 不重複接。空腳留給新的 Scatter。使用者另外接進群組的幾何留著。
local function link_scatters(group, scatters)
    local pinCount = 0
    local okCount, count = pcall(function()
        return group:getPinCount()
    end)
    if okCount and type(count) == "number" then
        pinCount = count
    end

    local linkedNames = {}
    local emptyPins = {}
    for ix = 1, pinCount do
        local ok, src = read_pin_source(group, ix)
        if not ok then
            return nil, "Geometry group pins could not be read; existing links were left unchanged."
        end
        if src and is_managed_scatter(scatters, src) then
            local name = node_name(src)
            if name then
                linkedNames[name] = true
            end
        elseif not src then
            emptyPins[#emptyPins + 1] = ix
        end
    end

    local pending = {}
    for _, scatter in ipairs(scatters) do
        local name = node_name(scatter)
        if not (name and linkedNames[name]) then
            pending[#pending + 1] = scatter
        end
    end
    if #pending == 0 then
        if #scatters > 0 then
            print("[Link] " .. #scatters .. " scatter(s) already connected to " .. GEO_GROUP_NAME)
        end
        return 0
    end

    local need = #pending - #emptyPins
    if need > 0 then
        local newCount = pinCount + need
        local ok, err = pcall(function()
            group:setAttribute(octane.A_PIN_COUNT, newCount)
        end)
        if not ok then
            return nil, "Could not add geometry group inputs: " .. tostring(err)
        end
        for extra = 1, need do
            emptyPins[#emptyPins + 1] = pinCount + extra
        end
    end

    local linked = 0
    for i, scatter in ipairs(pending) do
        local ix = emptyPins[i]
        local name = node_name(scatter) or ("pin " .. tostring(ix))
        local ok, err = pcall(function()
            group:connectToIx(ix, scatter)
        end)
        if not ok then
            return nil, "Could not connect " .. name .. ": " .. tostring(err)
        end
        linked = linked + 1
        print("[Link] " .. name .. " -> " .. GEO_GROUP_NAME)
    end
    pcall(function()
        group:evaluate()
    end)
    return linked
end

local function first_xyz(transforms)
    local m = transforms and transforms[1]
    if type(m) ~= "table" or type(m[1]) ~= "table" then
        return ""
    end
    local x = tonumber(m[1][4]) or 0
    local y = tonumber(m[2] and m[2][4]) or 0
    local z = tonumber(m[3] and m[3][4]) or 0
    return string.format(" xyz=%.3f,%.3f,%.3f", x, y, z)
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
    local ng = find_existing_ng(rootGraph, NG_NAME)
    -- 受管範圍＝前綴 R2O_Point_（含已從舊群組炸開、或仍在場景根的節點）。
    local existingAll = find_prefixed_scatters(rootGraph, NODE_PREFIX)
    print("[Found] " .. count_map(existingAll) .. " scatter(s) on the scene")
    for name, _ in pairs(existingAll) do
        print("[Found] " .. name)
    end

    local rootManaged = false
    for _, node in pairs(existingAll) do
        if not ng or not graph_contains(ng, node) then
            rootManaged = true
            break
        end
    end
    local geoExisting = find_geometry_group_anywhere(rootGraph, ng)
    if geoExisting and (not ng or not graph_contains(ng, geoExisting)) then
        rootManaged = true
    end

    local createOwner = rootGraph
    if ng and not rootManaged then
        createOwner = ng
    elseif not ng and count_map(existingAll) == 0 then
        local createdNg, ngErr = create_point_graph(rootGraph)
        if not createdNg then
            return false, "Could not create " .. NG_NAME .. ": " .. tostring(ngErr)
        end
        ng = createdNg
        createOwner = ng
        print("[Create] " .. NG_NAME)
    end

    local activeNames = {}
    local newIndex = 0
    local created = 0
    local updated = 0
    local deleted = 0

    for _, type_id in ipairs(order) do
        local transforms = grouped[type_id]
        local scatterName = node_key_from_type_id(type_id)
        activeNames[scatterName] = true
        local scatterNode = existingAll[scatterName]
        if not scatterNode then
            scatterNode = find_named_scatter(rootGraph, scatterName)
            if not scatterNode and ng then
                scatterNode = find_named_scatter(ng, scatterName)
            end
        end
        if scatterNode then
            scatterNode:setAttribute(octane.A_TRANSFORMS, transforms)
            updated = updated + 1
            print("[Update] " .. scatterName .. ": " .. #transforms .. " transform(s)" .. first_xyz(transforms))
        else
            local posX = NODE_START_X + newIndex * NODE_SPACING_X
            scatterNode = octane.node.create{
                type = octane.NT_GEO_SCATTER,
                name = scatterName,
                graphOwner = createOwner,
                position = { posX, NODE_START_Y },
            }
            scatterNode:setAttribute(octane.A_TRANSFORMS, transforms)
            existingAll[scatterName] = scatterNode
            newIndex = newIndex + 1
            created = created + 1
            print("[Create] " .. scatterName .. ": " .. #transforms .. " transform(s) in " .. NG_NAME .. first_xyz(transforms))
        end
    end

    for name, node in pairs(existingAll) do
        if not activeNames[name] then
            node:destroy()
            deleted = deleted + 1
            print("[Delete] " .. name .. ": type no longer exists in Rhino")
        end
    end

    local activeNodes = {}
    for _, type_id in ipairs(order) do
        local scatterName = node_key_from_type_id(type_id)
        local scatterNode = existingAll[scatterName]
        if activeNames[scatterName] and scatterNode then
            activeNodes[#activeNodes + 1] = scatterNode
        end
    end

    local group, groupCreated = ensure_geometry_group(createOwner)
    if not group then
        return false, "Could not create geometry group " .. GEO_GROUP_NAME .. "."
    end
    if groupCreated then
        print("[Create] " .. GEO_GROUP_NAME)
    end
    local linked, linkErr = link_scatters(group, activeNodes)
    if linked == nil then
        return false, linkErr
    end

    local linkerOwner = ng
    if not linkerOwner or not graph_contains(ng, group) then
        linkerOwner = createOwner
    end
    local outLinker, outErr = ensure_output_linker(linkerOwner, group)
    if not outLinker then
        return false, outErr
    end

    local packItems = {}
    local function add_pack(item)
        if item and (not ng or not graph_contains(ng, item)) then
            packItems[#packItems + 1] = item
        end
    end
    for _, scatter in ipairs(activeNodes) do
        add_pack(scatter)
    end
    add_pack(group)
    add_pack(outLinker)
    if #packItems > 0 then
        ng = pack_managed_into_graph(rootGraph, ng, packItems)
        if ng then
            print("[Info] Wire the scene to the " .. NG_NAME .. " geometry output.")
        end
    end

    if skipped > 0 then
        print("[Skip] " .. skipped .. " item(s) with missing type_id or xform")
    end
    print("[R2O Point] Created " .. created .. ", updated " .. updated .. ", deleted " .. deleted .. ", linked " .. linked .. ".")
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

