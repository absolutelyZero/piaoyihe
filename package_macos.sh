#!/bin/bash

# 票易合 macOS 打包脚本
# 功能：使用 PyInstaller 打包 macOS 应用程序

set -e  # 遇到错误立即退出

echo "=========================================="
echo "开始打包 票易合 macOS 应用程序..."
echo "=========================================="

# 删除之前的打包文件
echo "[1/4] 清理旧的打包文件..."
rm -rf dist build

# 检查必要的依赖
echo "[2/4] 检查依赖..."
python3 -c "import PySide6; print(f'PySide6 版本: {PySide6.__version__}')"
python3 -c "import fitz; print(f'PyMuPDF 已安装')"
python3 -c "import PIL; print(f'Pillow 版本: {PIL.__version__}')"
python3 -c "import PyInstaller; print(f'PyInstaller 已安装')"

# 使用 spec 文件打包
echo "[3/4] 开始打包..."
python3 -m PyInstaller invoice_tool.spec --clean --noconfirm 2>&1 | tee build.log

# 检查打包结果
if [ ! -d "dist/票易合.app" ]; then
    echo "错误：打包失败，未找到生成的 .app 文件"
    echo "请查看 build.log 了解详细错误信息"
    exit 1
fi

echo ""
echo "=========================================="
echo "打包成功！"
echo "=========================================="
echo ""
echo "应用程序位置: $(pwd)/dist/票易合.app"
echo ""

# 检查 app 结构
echo "应用程序结构:"
ls -la "dist/票易合.app/Contents/"
echo ""
echo "MacOS 目录内容:"
ls -la "dist/票易合.app/Contents/MacOS/" 2>/dev/null || echo "目录不存在"

# 创建 DMG
echo ""
echo "[4/4] 创建 DMG 安装包..."
cd dist
rm -rf tmp
mkdir -p tmp/dmg
cp -r 票易合.app tmp/dmg/

# 创建符号链接到 Applications 文件夹
ln -s /Applications tmp/dmg/Applications

# 创建 DMG
hdiutil create -volname "票易合" -srcfolder tmp/dmg -ov -format UDZO -fs HFS+ 票易合.dmg

# 清理临时文件
rm -rf tmp

cd ..

echo ""
echo "=========================================="
echo "DMG 创建成功！"
echo "=========================================="
echo ""
echo "安装包位置: $(pwd)/dist/票易合.dmg"
echo ""
echo "使用方法:"
echo "  1. 双击 票易合.dmg 挂载磁盘镜像"
echo "  2. 将 票易合.app 拖到 Applications 文件夹"
echo "  3. 从启动台打开应用程序"
echo ""
echo "如果系统提示'无法打开'，请前往:"
echo "  系统设置 > 隐私与安全性 > 安全性"
echo "  点击'仍要打开'"
echo ""
