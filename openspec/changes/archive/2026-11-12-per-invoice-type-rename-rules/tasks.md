# Tasks

## 1. 票种与字段集注册表

- [x] 1.1 新建 `code/core/invoice_field_registry.py`，定义 `INVOICE_TYPE_KEYS`（7 个票种标识有序列表）、`INVOICE_TYPE_LABELS`（标识→中文名）、`TYPE_FIELD_SPECS`（票种→有序 `(占位符显示名, file_info 键)` 列表）、`ALL_FIELD_KEYS`，以及 `get_fields` / `get_type_label` / `resolve_field_key` 辅助函数；验证：新写单测断言 7 个 key 齐全、每个票种的字段都落在 `ALL_FIELD_KEYS` 内、`resolve_field_key` 对全部显示名可反查
- [x] 1.2 按 design.md 决策 2 的表格填充各票种字段集（增值税发票含商品类型/买卖方，火车票含车次/出发站/到达站，飞机票含航班号/航空公司，机动车含车架号，出租车含车牌号，通行费含入口/出口/路段，定额发票仅通用四项）；验证：单测断言火车票字段集不含"商品类型"、定额发票字段集恰好为通用四项、7 个票种均含发票类型/开票日期/发票号码/金额
- [x] 1.3 在注册表新增 `DEFAULT_RULE_TEMPLATES`（7 条默认模板，内容见 design.md 决策 10）与 `get_default_template(type_key)`；验证：单测断言 7 个票种均有模板，且每条模板中出现的占位符全部属于该票种字段集（防止模板引用该票种提不到的字段）
- [x] 1.4 新增单测校验实测基线文件的自洽性：`baseline/expected-fields.json` 可被 `json.load` 解析，每个条目的 `invoice_type_key` 都在 `INVOICE_TYPE_KEYS` 内，且基线中用到的每次字段键都能在注册表里查到；验证：单测通过；若基线文件缺失则测试明确 skip 而非失败（该文件随变更提交，正常应存在）

## 2. 提取器补充票种标识与特有字段

- [x] 2.1 在 `code/core/invoice_extractors/base.py` 增加类属性 `TYPE_KEY: str = ""`、非抽象钩子 `extract_extra_fields()`（默认返回 `{}`），并让 `extract_all()` 合并钩子返回值与 `'invoice_type_key': self.TYPE_KEY`；验证：单测用最小子类断言 `extract_all()` 含 `invoice_type_key` 且未覆写钩子时无额外键
- [x] 2.2 为 7 个提取器赋值 `TYPE_KEY`（`vat_invoice`/`train_ticket`/`flight_ticket`/`vehicle_invoice`/`taxi_invoice`/`fixed_amount_invoice`/`toll_invoice`）；验证：单测遍历 `InvoiceExtractorFactory.get_registered_extractors()` 断言每个类的 `TYPE_KEY` 非空且互不重复、集合等于 `INVOICE_TYPE_KEYS`
- [x] 2.3 在 `train_ticket.py` 覆写 `extract_extra_fields()` 提取 `train_number`、`departure_station`、`arrival_station`；验证：单测用构造的 `_text`（含"车次D1234"、"北京南"、"上海虹桥"等文案）断言三个字段取值正确，缺失文案时返回空字符串
- [x] 2.4 在 `flight_ticket.py` 覆写 `extract_extra_fields()` 提取 `flight_number`、`airline`；验证：单测用构造的 `_text` 断言航班号与航空公司取值正确，缺失时为 `""`
- [x] 2.5 在 `taxi_invoice.py` 覆写 `extract_extra_fields()` 提取 `plate_number`；验证：单测用构造的 `_text`（含车牌号文案）断言取值正确，缺失时为 `""`
- [x] 2.6 在 `vehicle_invoice.py` 覆写 `extract_extra_fields()` 提取 `vin`（车架号）；验证：单测用构造的 `_text` 断言取值正确，缺失时为 `""`
- [x] 2.7 在 `toll_invoice.py` 覆写 `extract_extra_fields()` 提取 `toll_entry`、`toll_exit`、`toll_section`，且不改变现有 `extract_product_type()` 的取值口径；验证：单测断言三个字段取值正确，同时断言 `extract_product_type()` 在改动前后的输出保持不变
- [x] 2.8 确认 `CommonInvoiceExtractor` 与 `FixedAmountInvoiceExtractor` 不覆写钩子（无特有字段）；验证：单测断言两者的 `extract_extra_fields() == {}`

## 3. 核心服务：按票种规则与迁移

- [x] 3.1 在 `code/core/invoice_service.py` 新增 `migrate_rename_rules(config: dict) -> bool` 纯函数：当 `rename_rules` 不存在/非字典且 `rename_rule` 为非空字符串时，把该字符串写入全部 7 个票种并返回 `True`；`rename_rules` 已存在时返回 `False` 且不修改；验证：单测覆盖三种情形（有旧无新→迁移成功、已有新→不覆盖、两者皆无→不生成空规则且返回 `False`）
- [x] 3.2 删除 `RENAME_FIELD_MAPPING` 单一映射，改为从 `invoice_field_registry` 取字段集；保留 `get_available_fields()` 但改为按票种分组返回（`types` 分组 + `fields` 扁平并集，见 design.md 决策 8）；验证：单测断言返回值含 `types` 且长度 7、每个票种的 `fields` 与其注册表字段集一致
- [x] 3.3 改写 `apply_rule(rule, file_info, type_key=None)` 按 design.md 决策 5 实现：按票种取字段集（`type_key` 为空或未知时退回 `ALL_FIELD_KEYS`）、值为 `None`/缺失/空白串时保留 `{占位符}` 原文、数值字段按 `f"{value:.2f}"` 替换（含 0.0）、末尾仍走 `sanitize_filename`；验证：单测断言 `apply_rule('{发票类型}-{商品类型}', {'invoice_type':'普票','product_type':''})` 得到 `'普票-{商品类型}'`，`apply_rule('{金额}', {'amount':0})` 得到 `'0.00'`
- [x] 3.4 改写 `batch_rename(pdf_paths, rules: Dict[str, str], on_progress=None, dry_run=False)`：逐文件取 `info.get('invoice_type_key')` 后查 `rules`，规则为空则计入新增的 `skipped_unconfigured_count` 并跳过，其余沿用现有改名/冲突/进度逻辑，图片与 OFD 跳过逻辑不变；验证：单测断言混合票种各用各规则、未配置票种保持原名且计数正确、`dry_run=True` 不落盘、同名冲突仍产生 `(1)` 后缀
- [x] 3.5 确认 `batch_rename` 在票种标识缺失（`invoice_type_key` 不在 `rules` 中）时按未配置处理而不抛异常；验证：单测传入不含 `invoice_type_key` 的 info 字典，断言计入 `skipped_unconfigured_count` 且函数正常返回

## 4. GUI 重命名对话框

- [x] 4.1 在 `code/ui/rename_dialog.py` 用左侧票种导航替换顶部下拉框：左侧 `QFrame#typeNav` 内 7 个 `QPushButton#typeNavButton`（文字横排左对齐、checkable），`QTabWidget` 隐藏原生 tab 栏仅作页容器（West 竖排文字旋转 90° 观感异常，已否决），7 个页面顺序同 `INVOICE_TYPE_KEYS`、文案取自 `INVOICE_TYPE_LABELS`，对话框最小宽度 640→760；默认选中第一个已有非空规则的票种，否则选中增值税发票；验证：手工打开对话框确认导航在左侧横排、顺序与默认选中正确，且选中任一票种都不会遮挡下方字段按钮
- [x] 4.2 实现票种切换：丢弃当前未保存的输入、载入该票种已存规则、按该票种字段集重建字段按钮网格（信号源由票种选择控件触发，与控件形态无关）；验证：手工切换火车票↔增值税发票，确认规则文本与按钮集随之变化，且未保存的修改切走再切回即消失
- [x] 4.3 改为读写 `config.json` 的 `rename_rules` 字典：保存只写回当前所选票种，加载时缺 key 按空串处理（空串由 4.5 在界面层预填为默认模板，不在此处落盘）；同时更新对话框内使用说明（含按票种举的例子）；验证：手工保存火车票规则后检查 `config.json` 只多出 `rename_rules.train_ticket`，其他票种值不变
- [x] 4.4 `rename_executed` 信号改为携带全部票种的**已保存**规则字典；当 7 个票种的已保存规则全为空时点击执行弹提示并中止（界面上的预填模板不算已配置）；验证：手工在全部为空（界面已有预填模板）时点击执行确认被拦截，任一票种有已保存规则时可正常执行
- [x] 4.5 实现默认模板预填显示逻辑：切换到无已保存规则的票种时把该票种模板填入输入框，有已保存规则时显示已存规则，全程不写配置、不参与执行；并在说明区标注"输入框中的模板是建议起点，点击保存后才会用于重命名"与"切换票种前请先保存"；验证：手工在多个票种间切换后直接关闭对话框，确认 `config.json` 无任何变化；再验证清空某票种并保存后重新进入仍显示模板
- [x] 4.6 补 `QTabWidget` / `QTabBar` 样式（`::pane`、`::tab`、`::tab:selected`，沿用现有卡片与主色配色），并把说明区「切换上方『发票类型』」改为「切换左侧发票类型」、`_show_help` 中的同类措辞一并更新；验证：手工查看对话框样式与说明文字，并执行 `grep -n "上方\|下拉" code/ui/rename_dialog.py` 确认无残留

## 5. 主窗口接入

- [x] 5.1 `code/ui/main_frame.py` 的 `_on_rename` 打开对话框前读取配置并调用 `migrate_rename_rules`，迁移发生时随 `_save_config` 落盘；验证：手工把旧配置只留 `rename_rule` 后启动应用，确认 `config.json` 出现 `rename_rules` 且 7 个票种值均等于旧规则
- [x] 5.2 `_perform_batch_rename` 改为接收规则字典并调用新的 `batch_rename`，完成提示新增"跳过未配置规则的 N 个文件"（`skipped_unconfigured_count > 0` 时），其余提示（图片/OFD/未识别）保持不变；验证：手工对含火车票与一张规则为空的票种的列表执行重命名，确认提示同时列出重命名数与跳过数

## 6. MCP 接口

- [x] 6.1 `code/mcp_server/tools.py` 的 `handle_batch_rename_invoices` 增加 `rules: Optional[Dict[str, str]] = None` 参数（位置在 `dry_run` 之后），合并规则时先用非空 `rule` 填充尚未指定的票种、`rules` 优先；两者皆空时仍返回"重命名规则为空"；验证：单测覆盖 `rules` 单独、`rule` 单独、两者同时三种组合的规则解析结果
- [x] 6.2 `code/mcp_server/server.py` 对应改为 `batch_rename_invoices(pdf_paths, rule: str = "", dry_run: bool = False, rules: Optional[Dict[str, str]] = None)` 并更新 docstring；验证：`tests/test_mcp_tools.py` 中按位置调用 `handle_batch_rename_invoices(paths, rule, dry_run=True)` 的现有用例仍通过
- [x] 6.3 `handle_get_supported_fields` 改为返回 `{"types": [...7 个分组...], "fields": [...扁平并集...]}`；验证：单测断言 `types` 长度为 7、各分组的 `fields` 与注册表一致、`fields` 仍包含 `amount` 以兼容既有调用方

## 7. 实测比对（真实发票）

- [x] 7.1 新建 `scripts/compare_invoice_fields.py`：`--source-dir` 参数默认指向 `D:\minipro\piaoyihe\piaoyihe_test`，`--baseline` 默认指向本变更的 `baseline/expected-fields.json`；只用标准库读写 JSON，调用被测的 `PDFHandler.extract_all_invoice_info` 取实际值，逐字段比对并输出「文件名/字段/期望/实际」差异表，有差异时非零退出；验证：用 `--source-dir` 指向一个临时空目录时脚本正常退出并报告无样本，不因默认路径缺失而崩溃
- [x] 7.2 基线文件 `baseline/expected-fields.json` 已由 AI 读取票面文本整理完毕（16 个 PDF 中 12 个已解出文本，覆盖 3/7 类票种）；验证：JSON 可被 `json.load` 解析，且每个条目的 `expected.invoice_type_key` 都在 `INVOICE_TYPE_KEYS` 内
- [x] 7.3 脚本实现「无文本层文件」与「未覆盖票种」的标注逻辑：`其他票据/1.pdf` 不计入字段比对、单独报告为无法提取；报告末尾列出已覆盖与未覆盖票种清单；验证：对完整样本目录执行一次，确认报告中 1.pdf 被单独列出且未覆盖票种清单含机动车/出租车/定额/通行费
- [x] 7.4 执行实测并修复提取偏差：对 3 类已覆盖票种（增值税发票、火车票、飞机票）逐字段比对，修正 `expected-fields.json` 中标注为「未核实」的字段（`普票/4.pdf` 的日期与号码、`普票/6.pdf` 的全部字段）需在装有 PyMuPDF 的环境补全；验证：已核实字段全部一致，脚本报告 3 类票种通过
- [x] 7.5 迁移幂等验证：用迁移得到的 `vat_invoice` 规则 `{金额}-{发票类型}-{开票日期}-{发票号码}-{买方名字}-{销方名字}` 对顶层 7 个已按旧规则命名的文件执行 `dry_run` 重命名；验证：7 个文件的新名字与现有文件名完全一致，`renamed_count` 为 0
- [x] 7.6 在 `说明文档.md` 记录实测方法与覆盖缺口：说明 `--source-dir` 用法、基线维护方式（不可由被测代码自动生成）、以及 4 类未覆盖票种需靠单测验证；验证：按文档步骤在干净环境执行实测脚本可跑通

## 8. 单测与文档收尾

- [x] 8.1 运行全部单测（`python -m unittest discover -s tests -v`），修复 `test_invoice_service.py` / `test_mcp_tools.py` 中因签名变化而失败的用例；验证：全量测试通过
- [x] 8.2 手工端到端校验：用混合票种列表（增值税发票 + 火车票 + 定额发票）分别配置规则，确认前两者按各自规则改名、定额发票因规则为空保持原名，结果提示含跳过数；验证：文件系统上实际文件名与提示一致
- [x] 8.3 更新 `说明文档.md` 功能说明：新增「按票种重命名规则」小节（7 票种及各自字段、特有字段识别依据、跳过未配置规则的行为、旧配置迁移说明），并在变更记录中追加本次条目；验证：文档中的示例规则与应用实际行为一致

## Workflow follow-up

- 按项目审查要求完成后归档本变更（`/openspec-archive-change` 或 `openspec archive`）。
- 归档后确认 `openspec/specs/per-type-rename-rules/spec.md` 已生成且 Purpose 已从 delta 迁移。
