## 1. UI 层：移除旧裁切线复选框

- [ ] 1.1 从模式与排序卡片中移除裁切线复选框（`self.crop_mark_checkbox`）、分隔线及相关代码

## 2. UI 层：在布局卡片中新增裁切线设置

- [ ] 2.1 在布局卡片页边距 spinbox 后增加分隔线
- [ ] 2.2 增加"显示轮廓裁切线"复选框，默认未选中
- [ ] 2.3 增加"左" spinbox（范围 0~50mm，默认 0）
- [ ] 2.4 增加"右" spinbox（范围 0~50mm，默认 0）
- [ ] 2.5 复选框和 spinbox 的变更信号连接到 `_on_config_changed`

## 3. 配置层：更新保存/加载

- [ ] 3.1 `_get_current_layout` 返回 `crop_mark_left`、`crop_mark_right` 字段
- [ ] 3.2 `_load_config` 读取裁切线设置并恢复控件状态
- [ ] 3.3 `_on_margin_changed` 改为 `_on_config_changed`（如需要）

## 4. PDF 处理层：重构裁切线绘制

- [ ] 4.1 `_draw_crop_marks` 改为仅绘制左右两侧垂直线
- [ ] 4.2 参数改为接收 `crop_mark_left`、`crop_mark_right`（mm），内部转换为 pt
- [ ] 4.3 `_merge_files_into_doc` 调用处传递新的裁切线参数

## 5. 验证

- [ ] 5.1 编译检查
- [ ] 5.2 运行程序：裁切线设置在布局卡片中显示
- [ ] 5.3 设置左右裁切线距离，合并 PDF 验证效果
- [ ] 5.4 重启程序，设置保持