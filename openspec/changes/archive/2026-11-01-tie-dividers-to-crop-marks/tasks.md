## 1. 核心实现

- [x] 1.1 在 `code/core/pdf_handler.py` 的 `prepare_output_page` 中，将分割线绘制条件改为同时要求 `rows * cols > 1` 且 `layout_config.get('show_crop_marks', False)` 为真
- [x] 1.2 确认 `_draw_dividers` 内部逻辑、分割线样式与坐标计算不做任何改动

## 2. 测试

- [x] 2.1 新增 `tests/test_divider_visibility.py`：裁切线关闭时合并结果不含分割线
- [x] 2.2 同一测试文件覆盖：裁切线开启且 2x2 布局时包含分割线，且样式/位置与变更前一致（同时包含裁切线）
- [x] 2.3 覆盖单发票布局（1x1）即使开启裁切线也不绘制分割线
- [x] 2.4 覆盖配置缺省 `show_crop_marks` 时按关闭处理
- [x] 2.5 编写测试并运行 `python -m unittest discover -s tests -p "test_*.py"`，确认无回归（macOS 下 `test_ofd_support` 的既有环境性失败除外）

## 3. 文档

- [x] 3.1 在 `说明文档.md` 更新「使用说明/功能说明」中裁切线相关描述：勾选时同时显示分割线与裁切线，未勾选时两者均不显示；说明左右裁切线距离为 0 时仅显示分割线
- [x] 3.2 在 `说明文档.md` 进度记录中新增本次任务条目（任务、完成内容、验证结果、修改文件）
