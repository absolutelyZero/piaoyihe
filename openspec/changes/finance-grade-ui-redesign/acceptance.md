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
| `python -m unittest tests.test_ui_shell -v` | 16 项通过（五段式结构、9 列、按钮层级、配置加载、状态同步、重复告警、弹窗、CLI、51 项矩阵） |
| `python -m unittest tests.test_ui_merge_behavior -v` | 3 项通过（裁切线开关、零页边距、PDF/图片混合合并） |
| 既有业务回归（11 个模块，预导入 PySide6 以避免 fitz/Qt 导入顺序导致的段错误） | **169 项通过，0 失败，0 错误，3 跳过** |

覆盖到的既有规范：`divider-visibility`、`image-merge-support`、`per-type-rename-rules`、`mcp_server.tools`、`invoice_service`、`ofd_converter`、字段提取器回归。

真实运行时界面截图（浅色 / 深色 / 重命名弹窗）由 `QT_QPA_PLATFORM=offscreen` + `QWidget.grab()` 生成并与 `req/ui/01`、`02`、`04` 逐块核对，归档为 `req/ui/05-运行校验-浅色.png`、`06-运行校验-深色.png`、`07-运行校验-重命名.png`。

## 2b. 字体对齐专项验收（本轮）

按 `字体与界面对应关系.md` 完成 5 项字体修正，新增 `tests/test_font_alignment.py`（12 项）：

| 修正项 | 结果 |
| --- | --- |
| 1 字重/字号常量集中定义，QSS 无魔法数字 | `FONT_WEIGHT` / `FONT_SIZE` / `DESIGN_DISPLAY_SIZE` 落地；QSS 45 处 `font-size`、19 处 `font-weight` 全部改为常量引用；Bold 20px 明确标注「设计稿展示用，界面不消费」，未加入 QSS |
| 2 表头字体双来源 | `QHeaderView::section` 移除 font-*；统一由 `tokens.header_font()` 生成 11px / Noto Sans SC / Regular，仅金额列 Bold + 主色（实测 9 列均 11px，仅 col3 加粗） |
| 3 内联 `font-size` 清理 | `main_frame.py` 9 处逐控件 `setStyleSheet` 删除，改为 `helpText` / `qrcodeHint` / `qrcodePlaceholder` / `hSeparator` 的 objectName + QSS 绑定；旧版遗留方法与注释一并清理，全项目已无逐控件 `font-*` 内联样式 |
| 4 数字展示位统一 Inter + tnum | 纯数字/金额/版本号/缩放/示例结果、含数字的次级文本位（状态栏/页码/每页张数/重复计数/记录数）、数字输入控件（SpinBox / 路径框）全部纳入 `apply_numeric_text_fonts()`；中文经 `setFamilies` 回退 Noto Sans SC；中文规则输入框、字段芯片、中文下拉保持中文栈 |
| 5 QSS 与 setFont 冲突 | 6 类冲突逐项消除，清单见 `字体与界面对应关系.md` 第 4 节；关键机制：QSS 通用 `QLabel` / 容器 / 表单规则不再声明 `font-family`（否则覆盖 `setFont()` 导致 `tnum` 失效），默认字体由 `app.setFont()` 唯一提供 |

**关键回归修复**：启用 `Inter+tnum` 后 20 位发票号码在 11px 下实测宽 140px，叠加 delegate 文本边距后 151px 列会触发省略号。收紧单元格内边距 6→4px 并把发票号码列 151→162px（路径列 Stretch 吸收，9 列结构与总宽不变），放大截图确认 `24310000000017846321` 完整显示、无省略号。标题栏 `v0.1.15` 完整显示。

**最终回归**：12 个测试模块合计 **184 项通过，0 失败，0 错误，3 跳过**。浅色/深色/弹窗三张离屏截图确认无中文方框、数字字形一致、小数点对齐、无文字裁切或控件重叠。

## 3. 51 项功能保留矩阵（自动证据）

| 组 | 项数 | 证据 | 结论 |
| --- | --- | --- | --- |
| A 窗口框架 | 6 | `test_01` 五段 objectName、`test_16` 标题/版本/帮助/进度属性 | 通过 |
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
5. 台账空白区过大、投放带偏矮 → 投放带与表格共享剩余空间；浅色/深色截图复查无重叠、无裁切。
6. 回执标签在深色主题下对比不足 → 信息态文字改用 `text_primary`。
7. 输出提交条固定 76px 导致主按钮下半部被回执条裁切 → 提高到 96px，浅色/深色复查「合并 PDF」完整可见。
8. `res/icons` 图标固定 `#333` 描边在深色背景下几乎不可见 → `shell.tinted_icon_label()` 渲染时改为中性灰蓝 `#8A97A8`，复用仓库现有 SVG，不新增资源。
9. 用户反馈「字体与设计稿不是同一种、不清晰」→ 数字字体 `Geist Mono` 在目标机器不存在、静默回退 `Arial`（比例数字、字形不同），应用级字号 `9pt`=12px 小于设计稿 13px。改为随程序打包设计稿同款 `Inter-VF.ttf` / `NotoSansSC-VF.ttf` 并在启动时注册；财务列改用 `ui.tokens.numeric_font()`（Inter + `tnum` 等宽），发票号码列 11px、其余财务列 12px；应用级默认字号改为 13px。两 VF 均为 SIL OFL 1.1，许可证随包分发。

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
浅色主窗口 6 个关键区域众数色与设计稿逐点一致：标题栏 `#FFFFFF`、上下文条 `#EAF1FB`、页面间隙 `#F4F6F9`、台账头部 `#FFFFFF`、表头 `#F8FAFC`、状态栏 `#F8FAFC`。

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
| GUI + SSE 共存实测 | 本机缺少 `mcp` / `uvicorn` 包，无法启动 SSE 服务 |
| Windows `package_win.bat` 与 macOS `package_macos.sh` 打包运行 | 本机无 PyInstaller，且无 macOS 环境 |
| 浅色/深色各 51 项完整人工点击走查 | 需人工按矩阵逐项点击确认；本轮已完成结构/像素级自动核实（见 4b），但点击交互仍需人工 |

上述项对应 `tasks.md` 的 6.1 / 6.2 / 6.3。6.1 的**自动核实部分已完成并记入本文件第 4b 节**，但完整人工点击走查未完成，故 6.1 仍不勾选；完成前不应归档本变更。
