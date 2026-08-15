## Why

用户在打印发票后需要手动裁剪，但缺少裁剪参考线。在打印顺序配置项后增加裁切线显示开关，开启后沿页边距绘制虚线，标明裁剪边界，方便用户精确裁剪。

## What Changes

- 在模式与排序设置卡片中，打印顺序下拉框后增加"裁切线"复选框
- 布局配置字典增加 `show_crop_marks` 字段（bool）
- PDFHandler 在绘制分割线时，若 `show_crop_marks` 为 True，额外绘制四边裁切线
- 裁切线为虚线，沿页边距延伸至页面边界
- 裁切线状态保存到 config.json，重启后保持

## Capabilities

### New Capabilities
- `crop-mark-toggle`: 在打印顺序配置项后增加裁切线显示开关，开启后在 PDF 输出时沿页边距绘制虚线

### Modified Capabilities
- 无

## Impact

- `code/ui/main_frame.py`: `_create_mode_order_widget` 方法中增加复选框；配置保存/加载逻辑增加 `show_crop_marks` 字段
- `code/core/pdf_handler.py`: `_merge_files_into_doc` 中增加裁切线绘制逻辑
- `code/ui/merge_worker.py`: 透传 `show_crop_marks` 配置（如需要）