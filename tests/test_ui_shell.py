#!/usr/bin/env python3
"""
v2 UI 离屏回归测试

在 QT_QPA_PLATFORM=offscreen 下真实构造主窗口、重命名对话框与更新弹窗，
验证五段式结构、9 列台账、四级按钮、重复告警、状态组件、配置键名与
CLI 参数在改造后保持不变。不依赖真实发票样本，也不改写项目 config.json。
"""

import json
import os
import sys
import tempfile
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in (os.path.join(_ROOT, "code"), os.path.join(_ROOT, ".pylibs")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtGui import QFont  # noqa: E402
from PySide6.QtWidgets import QApplication, QPushButton, QFrame  # noqa: E402


def _file_info(name, code, amount=4860.0, tax=437.4):
    return {
        "name": name,
        "invoice_code": code,
        "amount": amount,
        "tax_amount": tax,
        "invoice_date": "2026-11-03",
        "path": os.path.join(_ROOT, name),
        "mod_time": "2026-11-04",
        "size": "128 KB",
    }


class UIShellTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        from ui.tokens import apply_application_style

        apply_application_style(cls.app)

        import ui.main_frame as mf

        cls.mf = mf
        cls._orig_config = mf.CONFIG_FILE
        cls._tmp_dir = tempfile.mkdtemp(prefix="piaoyihe_ui_", dir=os.path.join(_ROOT, ".testtmp"))
        cls.tmp_config = os.path.join(cls._tmp_dir, "config.json")
        with open(cls.tmp_config, "w", encoding="utf-8") as fh:
            json.dump(
                {
                    "layout_config": {
                        "orientation": "landscape",
                        "rows": 3,
                        "cols": 2,
                        "show_crop_marks": False,
                        "crop_mark_left": 0,
                        "crop_mark_right": 0,
                    },
                    "mode": "图像",
                    "sort_by": "amount",
                    "preview_enabled": True,
                },
                fh,
                ensure_ascii=False,
            )
        mf.CONFIG_FILE = cls.tmp_config
        cls.window = mf.MainWindow()

    @classmethod
    def tearDownClass(cls):
        # 必须先关闭窗口：closeEvent 会调用 _save_config()，
        # 若提前恢复真实 CONFIG_FILE 会污染项目配置。
        cls.window.close()
        cls.mf.CONFIG_FILE = cls._orig_config

    # ---- 结构 ----
    def test_01_five_sections_exist(self):
        w = self.window
        expected = {
            "title_bar": "titleBar",
            "context_bar": "contextBar",
            "content_splitter": "contentSplitter",
            "output_bar": "outputBar",
            "status_bar": "statusBar",
        }
        for attr, object_name in expected.items():
            self.assertTrue(hasattr(w, attr), attr)
            self.assertEqual(getattr(w, attr).objectName(), object_name)

    def test_02_splitter_ratio_and_scroll(self):
        w = self.window
        sizes = w.content_splitter.sizes()
        self.assertEqual(len(sizes), 2)
        self.assertEqual(w.ledger_column, w.content_splitter.widget(0))
        self.assertEqual(w.settings_column, w.content_splitter.widget(1))
        self.assertEqual(
            w.file_list.table.horizontalScrollBarPolicy(),
            Qt.ScrollBarPolicy.ScrollBarAsNeeded,
        )
        self.assertGreaterEqual(w.file_list.table.horizontalHeader().minimumSectionSize(), 36)
        self.assertGreaterEqual(w.content_splitter.sizes()[0], w.content_splitter.sizes()[1])

    def test_03_nine_columns_preserved(self):
        table = self.window.file_list.table
        self.assertEqual(table.columnCount(), 9)
        headers = [
            table.horizontalHeaderItem(i).text() if table.horizontalHeaderItem(i) else ""
            for i in range(9)
        ]
        self.assertEqual(
            headers,
            ["", "发票号码", "文件名", "金额", "税额", "开票日期", "路径", "修改日期", "大小"],
        )

    def test_04_button_hierarchy(self):
        w = self.window
        primary = [b.text() for b in w.findChildren(QPushButton)
                   if b.objectName() == "primaryButton"]
        self.assertEqual(primary, ["合并 PDF"])
        danger = [b.text() for b in w.findChildren(QPushButton)
                  if b.objectName() == "dangerButton"]
        self.assertTrue(any("删除" in text for text in danger), danger)
        self.assertTrue(any("清空" in text for text in danger), danger)
        self.assertIn(w.merge_btn, w.output_bar.findChildren(QPushButton))

    def test_05_config_loaded_and_status_synced(self):
        w = self.window
        self.assertTrue(w.radio_landscape.isChecked())
        self.assertEqual(w.row_spinbox.value(), 3)
        self.assertEqual(w.col_spinbox.value(), 2)
        self.assertEqual(w.mode_combo.currentText(), "图像")
        self.assertIn("横向 3 × 2", w.status_left_label.text())
        self.assertIn("每页 6 张", w.preview_summary_label.text())

        w.row_spinbox.setValue(4)
        self.assertIn("横向 4 × 2", w.status_left_label.text())
        self.assertIn("每页 8 张", w.preview_summary_label.text())
        w.row_spinbox.setValue(3)

    def test_06_merge_disabled_with_reason(self):
        w = self.window
        self.assertFalse(w.merge_btn.isEnabled())
        self.assertIn("请先添加", w.merge_btn.toolTip())

    def test_07_preview_empty_state_and_switch(self):
        w = self.window
        self.assertEqual(w.preview_stack.count(), 2)
        self.assertEqual(w.preview_stack.currentIndex(), 0)
        self.assertEqual(w.preview_placeholder.parent().objectName(), "previewPlaceholder")
        self.assertTrue(w.preview_checkbox.isChecked())

    # ---- 台账 ----
    def test_08_financial_columns_use_monospace_and_right_align(self):
        w = self.window
        w.file_list.add_file_info(_file_info("a.pdf", "CODE-A", 4860.0, 437.4))
        w.file_list.add_file_info(_file_info("b.pdf", "CODE-B", 553.0, 0.0))
        w.file_list.add_file_info(_file_info("c.pdf", "CODE-C", 68.5, 2.0))
        table = w.file_list.table
        row = table.rowCount() - 1
        for col in (3, 4, 8):
            item = table.item(row, col)
            self.assertTrue(item.textAlignment() & Qt.AlignmentFlag.AlignRight, col)
        self.assertEqual(table.item(row, 1).font().styleHint(), QFont.StyleHint.TypeWriter)
        self.assertIn("3 张", w.ledger_count_label.text())
        self.assertIn("5,481.50", w.ledger_total_label.text())

    def test_09_duplicate_state_marker_and_chip(self):
        w = self.window
        w.file_list._update_duplicate_display({"CODE-A"})
        self.assertEqual(w.file_list.duplicate_row_count, 1)
        w._on_duplicate_count_changed(1)
        self.assertFalse(w.ledger_warning_chip.isHidden())
        self.assertIn("重复 1 组", w.ledger_warning_chip.text())

        # 设计稿：重复行整行统一淡琥珀底（含最左眼睛列），
        # 发票号码与文件名用警示色，其余列保持正文色。
        table = w.file_list.table
        row = 0
        for col in range(table.columnCount()):
            self.assertEqual(
                table.item(row, col).background(),
                table.item(row, 3).background(),
                col,
            )
        self.assertEqual(table.item(row, 1).foreground().color(),
                         table.item(row, 2).foreground().color())
        self.assertNotEqual(table.item(row, 3).foreground().color(),
                            table.item(row, 1).foreground().color())

        w._on_duplicate_count_changed(0)
        self.assertTrue(w.ledger_warning_chip.isHidden())

    def test_10_context_menu_danger_action(self):
        from PySide6.QtWidgets import QLabel

        from ui.file_list import DangerMenuAction

        action = DangerMenuAction("删除")
        widget = action.defaultWidget()
        self.assertIsNotNone(widget)
        labels = [c for c in widget.findChildren(QLabel)
                  if c.objectName() == "dangerMenuLabel"]
        self.assertEqual(len(labels), 1)
        self.assertEqual(labels[0].text(), "删除")
        # 右键菜单四项对应的槽函数均保留
        panel = self.window.file_list
        for slot in ("_open_file_at_row", "_show_in_folder", "delete_selected", "_export_file"):
            self.assertTrue(hasattr(panel, slot), slot)

    # ---- 状态与配置 ----
    def test_11_feedback_states(self):
        w = self.window
        for state in ("info", "success", "warning", "danger"):
            w._show_feedback(f"回执-{state}", state)
            self.assertEqual(w.feedback_label.property("state"), state)
            self.assertEqual(w.feedback_label.text(), f"回执-{state}")
            self.assertFalse(w.feedback_label.isHidden())
        w._show_feedback("", "info")
        self.assertTrue(w.feedback_label.isHidden())

    def test_12_config_keys_unchanged(self):
        w = self.window
        w._save_config()
        with open(self.tmp_config, "r", encoding="utf-8") as fh:
            config = json.load(fh)
        expected = {
            "layout", "layout_config", "mode", "sort_by", "print_checkbox",
            "duplicate_copy", "output_path", "preview_enabled",
        }
        self.assertTrue(expected.issubset(set(config)), expected - set(config))
        self.assertEqual(config["layout_config"]["orientation"], "landscape")
        self.assertIn("show_crop_marks", config["layout_config"])
        self.assertIn("crop_mark_left", config["layout_config"])
        self.assertIn("crop_mark_right", config["layout_config"])
        # 不得新增/改名配置字段
        self.assertNotIn("ui_theme", config)

    def test_13_cli_args_unchanged(self):
        from main import _parse_args

        args = _parse_args([
            "--mcp-server", "--transport", "sse", "--host", "127.0.0.1",
            "--port", "8766", "--cors-origins", "*",
        ])
        self.assertTrue(args.mcp_server)
        self.assertEqual(args.transport, "sse")
        self.assertEqual(args.port, 8766)

    # ---- 弹窗 ----
    def test_14_rename_dialog_structure(self):
        from ui.rename_dialog import RenameDialog

        dialog = RenameDialog(config_file=self.tmp_config)
        self.assertEqual(len(dialog._type_nav_buttons), 7)
        self.assertFalse(dialog.type_tabs.tabBar().isVisible())
        chips = [c.objectName() for c in dialog.findChildren(QPushButton)
                 if c.objectName().startswith("fieldChip")]
        self.assertGreaterEqual(len(chips), 4)
        self.assertIn("fieldChip", chips)
        self.assertTrue(hasattr(dialog, "example_label"))
        self.assertTrue(hasattr(dialog, "result_label"))
        dialog.rule_input.setText("{开票日期}-{金额}")
        self.assertIn("2026-11-03", dialog.example_label.text())
        dialog.close()

    def test_16_feature_matrix_entries_present(self):
        """51 项功能基线：逐项核对入口/控件/handler 在改造后仍可达。"""
        w = self.window
        matrix = {
            "A 窗口框架": [
                "title_bar", "drop_label", "version_label", "check_update_btn",
                "feedback_button", "progress_bar",
            ],
            "B 票据台账": [
                "file_list", "ledger_card", "ledger_count_label", "ledger_total_label",
                "ledger_warning_chip", "drop_zone", "ledger_record_label",
                "ledger_footer_total", "actions_card",
            ],
            "C 列表操作": [
                "add_file_btn", "del_btn", "del_all_btn", "move_up_btn",
                "move_down_btn", "rename_btn", "export_list_btn",
            ],
            "D 排版参数": [
                "radio_portrait", "radio_landscape", "row_spinbox", "col_spinbox",
                "margin_top_spinbox", "margin_bottom_spinbox", "margin_left_spinbox",
                "margin_right_spinbox", "crop_mark_checkbox",
                "crop_mark_left_spinbox", "crop_mark_right_spinbox",
            ],
            "E 顺序与输出": [
                "order_combo", "path_edit", "select_path_btn", "merge_btn",
                "duplicate_copy_checkbox", "print_checkbox", "print_btn", "output_bar",
            ],
            "F 实时预览": [
                "preview_stack", "preview_scroll", "refresh_preview_btn",
                "preview_status_label", "preview_zoom_label", "preview_checkbox",
                "preview_summary_label", "preview_page_label",
            ],
            "G 批量重命名": [
                "_on_rename", "_perform_batch_rename", "_migrate_rename_rules_if_needed",
                "_on_export_list", "_show_feedback", "_update_status_bar",
            ],
            "H 系统能力": [
                "_load_config", "_save_config", "_check_update_status",
                "_on_version_click", "_on_feedback", "_on_preview_checkbox_changed",
            ],
        }
        total = 0
        for group, names in matrix.items():
            for name in names:
                self.assertTrue(hasattr(w, name), f"{group}: {name}")
                total += 1
        self.assertGreaterEqual(total, 51)
        # 业务层入口（MCP / OFD / 字段提取）未改动
        from core.ofd_converter import is_ofd_file
        from core.invoice_service import migrate_rename_rules

        self.assertTrue(callable(is_ofd_file))
        self.assertTrue(callable(migrate_rename_rules))

    def test_15_dialogs_use_unified_structure(self):
        from core.update_checker import QRCodeDialog, UpdateDialog

        update_dlg = UpdateDialog(
            self.window, "https://example.invalid/qr.png", self.tmp_config, "0.1.16"
        )
        self.assertEqual(update_dlg.view_button.objectName(), "primaryButton")
        for dlg in (update_dlg,):
            names = {f.objectName() for f in dlg.findChildren(QFrame)}
            self.assertIn("dialogHeader", names)
            self.assertIn("dialogFooter", names)
        update_dlg.close()

        qr_dlg = QRCodeDialog(self.window, "https://example.invalid/qr.png")
        names = {f.objectName() for f in qr_dlg.findChildren(QFrame)}
        self.assertIn("dialogHeader", names)
        self.assertIn("dialogFooter", names)
        qr_dlg.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
