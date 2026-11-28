# Tasks

## 1. 状态栏入口

- [x] 1.1 在 `code/ui/shell.py` 的 `create_status_bar` 中，于 `feedback_button` 左侧新增 `window.appreciation_button = text_button("赞赏作者")` 并连接 `window._on_appreciation`，复用现有 `text_button` 样式与 32px 状态栏行高；验证：启动主窗口后状态栏自左至右出现「赞赏作者」「使用帮助」两个文字入口，样式一致、无重复，点击「赞赏作者」触发 `_on_appreciation`（可临时打桩或确认信号已连接）。

## 2. 赞赏作者弹窗

- [x] 2.1 在 `code/ui/main_frame.py` 新增 `_on_appreciation` 方法（仿 `_on_feedback` 实例化模态 `AppreciationDialog`）；验证：点击状态栏「赞赏作者」弹出模态窗口，标题为「赞赏作者」，主窗口状态栏仍可见可用。
- [x] 2.2 实现 `AppreciationDialog(QDialog)`：标题栏 `sectionLabel`、内容区展示赞赏引导文案、页脚操作区，统一应用 `build_stylesheet`/`clear_inline_styles`/`apply_numeric_text_fonts`；验证：弹窗标题栏 / 内容区 / 页脚结构与「使用帮助」弹窗一致，浅色与深色主题截图无内联样式残留。
- [x] 2.3 在弹窗内容区并排展示 `res/qrcode/wxpay.jpeg`（标注「微信支付」）与 `res/qrcode/alipay.jpeg`（标注「支付宝」），`QPixmap` 缩放至约 160×160 保持纵横比；验证：开发环境下两张收款码均清晰可见、标注正确、不遮挡状态栏。
- [x] 2.4 对图片缺失或损坏做降级：`QPixmap` 为空时用占位 QLabel 显示「微信收款码不可用」/「支付宝收款码不可用」，另一张仍正常展示；验证：临时重命名其中一张图片后打开弹窗，占位提示出现且程序不崩溃，恢复文件后显示正常。

## 3. 打包资源与测试

- [x] 3.1 在 `invoice_tool.spec` 与 `invoice_tool_win.spec` 的 `datas` 中新增整目录打包 `code/res/qrcode` → `res/qrcode`；验证：按项目打包流程产出安装包后启动，点击「赞赏作者」弹窗内两张收款码均正常显示（路径指向 `_MEIPASS/res/qrcode`）。
- [x] 3.2 更新 `tests/test_ui_shell.py` 的状态栏入口断言，加入 `appreciation_button` 与 `_on_appreciation`；验证：`pytest tests/test_ui_shell.py` 通过，状态栏仅承载规定全局入口且信号已连接。
- [x] 3.3 集成回归：分别打开「使用帮助」与「赞赏作者」弹窗，确认状态栏顺序为「赞赏作者」「使用帮助」、版本号检查更新不受影响，且两处二维码互不干扰；验证：手动逐项检查通过，记录浅色 / 深色两套主题截图各一份。
