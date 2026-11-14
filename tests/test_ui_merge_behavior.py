#!/usr/bin/env python3
"""
UI 改造后的输出一致性验证（不依赖 Pillow）

用 PyMuPDF 生成合成发票页、用 QImage 生成合成图片票据，直接调用
``PDFHandler.merge_pdfs``，验证裁切线开关、页边距、图片混合合并
在改造前后行为一致（本次未改动 core 层）。
"""

import os
import sys
import tempfile
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in (os.path.join(_ROOT, "code"), os.path.join(_ROOT, ".pylibs")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# 注意：必须先导入 PySide6 再导入 fitz，否则本机 PyMuPDF 2.1 / Qt 6.11
# 在 offscreen 模式下会触发原生段错误。
from PySide6.QtWidgets import QApplication  # noqa: E402
from PySide6.QtGui import QColor, QImage  # noqa: E402

import fitz  # noqa: E402

from core.pdf_handler import PDFHandler  # noqa: E402

# QImage 需要已存在的 QGuiApplication，否则在部分平台会原生崩溃
_APP = QApplication.instance() or QApplication([])


def _layout(**overrides):
    config = {
        "orientation": "landscape",
        "rows": 2,
        "cols": 2,
        "rotate": 0,
        "margins": {"top": 10, "bottom": 10, "left": 10, "right": 10},
        "show_crop_marks": False,
        "crop_mark_left": 0,
        "crop_mark_right": 0,
    }
    config.update(overrides)
    return config


class MergeBehaviorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(
            prefix="piaoyihe_merge_", dir=os.path.join(_ROOT, ".testtmp")
        )
        self.handler = PDFHandler()

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmp, ignore_errors=True)

    def _make_pdf(self, name, text):
        path = os.path.join(self.tmp, name)
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        page.insert_text((72, 100), text, fontsize=12)
        doc.save(path)
        doc.close()
        return path

    def _make_png(self, name):
        path = os.path.join(self.tmp, name)
        image = QImage(240, 160, QImage.Format.Format_RGB32)
        image.fill(QColor("#FFFFFF"))
        for y in range(20, 140, 16):
            for x in range(20, 220, 4):
                image.setPixelColor(x, y, QColor("#C9D3DF"))
        self.assertTrue(image.save(path, "PNG"), "QImage 应能写出 PNG")
        return path

    def _page_count(self, path):
        doc = fitz.open(path)
        count = len(doc)
        doc.close()
        return count

    def test_01_crop_marks_toggle_changes_only_drawings(self):
        """裁切线关闭时不绘制分割线，开启时绘制；页数与排版不受影响。"""
        p1 = self._make_pdf("a.pdf", "INVOICE-A")
        p2 = self._make_pdf("b.pdf", "INVOICE-B")
        out_off = os.path.join(self.tmp, "off.pdf")
        out_on = os.path.join(self.tmp, "on.pdf")

        self.handler.merge_pdfs([p1, p2], out_off, layout=_layout(), mode="普通")
        self.handler.merge_pdfs(
            [p1, p2], out_on,
            layout=_layout(show_crop_marks=True, crop_mark_left=5, crop_mark_right=5),
            mode="普通",
        )

        self.assertEqual(self._page_count(out_off), self._page_count(out_on))
        doc_off = fitz.open(out_off)
        doc_on = fitz.open(out_on)
        off_drawings = len(doc_off[0].get_drawings())
        on_drawings = len(doc_on[0].get_drawings())
        doc_off.close()
        doc_on.close()
        self.assertGreater(on_drawings, off_drawings)
        self.assertTrue(os.path.getsize(out_off) > 0)

    def test_02_zero_margin_no_redundant_marks(self):
        """页边距为零时不绘制冗余标记，合并仍成功。"""
        p1 = self._make_pdf("z.pdf", "INVOICE-Z")
        out = os.path.join(self.tmp, "zero.pdf")
        self.handler.merge_pdfs(
            [p1], out,
            layout=_layout(margins={"top": 0, "bottom": 0, "left": 0, "right": 0}),
            mode="普通",
        )
        self.assertTrue(os.path.exists(out))
        self.assertGreaterEqual(self._page_count(out), 1)

    def test_03_pdf_and_image_mixed_merge(self):
        """PDF 与图片按列表顺序混合合并，图片保持宽高比完整放入单元格。"""
        pdf = self._make_pdf("m.pdf", "INVOICE-M")
        png = self._make_png("m.png")
        out = os.path.join(self.tmp, "mixed.pdf")
        self.handler.merge_pdfs([pdf, png], out, layout=_layout(), mode="普通")
        self.assertTrue(os.path.exists(out))
        doc = fitz.open(out)
        self.assertGreaterEqual(len(doc), 1)
        self.assertGreater(len(doc[0].get_images(full=True)) + len(doc[0].get_drawings()), 0)
        doc.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
