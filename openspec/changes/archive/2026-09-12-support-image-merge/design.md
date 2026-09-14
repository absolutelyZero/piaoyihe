## Context

当前应用仅支持 PDF 文件：拖放与文件对话框只接受 `.pdf`，加载线程通过提取器解析发票字段，合并管线 `PDFHandler.merge_pdfs` 用 `fitz.open()` 打开每个源文件。图片票据无法进入工作流。本次变更让应用支持 `.png`、`.jpg`、`.jpeg` 三种图片文件的拖入、列表展示、单文件预览与混合合并，图片不提取字段、不参与批量重命名。

现状关键路径：
- 拖放过滤：[main_frame.py 的 dropEvent](file:///Users/xieyonggao/Documents/self/minipro/invoiceTool/code/ui/main_frame.py#L2618-L2645)
- 文件信息构建：[file_list.py 的 build_file_info](file:///Users/xieyonggao/Documents/self/minipro/invoiceTool/code/ui/file_list.py#L779-L813)
- 合并排版：[pdf_handler.py 的 _merge_files_into_doc](file:///Users/xieyonggao/Documents/self/minipro/invoiceTool/code/core/pdf_handler.py#L157-L374)
- 批量重命名：[invoice_service.py 的 batch_rename](file:///Users/xieyonggao/Documents/self/minipro/invoiceTool/code/core/invoice_service.py#L93-L133)

## Goals / Non-Goals

**Goals:**
- 支持 `.png`、`.jpg`、`.jpeg` 三种图片文件的拖入、目录递归收集与文件对话框选择
- 图片文件跳过发票字段提取，在列表中以空字段展示，统计/导出/排序不报错
- `merge_pdfs` 支持 PDF 与图片按列表顺序混合合并，沿用现有布局、边距、旋转、裁切线配置
- 合并预览与单文件预览浮窗对图片文件可正常显示
- 批量重命名跳过图片文件，并提示被跳过的数量

**Non-Goals:**
- 不对图片做 OCR 或发票字段识别
- 不支持图片编辑、旋转等加工功能
- 不扩展其它图片格式（bmp/webp/tiff 等）
- 不改变 PDF 文件的既有行为

## Decisions

### 决策 1：图片类型判定集中到 `core/pdf_handler.py`
在 `pdf_handler.py` 增加模块级常量 `IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg'}` 与 `is_image_file(path)` 辅助函数，供 `main_frame`、`file_list`、`invoice_service`、`merge_pdfs` 复用，避免各文件各自维护扩展名列表导致不一致。

### 决策 2：加载阶段按文件类型分流
`FileLoadWorker` 保持调用 `build_file_info(pdf_handler, path)`，在 `build_file_info` 内部先判定图片：图片走独立分支，不调用 `extract_amount`/`extract_invoice_date`/`extract_invoice_code`/`extract_tax_amount`，字段填缺省值（金额/税额 `0.0`，日期/发票号码空字符串），`name`/`path`/`mod_time`/`size` 照常填充。
- 备选：在 `FileLoadWorker` 分流 — 不采用，避免把类型逻辑散布到线程层，且 `add_file`（同步入口）同样需要该分支。

### 决策 3：合并管线用 `Page.insert_image` 内联处理图片源
在 `_merge_files_into_doc` 中，把「单个源文件」抽象为「一个或多个排版单元」：
- PDF 源：按现有逻辑逐页 `show_pdf_page`（含注释/监制章复制）
- 图片源：作为单个单元，用 `fitz.Pixmap(path)` 打开，按现有"图像模式"的缩放公式（`cell - gap`、`min(scale_x, scale_y)`、居中）计算目标矩形，`current_page.insert_image(target_rect, pixmap=pix)` 插入；`rotate == 90` 时复用现有 PIL 旋转逻辑。

页创建、分割线、裁切线、批次临时文件等外层逻辑完全复用，无需改动。
- 备选 A：图片先转成临时 PDF 页再走统一 PDF 路径 — 不采用，徒增临时文件管理与失败点，且多一层磁盘 IO。
- 备选 B：仅用 `insert_image(filename=...)` — 不采用，`rotate` 场景与行列复用现有 pixmap 路径更一致。

### 决策 4：单文件预览浮窗对图片直接加载
`PreviewPopup.show_preview` 先判定图片：图片用 `QPixmap(path)` 直接加载并缩放显示，PDF 保持现有 `fitz` 渲染路径。避免 `fitz.open()` 对图片抛异常。

### 决策 5：批量重命名在提取前显式跳过图片
`batch_rename` 循环内先判定 `is_image_file`：图片直接计入新增返回键 `skipped_image_count`，不做提取、不生成新名、不写入 `renamed_map`。`main_frame._perform_batch_rename` 读取该键并追加提示「跳过 N 个图片文件」。
- 现状：图片走 `extract_all_invoice_info` 返回 `None` 落入 `unrecognized_files`，语义是"未能识别"，与用户要求的"明确跳过"不符。

### 决策 6：入口过滤统一扩展
- `dropEvent`（含目录递归）的文件后缀过滤由 `.pdf` 扩展为 PDF + 三种图片
- `_on_add_file` 文件对话框过滤器改为 `"PDF文件 (*.pdf);;图片文件 (*.png *.jpg *.jpeg)"`

## Risks / Trade-offs

- `fitz.Pixmap(path)` 对个别 JPEG 变体可能解析失败 → 失败时回退：用 PIL 打开并转 PNG bytes 再建 `fitz.Pixmap`；仍失败则跳过该文件并在日志输出，不影响其它文件合并
- 大尺寸图片的内存占用 → 直接插入目标矩形而非先整页栅格化，且沿用现有分批合并机制，单批内图片数量受 `batch_size` 控制
- 图片空字段参与排序/统计/导出 → 已确认 `sort_key_map` 使用 `.get()` 缺省、统计求和为 `0.0`、Excel 导出按现有字段结构处理，空值安全
- 预览浮窗对超大图片的缩放开销 → 与 PDF 预览一致，仅加载首张显示图并按浮窗尺寸缩放，可接受
