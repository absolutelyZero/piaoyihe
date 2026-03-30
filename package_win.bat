@echo off
chcp 65001 >nul
echo 开始打包 Windows 版本...

:: 清理旧构建文件
echo 清理旧文件...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build

:: 执行打包
echo 开始打包...
"C:\Users\Administrator\.pyenv\pyenv-win\versions\3.9.12\python.exe" -m PyInstaller invoice_tool_win.spec

echo.
echo 打包完成！
echo 输出目录: dist\票易合\票易合.exe
pause
