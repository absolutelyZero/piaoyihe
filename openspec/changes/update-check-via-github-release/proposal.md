# Proposal

## Why

当前版本检查依赖阿里云 OSS 上手工上传的 `version.json`，发布流程与版本清单是两条互不相干的手工链路：打 tag 触发的 GitHub Release 只上传安装包，OSS 上的版本文件需要人工另行覆盖，容易出现「包已发布但用户检查不到更新」或「清单版本与安装包不一致」。同时更新弹窗只有一个二维码入口，用户既看不到最新版本号，也拿不到可复制的发布页地址；而二维码图片同样走 OSS 远程加载，OSS 一挂，兜底入口也跟着失效。

把版本清单纳入 Release 产物、让客户端直接从 Release 读取，可以让「发布」成为唯一动作；在弹窗里同时给出最新版本号、可点击的 Release 地址与本地内置的公众号二维码，则让能上 GitHub 和不能上 GitHub 的两类用户都有明确出路。

此外，当前点击状态栏版本号后要等网络请求结束才会出现任何界面反馈（最长 10 秒超时），期间用户只能反复点击。更新提示应当先给出确定的界面，再异步填充检查结果。

## What Changes

- **发布侧**：Release 任务在上传安装包的同时，把 `code/version.json` 同步发布为该 Release 的资产，并注入 Release 自身的 `tag`、`release_url` 字段，形成一份「自描述」的版本清单。
- **检查侧**：客户端改为从 `https://github.com/absolutelyZero/piaoyihe/releases/latest/download/version.json` 读取版本清单（稳定下载地址，不消耗 GitHub API 配额、无需 token），不再访问 OSS。
- **BREAKING（内部）**：彻底移除 OSS 版本检查链路——`code/main.py`、`code/ui/main_frame.py` 中硬编码的 `piaoyihe.oss-cn-hangzhou.aliyuncs.com/update/version.json` 与 `updatelog.png` 全部删除，`UpdateChecker` / `check_updates_on_start` / `show_update_dialog` 不再接受 `qrcode_url` 参数。
- **弹窗侧**：点击状态栏版本号后**立即弹出**检查更新弹窗（先出骨架，再异步填充结果）：第一行展示当前版本，第二行展示最新版本信息——拉取中显示「正在检查最新版本中…」、失败显示「检查最新版本失败」、成功显示最新版本号与可点击的 GitHub Release 超链接；弹窗内同时展示本地内置的公众号二维码作为无法访问 GitHub 时的兜底。页脚删除「立即更新」按钮，只保留「稍后」与「忽略此版本」，打开更新页面统一由内容区超链接承担。
- **失败语义**：启动时的自动检查失败保持静默（且只有确实存在更高版本时才弹窗）；手动检查的失败与进行中状态都在弹窗内呈现，不再使用额外的消息框。
- 消除 `code/ui/main_frame.py` 中重复的 `_is_version_newer` 版本比较实现，统一走 `UpdateChecker` 的版本比较。

## Capabilities

### New Capabilities

- `update-distribution`: 版本清单的发布契约与客户端的更新发现行为——Release 必须携带 `version.json`，客户端从稳定地址读取清单、比较版本、决定是否提示，并在无法访问时静默降级。

### Modified Capabilities

- `ui-feedback-and-dialogs`: 「检查更新」弹窗改为「先固定弹窗、再异步填充结果」的两行结构（当前版本 / 最新版本与地址），操作区由「立即更新 + 忽略此版本 + 稍后」收敛为「忽略此版本 + 稍后」，二维码改为读取本地打包资源并作为离线兜底。

## Impact

- 代码：`code/core/update_checker.py`（清单解析、字段扩展、弹窗结构、异步检查 worker、本地二维码）、`code/main.py`（启动检查调用签名）、`code/ui/main_frame.py`（手动检查调用点、移除重复版本比较与消息框）。
- 构建：`.github/workflows/build.yml` 的 `release` job 需要生成并上传 `version.json`。
- 打包：`invoice_tool.spec` / `invoice_tool_win.spec` 已包含 `code/version.json` 与 `code/res/qrcode.jpg`，无需新增资源条目。
- 配置：继续沿用 `config.json` 的 `ignored_version` 字段，键名与语义不变。
- 外部依赖：不再依赖 OSS 上的 `update/` 目录；新增对 `github.com` 的 HTTPS 访问依赖（失败时静默）。
- 测试：`tests/test_ui_shell.py` 中构造 `UpdateDialog` 的用例需要改为「当前版本入参 + 三态断言」，`QRCodeDialog` 相关断言删除。
