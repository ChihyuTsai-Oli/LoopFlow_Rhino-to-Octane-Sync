@echo off
setlocal EnableDelayedExpansion

echo.
echo ============================================================
echo   LoopFlow Rhino-to-Octane Installer
echo ============================================================
echo.

set "ROOT_DIR=%~dp0"
if "%ROOT_DIR:~-1%"=="\" set "ROOT_DIR=%ROOT_DIR:~0,-1%"
set "SRC_PY=%ROOT_DIR%\Python"
set "SRC_LUA=%ROOT_DIR%\LUA"
set "SRC_DATA=%ROOT_DIR%\Data"
set "DST_ROOT=%APPDATA%\McNeel\Rhinoceros\8.0\scripts\LoopFlow_R2O"
set "DST_PY=%DST_ROOT%\Py"
set "DST_LUA=%DST_ROOT%\Lua"
set "DST_DATA=%DST_ROOT%\Data"

rem -- Check Python\ subfolder exists --
if not exist "%SRC_PY%\" (
    echo [ERROR] Cannot find the Python folder:
    echo         %SRC_PY%\
    echo.
    echo         Expected layout after unzip:
    echo           LoopFlow_Rhino-to-Octane-Sync\install_LoopFlow_R2O.bat
    echo           LoopFlow_Rhino-to-Octane-Sync\Python\*.py
    echo           LoopFlow_Rhino-to-Octane-Sync\LUA\*.lua
    echo           LoopFlow_Rhino-to-Octane-Sync\Data\R2O_Shortcuts.txt
    echo.
    goto :END_FAIL
)

rem -- Check Rhino 8.0 AppData root exists --
if not exist "%APPDATA%\McNeel\Rhinoceros\8.0\" (
    echo [ERROR] Rhino 8.0 settings folder not found:
    echo         %APPDATA%\McNeel\Rhinoceros\8.0\
    echo.
    echo         Please make sure Rhino 8.0 is installed and has been
    echo         launched at least once before running this installer.
    echo.
    goto :END_FAIL
)
echo [1/5] Rhino 8.0 settings folder ... OK

rem -- Get install date (YYYYMMDD) for shortcut file stamp --
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set "DATETIME=%%I"
set "INSTALL_DATE=%DATETIME:~0,8%"

rem -- Remove old Py and LUA; keep Data (user config) --
if exist "%DST_PY%\"  rmdir /s /q "%DST_PY%"
if exist "%DST_LUA%\" rmdir /s /q "%DST_LUA%"
mkdir "%DST_PY%"
mkdir "%DST_LUA%"
if not exist "%DST_DATA%\" mkdir "%DST_DATA%"
echo [2/5] Target folders ready: %DST_ROOT%

rem -- Copy Python scripts --
echo [3/5] Copying Python scripts...
echo.

set "PY_SRC_COUNT=0"
for %%F in ("%SRC_PY%\*") do set /a PY_SRC_COUNT+=1
if %PY_SRC_COUNT%==0 (
    echo [WARN] No files found in %SRC_PY%\
    goto :END_FAIL
)
robocopy "%SRC_PY%" "%DST_PY%" /NJH /NJS /NDL /NP
if errorlevel 8 (
    echo [ERROR] robocopy failed for Python folder ^(exit code ^>= 8^).
    goto :END_FAIL
)
set "PY_DST_COUNT=0"
for %%F in ("%DST_PY%\*") do set /a PY_DST_COUNT+=1
echo   Source : %SRC_PY%
echo   Target : %DST_PY%
echo   Copied : !PY_DST_COUNT! of !PY_SRC_COUNT! files
echo.

rem -- Copy LUA scripts --
echo [4/5] Copying LUA scripts...
echo.

set "LUA_SRC_COUNT=0"
for %%F in ("%SRC_LUA%\*") do set /a LUA_SRC_COUNT+=1
if %LUA_SRC_COUNT% GTR 0 (
    robocopy "%SRC_LUA%" "%DST_LUA%" /NJH /NJS /NDL /NP
    if errorlevel 8 (
        echo [ERROR] robocopy failed for LUA folder ^(exit code ^>= 8^).
        goto :END_FAIL
    )
)
set "LUA_DST_COUNT=0"
for %%F in ("%DST_LUA%\*") do set /a LUA_DST_COUNT+=1
echo   Source : %SRC_LUA%
echo   Target : %DST_LUA%
echo   Copied : !LUA_DST_COUNT! of !LUA_SRC_COUNT! files
echo.

rem -- Copy Data (all files except R2O_Shortcuts.txt, handled separately) --
echo [5/5] Copying Data files...
echo.

if exist "%SRC_DATA%\" (
    robocopy "%SRC_DATA%" "%DST_DATA%" /XF R2O_Shortcuts.txt /NJH /NJS /NDL /NP
)

rem -- Shortcut file: first install copies directly; re-install uses date suffix to preserve existing --
if not exist "%DST_DATA%\R2O_Shortcuts.txt" (
    copy "%SRC_DATA%\R2O_Shortcuts.txt" "%DST_DATA%\R2O_Shortcuts.txt" >nul
    echo   Shortcuts : R2O_Shortcuts.txt ^(first install^)
) else (
    copy "%SRC_DATA%\R2O_Shortcuts.txt" "%DST_DATA%\R2O_Shortcuts_%INSTALL_DATE%.txt" >nul
    echo   Shortcuts : R2O_Shortcuts_%INSTALL_DATE%.txt ^(existing preserved^)
)
echo   Data      : %DST_DATA%
echo.

rem -- Locate .rhc in the root folder (same level as this BAT) --
set "RHC_FILE="
for %%F in ("%ROOT_DIR%\*.rhc") do set "RHC_FILE=%%F"

rem -- Success popup --
powershell -NoProfile -Command "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.MessageBox]::Show('!PY_DST_COUNT! Python + !LUA_DST_COUNT! LUA scripts copied.' + [char]10 + [char]10 + 'NEXT STEPS:' + [char]10 + '  Rhino side:' + [char]10 + '    1. Open Rhino 8' + [char]10 + '    2. Drag LoopFlow_R2O.rhc (next to this installer) into any Rhino viewport' + [char]10 + '    3. The LoopFlow R2O toolbar will appear' + [char]10 + [char]10 + '  Octane side:' + [char]10 + '    4. In OctaneRender, set the scripts folder to:' + [char]10 + '       %APPDATA%\McNeel\Rhinoceros\8.0\scripts\LoopFlow_R2O\Lua' + [char]10 + '    5. Scan for LUA scripts to register hotkeys', 'LoopFlow R2O Installer', [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Information)"

echo ============================================================
echo   Installation complete.
echo ============================================================
echo.
pause
exit /b 0

:END_FAIL
echo.
echo ============================================================
echo   Installation failed. See messages above.
echo ============================================================
echo.
pause
exit /b 1
