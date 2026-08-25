## Why

当用户将某边页边距设为 0mm 时，该边裁切线会与页面边缘重合，显示为一条无意义的实线，反而影响视觉。此时应跳过该边的裁切线绘制。

## What Changes

- `_draw_crop_marks` 中，每条裁切线绘制前检查对应边距是否 > 0，若为 0 则跳过

## Capabilities

### New Capabilities
- 无

### Modified Capabilities
- 无

## Impact

- `code/core/pdf_handler.py`: `_draw_crop_marks` 方法中为四条边分别添加边距 > 0 的判断条件