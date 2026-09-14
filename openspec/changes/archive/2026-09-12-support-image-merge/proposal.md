## Why

当前应用仅支持拖入 PDF 发票文件（[main_frame.py 的 dropEvent](file:///Users/xieyonggao/Documents/self/minipro/invoiceTool/code/ui/main_frame.py#L2618-L2645) 只过滤 `.pdf`），合并管线 `PDFHandler.merge_pdfs` 也只能处理 PDF。用户的报销材料中常包含图片类型的票据（拍照/截图的开票照片等），无法直接拖入合并，需要先手动转成 PDF，体验割裂。本次变更让应用直接支持拖入图片文件，并支持 PDF 与图片混合合并。

## What Changes

- 拖放与文件对话框支持图片类型文件：`.png`、`.jpg`、`.jpeg`，与 PDF 文件混合拖入；拖入目录时同样递归收集上述类型文件。
- 图片文件**不提取发票字段**：不执行金额、发票号码、日期等字段提取，在文件列表中以空字段展示（金额、税额、日期、发票号码留空），文件列表与统计信息处理需兼容无字段文件。
- 合并管线支持混合合并：`PDFHandler` 将图片按原图比例渲染进目标页面单元格（沿用现有布局、边距、裁剪线、旋转配置），图片与 PDF 页面按列表顺序混合排版。
- 合并预览（[`_update_preview`](file:///Users/xieyonggao/Documents/self/minipro/invoiceTool/code/ui/main_frame.py#L1829)）与单文件预览浮窗（[`PreviewPopup.show_preview`](file:///Users/xieyonggao/Documents/self/minipro/invoiceTool/code/ui/file_list.py#L73-L124)）支持图片文件展示。
- 文件加载工作线程 `FileLoadWorker` 与 `build_file_info` 对图片文件走"跳过字段提取"分支。
- **批量重命名跳过图片文件**：`batch_rename` 对图片类型文件不生成新文件名、不参与重命名，结果统计与提示中体现被跳过的图片数量。
- 合并按钮/导出列表等依赖字段的逻辑需对图片文件提供合理缺省值，避免报错。

## Capabilities

### New Capabilities
- `image-merge-support`: 覆盖图片文件的拖入与选择、加载（跳过字段提取）、列表展示、单文件预览、混合合并排版及合并预览全链路能力。

### Modified Capabilities
<!-- 项目 openspec/specs/ 目录当前为空，暂无既有 spec -->

## Impact

- `code/ui/main_frame.py`：`dropEvent`/`dragEnterEvent` 文件类型过滤、`_on_add_file` 文件对话框过滤器、`_update_preview` 预览管线。
- `code/ui/file_list.py`：`build_file_info` 图片分支、`PreviewPopup.show_preview` 图片渲染、表格展示对空字段的兼容。
- `code/ui/file_load_worker.py`：加载逻辑需区分文件类型，图片跳过字段提取。
- `code/core/pdf_handler.py`：`merge_pdfs`/`_merge_files_into_doc` 增加图片源文件处理（PyMuPDF `insert_image`），`extract_*` 系列方法需对图片返回缺省值。
- `code/core/invoice_service.py`：`batch_rename` 跳过图片类型文件，返回结果补充被跳过的图片数量。
- `code/ui/merge_worker.py`：确认合并参数传递路径无需改动，图片由 `merge_pdfs` 统一处理。
- 依赖：PyMuPDF 已具备 `insert_image` 能力，Pillow 已用于图像模式渲染，无需新增依赖。
