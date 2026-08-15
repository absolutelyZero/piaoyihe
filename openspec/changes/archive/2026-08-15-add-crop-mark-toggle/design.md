## Context

当前模式与排序设置卡片（`_create_mode_order_widget`）包含处理模式下拉框和打印顺序下拉框，两者之间用分隔线隔开。裁切线开关应放在打印顺序后，作为该卡片的最后一个配置项。

布局配置字典 `layout_config` 已在 `_get_current_layout()` 中构建，包含 `orientation`、`rows`、`cols`、`rotate`、`margins`。新增 `show_crop_marks` 字段。

PDFHandler 的 `_merge_files_into_doc` 中，在绘制分割线（`_draw_dividers`）之后，根据 `show_crop_marks` 标志绘制四边裁切线。裁切线使用已有的 `_draw_dashed_line` 方法。

## Goals / Non-Goals

**Goals:**
- 在打印顺序下拉框后增加"裁切线"复选框
- 复选框状态保存到 config.json，重启后保持
- 开启时在 PDF 输出页面上沿页边距绘制虚线裁切线
- 裁切线使用与分割线一致的虚线样式（灰色，dash=5, gap=3, width=0.5）

**Non-Goals:**
- 不修改合并预览预览的生成逻辑（预览中也显示裁切线）
- 不修改分割线（单元格分割线）的绘制逻辑
- 不修改四边边距的计算逻辑

## Decisions

- **复选框放在打印顺序后**：与处理模式、打印顺序放在同一卡片，用分隔线隔开，保持 UI 一致性
- **使用 `_draw_dashed_line` 复用**：已有虚线绘制方法，可复用绘制裁切线，保持样式一致
- **裁切线位置**：沿四边页边距线绘制，从页面边缘延伸到内容区域边缘
  - 上边：`y = margin_top`，从 `x = 0` 到 `x = page_width`
  - 下边：`y = page_height - margin_bottom`，从 `x = 0` 到 `x = page_width`
  - 左边：`x = margin_left`，从 `y = 0` 到 `y = page_height`
  - 右边：`x = page_width - margin_right`，从 `y = 0` 到 `y = page_height`
- **配置存储**：`show_crop_marks` 作为 `layout_config` 的子字段，统一保存到 config.json
- **配置加载**：`_load_config` 中读取 `layout_config.show_crop_marks`，默认 False

## Risks / Trade-offs

- [预览一致性] 预览图像使用 `_generate_preview_images` 调用 `merge_pdfs`，因此裁切线会自动出现在预览中 → 无需额外处理
- [向后兼容] 旧版 config.json 无 `show_crop_marks` 字段 → 默认 False，不绘制裁切线，不破坏旧配置