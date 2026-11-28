#!/usr/bin/env python3
"""
更新检查器测试

覆盖版本清单读取、版本比较、忽略版本与失败降级：
- 清单合法时返回 UpdateInfo（含 release_url / tag）
- 版本相等、远程更低、清单字段缺失时返回 None
- 响应非 JSON、version 非法、网络异常时不抛异常且 last_error 有值

可直接以 python -m unittest tests.test_update_checker 运行。
"""

import json
import os
import sys
import unittest
from unittest import mock

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in (os.path.join(_ROOT, "code"), os.path.join(_ROOT, ".pylibs")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from core.update_checker import UpdateChecker, UpdateInfo  # noqa: E402


class _FakeResponse:
    """最小化的 urlopen 响应替身，只提供 read() 与上下文管理。"""

    def __init__(self, payload):
        self._payload = payload.encode("utf-8") if isinstance(payload, str) else payload

    def read(self):
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class UpdateCheckerTests(unittest.TestCase):
    def setUp(self):
        import tempfile

        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.version_file = os.path.join(self._tmpdir.name, "version.json")
        self.config_file = os.path.join(self._tmpdir.name, "config.json")
        self._write_json(self.version_file, {"version": "0.1.16"})
        self._write_json(self.config_file, {"layout": 0})

    def _write_json(self, path, data):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)

    def _read_json(self, path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _checker(self, payload=None, exc=None):
        """构造 checker，并把 urlopen 换成返回 payload 或抛 exc 的替身。"""
        checker = UpdateChecker(
            local_version_file=self.version_file,
            config_file=self.config_file,
            remote_version_url="https://example.invalid/version.json",
        )
        if exc is not None:
            patcher = mock.patch("core.update_checker.request.urlopen", side_effect=exc)
        else:
            patcher = mock.patch(
                "core.update_checker.request.urlopen", return_value=_FakeResponse(payload)
            )
        patcher.start()
        self.addCleanup(patcher.stop)
        return checker

    # ---- 有新版本 ----

    def test_newer_version_returns_update_info(self):
        payload = json.dumps({
            "version": "0.1.17",
            "tag": "v0.1.17",
            "release_url": "https://github.com/absolutelyZero/piaoyihe/releases/tag/v0.1.17",
        })
        info = self._checker(payload).check_for_updates()

        self.assertIsInstance(info, UpdateInfo)
        self.assertEqual(info.version, "0.1.17")
        self.assertEqual(info.tag, "v0.1.17")
        self.assertIn("/releases/tag/v0.1.17", info.release_url)

    def test_missing_optional_fields_do_not_break_check(self):
        info = self._checker(json.dumps({"version": "0.1.17"})).check_for_updates()

        self.assertIsInstance(info, UpdateInfo)
        self.assertEqual(info.version, "0.1.17")
        self.assertEqual(info.release_url, "")
        self.assertEqual(info.tag, "")

    def test_multi_digit_segment_compared_numerically(self):
        # 0.1.10 必须大于 0.1.9（按数字比较，不是按字符串）
        self._write_json(self.version_file, {"version": "0.1.9"})
        info = self._checker(json.dumps({"version": "0.1.10"})).check_for_updates()
        self.assertIsInstance(info, UpdateInfo)
        self.assertEqual(info.version, "0.1.10")

    # ---- 无更新 ----

    def test_same_version_returns_none(self):
        checker = self._checker(json.dumps({"version": "0.1.16"}))
        self.assertIsNone(checker.check_for_updates())
        self.assertIsNone(checker.last_error)

    def test_lower_version_returns_none(self):
        self.assertIsNone(self._checker(json.dumps({"version": "0.1.15"})).check_for_updates())

    # ---- 失败降级 ----

    def test_non_json_response_is_reported_not_raised(self):
        checker = self._checker("<html>captive portal</html>")
        self.assertIsNone(checker.check_for_updates())
        self.assertIsNotNone(checker.last_error)
        self.assertIn("JSON", checker.last_error)

    def test_invalid_version_field_is_reported_not_raised(self):
        checker = self._checker(json.dumps({"version": "latest"}))
        self.assertIsNone(checker.check_for_updates())
        self.assertIsNotNone(checker.last_error)
        self.assertIn("version", checker.last_error)

    def test_network_error_is_reported_not_raised(self):
        checker = self._checker(exc=OSError("network unreachable"))
        self.assertIsNone(checker.check_for_updates())
        self.assertIsNotNone(checker.last_error)
        self.assertIn("network unreachable", checker.last_error)

    # ---- 忽略版本 ----

    def test_ignored_version_is_skipped(self):
        checker = self._checker(json.dumps({"version": "0.1.17"}))
        checker._set_ignored_version("0.1.17")
        self.assertIsNone(checker.check_for_updates())

    def test_force_check_overrides_ignored_version(self):
        checker = self._checker(json.dumps({"version": "0.1.17"}))
        checker._set_ignored_version("0.1.17")
        info = checker.check_for_updates(ignore_ignored_version=True)
        self.assertIsInstance(info, UpdateInfo)
        self.assertEqual(info.version, "0.1.17")

    def test_ignored_version_persists_across_instances(self):
        checker = self._checker(json.dumps({"version": "0.1.17"}))
        checker._set_ignored_version("0.1.17")

        # 重新构造 checker 仍能读到写入的忽略版本
        fresh = UpdateChecker(
            local_version_file=self.version_file, config_file=self.config_file
        )
        self.assertEqual(fresh._get_ignored_version(), "0.1.17")
        # 其他配置键名不受影响
        self.assertIn("layout", self._read_json(self.config_file))

    # ---- 版本比较 ----

    def test_version_comparison_edge_cases(self):
        greater = UpdateChecker._is_version_greater_than
        self.assertTrue(greater("0.1.10", "0.1.9"))
        self.assertFalse(greater("0.2", "0.2.0"))
        self.assertFalse(greater("0.1.16", "0.1.16"))
        self.assertTrue(greater("1.0", "0.9.9"))
        self.assertFalse(greater("abc", "0.1.0"))


try:
    from PySide6.QtWidgets import QApplication

    HAS_QT = True
except Exception:  # pragma: no cover - 无 PySide6 时跳过
    HAS_QT = False


@unittest.skipUnless(HAS_QT, "PySide6 不可用")
class AutoCheckSilenceTests(unittest.TestCase):
    """自动检查失败时必须静默：不弹窗、不抛异常、不阻塞启动。"""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        import tempfile

        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.version_file = os.path.join(self._tmpdir.name, "version.json")
        self.config_file = os.path.join(self._tmpdir.name, "config.json")
        with open(self.version_file, "w", encoding="utf-8") as f:
            json.dump({"version": "0.1.16"}, f)
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump({"layout": 0}, f)

    def _run_immediately(self):
        """把 QTimer.singleShot 换成同步执行，避免测试依赖事件循环。"""
        from core import update_checker

        patcher = mock.patch.object(
            update_checker.QTimer, "singleShot", side_effect=lambda ms, fn: fn()
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_network_failure_does_not_show_dialog(self):
        from core import update_checker

        self._run_immediately()
        shown = []
        with mock.patch(
            "core.update_checker.request.urlopen", side_effect=OSError("offline")
        ), mock.patch(
            "core.update_checker.show_update_dialog", side_effect=lambda *a: shown.append(a)
        ):
            update_checker.check_updates_on_start(None, self.version_file, self.config_file)

        self.assertEqual(shown, [])

    def test_new_version_shows_dialog_with_update_info(self):
        from core import update_checker

        self._run_immediately()
        payload = json.dumps({
            "version": "0.1.17",
            "tag": "v0.1.17",
            "release_url": "https://example.invalid/releases/tag/v0.1.17",
        })
        shown = []
        with mock.patch(
            "core.update_checker.request.urlopen", return_value=_FakeResponse(payload)
        ), mock.patch(
            "core.update_checker.show_update_dialog", side_effect=lambda *a: shown.append(a)
        ):
            update_checker.check_updates_on_start(None, self.version_file, self.config_file)

        self.assertEqual(len(shown), 1)
        info = shown[0][1]
        self.assertEqual(info.version, "0.1.17")


@unittest.skipUnless(HAS_QT, "PySide6 不可用")
class UpdateCheckWorkerTests(unittest.TestCase):
    """手动检查用的后台线程：成功发 checked，失败发 failed，不阻塞主线程。"""

    def setUp(self):
        import tempfile

        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.version_file = os.path.join(self._tmpdir.name, "version.json")
        self.config_file = os.path.join(self._tmpdir.name, "config.json")
        with open(self.version_file, "w", encoding="utf-8") as f:
            json.dump({"version": "0.1.16"}, f)
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump({"layout": 0}, f)

    def test_success_emits_checked_with_update_info(self):
        from PySide6.QtWidgets import QApplication

        from core.update_checker import UpdateCheckWorker, UpdateInfo

        _app = QApplication.instance() or QApplication([])
        payload = json.dumps({
            "version": "0.1.17",
            "tag": "v0.1.17",
            "release_url": "https://example.invalid/releases/tag/v0.1.17",
        })
        received = []
        worker = UpdateCheckWorker(self.version_file, self.config_file)
        worker.checked.connect(lambda info: received.append(info))
        with mock.patch(
            "core.update_checker.request.urlopen", return_value=_FakeResponse(payload)
        ):
            worker.run()

        self.assertEqual(len(received), 1)
        self.assertIsInstance(received[0], UpdateInfo)
        self.assertEqual(received[0].version, "0.1.17")

    def test_no_update_emits_checked_none(self):
        from PySide6.QtWidgets import QApplication

        from core.update_checker import UpdateCheckWorker

        _app = QApplication.instance() or QApplication([])
        payload = json.dumps({"version": "0.1.16", "tag": "v0.1.16", "release_url": ""})
        received = []
        worker = UpdateCheckWorker(self.version_file, self.config_file)
        worker.checked.connect(lambda info: received.append(info))
        with mock.patch(
            "core.update_checker.request.urlopen", return_value=_FakeResponse(payload)
        ):
            worker.run()

        self.assertEqual(received, [None])

    def test_network_failure_emits_failed(self):
        from PySide6.QtWidgets import QApplication

        from core.update_checker import UpdateCheckWorker

        _app = QApplication.instance() or QApplication([])
        checked, failed = [], []
        worker = UpdateCheckWorker(self.version_file, self.config_file)
        worker.checked.connect(lambda info: checked.append(info))
        worker.failed.connect(lambda msg: failed.append(msg))
        with mock.patch(
            "core.update_checker.request.urlopen", side_effect=OSError("offline")
        ):
            worker.run()

        self.assertEqual(checked, [])
        self.assertEqual(len(failed), 1)
        self.assertIn("offline", failed[0])


@unittest.skipUnless(HAS_QT, "PySide6 不可用")
class UpdateDialogStateTests(unittest.TestCase):
    """弹窗三态：构造即可显示，结果由回填方法写入，不依赖网络。"""

    def setUp(self):
        from PySide6.QtWidgets import QApplication

        import tempfile

        self._app = QApplication.instance() or QApplication([])
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.config_file = os.path.join(self._tmpdir.name, "config.json")
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump({"layout": 0}, f)

    def _dialog(self):
        from core.update_checker import UpdateDialog

        return UpdateDialog(None, "0.1.16", self.config_file)

    def test_dialog_renders_before_network(self):
        from core.update_checker import TEXT_CHECKING

        dialog = self._dialog()
        self.assertIn("当前版本", dialog.current_label.text())
        self.assertEqual(dialog.latest_label.text(), TEXT_CHECKING)
        # 页脚只有稍后与忽略此版本，没有「立即更新」
        self.assertFalse(hasattr(dialog, "view_button"))
        dialog.close()

    def test_set_update_info_shows_version_and_link(self):
        from core.update_checker import UpdateDialog, UpdateInfo

        dialog = self._dialog()
        dialog.set_update_info(
            UpdateInfo(
                version="0.1.17",
                release_url="https://example.invalid/releases/tag/v0.1.17",
                tag="v0.1.17",
            )
        )
        self.assertIn("0.1.17", dialog.latest_label.text())
        self.assertIn("https://example.invalid", dialog.release_label.text())
        self.assertTrue(dialog.release_label.isVisible() or not dialog.isVisible())
        dialog.close()

    def test_set_check_failed_shows_text(self):
        from core.update_checker import TEXT_CHECK_FAILED

        dialog = self._dialog()
        dialog.set_check_failed()
        self.assertEqual(dialog.latest_label.text(), TEXT_CHECK_FAILED)
        dialog.close()

    def test_result_after_close_is_discarded(self):
        from core.update_checker import TEXT_CHECKING, UpdateInfo

        dialog = self._dialog()
        dialog.close()
        dialog._on_worker_checked(
            UpdateInfo("0.1.17", "https://example.invalid/x", "v0.1.17")
        )
        dialog._on_worker_failed("boom")
        self.assertEqual(dialog.latest_label.text(), TEXT_CHECKING)

    def test_ignore_button_persists_ignored_version(self):
        from core.update_checker import UpdateInfo

        dialog = self._dialog()
        dialog.set_update_info(
            UpdateInfo("0.1.17", "https://example.invalid/x", "v0.1.17")
        )
        dialog._ignore_version()
        with open(self.config_file, "r", encoding="utf-8") as f:
            self.assertEqual(json.load(f)["ignored_version"], "0.1.17")


if __name__ == "__main__":
    unittest.main()
