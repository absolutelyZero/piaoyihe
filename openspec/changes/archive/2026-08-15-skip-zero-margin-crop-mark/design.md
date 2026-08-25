## Context

`_draw_crop_marks` 方法目前无条件绘制四条边裁切线。当边距为 0 时，裁切线位置与页面边缘重合，没有实际意义。

## Goals / Non-Goals

**Goals:**
- 当某边边距为 0 时，跳过该边的裁切线绘制

**Non-Goals:**
- 不修改非零边距的裁切线行为
- 不修改分割线或其它绘制逻辑

## Decisions

- 使用 `if margin > 0` 简单判断，不做近似阈值处理（如 `<= 0.01`），因为边距输入为整数 mm，转换为 pt 后为精确值
- 四个边各自独立判断，互不影响

## Risks / Trade-offs

- 无