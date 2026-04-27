-- ============================================================
-- 腳本名稱 : Auto_Convert_StdSurf_to_Universal
-- 版本     : v2.0
-- 日期     : 2026-04-14
-- 作者     : Cursor + GPT-5.2
-- 功能說明 : 將選取的 USD node 內部所有 Standard Surface
--            Material 轉換為 Universal Material。
--            所有 pinOwned 子節點會隨舊材質被銷毀，
--            因此在建立新材質前完整備份貼圖路徑與色值，
--            建立後重新設定。
--            使用方式：選取 USD geometry node（可多選）後執行。
-- ============================================================
-- @shortcut Shift + M
--
-- 【使用說明】
-- 1) 在 Octane Standalone 選取 USD geometry node（可多選）後執行本腳本。
--
-- 【變數連動注意事項】
-- - 本腳本不讀取 `R2O_Path.txt`，不影響 R2O 同步流程。

local NT_STD_SURFACE = 277
local NT_UNIVERSAL   = 130
local NT_IN_MATERIAL = 20007
local P_INPUT        = 82

-- ── Pin 映射定義 ────────────────────────────────────────────

-- 共用 pin（pin ID 相同，pinOwned 子節點會被自動繼承）
local SHARED_PINS = {
    {  18, "Bump"                     },
    {  33, "Dispersion"               },
    {  41, "Emission"                 },
    {  46, "Fake Shadows"             },
    {  49, "Film Width"               },
    { 119, "Normal"                   },
    { 125, "Opacity"                  },
    { 146, "Refraction Alpha"         },
    { 203, "Rotation"                 },
    { 204, "Roughness"                },
    { 218, "Smooth"                   },
    { 222, "Specular"                 },
    { 245, "Transmission"             },
    { 377, "Sheen"                    },
    { 387, "Sheen Roughness"          },
    { 410, "Metallic"                 },
    { 437, "Coating"                  },
    { 438, "Coating Roughness"        },
    { 467, "Round Edges"              },
    { 474, "Material Layer"           },
    { 477, "Coating Bump"             },
    { 478, "Coating Normal"           },
    { 564, "Priority"                 },
    { 731, "Smooth Shadow Terminator" },
    { 740, "Has Caustics"             },
    { 959, "Bump Height"              },
    {1024, "Dispersion Mode"          },
}

-- 需要重映射的 pin（src ≠ dst，pinOwned 子節點會被銷毀，需要手動重建）
local REMAP_PINS = {
    { src = 763, dst = 409, name = "Base Color → Albedo" },
}

-- IOR 重映射（Grayscale → Float）
local IOR_REMAP = {
    { src = 951, dst = 411, name = "IOR"         },
    { src = 952, dst = 439, name = "Coating IOR" },
    { src = 953, dst =  48, name = "Film IOR"    },
}

-- ── 備份貼圖節點的完整資訊 ─────────────────────────────────
local function backupTextureNode(node)
    if not node then return nil end
    local props = node:getProperties()
    local info = {
        type = props.type,
        name = props.name,
    }
    local ok1, filename = pcall(function() return node:getAttribute(octane.A_FILENAME) end)
    if ok1 and filename then info.filename = filename end
    local ok2, val = pcall(function() return node:getAttribute(octane.A_VALUE) end)
    if ok2 and val then info.value = val end
    local ok3, gamma = pcall(function() return node:getAttribute(octane.A_GAMMA) end)
    if ok3 and gamma then info.gamma = gamma end
    local ok4, power = pcall(function() return node:getAttribute(octane.A_POWER) end)
    if ok4 and power then info.power = power end
    local ok5, invert = pcall(function() return node:getAttribute(octane.A_INVERT) end)
    if ok5 and invert ~= nil then info.invert = invert end
    local ok6, cs = pcall(function() return node:getAttribute(octane.A_COLOR_SPACE) end)
    if ok6 and cs then info.colorSpace = cs end
    local ok7, legacy = pcall(function() return node:getAttribute(octane.A_LEGACY_PNG) end)
    if ok7 and legacy ~= nil then info.legacyPng = legacy end
    return info
end

-- ── 用備份資訊重建貼圖節點並接到新材質 ─────────────────────
local function restoreTextureToPin(uniMat, dstPinId, backup)
    if not backup then return false end

    local ok, newTex = pcall(function()
        return octane.node.create{
            type         = backup.type,
            name         = backup.name,
            pinOwnerNode = uniMat,
            pinOwnerId   = dstPinId,
        }
    end)

    if not ok or not newTex then
        if backup.value then
            pcall(function() uniMat:setPinValue(dstPinId, backup.value) end)
        end
        return false
    end

    if backup.filename then
        pcall(function() newTex:setAttribute(octane.A_FILENAME, backup.filename) end)
    end
    if backup.value then
        pcall(function() newTex:setAttribute(octane.A_VALUE, backup.value) end)
    end
    if backup.gamma then
        pcall(function() newTex:setAttribute(octane.A_GAMMA, backup.gamma) end)
    end
    if backup.power then
        pcall(function() newTex:setAttribute(octane.A_POWER, backup.power) end)
    end
    if backup.invert ~= nil then
        pcall(function() newTex:setAttribute(octane.A_INVERT, backup.invert) end)
    end
    if backup.colorSpace then
        pcall(function() newTex:setAttribute(octane.A_COLOR_SPACE, backup.colorSpace) end)
    end
    if backup.legacyPng ~= nil then
        pcall(function() newTex:setAttribute(octane.A_LEGACY_PNG, backup.legacyPng) end)
    end

    return true
end

-- ── 收集 IOR 值 ────────────────────────────────────────────
local function collectIorValues(stdMat)
    local iorData = {}
    for _, ior in ipairs(IOR_REMAP) do
        local ok, val = pcall(function() return stdMat:getPinValue(ior.src) end)
        if ok and val then
            local floatVal = val
            if type(val) == "table" then floatVal = val[1] end
            if floatVal and floatVal > 0 then
                iorData[ior.dst] = floatVal
            end
        end
    end
    return iorData
end

-- ── 轉換單一材質 ───────────────────────────────────────────
local function convertMaterial(inMatNode, stdMat)
    local matPath = inMatNode:getProperties().name or "?"
    local count = 0

    -- Phase 1: 備份需要重映射的 pin 的貼圖資訊
    local remapBackups = {}
    for _, pin in ipairs(REMAP_PINS) do
        local ok, conn = pcall(function() return stdMat:getConnectedNode(pin.src) end)
        if ok and conn then
            remapBackups[pin.dst] = backupTextureNode(conn)
        else
            local ok2, val = pcall(function() return stdMat:getPinValue(pin.src) end)
            if ok2 and val then
                remapBackups[pin.dst] = { value = val, type = -1 }
            end
        end
    end

    -- Phase 1b: 備份 IOR 值
    local iorData = collectIorValues(stdMat)

    -- Phase 2: 建立 Universal Material（取代 pinOwned 的舊材質）
    local uniMat = octane.node.create{
        type         = NT_UNIVERSAL,
        name         = "Universal material",
        pinOwnerNode = inMatNode,
        pinOwnerId   = P_INPUT,
    }

    -- Phase 3a: 重映射 pin — 用備份重建貼圖
    for _, pin in ipairs(REMAP_PINS) do
        local backup = remapBackups[pin.dst]
        if backup then
            if backup.type and backup.type > 0 then
                if restoreTextureToPin(uniMat, pin.dst, backup) then
                    count = count + 1
                end
            elseif backup.value then
                pcall(function() uniMat:setPinValue(pin.dst, backup.value) end)
                count = count + 1
            end
        end
    end

    -- Phase 3b: IOR 值
    for dstId, val in pairs(iorData) do
        local ok, _ = pcall(function() uniMat:setPinValue(dstId, val) end)
        if ok then count = count + 1 end
    end

    -- 計算自動繼承的共用 pin 數
    for _, pin in ipairs(SHARED_PINS) do
        local ok, conn = pcall(function() return uniMat:getConnectedNode(pin[1]) end)
        if ok and conn then count = count + 1 end
    end

    print("  🔄 [" .. matPath .. "] → Universal Material (" .. count .. " 個參數)")
    return true
end

-- ── 主程式 ──────────────────────────────────────────────────
local sel = octane.project.getSelection()
if not sel or #sel == 0 then
    print("❌ 請先選取 USD geometry node！")
    return
end

print("========================================")
print(" Convert Standard Surface → Universal")
print(" v2.2")
print("========================================")

local totalConverted = 0

for _, item in ipairs(sel) do
    local props = item:getProperties()

    if not props.isGraph then
        print("⚠️ [" .. (props.name or "?") .. "] 不是 Graph 節點，略過")
        goto continue
    end

    print("\n📦 處理: " .. (props.name or "?"))

    local ok, inMats = pcall(function() return item:findNodes(NT_IN_MATERIAL, false) end)
    if not ok or not inMats or #inMats == 0 then
        print("  ⚠️ 未找到材質輸入節點")
        goto continue
    end

    for _, inMatNode in ipairs(inMats) do
        local ok2, conn = pcall(function() return inMatNode:getConnectedNode(P_INPUT) end)
        if ok2 and conn then
            local cProps = conn:getProperties()
            if cProps.type == NT_STD_SURFACE then
                if convertMaterial(inMatNode, conn) then
                    totalConverted = totalConverted + 1
                end
            end
        end
    end

    ::continue::
end

print("\n========================================")
print("🟢 完成！共轉換 " .. totalConverted .. " 個材質")
print("========================================")
