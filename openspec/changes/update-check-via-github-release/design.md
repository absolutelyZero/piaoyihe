# Design

## Context

现状与约束（动机见 `proposal.md`）：

- 客户端版本检查集中在 `code/core/update_checker.py`：`UpdateChecker.check_for_updates()`（:157）用 `urllib.request.urlopen` 拉取 JSON 并只读 `version` 字段；`UpdateDialog`（:200）展示版本号 + 一个「查看更新」按钮，按钮打开二级 `QRCodeDialog`（:299），后者用 `QNetworkAccessManager` 远程下载更新日志图片。
- 两处调用点各自硬编码 OSS 地址：`code/main.py:195-200`（启动自动检查）与 `code/ui/main_frame.py:1844-1856`（点击状态栏版本号手动检查）。`main_frame.py:1866` 还有一份与 `UpdateChecker` 重复的 `_is_version_newer`。
- 手动检查当前是**同步阻塞**的：`_check_update_status` 内直接调用 `check_for_updates()`（超时 10 秒），期间界面没有任何反馈，用户只能重复点击版本号。
- 打包已内置资源：`invoice_tool.spec` / `invoice_tool_win.spec` 的 datas 已包含 `code/res/qrcode.jpg`、`code/version.json`、`code/config.json`，无需新增条目。
- 发布链路：`.github/workflows/build.yml` 的 `release` job（:199-249）在 `refs/tags/v*` 时用 `softprops/action-gh-release@v2` 上传 `release-artifacts/*`，当前资产只有安装包；两个 build job 已分别用 Python / PowerShell 从 `code/version.json` 读取版本号并写入产物名。
- 现有 Release 实测：`releases/latest` 的 `tag_name` 为 `v0.1.16`，资产为三个安装包，尚无 `version.json`；`releases/latest/download/version.json` 当前返回 404，这正是本次要补的发布动作。
- 兼容性约束（`openspec/specs/feature-preservation/spec.md`）：`config.json` 键名不变、业务层接口零改动、主题与打包兼容。

## Goals / Non-Goals

**Goals:**

- 让「打一个 tag」同时产出安装包与版本清单，消除两条手工链路。
- 客户端只依赖一个稳定 HTTPS 地址，不消耗 GitHub API 配额、不需要 token。
- 更新提示对两类用户都可用：能上 GitHub 的点地址直达 Release，不能上的扫本地二维码。
- 手动检查**先给出确定的界面**，再异步填充结果，用户不再面对「点了没反应」的空窗期。
- 删除 OSS 相关的全部网络依赖与重复的版本比较实现。

**Non-Goals:**

- 不做应用内自动下载 / 静默安装 / 差分升级，仍然引导用户到 Release 页手动下载。
- 不做多通道（beta / stable）版本分发，`prerelease` 保持 `false`。
- 不改造「使用帮助」「变量说明」「赞赏作者」等其他弹窗的内容。
- 不改变启动时自动检查的行为（仍为先取后弹、无更新不打扰）。
- 不迁移或删除 OSS 上已有的历史文件（只保证客户端代码不再引用）。

## Decisions

### 1. 用 `releases/latest/download/version.json` 作为检查地址，而非 GitHub API

选择稳定下载地址：它是 Release 资产的固定软链，不随版本变化，客户端无需拼接 tag，也不会受 API 速率限制（未认证 60 次/小时/IP）与 403 影响。

否决的方案：`GET /repos/absolutelyZero/piaoyihe/releases/latest` 能直接拿到 `html_url` 与 `assets`，信息更全，但引入速率限制、需要 `User-Agent`、失败形态更复杂（限流返回 403 而非 404），对一个每天只检查一次的桌面应用不值得。

代价是清单里拿不到 Release 页面地址，因此**由发布侧把地址写进清单**（见决策 2），客户端一次请求即拿全所需信息。

### 2. 发布侧在 Release 前生成「自描述清单」，而不是直接上传仓库里的原文件

`release` job 在上传资产前，用一个脚本步骤读取 `code/version.json` 的 `version`，输出一份新文件到 `release-artifacts/version.json`：

```json
{
  "version": "0.1.17",
  "tag": "v0.1.17",
  "release_url": "https://github.com/absolutelyZero/piaoyihe/releases/tag/v0.1.17"
}
```

`release_url` 由 `${GITHUB_SERVER_URL}/${GITHUB_REPOSITORY}/releases/tag/${GITHUB_REF_NAME}` 拼出，不写死域名，fork 后仍然正确。

否决的方案：直接把仓库里的 `code/version.json` 作为资产上传。这样清单无法携带 `release_url`，客户端要么硬编码地址模板（仓库改名即失效），要么再发一次 API 请求（回到决策 1 的问题）。

### 3. 发布侧校验清单版本与 tag 一致，不一致则让 job 失败

新增校验步骤：`version.json` 的 `version` 必须等于 `${GITHUB_REF_NAME}` 去掉前缀 `v`。不一致时 `exit 1`，job 在创建 Release 之前终止。

理由：历史 tag 存在无 `v` 前缀与带后缀（`v0.1.12-mcpserver`）的情况，人工发版很容易忘记改版本号；一旦清单与 tag 不符，客户端会长期提示一个永远下载不到的版本。让 CI 失败比让用户困惑便宜。

否决的方案：只在文档里要求「记得同步改版本号」。这条规则过去就存在，实际仍出现过偏差。

### 4. 二维码改为读取本地打包资源，直接内嵌在更新弹窗里

二维码统一取 `code/res/qrcode.jpg`（258×258，公众号二维码，README 已引用），通过既有 `_res_dir()`（`code/ui/tokens.py`）解析路径，`QPixmap` 加载后等比缩放到固定尺寸。

该二维码是**项目固定资源**，不随应用版本变化，也不区分版本：任何版本的更新弹窗展示的都是同一张码。换码的唯一途径是替换 `code/res/qrcode.jpg` 并随下次发版生效，因此不需要为它设计远程加载、缓存或热更换机制。

原来的 `QRCodeDialog` 不再需要：它的唯一职责是展示二维码，而现在二维码就内嵌在 `UpdateDialog` 内容区，二级弹窗只会让用户多点一次。因此删除该类及其 `QNetworkAccessManager` 远程下载逻辑，只保留「读本地文件 → `QPixmap` → 缩放」这一小段，作为 `UpdateDialog._load_qrcode()`。

理由：兜底方案的前提是「GitHub 不可达」，此时任何远程资源都可能不可达；把二维码放进二级弹窗则要求用户多点一次，而这一步在离线场景下最容易失败（旧实现的失败文案「加载二维码失败」正是这种设计的产物）。

否决的方案：继续用 OSS 的 `updatelog.png`。它把兜底能力绑定在另一条同样可能不可达的链路上，逻辑上自相矛盾。

### 5. 弹窗以「当前版本」构造，检查结果通过回填注入

`UpdateDialog(parent, current_version, config_file)` 只依赖本地版本号即可构造并立即显示；检查结果后到，通过两个显式方法注入：

```python
def set_update_info(self, info: UpdateInfo) -> None: ...   # 成功：显示最新版本号 + Release 地址
def set_check_failed(self) -> None: ...                    # 失败：显示「检查最新版本失败」
```

`UpdateInfo` 仍是检查结果的载体（`version` / `release_url` / `tag`），只是不再作为弹窗的构造前提。

理由：用户的要求是「点击后先固定弹窗，再填充结果」。若沿用「先 `check_for_updates()` 再构造弹窗」的顺序，弹窗出现的时刻仍然取决于网络，无法满足要求。回填方式还让「拉取中 / 失败 / 成功 / 已是最新」四种状态成为显式分支，比在构造时用一堆条件判断更清晰。

否决的方案：在构造参数里传 `update_info=None` 并在内部启动请求。把网络副作用塞进 `__init__` 会让弹窗难以测试（构造即发请求），也让「关闭弹窗后结果如何处理」无处安放。

### 6. 检查请求放到 `QThread` 后台执行，弹窗用 `open()` 而非 `exec()`

新增 `UpdateCheckWorker(QThread)`（与 `code/ui/file_load_worker.py`、`code/ui/merge_worker.py` 既有写法一致）：信号用自有名 `checked = Signal(object)` 与 `failed = Signal(str)`，**不重声明 `finished`**——子类重声明会遮蔽 `QThread.finished` 的内建语义；`run()` 内调用 `UpdateChecker.check_for_updates(ignore_ignored_version=True)`，成功发 `UpdateInfo`（无更新发 `None`），失败发 `failed(原因)`。

弹窗以 `open()` 显示（窗口模态但**不阻塞**事件循环），worker 的 `checked` / `failed` 连接到弹窗的回填方法；弹窗 `closeEvent` 置 `_discard_result`，此后到达的结果一律丢弃，绝不在用户已经关掉弹窗后再弹一次。

理由：`exec()` 会开启嵌套事件循环，配合后台线程虽能工作，但「先 open 后 await 结果」的语义在 `exec()` 下要额外维护循环退出条件。`open()` + 信号回填是 Qt 里处理「先出界面、后到数据」的标准形态。

否决的方案：用 `QTimer.singleShot` 或 `QApplication.processEvents()` 假装异步。前者只是延后阻塞点，后者在请求期间重入事件循环，容易引发重入问题。

### 7. 内容区两行结构：第一行当前版本，第二行最新版本与地址

- 第一行：`当前版本 v{local_version}`（本地读取，立即渲染）。
- 第二行按状态切换：拉取中 `正在检查最新版本中…`；失败 `检查最新版本失败`；成功 `最新版本 v{remote} · <a href="{release_url}">{release_url}</a>`（超链接，点击由 `QDesktopServices` 打开浏览器）；无更新时说明当前已是最新版本，不给出指向更高版本的入口。

内容区预留固定高度、第二行允许换行，避免状态切换时窗口尺寸跳动——这是「固定弹窗」的字面要求。

### 8. 页脚删除「立即更新」按钮

打开更新页面统一由内容区的 Release 地址承担，页脚只保留「稍后」与「忽略此版本」。

理由：两个入口做同一件事属于重复；更关键的是「立即更新」在「正在检查」与「检查失败」两种状态下无地址可开，只能禁用或空转，反而是状态机的负担。

否决的方案：保留按钮并在无地址时置灰。置灰按钮仍然占用页脚空间，且在失败态下会让用户误以为可以点。

### 9. 检查地址以模块常量提供默认值，仍保留可注入参数

在 `update_checker.py` 定义 `VERSION_MANIFEST_URL = "https://github.com/absolutelyZero/piaoyihe/releases/latest/download/version.json"`，`UpdateChecker.__init__` 的 `remote_version_url` 参数默认取该常量，调用方不再传 URL；`qrcode_url` 参数删除。

理由：两处调用点重复硬编码同一个地址，正是这次要消除的问题；但保留参数可注入，让测试不必访问网络。

### 10. 失败语义按调用来源分流

- 自动检查（`check_updates_on_start`）：先取后弹，任何异常都只 `print` 到控制台，不弹窗、不阻塞启动；只有确实发现更高版本才弹窗。
- 手动检查（点击状态栏版本号）：先弹窗后取，进行中与失败都在弹窗第二行呈现，**不再使用** `QMessageBox.warning` 失败框，也不再用 `QMessageBox.information` 提示「当前已是最新版本」——该结论同样落在第二行。

否决的方案：手动失败仍弹消息框。弹窗已经在屏幕上，再叠一个消息框是双重反馈，且消息框关闭后用户失去「刚才到底检查没检查」的上下文。

### 11. 删除 `main_frame.py` 中重复的 `_is_version_newer`

版本比较只保留 `UpdateChecker` 一处（`_is_version_greater_than`），对外暴露为静态方法供 UI 复用。两份实现一旦漂移，会出现「弹窗说有新版本、状态栏说没有」的矛盾。

## Risks / Trade-offs

- **国内网络访问 `github.com` 不稳定** → 自动检查失败静默，不影响启动；手动检查在弹窗内明确显示「检查最新版本失败」；弹窗内的二维码是纯本地资源，离线可用。
- **`releases/latest` 只返回最新正式 Release**（跳过 draft 与 prerelease）→ 保持 `prerelease: false`；若将来需要 beta 通道，应新增独立的清单地址，而不是改动这里。
- **发布 job 顺序错乱导致用户拿到不含清单的 Release** → `fail_on_unmatched_files: true` 已保证 `release-artifacts/*` 匹配失败即报错；清单生成步骤放在下载产物之后、创建 Release 之前，任一步失败都不会产生半成品 Release。注意 `actions/checkout@v4` 默认会 `git clean -ffdx`，必须排在三个 `download-artifact` 之前（`release-artifacts/` 是未跟踪目录，放在其后会被清空），因此 release job 的首个步骤是检出仓库。
- **后台 worker 与弹窗生命周期错配**（用户在结果返回前关闭弹窗）→ worker 结果丢弃，不重建弹窗、不弹消息框；worker 以 `parent` 归属主窗口，窗口销毁时随 `QThread` 默认析构安全退出。这一点需要一条测试兜住。
- **`open()` 与 `exec()` 的模态差异** → `open()` 为窗口模态且不阻塞调用方，因此调用点之后不能再假设「弹窗关闭后才继续执行」；现有代码在弹窗后没有任何依赖该假设的逻辑，但改动时需要复核。
- **老客户端仍指向 OSS** → 迁移期需要一次人工跳板（见迁移计划第 1 步），否则老用户永远收不到新机制的版本。
- **清单被篡改或返回 HTML（如企业网络劫持）** → 解析前校验响应为 JSON 且 `version` 为形如 `x.y.z` 的字符串，否则按失败处理，避免把错误内容当版本号弹给用户。
- **本地二维码资源缺失（打包漏打）** → `QPixmap.isNull()` 时降级为文字提示「请访问公众号获取更新」，不弹错误框；spec 的场景要求正常情况下离线可见，此处只做防御。

## Migration Plan

1. **一次性跳板**：在发布首个包含本变更的版本（记为 `v0.1.17`）时，先在 OSS 上把 `update/version.json` 的 `version` 改为 `0.1.17`，让仍在使用旧客户端的用户能收到这一次更新；此后 OSS 不再维护。客户端代码中不保留任何 OSS 引用，这一步纯粹是运维动作。
2. **发布**：推送 `v0.1.17` 标签，确认 Release 资产中出现 `version.json`，且 `https://github.com/absolutelyZero/piaoyihe/releases/latest/download/version.json` 返回的 `version` 为 `0.1.17`。
3. **验证新机制**：用 `v0.1.17` 客户端点击状态栏版本号，确认弹窗**先于**网络请求出现、第二行依次经历「正在检查最新版本中…」→ 结果；再在断网环境确认弹窗立即出现并显示「检查最新版本失败」、无额外消息框；启动时的自动检查在断网下不弹任何窗口。
4. **回滚**：若清单发布出错，删除该 Release 的 `version.json` 资产并重发正确清单即可；客户端在 404 时静默降级，不会崩溃。代码回滚只需还原三处调用点与 workflow 的一个步骤。
5. **清理**：确认无老版本客户端在线后（可观察 Release 下载量），删除 OSS 上的 `update/` 目录。

## Open Questions

无。二维码是否随版本变化已在规划阶段确认：使用项目固定的公众号二维码，不随版本更新；手动检查「先弹窗后拉取」的范围已确认仅限手动检查，启动自动检查保持先取后弹。
