# 票易合 Windows版本编译计划

## 一、项目概述

**项目名称**: 票易合 - 发票PDF合并排版工具  
**项目路径**: `d:\minipro\piaoyihe\piaoyihe`  
**目标平台**: Windows  
**打包工具**: PyInstaller

### 1.1 项目结构
```
piaoyihe/
├── code/
│   ├── main.py              # 程序入口
│   ├── core/
│   │   └── pdf_handler.py   # PDF处理核心
│   ├── ui/
│   │   ├── main_frame.py    # 主窗口
│   │   └── file_list.py     # 文件列表组件
│   └── res/
│       ├── logo3.png        # 应用图标
│       └── qrcode.jpg       # 反馈二维码
├── invoice_tool_win.spec    # Windows打包配置
└── repackage_win.sh         # Windows打包脚本
```

### 1.2 技术栈
- **GUI框架**: wxPython
- **PDF处理**: PyMuPDF (fitz)
- **打包工具**: PyInstaller

### 1.3 依赖项
- wxPython
- PyMuPDF

---

## 二、编译前检查清单

### 2.1 环境检查
- [ ] Python已安装（建议3.8+）
- [ ] pip可用
- [ ] 已安装PyInstaller: `pip install pyinstaller`
- [ ] 已安装wxPython: `pip install wxPython`
- [ ] 已安装PyMuPDF: `pip install PyMuPDF`

### 2.2 配置文件检查
- [ ] `invoice_tool_win.spec` 配置正确
  - [ ] `pathex` 路径已更新为当前项目路径
  - [ ] `datas` 包含所有资源文件
  - [ ] `hiddenimports` 包含wx和fitz

---

## 三、编译步骤

### 步骤1: 清理旧构建文件
```powershell
# 删除之前的打包文件
Remove-Item -Recurse -Force dist, build -ErrorAction SilentlyContinue
```

### 步骤2: 更新spec文件路径
**需要修改**: `invoice_tool_win.spec` 第7行
```python
# 原配置（需要修改）
pathex=['D:\path\to\invoiceTool']

# 修改为实际路径
pathex=['d:\minipro\piaoyihe\piaoyihe']
```

### 步骤3: 执行打包
```powershell
# 在项目根目录执行
pyinstaller invoice_tool_win.spec
```

### 步骤4: 验证输出
打包完成后，检查以下文件：
- [ ] `dist/票易合.exe` 存在
- [ ] 可执行文件能正常启动
- [ ] 界面显示正常
- [ ] 拖放PDF功能正常
- [ ] 合并功能正常

---

## 四、spec文件配置说明

当前配置关键点：

| 配置项 | 当前值 | 说明 |
|--------|--------|------|
| 入口文件 | `code\main.py` | 程序主入口 |
| 资源文件 | `code\res\logo3.png` | 应用图标资源 |
| 隐藏导入 | `wx`, `fitz` | PyInstaller需要显式声明 |
| 输出名称 | `票易合` | 生成的exe文件名 |
| 控制台窗口 | `False` | 隐藏控制台，仅显示GUI |
| UPX压缩 | `True` | 启用UPX压缩减小体积 |

---

## 五、常见问题及解决方案

### 问题1: 路径错误
**现象**: 打包失败，提示找不到模块  
**解决**: 修改spec文件中`pathex`为实际项目路径

### 问题2: 资源文件缺失
**现象**: 运行后图标不显示  
**解决**: 确保spec中`datas`包含所有资源文件路径

### 问题3: 缺少隐藏导入
**现象**: 运行时提示模块未找到  
**解决**: 在`hiddenimports`中添加缺失模块

### 问题4: 杀毒软件误报
**现象**: 生成的exe被杀毒软件拦截  
**解决**: 
1. 添加信任目录
2. 使用`--onefile`改为单文件模式可能减少误报

---

## 六、编译命令汇总

```powershell
# 1. 进入项目目录
cd d:\minipro\piaoyihe\piaoyihe

# 2. 清理旧文件
Remove-Item -Recurse -Force dist, build -ErrorAction SilentlyContinue

# 3. 执行打包
pyinstaller invoice_tool_win.spec

# 4. 输出位置
dist\票易合.exe
```

---

## 七、后续优化建议

1. **添加版本信息**: 可在spec中添加版本号、版权信息
2. **代码签名**: 企业环境建议对exe进行数字签名
3. **创建安装程序**: 可使用Inno Setup或NSIS创建安装包
4. **自动更新**: 可考虑添加自动更新功能

---

## 八、进度记录

| 时间 | 任务 | 状态 | 备注 |
|------|------|------|------|
| 2026-03-30 | 项目分析与计划制定 | 已完成 | 本文档创建 |
| | 环境检查与依赖安装 | 待执行 | |
| | 修改spec文件路径 | 待执行 | |
| | 执行打包 | 待执行 | |
| | 验证测试 | 待执行 | |

