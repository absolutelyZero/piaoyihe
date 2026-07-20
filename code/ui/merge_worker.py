#!/usr/bin/env python3
"""
PDF 合并后台工作线程

该模块提供在后台线程中执行 PDF 合并任务的功能，
避免合并大量文件时阻塞主界面，并通过信号报告进度和结果。
"""

from PySide6.QtCore import QThread, Signal


class MergeWorker(QThread):
    """
    PDF 合并后台工作线程

    在独立的后台线程中调用 PDFHandler.merge_pdfs，将合并操作从 UI 主线程剥离，
    合并过程中通过 progress 信号实时反馈进度，完成后通过 finished 或 error 信号通知界面。

    属性:
        progress: 进度信号，参数为 (current, total)
        finished: 完成信号，参数为 (success, message)
        error: 错误信号，参数为 error_message
    """

    progress = Signal(int, int)
    finished = Signal(bool, str)
    error = Signal(str)

    def __init__(self, pdf_handler, pdf_paths, output_path, layout, mode,
                 batch_size=50, parent=None):
        """
        初始化合并工作线程

        参数:
            pdf_handler: PDFHandler 实例，用于执行实际的合并操作
            pdf_paths: 待合并的 PDF 文件路径列表
            output_path: 合并后的输出文件路径
            layout: 布局配置，字符串或字典
            mode: 合并模式，'普通' 或 '图像'
            batch_size: 每批处理的文件数量，默认 50
            parent: 父对象，用于 Qt 对象生命周期管理
        """
        super().__init__(parent)
        self.pdf_handler = pdf_handler
        self.pdf_paths = pdf_paths
        self.output_path = output_path
        self.layout = layout
        self.mode = mode
        self.batch_size = batch_size

    def run(self):
        """
        执行合并任务

        在线程中调用 pdf_handler.merge_pdfs，并通过回调函数转发进度。
        合并成功或失败时分别发射 finished 信号，发生异常时发射 error 信号。
        """
        try:
            def on_progress(current, total):
                """将合并进度转发为 Qt 信号"""
                self.progress.emit(current, total)

            result = self.pdf_handler.merge_pdfs(
                self.pdf_paths,
                self.output_path,
                self.layout,
                mode=self.mode,
                batch_size=self.batch_size,
                progress_callback=on_progress
            )

            if result:
                self.finished.emit(True, f"PDF 合并完成！\n保存至: {self.output_path}")
            else:
                self.finished.emit(False, "合并失败，请检查文件或日志")

        except Exception as e:
            self.error.emit(str(e))
