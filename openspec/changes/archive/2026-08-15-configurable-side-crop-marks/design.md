## Context

当前裁切线复选框在模式与排序卡片中，`_draw_crop_marks` 绘制四边虚线，位置与页边距绑定。新需求要求裁切线仅左右两侧，距离独立可配，控件应放在布局卡片中与页边距设置相邻。

## Goals / Non-Goals

**Goals:**
- 裁切线仅左右两侧，绘制垂直虚线从页面顶部到底部
- 左右裁切线距离页面边缘的距离独立可配置
- 控件放在布局卡片的页边距设置后
- 配置保存/加载

**Non-Goals:**
- 不修改页边距计算逻辑
- 不修改分割线绘制逻辑

## Decisions

- **控件位置**：在布局卡片的页边距 spinbox 后，增加分隔线 + "显示轮廓裁切线"复选框 + 左/右距离 spinbox（单位 mm，范围 0~50，精度 1mm）
- **裁切线距离**：从页面边缘向内的距离，单位为 mm，与页边距单位一致。例如左裁切线距离为 5mm，则 x = 5 * 72/25.4 pt 处绘制垂直线
- **配置存储**：`crop_mark_left`、`crop_mark_right` 作为 layout_config 的子字段，默认 0（不显示）
- **`show_crop_marks` 保留**：作为总开关，复选框控制此字段；距离为 0 时该边裁切线不绘制
- **`_draw_crop_marks` 重构**：参数改为读取 `crop_mark_left`、`crop_mark_right`（mm），转换为 pt 后绘制垂直线

## Risks / Trade-offs

- [向后兼容] 旧配置无 `crop_mark_left`/`crop_mark_right` → 默认 0，不绘制裁切线
- [预览一致] 预览路径不变，自动同步