-- ============================================================
-- 腳本名稱 : Auto_PBR_Universal
-- 版本     : v2.0
-- 日期     : 2026-04-14
-- 作者     : Cursor + GPT-5.2
-- 功能說明 : Octane Standalone 自動 PBR 材質建立工具
--            - 選擇貼圖資料夾後自動建立 Universal Material
--            - 自動偵測並連接所有 PBR 貼圖到對應 pin
--            - 建立兩組 Box Projection + 3D Transform
--              A組：連接所有非 Displacement 貼圖
--              B組：連接 Displacement 貼圖（預設不接入材質）
--            - 預設模式1（Box Projection）
--              模式1：tex → projection → BoxProjection → Transform
--              模式2：tex → transform（UV）→ Transform
--              切換請使用 Auto_PBR_Switch_UV.lua
--            - 所有節點打包進 Nodegraph，具備 Material 輸出端
--            - 打包後自動清除畫布上殘留的 output 節點
--            - 生成位置：以執行前選取的節點位置加上偏移為起點
--            - 記憶上次選擇的資料夾路徑
-- ============================================================
-- @shortcut Ctrl + Shift + T
--
-- 【使用說明】
-- 1) 在 Octane Standalone 執行本腳本，選取貼圖資料夾後自動建立並打包材質 Nodegraph。
--
-- 【變數連動注意事項】
-- - 本腳本不讀取 `R2O_Path.txt`，不影響 R2O 同步流程。
--
-- ★ 色彩空間工作流切換 ★
--
-- 切換方式：修改下方 CS_COLOR 變數（只需改一行）
--
--   可用值：
--     0 = Non-color data
--     1 = sRGB
--     2 = Linear sRGB + legacy gamma
--     3 = ACES2065-1
--     4 = ACEScg（預設，需搭配 Octane Imager 開啟 ACES tone mapping）
--
--   ACEScg 工作流（預設）：
--     local CS_COLOR = 4
--
--   sRGB 工作流：
--     local CS_COLOR = 1
--
-- Non-color data（Roughness、Normal、Bump、Displacement 等）固定為 0
--
-- ★ 節點位置調整說明 ★
--
-- 座標系（ng 內部節點排列用）：
--   x 控制水平（左右），x 負 = 左，x 正 = 右
--   y 控制垂直（上下），y 負 = 上，y 正 = 下
--
-- 垂直層次由上而下（修改 Y_ 開頭的變數）：
--   Y_TRANSFORM : Transform 節點，數值越負越上方
--   Y_BOXPROJ   : BoxProjection 節點，應比 Y_TRANSFORM 大（更下方）
--   Y_TEX       : ImageTexture 節點，應比 Y_BOXPROJ 大（更下方）
--   Y_DISP      : Displacement 節點（B組），應比 Y_TEX 大（更下方）
--   Y_MAT       : Material 節點，固定為 0
--   Y_OUT       : Output 節點，ng 內部相對座標 y 值
--                 0 = ng 圖示同高，正值 = 往下（預設 50）
--
-- 水平間距（修改 X_ 開頭的變數）：
--   X_STEP      : 每個貼圖節點之間的水平間距（預設 220）
--   X_GAP       : A 組與 B 組之間的額外間距（預設 300）
--   X_CS_OFFSET : colorSpace 節點相對於 ImageTexture 的水平偏移
--                 負值 = 往左，正值 = 往右（預設 -100）
--
-- colorSpace 節點垂直偏移（相對於 ImageTexture）：
--   Y_CS_OFFSET : 負值 = 往上，正值 = 往下（預設 -50）
--
-- ★ 生成位置說明 ★
-- 執行前選取畫布上任一節點，新的 ng 本身會生成在：
--   選取節點位置 + SPAWN_OFFSET
-- 若無選取，則以座標 (0, 0) + SPAWN_OFFSET 為起點
--
-- 偏移設定：
--   SPAWN_OFFSET_X : 水平偏移，正值 = 往右（預設 200）
--   SPAWN_OFFSET_Y : 垂直偏移，正值 = 往下（預設 0）
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

-- ★ 色彩空間設定（切換工作流只需改 CS_COLOR）★
local CS_COLOR    = 4  -- ACEScg（預設）
-- local CS_COLOR = 1  -- sRGB（改用這行切換）
local CS_NONCOLOR = 0  -- Non-color data（固定不變）

-- 垂直層次（y 值，由上而下，數值越負越上方）
local Y_TRANSFORM = -300
local Y_BOXPROJ   = -250
local Y_TEX       = -100
local Y_DISP      =  -50
local Y_MAT       =    0
local Y_OUT       =   50  -- output 在 ng 圖示正下方 50 單位

-- 水平間距（x 值）
local X_STEP      =  220  -- 每個貼圖節點的水平間距
local X_GAP       =  300  -- A/B 兩組之間的額外間距
local X_CS_OFFSET = -100  -- colorSpace 節點水平偏移（負=左，正=右）

-- colorSpace 節點垂直偏移（相對於 ImageTexture）
local Y_CS_OFFSET =  -50  -- 負值 = 往上，正值 = 往下

-- ★ 生成位置偏移 ★
-- ng 本身生成在「選取節點位置 + 以下偏移」
-- 無選取時以 (0,0) + 偏移為起點
local SPAWN_OFFSET_X =  200  -- 水平偏移，正值 = 往右（預設 200）
local SPAWN_OFFSET_Y =    0  -- 垂直偏移，正值 = 往下（預設 0）

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
-- Step 1: 取得生成位置
------------------------------------------------------------
local spawnX, spawnY = SPAWN_OFFSET_X, SPAWN_OFFSET_Y
local selBefore = octane.project.getSelection()
if #selBefore > 0 then
    local sp = selBefore[1]:getProperties()
    if type(sp.position) == "table" then
        spawnX = (sp.position[1] or 0) + SPAWN_OFFSET_X
        spawnY = (sp.position[2] or 0) + SPAWN_OFFSET_Y
    end
    print("[INFO] 參考節點: " .. selBefore[1]:getProperties().name
        .. " -> ng 生成位置: (" .. spawnX .. ", " .. spawnY .. ")")
else
    print("[INFO] 無選取節點 -> ng 生成位置: (" .. spawnX .. ", " .. spawnY .. ")")
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

-- 從資料夾內圖檔名稱取公共前綴作為 matName
local function getCommonPrefix(files)
    if #files == 0 then return "Auto_PBR_Universal" end

    -- 取得所有不含副檔名的檔名（basename only）
    local names = {}
    for _, fp in ipairs(files) do
        local basename = fp:match("([^/\\]+)$") or fp
        local noext = basename:match("(.+)%..+$") or basename
        table.insert(names, noext)
    end

    if #names == 1 then
        -- 只有一個檔案：移除最後一個底線/連字號及其後內容
        local stripped = names[1]:match("^(.-)[-_][^-_]+$") or names[1]
        return stripped ~= "" and stripped or names[1]
    end

    -- 多個檔案：逐字元找公共前綴
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

    -- 移除結尾的底線或連字號
    prefix = prefix:match("^(.-)[-_]+$") or prefix
    return prefix ~= "" and prefix or "Auto_PBR_Universal"
end

-- 先掃一次檔案以取前綴，之後 listImages 會再掃一次
local tempFiles = listImages(folder)
local matName   = getCommonPrefix(tempFiles)

local csName = (CS_COLOR == 4) and "ACEScg"
            or (CS_COLOR == 1) and "sRGB"
            or (CS_COLOR == 3) and "ACES2065-1"
            or (CS_COLOR == 2) and "Linear sRGB + legacy"
            or "Custom(" .. CS_COLOR .. ")"

print("========================================")
print(" PBR Auto-Setup v2.8")
print(" 資料夾: " .. folder)
print(" 材質名稱: " .. matName)
print(" 色彩工作流: " .. csName)
print("========================================")

local texFiles = listImages(folder)
if #texFiles == 0 then
    print("[ERROR] 找不到貼圖")
    return
end
print("[INFO] 找到 " .. #texFiles .. " 個檔案")

------------------------------------------------------------
-- Step 3: 預掃描分組
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

print("[INFO] A 組（一般貼圖）: " .. #groupA)
print("[INFO] B 組（Displacement）: " .. #groupB)

local groupA_x_start = 0
local groupA_x_end   = math.max(0, #groupA - 1) * X_STEP
local groupA_x_mid   = math.floor(groupA_x_end / 2)

local groupB_x_start = groupA_x_end + X_GAP
local groupB_x_end   = groupB_x_start + math.max(0, #groupB - 1) * X_STEP
local groupB_x_mid   = math.floor((groupB_x_start + groupB_x_end) / 2)

local mat_x = math.floor((groupA_x_start + groupB_x_end) / 2)

local allNodes = {}

------------------------------------------------------------
-- Step 4: 建立 Material
------------------------------------------------------------
local matNode = octane.node.create{
    type     = octane.NT_MAT_UNIVERSAL,
    name     = matName,
    position = {mat_x, Y_MAT},
}
if not matNode then
    print("[ERROR] 材質節點建立失敗")
    return
end
table.insert(allNodes, matNode)
print("[OK] 建立材質: " .. matName)

------------------------------------------------------------
-- Step 5: 建立 Output 接頭
-- NT_OUT_MATERIAL 就是 ng 的輸出接頭
-- 位置暫設 (0, Y_OUT)，打包後會調整到 ng 正下方
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
print("[OK] 建立 Output 接頭")

------------------------------------------------------------
-- Step 6: A 組 Transform + BoxProjection
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
print("[OK] A 組: BoxProjection_A + Transform_A")

------------------------------------------------------------
-- Step 7: B 組 Transform + BoxProjection
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
    print("[OK] B 組: BoxProjection_B + Transform_B")
end

------------------------------------------------------------
-- Step 8: A 組 ImageTexture 連接
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
        print("[WARN] A | " .. m.pinName .. " 失敗: " .. tostring(err))
    end
end

------------------------------------------------------------
-- Step 9: B 組 ImageTexture + Displacement
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

            -- Displacement 建立，不接入 matNode（手動接）
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
            print("[OK] B | displacement 建立（未接入材質）<- " .. m.filename)
            connected = connected + 1
        else
            print("[WARN] B | displacement 失敗: " .. tostring(err))
        end
    end
end

------------------------------------------------------------
-- Step 10: 打包、改名、設定位置
-- output node 已在 allNodes 裡，打包後調整到 ng 正下方
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

    -- output 在 ng 內部，調整到材質正下方
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
        .. " 生成於 (" .. spawnX .. ", " .. spawnY .. ")")

    -- Step 11: 清除畫布上殘留的臨時 output 節點
    local residual = scene:findItemsByName(OUT_TEMP_NAME)
    local cleaned = 0
    for _, item in ipairs(residual) do
        item:destroy()
        cleaned = cleaned + 1
    end
    if cleaned > 0 then
        print("[OK] 已清除畫布上 " .. cleaned .. " 個殘留的臨時 output 節點")
    end
else
    print("[WARN] 打包失敗: " .. tostring(ng))
end

print("\n完成！共連接 " .. connected .. " 個 pin")
print("色彩工作流: " .. csName)
print("UV 模式: 模式1（Box Projection）預設")
print("Displacement: 已建立，請手動接入材質")
print("Output 接頭（output）可直接接給 Geo")
print("========================================")