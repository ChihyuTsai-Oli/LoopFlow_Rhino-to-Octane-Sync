-- ============================================================
-- 腳本名稱 : LiveLink_R2O_Camera
-- 版本     : v3.0
-- 日期     : 2026-04-27
-- 作者     : Cursor + Claude Sonnet 4.6
-- 功能說明 : 自動解析設定檔（%APPDATA%\McNeel\Rhinoceros\8.0\scripts\LoopFlow_R2O\Data\R2O_Path.txt）
--            讀取攝影機同步檔，即時同步 Rhino 視角至 Octane。
-- ============================================================

-- @description Rhino to Octane Camera Sync Macro
-- @shortcut Ctrl + Q
--
-- 【使用說明】
-- 1) Rhino 端先啟用 `LiveLink_R2O_Camera.py`（常開即可）。
-- 2) Octane Standalone 需要更新視角時，按 `Ctrl + Q` 或執行本腳本讀取同步檔。
-- 3) 注意：Octane 場景中的 Thin Lens Camera 節點必須從 Render Target 中
--    「展開（Expand）」為獨立節點，腳本才能找到並同步；
--    若 Camera 仍 collapse 在 Render Target 內則無效。
--
-- 【變數連動注意事項】
-- - 讀取設定檔 R2O_Path.txt 的 DataPath 與 CameraFile 欄位。

-- ── 路徑常數（依安裝位置自動推算，不依賴硬編碼） ───────────────────
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
    -- Camera 必須從 Render Target 中「展開（Expand）」為獨立節點才可被找到；
    -- collapse 狀態的 Camera 無法透過 Octane Lua API 存取。
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
        print("[Error] 找不到攝影機同步檔: " .. syncPath)
        return
    end

    local status, data = pcall(chunk)
    if not status or type(data) ~= "table" then
        print("[Error] 攝影機資料解析失敗。")
        return
    end

    local camNode = getThinLensCamera()
    if not camNode then
        print("[Warning] 找不到 Thin Lens Camera 節點，請確保場景中至少有一台相機。")
        return
    end

    print("========================================")
    camNode:setPinValue(octane.P_POSITION, data.position)
    camNode:setPinValue(octane.P_TARGET, data.target)
    camNode:setPinValue(octane.P_UP, data.up_vector)
    camNode:setPinValue(octane.P_FOV, data.fov_degrees)
    print("[Success] 攝影機視角同步完成。")
    print("========================================")
end

main()
