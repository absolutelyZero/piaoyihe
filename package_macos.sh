# 删除之前的打包文件
rm -rf dist build

# 激活干净的虚拟环境并使用其中的pyinstaller
source clean_venv/bin/activate
# 使用spec文件打包
clean_venv/bin/pyinstaller invoice_tool.spec

cd dist
mkdir -p tmp/dmg
cp -r 票易合.app tmp/dmg/
hdiutil create -volname "票易合" -srcfolder tmp/dmg -ov -format UDZO 票易合.dmg
rm -rf tmp

# 读取版本号
VERSION=$(python3 -c "import json; print(json.load(open('../code/version.json'))['version'])")
echo "版本号: $VERSION"

# 压缩为 zip
echo "开始压缩..."
zip -ry "票易合_macos_${VERSION}.zip" "票易合.app"
echo "压缩完成: 票易合_macos_${VERSION}.zip"

