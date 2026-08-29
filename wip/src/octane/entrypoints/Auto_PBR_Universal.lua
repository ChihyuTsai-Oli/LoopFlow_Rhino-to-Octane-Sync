-- ============================================================
-- Script Name  : Auto_PBR_Universal
-- Version           : v1.0
-- Date              : 2026-04-28
-- Author            : Cursor + Claude Sonnet 4.6
-- Description : Automated PBR material builder for Octane Standalone.
--               - Select a texture folder to auto-create a Universal Material.
--               - Automatically detects and connects all PBR maps to matching pins.
--               - Creates two sets of Box Projection + 3D Transform:
--                 Group A: connects all non-Displacement maps.
--                 Group B: connects Displacement maps (not connected to material by default).
--               - Default mode 1 (Box Projection):
--                 Mode 1: tex → projection → BoxProjection → Transform
--                 Mode 2: tex → transform (UV) → Transform
--                 Use Auto_PBR_Switch_UV.lua to toggle.
--               - All nodes are packed into a Nodegraph with a Material output pin.
--               - Leftover temporary output nodes on the canvas are cleaned up after packing.
--               - Spawn position: selected node position + offset before execution.
--               - Remembers the last selected folder path.
-- ============================================================
-- @shortcut Ctrl + Shift + T
--
-- [Usage]
-- 1) Run this script in Octane Standalone, then select a texture folder to auto-build
--    and pack the material Nodegraph.
--
-- [Variable Notes]
-- - This script does not read `R2O_Path.txt` and does not affect the R2O sync workflow.
--
-- ★ Color Space Workflow Switch ★
--
-- To switch: change the CS_COLOR variable below (only one line to edit).
--
--   Available values:
--     0 = Non-color data
--     1 = sRGB
--     2 = Linear sRGB + legacy gamma
--     3 = ACES2065-1
--     4 = ACEScg (default; requires Octane Imager with ACES tone mapping enabled)
--
--   ACEScg workflow (default):
--     local CS_COLOR = 4
--
--   sRGB workflow:
--     local CS_COLOR = 1
--
-- Non-color data (Roughness, Normal, Bump, Displacement, etc.) is always 0.
--
-- ★ Node Position Guide ★
--
-- Coordinate system (for node layout inside ng):
--   x controls horizontal (left/right): negative = left, positive = right
--   y controls vertical (up/down):      negative = up,   positive = down
--
-- Vertical layers top-to-bottom (edit variables starting with Y_):
--   Y_TRANSFORM : Transform nodes; more negative = higher
--   Y_BOXPROJ   : BoxProjection nodes; must be greater than Y_TRANSFORM (lower)
--   Y_TEX       : ImageTexture nodes; must be greater than Y_BOXPROJ (lower)
--   Y_DISP      : Displacement nodes (Group B); must be greater than Y_TEX (lower)
--   Y_MAT       : Material node; fixed at 0
--   Y_OUT       : Output node, relative y inside ng
--                 0 = same height as ng icon, positive = downward (default 50)
--
-- Horizontal spacing (edit variables starting with X_):
--   X_STEP      : Horizontal gap between each texture node (default 220)
--   X_GAP       : Extra gap between Group A and Group B (default 300)
--   X_CS_OFFSET : Horizontal offset of colorSpace node relative to ImageTexture
--                 negative = left, positive = right (default -100)
--
-- colorSpace node vertical offset (relative to ImageTexture):
--   Y_CS_OFFSET : negative = up, positive = down (default -50)
--
-- ★ Spawn Position ★
-- Select any node on the canvas before running; the new ng will be placed at:
--   selected node position + SPAWN_OFFSET
-- If nothing is selected, origin (0, 0) + SPAWN_OFFSET is used.
--
-- Offset settings:
--   SPAWN_OFFSET_X : horizontal offset, positive = right (default 200)
--   SPAWN_OFFSET_Y : vertical offset,   positive = down  (default 0)
--
-- ============================================================

local PIN_MAP = {
    { "albedo",       false, {"col","color","colour","albedo","diffuse","basecolor","base_color"} },
    { "specular",     false, {"refl","reflection","specular","spec"} },
    { "roughness",    true,  {"roughness","rough","gloss","glossy","glossiness"} },
    { "metallic",     true,  {"metallic","metal"} },
    { "bump",         true,  {"bump"} },
    { "normal",       true,  {"nrm","normal","nor"} },
    { "displacement", true,  {"disp","displacement"} },
    { "opacity",      true,  {"opacity","alpha","mask"} },
    { "emission",     false, {"emission","emissive","emit"} },
    { "sheen",        false, {"sheen"} },
}

-- ★ Color space setting (change only CS_COLOR to switch workflow) ★
local CS_COLOR    = 4  -- ACEScg (default)
-- local CS_COLOR = 1  -- sRGB (use this line to switch)
local CS_NONCOLOR = 0  -- Non-color data (fixed)

-- Vertical layers (y values, top-to-bottom; more negative = higher)
local Y_TRANSFORM = -300
local Y_BOXPROJ   = -250
local Y_TEX       = -100
local Y_DISP      =  -50
local Y_MAT       =    0
local Y_OUT       =   50  -- output positioned 50 units below ng icon

-- Horizontal spacing (x values)
local X_STEP      =  220  -- Horizontal gap between texture nodes
local X_GAP       =  300  -- Extra gap between Group A and Group B
local X_CS_OFFSET = -100  -- colorSpace node horizontal offset (negative=left, positive=right)

-- colorSpace node vertical offset (relative to ImageTexture)
local Y_CS_OFFSET =  -50  -- negative = up, positive = down

-- ★ Spawn position offset ★
-- ng is placed at "selected node position + the offsets below"
-- If nothing is selected, (0,0) + offsets is used
local SPAWN_OFFSET_X =  200  -- horizontal offset, positive = right (default 200)
local SPAWN_OFFSET_Y =    0  -- vertical offset,   positive = down  (default 0)

------------------------------------------------------------
local LAST_PATH_FILE = (os.getenv("TEMP") or "/tmp") .. "/octane_pbr_lastpath.txt"

local function savePath(path)
    local f = io.open(LAST_PATH_FILE, "w")
    if f then f:write(path) f:close() end
end

local function loadPath()
    local f = io.open(LAST_PATH_FILE, "r")
    if f then local p = f:read("*l") f:close() return p or "" end
    return ""
end

local function getFilename(path)
    return path:match("([^/\\]+)$") or path
end

local function matchKeywords(filename, keywords)
    local lower = filename:lower()
    for _, kw in ipairs(keywords) do
        if lower:find(kw, 1, true) then return true end
    end
    return false
end

local function listImages(folder)
    local files = {}
    local exts = {".png",".jpg",".jpeg",".tga",".exr",".tif",".tiff"}
    local isWin = package.config:sub(1,1) == "\\"
    local cmd = isWin
        and ('dir /b "' .. folder .. '" 2>nul')
        or  ('ls "' .. folder .. '" 2>/dev/null')
    local handle = io.popen(cmd)
    if not handle then return files end
    for line in handle:lines() do
        local lower = line:lower()
        for _, ext in ipairs(exts) do
            if lower:sub(-#ext) == ext then
                local sep = isWin and "\\" or "/"
                table.insert(files, folder .. sep .. line)
                break
            end
        end
    end
    handle:close()
    return files
end

local function createCSNode(val, pinName, xPos, yPos)
    local cs = octane.node.create{
        type     = octane.NT_OCIO_COLOR_SPACE,
        name     = "cs_" .. pinName,
        position = {xPos + X_CS_OFFSET, yPos + Y_CS_OFFSET},
    }
    cs:setAttribute(406, val)
    cs:evaluate()
    return cs
end

------------------------------------------------------------
-- Step 1: Determine spawn position
------------------------------------------------------------
local spawnX, spawnY = SPAWN_OFFSET_X, SPAWN_OFFSET_Y
local selBefore = octane.project.getSelection()
if #selBefore > 0 then
    local sp = selBefore[1]:getProperties()
    if type(sp.position) == "table" then
        spawnX = (sp.position[1] or 0) + SPAWN_OFFSET_X
        spawnY = (sp.position[2] or 0) + SPAWN_OFFSET_Y
    end
    print("[INFO] Reference node: " .. selBefore[1]:getProperties().name
        .. " -> ng spawn position: (" .. spawnX .. ", " .. spawnY .. ")")
else
    print("[INFO] No node selected -> ng spawn position: (" .. spawnX .. ", " .. spawnY .. ")")
end

------------------------------------------------------------
-- Step 2: FILE_DIALOG
------------------------------------------------------------
local lastPath = loadPath()

local dlg = octane.gui.showDialog({
    type            = octane.gui.dialogType.FILE_DIALOG,
    title           = "Select PBR Texture Folder",
    browseDirectory = true,
    save            = false,
    path            = lastPath,
})

if not dlg or not dlg.result or dlg.result == "" then
    print("[INFO] Cancelled")
    return
end

local folder  = dlg.result

savePath(folder)

-- Derive matName from the common prefix of image filenames in the folder
local function getCommonPrefix(files)
    if #files == 0 then return "Auto_PBR_Universal" end

    -- Get all basenames without extension
    local names = {}
    for _, fp in ipairs(files) do
        local basename = fp:match("([^/\\]+)$") or fp
        local noext = basename:match("(.+)%..+$") or basename
        table.insert(names, noext)
    end

    if #names == 1 then
        -- Single file: strip the last underscore/hyphen and everything after it
        local stripped = names[1]:match("^(.-)[-_][^-_]+$") or names[1]
        return stripped ~= "" and stripped or names[1]
    end

    -- Multiple files: find common prefix character by character
    local prefix = names[1]
    for i = 2, #names do
        local n = names[i]
        local len = math.min(#prefix, #n)
        local commonLen = 0
        for j = 1, len do
            if prefix:sub(j,j) == n:sub(j,j) then
                commonLen = j
            else
                break
            end
        end
        prefix = prefix:sub(1, commonLen)
        if prefix == "" then break end
    end

    -- Strip trailing underscores or hyphens
    prefix = prefix:match("^(.-)[-_]+$") or prefix
    return prefix ~= "" and prefix or "Auto_PBR_Universal"
end

-- Scan once for the prefix; listImages will scan again below
local tempFiles = listImages(folder)
local matName   = getCommonPrefix(tempFiles)

local csName = (CS_COLOR == 4) and "ACEScg"
            or (CS_COLOR == 1) and "sRGB"
            or (CS_COLOR == 3) and "ACES2065-1"
            or (CS_COLOR == 2) and "Linear sRGB + legacy"
            or "Custom(" .. CS_COLOR .. ")"

print("========================================")
print(" PBR Auto-Setup v2.8")
    print(" Folder: " .. folder)
    print(" Material: " .. matName)
    print(" Color workflow: " .. csName)
print("========================================")

local texFiles = listImages(folder)
if #texFiles == 0 then
    print("[ERROR] No texture files found")
    return
end
print("[INFO] Found " .. #texFiles .. " file(s)")

------------------------------------------------------------
-- Step 3: Pre-scan and group textures
------------------------------------------------------------
local groupA   = {}
local groupB   = {}
local usedScan = {}

for _, mapping in ipairs(PIN_MAP) do
    local pinName, isLinear, keywords = mapping[1], mapping[2], mapping[3]
    for _, filepath in ipairs(texFiles) do
        local filename = getFilename(filepath)
        if not usedScan[filepath] and matchKeywords(filename, keywords) then
            local entry = {
                pinName  = pinName,
                isLinear = isLinear,
                filepath = filepath,
                filename = filename,
            }
            if pinName == "displacement" then
                table.insert(groupB, entry)
            else
                table.insert(groupA, entry)
            end
            usedScan[filepath] = true
            break
        end
    end
end

print("[INFO] Group A (standard maps): " .. #groupA)
print("[INFO] Group B (Displacement): " .. #groupB)

local groupA_x_start = 0
local groupA_x_end   = math.max(0, #groupA - 1) * X_STEP
local groupA_x_mid   = math.floor(groupA_x_end / 2)

local groupB_x_start = groupA_x_end + X_GAP
local groupB_x_end   = groupB_x_start + math.max(0, #groupB - 1) * X_STEP
local groupB_x_mid   = math.floor((groupB_x_start + groupB_x_end) / 2)

local mat_x = math.floor((groupA_x_start + groupB_x_end) / 2)

local allNodes = {}

------------------------------------------------------------
-- Step 4: Create Material
------------------------------------------------------------
local matNode = octane.node.create{
    type     = octane.NT_MAT_UNIVERSAL,
    name     = matName,
    position = {mat_x, Y_MAT},
}
if not matNode then
    print("[ERROR] Failed to create material node")
    return
end
table.insert(allNodes, matNode)
print("[OK] Material created: " .. matName)

------------------------------------------------------------
-- Step 5: Create Output connector
-- NT_OUT_MATERIAL is the ng output connector
-- Positioned temporarily at (0, Y_OUT); adjusted below ng after packing
------------------------------------------------------------
local OUT_TEMP_NAME = "__auto_pbr_output_temp__"

local outNode = octane.node.create{
    type     = octane.NT_OUT_MATERIAL,
    name     = OUT_TEMP_NAME,
    position = {mat_x, Y_MAT + Y_OUT},
}
outNode:connectTo("input", matNode)
outNode:evaluate()
table.insert(allNodes, outNode)
print("[OK] Output connector created")

------------------------------------------------------------
-- Step 6: Group A — Transform + BoxProjection
------------------------------------------------------------
local transformA = octane.node.create{
    type     = octane.NT_TRANSFORM_3D,
    name     = "Transform_A",
    position = {groupA_x_mid, Y_TRANSFORM},
}
local boxProjA = octane.node.create{
    type     = octane.NT_PROJ_BOX,
    name     = "BoxProjection_A",
    position = {groupA_x_mid, Y_BOXPROJ},
}
boxProjA:connectTo("transform", transformA)
boxProjA:evaluate()
transformA:evaluate()
table.insert(allNodes, transformA)
table.insert(allNodes, boxProjA)
print("[OK] Group A: BoxProjection_A + Transform_A")

------------------------------------------------------------
-- Step 7: Group B — Transform + BoxProjection
------------------------------------------------------------
local transformB, boxProjB
if #groupB > 0 then
    transformB = octane.node.create{
        type     = octane.NT_TRANSFORM_3D,
        name     = "Transform_B",
        position = {groupB_x_mid, Y_TRANSFORM},
    }
    boxProjB = octane.node.create{
        type     = octane.NT_PROJ_BOX,
        name     = "BoxProjection_B",
        position = {groupB_x_mid, Y_BOXPROJ},
    }
    boxProjB:connectTo("transform", transformB)
    boxProjB:evaluate()
    transformB:evaluate()
    table.insert(allNodes, transformB)
    table.insert(allNodes, boxProjB)
    print("[OK] Group B: BoxProjection_B + Transform_B")
end

------------------------------------------------------------
-- Step 8: Group A — Connect ImageTextures
------------------------------------------------------------
local connected = 0

for i, m in ipairs(groupA) do
    local xPos = groupA_x_start + (i - 1) * X_STEP

    local ok, err = pcall(function()
        local csVal  = m.isLinear and CS_NONCOLOR or CS_COLOR
        local csNode = createCSNode(csVal, m.pinName, xPos, Y_TEX)
        table.insert(allNodes, csNode)

        local texNode = octane.node.create{
            type     = octane.NT_TEX_IMAGE,
            name     = m.filename:match("(.+)%..+$") or m.filename,
            position = {xPos, Y_TEX},
        }
        texNode:setAttribute(octane.A_FILENAME, m.filepath)
        texNode:connectTo("colorSpace", csNode)
        texNode:connectTo("projection", boxProjA)
        texNode:connectTo("transform",  transformA)
        texNode:evaluate()
        matNode:connectTo(m.pinName, texNode)
        table.insert(allNodes, texNode)
    end)

    if ok then
        local csLabel = m.isLinear and "non-color" or csName
        print("[OK] A | " .. m.pinName .. " <- " .. m.filename .. " [" .. csLabel .. "]")
        connected = connected + 1
    else
        print("[WARN] A | " .. m.pinName .. " failed: " .. tostring(err))
    end
end

------------------------------------------------------------
-- Step 9: Group B — ImageTexture + Displacement
------------------------------------------------------------
if #groupB > 0 then
    for i, m in ipairs(groupB) do
        local xPos = groupB_x_start + (i - 1) * X_STEP

        local ok, err = pcall(function()
            local csNode = createCSNode(CS_NONCOLOR, m.pinName, xPos, Y_TEX)
            table.insert(allNodes, csNode)

            local texNode = octane.node.create{
                type     = octane.NT_TEX_IMAGE,
                name     = m.filename:match("(.+)%..+$") or m.filename,
                position = {xPos, Y_TEX},
            }
            texNode:setAttribute(octane.A_FILENAME, m.filepath)
            texNode:connectTo("colorSpace", csNode)
            texNode:connectTo("projection", boxProjB)
            texNode:connectTo("transform",  transformB)
            texNode:evaluate()
            table.insert(allNodes, texNode)

            -- Create Displacement node without connecting to matNode (connect manually)
            local dispNode = octane.node.create{
                type     = octane.NT_DISPLACEMENT,
                name     = "Displacement",
                position = {xPos, Y_DISP},
            }
            dispNode:connectTo("texture", texNode)
            dispNode:evaluate()
            table.insert(allNodes, dispNode)
        end)

        if ok then
            print("[OK] B | displacement created (not connected to material) <- " .. m.filename)
            connected = connected + 1
        else
            print("[WARN] B | displacement failed: " .. tostring(err))
        end
    end
end

------------------------------------------------------------
-- Step 10: Pack into Nodegraph, rename, set position
-- output node is already in allNodes; repositioned below ng after packing
------------------------------------------------------------
local scene = octane.project.getSceneGraph()
local ok_grp, ng = pcall(function()
    return scene:group(allNodes)
end)

if ok_grp and ng then
    ng:updateProperties({
        name     = matName,
        position = {spawnX, spawnY},
    })

    -- output is inside ng; move it directly below the material node
    local matInside = ng:findNodes(octane.NT_MAT_UNIVERSAL)
    local outNodes  = ng:findNodes(octane.NT_OUT_MATERIAL)

    if #matInside > 0 and #outNodes > 0 then
        local matPos = matInside[1]:getProperties().position
        outNodes[1]:updateProperties({
            name     = "output",
            position = {matPos[1], matPos[2] + Y_OUT},
        })
    end

    print("[OK] Nodegraph: " .. matName
        .. " created at (" .. spawnX .. ", " .. spawnY .. ")")

    -- Step 11: Clean up leftover temporary output nodes on the canvas
    local residual = scene:findItemsByName(OUT_TEMP_NAME)
    local cleaned = 0
    for _, item in ipairs(residual) do
        item:destroy()
        cleaned = cleaned + 1
    end
    if cleaned > 0 then
        print("[OK] Cleaned up " .. cleaned .. " leftover temporary output node(s) from canvas")
    end
else
    print("[WARN] Packing failed: " .. tostring(ng))
end

print("\nDone! Connected " .. connected .. " pin(s)")
print("Color workflow: " .. csName)
print("UV mode: Mode 1 (Box Projection) — default")
print("Displacement: created; connect to material manually")
print("Output connector (output) can be connected directly to Geo")
print("========================================")