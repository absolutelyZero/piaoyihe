# Design

## Context

现状（见 proposal.md - Why）：

- 提取层已经是策略模式：`code/core/invoice_extractors/factory.py` 按票面关键词从 7 个提取器里挑一个，`base.py` 定义统一的 8 个抽象字段（`amount`、`invoice_date`、`invoice_type`、`product_type`、`buyer_name`、`seller_name`、`invoice_code`、`tax_amount`），`extract_all()` 把它们打包成一个字典返回。`PDFHandler.extract_all_invoice_info` 是这个字典的唯一出口。
- 重命名层是单规则：`InvoiceService.RENAME_FIELD_MAPPING` 一份全局中文→键映射，`apply_rule(rule, file_info)` 做占位符替换，`batch_rename` 对列表里每个文件套同一条 `rule`；`config.json` 只有一个字符串 `rename_rule`。
- UI 层：`RenameDialog.AVAILABLE_FIELDS` 是一份写死的 7 项字段清单，规则读写直接落在 `config.json` 的 `rename_rule`。
- MCP 层：`batch_rename_invoices(pdf_paths, rule, dry_run)` 必填 `rule`；`get_supported_fields` 返回 `InvoiceService.get_available_fields()` 的扁平列表。

约束：

- 中文占位符 `{字段名}` 格式不变，已有规则字符串可原样复用。
- 图片与 OFD 不参与重命名（`skipped_image_count` / `skipped_ofd_count`）的既有行为不变。
- `config.json` 由 `main_frame._save_config` 增量写回（读旧→改若干键→写），未知键不会被清除，因此新增配置键不会丢。
- 不新增第三方依赖。

## Goals / Non-Goals

**Goals:**

- 票种归类与字段集的"唯一事实来源"只有一个模块，GUI / 核心服务 / MCP 三个入口都从它取数据，避免三处各写一份票种清单。
- 重命名执行时**不重复解析 PDF**：票种信息随 `extract_all_invoice_info` 的返回值一起拿到，`batch_rename` 直接据此选规则。
- 旧单规则升级后行为零变化。
- 新增票种特有字段时，只改对应提取器 + 字段注册表两处。

**Non-Goals:**

- 不把特有字段加入文件列表表格列、Excel 导出列或排序/统计口径。
- 不改变 `invoice_type` 的展示值（普票/专票/机动车发票/二手车发票等保持原样）。
- 不引入"票种自动识别失败时的兜底规则优先级链"以外的规则继承机制（无全局默认规则）。
- 不重构 `pdf_handler.py` 的合并逻辑，不触碰 OFD 渲染缓存。

## Decisions

### 1. 票种标识下沉到提取器类属性，随提取结果返回

在 `base.py` 给 `InvoiceExtractor` 加类属性 `TYPE_KEY: str = ""`，7 个子类各自赋值（`vat_invoice` / `train_ticket` / `flight_ticket` / `vehicle_invoice` / `taxi_invoice` / `fixed_amount_invoice` / `toll_invoice`），并在 `extract_all()` 的返回字典里追加 `'invoice_type_key': self.TYPE_KEY`。

- 理由：`batch_rename` 已经在调用 `extract_all_invoice_info(file_path)`，票种标识搭同一个返回值返回即可，无需为选规则再开一次 PDF 或再跑一次工厂匹配（当前 `extract_*` 系列每个方法都会各自 `fitz.open` 一次，重命名路径上已经只有一开了，不能再加）。
- 「普票/专票同属增值税发票」天然成立：两者都由 `CommonInvoiceExtractor` 处理，`TYPE_KEY` 相同，`invoice_type` 展示值仍区分普票/专票。
- 备选：在 `invoice_service` 里用 `invoice_type` 展示值反查票种。否决原因——展示值是文案（"普票""二手车发票"），文案调整会静默改掉重命名行为，且反查表会与提取器清单形成第二份事实来源。

### 2. 字段集注册表独立成模块 `code/core/invoice_field_registry.py`

模块内容：

- `INVOICE_TYPE_KEYS`：7 个票种标识的有序列表。
- `INVOICE_TYPE_LABELS`：标识 → 中文名（增值税发票、火车票、飞机票、机动车发票、出租车发票、定额发票、通行费发票）。
- `TYPE_FIELD_SPECS`：票种标识 → 有序的 `(占位符显示名, file_info 键)` 列表，即该票种可插入的字段集。
- `DEFAULT_RULE_TEMPLATES`：票种标识 → 该票种的默认规则模板串（见决策 10），供对话框在规则为空时预填。
- `ALL_FIELD_KEYS`：所有字段键的并集，供占位符替换时跨票种兜底解析。
- 辅助函数 `get_fields(type_key)` / `get_type_label(type_key)` / `get_default_template(type_key)` / `resolve_field_key(display_name)`。

字段集划分（`发票类型`、`开票日期`、`发票号码`、`金额` 四类全票种通用）：

| 票种 | 额外字段 |
| --- | --- |
| 增值税发票 | 商品类型、买方名字、销方名字 |
| 火车票 | 买方名字（旅客）、车次、出发站、到达站 |
| 飞机票 | 买方名字（乘机人）、销方名字（填开单位/航空公司）、航班号、航空公司 |
| 机动车发票 | 商品类型（车辆类型/品牌）、买方名字、销方名字、车架号 |
| 出租车发票 | 销方名字（出租车公司）、车牌号 |
| 定额发票 | 无 |
| 通行费发票 | 商品类型（路段）、买方名字、销方名字、入口、出口、路段 |

- 理由：新建模块而不是塞进 `invoice_service.py`（已 355 行、职责是业务动作）或 `rename_dialog.py`（UI 不该被 MCP 依赖）。MCP 的 `get_supported_fields` 必须能拿到同一份表，若放在 UI 里就得反向依赖。
- 只列"该票种能实际提取到值"的字段，所以定额发票只有通用四项、火车票不含商品类型——这与 spec「每类票种只提供能提取的字段」一致。
- 备选：把字段集声明为提取器类属性。否决原因——提取器应只关心"怎么提"，字段显示名是重命名域的概念；且 `base.py` 的抽象字段是固定的 8 个，强塞显示名会让提取器承担展示职责。

### 3. 特有字段用 `extract_extra_fields()` 钩子收集，不扩抽象方法

在 `base.py` 增加非抽象方法 `extract_extra_fields(self) -> Dict[str, Any]: return {}`，`extract_all()` 把它合并进返回字典。各票种提取器覆写它返回自己的特有字段键（`train_number`、`departure_station`、`arrival_station`、`flight_number`、`airline`、`plate_number`、`vin`、`toll_entry`、`toll_exit`、`toll_section`）。

- 理由：加抽象方法会破坏"新增票种只需新增一个类"的开闭原则——每个新类都被迫实现一堆返回空值的空方法。钩子默认空实现，未覆写即无特有字段。
- 特有字段的键统一用英文 snake_case，与现有 `buyer_name` 等一致；占位符仍是中文，映射在注册表里。
- 复用现有正则思路（如火车票已有"乘车日期"模式、通行费已从"入口/出口"拼 product_type），新增提取只补充独立字段，不改动现有字段的取值口径。

### 4. 配置结构：新增 `rename_rules`，保留 `rename_rule` 作迁移源

`config.json` 新增 `"rename_rules": { "<type_key>": "<rule>" }`；旧的字符串键 `rename_rule` 保留原样不动。

迁移用纯函数 `migrate_rename_rules(config: dict) -> bool`（放 `invoice_service.py`，不依赖 Qt）：当 `rename_rules` 缺失/非字典且 `rename_rule` 为非空字符串时，把该字符串写进全部 7 个票种，返回 `True`（表示已改动、调用方可选择落盘）；`rename_rules` 已存在时一律不覆盖。

- 理由：纯函数便于单测，也便于 GUI 在加载配置时、以及 MCP 侧未来读取配置时复用同一逻辑。
- 不删除 `rename_rule`：旧版本回退安装时还能读到原规则；同时它可作为"该用户曾经用过的规则"的痕迹。
- 备选：改为一个扁平列表 `[{type, rule}]`。否决原因——字典按 key 查规则是 `batch_rename` 的主路径（N 个文件各查一次），列表需要每次线性扫描或先建索引。

### 5. `apply_rule` 增加票种参数，缺失值保留占位符

签名改为 `apply_rule(rule, file_info, type_key=None) -> Optional[str]`：

1. 按 `type_key` 取该票种字段集；`type_key` 为 `None` 或未知时退回 `ALL_FIELD_KEYS`（兼容旧调用与测试）。
2. 逐个字段查 `file_info`；值为 `None`、缺失、或 `str(value).strip() == ""` → **不替换，保留 `{占位符}` 原文**。
3. 金额这类数值字段：`isinstance(value, (int, float))` 时按 `f"{value:.2f}"` 格式化后替换（含 0.0，因为 0 是有效值而非缺失）。
4. 最后仍走 `sanitize_filename`。

- 理由：spec 要求未识别字段保留占位符，而当前实现是替换成空字符串——这与对话框里"如果发票中没有识别出你选定的模板内容，则会保留相应的模板内容"的既有说明相矛盾，本次顺手对齐。
- 风险提示：提取器现有的兜底文案（如 `CommonInvoiceExtractor` 返回 `"购买方"`/`"销售方"`/`"商品"`）是**非空值**，仍会被替换。本次不把兜底文案改判为"未识别"，否则会连带改变发票列表展示与 Excel 导出的既有取值，超出本次范围。

### 6. `batch_rename` 改为按文件票种取规则

签名改为 `batch_rename(pdf_paths, rules: Dict[str, str], on_progress=None, dry_run=False)`，其中 `rules` 是票种标识 → 规则串（空串表示未配置）。

逐文件流程：跳过图片 → 跳过 OFD → `extract_all_invoice_info` → 取 `info.get('invoice_type_key')` → `rule = rules.get(type_key, "")` → 规则为空则 `skipped_unconfigured_count += 1` 并 `continue` → 否则 `apply_rule` 生成名字 → 冲突处理（沿用现有 `(n)` 后缀逻辑）。

返回值新增 `skipped_unconfigured_count`，其余键保持不变。

- 理由：规则选择必须发生在拿到票种之后，即每个文件一次决策；把规则映射整体传入而不是在 UI 里预先分拣，才能保证"按识别结果选规则"而不是"按文件名选规则"。
- 票种标识缺失（老提取器/异常）时按未配置处理并计入跳过，不抛异常。
- 备选：保留 `rule: str` 主签名再加重载。否决原因——Python 里两个位置参数同名冲突，只会让调用方猜；MCP 侧的兼容在工具层做更清楚（见决策 8）。

### 7. 对话框：票种下拉 + 单票种保存

`RenameDialog` 顶部加票种下拉（7 项，默认选中第一个有非空规则的票种，否则增值税发票）。切换票种时：把当前输入框内容丢弃（不落盘）、载入该票种已存规则（为空则显示默认模板，见决策 10）、按该票种字段集重建字段按钮网格。保存只写 `rename_rules[当前票种]`。执行时发出 `rename_executed(dict)` 携带**全部**票种的**已保存**规则。

- 理由：spec 明确"切换票种前未保存的修改不生效"和"执行使用全部票种已保存的规则"。实现上"切走即丢弃"最简单也最符合直觉，不需要未保存提示弹窗（本 dialog 已有"保存"按钮作为显式动作）。
- **执行拦截只看已保存规则**：7 个票种的已存规则全为空 → 弹提示并中止。界面上的预填模板不算"已配置"，因此不会让"全空却点击执行"变成一次按模板的批量改名。
- 字段按钮网格按需重建（`QGridLayout` 清空重排）而不是全部创建后 `setVisible`，因为不同票种字段数从 4 到 10 不等，3 列布局的行数会变。

### 8. MCP：`rules` 可选、`rule` 兼容；字段查询双向返回

- `handle_batch_rename_invoices(pdf_paths, rule="", dry_run=False, rules=None)`：合并出最终规则映射——先取 `rules`（仅保留 7 个合法票种键、值为字符串），再用非空 `rule` 填充**尚未指定**的票种；两者都没有的票种即未配置，走跳过分支。`rule` 与 `rules` 同时为空时仍返回原来的"重命名规则为空"错误。
- `server.py` 对应改为 `rule: str = ""`, `rules: Optional[Dict[str, str]] = None`，参数顺序保持 `pdf_paths, rule, dry_run, rules` 以免破坏按位置调用的旧客户端。
- `handle_get_supported_fields` 返回 `{"types": [{"key","label","fields":[...]}...], "fields": [...扁平并集...]}`：`types` 是新增的分组视图（spec 要求），`fields` 保留是为不打断既有调用方。

### 9. 测试策略

分两层：**不依赖真实 PDF 的单测**（进 `tests/`，随 CI 跑）+ **基于真实发票目录的实测比对**（独立脚本，本地跑）。

**9.1 单测（不依赖真实 PDF）**

- 注册表与迁移：纯函数级单测（7 票种齐全、字段集不越界、迁移覆盖全票种、已有 `rename_rules` 不被覆盖）。
- 默认模板：单测断言每个票种的模板占位符都落在该票种字段集内（防止模板引用该票种提不到的字段）。
- `apply_rule`：占位符保留、金额 0.0 替换、跨票种字段解析。
- `batch_rename`：混合票种各用各规则、未配置票种跳过并计数、`dry_run` 不落盘、冲突后缀仍生效（用 `Mock` 的 `extract_all_invoice_info` 返回带 `invoice_type_key` 的字典，沿用 `tests/test_invoice_service.py` 现有 Mock 风格）。
- 提取器特有字段：构造含目标文案的 `_text` 直接断言提取结果，不依赖真实 PDF（沿用 `说明文档.md` 记录的"无 PDF 夹具"惯例，`tests/fixtures` 目前只有 `.DS_Store`）。
- MCP：`rules` 单独、`rule` 单独、两者同时三种组合。

**9.2 实测比对（基于真实发票目录）**

样本目录：`D:\minipro\piaoyihe\piaoyihe_test`（**在 git 仓库之外**，不进版本控制）。脚本以路径参数接收，默认指向该目录，换机器时传 `--source-dir` 覆盖即可，不把绝对路径写死进断言。

比对基准：`openspec/changes/per-invoice-type-rename-rules/baseline/expected-fields.json`。该文件由 AI 直接读取每张发票的票面文本整理而成（解析 PDF 内容流与 ToUnicode CMap），逐文件记录期望的票种标识、各字段值以及「哪些字段经票面文本核实」。它是**地面真值**，不是由被测代码生成的，因此能真正发现提取错误。

**脚本不依赖 PyMuPDF**：比对脚本只做两件事——
1. 调用被测的 `PDFHandler.extract_all_invoice_info` 得到实际字段；
2. 与 `expected-fields.json` 逐字段比对，输出差异表。

PDF 文本解析由被测代码自己完成（它本来就依赖 PyMuPDF）；脚本自身只用标准库读写 JSON，因此在任何能运行本应用的 Python 环境下都能执行，不需要额外安装。

**覆盖情况如实标注**：16 个 PDF 中 12 个已解出票面文本，覆盖 **3/7 类票种**——
- 已覆盖：增值税发票（含普票/专票）、火车票（`其他票据/3.pdf`）、飞机票（`其他票据/2.pdf`）
- 未覆盖：机动车发票、出租车发票、定额发票、通行费发票 → 只能靠构造文案的单测验证提取逻辑，实测阶段标注为「未覆盖」

`其他票据/1.pdf` 是无文本层的扫描件，专用于验证「识别不出票种」的降级路径，不作为字段比对样本。`output.pdf`（合并产物）与 `发票1.rar` 排除。

**回归基准**：顶层 7 个文件的文件名本身就是现行规则 `{金额}-{发票类型}-{开票日期}-{发票号码}-{买方名字}-{销方名字}` 的产物。用迁移后的 `vat_invoice` 规则对它们重命名应**幂等**（得到与现有文件名一致的名称），这是「旧配置迁移后行为不变」最直接的验证。

### 10. 默认模板只作用于对话框显示层

`invoice_field_registry.DEFAULT_RULE_TEMPLATES` 存 7 条模板：

| 票种 | 默认模板 |
| --- | --- |
| 增值税发票 | `{开票日期}-{买方名字}-{金额}` |
| 火车票 | `{开票日期}-{车次}-{出发站}到{到达站}` |
| 飞机票 | `{开票日期}-{航班号}-{航空公司}` |
| 机动车发票 | `{开票日期}-{车架号}` |
| 出租车发票 | `{开票日期}-{车牌号}-{金额}` |
| 定额发票 | `{开票日期}-{金额}` |
| 通行费发票 | `{开票日期}-{入口}到{出口}` |

对话框在"该票种无已保存规则"时把模板填入输入框。关键约束：

1. **不落盘**：切换/关闭对话框都不写配置；只有「保存」按钮把输入框内容写进 `rename_rules[当前票种]`。
2. **不参与执行**：`rename_executed` 传的是已保存规则字典；界面显示模板不等于已配置，因此与「未配置规则的票种跳过重命名」天然不冲突。
3. **不加状态位**：采用"只要该票种规则为空就预填"，每次进入/切换都重新判定，无需记录"是否已预填过"。用户清空并保存后再次进入仍会看到模板。
4. **模板来源唯一**：模板与字段集同处一个注册表模块，单测保证模板只引用该票种字段集内的占位符。

- 理由：用户选择的形态是"提供一个可直接采用的起点，但不改变默认不改名的既有语义"。预填即落盘会让新用户一打开重命名就被按模板批量改名，直接推翻 `说明文档.md` 中"默认不会修改文件名，如果要改，就修改上面的内容"这条既有承诺。
- 备选：预填即写入配置并在执行时按模板改名。否决原因——与现有默认行为冲突，且需要推翻 spec 中"全部票种规则为空则不改名任何文件"的场景。
- 备选：预填并在点击执行时按界面内容生效（含未保存）。否决原因——会与"切换票种前未保存的修改不生效"直接矛盾，需要重新划定保存边界，把一个显示层的小功能扩散成保存语义改造。

## Risks / Trade-offs

- [旧规则迁移到全部 7 类会让不该改名的票种也改名] → 这是用户明确选择的"升级后行为不变"；对新用户而言 7 类规则初始为空，不会误改名，只有存量用户会继承。
- [特有字段的正则准确率无法在本次验证] → 提取失败时占位符原样保留在文件名里，用户能肉眼看出未识别，不会静默产生奇怪文件名；`说明文档.md` 中标注各特有字段的识别依据。
- [7 票种 × 多条规则让配置膨胀] → `rename_rules` 只写非空项？否——统一写全 7 个 key（空串），使"未配置"与"配置了空串"语义唯一，避免读取端出现 `KeyError`/缺省差异。
- [`extract_all` 返回体新增键可能影响按固定键集合消费的调用方] → 现有消费方（`file_list.build_file_info`、`export_to_excel`、MCP 提取）都按需取键，不遍历；`export_to_excel` 的列是硬编码的，新增键不进列。
- [`apply_rule` 改为保留占位符会改变个别旧规则的产出] → 仅当字段确实为空时才有差异，且是修正与说明文档矛盾的行为；在 `说明文档.md` 变更记录中写明。
- [对话框切换票种丢弃未保存编辑可能让用户白改] → 保存按钮文案与位置不变，且在说明区新增一行"切换票种前请先保存"。
- [用户误以为看到预填模板就已生效] → 对话框说明区注明"输入框中的模板是建议起点，点击保存后才会用于重命名"；同时执行拦截只看已保存规则，永远不会因为界面上有模板而改名。
- [预填模板引用了该票种提不到的字段，导致文件名里留下占位符原文] → 单测强制校验每条模板的占位符都落在该票种字段集内；且 `apply_rule` 对未识别字段保留占位符原文，问题在文件名上肉眼可见，不会静默出错。

## Migration Plan

1. 应用启动加载配置后调用 `migrate_rename_rules(config)`；返回 `True` 说明发生了迁移，下次 `_save_config` 时自然把 `rename_rules` 落入 `config.json`（`_save_config` 是读-改-写，不会丢其他键）。为避免"用户只是启动一下就改配置"，迁移结果立即随 `_save_config` 落盘，不做额外提示。
2. 对话框打开时读取 `rename_rules`，缺失则按空规则处理（并在界面预填默认模板）；不触发迁移（迁移已在启动时统一做过）。
3. 迁移后 7 个票种都存在规则，因此存量用户升级后**不会**看到预填模板；只有新用户，或主动把某票种规则清空并保存的用户，才会看到对应模板。
4. 回滚：旧版本读不到 `rename_rules` 只会当未知键忽略，仍能读 `rename_rule`，因此降级安装不会崩，只是回到单规则模型。
5. MCP 侧无配置迁移（规则由工具参数传入），完全向后兼容。
