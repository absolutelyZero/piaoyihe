#!/usr/bin/env python3
"""
OFD处理核心功能

该模块提供OFD文件处理和发票字段提取功能。
与PDF处理器结构平行，完全独立。
"""

import os
import time
import tempfile
from typing import List, Optional
from .ofd_extractors.factory import OFDExtractorFactory


class OFDHandler:
    """
    OFD处理器类

    提供OFD文件处理和发票字段提取功能。
    所有方法与PDFHandler保持一致，便于统一接口层调用。

    Attributes:
        无实例属性
    """

    def __init__(self):
        """初始化OFD处理器"""
        pass

    def convert_to_pdf(self, ofd_path: str, output_path: Optional[str] = None) -> str:
        """
        将OFD文件转换为PDF

        Args:
            ofd_path: OFD文件路径
            output_path: 输出PDF路径，为None则创建临时文件

        Returns:
            str: 生成的PDF文件路径

        Raises:
            Exception: 转换失败时抛出异常
        """
        if output_path is None:
            fd, output_path = tempfile.mkstemp(suffix='.pdf')
            os.close(fd)

        try:
            # 使用easyofd库转换
            from easyofd.ofd import OFD
            import base64
            from PIL import Image
            import io

            ofd = OFD()

            # easyofd需要base64编码的数据
            with open(ofd_path, 'rb') as f:
                ofdb64 = str(base64.b64encode(f.read()), "utf-8")

            print(f"[OFDHandler] 开始解析OFD文件...")
            try:
                ofd.read(ofdb64, save_xml=False)
                print(f"[OFDHandler] OFD解析完成，开始转换PDF...")
            except (AssertionError, Exception) as ae:
                # easyofd在解析某些带签名的OFD时会失败，尝试忽略签名解析
                print(f"[OFDHandler] 标准解析失败，尝试备用方案: {ae}")
                # 尝试使用save_xml=True可能绕过某些问题
                try:
                    ofd.read(ofdb64, save_xml=True, xml_name="temp_ofd_parse")
                    print(f"[OFDHandler] 备用解析成功")
                except Exception as e2:
                    print(f"[OFDHandler] 备用解析也失败: {e2}")
                    # 最终备用方案：尝试使用PyMuPDF直接打开OFD
                    print(f"[OFDHandler] 尝试使用PyMuPDF直接处理OFD...")
                    try:
                        import fitz
                        doc = fitz.open(ofd_path)
                        # 直接保存为PDF
                        doc.save(output_path)
                        doc.close()
                        print(f"[OFDHandler] PyMuPDF转换成功: {output_path}")
                        return output_path
                    except Exception as e3:
                        print(f"[OFDHandler] PyMuPDF也失败: {e3}")
                        raise Exception(f"无法解析该OFD文件，可能是格式不受支持。原始错误: {ae}")

            try:
                pdf_bytes = ofd.to_pdf()
                print(f"[OFDHandler] PDF转换完成，类型: {type(pdf_bytes)}")

                # 确保pdf_bytes是字节类型
                if pdf_bytes is None:
                    raise Exception("to_pdf() 返回 None")
                elif isinstance(pdf_bytes, str):
                    pdf_bytes = pdf_bytes.encode('utf-8')
                elif isinstance(pdf_bytes, (list, tuple)):
                    # 如果是列表，取第一个元素
                    pdf_bytes = pdf_bytes[0] if pdf_bytes else b''
                    if isinstance(pdf_bytes, str):
                        pdf_bytes = pdf_bytes.encode('utf-8')

                # 写入输出文件
                with open(output_path, 'wb') as f:
                    f.write(pdf_bytes)

                print(f"[OFDHandler] PDF文件已保存: {output_path}")

            except Exception as pdf_error:
                print(f"[OFDHandler] PDF转换失败，尝试转换为图片: {pdf_error}")
                # 备用方案：转换为图片再合成PDF
                img_list = ofd.to_jpg()
                print(f"[OFDHandler] 图片转换完成，共 {len(img_list)} 页")

                if img_list:
                    # 将图片转换为PDF
                    pil_images = []
                    for img in img_list:
                        if isinstance(img, Image.Image):
                            pil_images.append(img)
                        else:
                            # 如果是numpy数组
                            pil_images.append(Image.fromarray(img))

                    if pil_images:
                        # 第一张图片保存为PDF，其余追加
                        first_img = pil_images[0]
                        if len(pil_images) > 1:
                            first_img.save(output_path, 'PDF', save_all=True, 
                                         append_images=pil_images[1:], resolution=100.0)
                        else:
                            first_img.save(output_path, 'PDF', resolution=100.0)
                        print(f"[OFDHandler] 通过图片方式保存PDF: {output_path}")
                else:
                    raise Exception("无法从OFD提取图片")

            ofd.del_data()
            return output_path

        except Exception as e:
            print(f"[OFDHandler] OFD转PDF失败: {str(e)}")
            import traceback
            traceback.print_exc()
            raise

    def extract_amount(self, ofd_path: str) -> float:
        """
        从OFD中提取金额

        Args:
            ofd_path: OFD文件路径

        Returns:
            float: 提取的金额，失败返回0.0
        """
        try:
            extractor = OFDExtractorFactory.get_extractor(ofd_path)
            if extractor:
                with extractor:
                    return extractor.extract_amount()
        except Exception as e:
            print(f"[OFDHandler] 提取金额失败: {str(e)}")
            return 0.0
        return 0.0

    def extract_invoice_date(self, ofd_path: str) -> str:
        """
        从OFD中提取开票日期

        Args:
            ofd_path: OFD文件路径

        Returns:
            str: 提取的开票日期，格式为YYYY-MM-DD，失败返回文件修改日期
        """
        try:
            extractor = OFDExtractorFactory.get_extractor(ofd_path)
            if extractor:
                with extractor:
                    return extractor.extract_invoice_date()
        except Exception as e:
            print(f"[OFDHandler] 提取开票日期失败: {str(e)}")

        # 返回文件修改日期作为备选
        try:
            mod_time = os.path.getmtime(ofd_path)
            return time.strftime('%Y-%m-%d', time.localtime(mod_time))
        except Exception:
            return time.strftime('%Y-%m-%d', time.localtime())

    def extract_invoice_type(self, ofd_path: str) -> str:
        """
        从OFD中提取发票类型

        Args:
            ofd_path: OFD文件路径

        Returns:
            str: 提取的发票类型，失败返回"普票"
        """
        try:
            extractor = OFDExtractorFactory.get_extractor(ofd_path)
            if extractor:
                with extractor:
                    return extractor.extract_invoice_type()
        except Exception as e:
            print(f"[OFDHandler] 提取发票类型失败: {str(e)}")
        return "普票"

    def extract_product_type(self, ofd_path: str) -> str:
        """
        从OFD中提取商品类型

        Args:
            ofd_path: OFD文件路径

        Returns:
            str: 提取的商品类型，失败返回"商品"
        """
        try:
            extractor = OFDExtractorFactory.get_extractor(ofd_path)
            if extractor:
                with extractor:
                    return extractor.extract_product_type()
        except Exception as e:
            print(f"[OFDHandler] 提取商品类型失败: {str(e)}")
            return "商品"
        return "商品"

    def extract_buyer_name(self, ofd_path: str) -> str:
        """
        从OFD中提取购买方名称

        Args:
            ofd_path: OFD文件路径

        Returns:
            str: 提取的购买方名称，失败返回"购买方"
        """
        try:
            extractor = OFDExtractorFactory.get_extractor(ofd_path)
            if extractor:
                with extractor:
                    return extractor.extract_buyer_name()
        except Exception as e:
            print(f"[OFDHandler] 提取购买方名称失败: {str(e)}")
            return "购买方"
        return "购买方"

    def extract_seller_name(self, ofd_path: str) -> str:
        """
        从OFD中提取销售方名称

        Args:
            ofd_path: OFD文件路径

        Returns:
            str: 提取的销售方名称，失败返回"销售方"
        """
        try:
            extractor = OFDExtractorFactory.get_extractor(ofd_path)
            if extractor:
                with extractor:
                    return extractor.extract_seller_name()
        except Exception as e:
            print(f"[OFDHandler] 提取销售方名称失败: {str(e)}")
            return "销售方"
        return "销售方"

    def extract_invoice_code(self, ofd_path: str) -> str:
        """
        从OFD中提取发票号码

        Args:
            ofd_path: OFD文件路径

        Returns:
            str: 提取的发票号码，失败返回空字符串
        """
        try:
            extractor = OFDExtractorFactory.get_extractor(ofd_path)
            if extractor:
                with extractor:
                    return extractor.extract_invoice_code()
        except Exception as e:
            print(f"[OFDHandler] 提取发票号码失败: {str(e)}")
            return ""
        return ""

    def extract_tax_amount(self, ofd_path: str) -> float:
        """
        从OFD中提取税额

        Args:
            ofd_path: OFD文件路径

        Returns:
            float: 提取的税额，失败返回0.0
        """
        try:
            extractor = OFDExtractorFactory.get_extractor(ofd_path)
            if extractor:
                with extractor:
                    return extractor.extract_tax_amount()
        except Exception as e:
            print(f"[OFDHandler] 提取税额失败: {str(e)}")
            return 0.0
        return 0.0

    def extract_all_invoice_info(self, ofd_path: str) -> Optional[dict]:
        """
        一次性提取所有发票信息

        Args:
            ofd_path: OFD文件路径

        Returns:
            dict or None: 包含所有字段信息的字典，无法识别则返回None
                - amount: 金额
                - invoice_date: 开票日期
                - invoice_type: 发票类型
                - product_type: 商品类型
                - buyer_name: 购买方名称
                - seller_name: 销售方名称
                - invoice_code: 发票号码
                - tax_amount: 税额
        """
        try:
            extractor = OFDExtractorFactory.get_extractor(ofd_path)
            if extractor:
                with extractor:
                    return extractor.extract_all()
            else:
                return None
        except Exception as e:
            print(f"[OFDHandler] 提取发票信息失败: {str(e)}")
            return None
