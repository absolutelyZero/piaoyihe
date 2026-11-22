#!/usr/bin/env python3
"""
分割线跟随裁切线开关显隐的单元测试

覆盖：裁切线关闭时无分割线、开启时绘制分割线且位置/样式不变、
单发票布局不绘制分割线、配置缺省 show_crop_marks 时按关闭处理。
"""

import os
import sys
import shutil
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'code'))

import fitz
from PIL import Image

from core.pdf_handler import PDFHandler


MM_TO_PT = 72.0 / 25.4


class TestDividerVisibility(unittest.TestCase):
    """验证分割线的显示由裁切线开关统一控制"""

    def setUp(self):
        """创建临时目录"""
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """清理临时目录"""
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _make_pngs(self, count):
        """
        生成指定数量的纯白 PNG 图片，作为合并输入

        参数:
            count: 需要生成的图片数量

        返回:
            list[str]: 图片文件绝对路径列表
        """
        paths = []
        for index in range(count):
            path = os.path.join(self.tmp_dir, f'img_{index}.png')
            Image.new('RGB', (400, 250), 'white').save(path)
            paths.append(path)
        return paths

    def _merge(self, layout_config, count=4, output_name='merged.pdf'):
        """
        使用指定布局配置合并若干图片

        参数:
            layout_config: 布局配置字典
            count: 参与合并的图片数量
            output_name: 输出 PDF 文件名

        返回:
            str: 输出 PDF 的绝对路径
        """
        output_path = os.path.join(self.tmp_dir, output_name)
        success = PDFHandler().merge_pdfs(self._make_pngs(count), output_path, layout_config)
        self.assertTrue(success, '合并应成功')
        return output_path

    def _collect_points(self, pdf_path):
        """
        收集 PDF 首页所有线段的端点坐标

        参数:
            pdf_path: PDF 文件路径

        返回:
            tuple[list[float], list[float], list[dict]]: (所有点的 x 坐标, 所有点的 y 坐标, 绘图对象列表)
        """
        x_coords = []
        y_coords = []
        drawings = []
        with fitz.open(pdf_path) as doc:
            page = doc[0]
            drawings = page.get_drawings()
            for drawing in drawings:
                for item in drawing.get('items', []):
                    if item[0] == 'l':
                        for point in item[1:3]:
                            x_coords.append(point.x)
                            y_coords.append(point.y)
        return x_coords, y_coords, drawings

    def test_dividers_hidden_when_crop_marks_off(self):
        """裁切线未勾选时不应绘制任何分割线"""
        pdf_path = self._merge({
            'orientation': 'landscape', 'rows': 2, 'cols': 2,
            'rotate': 0, 'show_crop_marks': False,
            'crop_mark_left': 5, 'crop_mark_right': 5,
        })
        _, _, drawings = self._collect_points(pdf_path)
        self.assertEqual(len(drawings), 0, '裁切线关闭时不应产生任何线段')

    def test_dividers_shown_when_crop_marks_on(self):
        """裁切线勾选时应在 2x2 布局中绘制分割线，且样式保持不变"""
        pdf_path = self._merge({
            'orientation': 'landscape', 'rows': 2, 'cols': 2,
            'rotate': 0, 'show_crop_marks': True,
            'crop_mark_left': 5, 'crop_mark_right': 5,
        })
        x_coords, y_coords, drawings = self._collect_points(pdf_path)
        self.assertGreater(len(drawings), 0, '裁切线开启时应有分割线/裁切线')

        # 样式保持不变：灰色虚线、线宽 0.5
        for drawing in drawings:
            self.assertAlmostEqual(drawing['color'][0], 0.7, places=3)
            self.assertAlmostEqual(drawing['color'][1], 0.7, places=3)
            self.assertAlmostEqual(drawing['color'][2], 0.7, places=3)
            self.assertAlmostEqual(drawing['width'], 0.5, places=3)

        # A4 横向 842x595，页边距默认 10mm，2x2 时分割线位于可用区域中点
        mid_y = 10 * MM_TO_PT + (595 - 20 * MM_TO_PT) / 2
        mid_x = 10 * MM_TO_PT + (842 - 20 * MM_TO_PT) / 2
        self.assertTrue(any(abs(y - mid_y) < 1 for y in y_coords), '应存在位于垂直中线的水平分割线')
        self.assertTrue(any(abs(x - mid_x) < 1 for x in x_coords), '应存在位于水平中线的垂直分割线')

    def test_dividers_only_without_crop_marks_distance(self):
        """裁切线勾选但左右距离为 0 时，仅显示分割线"""
        pdf_path = self._merge({
            'orientation': 'landscape', 'rows': 2, 'cols': 2,
            'rotate': 0, 'show_crop_marks': True,
            'crop_mark_left': 0, 'crop_mark_right': 0,
        })
        _, _, drawings = self._collect_points(pdf_path)
        self.assertGreater(len(drawings), 0, '应仍绘制分割线')

    def test_single_cell_has_no_dividers(self):
        """单发票布局（1x1）即使勾选裁切线也不绘制分割线"""
        pdf_path = self._merge({
            'orientation': 'portrait', 'rows': 1, 'cols': 1,
            'rotate': 0, 'show_crop_marks': True,
            'crop_mark_left': 0, 'crop_mark_right': 0,
        }, count=1)
        _, _, drawings = self._collect_points(pdf_path)
        self.assertEqual(len(drawings), 0, '1x1 布局不应绘制分割线')

    def test_missing_show_crop_marks_defaults_to_off(self):
        """配置缺省 show_crop_marks 时按关闭处理"""
        pdf_path = self._merge({
            'orientation': 'landscape', 'rows': 2, 'cols': 2,
            'rotate': 0, 'crop_mark_left': 5, 'crop_mark_right': 5,
        })
        _, _, drawings = self._collect_points(pdf_path)
        self.assertEqual(len(drawings), 0, '缺省配置应不显示分割线')


if __name__ == '__main__':
    unittest.main()
