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

    new_content = re.sub(
        r"pathex=\[.*?\]",
        f"pathex=['{cwd}']",
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