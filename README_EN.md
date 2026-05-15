# PiaoYiHe - Invoice PDF Merge & Layout Tool

#### Introduction
PiaoYiHe (票易合) is a cross-platform desktop application built with Python + PySide6 (supporting Windows and macOS), specifically designed for merging and arranging multiple invoice PDF files into specified formats. The software supports various layout modes to meet different invoice merging requirements.

![Interface Preview](req/界面.png)

#### Software Architecture
- **Frontend Framework**: PySide6 (Qt cross-platform GUI framework)
- **PDF Processing**: PyMuPDF (fitz)
- **Programming Language**: Python 3
- **Packaging Tool**: PyInstaller

#### Features
- Drag and drop PDF file import, or click "Add" button to select files
- Multiple layout modes: Vertical 1x2, Vertical 1x3, Vertical 2x4, Horizontal 2x2
- **Dual Processing Modes**: Normal mode (preserves PDF vector information and invoice stamps), Image mode (high-precision image conversion)
- **Print Order**: Support sorting by list order, invoice date, or invoice amount
- **Real-time Preview**: Automatically generates merged preview after adding files, supports mouse wheel zoom
- File list display: File name, amount, invoice date, path, modification date, size
- **File Management**: Support move up/down to adjust order, context menu (open file, show in folder)
- Support delete selected and delete all operations
- **Batch Rename**: Support custom rules for batch renaming based on invoice fields (invoice type, product type, invoice date, buyer name, seller name, amount)
- Support direct printing after merging
- **Auto Update Check**: Automatically check for new versions on startup, supports version update notifications

#### Installation Guide

1. Install Python 3 environment
2. Install dependencies:
   ```bash
   pip install PySide6 PyMuPDF pyinstaller
   ```
3. Clone the project and run:
   ```bash
   python code/main.py
   ```

#### Usage Instructions

1. **Add Files**: Drag PDF invoice files into the window, or click the "Add" button
2. **Select Layout**: Choose the appropriate layout according to your needs
3. **Batch Rename**: Click the "Rename" button, configure rules, and batch rename files
   - Supported fields: Invoice type, Product type, Invoice date, Buyer name, Seller name, Amount
   - Example rule: `{BuyerName}-{InvoiceDate}-{ProductType}`
4. **View Statistics**: The right panel displays file count and amount statistics
5. **Merge Files**: Click the "Merge PDF" button to generate the merged PDF
6. **Print Output**: Check the "Print after merge" checkbox to print directly

#### Packaging and Distribution

- Windows packaging: `package_win.bat`
- macOS packaging: `package_macos.sh`

#### Contact Us

If you have any questions, please follow our WeChat official account and send us a message.

![WeChat QR Code](code/res/qrcode.jpg)

#### Contributing

1. Fork this repository
2. Create a new Feat_xxx branch
3. Submit your code
4. Create a new Pull Request
