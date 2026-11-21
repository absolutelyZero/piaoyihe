## Why

当前合并结果中，发票之间的分割线始终绘制，而裁切线有独立开关，导致用户无法通过「裁切线」复选框统一控制输出中的辅助线：不需要辅助线时分割线仍然出现在打印/导出结果中。将分割线纳入裁切线配置项管理，可让用户用一个开关同时控制两类辅助线的显示。

## What Changes

- 分割线的绘制受裁切线开关 `show_crop_marks` 控制：开关未勾选时不绘制分割线，勾选时照常绘制
- 不再对分割线提供独立开关，分割线效果与裁切线开关严格一致
- 布局配置中不新增字段（复用现有 `show_crop_marks`），配置结构保持不变
- 裁切线本身的绘制逻辑与外观保持不变

## Capabilities

### New Capabilities
- `divider-visibility`: 发票之间分割线的显示由「裁切线」复选框统一控制，与裁切线开关保持同步

### Modified Capabilities
- 无（`crop-mark-toggle` 尚未同步到 `openspec/specs/`，本次不修改其需求）

## Impact

- `code/core/pdf_handler.py`: `_merge_files_into_doc` 中 `prepare_output_page` 的分割线绘制增加 `show_crop_marks` 判断
- `code/ui/main_frame.py`: 无需改动（`show_crop_marks` 已随布局配置传递）
- `code/mcp_server/tools.py`: 无需改动（`crop_marks.show` 已映射为 `show_crop_marks`，分割线随之同步）
- `tests/`：补充分割线随裁切线开关显隐的单元测试
- `说明文档.md`：补充本次功能说明与进度记录
