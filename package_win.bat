@echo off
chcp 65001 >nul

:: Switch to the directory where this batch file is located
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo Starting Windows build...

:: Clean old build files
echo Cleaning old files...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
if exist dist_build rmdir /s /q dist_build

:: Build to a temporary directory to avoid file locks on the common 'dist' folder
:: (IDE file watchers / antivirus may hold handles on 'dist' during COLLECT)
echo Building...
"E:\tools\pyenv-win\pyenv-win\versions\3.14.4\python3.14.exe" -m PyInstaller -y invoice_tool_win.spec --distpath dist_build --workpath build
if %ERRORLEVEL% NEQ 0 (
    echo Build failed
    pause
    exit /b 1)

:: Move build output to the final dist folder
echo Moving build output to dist...
robocopy "dist_build" "dist" /E /MOVE /R:5 /W:2 >nul
if %ERRORLEVEL% GEQ 8 (
    echo Failed to move build output to dist
    pause
    exit /b 1)
:: robocopy 成功时也可能返回非零的 1-7，避免影响后续 %ERRORLEVEL% 判断
set ERRORLEVEL=

echo.
echo Build complete!
echo Output: dist\票易合\票易合.exe

:: Verify MCP Server help (check exit code, no console output because console=False)
echo.
echo Verifying MCP Server mode...
"dist\票易合\票易合.exe" --mcp-server --help
if %ERRORLEVEL% NEQ 0 (
    echo MCP Server verification failed
    pause
    exit /b 1)

:: Verify key MCP dependencies can be imported in the packaged build
echo.
echo Verifying MCP Server dependencies...
"dist\票易合\票易合.exe" --verify-imports
if %ERRORLEVEL% NEQ 0 (
    echo MCP Server dependency import failed
    pause
    exit /b 1)

:: Read version
for /f "usebackq delims=" %%i in (`powershell -NoProfile -Command "(Get-Content code\version.json | ConvertFrom-Json).version"`) do set VERSION=%%i
echo Version: %VERSION%

:: Wait for PyInstaller to release file handles
echo Waiting for file handles to be released...
timeout /t 3 /nobreak >nul

:: Compress to zip (with retries in case of transient file locks)
echo Compressing...
set ZIP_FILE=票易合_win_%VERSION%.zip
if exist "%ZIP_FILE%" del /f /q "%ZIP_FILE%"

set RETRY=0
:COMPRESS_RETRY
powershell -NoProfile -Command "Compress-Archive -Path 'dist\票易合' -DestinationPath '%ZIP_FILE%' -Force" 2>nul
if %ERRORLEVEL% NEQ 0 (
    set /a RETRY+=1
    if %RETRY% LEQ 5 (
        echo Compression locked, retry %RETRY%...
        timeout /t 2 /nobreak >nul
        goto COMPRESS_RETRY
    ) else (
        echo Compression failed after max retries.
        pause
        exit /b 1
    )
)
echo Compression complete: %ZIP_FILE%

pause
