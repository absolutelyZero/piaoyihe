## 1. 修改 `_draw_crop_marks` 方法

- [x] 1.1 上边裁切线：添加 `if margin_top > 0:` 判断
- [x] 1.2 下边裁切线：添加 `if margin_bottom > 0:` 判断
- [x] 1.3 左边裁切线：添加 `if margin_left > 0:` 判断
- [x] 1.4 右边裁切线：添加 `if margin_right > 0:` 判断

## 2. 验证

- [x] 2.1 编译检查：`python3 -m py_compile code/core/pdf_handler.py`
- [ ] 2.2 将某边距设为 0，勾选裁切线，输出 PDF 中该边无裁切线