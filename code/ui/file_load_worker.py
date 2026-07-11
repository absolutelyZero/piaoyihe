#!/usr/bin/env python3
"""
PDF 文件加载后台工作线程

该模块提供在后台线程中批量加载 PDF 文件信息的功能，
避免一次性拖入大量文件时阻塞主界面，并通过信号报告进度和结果。
"""

from PySide6.QtCore import QThread, Signal


class FileLoadWorker(QThread):
    """
    PDF 文件加载后台工作线程

    在独立的后台线程中逐个打开 PDF 并提取发票字段，
    每处理完一个文件即将结果发回主线程插入到文件列表。

    属性:
        progress: 进度信号，参数为 (current, total)
        file_loaded: 单个文件加载完成信号，参数为 file_info 字典
        finished: 全部加载完成信号，参数为 (success, message)
        error: 错误信号，参数为 error_message
    """

    progress = Signal(int, int)
    file_loaded = Signal(dict)
    finished = Signal(bool, str)
    error = Signal(str)

    def __init__(self, pdf_handler, file_paths, file_list_panel, parent=None):
        """
        初始化文件加载工作线程

        参数:
            pdf_handler: PDFHandler 实例，用于提取发票字段
            file_paths: 待加载的 PDF 文件路径列表
            file_list_panel: FileListPanel 实例，用于调用 build_file_info
            parent: 父对象，用于 Qt 对象生命周期管理
        """
        super().__init__(parent)
        self.pdf_handler = pdf_handler
        self.file_paths = file_paths
        self.file_list_panel = file_list_panel

    def run(self):
        """
        执行文件加载任务

        在线程中逐个提取文件信息并通过 file_loaded 信号发回主线程，
        全部完成后发射 finished 信号，发生异常时发射 error 信号。
        """
        try:
            total = len(self.file_paths)
            for idx, file_path in enumerate(self.file_paths):
                try:
                    file_info = self.file_list_panel.build_file_info(
                        self.pdf_handler, file_path
                    )
                    if file_info:
                        self.file_loaded.emit(file_info)
                except Exception as e:
                    print(f"加载文件失败 [{file_path}]: {str(e)}")

                self.progress.emit(idx + 1, total)

            self.finished.emit(True, f"已加载 {total} 个文件")

        except Exception as e:
            self.error.emit(str(e))
