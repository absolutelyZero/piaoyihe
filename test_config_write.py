#!/usr/bin/env python3
"""
测试配置文件写入功能
"""

import os
import json

# 测试配置文件路径
config_file = os.path.join(os.path.dirname(__file__), 'code', 'config.json')
print(f"配置文件路径: {config_file}")
print(f"配置文件存在: {os.path.exists(config_file)}")

# 测试写入忽略版本
try:
    if os.path.exists(config_file):
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        print(f"当前配置: {list(config.keys())}")
        
        # 设置忽略版本
        config['ignored_version'] = '1.0.0'
        
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
        print("写入成功")
        
        # 验证
        with open(config_file, 'r', encoding='utf-8') as f:
            new_config = json.load(f)
        print(f"验证忽略版本: {new_config.get('ignored_version')}")
    else:
        print("配置文件不存在，创建新文件")
        config = {
            'layout': 0,
            'mode': 0,
            'order': 0,
            'save_path': 'out.pdf',
            'print_checkbox': False,
            'ignored_version': '1.0.0'
        }
        # 确保目录存在
        os.makedirs(os.path.dirname(config_file), exist_ok=True)
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
        print("创建并写入成功")
        
        # 验证
        with open(config_file, 'r', encoding='utf-8') as f:
            new_config = json.load(f)
        print(f"验证忽略版本: {new_config.get('ignored_version')}")
except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()
