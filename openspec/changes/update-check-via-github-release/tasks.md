# Tasks

> 本清单在「先弹窗后拉取」修订后重新校准：发布链路（1.x）与清单读取（2.x）的成果仍然有效，弹窗与调用点相关的任务改回未完成。

## 1. 发布链路：让 Release 携带自描述版本清单

- [x] 1.1 在 `.github/workflows/build.yml` 的 `release` job 中，把 `actions/checkout@v4` 放在首个步骤（它默认 `git clean -ffdx`，排在 `download-artifact` 之后会清空未跟踪的 `release-artifacts/`），再于下载产物之后、创建 Release 之前增加清单生成步骤：读取 `code/version.json` 的 `version`，写出 `release-artifacts/version.json`，内容含 `version`、`tag`（`${GITHUB_REF_NAME}`）、`release_url`（`${GITHUB_SERVER_URL}/${GITHUB_REPOSITORY}/releases/tag/${GITHUB_REF_NAME}`）；验证：本地用 `GITHUB_REF_NAME=v0.1.17 GITHUB_REPOSITORY=absolutelyZero/piaoyihe GITHUB_SERVER_URL=https://github.com` 跑一遍步骤中的 shell，`cat release-artifacts/version.json` 得到三个字段且 `version` 为 `0.1.17`
- [x] 1.2 在同一 job 中增加一致性校验步骤：`version` 必须等于 `${GITHUB_REF_NAME}` 去掉前缀 `v`，否则 `exit 1` 并打印两者的实际值；验证：构造 `version=0.1.16` 与 `GITHUB_REF_NAME=v0.1.17` 的输入运行该步骤，确认退出码非 0 且输出包含两个版本号；再用一致的输入确认退出码为 0
- [x] 1.3 确认 `softprops/action-gh-release@v2` 的 `files: release-artifacts/*` 能匹配到新生成的清单，且 `fail_on_unmatched_files: true` 保持开启；验证：检查 workflow 该步骤参数未变，并在 `release-artifacts/` 中同时存在安装包与 `version.json` 时确认 glob 匹配数为 4
- [x] 1.4 在 `.github/workflows/build.yml` 顶部注释或 README 的发布说明中补一句「打 tag 前先改 `code/version.json`，CI 会校验二者一致」；验证：文档中可检索到该说明，且与 1.2 的校验行为一致

## 2. 清单读取与版本判定

- [x] 2.1 在 `code/core/update_checker.py` 定义模块常量 `VERSION_MANIFEST_URL = "https://github.com/absolutelyZero/piaoyihe/releases/latest/download/version.json"`，并新增 `@dataclass(frozen=True) class UpdateInfo`（字段 `version`、`release_url`、`tag`）；验证：`python3 -c "from code.core.update_checker import UpdateInfo, VERSION_MANIFEST_URL; print(VERSION_MANIFEST_URL)"` 能正常导入并输出地址
- [x] 2.2 改造 `UpdateChecker.__init__`：`remote_version_url` 默认取 `VERSION_MANIFEST_URL`，删除 `qrcode_url` 相关形参与属性；验证：`grep -rn "qrcode_url" code/` 在 `code/core/update_checker.py` 中无命中，且 `UpdateChecker(local_version_file=..., config_file=...)` 不传 URL 也能构造
- [x] 2.3 改造 `check_for_updates()`：返回 `UpdateInfo | None`，解析前校验响应为 JSON 且 `version` 形如 `x.y.z`，读取 `release_url` / `tag`（缺失时为空串）；无更新与异常统一返回 `None`，异常仅记录不抛；验证：单测覆盖「远程更高」「版本相等」「字段缺失」「返回非 JSON」「网络异常」五种输入，断言返回值分别为 `UpdateInfo` / `None`（不崩溃）等预期，`python3 -m unittest tests.test_update_checker` 通过
- [x] 2.4 把 `_is_version_greater_than` 提升为可复用的静态方法（保留现有逐段比较实现），并为其补充「段数不同」「非数字段」用例；验证：新增用例覆盖 `0.1.9 < 0.1.10`、`0.2 < 0.2.0`、`0.1.16 vs 0.1.16`，`python3 -m unittest tests.test_update_checker` 通过
- [x] 2.5 保留 `_get_ignored_version` / `_set_ignored_version` 对 `config.json` 中 `ignored_version` 字段的读写语义不变，并补一条「写入后重新构造 checker 能读到」的用例；验证：该用例通过，且 `code/config.json` 的键名与格式未被改动

## 3. 更新弹窗：先固定弹窗，再异步填充结果

- [x] 3.1 改造 `UpdateDialog.__init__` 签名为 `(parent, current_version, config_file)`，构造时即可渲染：第一行「当前版本 v{current_version}」，第二行初始文案「正在检查最新版本中…」，内容区预留固定高度使状态切换不改变窗口尺寸；验证：离屏构造 `UpdateDialog(window, "0.1.16", config)` 不传任何网络结果即可显示，且第二行初始文案为「正在检查最新版本中…」
- [x] 3.2 新增 `UpdateCheckWorker(QThread)`（与 `code/ui/file_load_worker.py` 写法一致）：信号用自有名 `checked = Signal(object)` 与 `failed = Signal(str)`（不重声明 `finished`，避免遮蔽 `QThread.finished`），`run()` 内调用 `UpdateChecker.check_for_updates(ignore_ignored_version=True)`，成功发 `UpdateInfo`（无更新发 `None`）、失败发 `failed(原因)`；验证：单测中 patch `check_for_updates` 后启动 worker，确认 `checked` 以 `UpdateInfo` 与 `None` 各发出一次、`failed` 在异常时发出，且主线程不被阻塞
- [x] 3.3 弹窗增加两个回填方法 `set_update_info(info)`（显示最新版本号 + Release 超链接；远程不高于本地时说明当前已是最新版本）与 `set_check_failed()`（显示「检查最新版本失败」）；验证：三种状态各调用一次，第二行文案与链接状态符合预期，窗口尺寸不变
- [x] 3.4 手动检查改为「先弹窗、后拉取」：`MainFrame._check_update_status(force_check=True)` 用 `dialog.open()` 显示弹窗，再启动 `UpdateCheckWorker`，`checked` / `failed` 连到 `set_update_info` / `set_no_update` / `set_check_failed`；弹窗在结果返回前被关闭时丢弃结果、不二次弹窗；验证：断网点击状态栏版本号，弹窗立即出现，随后第二行变为「检查最新版本失败」，全程无额外消息框
- [x] 3.5 删除页脚「立即更新」按钮，只保留「稍后」与「忽略此版本」；打开更新页面统一由内容区 Release 地址承担；验证：`grep -n "立即更新\|view_button" code/core/update_checker.py` 无命中，页脚按钮依次为「稍后」「忽略此版本」
- [x] 3.6 二维码改为读取本地打包资源（项目固定的公众号二维码，不按版本区分、不引入任何热更换逻辑）：通过 `_res_dir()` 拼出 `res/qrcode.jpg`，`QPixmap` 加载并等比缩放到固定尺寸，`isNull()` 时降级为文字提示；验证：断网启动并触发弹窗，二维码仍正常显示；临时改名该资源文件后确认出现降级文案而非报错框
- [x] 3.7 删除 `QRCodeDialog` 类及其远程下载逻辑（`QNetworkAccessManager` 相关代码一并移除）；验证：`grep -n "QRCodeDialog\|QNetworkAccessManager" code/core/update_checker.py` 无命中
- [x] 3.8 更新 `tests/test_ui_shell.py`：`UpdateDialog` 构造改为 `(window, "0.1.16", config)`，断言第一行含当前版本、第二行初始为「正在检查最新版本中…」、`set_update_info` 后出现版本号与地址、`set_check_failed` 后出现失败文案，页脚只有两个按钮且不含「立即更新」；验证：`python3 -m unittest tests.test_ui_shell` 中相关用例通过
- [x] 3.9 同步更新 `tests/test_font_alignment.py` 中涉及弹窗的字体/对齐断言（若因结构变化失效）；验证：`python3 -m unittest tests.test_font_alignment` 通过

## 4. 调用点收敛与 OSS 清理

- [x] 4.1 改造 `code/main.py` 的 `delayed_check_update()`：删除 OSS 的 `remote_version_url` 与 `qrcode_url` 两行硬编码，改为不传 URL 调用 `check_updates_on_start`；验证：`grep -rn "piaoyihe.oss-cn-hangzhou" code/` 无命中
- [x] 4.2 改造 `code/ui/main_frame.py` 的 `_check_update_status()`：手动检查按 3.4 改为先弹窗后拉取，删除 `QMessageBox.warning` 失败框与「当前已是最新版本」信息框（结论改由弹窗第二行呈现）；自动检查分支保持「先取后弹、失败静默」；验证：断网 / 有更新 / 已是最新三种情况下点击版本号，界面反馈均来自弹窗本身，无任何额外消息框
- [x] 4.3 删除 `code/ui/main_frame.py` 中重复的 `_is_version_newer`，改调 `UpdateChecker` 的版本比较；验证：`grep -n "_is_version_newer" code/ui/main_frame.py` 无命中，且版本比较行为与改造前一致（用 2.4 的用例覆盖）
- [x] 4.4 更新 `tests/test_ui_shell.py` 的方法清单断言（:319-322）与 `test_15_dialogs_use_unified_structure`；验证：`python3 -m unittest tests.test_ui_shell` 中相关用例通过
- [x] 4.5 在 README.md / README_EN.md 的发布说明处注明版本清单随 Release 发布、检查地址为 `releases/latest/download/version.json`；验证：两份文档中均可检索到该地址

## 5. 集成验证

- [x] 5.1 全量测试：验证 `python3 -m unittest discover -s tests -p 'test_*.py'` 的失败集合不超出改动前的基线，无因弹窗签名变化导致的失败
- [ ] 5.2 端到端发布演练：在测试 tag 上跑一次完整 workflow，验证 Release 资产含 `version.json`，且 `https://github.com/absolutelyZero/piaoyihe/releases/latest/download/version.json` 返回内容与 tag 一致；注：客户端侧已用 v0.1.16 的现有 Release 实测通过（资产 `version.json` 存在、稳定地址返回 `version: 0.1.16` 与 tag 一致、离屏弹窗显示「当前版本 v0.1.15 → 最新版本 v0.1.16」并可打开链接），但该资产是手工上传的，workflow 自动产出仍待首次打 tag 验证
- [x] 5.3 离线与异步降级验证：断网启动应用无任何弹窗与错误框；断网点击状态栏版本号时弹窗**立即**出现，第二行随后变为「检查最新版本失败」，无额外消息框；离屏渲染确认二维码与地址在三态下均正常
- [x] 5.4 一致性核对：确认 `code/` 下无 OSS 地址残留、无 `QRCodeDialog` 残留、`config.json` 键名未变，并与 `openspec/specs/feature-preservation/spec.md` 的基线逐条对照

## Workflow follow-up

- 实施完成并通过评审后，按项目流程归档本变更（`openspec archive update-check-via-github-release`）。
- 归档前确认迁移计划第 1 步（OSS 跳板）已在发布 `v0.1.17` 时执行，否则老客户端收不到新机制。
