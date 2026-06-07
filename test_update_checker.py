#!/usr/bin/env python3
"""
测试更新检查器
"""

import os
import sys
import json
import tempfile

# 添加code目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'code'))

from core.update_checker import UpdateChecker
import wx

# 创建临时配置文件
def test_ignore_version():
    # 创建临时版本文件
    with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
        json.dump({'version': '0.0.4'}, f)
        version_file = f.name
    
    # 创建临时配置文件
    with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
        json.dump({'layout': 0}, f)
        config_file = f.name
    
    try:
        # 创建更新检查器
        checker = UpdateChecker(version_file, "https://piaoyihe.oss-cn-hangzhou.aliyuncs.com/update/version.json", config_file)
        
        # 检查更新
        has_update, remote_version = checker.check_for_updates()
        print(f"有更新: {has_update}, 远程版本: {remote_version}")
        
        if has_update:
            # 模拟忽略版本
            checker._set_ignored_version(remote_version)
            print(f"已忽略版本: {remote_version}")
            
            # 检查配置文件
            with open(config_file, 'r') as f:
                config = json.load(f)
                print(f"配置文件中的忽略版本: {config.get('ignored_version')}")
            
            # 再次检查更新
            has_update, _ = checker.check_for_updates()
            print(f"忽略后再次检查更新: {has_update}")
    finally:
        # 清理临时文件
        if os.path.exists(version_file):
            os.unlink(version_file)
        if os.path.exists(config_file):
            os.unlink(config_file)

if __name__ == "__main__":
    test_ignore_version()
