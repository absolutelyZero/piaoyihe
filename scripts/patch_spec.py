#!/usr/bin/env python3
"""
修正 PyInstaller spec 文件中的 pathex 为当前工作目录

功能描述:
    GitHub Actions CI 环境中，spec 文件中的 pathex 是硬编码的本地路径，
    此脚本自动将其替换为当前工作目录，确保打包能正确找到项目依赖。

参数:
    sys.argv[1] (str): spec 文件路径（如 invoice_tool.spec 或 invoice_tool_win.spec）

返回值:
    int: 0 表示成功，非 0 表示失败
"""

import re
import sys
import os


def main():
    """主函数：读取 spec 文件，替换 pathex 为当前工作目录"""
    if len(sys.argv) < 2:
        print("用法: python patch_spec.py <spec_file>")
        sys.exit(1)

    spec_file = sys.argv[1]
    cwd = os.getcwd()

    print(f"正在修正 {spec_file} 的 pathex...")
    print(f"当前工作目录: {cwd}")

    with open(spec_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 替换 pathex 为当前工作目录
    new_content = re.sub(
        r"pathex=\[.*?\]",
        f"pathex=['{cwd}']",
        content
    )

    if new_content == content:
        print("警告: 未找到 pathex 配置，请检查 spec 文件格式")
        sys.exit(1)

    with open(spec_file, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print(f"已修正 {spec_file} 的 pathex 为: {cwd}")
    return 0


if __name__ == "__main__":
    sys.exit(main())