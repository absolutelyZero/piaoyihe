## Why

页边距预设方案（默认/窄边距/宽边距/自定义）增加了界面复杂度，但用户实际使用中仅需直接输入数值，预设选择逻辑还引入了循环触发和信号竞争等 Bug。移除预设方案可简化代码、减少维护成本，使交互更直接。

## What Changes

- 移除页边距预设下拉框（`margin_preset_combo`）及关联的预设匹配逻辑
- 移除"恢复默认"按钮（`reset_margin_btn`）
- 移除 `_is_updating_margin_preset` 标志位及循环防护逻辑，简化 `_on_margin_changed`
- 移除 `_on_margin_preset_changed` 和 `_on_reset_margins` 方法
- 保留四个上/下/左/右边距输入框（`QSpinBox`），保留默认值定义（`default_margins`）
- `_on_margin_changed` 简化为仅调用 `_on_config_changed()` 触发预览更新

## Capabilities

### New Capabilities
- 无（不引入新能力）

### Modified Capabilities
- 无（不涉及 spec 级行为变更，仅实现简化）

## Impact

- `code/ui/main_frame.py`: 简化 `_create_margin_widget` 为仅保留四个输入框；移除预设相关方法；移除 `_is_updating_margin_preset` 标志
- 不涉及后端 PDFHandler 变更，不涉及 API 或依赖变更