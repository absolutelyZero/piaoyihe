# Design

## Context

见 proposal.md 的 Why。当前状态栏由 `code/ui/shell.py:669` 的 `create_status_bar` 构建，右端依次为临时消息位、配置保存状态、`使用帮助` 文字按钮（`window.feedback_button`，连接 `window._on_feedback`）与可点击的版本号；`code/ui/main_frame.py:1989` 的 `FeedbackDialog` 展示了现有 `res/qrcode.jpg` 反馈二维码。项目已存在 `ui-feedback-and-dialogs` 规定的统一弹窗结构（`tokens.build_stylesheet` + `clear_inline_styles` + `apply_numeric_text_fonts`）。本次新增的收款码位于 `code/res/qrcode/wxpay.jpeg` 与 `code/res/qrcode/alipay.jpeg`，当前 PyInstaller spec 仅打包了 `code/res/qrcode.jpg`，尚未打包新目录。

## Goals / Non-Goals

**Goals:**
- 在状态栏「使用帮助」左侧加入「赞赏作者」入口，风格与现有文字按钮一致。
- 新增赞赏作者弹窗，统一标题 / 内容 / 页脚结构，展示赞赏引导与两张带标注的收款码。
- 让两张收款码同时可用于开发与打包后的运行环境；图片异常时优雅降级。

**Non-Goals:**
- 不引入网络支付、订单跟踪或金额输入等交互，二维码仅作静态展示。
- 不修改现有使用帮助 / 检查更新 / 变量说明弹窗的内容与行为。
- 不改变状态栏其余入口的顺序、文案或行为。

## Decisions

1. **入口实现**：在 `code/ui/shell.py` 的 `create_status_bar` 中，于 `feedback_button` 之前用现有 `text_button`（`code/ui/tokens.py` 生成的 `statusBarLabel` 同类样式）新增 `window.appreciation_button = text_button("赞赏作者")`，连接到 `window._on_appreciation`。复用现有 `text_button` 可保证字号、行高与去下划线行为跟「使用帮助」一致，避免新增一套样式导致状态栏高度不齐（参照既有「使用帮助」text_button 的对齐修复）。
2. **弹窗实现**：在 `code/ui/main_frame.py` 新增处理函数 `_on_appreciation`（仿 `_on_feedback` 实例化模态对话框）与 `AppreciationDialog(QDialog)`。弹窗结构沿用 `FeedbackDialog` 的做法：`setStyleSheet(build_stylesheet(_theme.dark))`、`clear_inline_styles`、`apply_numeric_text_fonts`；标题栏用 `sectionLabel`，内容区用 `QTextEdit`/`QLabel` 展示引导，底部以 `QHBoxLayout` 并排两张 `QLabel` 展示 `QPixmap`，两侧配 `qrcodeHint` 标注「微信支付」「支付宝」。
   - 备选：嵌入 `QWebView`/富文本 HTML 图片 → 否决，增加体积且二维码加载路径更难控制；用原生 QLabel/QPixmap 与现有反馈二维码做法一致。
3. **资源加载路径**：按现有 `FeedbackDialog` 的相对路径方式（从 `__file__` 上溯到 `code/res`）定位 `res/qrcode/wxpay.jpeg` 与 `res/qrcode/alipay.jpeg`，`QPixmap` 缩放至约 160×160 保持纵横比。图片不存在或 `isNull()` 时用 `qrcodePlaceholder`（或等价 objectName）显示「微信收款码不可用」「支付宝收款码不可用」，保证另一张正常显示。
   - 注意 `wxpay.jpeg` 实为 PNG 内容，`QPixmap` 按扩展名可正常识别，不做预转换。
4. **打包资源**：在 `invoice_tool.spec` 与 `invoice_tool_win.spec` 的 `datas` 中新增将整个 `code/res/qrcode` 目录打包到 `res/qrcode` 的条目（类似现有 `code/res/icons` 的整目录打包），使上述相对路径在 `_MEIPASS/res/qrcode` 下成立，避免逐个文件遗漏。
5. **测试**：`tests/test_ui_shell.py` 的入口断言列表加入 `appreciation_button` 与 `_on_appreciation`，确保状态栏仍只承载这些全局入口且信号已连接。

## Risks / Trade-offs

- [新员工/打包环境遗漏资源目录] → 通过两个 spec 均采用整目录打包，开发与打包路径一致；弹窗对缺失图片有占位降级，不会崩溃。
- [新增按钮导致状态栏拥挤或高度变化] → 复用 `text_button` 与现有 32px 状态栏行高规则，按钮置于「使用帮助」左侧，不改变状态栏高度；实现后用截图比对浅色 / 深色两套主题。
- [图片体积较大（alipay.jpeg 338KB）] → 仅两张静态图，对包体影响有限；如后续在意体积可单独压缩，不在本次范围内。

## Migration Plan

无需迁移用户数据或配置。代码与资源改动随版本发布即可；回滚时删除状态栏入口、弹窗与 spec 打包条目即可恢复原状。

## Open Questions

无。赞赏引导文案采用通用表述（「如果本工具对你有帮助，欢迎扫码赞赏作者，你的支持是持续改进的动力。」），可在实现时按产品语气微调，不影响结构与验收。
