#!/usr/bin/env python3
"""
Patch PyInstaller spec file: replace hardcoded pathex with current working directory.

Args:
    sys.argv[1] (str): path to spec file (e.g. invoice_tool.spec or invoice_tool_win.spec)

Returns:
    int: 0 on success, 1 on failure
"""

import re
import sys
import os


def main() -> int:
    """Read spec file, replace pathex with current working directory."""
    if len(sys.argv) < 2:
        print("Usage: python patch_spec.py <spec_file>")
        return 1

    spec_file = sys.argv[1]
    cwd = os.getcwd()

    print(f"Patching {spec_file} pathex ...")
    print(f"Current working directory: {cwd}")

    with open(spec_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 保留 cwd，并把入口脚本所在目录(code/)也加入 pathex。
    # 原因: ui/core 是 code/ 下的顶层包，若 pathex 缺省 code 目录，
    # PyInstaller 在 CI 下将无法解析这些 (hidden)import，打出的 exe 会报 No module named 'ui'。
    code_dir = os.path.join(cwd, 'code')
    if not os.path.isdir(code_dir):
        code_dir = cwd
    new_pathex = f"pathex=[r'{cwd}', r'{code_dir}']"

    new_content = re.sub(
        r"pathex=\[.*?\]",
        lambda m: new_pathex,
        content
    )

    if new_content == content:
        print("Warning: no pathex found in spec file, check format")
        return 1

    with open(spec_file, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print(f"Patched {spec_file} pathex -> {cwd}")
    return 0


if __name__ == "__main__":
    sys.exit(main())