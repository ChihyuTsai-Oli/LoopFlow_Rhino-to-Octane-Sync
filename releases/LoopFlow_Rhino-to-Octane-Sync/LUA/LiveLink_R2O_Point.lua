-- ============================================================
-- 腳本名稱 : LiveLink_R2O_Point
-- 版本     : v4.0
-- 日期     : 2026-04-27
-- 作者     : Cursor + Claude Sonnet 4.6
-- 功能說明 : 自動解析設定檔（%APPDATA%\McNeel\Rhinoceros\8.0\scripts\LoopFlow_R2O\Data\R2O_Path.txt）
--            讀取 Point 同步檔，依類型建立或更新 Scatter 節點。
--            全場景搜尋既有節點並就地更新（不搬動），
--            自動清理已不存在於同步資料的舊節點，
--            新建的節點直接建立於設定檔指定的群組內。
-- ============================================================
--
-- 【使用說明】
-- 1) Rhino 端先執行 `LiveLink_R2O_Point.py` 產生同步檔。
-- 2) Octane Standalone 執行本腳本讀取同步檔並更新 Scatter。
--
-- 【變數連動注意事項】
-- - 讀取設定檔 R2O_Path.txt 的 DataPath、PointFile、PointNgName、PointPrefix 欄位。
--
-- @shortcut

-- ── 路徑常數（依安裝位置自動推算，不依賴硬編碼） ───────────────────
local APPDATA     = os.getenv("APPDATA")
local INSTALL_DIR = APPDATA .. "\\McNeel\\Rhinoceros\\8.0\\scripts\\LoopFlow_R2O"
local DATA_DIR    = INSTALL_DIR .. "\\Data"
local CONFIG_FILE = DATA_DIR .. "\\R2O_Path.txt"

local function loadConfig()
    local cfg = {
        DataPath    = DATA_DIR,
        PointFile   = "R2O_Point_Sync_Data.lua",
        PointNgName = "R2O_Point",
        PointPrefix = "R2O_Point_",
    }
    local f = io.open(CONFIG_FILE, "r")
    if f then
        for line in f:lines() do
            local k, v = line:match("^(%w+):%s*(.*)")
            if k and cfg[k] ~= nil then cfg[k] = v end
        end
        f:close()
    end
    return cfg
end

-- ng 內部節點排列參數
local NODE_SPACING_X = 200
local NODE_START_X   = 100
local NODE_START_Y   = 200

-- 在整個場景中搜尋所有符合前綴的 scatter 節點
local function findAllPrefixedScatters(rootGraph, prefix)
    local result = {}
    local allScatters = rootGraph:findNodes(octane.NT_GEO_SCATTER, true)
    if allScatters then
        for _, n in ipairs(allScatters) do
            local name = n:getProperties().name
            if name and name:sub(1, #prefix) == prefix then
                result[name] = n
            end
        end
    end
    return result
end

-- 尋找既有 ng 群組（不建立）
local function findExistingNg(rootGraph, ngName)
    local existingGraphs = rootGraph:findItemsByName(ngName)
    if existingGraphs then
        for _, g in ipairs(existingGraphs) do
            local gProps = g:getProperties()
            if gProps.isGraph then
                print("[Info] 找到既有群組: " .. ngName)
                return g
            end
        end
    end
    return nil
end

-- 建立 ng 群組（僅在確定需要新節點時呼叫）
local function createNg(rootGraph, ngName)
    local ng = octane.nodegraph.create{
        type     = octane.GT_STANDARD,
        name     = ngName,
        graph    = rootGraph,
        position = { 100, 100 }
    }
    print("[Info] 建立新群組: " .. ngName)
    return ng
end

local function main()
    local cfg = loadConfig()
    local dataPath   = cfg.DataPath:match("^%s*(.-)%s*$"):gsub("\\", "/")
    local syncPath   = dataPath .. "/" .. cfg.PointFile:match("^%s*(.-)%s*$")
    local NG_NAME    = cfg.PointNgName:match("^%s*(.-)%s*$")
    local NODE_PREFIX = cfg.PointPrefix:match("^%s*(.-)%s*$")

    local chunk, err = loadfile(syncPath)
    if not chunk then
        print("[Error] 找不到 Point 同步檔: " .. syncPath)
        return
    end

    local status, data = pcall(chunk)
    if not status or type(data) ~= "table" or not data.items then
        print("[Error] Point 資料解析失敗。")
        return
    end

    -- 依類型分組 transforms
    local groupedTransforms = {}
    for _, item in ipairs(data.items) do
        local pType = item.type or "Default_Point"
        if not groupedTransforms[pType] then
            groupedTransforms[pType] = {}
        end
        local f = item.xform
        local mat = {
            { f[1], f[2], f[3], f[4] },
            { f[5], f[6], f[7], f[8] },
            { f[9], f[10], f[11], f[12] }
        }
        table.insert(groupedTransforms[pType], mat)
    end

    local rootGraph = octane.project.getSceneGraph()

    -- Step 1: 先只找既有群組；若本次只更新既有節點且群組不存在，就不建立空群組
    local ngGroup = findExistingNg(rootGraph, NG_NAME)

    -- Step 2: 全場景搜尋所有符合前綴的既有 scatter 節點（用於更新）
    local existingNodesAll = findAllPrefixedScatters(rootGraph, NODE_PREFIX)
    -- 群組內搜尋（用於清理）
    local existingNodesInGroup = ngGroup and findAllPrefixedScatters(ngGroup, NODE_PREFIX) or {}

    -- 記錄本次有用到的節點名稱
    local activeNames = {}
    -- 計算新建節點數（用於排列位置）
    local newNodeIndex = 0

    print("========================================")

    -- Step 3: 更新既有節點 / 建立新節點
    for pType, transforms in pairs(groupedTransforms) do
        local scatterNodeName = NODE_PREFIX .. pType
        activeNames[scatterNodeName] = true

        local scatterNode = existingNodesAll[scatterNodeName]

        if scatterNode then
            -- 既有節點：就地更新，不搬動（保留使用者的接線）
            scatterNode:setAttribute(octane.A_TRANSFORMS, transforms)
            print("[Update] " .. scatterNodeName .. ": 更新 " .. #transforms .. " 筆位置與旋轉矩陣")
        else
            -- 新節點：需要 ng 群組，延遲建立（避免只更新時產生空 ng）
            if not ngGroup then
                ngGroup = createNg(rootGraph, NG_NAME)
            end

            local posX = NODE_START_X + newNodeIndex * NODE_SPACING_X
            local posY = NODE_START_Y

            scatterNode = octane.node.create{
                type       = octane.NT_GEO_SCATTER,
                name       = scatterNodeName,
                graphOwner = ngGroup,
                position   = { posX, posY }
            }
            scatterNode:setAttribute(octane.A_TRANSFORMS, transforms)
            newNodeIndex = newNodeIndex + 1
            print("[Create] " .. scatterNodeName .. ": 建立並寫入 " .. #transforms .. " 筆位置與旋轉矩陣 -> " .. NG_NAME)
        end
    end

    -- Step 4: 清理已不存在於同步資料的舊節點（僅針對 ng 群組內的節點，避免誤刪外部節點）
    for name, node in pairs(existingNodesInGroup) do
        if not activeNames[name] then
            node:destroy()
            print("[Delete] " .. name .. ": 已從場景移除（Rhino 端已無此類型）")
        end
    end

    print("========================================")
end

main()
