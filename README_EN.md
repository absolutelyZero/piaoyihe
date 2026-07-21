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
- **Batch Rename**: Support custom rules for batch renaming based on invoice fields (invoice type, invoice number, product type, invoice date, buyer name, seller name, amount)
- Support direct printing after merging
- **Auto Update Check**: Automatically check for new versions on startup, supports version update notifications
- **MCP Server**: Built-in Model Context Protocol server, allowing AI clients (Claude Desktop, Cursor, etc.) to invoke core capabilities through standard MCP protocol

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

#### MCP Server Usage

PiaoYiHe includes a built-in MCP Server, enabling AI clients such as Claude Desktop and Cursor to invoke core capabilities through the standard MCP protocol.

##### Start Methods

```bash
# stdio standalone mode (recommended for Claude Desktop)
python -m code.mcp_server

# SSE standalone mode
python -m code.mcp_server --transport sse --host 127.0.0.1 --port 8766

# GUI coexistence mode
python code/main.py --mcp-server --transport sse --host 127.0.0.1 --port 8766
```

##### Command Line Arguments

| Argument | Description | Default |
|---|---|---|
| `--transport` | Transport type, `stdio` or `sse` | `stdio` |
| `--host` | SSE listen address | `127.0.0.1` |
| `--port` | SSE listen port | `8765` |
| `--cors-origins` | Allowed CORS origins for SSE | `*` |

##### Environment Variables

| Variable | Description | Default |
|---|---|---|
| `PYYH_LOG_LEVEL` | MCP Server log level (DEBUG/INFO/WARNING/ERROR) | `INFO` |

##### Claude Desktop Configuration Example (stdio)

```json
{
  "mcpServers": {
    "piaoyihe": {
      "command": "python",
      "args": ["-m", "code.mcp_server"],
      "cwd": "D:\\minipro\\piaoyihe\\piaoyihe"
    }
  }
}
```

##### Available Tools

| Tool Name | Description |
|-----------|-------------|
| `merge_invoices` | Merge multiple PDF invoices into a specified layout |
| `extract_invoice_info` | Extract all fields from a single invoice |
| `batch_extract_invoice_info` | Extract fields from multiple invoices |
| `batch_rename_invoices` | Batch rename files by rule (supports `dry_run` preview) |
| `export_invoice_list` | Export a constructed invoice list to Excel |
| `export_invoice_list_from_paths` | Export Excel directly from a list of PDF paths |
| `get_supported_layouts` | Get supported layout configurations |
| `get_supported_fields` | Get available fields for renaming rules |
| `get_server_info` | Get server name, version, and tool list |

##### Response Format

All tools return a JSON object containing at least `success` and `message`:

```json
{
  "success": true,
  "message": "Operation completed successfully"
}
```

Additional fields vary by tool, such as `output_path`, `info`, `results`, `renamed_map`, `layouts`, `fields`, etc.

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
