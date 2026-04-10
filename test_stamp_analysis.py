#!/usr/bin/env python3
"""
测试脚本：分析PDF中的监制章对象类型

功能：
1. 遍历PDF页面中的所有对象
2. 识别图片、矢量图形、表单域等不同类型对象
3. 输出详细的对象信息帮助定位监制章
"""

import fitz
import sys
import os

def analyze_pdf_stamps(pdf_path):
    """
    分析PDF中的监制章对象
    
    Args:
        pdf_path (str): PDF文件路径
    """
    try:
        doc = fitz.open(pdf_path)
        print(f"分析PDF文件: {pdf_path}")
        print(f"总页数: {len(doc)}\n")
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            print(f"=== 第 {page_num + 1} 页 ===")
            
            # 1. 检查页面中的图片
            images = page.get_images(full=True)
            print(f"图片数量: {len(images)}")
            for img_idx, img in enumerate(images):
                xref = img[0]
                width = img[2]
                height = img[3]
                colorspace = img[1]
                print(f"  图片 {img_idx + 1}: xref={xref}, 尺寸={width}x{height}, 色彩空间={colorspace}")
            
            # 2. 检查页面中的表单域
            widgets = list(page.widgets()) if page.widgets() else []
            if widgets:
                print(f"\n表单域数量: {len(widgets)}")
                for widget_idx, widget in enumerate(widgets):
                    print(f"  表单域 {widget_idx + 1}: 类型={widget.field_type}, 名称={widget.field_name}")
            
            # 3. 检查页面中的注释
            annotations = list(page.annots()) if page.annots() else []
            if annotations:
                print(f"\n注释数量: {len(annotations)}")
                for annot_idx, annot in enumerate(annotations):
                    print(f"  注释 {annot_idx + 1}: 类型={annot.type}")
                    # 尝试获取注释的矩形区域
                    if hasattr(annot, 'rect'):
                        print(f"      位置: {annot.rect}")
                    # 尝试获取注释的内容
                    if hasattr(annot, 'info'):
                        print(f"      信息: {annot.info}")
                    
                    # 尝试将注释渲染为图片并保存
                    try:
                        # 直接从原页面渲染注释区域
                        pix = page.get_pixmap(dpi=150, clip=annot.rect)
                        # 保存图片
                        output_path = f"annotation_{page_num}_{annot_idx}.png"
                        pix.save(output_path)
                        print(f"      已保存为图片: {output_path}")
                    except Exception as e:
                        print(f"      渲染注释失败: {str(e)}")
            
            # 4. 检查页面中的矢量图形路径
            paths = page.get_drawings()
            print(f"\n矢量路径数量: {len(paths)}")
            
            # 5. 检查页面中的文本块
            text_blocks = page.get_text("blocks")
            print(f"文本块数量: {len(text_blocks)}")
            
            print("\n" + "="*50 + "\n")
            
        doc.close()
        
    except Exception as e:
        print(f"分析失败: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法: python test_stamp_analysis.py <PDF文件路径>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    if not os.path.exists(pdf_path):
        print(f"错误: 文件 {pdf_path} 不存在")
        sys.exit(1)
    
    analyze_pdf_stamps(pdf_path)