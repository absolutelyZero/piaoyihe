## Why

页边距（上/下/左/右）的数值调整后，右侧合并预览区域没有实时反映变更。当前仅有预设方案切换和布局变更会触发预览更新，手动输入边距值时预览未同步，导致用户无法直观看到调整效果，需要反复切换窗口确认，影响使用体验。

## What Changes

- 在 `_on_margin_changed` 中补充调用预览更新流程，确保任意一个边距输入框的值变更后，右侧预览在 500ms 内自动刷新
- 确保预设方案选择和恢复默认按钮同样触发预览更新
- 确保预览更新时使用最新的边距配置（而非缓存值）

## Capabilities

### New Capabilities
- `margin-preview-sync`: 页边距数值变更后自动同步到右侧合并预览，用户在调整上/下/左/右边距时可实时看到排版效果

### Modified Capabilities
- 无（不涉及 spec 级行为变更，仅实现细节修复）

## Impact

- `code/ui/main_frame.py`: 修改 `_on_margin_changed` 方法，确保其调用 `_on_config_changed()` 触发预览更新
- 不涉及后端 PDFHandler 变更，不涉及 API 或依赖变更