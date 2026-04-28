-- ============================================================
-- Script Name  : LiveLink_R2O_Camera
-- Version           : v1.0
-- Date              : 2026-04-28
-- Author            : Cursor + Claude Sonnet 4.6
-- Description : Auto-parses the config file
--               (%APPDATA%\McNeel\Rhinoceros\8.0\scripts\LoopFlow_R2O\Data\R2O_Path.txt),
--               reads the camera sync file, and syncs the Rhino viewport to Octane in real time.
-- ============================================================

-- @description Rhino to Octane Camera Sync Macro
-- @shortcut Ctrl + Q
--
-- [Usage]
-- 1) Enable `LiveLink_R2O_Camera.py` on the Rhino side (keep it running).
-- 2) In Octane Standalone, press `Ctrl + Q` or run this script to apply the latest camera sync.
-- 3) Note: the Thin Lens Camera node in the Octane scene must be "Expanded" out of the
--    Render Target as a standalone node; a collapsed Camera cannot be accessed by this script.
--
-- [Variable Notes]
-- - Reads the DataPath and CameraFile fields from R2O_Path.txt.

-- ── Path constants (derived automatically from install location, no hard-coding) ──────────
local APPDATA     = os.getenv("APPDATA")
local INSTALL_DIR = APPDATA .. "\\McNeel\\Rhinoceros\\8.0\\scripts\\LoopFlow_R2O"
local DATA_DIR    = INSTALL_DIR .. "\\Data"
local CONFIG_FILE = DATA_DIR .. "\\R2O_Path.txt"

local function loadConfig()
    local cfg = {
        DataPath   = DATA_DIR,
        CameraFile = "R2O_Camera_Sync_Data.lua",
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

local function getThinLensCamera()
    local graph = octane.project.getSceneGraph()
    -- Camera must be "Expanded" out of the Render Target as a standalone node to be found;
    -- a collapsed Camera cannot be accessed via the Octane Lua API.
    local cams = graph:findNodes(octane.NT_CAM_THINLENS, true)
    if cams and #cams > 0 then return cams[1] end
    return nil
end

local function main()
    local cfg = loadConfig()
    local dataPath = cfg.DataPath:match("^%s*(.-)%s*$"):gsub("\\", "/")
    local syncPath = dataPath .. "/" .. cfg.CameraFile:match("^%s*(.-)%s*$")

    local chunk, err = loadfile(syncPath)
    if not chunk then
        print("[Error] Camera sync file not found: " .. syncPath)
        return
    end

    local status, data = pcall(chunk)
    if not status or type(data) ~= "table" then
        print("[Error] Failed to parse camera data.")
        return
    end

    local camNode = getThinLensCamera()
    if not camNode then
        print("[Warning] Thin Lens Camera node not found. Please ensure at least one camera exists in the scene.")
        return
    end

    print("========================================")
    camNode:setPinValue(octane.P_POSITION, data.position)
    camNode:setPinValue(octane.P_TARGET, data.target)
    camNode:setPinValue(octane.P_UP, data.up_vector)
    camNode:setPinValue(octane.P_FOV, data.fov_degrees)
    print("[Success] Camera view synced successfully.")
    print("========================================")
end

main()
