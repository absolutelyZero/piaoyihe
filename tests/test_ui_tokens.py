#!/usr/bin/env python3
"""
UI 令牌一致性测试

验证 v2 UI 的浅色/深色令牌键名完全对齐、关键色值与设计稿一致、
全局 QSS 由令牌生成，以及 AppTheme 兼容层属性名未发生变化。
"""

import os
import sys
import unittest

# 让测试可以直接以 `python -m unittest tests.test_ui_tokens` 运行
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in (os.path.join(_ROOT, "code"), os.path.join(_ROOT, ".pylibs")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from ui import tokens  # noqa: E402

try:
    from ui.theme import AppTheme  # noqa: E402
    HAS_QT = True
except Exception:  # pragma: no cover - 无 PySide6 时跳过兼容层断言
    AppTheme = None
    HAS_QT = False


OLD_THEME_ATTRS = (
    "bg", "card_bg", "border", "text_primary", "text_secondary", "text_muted",
    "hover_bg", "pressed_bg", "selected_bg", "selected_text", "alt_row",
    "scroll_area_bg", "placeholder_start", "placeholder_mid",
    "placeholder_end", "placeholder_border",
)


class TokenAlignmentTests(unittest.TestCase):
    def test_light_dark_keys_are_identical(self):
        self.assertEqual(set(tokens.LIGHT), set(tokens.DARK))
        self.assertGreaterEqual(len(tokens.LIGHT), 30)

    def test_design_baseline_colors(self):
        self.assertEqual(tokens.LIGHT["accent"], "#1A56A8")
        self.assertEqual(tokens.LIGHT["background"], "#F4F6F9")
        self.assertEqual(tokens.LIGHT["surface"], "#FFFFFF")
        self.assertEqual(tokens.LIGHT["border"], "#E3E8EF")
        self.assertEqual(tokens.LIGHT["text_primary"], "#16202E")
        self.assertEqual(tokens.LIGHT["success"], "#12805C")
        self.assertEqual(tokens.LIGHT["warning"], "#B7791F")
        self.assertEqual(tokens.LIGHT["danger"], "#C0392B")
        self.assertEqual(tokens.DARK["accent"], "#4A86D8")
        self.assertEqual(tokens.DARK["background"], "#141A23")
        self.assertEqual(tokens.DARK["surface"], "#1C2430")
        self.assertEqual(tokens.DARK["border"], "#2E3A49")
        self.assertEqual(tokens.DARK["text_primary"], "#E6EDF5")

    def test_get_tokens_returns_a_copy(self):
        light = tokens.get_tokens(False)
        self.assertEqual(light, tokens.LIGHT)
        light["accent"] = "#000000"
        self.assertEqual(tokens.LIGHT["accent"], "#1A56A8")

    def test_spacing_and_radius_scales(self):
        self.assertEqual(tokens.SPACING, (4, 8, 12, 16, 20, 24, 32))
        self.assertEqual(tokens.RADIUS, {"card": 8, "control": 6, "chip": 4})


class StylesheetTests(unittest.TestCase):
    def test_stylesheet_is_generated_from_tokens(self):
        light_qss = tokens.build_stylesheet(False)
        dark_qss = tokens.build_stylesheet(True)
        self.assertIn("#1A56A8", light_qss)
        self.assertIn("#4A86D8", dark_qss)
        self.assertNotIn("#4A86D8", light_qss)
        self.assertIn("QPushButton#primaryButton", light_qss)
        self.assertIn("QFrame#statusBar", light_qss)
        # 标题栏与上下文条已并入状态栏，其选择器不再生成
        self.assertNotIn("QFrame#titleBar", light_qss)
        self.assertNotIn("QFrame#contextBar", light_qss)
        self.assertIn("QTableWidget", light_qss)
        self.assertIn("QFrame#dropZone", light_qss)
        # 状态栏行高：文字项与文字按钮统一 22px，避免「使用帮助」比相邻文本低 2px
        self.assertIn("QFrame#statusBar QLabel#statusBarLabel { min-height: 22px; max-height: 22px; }", light_qss)
        self.assertIn("QFrame#statusBar QPushButton#textButton { min-height: 22px; max-height: 22px; }", light_qss)

    def test_font_stacks_match_design_system(self):
        # 设计稿（req/ui/00「05 / 字体与数字」）：中文 Noto Sans SC，数字 Inter。
        # Geist Mono 在目标机器不存在会回退 Arial，已从字体栈移除。
        self.assertIn("Noto Sans SC", tokens.FONT_CN_STACK)
        self.assertIn("Microsoft YaHei", tokens.FONT_CN_STACK)
        self.assertIn("Inter", tokens.FONT_MONO_STACK)
        self.assertNotIn("Geist Mono", tokens.FONT_MONO_STACK)
        self.assertIn("monospace", tokens.FONT_MONO_STACK)
        self.assertEqual(tokens.FONT_CN_STACK.split(",")[0].strip('"'), "Noto Sans SC")
        self.assertEqual(tokens.FONT_MONO_STACK.split(",")[0].strip('"'), "Inter")

    def test_bundled_fonts_declared(self):
        self.assertIn("Inter-VF.ttf", tokens.BUNDLED_FONTS)
        self.assertIn("NotoSansSC-VF.ttf", tokens.BUNDLED_FONTS)
        self.assertEqual(tokens.FONT_BODY_PIXEL_SIZE, 13)

    def test_resolve_font_family_is_deterministic(self):
        family = tokens.resolve_font_family()
        self.assertIsInstance(family, str)
        self.assertTrue(family)

    def test_numeric_font_uses_inter_with_tnum(self):
        # 重点：财务列字体改为设计稿同款 Inter（启用 tnum 等宽），
        # 不再硬编码不存在的 Geist Mono；字号按传入值设置。
        try:
            from PySide6.QtWidgets import QApplication
        except Exception:
            self.skipTest("PySide6 不可用")
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        QApplication.instance() or QApplication([])
        font = tokens.numeric_font(12)
        self.assertEqual(font.family(), "Inter")
        self.assertEqual(font.pixelSize(), 12)
        self.assertEqual(tokens.numeric_font(11).pixelSize(), 11)


@unittest.skipUnless(HAS_QT, "PySide6 不可用")
class ThemeCompatTests(unittest.TestCase):
    def test_theme_reads_from_tokens(self):
        light = AppTheme(dark=False)
        dark = AppTheme(dark=True)
        self.assertEqual(light.bg, tokens.LIGHT["background"])
        self.assertEqual(light.card_bg, tokens.LIGHT["surface"])
        self.assertEqual(dark.bg, tokens.DARK["background"])
        self.assertEqual(dark.accent, tokens.DARK["accent"])

    def test_old_attribute_names_preserved_in_both_modes(self):
        for theme in (AppTheme(dark=False), AppTheme(dark=True)):
            for name in OLD_THEME_ATTRS:
                self.assertTrue(hasattr(theme, name), name)
                self.assertTrue(getattr(theme, name).startswith("#"), name)


class DocumentationConsistencyTests(unittest.TestCase):
    """说明文档.md 的令牌映射表必须与 tokens.py 完全一致。"""

    def test_doc_table_matches_tokens(self):
        import re

        doc_path = os.path.join(_ROOT, "说明文档.md")
        with open(doc_path, "r", encoding="utf-8") as fh:
            content = fh.read()
        rows = re.findall(
            r"\|\s*`([a-z_]+)`\s*\|\s*`(#[0-9A-Fa-f]{6})`\s*\|\s*`(#[0-9A-Fa-f]{6})`\s*\|",
            content,
        )
        self.assertEqual(len(rows), len(tokens.LIGHT), "文档表格行数应与令牌数一致")
        self.assertEqual({name for name, _, _ in rows}, set(tokens.LIGHT))
        for name, light_value, dark_value in rows:
            self.assertEqual(tokens.LIGHT[name], light_value, f"浅色 {name}")
            self.assertEqual(tokens.DARK[name], dark_value, f"深色 {name}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
