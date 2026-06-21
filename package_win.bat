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

:: 压缩为 zip
echo 开始压缩...
powershell -NoProfile -Command "Compress-Archive -Path 'dist\票易合' -DestinationPath '票易合_win_%VERSION%.zip' -Force"
echo 压缩完成: 票易合_win_%VERSION%.zip

pause
