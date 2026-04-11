# 删除之前的打包文件
rm -rf dist build

# 激活虚拟环境并使用虚拟环境中的pyinstaller
source venv/bin/activate
# 使用spec文件打包
venv/bin/pyinstaller invoice_tool.spec

cd dist
mkdir -p tmp/dmg
cp -r 票易合.app tmp/dmg/
hdiutil create -volname "票易合" -srcfolder tmp/dmg -ov -format UDZO 票易合.dmg
rm -rf tmp