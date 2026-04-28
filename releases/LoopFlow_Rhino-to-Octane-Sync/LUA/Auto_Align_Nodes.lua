-- ============================================================
-- Script Name  : Auto_Align_Nodes
-- Version           : v1.0
-- Date              : 2026-04-28
-- Author            : Cursor + Claude Sonnet 4.6
-- Description : Aligns selected nodes to a common horizontal baseline (same Y),
--               then arranges them left-to-right by X position without overlap.
--               A dialog appears before execution to set the gap between nodes.
--               A negative gap causes nodes to overlap.
--               Usage: select target nodes then run.
-- ============================================================
-- @shortcut alt+a
--
-- [Usage]
-- 1) Select at least 2 nodes in Octane Standalone, then run this script.
--
-- [Variable Notes]
-- - This script does not read `R2O_Path.txt` and does not affect the R2O sync workflow.

-- ── Defaults ────────────────────────────────────────────────
local ALIGN_Y_MODE  = "min"
local DEFAULT_WIDTH = 160
-- ────────────────────────────────────────────────────────────

print("========================================")
print(" Auto Align Nodes v1.0")
print("========================================")

-- ── GUI: gap input ─────────────────────────────────────────
local HORIZONTAL_GAP = nil

local editor = octane.gui.create{
    type   = octane.gui.componentType.TEXT_EDITOR,
    text   = "-10",
    width  = 260,
    height = 22,
}

local label = octane.gui.create{
    type   = octane.gui.componentType.LABEL,
    text   = "Gap between nodes, px  (e.g. -10, 0, 20):",
    width  = 260,
    height = 18,
}

local win

local okBtn = octane.gui.create{
    type     = octane.gui.componentType.BUTTON,
    text     = "OK",
    width    = 80,
    height   = 24,
    callback = function()
        local v = tonumber(editor:getProperties().text)
        if not v then
            octane.gui.showDialog{
                type  = octane.gui.dialogType.ERROR_DIALOG,
                title = "Invalid input",
                text  = "Please enter a number (e.g. 20 or -10).",
            }
            return
        end
        HORIZONTAL_GAP = v
        win:closeWindow()
    end,
}

local cancelBtn = octane.gui.create{
    type     = octane.gui.componentType.BUTTON,
    text     = "Cancel",
    width    = 80,
    height   = 24,
    callback = function()
        win:closeWindow()
    end,
}

local btnRow = octane.gui.create{
    type     = octane.gui.componentType.GROUP,
    rows     = 1,
    cols     = 2,
    children = { okBtn, cancelBtn },
    border   = false,
    padding  = { 4 },
    inset    = { 0 },
}

local layout = octane.gui.create{
    type     = octane.gui.componentType.GROUP,
    rows     = 3,
    cols     = 1,
    children = { label, editor, btnRow },
    border   = false,
    padding  = { 6 },
    inset    = { 10 },
}

win = octane.gui.create{
    type     = octane.gui.componentType.WINDOW,
    text     = "Auto Align Nodes",
    width    = layout:getProperties().width,
    height   = layout:getProperties().height,
    children = { layout },
}

win:showWindow()

if not HORIZONTAL_GAP then
    print("[INFO] Cancelled.")
    return
end

print("[INFO] Gap: " .. HORIZONTAL_GAP .. " px")

-- ── Node width map ─────────────────────────────────────────
local function safeMap(entries)
    local t = {}
    for _, entry in ipairs(entries) do
        local key, width = entry[1], entry[2]
        if type(key) == "number" then
            t[key] = width
        else
            local ok, val = pcall(function() return octane[key] end)
            if ok and val ~= nil then t[val] = width end
        end
    end
    return t
end

local NODE_WIDTH_MAP = safeMap({
    { "NT_RENDERTARGET",         160 },
    { "NT_CAM_THINLENS",         160 },
    { "NT_CAM_PANORAMIC",        160 },
    { "NT_CAM_BAKING",           160 },
    { "NT_CAM_OSL",              200 },
    { "NT_KERN_PATHTRACING",     160 },
    { "NT_KERN_DIRECTLIGHTING",  160 },
    { "NT_KERN_PMC",             160 },
    { "NT_LIGHTAOV",             130 },
    { 205,                       130 },
    { "NT_SPOTLIGHT",            130 },
    { "NT_AREALIGHT",            130 },
    { "NT_MESHLIGHT",            130 },
    { "NT_MAT_DIFFUSE",          160 },
    { "NT_MAT_GLOSSY",           160 },
    { "NT_MAT_SPECULAR",         160 },
    { "NT_MAT_MIX",              160 },
    { "NT_MAT_PORTAL",           160 },
    { "NT_MAT_TOON",             160 },
    { "NT_MAT_METALLIC",         160 },
    { "NT_MAT_UNIVERSAL",        200 },
    { "NT_MAT_LAYERED",          200 },
    { "NT_MAT_COMPOSITE",        200 },
    { "NT_MAT_HAIRMATERIAL",     160 },
    { "NT_MAT_SHADOWCATCHER",    160 },
    { "NT_TEX_RGB",              130 },
    { "NT_TEX_FLOAT",            130 },
    { "NT_TEX_IMAGE",            160 },
    { "NT_TEX_ALPHAIMAGE",       160 },
    { "NT_TEX_FLOATIMAGE",       160 },
    { "NT_TEX_GAUSSIAN",         130 },
    { "NT_TEX_MARBLE",           130 },
    { "NT_TEX_TURBULENCE",       130 },
    { "NT_TEX_CHECKS",           130 },
    { "NT_TEX_DIRT",             130 },
    { "NT_TEX_GRADIENT",         160 },
    { "NT_TEX_RANDOM_COLOR",     130 },
    { "NT_TEX_POLYGON_SIDE",     130 },
    { "NT_TEX_NOISE",            130 },
    { "NT_TEX_CURVATURE",        130 },
    { "NT_TEX_MIX",              130 },
    { "NT_TEX_MULTIPLY",         130 },
    { "NT_TEX_ADD",              130 },
    { "NT_TEX_SUBTRACT",         130 },
    { "NT_TEX_COMPARE",          130 },
    { "NT_TEX_CLAMP",            130 },
    { "NT_TEX_COSINE",           130 },
    { "NT_TEX_INVERT",           130 },
    { "NT_TEX_FALLOFF",          130 },
    { "NT_TEX_COLORCORRECTION",  160 },
    { "NT_TEX_TRIPLANAR",        160 },
    { "NT_TEX_OSL",              200 },
    { "NT_TEX_BAKING",           160 },
    { "NT_TEX_DISPLACEMENT",     130 },
    { "NT_TRANSFORM_VALUE",      160 },
    { "NT_TRANSFORM_ROTATION",   160 },
    { "NT_TRANSFORM_SCALE",      160 },
    { "NT_PROJ_BOX",             130 },
    { "NT_PROJ_CYLINDRICAL",     130 },
    { "NT_PROJ_PERSPECTIVE",     130 },
    { "NT_PROJ_SPHERICAL",       130 },
    { "NT_PROJ_TRIPLANAR",       130 },
    { "NT_PROJ_UVW",             130 },
    { "NT_PROJ_OSL",             200 },
    { "NT_MED_ABSORPTION",       160 },
    { "NT_MED_SCATTERING",       160 },
    { "NT_MED_VOLUME",           160 },
    { "NT_MED_RANDOMWALK",       160 },
    { "NT_GEO_GROUP",            160 },
    { "NT_GEO_MESH",             160 },
    { "NT_GEO_PLACEMENT",        160 },
    { "NT_GEO_SCATTER",          200 },
    { "NT_GEO_VOLUME",           160 },
    { "NT_ENV_TEXTURE",          160 },
    { "NT_ENV_DAYLIGHT",         160 },
    { "NT_ENV_PLANETARY",        160 },
    { "NT_IMAGER_CAMERA",        200 },
    { "NT_POSTPROCESS",          160 },
    { "NT_RENDERAOV",            160 },
    { "NT_RENDERAOVGROUP",       200 },
    { 179,                       200 },
})

-- ── Validate selection ─────────────────────────────────────
local selection = octane.project.getSelection()

if not selection or #selection == 0 then
    print("[ERROR] No nodes selected.")
    octane.gui.showDialog{
        type  = octane.gui.dialogType.ERROR_DIALOG,
        title = "Auto Align Nodes",
        text  = "No nodes selected.\nPlease select nodes in the Node Graph first.",
    }
    return
end

if #selection < 2 then
    print("[ERROR] Please select at least 2 nodes.")
    octane.gui.showDialog{
        type  = octane.gui.dialogType.ERROR_DIALOG,
        title = "Auto Align Nodes",
        text  = "Please select at least 2 nodes.",
    }
    return
end

print("[INFO] Processing " .. #selection .. " nodes")

-- ── Helpers ────────────────────────────────────────────────
local function getPos(item)
    local p = item.position
    return p[1], p[2]
end

local function getNodeWidth(item)
    local ok, props = pcall(function() return item:getProperties() end)
    if ok and props and props.type then
        local w = NODE_WIDTH_MAP[props.type]
        if w then return w end
        print(string.format("  [unmapped] %s (type=%d) -> add { %d, width } to NODE_WIDTH_MAP",
            props.name or "?", props.type, props.type))
    end
    local ok2, sz = pcall(function() return item.size end)
    if ok2 and sz and type(sz) == "table" and sz[1] and sz[1] > 10 then
        return sz[1]
    end
    return DEFAULT_WIDTH
end

local function computeTargetY()
    if ALIGN_Y_MODE == "min" then
        local v = math.huge
        for _, item in ipairs(selection) do
            local _, y = getPos(item)
            if y < v then v = y end
        end
        return v
    elseif ALIGN_Y_MODE == "max" then
        local v = -math.huge
        for _, item in ipairs(selection) do
            local _, y = getPos(item)
            if y > v then v = y end
        end
        return v
    else
        local sum = 0
        for _, item in ipairs(selection) do
            local _, y = getPos(item)
            sum = sum + y
        end
        return sum / #selection
    end
end

-- ── Sort & align ───────────────────────────────────────────
table.sort(selection, function(a, b)
    return getPos(a) < getPos(b)
end)

local target_y    = computeTargetY()
local start_x, _ = getPos(selection[1])
local cursor_x   = start_x

for _, item in ipairs(selection) do
    local w = getNodeWidth(item)
    item.position = { cursor_x, target_y }
    cursor_x = cursor_x + w + HORIZONTAL_GAP
end

print(string.format("[OK] %d nodes aligned  |  Y=%.0f  |  gap=%d px",
    #selection, target_y, HORIZONTAL_GAP))
print("========================================")