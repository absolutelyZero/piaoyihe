#!/usr/bin/env python3
"""
MCP Tool handler 单元测试

不依赖真实 PDF 文件，通过 mock _new_pdf_handler 返回伪造的 PDFHandler。
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'code'))

from unittest.mock import patch, Mock
from mcp_server.tools import (
    handle_extract_invoice_info,
    handle_batch_rename_invoices,
    handle_export_invoice_list_from_paths,
    handle_export_invoice_list,
    handle_merge_invoices,
    handle_get_server_info,
    handle_get_supported_layouts,
    handle_get_supported_fields,
    _validate_pdf_paths,
    _ensure_output_dir,
)


class TestValidation(unittest.TestCase):
    """测试输入校验辅助函数"""

    def test_validate_pdf_paths_empty(self):
        """空列表应失败"""
        valid, msg = _validate_pdf_paths([])
        self.assertFalse(valid)
        self.assertIn('为空', msg)

    def test_validate_pdf_paths_not_list(self):
        """非列表应失败"""
        valid, msg = _validate_pdf_paths('a.pdf')
        self.assertFalse(valid)

    def test_validate_pdf_paths_non_pdf(self):
        """非 PDF 后缀应失败"""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            txt_path = f.name
        try:
            valid, msg = _validate_pdf_paths([txt_path])
            self.assertFalse(valid)
            self.assertIn('仅支持 PDF', msg)
        finally:
            os.unlink(txt_path)

    def test_validate_pdf_paths_missing(self):
        """不存在的 PDF 应失败"""
        valid, msg = _validate_pdf_paths(['/not/exist.pdf'])
        self.assertFalse(valid)
        self.assertIn('不存在', msg)

    def test_validate_pdf_paths_ok(self):
        """存在的 PDF 应通过"""
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            pdf_path = f.name
        try:
            valid, msg = _validate_pdf_paths([pdf_path])
            self.assertTrue(valid)
            self.assertEqual(msg, '')
        finally:
            os.unlink(pdf_path)


class TestTools(unittest.TestCase):
    """测试 MCP Tool handler"""

    @staticmethod
    def _fake_handler(info):
        """构造返回指定 info 的伪造 PDFHandler"""
        handler = Mock()
        handler.extract_all_invoice_info = Mock(return_value=info)
        return handler

    @patch('mcp_server.tools._new_pdf_handler')
    def test_extract_invoice_info_success(self, mock_new):
        """正常提取应返回 info"""
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            pdf_path = f.name
        try:
            mock_new.return_value = self._fake_handler({'amount': 100})
            result = handle_extract_invoice_info(pdf_path)
            self.assertTrue(result['success'])
            self.assertEqual(result['info']['amount'], 100)
        finally:
            os.unlink(pdf_path)

    @patch('mcp_server.tools._new_pdf_handler')
    def test_extract_invoice_info_non_pdf(self, mock_new):
        """传入 txt 文件应返回失败，不会调用 PDFHandler"""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            txt_path = f.name
        try:
            result = handle_extract_invoice_info(txt_path)
            self.assertFalse(result['success'])
            mock_new.assert_not_called()
        finally:
            os.unlink(txt_path)

    @patch('mcp_server.tools._new_pdf_handler')
    def test_batch_rename_dry_run(self, mock_new):
        """预览模式不应修改文件系统"""
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = []
            for name in ['a.pdf', 'b.pdf']:
                p = os.path.join(tmpdir, name)
                with open(p, 'w') as f:
                    pass
                paths.append(p)

            mock_new.return_value = self._fake_handler({
                'invoice_type': '普票',
                'invoice_date': '2024-01-01',
                'amount': 10,
                'invoice_code': '001',
                'buyer_name': 'A',
                'seller_name': 'B',
                'product_type': 'X',
            })
            result = handle_batch_rename_invoices(
                paths, '{发票类型}-{开票日期}', dry_run=True
            )
            self.assertTrue(result['success'])
            self.assertTrue(result['dry_run'])
            self.assertEqual(result['renamed_count'], 2)
            # 文件系统未改变
            self.assertTrue(os.path.exists(os.path.join(tmpdir, 'a.pdf')))
            self.assertTrue(os.path.exists(os.path.join(tmpdir, 'b.pdf')))

    @patch('mcp_server.tools._new_pdf_handler')
    def test_export_invoice_list_from_paths(self, mock_new):
        """按路径导出应生成 Excel"""
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, 'a.pdf')
            with open(pdf_path, 'w') as f:
                pass
            output_path = os.path.join(tmpdir, 'out.xlsx')

            mock_new.return_value = self._fake_handler({
                'amount': 10,
                'tax_amount': 1,
                'invoice_date': '2024-01-01',
                'invoice_code': '001',
            })
            result = handle_export_invoice_list_from_paths([pdf_path], output_path)
            self.assertTrue(result['success'])
            self.assertTrue(os.path.exists(output_path))

    @patch('mcp_server.tools._new_pdf_handler')
    def test_merge_invoices_success(self, mock_new):
        """合并成功应返回 output_path"""
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, 'a.pdf')
            output_path = os.path.join(tmpdir, 'out.pdf')
            with open(pdf_path, 'w') as f:
                pass

            handler = self._fake_handler({})
            handler.merge_pdfs = Mock(return_value=True)
            mock_new.return_value = handler

            result = handle_merge_invoices(
                [pdf_path], output_path,
                {'orientation': 'portrait', 'rows': 2, 'cols': 1}
            )
            self.assertTrue(result['success'])
            self.assertEqual(result['output_path'], output_path)
            handler.merge_pdfs.assert_called_once()

    @patch('mcp_server.tools._new_pdf_handler')
    def test_merge_invoices_failure(self, mock_new):
        """合并失败应返回 success=False"""
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, 'a.pdf')
            output_path = os.path.join(tmpdir, 'out.pdf')
            with open(pdf_path, 'w') as f:
                pass

            handler = self._fake_handler({})
            handler.merge_pdfs = Mock(return_value=False)
            mock_new.return_value = handler

            result = handle_merge_invoices(
                [pdf_path], output_path,
                {'orientation': 'portrait', 'rows': 2, 'cols': 1}
            )
            self.assertFalse(result['success'])

    @patch('mcp_server.tools._new_pdf_handler')
    def test_merge_invoices_with_margins(self, mock_new):
        """合并时传入页边距应透传到 layout 中"""
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, 'a.pdf')
            output_path = os.path.join(tmpdir, 'out.pdf')
            with open(pdf_path, 'w') as f:
                pass

            handler = self._fake_handler({})
            handler.merge_pdfs = Mock(return_value=True)
            mock_new.return_value = handler

            result = handle_merge_invoices(
                [pdf_path], output_path,
                {'orientation': 'portrait', 'rows': 2, 'cols': 1},
                margins={'top': 15, 'bottom': 15, 'left': 20, 'right': 20},
            )
            self.assertTrue(result['success'])

            # 验证 margins 被合并到 layout 中
            call_args = handler.merge_pdfs.call_args
            passed_layout = call_args[0][2]  # layout 参数位置
            self.assertIn('margins', passed_layout)
            self.assertEqual(passed_layout['margins']['top'], 15)
            self.assertEqual(passed_layout['margins']['left'], 20)

    @patch('mcp_server.tools._new_pdf_handler')
    def test_merge_invoices_with_crop_marks(self, mock_new):
        """合并时传入裁切线应透传到 layout 中"""
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, 'a.pdf')
            output_path = os.path.join(tmpdir, 'out.pdf')
            with open(pdf_path, 'w') as f:
                pass

            handler = self._fake_handler({})
            handler.merge_pdfs = Mock(return_value=True)
            mock_new.return_value = handler

            result = handle_merge_invoices(
                [pdf_path], output_path,
                {'orientation': 'portrait', 'rows': 2, 'cols': 1},
                crop_marks={'show': True, 'left_mm': 5, 'right_mm': 5},
            )
            self.assertTrue(result['success'])

            call_args = handler.merge_pdfs.call_args
            passed_layout = call_args[0][2]
            self.assertTrue(passed_layout['show_crop_marks'])
            self.assertEqual(passed_layout['crop_mark_left'], 5)
            self.assertEqual(passed_layout['crop_mark_right'], 5)

    @patch('mcp_server.tools._new_pdf_handler')
    def test_merge_invoices_with_both_params(self, mock_new):
        """同时传入页边距和裁切线都应正确透传"""
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, 'a.pdf')
            output_path = os.path.join(tmpdir, 'out.pdf')
            with open(pdf_path, 'w') as f:
                pass

            handler = self._fake_handler({})
            handler.merge_pdfs = Mock(return_value=True)
            mock_new.return_value = handler

            result = handle_merge_invoices(
                [pdf_path], output_path,
                {'orientation': 'landscape', 'rows': 2, 'cols': 2},
                margins={'top': 5, 'bottom': 5, 'left': 5, 'right': 5},
                crop_marks={'show': True, 'left_mm': 10, 'right_mm': 0},
            )
            self.assertTrue(result['success'])

            call_args = handler.merge_pdfs.call_args
            passed_layout = call_args[0][2]
            self.assertEqual(passed_layout['margins']['top'], 5)
            self.assertEqual(passed_layout['margins']['right'], 5)
            self.assertTrue(passed_layout['show_crop_marks'])
            self.assertEqual(passed_layout['crop_mark_left'], 10)
            self.assertEqual(passed_layout['crop_mark_right'], 0)

    @patch('mcp_server.tools._new_pdf_handler')
    def test_merge_invoices_exception(self, mock_new):
        """合并异常应返回 success=False 并携带异常信息"""
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, 'a.pdf')
            output_path = os.path.join(tmpdir, 'out.pdf')
            with open(pdf_path, 'w') as f:
                pass

            handler = self._fake_handler({})
            handler.merge_pdfs = Mock(side_effect=RuntimeError('合并异常'))
            mock_new.return_value = handler

            result = handle_merge_invoices(
                [pdf_path], output_path,
                {'orientation': 'portrait', 'rows': 2, 'cols': 1}
            )
            self.assertFalse(result['success'])
            self.assertIn('合并异常', result['message'])

    def test_merge_invoices_invalid_input(self):
        """合并输入校验失败时不应调用 handler"""
        result = handle_merge_invoices([], 'out.pdf', {})
        self.assertFalse(result['success'])

    def test_export_invoice_list_success(self):
        """直接传入 pdf_infos 应成功导出 Excel"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, 'out.xlsx')
            pdf_infos = [{
                'name': 'a.pdf',
                'amount': 10,
                'tax_amount': 1,
                'invoice_date': '2024-01-01',
                'invoice_code': '001',
                'path': '/a.pdf',
                'mod_time': '',
                'size': '',
            }]
            result = handle_export_invoice_list(pdf_infos, output_path)
            self.assertTrue(result['success'])
            self.assertTrue(os.path.exists(output_path))

    def test_export_invoice_list_empty(self):
        """空列表应返回失败"""
        result = handle_export_invoice_list([], 'out.xlsx')
        self.assertFalse(result['success'])

    @patch('mcp_server.tools.os.makedirs')
    def test_export_invoice_list_cannot_create_dir(self, mock_makedirs):
        """输出目录不可写应返回失败"""
        mock_makedirs.side_effect = PermissionError('权限不足')
        result = handle_export_invoice_list([{'name': 'a.pdf'}], '/root/out.xlsx')
        self.assertFalse(result['success'])
        self.assertIn('权限', result['message'])

    def test_get_server_info(self):
        """服务信息应包含 name/version/tools"""
        result = handle_get_server_info()
        self.assertEqual(result['name'], 'piaoyihe')
        self.assertIn('version', result)
        self.assertIsInstance(result['tools'], list)
        self.assertEqual(len(result['tools']), 9)

    def test_get_supported_layouts(self):
        """应返回非空布局列表"""
        result = handle_get_supported_layouts()
        self.assertIn('layouts', result)
        self.assertIsInstance(result['layouts'], list)
        self.assertTrue(len(result['layouts']) > 0)
        layout = result['layouts'][0]
        self.assertIn('orientation', layout)
        self.assertIn('rows', layout)
        self.assertIn('cols', layout)

    def test_get_supported_fields(self):
        """应返回非空字段列表"""
        result = handle_get_supported_fields()
        self.assertIn('fields', result)
        self.assertIsInstance(result['fields'], list)
        self.assertTrue(any(f['key'] == 'amount' for f in result['fields']))


class TestEnsureOutputDir(unittest.TestCase):
    """测试输出目录辅助函数"""

    def test_ensure_output_dir_create(self):
        """父目录不存在时应创建"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, 'new_dir', 'out.xlsx')
            valid, msg = _ensure_output_dir(output_path)
            self.assertTrue(valid)
            self.assertTrue(os.path.exists(os.path.dirname(output_path)))

    @patch('mcp_server.tools.os.makedirs')
    def test_ensure_output_dir_create_failed(self, mock_makedirs):
        """创建失败时应返回错误"""
        mock_makedirs.side_effect = OSError('创建失败')
        valid, msg = _ensure_output_dir('/some/path/out.xlsx')
        self.assertFalse(valid)
        self.assertIn('创建', msg)


class TestBatchRenameReal(unittest.TestCase):
    """测试实际重命名（非预览模式）"""

    @staticmethod
    def _fake_handler(info):
        handler = Mock()
        handler.extract_all_invoice_info = Mock(return_value=info)
        return handler

    @patch('mcp_server.tools._new_pdf_handler')
    def test_batch_rename_real(self, mock_new):
        """实际重命名应修改文件系统"""
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = []
            for name in ['a.pdf', 'b.pdf']:
                p = os.path.join(tmpdir, name)
                with open(p, 'w') as f:
                    pass
                paths.append(p)

            mock_new.return_value = self._fake_handler({
                'invoice_type': '普票',
                'invoice_date': '2024-01-01',
                'amount': 10,
                'invoice_code': '001',
                'buyer_name': 'A',
                'seller_name': 'B',
                'product_type': 'X',
            })
            result = handle_batch_rename_invoices(
                paths, '{发票类型}-{开票日期}', dry_run=False
            )
            self.assertTrue(result['success'])
            self.assertFalse(result['dry_run'])
            self.assertEqual(result['renamed_count'], 2)
            self.assertTrue(os.path.exists(os.path.join(tmpdir, '普票-2024-01-01.pdf')))
            self.assertTrue(os.path.exists(os.path.join(tmpdir, '普票-2024-01-01(1).pdf')))


if __name__ == '__main__':
    unittest.main()
