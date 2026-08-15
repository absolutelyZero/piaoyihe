## Context

当前 `_create_margin_widget()` 中创建了预设下拉框和恢复默认按钮，与四个边距输入框放在同一行。`_on_margin_changed` 中需要匹配预设方案、维护 `_is_updating_margin_preset` 标志位、处理"自定义"临时项，逻辑复杂且容易出错。

## Goals / Non-Goals

**Goals:**
- 移除预设下拉框、恢复默认按钮及其关联逻辑
- 简化 `_on_margin_changed` 为仅触发预览更新
- 移除 `_is_updating_margin_preset` 标志位
- 移除 `_on_margin_preset_changed` 和 `_on_reset_margins` 方法
- 保留 `margin_presets` 字典仅用于配置加载时的默认值回退（不对外暴露 UI）

**Non-Goals:**
- 不修改四个边距输入框的交互方式
- 不修改 PDFHandler 后端逻辑
- 不修改预览更新机制

## Decisions

- **移除而非保留**：彻底移除预设相关代码，而不是保留但隐藏 UI。因为预设逻辑（匹配、循环防护）是 Bug 的来源，且用户不需要
- **保留`default_margins`**：作为配置加载时未找到 `margins` 键的默认值回退，继续使用
- **`margin_presets`可保留但不再使用**：为了最小化改动，保留字典定义但不再被 UI 引用，后续可单独清理
- **`_on_margin_changed`简化**：直接调用 `_on_config_changed()`，不再做预设匹配

## Risks / Trade-offs

- 无。纯移除操作，不引入新功能，不存在回归风险