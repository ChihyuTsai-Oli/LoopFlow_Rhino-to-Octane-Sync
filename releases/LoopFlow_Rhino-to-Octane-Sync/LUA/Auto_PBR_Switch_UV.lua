-- ============================================================
-- 腳本名稱 : Auto_PBR_Switch_UV
-- 版本     : v2.0
-- 日期     : 2026-04-14
-- 作者     : Cursor + GPT-5.2
-- 功能說明 : 切換選取 Nodegraph 的 UV 投影模式
--            模式1（Box Projection）：
--              tex → projection → BoxProjection_A → Transform_A
--              tex → transform  → Transform_A（保持接著）
--            模式2（UV Transform）：
--              tex → transform  → Transform_A
--              projection pin 斷開
--            使用方式（以下任一皆可）：
--              1. 選取目標 Nodegraph 後執行
--              2. 選取 ng 內部任一節點後執行
--              3. 選取畫布上的 Material 節點後執行
--              4. 在 ng 內部畫布中，無選取直接執行
-- ============================================================
-- @shortcut Ctrl + T
--
-- 【使用說明】
-- 1) 在 Octane Standalone 選取目標 Nodegraph（或其內部任一節點）後執行本腳本。
--
-- 【變數連動注意事項】
-- - 本腳本不讀取 `R2O_Path.txt`，不影響 R2O 同步流程。

------------------------------------------------------------
-- 輔助：從 Material 節點往上找所屬 Nodegraph
------------------------------------------------------------
local function findNgByMaterial(matNode)
    local scene = octane.project.getSceneGraph()
    local allGraphs = scene:findNodes(octane.NT_GRAPH_NODE)
    for _, g in ipairs(allGraphs) do
        local gProps = g:getProperties()
        if gProps.isGraph and gProps.name ~= "Scene" then
            local mats = g:findNodes(octane.NT_MAT_UNIVERSAL)
            for _, m in ipairs(mats) do
                if m == matNode then
                    return g
                end
            end
        end
    end
    return nil
end

------------------------------------------------------------
-- 主切換函式：傳入 ng，執行模式切換
------------------------------------------------------------
local function runSwitch(ng)
    local ngProps = ng:getProperties()
    print("========================================")
    print(" Switch UV Mode v1.5")
    print(" 目標 Nodegraph: " .. ngProps.name)
    print("========================================")

    -- Step 2: 找 ng 內的節點
    local texNodes   = ng:findNodes(octane.NT_TEX_IMAGE)
    local boxNodes   = ng:findNodes(octane.NT_PROJ_BOX)
    local xformNodes = ng:findNodes(octane.NT_TRANSFORM_3D)

    print("[INFO] 找到 " .. #texNodes .. " 個 ImageTexture")

    if #texNodes == 0 then
        print("[ERROR] 找不到 ImageTexture 節點")
        return
    end

    local boxProjA, transformA
    for _, b in ipairs(boxNodes) do
        if b:getProperties().name == "BoxProjection_A" then boxProjA = b end
    end
    for _, x in ipairs(xformNodes) do
        if x:getProperties().name == "Transform_A" then transformA = x end
    end

    if not boxProjA then
        print("[ERROR] 找不到 BoxProjection_A")
        return
    end
    if not transformA then
        print("[ERROR] 找不到 Transform_A")
        return
    end

    -- Step 3: 分類 A 組和 B 組
    local groupA_tex = {}
    local groupB_tex = {}

    for _, tex in ipairs(texNodes) do
        local projNode  = tex:getInputNode(141)
        local xformNode = tex:getInputNode(243)
        local isGroupB  = false

        if projNode then
            if projNode:getProperties().name == "BoxProjection_B" then
                isGroupB = true
            end
        end
        if not isGroupB and xformNode then
            if xformNode:getProperties().name == "Transform_B" then
                isGroupB = true
            end
        end

        if isGroupB then
            table.insert(groupB_tex, tex)
        else
            table.insert(groupA_tex, tex)
        end
    end

    print("[INFO] A 組: " .. #groupA_tex .. " 個，B 組: " .. #groupB_tex .. " 個")

    -- Step 4: 判斷目前模式
    local currentMode = 2
    for _, tex in ipairs(groupA_tex) do
        local projNode = tex:getInputNode(141)
        if projNode and projNode:getProperties().type == octane.NT_PROJ_BOX then
            currentMode = 1
            break
        end
    end

    local nextMode = (currentMode == 1) and 2 or 1
    print("[INFO] 目前模式: " .. currentMode
        .. "（" .. (currentMode == 1 and "Box Projection" or "UV Transform") .. "）")
    print("[INFO] 切換至模式: " .. nextMode
        .. "（" .. (nextMode == 1 and "Box Projection" or "UV Transform") .. "）")

    -- Step 5: 切換 A 組 tex node
    local switched = 0

    for _, tex in ipairs(groupA_tex) do
        local tprops = tex:getProperties()

        local ok, err = pcall(function()
            if nextMode == 2 then
                tex:disconnect("projection")
            else
                tex:connectTo("projection", boxProjA)
                local xformNode = tex:getInputNode(243)
                if not xformNode or xformNode:getProperties().name ~= "Transform_A" then
                    tex:connectTo("transform", transformA)
                end
            end
            tex:evaluate()
        end)

        if ok then
            print("[OK] " .. tprops.name .. " 切換完成")
            switched = switched + 1
        else
            print("[WARN] " .. tprops.name .. " 失敗: " .. tostring(err))
        end
    end

    for _, tex in ipairs(groupB_tex) do
        print("[SKIP] " .. tex:getProperties().name .. "（B 組，略過）")
    end

    ng:evaluate()

    print("\n完成！共切換 " .. switched .. " 個節點")
    print("目前模式: " .. nextMode
        .. "（" .. (nextMode == 1 and "Box Projection" or "UV Transform") .. "）")
    print("========================================")
end

------------------------------------------------------------
-- Step 1: 決定目標 ng
------------------------------------------------------------
local ng  = nil
local sel = octane.project.getSelection()

if #sel == 0 then
    -- 無選取：嘗試從目前開啟的畫布取得 ng
    local currentGraph = octane.project.getCurrentGraph
                         and octane.project.getCurrentGraph()
    if currentGraph then
        local cgProps = currentGraph:getProperties()
        if cgProps.isGraph and cgProps.name ~= "Scene" then
            ng = currentGraph
            print("[INFO] 無選取，使用目前開啟的 Nodegraph: " .. cgProps.name)
        end
    end
    if not ng then
        print("[ERROR] 請先選取一個 Nodegraph、其內部節點，或在 ng 畫布內執行")
        return
    end
else
    local item  = sel[1]
    local props = item:getProperties()

    if props.isGraph and props.name ~= "Scene" then
        -- 選取的是 Nodegraph 本身
        ng = item

    elseif props.isNode and props.type == octane.NT_MAT_UNIVERSAL then
        -- 選取的是 Material 節點 → 找所屬 ng
        local owner = props.graphOwner
        if owner then
            local ownerProps = owner:getProperties()
            if ownerProps.isGraph and ownerProps.name ~= "Scene" then
                ng = owner
                print("[INFO] 偵測到 Material 節點，自動切換至 Nodegraph: " .. ownerProps.name)
            end
        end
        if not ng then
            ng = findNgByMaterial(item)
            if ng then
                print("[INFO] 從 Material 找到 Nodegraph: " .. ng:getProperties().name)
            else
                print("[ERROR] 無法從 Material 節點找到所屬 Nodegraph")
                return
            end
        end

    elseif props.isNode then
        -- 選取的是 ng 內部其他節點
        local owner = props.graphOwner
        if owner then
            local ownerProps = owner:getProperties()
            if ownerProps.isGraph and ownerProps.name ~= "Scene" then
                ng = owner
                print("[INFO] 偵測到內部節點，自動切換至 Nodegraph: " .. ownerProps.name)
            else
                print("[ERROR] 選取的節點不在任何 Nodegraph 內")
                return
            end
        end

    else
        print("[ERROR] 無法識別選取的項目")
        return
    end
end

runSwitch(ng)
