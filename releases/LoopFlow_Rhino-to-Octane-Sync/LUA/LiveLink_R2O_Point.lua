-- ============================================================
-- Script Name  : LiveLink_R2O_Point
-- Version           : v1.0
-- Date              : 2026-04-28
-- Author            : Cursor + Claude Sonnet 4.6
-- Description : Auto-parses the config file
--               (%APPDATA%\McNeel\Rhinoceros\8.0\scripts\LoopFlow_R2O\Data\R2O_Path.txt),
--               reads the Point sync file, and creates or updates Scatter nodes by type.
--               Searches the whole scene for existing nodes and updates them in place
--               (without moving them), auto-removes nodes that no longer exist in the
--               sync data, and creates new nodes directly inside the group specified
--               in the config file.
-- ============================================================
--
-- [Usage]
-- 1) Run `LiveLink_R2O_Point.py` on the Rhino side to generate the sync file.
-- 2) Run this script in Octane Standalone to load the sync file and update Scatter nodes.
--
-- [Variable Notes]
-- - Reads the DataPath, PointFile, PointNgName, and PointPrefix fields from R2O_Path.txt.
--
-- @shortcut

-- ── Path constants (derived automatically from install location, no hard-coding) ──────────
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

-- Node layout parameters inside ng
local NODE_SPACING_X = 200
local NODE_START_X   = 100
local NODE_START_Y   = 200

-- Search the entire scene for all scatter nodes matching the prefix
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

-- Find an existing ng group (do not create one)
local function findExistingNg(rootGraph, ngName)
    local existingGraphs = rootGraph:findItemsByName(ngName)
    if existingGraphs then
        for _, g in ipairs(existingGraphs) do
            local gProps = g:getProperties()
            if gProps.isGraph then
                print("[Info] Found existing group: " .. ngName)
                return g
            end
        end
    end
    return nil
end

-- Create ng group (only called when new nodes are needed)
local function createNg(rootGraph, ngName)
    local ng = octane.nodegraph.create{
        type     = octane.GT_STANDARD,
        name     = ngName,
        graph    = rootGraph,
        position = { 100, 100 }
    }
    print("[Info] New group created: " .. ngName)
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
        print("[Error] Point sync file not found: " .. syncPath)
        return
    end

    local status, data = pcall(chunk)
    if not status or type(data) ~= "table" or not data.items then
        print("[Error] Failed to parse Point data.")
        return
    end

    -- Group transforms by type
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

    -- Step 1: Only look for an existing group; if this run only updates existing nodes and
    --         no group exists, skip creating an empty one
    local ngGroup = findExistingNg(rootGraph, NG_NAME)

    -- Step 2: Search the whole scene for all prefixed existing scatter nodes (for updating)
    local existingNodesAll = findAllPrefixedScatters(rootGraph, NODE_PREFIX)
    -- Search inside the group (for cleanup)
    local existingNodesInGroup = ngGroup and findAllPrefixedScatters(ngGroup, NODE_PREFIX) or {}

    -- Track node names used in this run
    local activeNames = {}
    -- Count new nodes created (used to calculate positions)
    local newNodeIndex = 0

    print("========================================")

    -- Step 3: Update existing nodes / create new nodes
    for pType, transforms in pairs(groupedTransforms) do
        local scatterNodeName = NODE_PREFIX .. pType
        activeNames[scatterNodeName] = true

        local scatterNode = existingNodesAll[scatterNodeName]

        if scatterNode then
            -- Existing node: update in place without moving (preserve user connections)
            scatterNode:setAttribute(octane.A_TRANSFORMS, transforms)
            print("[Update] " .. scatterNodeName .. ": updated " .. #transforms .. " transform(s)")
        else
            -- New node: requires ng group; defer creation (avoid empty ng when only updating)
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
            print("[Create] " .. scatterNodeName .. ": created with " .. #transforms .. " transform(s) -> " .. NG_NAME)
        end
    end

    -- Step 4: Remove stale nodes no longer in sync data (only inside the ng group; avoid
    --         deleting external nodes)
    for name, node in pairs(existingNodesInGroup) do
        if not activeNames[name] then
            node:destroy()
            print("[Delete] " .. name .. ": removed from scene (type no longer exists on Rhino side)")
        end
    end

    print("========================================")
end

main()
