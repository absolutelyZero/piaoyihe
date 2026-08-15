## Why

当前裁切线沿四边页边距绘制，但用户实际只需要左右两侧的裁切线作为裁剪参考，且裁切线的距离应根据实际裁剪需求独立设置，而非与页边距绑定。

## What Changes

- 移除模式与排序卡片中的裁切线复选框
- 在布局卡片的页边距设置区域后，增加裁切线设置区域："显示轮廓裁切线"复选框 + 左/右裁切线距离输入框
- 裁切线仅保留左右两侧（垂直虚线），取消上/下裁切线
- 左右裁切线距离独立可配置，单位为 mm
- 布局配置字典增加 `crop_mark_left` 和 `crop_mark_right` 字段（mm），`show_crop_marks` 保留

## Capabilities

### New Capabilities
- 无

### Modified Capabilities
- `crop-mark-toggle`: 裁切线从四边改为仅左右两侧，距离独立可配置

## Impact

- `code/ui/main_frame.py`: 移除模式卡片中的复选框；在布局卡片中增加裁切线设置区域
- `code/core/pdf_handler.py`: `_draw_crop_marks` 改为仅绘制左右两侧裁切线，距离从配置读取