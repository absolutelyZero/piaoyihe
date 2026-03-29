#!/usr/bin/env python3
"""
测试发票PDF合并工具
"""

import os
import sys

# 添加代码目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'code'))

try:
    import wx
    import fitz
    print("✓ 依赖安装成功")
except ImportError as e:
    print(f"✗ 依赖安装失败: {e}")
    print("请先安装依赖: pip3 install wxPython PyMuPDF")
    sys.exit(1)

print("\n测试文件结构:")
print(f"主入口文件: {os.path.exists('code/main.py')}")
print(f"主窗口文件: {os.path.exists('code/ui/main_frame.py')}")
print(f"文件列表文件: {os.path.exists('code/ui/file_list.py')}")
print(f"PDF处理文件: {os.path.exists('code/core/pdf_handler.py')}")

print("\n测试完成！")
print("运行以下命令启动工具:")
print("python3 code/main.py")
