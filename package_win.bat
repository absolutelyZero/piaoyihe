@echo off
chcp 65001 >nul
echo 开始打包 Windows 版本...

:: 清理旧构建文件
echo 清理旧文件...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build

:: 执行打包
echo 开始打包...
"E:\tools\pyenv-win\pyenv-win\versions\3.14.4\python3.14.exe" -m PyInstaller invoice_tool_win.spec

echo.
echo 打包完成！
echo 输出目录: dist\票易合\票易合.exe

:: 读取版本号
for /f "usebackq delims=" %%i in (`powershell -NoProfile -Command "(Get-Content code\version.json | ConvertFrom-Json).version"`) do set VERSION=%%i
echo 版本号: %VERSION%

:: 等待 PyInstaller 释放文件句柄
echo 等待文件句柄释放...
timeout /t 3 /nobreak >nul

:: 压缩为 zip（带重试，避免偶发文件占用）
echo 开始压缩...
set ZIP_FILE=票易合_win_%VERSION%.zip
if exist "%ZIP_FILE%" del /f /q "%ZIP_FILE%"

set RETRY=0
:COMPRESS_RETRY
powershell -NoProfile -Command "Compress-Archive -Path 'dist\票易合' -DestinationPath '%ZIP_FILE%' -Force" 2>nul
if %ERRORLEVEL% NEQ 0 (
    set /a RETRY+=1
    if %RETRY% LEQ 5 (
        echo 压缩被占用，第 %RETRY% 次重试...
        timeout /t 2 /nobreak >nul
        goto COMPRESS_RETRY
    ) else (
        echo 压缩失败，已达到最大重试次数。
        pause
        exit /b 1
    )
)
echo 压缩完成: %ZIP_FILE%

pause
