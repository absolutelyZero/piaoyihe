# 验收记录 · finance-grade-ui-redesign

> 本文件记录 v2 UI 改造后的自动回归证据与剩余人工验证项。
> 设计基线：`req/ui/00`–`04`；功能基线 51 项见 `req/ui/00-设计说明与设计系统.png` 的保留矩阵。

## 1. 验证环境

| 项 | 值 |
| --- | --- |
| Python | 3.13.14（首次验收记录）；本轮复核用 DSH 内置 Python 3.12.14 |
| PySide6 | 6.11.2（`.pylibs`） |
| PyMuPDF | 2.1（`.pylibs`） |
| Qt 平台 | `QT_QPA_PLATFORM=offscreen` |
| 字体 | `QT_QPA_FONTDIR=C:/Windows/Fonts`；设计稿同款 `Inter-VF.ttf` / `NotoSansSC-VF.ttf` 由 `register_bundled_fonts()` 随程序注册，空字体环境下也能正常显示中文与数字 |

补充：`openpyxl` 缺 `et_xmlfile`、`Pillow` 缺 cp313 扩展，均为本机依赖缺失。前者已补入本地 `.pylibs`；后者在 `.testtmp/shims/PIL` 提供仅用于测试的 `Image.new().save()` 替身（不进入项目产物）。

## 2. 自动回归结果

| 命令 | 结果 |
| --- | --- |
| `python -m unittest tests.test_ui_tokens -v` | 10 项通过（令牌键名、色值、QSS、文档一致性、AppTheme 兼容） |
| `python -m unittest tests.test_ui_shell -v` | 16 项通过（三段式结构、9 列、按钮层级、配置加载、状态同步、重复告警、弹窗、CLI、51 项矩阵） |
| `python -m unittest tests.test_ui_merge_behavior -v` | 3 项通过（裁切线开关、零页边距、PDF/图片混合合并） |
| 既有业务回归（11 个模块，预导入 PySide6 以避免 fitz/Qt 导入顺序导致的段错误） | **169 项通过，0 失败，0 错误，3 跳过** |

覆盖到的既有规范：`divider-visibility`、`image-merge-support`、`per-type-rename-rules`、`mcp_server.tools`、`invoice_service`、`ofd_converter`、字段提取器回归。

真实运行时界面截图（浅色 / 深色 / 重命名弹窗）由 `QT_QPA_PLATFORM=offscreen` + `QWidget.grab()` 生成并与 `req/ui/01`、`02`、`04` 逐块核对，归档为 `req/ui/05-运行校验-浅色.png`、`06-运行校验-深色.png`、`07-运行校验-重命名.png`。

## 2b. 字体对齐专项验收（本轮）

按 `字体与界面对应关系.md` 完成 5 项字体修正，新增 `tests/test_font_alignment.py`（12 项）：

| 修正项 | 结果 |
| --- | --- |
| 1 字重/字号常量集中定义，QSS 无魔法数字 | `FONT_WEIGHT` / `FONT_SIZE` / `DESIGN_DISPLAY_SIZE` 落地；QSS 45 处 `font-size`、19 处 `font-weight` 全部改为常量引用；Bold 20px 明确标注「设计稿展示用，界面不消费」，未加入 QSS |
| 2 表头字体双来源 | `QHeaderView::section` 移除 font-*；统一由 `tokens.header_font()` 生成 12px / 中文栈首位 Microsoft YaHei UI / Regular，仅金额列 Bold + 主色（实测 9 列均 12px，仅 col3 加粗；12px 即设计稿实测值，见 4b-9） |
| 3 内联 `font-size` 清理 | `main_frame.py` 9 处逐控件 `setStyleSheet` 删除，改为 `helpText` / `qrcodeHint` / `qrcodePlaceholder` / `hSeparator` 的 objectName + QSS 绑定；旧版遗留方法与注释一并清理，全项目已无逐控件 `font-*` 内联样式 |
| 4 数字展示位统一 Inter + tnum | 纯数字/金额/版本号/缩放/示例结果、含数字的次级文本位（状态栏/页码/每页张数/重复计数/记录数）、数字输入控件（SpinBox / 路径框）全部纳入 `apply_numeric_text_fonts()`；中文经 `setFamilies` 回退到中文栈首位（Microsoft YaHei UI）；中文规则输入框、字段芯片、中文下拉保持中文栈 |
| 5 QSS 与 setFont 冲突 | 6 类冲突逐项消除，清单见 `字体与界面对应关系.md` 第 4 节；关键机制：QSS 通用 `QLabel` / 容器 / 表单规则不再声明 `font-family`（否则覆盖 `setFont()` 导致 `tnum` 失效），默认字体由 `app.setFont()` 唯一提供 |

**关键回归修复**：启用 `Inter+tnum` 后 20 位发票号码在 11px 下实测宽 140px，叠加 delegate 文本边距后 151px 列会触发省略号。收紧单元格内边距 6→4px 并把发票号码列 151→162px（路径列 Stretch 吸收，9 列结构与总宽不变），放大截图确认 `24310000000017846321` 完整显示、无省略号。标题栏 `v0.1.15` 完整显示。

**最终回归**：12 个测试模块合计 **184 项通过，0 失败，0 错误，3 跳过**。浅色/深色/弹窗三张离屏截图确认无中文方框、数字字形一致、小数点对齐、无文字裁切或控件重叠。

## 3. 51 项功能保留矩阵（自动证据）

| 组 | 项数 | 证据 | 结论 |
| --- | --- | --- | --- |
| A 窗口框架 | 6 | `test_01` 三段 objectName（且断言无 `title_bar` / `context_bar` / `check_update_btn`）、`test_16` 状态栏内版本/帮助/进度属性 | 通过 |
| B 票据台账 | 9 | `test_03` 9 列列名、`test_02` 横向滚动、`test_08` 等宽右对齐、`test_09` 重复状态标记、`test_10` 右键四项槽 | 通过 |
| C 列表操作 | 6 | `test_16` 七个按钮属性 + `test_04` 危险级样式 | 通过 |
| D 排版参数 | 5 | `test_05` 方向/行列/模式加载、`test_12` 配置键名与裁切线字段 | 通过 |
| E 顺序与输出 | 8 | `test_04` 唯一主按钮、`test_06` 禁用原因、`test_12` 输出配置键 | 通过 |
| F 实时预览 | 5 | `test_07` 空态/预览开关、`test_05` 页码与每页张数摘要 | 通过 |
| G 批量重命名 | 6 | `test_14` 7 类票种导航/字段芯片/示例结果/回执、`tests.test_rename_rules_by_type` | 通过 |
| H 系统能力 | 6 | `test_12` 配置持久化与键名、`test_13` CLI 参数、`tests.test_mcp_tools`、`tests.test_ofd_support` | 通过 |

`config.json` 键名比对：改造前后一致，未新增/改名/删除任何字段（含 `layout_config.show_crop_marks` / `crop_mark_left` / `crop_mark_right` / `preview_enabled` / `rename_rules`）。

## 4. 截图核对发现并已修复的问题

1. 右侧参数卡片最小宽度过大，把分栏挤成 48/52 → 重写为紧凑表单行，实测恢复 `860 / 574`（60/40）。
2. `minimumSectionSize(72)` 把首列预览图标列撑到 72px → 改为 40px 并保留水平滚动，9 列完整可见。
3. 深色模式下非重复行被写入浅色前景导致不可读 → 改为清空 `ForegroundRole`/`BackgroundRole`，交由全局 QSS 决定颜色。
4. 离屏环境下强制设置不存在的 `Noto Sans SC` 字体导致中文方框 → `apply_application_style()` 仅在字体确实可用时覆盖应用字体，否则保留 Qt 默认；QSS 内仍使用带回退的字体栈。
5. 台账空白区过大、投放带偏矮 → ~~投放带与表格共享剩余空间~~ ~~**已修正为投放带独占列表区**（空态隐藏九列表格，投放带与列表同宽同高）~~ → **后续修订：投放带改为表格视口覆盖层**，只铺满九列表头以下的整块列表区，九列表头始终可见（`FileListPanel.set_empty_overlay()` / `sync_empty_overlay()`）；首个文件导入后投放带隐藏、表格占满列表区，表头位置与列宽不跳动。见 `invoice-ledger-ui` 投放带需求与 `tasks.md` 3.4；浅色/深色截图复查无重叠、无裁切。
6. 回执标签在深色主题下对比不足 → 信息态文字改用 `text_primary`。
7. 输出提交条固定 76px 导致主按钮下半部被回执条裁切 → 提高到 96px，浅色/深色复查「合并 PDF」完整可见。
8. `res/icons` 图标固定 `#333` 描边在深色背景下几乎不可见 → `shell.tinted_icon_label()` 渲染时改为中性灰蓝 `#8A97A8`，复用仓库现有 SVG，不新增资源。
10. 用户两轮反馈状态栏右侧高度不齐（「使用帮助」低于两侧文本）→ 分两步修：
    - 第一步（不足）：文字按钮 QSS 原为 `padding: 4px 8px; min-height: 24px`，24px 内容高 + 上下各 4px 内边距把按钮撑到 32px，在 32px 高的状态栏里被裁切。改为 `padding: 0px 8px; min-height: 24px; max-height: 24px` 后，**离屏(offscreen)测得已对齐，但真实 cocoa 下按钮仍比相邻文本低 2px**（标签 h=19、按钮 h=24，墨迹中线 14.0 vs 16.0）——离屏与真实平台的字体度量差 2px 以上，此类对齐必须在真实平台按墨迹中线复测。
    - 第二步（最终）：根因是**各控件行高不统一**（标签由 sizeHint 得 19px、按钮被 QSS 钉 24px），且**QSS 的 `min-height`/`max-height` 会覆盖代码里的 `setFixedHeight()`**（重刷样式即回弹，代码里钉高度无效）。因此在 `tokens.py` 增加三条作用域规则统一状态栏行高：`QFrame#statusBar QLabel#statusBarLabel`、`QFrame#statusBar QPushButton#textButton` 均 `min-height/max-height: 22px`，`QFrame#statusBar QLabel#versionLabel` 因自带 1px 边框 + 3px 内边距改为 `padding: 3px 8px; min-height/max-height: 14px`（内容高 14 + 边距 = 22）。`QPushButton#textButton` 默认 24px 保留给预览头与对话框标题栏。
    - 结果：cocoa（dpr=2）实测五项 h 全为 22、y 全为 5，墨迹中线 spread 0.5px，且在 light / repolish / dark / light again 四种状态下稳定；预览头三项 h 全为 24、spread 0.25px 未受影响。新增 `test_18`（断言状态栏四项同高且为 22px、盒中心极差 ≤ 1px、不超出栏高）与 `test_19`（断言浅/深两套 QSS 都含三条作用域规则），`tests/test_ui_tokens.py` 同步断言这两条选择器。

9. 用户反馈「字体与设计稿不是同一种、不清晰」→ 数字字体 `Geist Mono` 在目标机器不存在、静默回退 `Arial`（比例数字、字形不同），应用级字号 `9pt`=12px 小于设计稿 13px。改为随程序打包设计稿同款 `Inter-VF.ttf` / `NotoSansSC-VF.ttf` 并在启动时注册；财务列改用 `ui.tokens.numeric_font()`（Inter + `tnum` 等宽），发票号码列 11px、其余财务列 12px；应用级默认字号改为 13px（后续 P2 又抬到 14px，理由与实测见 `字体与界面对应关系.md` §6.5）。两 VF 均为 SIL OFL 1.1，许可证随包分发。

10. 用户反馈「Windows 下字体看上去有点不清晰」→ 根因是打包的 Noto Sans SC 由自动工具生成、**不含 TrueType hinting 指令**（`fpgm`/`prep`/`cvt` 三表皆无），96 DPI 1x 屏上小字横画只能摊在两行像素上。三步处置：①`text_muted` 对比度 2.97:1 → 4.97:1（深色 4.18 → 5.29）；②`caption` 11 → 12px（同时回到设计稿表头实测值）；③中文栈首位改为系统 `Microsoft YaHei UI`（雅黑逐字形调过指令，12px 边缘像素 42.8% vs Noto 47.9%）。P2 保留 `base` = 14px。连带把裁切线数字框 60 → 64px、前缀空格 2 → 1，修掉雅黑下「左 0 mm」末位 `m` 被削的问题。实测与冲突说明见 `字体与界面对应关系.md` §6.1–§6.6。

## 4b. 第二轮「逐一核实」：按 `req/ui/` 原型图逐区域像素比对后修复

> 方法：以 `01-主工作台-完整界面.png`（2880×1800 = 1440×900 ×2）为几何/形状基线，
> `00` 为设计系统基线，`04` 为深色基线，`02` 为重命名对话框基线，`03` 为状态/弹窗基线。
> 离屏 `QWidget.grab()` 生成 `app_light.png` / `app_dark.png`（1440×900）与 `dlg_app.png`（1136×686），
> 用 PIL 逐行/逐列扫描色块边界、量化几何，再与设计稿同坐标比对。
> 注：`05/06-运行校验-*.png` 经核实是**改造前的历史运行截图**，仅用于色值采样，不作几何基线。

| # | 差异（设计稿 vs 改前） | 修复 | 实测证据 |
| --- | --- | --- | --- |
| 9 | 表头左对齐、11px、金额列头无强调；设计稿居中、12px、金额列头主色蓝加粗 | `file_list.py` 新增 `_apply_header_colors()`，表头居中、金额列 `#1A56A8` 加粗，首列眼睛图标 | 表头 `#F8FAFC`、列头居中 |
| 10 | 数据行高偏紧、金额列黑色；重复行整行无琥珀底、重复色偏橙 | 行高 38、金额列主色蓝等宽粗体、重复行 `#FEFBF4` 整行 + `#B7791F` 号码/文件名 + ` · 重复` 后缀；并修「首次出现不标记」语义（仅第 2 张起高亮） | 行 1 号黑、行 2 号 `(183,121,31)` 琥珀 + 后缀 |
| 11 | `_apply_financial_cell_style(row)` 只作用于循环残留末行（等宽字体 bug） | 改为无参 `_apply_financial_cell_style()` 遍历全部行 | `test_08` TypeWriter + col(3,4,8) 右对齐 |
| 12 | 芯片偏蓝（accent_tint 底 + accent 字、宽 56）；警告 chip 无 ⚠ 前缀 | `statusChip` 改 `hover_bg` 底 + `text_secondary` 字、padding 12；`warningChip` 11px + ⚠ 前缀 | 计数芯片 52×22（设计同）、警告芯片 104×22（设计 103×23） |
| 13 | `QSplitter` handle 显示为灰色带 | QSS `QSplitter::handle` 透明、宽 16px | x=991..1006 采样为 `(244,246,249)` 页面底色 |
| 14 | 纸张方向 QRadioButton 圆点、处理模式 QComboBox；设计稿为分段控件 | `shell.py` 改用可 checkable 分段按钮组（蓝底白字选中段） | 分段外框 28–30px、实心段 24px |
| 15 | 参数卡双重边框（子卡嵌进 settings_card）；勾选框散落在输出条 | 参数卡改单层分组；「一式两份/合并后打开/合并后打印」移入参数卡底部勾选胶囊 | 单层卡片、胶囊 92/96/96 高 26 |
| 16 | 操作条按钮短文案 + SVG 图标、无竖线分组；设计稿纯文字长文案 + 分组竖线 | 改长文案（添加文件/删除选中/清空全部/上移/下移/批量重命名/导出列表）、去图标、竖线分组、右端灰字提示 | 按钮高 30、x 26/126/216/316/381/455/558 |
| 17 | 输出条固定 96px、进度条/回执常驻占位；设计稿两段式、进度仅进行中显示 | 输出条改「路径行 + 行内回执/进度」；`inlineProgress` 高 4、仅进行中显示；主按钮 152×40 | 输出条 800..874 |
| 18 | 预览卡有独立「启用实时预览」行、头部文案 `(添加文件后自动更新)` | 去独立行、头部改「（4 个文件）」、底部加绿色「实时预览：开」 | 预览卡 111..429 |
| 19 | 上下文条 `drop_label` 用 16px/700 titleLabel，明显偏大 | 改 14px 常规 | 上下文条 50px |
| 20 | 深色模式表头文字不可读（FileListPanel 自建 `AppTheme()` 探测到浅色） | `FileListPanel.apply_theme(dark)` + `MainWindow._sync_list_theme()` 同步主窗口主题 | 深色表头 `#A3B1C2`、金额列 `#4A86D8`、重复行 `#2A2418` |
| 21 | `code/ui/rename_dialog.py` 布局与 `02` 差异大 | 重写四段式（标题栏 / 左 7 票种导航 / 右编辑区 / 使用说明 + 统计 + 按钮），字段芯片 7 列单行 106×30、通用蓝底/专属白底、保存描边/执行实心、示例结果 success 色 | `dlg_app.png` 1136×686；芯片色 `#EAF1FB` / `#F8FAFC` |

自动回归（本轮收尾复跑）：
`python -m unittest tests.test_ui_shell tests.test_ui_tokens tests.test_ui_merge_behavior tests.test_invoice_field_registry tests.test_rename_rules_by_type` → **Ran 85 tests, OK**。
全量回归（12 个测试模块、需显式 `PYTHONPATH=.pylibs;code` 以避免 `fitz` 导入顺序问题）：
**Ran 207 tests, OK（skipped=3）**。
浅色主窗口关键区域众数色与设计稿逐点一致：页面间隙 `#F4F6F9`、台账头部 `#FFFFFF`、表头 `#F8FAFC`、状态栏 `#F8FAFC`。原记录中的「标题栏 `#FFFFFF`、上下文条 `#EAF1FB`」两处已随标题栏/上下文提示条合并进状态栏而失效（对应区段已从窗口结构中删除）。

## 5. 与设计稿的差异（剩余，已逐项核实）

1. **重命名对话框为整窗 1136×686，设计稿 02 是「画布内嵌白卡」**（卡片 x=29..1084 / y=28..647，四周约 29px `#F4F6F9` 留白 + 阴影）。属原型图呈现方式差异：真实 Qt 对话框无外层画布；强行缩小可用区会使 7 枚 106px 字段芯片（总宽约 802 + 间距）溢出，故保留整窗。
2. **重命名对话框字段芯片为 7 枚，设计稿 02 为 8 枚**：设计稿第二行多一枚 `{税额}`，但 `code/core/invoice_field_registry.py` 的 `vat_invoice` 字段集只有 7 项（4 通用 + 商品类型/买方名字/销方名字），且 `InvoiceService.apply_rule()` 只按 `get_fields()` 替换占位符，`{税额}` 永远不解析。加入它会改动 7 个票种字段集与 `tests/test_invoice_field_registry.py` 严格断言、`tests/openspec/.../expected-fields.json` 基线，属业务逻辑变更而非 UI 样式修复 → 不改动，作为设计稿与字段注册表的固有差异记录。
3. **输出条回执文案**：设计稿 01 静态文案为「已就绪 · 合并任务在后台执行，完成后可打印或打开」；应用按运行状态动态显示（如「4 张票据待合并」），语义一致、文案不同。
4. **台账列宽随窗口自适应**，超出时横向滚动；设计稿按 1440×900 固定列宽绘制。
5. **运行截图在离屏模式下无真实发票预览图**（占位空态），真实 PDF 预览需人工用样本文件验证。
6. 设计稿 03 的加载/成功/失败回执、右键菜单、悬停缩略图、帮助/更新弹窗为**多状态说明板**，应用已实现对应组件与回执样式（`test_13`/`test_15`），但未逐一截图逐像素对齐。

## 6. 仍需人工 / 外部环境验证（未完成）

| 项 | 原因 |
| --- | --- |
| 真实拖放 PDF/图片/OFD 与文件夹递归导入 | 需要真实文件与桌面交互 |
| 右键菜单实际弹出、系统默认程序打开、系统打印对话框 | 需要桌面交互 |
| 真实发票的合并预览渲染、缩放与多页显示 | 需要真实发票样本 |
| 检查更新网络请求、更新弹窗与二维码扫描 | 需要外网与显示设备 |
| ~~GUI + SSE 共存实测~~ | **已完成**：源码模式与冻结包均实测 SSE 200，见 §6 / §7 |
| ~~macOS `package_macos.sh` 打包运行~~ | **已完成**：`dist/票易合.app` + ZIP 产出并实测通过，见 §7 |
| Windows `package_win.bat` 打包运行 | 本机为 macOS，无 Windows 主机可执行 |
| 浅色/深色各 51 项完整人工点击走查 | 需人工按矩阵逐项点击确认；本轮已完成结构/像素级自动核实（见 4b），但点击交互仍需人工 |

上述项对应 `tasks.md` 的 6.1 / 6.2 / 6.3。6.1 的**自动核实部分已完成并记入本文件第 4b 节**，但完整人工点击走查未完成，故 6.1 仍不勾选；完成前不应归档本变更。

## 6. MCP 9 Tools 与 CLI 参数回归（对应 `tasks.md` 6.2，已完成）

环境：`./clean_venv/bin/python`（Python 3.14、PySide6 6.11.0、mcp 1.28.1、uvicorn）。

| 项 | 命令 / 方法 | 结果 |
| --- | --- | --- |
| MCP 单元回归 | `PYTHONPATH=code python -m unittest tests.test_mcp_tools` | **Ran 30 tests, OK** |
| Tool 数量与必需参数 | `mcp.list_tools()` 逐项读取 `inputSchema.required` | **9 个**，与改造前一致（见下表） |
| Tool 实调返回结构 | 用 `tests/fixtures/invoices/` 前 3 个 PDF 逐个调用，输出到临时目录 | 9 个全部 `success=True`，返回键集合与改造前完全一致 |
| GUI + SSE 共存 | `python code/main.py --mcp-server --transport sse --host 127.0.0.1 --port 8766`，随后 `curl -H "Accept: text/event-stream" .../sse` | **HTTP 200**；日志 `MCP Server 启动中: name=piaoyihe, version=0.1.15, transport=sse`、`Uvicorn running on http://127.0.0.1:8766` |
| CLI 5 参数解析 | `tests.test_ui_shell.test_13_cli_args_unchanged` | 通过（`--mcp-server --transport sse --host --port --cors-origins`） |

| Tool | 必需参数 | 返回键 |
| --- | --- | --- |
| `merge_invoices` | pdf_paths, output_path, layout | message, output_path, success |
| `extract_invoice_info` | pdf_path | info, message, success |
| `batch_extract_invoice_info` | pdf_paths | message, results, success |
| `batch_rename_invoices` | pdf_paths | dry_run, failed_count, message, renamed_count, renamed_map, skipped_unconfigured_count, success, unrecognized_files |
| `export_invoice_list` | pdf_infos, output_path | message, output_path, success |
| `export_invoice_list_from_paths` | pdf_paths, output_path | message, output_path, success |
| `get_supported_layouts` | — | layouts |
| `get_supported_fields` | — | fields, types |
| `get_server_info` | — | name, version, tools |

> 说明：`get_server_info` 的 `version` 在冻结包中曾回落到兜底值 `0.2.0`（见 §7 缺陷 5），修复后源码与冻结包均返回 `0.1.15`。

## 7. macOS 打包回归（对应 `tasks.md` 6.3，macOS 侧完成）

环境：`./clean_venv/bin/python`（PyInstaller 6.19.0）、`PYINSTALLER_CONFIG_DIR=/tmp/pyi_cache`（默认缓存目录在本机不可写）。

产物：`dist/票易合.app`（COLLECT）+ `dist/票易合_macos_0.1.15.zip`（91 MB）。构建日志 **0 条 ERROR**。

### 7.1 本次打包暴露并已修复的 7 处真实缺陷

| # | 缺陷 | 影响 | 修复 |
| --- | --- | --- | --- |
| 1 | 两份 spec 的 `pathex` 硬编码 `D:\minipro\piaoyihe\...`，且本地打包脚本未调用 `scripts/patch_spec.py` | 打出的包启动即 `ModuleNotFoundError: No module named 'ui'`，GUI 与 MCP 全部不可用 | 两份 spec 的 `pathex` 改为 `[]` 占位；`package_macos.sh` 与 `package_win.bat` 在 pyinstaller 前调用 `scripts/patch_spec.py` 写入当前仓库绝对路径 |
| 2 | `scripts/patch_spec.py` 在 spec 已是当前路径时返回 1 | 打包脚本第二次运行必然失败（`spec 路径修正失败`） | 改为幂等：`pathex=` 存在即视为成功并打印 `Already patched` |
| 3 | `package_macos.sh` 用 `"$APP" -c "import ..."` 校验 MCP 依赖 | 冻结入口不解析 `-c`，必然 `unrecognized arguments: -c`，脚本 exit 1 | 改用项目已提供的 `"$APP" --verify-imports`（输出 `mcp deps ok`），与 `package_win.bat` 一致 |
| 4 | spec 的 `datas` 只列 10 个 SVG，代码实际引用 14 个 | 冻结包缺 `勾选_check-white` / `箭头下_chevron-light` / `文件夹-开_folder-open` / `保存硬盘_save-one`，勾选框、下拉箭头、右键菜单与浏览按钮图标空白 | 两份 spec 改为整目录打包 `('code/res/icons', 'res/icons')`，现包内 21 个图标全部就位 |
| 5 | `code/mcp_server/config.py` 的 `_load_version()` 只拼 `__file__/../version.json` | 冻结后 `__file__` 在 `_MEIPASS/mcp_server/`，而 datas 把 `version.json` 放到 `_MEIPASS/code/`，MCP 静默回落到 `0.2.0` | 改为多候选路径查找（含 `_MEIPASS/code/`、可执行文件目录、cwd），源码与冻结包均正确返回 `0.1.15` |
| 6 | `code/ui/tokens.py` 的 `_icon_url()` / `_fonts_dir()` 用 `__file__` 定位 `res/` | 冻结后指向 `Contents/Frameworks/res/`，Qt 报 `Cannot open file '.../Frameworks/res/icons/...'`（4 条） | 新增 `_res_dir()`：`sys.frozen` 时用 `sys._MEIPASS`，否则回退到源码目录 |
| 7 | spec 的 `hiddenimports` 含 4 个已不存在/不可用的模块（`fitz.fitz`、`core.rename_engine`、`ofd2pdf.ofd_cli`、`ofd2pdf.converter`） | 构建日志 4 条 `ERROR: Hidden import ... not found` 噪声，掩盖真实问题；macOS 无 ofd2pdf wheel 时这两条必然失败 | 删除 `fitz.fitz` / `core.rename_engine`（补入实际存在的 `core.ofd_converter`）；ofd2pdf 两条改为按平台条件化（`try: import ofd2pdf` 成功才加入） |

附带修正：`invoice_tool.spec` 的 `BUNDLE.info_plist` 原本硬编码 `CFBundleShortVersionString = 1.0.0`，改为从 `code/version.json` 读取（现为 `0.1.15`）；`FONT_MONO_STACK` 去掉目标机不存在的 `JetBrains Mono` / `Consolas` / `Cascadia Mono`，只保留随包分发的 `Inter` 与 `Noto Sans SC`，消除启动时 `Populating font family aliases` 告警。

### 7.2 冻结包实测

| 项 | 方法 | 结果 |
| --- | --- | --- |
| 依赖导入 | `票易合 --verify-imports` | `mcp deps ok` |
| CLI 参数 | `票易合 --mcp-server --help` | 5 个参数正常列出 |
| 版本号 | `PlistBuddy -c "Print :CFBundleShortVersionString"` / MCP 日志 | 均为 `0.1.15` |
| SSE 服务 | `票易合 --mcp-server --transport sse --host 127.0.0.1 --port 8796` + `curl` | **HTTP 200**，日志 `version=0.1.15` |
| GUI 启动 | `QT_QPA_PLATFORM=offscreen 票易合` | 进程存活，日志无 `Traceback` / `Cannot open file` / 字体告警 |
| 图标完整性 | `ls dist/票易合.app/Contents/Resources/res/icons` | 21 个，含此前缺失的 4 个 |
| 源码回归 | `tests.test_ui_tokens tests.test_font_alignment tests.test_ui_shell tests.test_ui_merge_behavior tests.test_mcp_tools` | **Ran 73 tests, OK** |

### 7.3 未完成项

- **Windows 侧未验证**：`package_win.bat` 已按同一口径修复（补 `patch_spec.py` 调用），但本机为 macOS，无法执行打包与「启动/合并/预览/重命名/导出」回归。
- **DMG 未产出**：本机沙箱禁止 `hdiutil create`（`目录非空` / `操作不被允许`，最小目录与 `pkill diskimages-helper` 均无效），属环境限制而非脚本缺陷；`.app` 与 ZIP 不受影响，CI `.github/workflows/build.yml` 已对 DMG 失败做 3 次重试并降级为 warning。
- **spec 变更偏离任务原文**：6.3 原写「无需改动 spec 时确认 `invoice_tool*.spec` 未变更」，实际必须改动（缺陷 1/4/7），已在 `tasks.md` 6.3 记录该偏差。

