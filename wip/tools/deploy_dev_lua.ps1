#Requires -Version 5.1
# 把 Git 裡的 Octane 測試入口拷到測檔根 lua 資料夾（開發期可選）。
# 正式路徑：第一次跑 Rhino 指令後在「文件\LoopFlow\Rhino to OctaneRender Sync\lua」。
# 開發期目標：<LOOPFLOW_R2O_WORKFILES_ROOT>\_LoopFlow_Config\loopflow_R2O\lua
$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$SourceDir = Join-Path $RepoRoot "wip\src\octane\entrypoints"

$WorkRoot = [Environment]::GetEnvironmentVariable("LOOPFLOW_R2O_WORKFILES_ROOT", "User")
if (-not $WorkRoot) {
    $WorkRoot = $env:LOOPFLOW_R2O_WORKFILES_ROOT
}
if (-not $WorkRoot) {
    throw "LOOPFLOW_R2O_WORKFILES_ROOT is not set. See workspace 工作檔路徑.md"
}
if (-not (Test-Path -LiteralPath $WorkRoot)) {
    throw "Workfiles root not found: $WorkRoot"
}
if (-not (Test-Path -LiteralPath $SourceDir)) {
    throw "Source not found: $SourceDir"
}

$DestDir = Join-Path $WorkRoot "_LoopFlow_Config\loopflow_R2O\lua"
New-Item -ItemType Directory -Force -Path $DestDir | Out-Null

Get-ChildItem -LiteralPath $SourceDir -Filter "*.lua" | ForEach-Object {
    Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $DestDir $_.Name) -Force
    Write-Host ("Copied {0}" -f $_.Name)
}

$TxtName = "R2O_Shortcuts.txt"
$TxtSrc = Join-Path $SourceDir $TxtName
$TxtDst = Join-Path $DestDir $TxtName
if (Test-Path -LiteralPath $TxtSrc) {
    if (Test-Path -LiteralPath $TxtDst) {
        Write-Host ("Kept existing {0}" -f $TxtName)
    }
    else {
        Copy-Item -LiteralPath $TxtSrc -Destination $TxtDst -Force
        Write-Host ("Copied {0} (new)" -f $TxtName)
    }
}

Write-Host ""
Write-Host "Octane test Lua:"
Write-Host "  $DestDir"
Write-Host "Run __Setup_Shortcuts.lua after copy, then re-scan Octane scripts."
Write-Host "Do not overwrite 1.x AppData Lua."
