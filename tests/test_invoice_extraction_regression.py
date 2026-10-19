#!/usr/bin/env python3
"""
发票字段提取回归测试

使用 tests/fixtures/invoices 下的真实发票 PDF 样本，锁定各票种「金额/税额」
的提取结果，防止修改提取器逻辑时破坏此前已经正确的识别结果。

样本说明：
- 新版旅客运输服务电子发票（出租车/网约车出行）：金额取「价税合计（小写）」含税总额，
  税额取合计行税额；此前该版式被误识别为旧版出租车发票，金额取到明细行不含税金额、税额为 0。
- 普通发票 / 铁路电子客票：此前已识别正确，纳入测试用于回归保护。
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'code'))

from core.pdf_handler import PDFHandler


# 样本目录
FIXTURE_DIR = os.path.join(os.path.dirname(__file__), 'fixtures', 'invoices')

# 样本发票 → 期望提取结果：(文件名, 期望金额, 期望税额)
CASES = [
    # 新版旅客运输服务电子发票（出租车/网约车出行）
    ('0908 打车 家-高铁站 12.8.pdf', 12.80, 0.37),
    ('0925 打车 宿舍→石家庄正定机场 72.35.pdf', 72.35, 2.11),
    ('1008 打车 家-高铁站 19.06.pdf', 19.06, 0.56),
    ('1010 打车 团建 10.45.pdf', 10.45, 0.30),
    ('1014 打车 团建 9.32.pdf', 9.32, 0.27),
    ('1014 打车 团建 9.6.pdf', 9.60, 0.28),
    # 普通发票（此前已正确，防回归）
    ('2026-04-01-郑州衡量科技股份有限-24.27.pdf', 24.27, 0.24),
    # 铁路电子客票（无税额，防回归）
    ('2026-04-29-郑州衡量科技股份有限公司统一社会信用代码-496.pdf', 496.00, 0.0),
]


@unittest.skipUnless(os.path.isdir(FIXTURE_DIR), '缺少测试样本目录 tests/fixtures/invoices')
class TestInvoiceExtractionRegression(unittest.TestCase):
    """基于真实发票样本的提取结果回归测试"""

    def setUp(self):
        """初始化 PDF 处理器"""
        self.handler = PDFHandler()

    def _extract(self, file_name):
        """
        提取指定样本发票的字段

        参数:
            file_name: 样本文件名（位于 FIXTURE_DIR 下）

        返回值:
            dict or None: 提取结果字典，识别失败返回 None
        """
        path = os.path.join(FIXTURE_DIR, file_name)
        self.assertTrue(os.path.exists(path), f'缺少测试样本: {file_name}')
        return self.handler.extract_all_invoice_info(path)

    def test_amount_and_tax_extraction(self):
        """逐张校验样本发票的金额与税额提取结果"""
        for file_name, expected_amount, expected_tax in CASES:
            with self.subTest(file=file_name):
                info = self._extract(file_name)
                self.assertIsNotNone(info, f'{file_name} 未能识别')
                self.assertAlmostEqual(
                    info['amount'], expected_amount, places=2,
                    msg=f'{file_name} 金额提取错误'
                )
                self.assertAlmostEqual(
                    info['tax_amount'], expected_tax, places=2,
                    msg=f'{file_name} 税额提取错误'
                )


if __name__ == '__main__':
    unittest.main()
