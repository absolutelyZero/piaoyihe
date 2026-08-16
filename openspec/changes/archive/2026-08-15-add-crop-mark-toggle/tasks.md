## 1. UI 层：增加裁切线复选框

- [x] 1.1 在 `_create_mode_order_widget` 中，打印顺序下拉框后增加分隔线
- [x] 1.2 在分隔线后增加"裁切线"复选框（`self.crop_mark_checkbox`），默认未选中
- [x] 1.3 复选框的 `stateChanged` 信号连接到 `_on_config_changed`

## 2. 配置层：保存/加载裁切线状态

- [x] 2.1 `_get_current_layout` 中返回 `show_crop_marks` 字段
- [x] 2.2 `_load_config` 中读取 `layout_config.show_crop_marks` 并设置复选框
- [x] 2.3 旧配置兼容：无 `show_crop_marks` 时默认 False

## 3. PDF 处理层：绘制裁切线

- [x] 3.1 `_merge_files_into_doc` 中读取 `layout_config.show_crop_marks`
- [x] 3.2 在新页面创建时调用 `_draw_crop_marks` 方法
- [x] 3.3 新增 `_draw_crop_marks` 方法，绘制四条边页边距虚线
- [x] 3.4 裁切线从页面边缘延伸至内容区域边缘，使用灰色虚线样式（dash=5, gap=3, width=0.5）

## 4. 验证

- [x] 4.1 编译检查：`python3 -m py_compile code/ui/main_frame.py code/core/pdf_handler.py`
- [ ] 4.2 运行程序：裁切线复选框显示在打印顺序后
- [ ] 4.3 勾选裁切线后合并 PDF，输出文件包含四边虚线
- [ ] 4.4 取消勾选后合并，输出文件无虚线
- [ ] 4.5 重启程序，裁切线状态保持
- [ ] 4.6 预览中也显示裁切线