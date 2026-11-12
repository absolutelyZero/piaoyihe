#!/usr/bin/env python3
"""
OFD 支持单元测试

覆盖 OFD 文件识别、受支持文件判定、渲染异常处理、
OFD 混合合并、字段跳过、批量重命名跳过以及 MCP 路径校验。
"""

import os
import sys
import shutil
import tempfile
import importlib.util
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'code'))

from unittest.mock import patch, Mock

import fitz
from PIL import Image

from core.ofd_converter import is_ofd_file, render_ofd_pages, OfdConversionError
from core.pdf_handler import PDFHandler, is_supported_file
from core.invoice_service import InvoiceService
from mcp_server.tools import _validate_pdf_paths


class TestFileTypeDetection(unittest.TestCase):
    """测试 OFD / 受支持文件类型判定"""

    def test_is_ofd_file(self):
        """扩展名 .ofd（大小写不敏感）应识别为 OFD"""
        self.assertTrue(is_ofd_file('a.ofd'))
        self.assertTrue(is_ofd_file('A.OFD'))
        self.assertFalse(is_ofd_file('a.pdf'))
        self.assertFalse(is_ofd_file('a.png'))
        self.assertFalse(is_ofd_file(''))
        self.assertFalse(is_ofd_file(None))

    def test_is_supported_file(self):
        """PDF / 图片 / OFD 应受支持，其他类型不受支持"""
        self.assertTrue(is_supported_file('a.pdf'))
        self.assertTrue(is_supported_file('a.PNG'))
        self.assertTrue(is_supported_file('a.ofd'))
        self.assertFalse(is_supported_file('a.txt'))
        self.assertFalse(is_supported_file(''))
        self.assertFalse(is_supported_file(None))


class TestOfdRenderer(unittest.TestCase):
    """测试 OFD 渲染封装的异常处理"""

    def test_render_missing_file(self):
        """文件不存在时应抛出 OfdConversionError"""
        with self.assertRaises(OfdConversionError):
            render_ofd_pages('not/exist/file.ofd')

    def test_render_invalid_ofd(self):
        """非法的 OFD 内容应抛出 OfdConversionError 而非崩溃"""
        tmp_dir = tempfile.mkdtemp()
        try:
            bad_path = os.path.join(tmp_dir, 'bad.ofd')
            with open(bad_path, 'w', encoding='utf-8') as f:
                f.write('this is not a real ofd file')

            with self.assertRaises(OfdConversionError):
                render_ofd_pages(bad_path, cache_root=os.path.join(tmp_dir, 'cache'))
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    @unittest.skipUnless(
        importlib.util.find_spec('ofd2pdf') is not None,
        'ofd2pdf 未安装（requirements 中为平台条件依赖），跳过依赖其 mock 的用例'
    )
    @patch('ofd2pdf.render_ofd')
    def test_render_cache_reuse(self, mock_render):
        """同一文件重复渲染应命中缓存，仅调用底层渲染一次"""
        tmp_dir = tempfile.mkdtemp()
        try:
            ofd_path = os.path.join(tmp_dir, 'demo.ofd')
            with open(ofd_path, 'wb') as f:
                f.write(b'fake ofd content')
            cache_root = os.path.join(tmp_dir, 'cache')

            def fake_render(ofd_path, out_dir, **kwargs):
                """模拟 ofd-cli 渲染出单页 PNG"""
                out_dir = str(out_dir)
                os.makedirs(out_dir, exist_ok=True)
                page = os.path.join(out_dir, 'page_doc1_page1.png')
                Image.new('RGB', (10, 10), 'white').save(page)
                return [page]

            mock_render.side_effect = fake_render

            first = render_ofd_pages(ofd_path, cache_root=cache_root)
            second = render_ofd_pages(ofd_path, cache_root=cache_root)

            self.assertEqual(len(first), 1)
            self.assertEqual(first, second)
            self.assertEqual(mock_render.call_count, 1)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)


class TestBuildFileInfo(unittest.TestCase):
    """测试 OFD 文件在列表中的字段缺省行为"""

    def test_ofd_build_file_info_empty_fields(self):
        """OFD 文件应跳过字段提取，返回空字段"""
        from ui.file_list import FileListPanel

        tmp_dir = tempfile.mkdtemp()
        try:
            ofd_path = os.path.join(tmp_dir, 'demo.ofd')
            with open(ofd_path, 'wb') as f:
                f.write(b'fake ofd content')

            handler = Mock()
            file_info = FileListPanel.build_file_info(handler, ofd_path)

            self.assertEqual(file_info['name'], 'demo.ofd')
            self.assertEqual(file_info['amount'], 0.0)
            self.assertEqual(file_info['tax_amount'], 0.0)
            self.assertEqual(file_info['invoice_date'], '')
            self.assertEqual(file_info['invoice_code'], '')
            # 不应触发字段提取
            handler.extract_amount.assert_not_called()
            handler.extract_all_invoice_info.assert_not_called()
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)


class TestRenameSkipOfd(unittest.TestCase):
    """测试批量重命名跳过 OFD 文件"""

    def test_batch_rename_skips_ofd(self):
        """OFD 文件不应参与重命名，计入 skipped_ofd_count"""
        handler = Mock()
        service = InvoiceService(handler)

        result = service.batch_rename(
            ['a.ofd', 'b.OFD'], {'vat_invoice': '{金额}'}, dry_run=True
        )

        self.assertEqual(result['skipped_ofd_count'], 2)
        self.assertEqual(result['renamed_count'], 0)
        self.assertEqual(result['skipped_image_count'], 0)
        handler.extract_all_invoice_info.assert_not_called()


class TestMergeWithOfd(unittest.TestCase):
    """测试 OFD 与图片/PDF 混合合并"""

    def setUp(self):
        """创建临时目录"""
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """清理临时目录"""
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _make_png(self, name):
        """生成一张真实 PNG 图片，模拟 OFD 渲染结果"""
        path = os.path.join(self.tmp_dir, name)
        Image.new('RGB', (400, 250), 'white').save(path)
        return path

    @patch('core.pdf_handler.render_ofd_pages')
    def test_merge_single_page_ofd(self, mock_render):
        """单个 OFD（单页）应合并为一页 PDF"""
        mock_render.return_value = [self._make_png('ofd_doc1_page1.png')]

        output = os.path.join(self.tmp_dir, 'out1.pdf')
        ok = PDFHandler().merge_pdfs(
            ['invoice.ofd'], output,
            {'orientation': 'portrait', 'rows': 1, 'cols': 1, 'rotate': 0}
        )

        self.assertTrue(ok)
        mock_render.assert_called_once()
        with fitz.open(output) as doc:
            self.assertEqual(len(doc), 1)

    @patch('core.pdf_handler.render_ofd_pages')
    def test_merge_multipage_ofd_fills_cells(self, mock_render):
        """多页 OFD 每页作为一个排版单元，按单元格排布"""
        mock_render.return_value = [
            self._make_png('ofd_doc1_page1.png'),
            self._make_png('ofd_doc1_page2.png'),
        ]

        output = os.path.join(self.tmp_dir, 'out2.pdf')
        ok = PDFHandler().merge_pdfs(
            ['invoice.ofd'], output,
            {'orientation': 'landscape', 'rows': 1, 'cols': 2, 'rotate': 0}
        )

        self.assertTrue(ok)
        with fitz.open(output) as doc:
            self.assertEqual(len(doc), 1)

    @patch('core.pdf_handler.render_ofd_pages')
    def test_merge_ofd_failure_is_skipped(self, mock_render):
        """OFD 渲染失败时应跳过该文件，其余文件正常合并"""
        mock_render.side_effect = OfdConversionError('模拟渲染失败')
        png_path = self._make_png('normal.png')

        output = os.path.join(self.tmp_dir, 'out3.pdf')
        ok = PDFHandler().merge_pdfs(
            ['bad.ofd', png_path], output,
            {'orientation': 'portrait', 'rows': 1, 'cols': 1, 'rotate': 0}
        )

        self.assertTrue(ok)
        with fitz.open(output) as doc:
            self.assertEqual(len(doc), 1)


class TestMcpValidationOfd(unittest.TestCase):
    """测试 MCP 路径校验放行 OFD / 图片"""

    def test_validate_accepts_ofd(self):
        """存在的 .ofd 路径应通过校验"""
        with tempfile.NamedTemporaryFile(suffix='.ofd', delete=False) as f:
            ofd_path = f.name
        try:
            valid, msg = _validate_pdf_paths([ofd_path])
            self.assertTrue(valid)
            self.assertEqual(msg, '')
        finally:
            os.unlink(ofd_path)

    def test_validate_accepts_image(self):
        """存在的 .png 路径应通过校验"""
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            png_path = f.name
        try:
            valid, msg = _validate_pdf_paths([png_path])
            self.assertTrue(valid)
        finally:
            os.unlink(png_path)

    def test_validate_rejects_unsupported(self):
        """不受支持的后缀（如 .txt）应失败"""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            txt_path = f.name
        try:
            valid, msg = _validate_pdf_paths([txt_path])
            self.assertFalse(valid)
            self.assertIn('仅支持', msg)
        finally:
            os.unlink(txt_path)


if __name__ == '__main__':
    unittest.main()