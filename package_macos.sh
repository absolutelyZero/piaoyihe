# 切换到脚本所在目录，确保相对路径正确
cd "$(dirname "$0")" || exit 1

# 删除之前的打包文件
rm -rf dist build

# 激活干净的虚拟环境并使用其中的pyinstaller
source clean_venv/bin/activate
# 修正 spec 中的硬编码 pathex（与 .github/workflows/build.yml 保持一致）。
# 原因: ui/core 是 code/ 下的顶层包，pathex 缺省 code 目录时 PyInstaller 无法解析，
# 打出的包启动即报 No module named 'ui'。
clean_venv/bin/python scripts/patch_spec.py invoice_tool.spec || { echo "spec 路径修正失败"; exit 1; }
# 使用spec文件打包
clean_venv/bin/pyinstaller invoice_tool.spec

cd dist
mkdir -p tmp/dmg
cp -r 票易合.app tmp/dmg/
hdiutil create -volname "票易合" -srcfolder tmp/dmg -ov -format UDZO 票易合.dmg
rm -rf tmp

# 验证 MCP Server 模式与关键依赖
APP="票易合.app/Contents/MacOS/票易合"
echo "验证 MCP Server 模式..."
"$APP" --mcp-server --help || { echo "MCP Server 验证失败"; exit 1; }
echo "验证 MCP Server 关键依赖导入..."
"$APP" --verify-imports || { echo "MCP Server 依赖导入失败"; exit 1; }

# 读取版本号
VERSION=$(python3 -c "import json; print(json.load(open('../code/version.json'))['version'])")
echo "版本号: $VERSION"

# 压缩为 zip
echo "开始压缩..."
zip -ry "票易合_macos_${VERSION}.zip" "票易合.app"
echo "压缩完成: 票易合_macos_${VERSION}.zip"

