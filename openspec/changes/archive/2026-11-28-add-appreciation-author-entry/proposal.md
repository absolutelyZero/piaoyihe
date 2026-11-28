# Proposal: 赞赏作者入口

## Why

希望让认可本工具的用户能直接扫码赞赏作者；目前底部状态栏只有「使用帮助」入口，已有二维码仅为公众号反馈码，缺少赞赏引导与收款码入口。

## What Changes

- 在底部状态栏的「使用帮助」左侧新增「赞赏作者」文字入口，与现有状态栏文字按钮样式保持一致。
- 点击「赞赏作者」弹出引导弹窗，复用现有辅助弹窗统一的标题栏 / 内容区 / 页脚结构，展示简短赞赏引导文案。
- 弹窗内并排展示 `code/res/qrcode/wxpay.jpeg` 与 `code/res/qrcode/alipay.jpeg` 两张收款码，分别标注支付方式。
- 两张收款码加入 PyInstaller 打包资源清单（mac / win 两个 spec），保证打包后可正常显示；图片缺失或损坏时给出占位提示，不影响其余界面。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `workspace-structure`：状态栏全局入口清单新增「赞赏作者」，规定其位于「使用帮助」左侧且全窗口仅出现一次。
- `ui-feedback-and-dialogs`：新增赞赏作者弹窗的外部可见行为——展示赞赏引导与微信 / 支付宝两张收款码，并沿用统一弹窗结构。

## Impact

- `code/ui/shell.py`：状态栏构建处新增「赞赏作者」文字按钮及信号连接。
- `code/ui/main_frame.py`：新增点击事件处理与赞赏作者弹窗实现。
- `code/res/qrcode/wxpay.jpeg`、`code/res/qrcode/alipay.jpeg`：作为弹窗图片资源。
- `invoice_tool.spec`、`invoice_tool_win.spec`：新增收款码目录的打包资源声明。
- `tests/test_ui_shell.py`：状态栏入口测试更新。
