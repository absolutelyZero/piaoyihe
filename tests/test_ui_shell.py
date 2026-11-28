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
    def test_01_three_sections_exist(self):
        """三段式结构：主体 → 输出提交条 → 状态栏（状态栏承载全部全局入口）。"""
        w = self.window
        expected = {
            "content_splitter": "contentSplitter",
            "output_bar": "outputBar",
            "status_bar": "statusBar",
        }
        for attr, object_name in expected.items():
            self.assertTrue(hasattr(w, attr), attr)
            self.assertEqual(getattr(w, attr).objectName(), object_name)
        # 标题栏与上下文提示条已并入状态栏，不再单独存在
        self.assertFalse(hasattr(w, "title_bar"))
        self.assertFalse(hasattr(w, "context_bar"))
        for attr in (
            "status_left_label", "context_status_label", "status_right_label",
            "feedback_button", "version_label",
        ):
            self.assertTrue(hasattr(w, attr), attr)
            self.assertIn(getattr(w, attr), w.status_bar.findChildren(type(getattr(w, attr))))
        # 版本号即检查更新入口，不再另设按钮
        self.assertFalse(hasattr(w, "check_update_btn"))

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
                "status_bar", "status_left_label", "version_label",
                "appreciation_button", "feedback_button", "progress_bar",
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
                "_on_version_click", "_on_feedback", "_on_appreciation",
                "_on_preview_checkbox_changed",
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
        from core.update_checker import TEXT_CHECKING, TEXT_CHECK_FAILED, UpdateDialog, UpdateInfo

        # 构造即可显示：不传任何网络结果，第二行先呈现「正在检查最新版本中…」
        update_dlg = UpdateDialog(self.window, "0.1.16", self.tmp_config)

        # 统一结构：标题栏 + 内容区 + 页脚操作区
        names = {f.objectName() for f in update_dlg.findChildren(QFrame)}
        self.assertIn("dialogHeader", names)
        self.assertIn("dialogFooter", names)

        # 第一行当前版本、第二行初始为检查中
        self.assertIn("当前版本", update_dlg.current_label.text())
        self.assertIn("0.1.16", update_dlg.current_label.text())
        self.assertEqual(update_dlg.latest_label.text(), TEXT_CHECKING)

        # 页脚只有稍后与忽略此版本，不再有「立即更新」
        self.assertEqual(update_dlg.ignore_button.objectName(), "secondaryButton")
        self.assertEqual(update_dlg.later_button.objectName(), "secondaryButton")
        self.assertIn("忽略", update_dlg.ignore_button.text())
        self.assertIn("稍后", update_dlg.later_button.text())
        self.assertFalse(hasattr(update_dlg, "view_button"))
        footer_buttons = [
            b.text() for b in update_dlg.findChild(QFrame, "dialogFooter").findChildren(QPushButton)
        ]
        self.assertEqual(footer_buttons, ["稍后", "忽略此版本"])

        # 成功回填：显示最新版本号与可点击的 Release 地址
        info = UpdateInfo(
            version="0.1.17",
            release_url="https://example.invalid/releases/tag/v0.1.17",
            tag="v0.1.17",
        )
        update_dlg.set_update_info(info)
        self.assertIn("最新版本", update_dlg.latest_label.text())
        self.assertIn("0.1.17", update_dlg.latest_label.text())
        self.assertIn("example.invalid/releases/tag/v0.1.17", update_dlg.release_label.text())
        self.assertTrue(update_dlg.release_label.openExternalLinks())

        # 失败回填：只在弹窗内提示，不抛异常
        update_dlg.set_check_failed()
        self.assertEqual(update_dlg.latest_label.text(), TEXT_CHECK_FAILED)

        # 已是最新版本的回填
        update_dlg.set_no_update()
        self.assertIn("已是最新", update_dlg.latest_label.text())

        # 二维码为本地资源，不依赖网络下载
        self.assertGreater(update_dlg.qrcode_label.minimumWidth(), 0)

        update_dlg.close()

    def test_16_update_dialog_degrades_when_qrcode_missing(self):
        """二维码资源缺失时降级为文字提示，不抛异常、不弹错误框。"""
        from unittest import mock

        from core.update_checker import UpdateDialog, UpdateInfo

        # 把资源目录指向不存在的路径，模拟二维码缺失（不能 patch 方法本身：
        # QPixmap 收到 MagicMock 会段错误，必须让 _qrcode_path 返回真实的字符串路径）
        with mock.patch("core.update_checker._res_dir", return_value="/nonexistent"):
            dlg = UpdateDialog(self.window, "0.1.16", self.tmp_config)
            # 降级为文字，而不是崩溃或空控件
            self.assertTrue(dlg.qrcode_label.pixmap().isNull())
            self.assertIn("二维码", dlg.qrcode_label.text())
            dlg.close()

    # ---- 空态投放带（tasks 3.4）----

    # ---- 赞赏作者弹窗（add-appreciation-author-entry）----
    def test_20_appreciation_dialog(self):
        """赞赏弹窗沿用统一结构，并展示两张带标注的收款码；缺失图片优雅降级。"""
        from PySide6.QtWidgets import QLabel

        dlg = self.mf.AppreciationDialog(self.window)
        self.assertEqual(dlg.windowTitle(), "赞赏作者")
        self.assertTrue(dlg.isModal())
        names = {f.objectName() for f in dlg.findChildren(QFrame)}
        self.assertIn("dialogHeader", names)
        self.assertIn("dialogFooter", names)

        texts = [w.text() for w in dlg.findChildren(QLabel)]
        self.assertTrue(any("赞赏作者" in t for t in texts))
        self.assertTrue(any("微信支付" in t for t in texts))
        self.assertTrue(any("支付宝" in t for t in texts))
        self.assertTrue(any("扫码赞赏" in t for t in texts))

        # 图片缺失时降级为占位提示，不抛异常
        original = self.mf._res_dir
        try:
            self.mf._res_dir = lambda: os.path.join(self._tmp_dir, "missing_res")
            degraded = self.mf.AppreciationDialog(self.window)
            dtexts = [w.text() for w in degraded.findChildren(QLabel)]
            self.assertTrue(any("收款码不可用" in t for t in dtexts))
            degraded.close()
        finally:
            self.mf._res_dir = original

        dlg.close()

    def test_21_manual_check_opens_dialog_without_blocking(self):
        """点击版本号：先弹窗，检查结果异步回填，不再弹任何消息框。"""
        from unittest import mock

        shown_messages = []
        with mock.patch(
            "ui.main_frame.open_update_dialog", return_value=object()
        ) as opener, mock.patch(
            "ui.main_frame.QMessageBox.warning",
            side_effect=lambda *a: shown_messages.append(a),
        ), mock.patch(
            "ui.main_frame.QMessageBox.information",
            side_effect=lambda *a: shown_messages.append(a),
        ):
            self.window._check_update_status(force_check=True)

        opener.assert_called_once()
        args = opener.call_args[0]
        self.assertIs(args[0], self.window)
        self.assertEqual(args[1], self.mf.VERSION_FILE)
        self.assertEqual(args[2], self.tmp_config)
        self.assertEqual(shown_messages, [])
        self.assertIsNotNone(self.window._update_dialog)

    def test_17_empty_drop_zone_keeps_ledger_header(self):
        """空态投放带占满表头以下的列表区，九列表头始终可见。"""
        from PySide6.QtWidgets import QTableWidget

        w = self.window
        panel = w.file_list
        table = panel.table
        overlay = w.drop_zone

        # 1) 九列表头常驻：表格本身不被隐藏，列数不变
        self.assertIsInstance(table, QTableWidget)
        self.assertEqual(table.columnCount(), 9)
        self.assertFalse(table.isHidden())
        self.assertFalse(table.horizontalHeader().isHidden())

        # 2) 投放带是表格视口的子控件（视口恰在表头下方），不是台账卡片里的兄弟控件
        self.assertIs(overlay.parent(), table.viewport())
        self.assertIs(panel.empty_overlay, overlay)

        # 3) 空态：投放带可见，且几何铺满表头以下的整块视口
        panel.clear()
        w._update_status_bar()
        self.assertEqual(len(panel.files), 0)
        self.assertFalse(overlay.isHidden())
        self.assertEqual(overlay.geometry(), table.viewport().rect())
        self.assertTrue(table.horizontalHeader().isVisible() or table.horizontalHeader().isHidden() is False)

        # 4) 加入首个文件后投放带让位，表头仍在
        panel.add_file_info(_file_info("d.pdf", "CODE-D", 120.0, 12.0))
        w._update_status_bar()
        self.assertEqual(len(panel.files), 1)
        self.assertTrue(overlay.isHidden())
        self.assertFalse(table.isHidden())
        self.assertEqual(table.rowCount(), 1)

        # 5) 删空后重新铺开
        panel.clear()
        w._update_status_bar()
        self.assertFalse(overlay.isHidden())
        self.assertEqual(overlay.geometry(), table.viewport().rect())

    # ---- 状态栏 / 预览头的高度对齐 ----
    def test_18_status_bar_items_share_one_center_line(self):
        """状态栏与预览头的文字、文字按钮必须共用同一条视觉中线（tasks 2.5）。"""
        w = self.window
        w.resize(1440, 900)
        w.show()
        self.app.processEvents()

        bar = w.status_left_label.parent()
        items = [w.status_left_label, w.status_right_label, w.feedback_button, w.version_label]
        for wdg in items:
            # 文字按钮不得比状态栏的内层可用高度更高（32px 栏高 - 上下各 4px 内边距）
            self.assertLessEqual(wdg.height(), bar.height() - 8, f"{wdg.objectName()} 超出状态栏高度")
            self.assertGreaterEqual(wdg.y(), 0)
            self.assertLessEqual(wdg.y() + wdg.height(), bar.height())
        # 四个文字项与文字按钮必须同高：高度不等时「盒中心」会掩盖真实的墨迹偏移
        # （cocoa 实测 19px 标签与 24px 按钮盒中心只差 0.5px，墨迹中线却差 2px）
        heights = {wdg.height() for wdg in items}
        self.assertEqual(len(heights), 1, f"状态栏各文字项高度不一致: {sorted(heights)}")
        self.assertEqual(heights.pop(), 22, "状态栏文字项行高应为 22px")

        centers = [wdg.y() + wdg.height() / 2 for wdg in items]
        self.assertLessEqual(max(centers) - min(centers), 1.0, f"状态栏中线不齐: {centers}")

        header = w.preview_page_label.parent()
        row = [w.preview_page_label, w.preview_zoom_label, w.refresh_preview_btn]
        self.assertEqual({wdg.height() for wdg in row}, {24}, "预览头文字与按钮应同为 24px")
        centers = [wdg.y() + wdg.height() / 2 for wdg in row]
        self.assertLessEqual(max(centers) - min(centers), 1.0, f"预览头中线不齐: {centers}")

    def test_19_status_bar_heights_come_from_stylesheet(self):
        """状态栏行高必须由 QSS 作用域规则给出（代码里的 setFixedHeight 会被 QSS 覆盖）。"""
        from ui import tokens

        for dark in (False, True):
            qss = tokens.build_stylesheet(dark)
            self.assertIn("QFrame#statusBar QLabel#statusBarLabel", qss)
            self.assertIn("QFrame#statusBar QPushButton#textButton", qss)
            self.assertIn("QFrame#statusBar QLabel#versionLabel", qss)
            # 文字按钮的默认高度仍是 24px（预览头与对话框标题栏靠它）
            base = qss.split("QPushButton#textButton {", 1)[1].split("}", 1)[0]
            self.assertIn("min-height: 24px", base)
            self.assertIn("max-height: 24px", base)
            self.assertIn("padding: 0px 8px", base)


if __name__ == "__main__":
    unittest.main(verbosity=2)
