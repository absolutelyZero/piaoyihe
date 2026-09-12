## 1. 图片类型判定

- [x] 1.1 在 `core/pdf_handler.py` 添加 `IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg'}` 常量与 `is_image_file(path)` 辅助函数

## 2. 加载与列表展示

- [x] 2.1 `FileListPanel.build_file_info` 对图片文件跳过字段提取，金额/税额填 0.0、发票号码/开票日期填空字符串
- [x] 2.2 `PreviewPopup.show_preview` 对图片文件用 QPixmap 直接加载缩放显示
- [x] 2.3 验证图片空字段在排序、统计、导出 Excel 场景下不报错

## 3. 合并管线

- [x] 3.1 `_merge_files_into_doc` 支持图片源文件：`fitz.Pixmap` 打开、按单元格等比居中缩放（含 gap）、`rotate == 90` 时 PIL 旋转后 `insert_image` 插入

## 4. 入口过滤

- [x] 4.1 `main_frame.dropEvent` 文件与目录递归收集扩展名为 PDF + 三种图片的文件
- [x] 4.2 `main_frame._on_add_file` 文件对话框过滤器扩展为 PDF 与图片两种过滤器

## 5. 批量重命名跳过图片

- [x] 5.1 `invoice_service.batch_rename` 提取前跳过图片文件，返回结果新增 `skipped_image_count`
- [x] 5.2 `main_frame._perform_batch_rename` 读取 `skipped_image_count` 并在完成提示中追加"跳过 N 个图片文件"

## 6. 验证

- [x] 6.1 功能测试：混合拖入 PDF+图片、预览、合并输出 PDF 与图片混合排版正确
