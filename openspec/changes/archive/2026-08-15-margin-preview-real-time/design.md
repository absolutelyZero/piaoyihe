## Context

当前主界面中，页边距（上/下/左/右）的四个 `QSpinBox` 输入框的 `valueChanged` 信号已连接到 `_on_margin_changed`，该方法会通过标签匹配更新预设方案的显示状态，并调用 `_on_config_changed()` 触发预览更新和配置保存。`_on_config_changed()` 使用 500ms 延迟定时器调用 `_update_preview()`，避免频繁操作。

## Goals / Non-Goals

**Goals:**
- 用户调整任意一个页边距输入框的值后，右侧合并预览在 500ms 内自动刷新
- 预设方案选择和恢复默认按钮同样触发预览更新
- 预览始终使用最新的边距值（实时读取 spinbox 值）

**Non-Goals:**
- 不修改 PDFHandler 后端逻辑
- 不改变预览延迟时间（500ms 已足够，避免频繁重渲染）
- 不涉及边距单位或精度变更

## Decisions

- **信号连接保持不变**：四个 spinbox 的 `valueChanged` → `_on_margin_changed` → `_on_config_changed` → `_update_preview` 链路已完整
- **实时读取而非缓存**：`_get_margin_config()` 直接读取 spinbox 的 `value()`，确保每次预览都使用最新值
- **预设方案同步**：`_on_margin_changed` 中自动匹配预设并更新 combo 显示，避免手动输入后预设状态不一致
- **信号安全**：更新 combo 时临时断开 `currentTextChanged` 信号，防止循环触发

## Risks / Trade-offs

- [信号竞争] 预设方案选择时，`setValue` 会触发 4 次 `valueChanged`，但 `_on_config_changed` 的 500ms 定时器会 coalesce（每次重置），最终只触发一次预览更新 → 无性能问题
- [自定义预设] 手动输入不匹配任何预设时，combo 会显示"自定义"临时项，该逻辑在 `_on_margin_preset_changed` 中自动清理 → 不影响预览更新