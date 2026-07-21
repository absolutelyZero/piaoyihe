# 票易合 - 发票PDF合并排版工具

#### 介绍
票易合是一款基于 Python + PySide6 开发的跨平台桌面应用程序(支持Windows和MacOS)，专门用于将多张发票 PDF 文件合并排版成指定格式。软件支持多种布局方式，可满足不同场景下的发票合并需求。

![界面预览](req/界面.png)

#### 软件架构
- **前端框架**: PySide6 (Qt 跨平台 GUI 框架)
- **PDF 处理**: PyMuPDF (fitz)
- **编程语言**: Python 3
- **打包工具**: PyInstaller
- **MCP 协议**: 官方 `mcp` Python SDK + FastMCP

#### 功能特性
- 支持拖拽导入 PDF 文件，亦可点击"添加"按钮选择文件
- **布局自定义**：可以从1x1到10x10的范围内自由选择排版布局
- **双模式处理**：普通模式（保留PDF矢量信息和发票监制章）、图像模式（高精度图片转换）
- **打印顺序**：支持按列表顺序、开票日期、开票金额三种方式排序打印
- **实时预览**：添加文件后自动生成合并预览图，支持滚轮缩放查看
- 文件列表显示：文件名、金额、开票日期、路径、修改日期、大小
- **文件管理**：支持上移/下移调整顺序、右键菜单（打开文件、在文件夹中显示）
- 支持删除选中、删除全部操作
- **批量重命名**：支持根据发票字段（发票类型、发票号码、商品类型、开票日期、买方名字、销方名字、金额）自定义规则批量重命名文件
- 支持合并后直接打印
- **重复发票检查** ：合并前检查是否有重复发票，避免重复打印
- **导出列表**：支持导出当前文件列表为Excel文件，方便后续处理
- **一式两份**：支持合并后打印一式两份发票，方便抵扣和存档
- **Win7兼容** ：搭配VxKex Next可在Win7下正常使用


#### 安装教程

1. 安装 Python 3 环境
2. 安装依赖包：
   ```bash
   pip install PySide6 PyMuPDF pyinstaller
   ```
3. 克隆项目后运行：
   ```bash
   python code/main.py
   ```

#### 使用说明

1. **添加文件**：将 PDF 发票文件拖入窗口，或点击"添加"按钮
2. **选择布局**：根据需要选择合适的排版布局
3. **批量重命名**：点击"重命名"按钮，配置规则后批量重命名文件
   - 支持字段：发票类型、商品类型、开票日期、买方名字、销方名字、金额
   - 示例规则：`{买方名字}-{开票日期}-{商品类型}`
4. **查看统计**：右侧面板显示文件数量和金额统计
5. **合并文件**：点击"合并PDF"按钮生成合并后的 PDF
6. **打印输出**：可勾选"合并后打印"复选框直接打印

#### MCP Server 使用

票易合已内置 MCP Server，支持 Claude Desktop、Cursor、Cherry Studio 等 AI 客户端通过标准 MCP 协议调用核心能力。

##### 启动方式

```bash
# stdio 独立模式（推荐用于 Claude Desktop）
python -m code.mcp_server

# SSE 独立模式
python -m code.mcp_server --transport sse --host 127.0.0.1 --port 8766

# GUI 共存模式
python code/main.py --mcp-server --transport sse --host 127.0.0.1 --port 8766
```

##### 命令行参数

| 参数 | 说明 | 默认值 |
|---|---|---|
| `--transport` | 传输方式，`stdio` 或 `sse` | `stdio` |
| `--host` | SSE 模式监听地址 | `127.0.0.1` |
| `--port` | SSE 模式监听端口 | `8765` |
| `--cors-origins` | SSE 模式允许的 CORS 来源列表 | `*` |

##### 环境变量

| 变量名 | 说明 | 默认值 |
|---|---|---|
| `PYYH_LOG_LEVEL` | MCP Server 日志级别（DEBUG/INFO/WARNING/ERROR） | `INFO` |

##### Claude Desktop 配置示例（stdio）

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

##### Cursor / Cherry Studio 配置示例（SSE）

若使用 SSE 模式，在支持 SSE 的客户端中填写：

```
http://127.0.0.1:8766/sse
```

启动命令：

```bash
python -m code.mcp_server --transport sse --host 127.0.0.1 --port 8766
```

##### 可用 Tools

| Tool 名称 | 功能 |
|-----------|------|
| `merge_invoices` | 合并多个 PDF 发票为指定布局 |
| `extract_invoice_info` | 提取单张发票全部字段 |
| `batch_extract_invoice_info` | 批量提取多张发票字段 |
| `batch_rename_invoices` | 按规则批量重命名文件（支持 `dry_run` 预览） |
| `export_invoice_list` | 将构造好的发票信息列表导出为 Excel |
| `export_invoice_list_from_paths` | 按 PDF 路径列表直接导出 Excel |
| `get_supported_layouts` | 获取支持的布局配置 |
| `get_supported_fields` | 获取重命名可用字段 |
| `get_server_info` | 获取服务名称、版本和 Tools 列表 |

##### 返回结构说明

所有 Tool 统一返回 JSON 对象，至少包含 `success` 和 `message` 字段：

```json
{
  "success": true,
  "message": "操作成功提示"
}
```

常见附加字段：

- `merge_invoices`：`output_path`（合并后的文件路径）
- `extract_invoice_info`：`info`（发票字段字典）
- `batch_extract_invoice_info`：`results`（结果列表）
- `batch_rename_invoices`：`renamed_count`、`failed_count`、`unrecognized_files`、`renamed_map`、`dry_run`
- `export_invoice_list` / `export_invoice_list_from_paths`：`output_path`
- `get_supported_layouts`：`layouts`
- `get_supported_fields`：`fields`
- `get_server_info`：`name`、`version`、`tools`

##### 常见错误与排查

| 现象 | 原因 | 解决 |
|---|---|---|
| `文件不存在: xxx` | 传入的 PDF 路径错误或文件已被移动 | 检查路径是否为绝对路径或相对当前工作目录的正确路径 |
| `仅支持 PDF 文件: xxx` | 文件后缀不是 `.pdf` | 确认传入文件为 PDF 格式 |
| `无法创建输出目录: xxx` | 输出目录父目录不存在或无写入权限 | 选择可写目录，或先手动创建父目录 |
| `无法识别该发票类型` | PDF 为图片格式或暂不支持的发票版式 | 尝试使用图像模式合并，或检查 PDF 是否可正常打开 |
| SSE 端口被占用 | 上次服务未完全退出 | 更换 `--port` 或结束占用该端口的进程 |

#### 打包发布

- Windows 打包：`package_win.bat`
- macOS 打包：`package_macos.sh`

#### 联系我们

如果有问题，欢迎关注公众号并私信

![公众号二维码](code/res/qrcode.jpg)


#### 参与贡献

1. Fork 本仓库
2. 新建 Feat_xxx 分支
3. 提交代码
4. 新建 Pull Request
