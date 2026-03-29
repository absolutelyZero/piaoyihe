# 删除之前的打包文件
rmdir /s /q dist build

# 使用spec文件打包
pyinstaller invoice_tool_win.spec