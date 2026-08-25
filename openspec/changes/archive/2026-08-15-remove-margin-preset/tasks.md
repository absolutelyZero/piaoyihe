## 1. 移除预设关联字段和方法

- [x] 1.1 移除 `_is_updating_margin_preset` 标志位（`__init__` 中的第 76 行）
- [x] 1.2 移除 `_on_margin_preset_changed` 方法（第 1797~1831 行）
- [x] 1.3 移除 `_on_reset_margins` 方法（第 1833~1856 行）

## 2. 简化 `_on_margin_changed`

- [x] 2.1 移除预设匹配循环、`_is_updating_margin_preset` 标志位设置、`margin_preset_combo` 操作
- [x] 2.2 简化为仅调用 `self._on_config_changed()`

## 3. 清理 `_create_margin_widget` UI

- [x] 3.1 移除预设标签、预设下拉框（`margin_preset_combo`）及其样式代码
- [x] 3.2 移除恢复默认按钮（`reset_margin_btn`）及其信号连接

## 4. 清理配置加载代码

- [x] 4.1 移除配置加载中 `_on_margin_changed()` 的调用（第 2846 行），改为直接调用 `_on_config_changed()`
- [x] 4.2 移除 `self.margin_preset_combo.setCurrentText('默认')` 引用（第 2853、2888 行）

## 5. 验证

- [x] 5.1 编译检查：`python3 -m py_compile code/ui/main_frame.py`
- [ ] 5.2 运行程序：四个边距输入框正常显示，预设下拉框和恢复默认按钮已消失
- [ ] 5.3 修改边距值，右侧预览实时刷新
- [ ] 5.4 重启程序，之前保存的边距配置正确加载