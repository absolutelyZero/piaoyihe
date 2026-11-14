# Spec Delta

## Purpose

把「改造不得遗漏或删减任何功能」固化为可逐项核对的验收契约：以改造前源码盘点出的 51 个功能点为基线，要求新版界面中每一项都能触发、行为一致，并且业务层接口与既有配置完全不受影响。

## ADDED Requirements

### Requirement: 功能基线 51 项逐项保留

系统 SHALL 保留改造前盘点出的全部 51 个功能点，按 A 窗口框架 6 项、B 票据台账 9 项、C 列表操作 6 项、D 排版参数 5 项、E 顺序与输出 8 项、F 实时预览 5 项、G 批量重命名 6 项、H 系统能力 6 项分组；任一项 SHALL NOT 因改版被删除、隐藏到不可达位置或改为需额外步骤才能触发。

#### Scenario: 逐项核对台账与操作
- **WHEN** 验收人员按 `req/ui/00-设计说明与设计系统.png` 中的功能保留矩阵逐项操作新版界面
- **THEN** A–H 八组共 51 项均能在界面中找到入口并成功触发，无缺项

#### Scenario: 右键菜单四项无删减
- **WHEN** 验收人员在台账任一行打开右键菜单
- **THEN** 打开文件、在文件夹中显示、删除、导出列表四项全部存在且可执行

#### Scenario: 七类票种规则无删减
- **WHEN** 验收人员打开批量重命名对话框
- **THEN** 7 类票种导航、字段芯片、保存/清空/执行与结果统计全部存在且行为与改造前一致

### Requirement: 业务层接口与配置零改动

系统 SHALL NOT 改变 `code/core/`、`code/core/invoice_extractors/`、`code/mcp_server/` 的公开行为；MCP 的 9 个 Tools、CLI 参数（`--mcp-server`、`--transport`、`--host`、`--port`、`--cors-origins`）、`config.json` 键名与旧规则迁移逻辑 SHALL 与改造前完全一致。

#### Scenario: MCP Tools 回归
- **WHEN** 通过 MCP 客户端调用 `merge_invoices`、`extract_invoice_info`、`batch_extract_invoice_info`、`batch_rename_invoices`、`export_invoice_list`、`export_invoice_list_from_paths`、`get_supported_layouts`、`get_supported_fields`、`get_server_info`
- **THEN** 9 个 Tool 的返回结构与改造前一致，不因 UI 改造出现字段缺失或调用失败

#### Scenario: 命令行参数回归
- **WHEN** 以 `python code/main.py --mcp-server --transport sse --port 8766` 启动
- **THEN** GUI 与 SSE 服务同时可用，参数解析行为不变

### Requirement: 主题与打包兼容性不回退

系统 SHALL 保持 Windows 11 深浅色自动检测、Win7 + VxKex 兼容、macOS 运行与 PyInstaller 打包可用；新增样式资源 SHALL 被打包配置覆盖，且 SHALL NOT 引入需要联网加载的字体或图标。

#### Scenario: 深色模式启动
- **WHEN** 在 Windows 深色主题下启动应用
- **THEN** 主窗口、台账、弹窗全部按深色令牌渲染，无白底黑字残留块

#### Scenario: 打包后资源完整
- **WHEN** 使用 `package_win.bat` 打包并运行生成的可执行文件
- **THEN** 图标、字体与样式正常显示，合并、预览、重命名与导出功能均可用

### Requirement: 改造后功能回归验收

系统 SHALL 在交付前提供一份逐项验收记录，覆盖 51 项功能点在浅色与深色主题下的触发结果，并记录合并输出 PDF、导出 Excel、批量重命名结果与改造前一致。

#### Scenario: 输出物比对
- **WHEN** 用同一组发票分别执行改造前与改造后的合并、导出与重命名
- **THEN** 生成的 PDF 页数与排版、Excel 字段与重复高亮、重命名后的文件名集合完全一致

#### Scenario: 验收记录归档
- **WHEN** 全部功能点验证完成
- **THEN** 验收记录写入变更目录或项目文档，逐项标注通过，未通过项须在归档前修复
