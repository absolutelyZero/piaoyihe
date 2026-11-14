#!/usr/bin/env python3
"""
字体对齐专项测试

验证 v2 UI 按设计稿对齐字体的约束：
  - 字重/字号常量集中定义，QSS 源码无魔法数字
  - 表头字体单一来源（header_font），消除 QSS/setBold 双来源
  - 数字位走 Inter + tnum（含中文回退链）
  - QSS 通用规则不声明 font-family（否则覆盖 setFont 导致 tnum 失效）
  - 全项目无逐控件 setStyleSheet 书写 font-*
"""

import os
import re
import sys
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in (os.path.join(_ROOT, "code"), os.path.join(_ROOT, ".pylibs")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from ui import tokens  # noqa: E402

try:
    from PySide6.QtWidgets import QApplication  # noqa: E402
    from PySide6.QtGui import QFont  # noqa: E402
    HAS_QT = True
except Exception:
    HAS_QT = False


def _read(path):
    with open(os.path.join(_ROOT, path), "r", encoding="utf-8") as fh:
        return fh.read()


class FontConstantTests(unittest.TestCase):
    def test_weight_scale_matches_design(self):
        self.assertEqual(
            tokens.FONT_WEIGHT,
            {"regular": 400, "medium": 500, "semibold": 600, "bold": 700},
        )
        self.assertEqual(tokens.FONT_SIZE["base"], 13)
        self.assertEqual(tokens.FONT_BODY_PIXEL_SIZE, tokens.FONT_SIZE["base"])
        self.assertEqual(tokens.FONT_LINE_HEIGHT_BODY, 22)
        self.assertEqual(tokens.FONT_LETTER_SPACING, 0)

    def test_20px_is_display_only_not_consumed_by_ui(self):
        """设计稿 Bold 20 只用于说明页大标题，界面不消费。"""
        self.assertEqual(tokens.DESIGN_DISPLAY_SIZE, 20)
        self.assertNotIn(20, tokens.FONT_SIZE.values())
        # 只校验字号；20px 也用于 min-height 等几何属性，不应误判
        self.assertNotRegex(tokens.build_stylesheet(False), r"font-size:\s*20px")

    def test_qss_source_has_no_font_magic_numbers(self):
        src = _read("code/ui/tokens.py")
        # 允许文档字符串里引用历史值；此处只检查 QSS 规则区域内的裸数字
        qss_start = src.index("def build_stylesheet")
        qss_src = src[qss_start:]
        self.assertNotIn("font-size: 13px", qss_src)
        self.assertNotIn("font-weight: 700;", qss_src)
        self.assertNotIn("font-weight: 500;", qss_src)
        self.assertIn("{S['base']}", qss_src)
        self.assertIn("{W['bold']}", qss_src)

    def test_qss_general_rules_do_not_declare_font_family(self):
        """通用 QLabel / 容器 / 表单规则声明 font-family 会覆盖 setFont 的 tnum。"""
        qss = tokens.build_stylesheet(False)
        for selector in (
            "QMainWindow, QWidget#centralWidget, QDialog",
            "QLabel {",
            "QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {",
        ):
            self.assertIn(selector, qss)
        # 定位 QLabel 通用块
        block = re.search(r"\nQLabel \{([^}]*)\}", qss).group(1)
        self.assertNotIn("font-family", block)
        self.assertNotIn("font-size", block)
        # 表头区块不声明字体
        header = re.search(r"QHeaderView::section \{([^}]*)\}", qss).group(1)
        self.assertNotIn("font-size", header)
        self.assertNotIn("font-weight", header)
        self.assertNotIn("font-family", header)

    def test_numeric_mapping_covers_design_positions(self):
        required = {
            "statusBarLabel", "footLabel", "statusLabel", "statusChip",
            "warningChip", "successChip", "dangerChip", "mutedLabel",
            "subtitleLabel", "hintLabel", "inlineUnit", "paramCaption",
            "ledgerTotalCaption", "liveStateLabel", "typeNavTitle", "helpCardText",
        }
        self.assertEqual(required, set(tokens.NUMERIC_TEXT_OBJECTS))
        self.assertEqual(required, set(tokens.NUMERIC_TEXT_SIZES))
        self.assertEqual(
            set(tokens.NUMERIC_INPUT_OBJECTS), {"paramSpin", "bareSpin", "pathInput"}
        )
        for name, px in tokens.NUMERIC_TEXT_SIZES.items():
            self.assertIn(px, tokens.FONT_SIZE.values(), name)

    def test_font_stacks_have_chinese_fallback_for_mixed_text(self):
        self.assertIn("Noto Sans SC", tokens.FONT_MONO_STACK)
        self.assertEqual(tokens.FONT_MONO_STACK.split(",")[0].strip('"'), "Inter")
        self.assertEqual(tokens.FONT_CN_STACK.split(",")[0].strip('"'), "Noto Sans SC")
        self.assertNotIn("Geist Mono", tokens.FONT_MONO_STACK)

    def test_no_inline_font_stylesheets_in_ui_sources(self):
        for rel in (
            "code/ui/main_frame.py", "code/ui/file_list.py", "code/ui/shell.py",
            "code/ui/rename_dialog.py", "code/ui/tokens.py",
            "code/core/update_checker.py",
        ):
            src = _read(rel)
            self.assertIsNone(
                re.search(r"setStyleSheet\([^)]*font-(size|family|weight)", src, re.S),
                f"{rel} 仍有逐控件 font-* 内联样式",
            )
        # main_frame.py 不应再有 font-size 字面量（含注释）
        self.assertNotIn("font-size", _read("code/ui/main_frame.py"))


@unittest.skipUnless(HAS_QT, "PySide6 不可用")
class NumericFontRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        tokens.apply_application_style(cls.app)

    def test_numeric_font_uses_inter_tnum_and_chinese_fallback(self):
        font = tokens.numeric_font(12)
        self.assertEqual(font.family(), "Inter")
        self.assertEqual(font.pixelSize(), 12)
        self.assertIn("Noto Sans SC", font.families())
        self.assertEqual(font.styleHint(), QFont.StyleHint.TypeWriter)
        self.assertEqual(tokens.numeric_font(11).pixelSize(), 11)

    def test_numeric_font_weight_from_constants(self):
        bold = tokens.numeric_font(15, tokens.FONT_WEIGHT["bold"])
        self.assertEqual(bold.pixelSize(), 15)
        self.assertEqual(bold.weight(), QFont.Weight.Bold)

    def test_header_font_is_single_source(self):
        regular = tokens.header_font(False)
        bold = tokens.header_font(True)
        self.assertEqual(regular.family(), "Noto Sans SC")
        self.assertEqual(regular.pixelSize(), tokens.FONT_SIZE["caption"])
        self.assertFalse(regular.bold())
        self.assertTrue(bold.bold())

    def test_table_header_and_numeric_columns(self):
        from core.pdf_handler import PDFHandler
        from ui.file_list import FileListPanel

        panel = FileListPanel(PDFHandler())
        hdr = panel.table.horizontalHeaderItem(3)
        self.assertEqual(hdr.font().pixelSize(), 11)
        self.assertTrue(hdr.font().bold())  # 仅金额列加粗
        self.assertFalse(panel.table.horizontalHeaderItem(1).font().bold())

    def test_apply_numeric_text_fonts_sets_inter(self):
        from PySide6.QtWidgets import QLabel, QWidget

        root = QWidget()
        a = QLabel("就绪 | 横向 2 × 2 | 4 张票据", root)
        a.setObjectName("statusBarLabel")
        b = QLabel("普通中文", root)
        b.setObjectName("brandTitle")
        root.setStyleSheet(tokens.build_stylesheet(False))
        applied = tokens.apply_numeric_text_fonts(root)
        self.assertGreaterEqual(applied, 1)
        self.assertEqual(a.font().family(), "Inter")
        self.assertEqual(a.font().pixelSize(), 11)
        # 未在数字清单中的中文标签保持应用默认中文栈
        self.assertNotEqual(b.font().family(), "Inter")


if __name__ == "__main__":
    unittest.main(verbosity=2)
