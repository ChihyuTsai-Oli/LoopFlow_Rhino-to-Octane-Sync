-- ============================================================
-- Script Name  : Auto_PBR_Switch_UV
-- Version           : v1.0
-- Date              : 2026-04-28
-- Author            : Cursor + Claude Sonnet 4.6
-- Description : Toggles the UV projection mode of the selected Nodegraph.
--               Mode 1 (Box Projection):
--                 tex → projection → BoxProjection_A → Transform_A
--                 tex → transform  → Transform_A (remains connected)
--               Mode 2 (UV Transform):
--                 tex → transform  → Transform_A
--                 projection pin disconnected
--               Usage (any of the following works):
--                 1. Select the target Nodegraph, then run
--                 2. Select any node inside the ng, then run
--                 3. Select a Material node on the canvas, then run
--                 4. Run inside the ng canvas with nothing selected
-- ============================================================
-- @shortcut Ctrl + T
--
-- [Usage]
-- 1) Select the target Nodegraph (or any node inside it) in Octane Standalone, then run.
--
-- [Variable Notes]
-- - This script does not read `R2O_Path.txt` and does not affect the R2O sync workflow.

------------------------------------------------------------
-- Helper: find the parent Nodegraph from a Material node
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
-- Main switch function: receives ng and toggles UV mode
------------------------------------------------------------
local function runSwitch(ng)
    local ngProps = ng:getProperties()
    print("========================================")
    print(" Switch UV Mode v1.5")
    print(" Target Nodegraph: " .. ngProps.name)
    print("========================================")

    -- Step 2: Find nodes inside ng
    local texNodes   = ng:findNodes(octane.NT_TEX_IMAGE)
    local boxNodes   = ng:findNodes(octane.NT_PROJ_BOX)
    local xformNodes = ng:findNodes(octane.NT_TRANSFORM_3D)

    print("[INFO] Found " .. #texNodes .. " ImageTexture(s)")

    if #texNodes == 0 then
        print("[ERROR] No ImageTexture node found")
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
        print("[ERROR] BoxProjection_A not found")
        return
    end
    if not transformA then
        print("[ERROR] Transform_A not found")
        return
    end

    -- Step 3: Classify into Group A and Group B
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

    print("[INFO] Group A: " .. #groupA_tex .. ", Group B: " .. #groupB_tex)

    -- Step 4: Detect current mode
    local currentMode = 2
    for _, tex in ipairs(groupA_tex) do
        local projNode = tex:getInputNode(141)
        if projNode and projNode:getProperties().type == octane.NT_PROJ_BOX then
            currentMode = 1
            break
        end
    end

    local nextMode = (currentMode == 1) and 2 or 1
    print("[INFO] Current mode: " .. currentMode
        .. " (" .. (currentMode == 1 and "Box Projection" or "UV Transform") .. ")")
    print("[INFO] Switching to mode: " .. nextMode
        .. " (" .. (nextMode == 1 and "Box Projection" or "UV Transform") .. ")")

    -- Step 5: Switch Group A tex nodes
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
            print("[OK] " .. tprops.name .. " switched")
            switched = switched + 1
        else
            print("[WARN] " .. tprops.name .. " failed: " .. tostring(err))
        end
    end

    for _, tex in ipairs(groupB_tex) do
        print("[SKIP] " .. tex:getProperties().name .. " (Group B, skipped)")
    end

    ng:evaluate()

    print("\nDone! Switched " .. switched .. " node(s)")
    print("Current mode: " .. nextMode
        .. " (" .. (nextMode == 1 and "Box Projection" or "UV Transform") .. ")")
    print("========================================")
end

------------------------------------------------------------
-- Step 1: Determine target ng
------------------------------------------------------------
local ng  = nil
local sel = octane.project.getSelection()

if #sel == 0 then
    -- Nothing selected: try to get ng from the currently open canvas
    local currentGraph = octane.project.getCurrentGraph
                         and octane.project.getCurrentGraph()
    if currentGraph then
        local cgProps = currentGraph:getProperties()
        if cgProps.isGraph and cgProps.name ~= "Scene" then
            ng = currentGraph
            print("[INFO] Nothing selected, using currently open Nodegraph: " .. cgProps.name)
        end
    end
    if not ng then
        print("[ERROR] Please select a Nodegraph, a node inside one, or run inside the ng canvas")
        return
    end
else
    local item  = sel[1]
    local props = item:getProperties()

    if props.isGraph and props.name ~= "Scene" then
        -- Selected item is the Nodegraph itself
        ng = item

    elseif props.isNode and props.type == octane.NT_MAT_UNIVERSAL then
        -- Selected item is a Material node → find its parent ng
        local owner = props.graphOwner
        if owner then
            local ownerProps = owner:getProperties()
            if ownerProps.isGraph and ownerProps.name ~= "Scene" then
                ng = owner
                print("[INFO] Material node detected, switching to Nodegraph: " .. ownerProps.name)
            end
        end
        if not ng then
            ng = findNgByMaterial(item)
            if ng then
                print("[INFO] Found Nodegraph from Material: " .. ng:getProperties().name)
            else
                print("[ERROR] Unable to find Nodegraph from the Material node")
                return
            end
        end

    elseif props.isNode then
        -- Selected item is another node inside ng
        local owner = props.graphOwner
        if owner then
            local ownerProps = owner:getProperties()
            if ownerProps.isGraph and ownerProps.name ~= "Scene" then
                ng = owner
                print("[INFO] Internal node detected, switching to Nodegraph: " .. ownerProps.name)
            else
                print("[ERROR] The selected node is not inside any Nodegraph")
                return
            end
        end

    else
        print("[ERROR] Unable to identify the selected item")
        return
    end
end

runSwitch(ng)
