# Design

## Context

票易合是 PySide6 (Qt Widgets) 桌面应用，业务能力已稳定：PDF/图片/OFD 混合合并、7 类票种字段提取与按票种重命名、MCP Server（9 个 Tools）、检查更新与系统深浅色适配。改造动机见 [proposal.md](proposal.md)。

现状约束：

- `code/ui/main_frame.py`（3238 行）把窗口结构、60 余处 `setStyleSheet(f"...")`、`QSplitter`、`QStackedWidget` 预览空态、全部按钮信号槽写在一个类里。
- `code/ui/file_list.py`（1261 行）用 `QTableWidget` 实现 9 列台账，样式为组件内独立 QSS；`_update_duplicate_display()` 通过 `setBackground(QColor("#FF9800"))` 整行涂色；`PreviewPopup` 为常驻浮窗；异步重复检查走 `ThreadPoolExecutor` + `QTimer(300ms)`。
- `code/ui/rename_dialog.py`（753 行）用 `QTabWidget` + 隐藏 tabBar + 左侧常驻导航按钮（2026-11-12 明确定稿），有独立的 `TEXT_PRIMARY` 等常量与整套 `_setup_stylesheet()`。
- `code/ui/theme.py` 的 `AppTheme` 暴露 `bg/card_bg/border/text_primary/...` 属性，被三个文件直接引用；`is_dark_mode()` 优先 Qt `colorScheme()`，Windows 回退注册表。
- `code/core/update_checker.py` 内 `UpdateDialog` / `QRCodeDialog` 使用默认控件样式，尚未接入统一令牌。
- 设计基线已产出：`req/ui/` 下 5 张 PNG（设计系统、主工作台、批量重命名、状态与弹窗、深色模式）。

因此这是一次**纯表现层重构**：所有既有 handler、信号槽、配置项与业务服务保持可复用，改造只负责「把控件搬到新位置、把样式换成令牌、把状态补齐」。

## Goals / Non-Goals

**Goals:**

- 建立单一色值/字体/尺寸来源，消除三个 UI 文件各自硬编码的配色。
- 用三段式结构重排主窗口（主体 → 输出提交条 → 状态栏），确立唯一主操作，并把全部全局状态与入口收敛到底部状态栏这一处。
- 让 6 份新增能力规格（`finance-ui-design-system`、`workspace-structure`、`invoice-ledger-ui`、`merge-configuration-ui`、`ui-feedback-and-dialogs`、`feature-preservation`）逐条可验收。
- 51 项功能改造前后行为一致，浅色/深色两套视觉都通过截图回归。

**Non-Goals:**

- 不迁移 UI 技术栈，不引入 WebView / QML / 前端框架。
- 不改 `code/core/` 业务算法、`code/mcp_server/`、CLI 参数、`config.json` 键名与迁移逻辑。
- 不新增功能点（含手动主题切换、搜索框、多语言、云同步）；主题仍跟随系统。
- 不改快捷键、文件对话框过滤器、拖放格式判定与打印顺序语义。
- 不重写 `per-type-rename-rules` 定义的票种规则行为，只调整承载它的控件。

## Decisions

### D1 — 保留 PySide6 Qt Widgets，不换渲染栈

保持现有 `QMainWindow` + `QWidget` + 信号槽架构。备选 Qt Quick / QML、Electron 式 Web UI、改用 WebView 承载新设计稿：全部否决，原因是会重写 7 类票种对话框与全部交互，破坏 Win7 + VxKex 兼容、PyInstaller 打包链与 GUI/MCP 共存模式，且对「保留全部功能」是最大风险源。Qt Widgets 完全能表达设计稿中的卡片、分段控件、状态标签与表格。

### D2 — 新增 `code/ui/tokens.py` 作为唯一令牌源，`AppTheme` 降级为兼容层

`tokens.py` 定义浅色/深色两套语义令牌（背景、卡片、描边、三级文字、主色、成功/警示/危险、圆角、间距刻度、字体栈）。`theme.py` 保留现有 `AppTheme` 属性名，内部改为从令牌取值，使三个旧文件在不改引用方式的前提下先获得一致性，再逐步把内联 QSS 迁移到全局样式表。

备选：(a) 继续逐控件 f-string QSS —— 否决，60 余处散落色值无法保证一致性；(b) 纯静态 `.qss` 文件 —— 否决，深浅主题需要运行时按系统检测结果切换，静态文件需维护两份且无法复用现有 `is_dark_mode()`。选择「令牌 + 运行时生成全局 QSS」兼顾两者。

### D3 — 全局样式表 + 组件工厂，替换逐控件 `setStyleSheet`

在 `QApplication` 级别注入一份由令牌生成的 QSS，按 `objectName` / 类选择器定义四级按钮、输入框、分段控件、卡片、状态标签与表格；新增 `ui/components.py` 提供 `primary_button()` / `secondary_button()` / `text_button()` / `danger_button()` / `status_chip()` / `section_card()` 等工厂，控件只设置 `objectName`。现有内联 `setStyleSheet` 随重构逐步删除，避免选择器优先级互相覆盖。

### D4 — 主窗口用现有 `QSplitter` 重排为三段式，不引入 Dock 体系

主体、输出提交条、状态栏用嵌套 `QVBoxLayout`；主体继续用 `QSplitter(Qt.Horizontal)` 承载左台账 / 右「预览 + 参数」，右侧用 `QVBoxLayout` 上下分。预览空态继续由 `QStackedWidget` 在占位页与图像页间切换。原「标题栏 + 上下文提示条」两个区段取消：品牌标记与副标题直接删除，就绪/运行状态、配置保存状态、版本号、使用帮助入口全部迁入底部状态栏，状态栏因此由 25px 单行扩展为 32px 单行（左：就绪状态 + 模式 + 布局摘要 + 文件数；右：临时消息位 + 配置保存状态 + 使用帮助 + 版本号）。合并去重规则是「以状态栏既有文案为准」——统一用「就绪」（弃用「已就绪」）、「配置自动保存」（弃用「配置已自动保存」），版本号「票易合 {版本号}」只保留状态栏一处；检查更新不再单独设按钮，改为点击版本号直接触发，与既有 `_on_version_click()` 行为一致；常驻拖放引导文案删除，拖放入口说明由台账空态投放带承担。备选 `QMainWindow` + `QDockWidget`：否决，会让输出提交条与状态栏脱离固定位置，也增加用户误拖动导致的布局漂移。

### D5 — 业务逻辑零改动，控件只重连既有 handler

所有按钮仍连接改造前同名 slot（添加/删除/清空/上移/下移/重命名/导出/浏览/合并/打印/刷新），参数控件仍写入同名 `config.json` 键。这样回归面被限制在布局与样式。备选「顺手重构 handler 与配置读取」：否决，`feature-preservation` 的 51 项验收会因此失去可比基线。

### D6 — 重复发票由「整行填色」改为「状态标记 + 计数」，判定逻辑不动

保留 `_do_check_duplicates()` / `duplicate_count_changed` 信号与 300ms 防抖；只把 `_update_duplicate_display()` 的呈现从 `setBackground("#FF9800")` 改为琥珀色行状态（左侧色条 + 发票号码与文件名警示色）并在台账标题栏显示重复组数/张数。Excel 导出的黄色高亮仍由 `InvoiceService.export_to_excel(..., duplicate_codes=...)` 负责，不改。备选「发现重复即阻断合并」：否决，会改变既有行为。

### D7 — 重命名对话框沿用既有 QTabWidget 方案

保留「隐藏 tabBar + 左侧常驻 7 票种导航按钮 + 单实例编辑器迁移」实现（这是 2026-11-12 专门修掉下拉遮挡字段按钮问题的方案），只替换样式、把字段按钮改为 chip 组件、补充示例结果与执行回执。备选改为下拉选择或重写导航：否决，会把已修复的缺陷重新引入。

### D8 — 设计稿作为验收基线，配套 51 项清单

`req/ui/00-设计说明与设计系统.png` 中的功能保留矩阵即验收清单；`01`–`04` 提供浅色主界面、重命名、状态弹窗与深色模式的像素级参照。每完成一个 UI 分组用截图比对，避免主观反复打磨。**注意**：设计稿 `01` 仍是五段式（含标题栏与上下文提示条），本规格已改为三段式，结构验收以 `workspace-structure` 的三段式需求为准，`01` 仅作为色值、间距、控件形态的参照，不作为区段数量的依据。

## Risks / Trade-offs

- **[QSS 优先级混乱]** 新旧样式并存期间局部 `setStyleSheet` 会覆盖全局 QSS → 分阶段替换，先生成全局表再逐文件删除内联样式；每次替换后按 `01`/`04` 截图比对。
- **[中文字体缺失]** macOS / Win7 未必有 Noto Sans SC → 字体栈回退 `Noto Sans SC → Source Han Sans SC → Source Han Sans CN → Microsoft YaHei → PingFang SC → SimHei → DengXian → system sans`，数字栈回退 `Inter → Noto Sans SC → monospace`（栈内只保留随包分发的字体）；并把设计稿同款 `Inter-VF.ttf` / `NotoSansSC-VF.ttf`（SIL OFL 1.1）随程序打包、启动时由 `register_bundled_fonts()` 注册，不联网加载，避免离线风险。
- **[深色模式对比不足]** 琥珀警示与蓝色数值在深色底上可能不够清晰 → 令牌表固定深色专用语义色（`#D9A441` / `#4A86D8`），并要求深色截图逐项核对文字对比。
- **[信号槽漏接]** 重排 3238 行主窗口时可能漏连某个按钮 → 51 项清单逐项手动触发 + 现有 `test_*.py` 回归；`feature-preservation` 提供验收记录要求。
- **[设计稿与规格区段数不一致]** `req/ui/01` 仍是五段式，规格已改为三段式，直接按图比对会误判缺项 → 结构验收以 `workspace-structure` 的三段式需求与 `test_ui_shell.py` 的 `test_01` 为准，`01` 只用于色值/间距/控件形态比对；A 组 6 项按「落点变化、项数不变」口径核对（标题栏入口 → 状态栏、拖放提示 → 台账投放带、检查更新 → 版本号）。
- **[窄窗口 9 列被裁]** 分栏拖动后列宽不足 → 表格启用水平滚动与最小列宽，禁止通过隐藏列来适配；`workspace-structure` 明确要求列不被裁切。
- **[异步任务与重绘竞态]** 预览刷新、重复检查、文件加载与界面重建并发 → 保留现有 `QTimer` 防抖、`ThreadPoolExecutor` 与 Qt 信号切回主线程的机制，重构期间不改这些线程的生命周期。
- **[打包资源]** 新增的 `Inter-VF.ttf` / `NotoSansSC-VF.ttf` / `OFL-1.1.txt` 已同步补入 `invoice_tool_win.spec` 与 `invoice_tool.spec` 的 `datas`（目标 `res/fonts/`），并复制到已构建的 `dist/票易合/_internal/res/fonts/`；`_fonts_dir()` 在打包后指向 `sys._MEIPASS/res/fonts`、开发时指向 `code/res/fonts`，须在 Windows/macOS 打包后各验一次字体确实注册成功。
- **[权衡]** 全局 QSS 会带来一次性的样式迁移成本，换取后续换肤/新增页面的一致性；`AppTheme` 兼容层保留一段时间会让代码里短期存在两套入口，计划在重构完成后随同批改动收敛。

## Migration Plan

1. **令牌层**：新增 `ui/tokens.py`；改造 `ui/theme.py` 使 `AppTheme` 从令牌取值且属性名不变；生成全局 QSS 并在 `code/main.py` 的 `QApplication` 创建后注入（只加一行，不动 CLI/MCP 参数解析）。验证：浅色/深色启动后现有界面配色统一、无报错。
2. **结构层**：在 `main_frame.py` 中把控件按三段式重排，保持所有控件变量名与信号连接不变；删除 `shell.py` 的 `create_title_bar()` / `create_context_bar()`（`brand_mark()` 随之删除），把 `version_label`、`feedback_button` 与状态文案迁入 `create_status_bar()`，`context_status_label` 变量名保留但改作状态栏临时消息位；同步清理 `tokens.py` 中 `#titleBar` / `#contextBar` / `#contextLabel` / `#brandTitle` 选择器并更新 `test_ui_shell.py` / `test_ui_tokens.py` / `test_font_alignment.py` 的相关断言。引入 `ui/components.py` 工厂替换按钮创建。验证：51 项清单中 A/C/E 组入口全部可见可点。
3. **台账层**：`file_list.py` 表头/行样式改为全局 QSS；新增投放带空态（台账为空时投放带占满列表区表头以下空间、保留九列表头，导入首个文件后让位给表格）、状态标记式重复告警与标题栏统计；右键菜单、悬停浮窗、双击、列头排序保持原样。验证：B 组 9 项 + `image-merge-support` 场景回归。
4. **参数与预览层**：把方向/行列/页边距/裁切线/模式/顺序控件搬入右侧分组面板，预览状态与缩放显示接入状态组件。验证：D/F 组 + `divider-visibility` 场景回归，输出 PDF 与改造前一致。
5. **弹窗层**：`rename_dialog.py` 与 `update_checker.py` 的 `UpdateDialog` / `QRCodeDialog` 对齐统一结构；补齐变量说明、使用帮助、结果回执与四态反馈。验证：G/H 组 + `per-type-rename-rules` 场景回归。
6. **验收与文档**：按 `feature-preservation` 逐项记录浅色/深色结果，替换 `README.md` / `说明文档.md` 中的界面预览图，执行 MCP 9 Tools 与 CLI 参数回归、Windows/macOS 打包验证。
7. **回滚**：本次不产生数据迁移，`config.json` 格式不变；若需回滚，`git revert` 本变更的提交即可回到旧界面，旧版仍可读取改造期间写下的配置。设计稿位于 `req/ui/`，不影响运行时。
