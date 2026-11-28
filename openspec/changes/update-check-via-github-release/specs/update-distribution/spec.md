# Spec Delta

## Purpose

定义票易合的版本清单如何随 GitHub Release 一起发布，以及客户端如何从该 Release 发现、比较并提示新版本，让「发布一次」成为版本分发的唯一动作。

## ADDED Requirements

### Requirement: Release 必须携带自描述的版本清单

发布流程 SHALL 在创建 GitHub Release 时，把仓库中的 `code/version.json` 作为该 Release 的资产一并上传，且上传的清单 SHALL 在原有 `version` 字段之外附带 `tag` 与 `release_url` 两个字段；`version` 的值 SHALL 与 Release 标签去掉 `v` 前缀后的版本号完全一致。

#### Scenario: 打标签后清单随包发布
- **WHEN** 维护者推送形如 `v0.1.17` 的标签并触发发布任务
- **THEN** 该 Release 的资产列表中同时包含安装包与 `version.json`，且清单的 `version` 为 `0.1.17`、`tag` 为 `v0.1.17`、`release_url` 指向该 Release 页面

#### Scenario: 清单版本与标签不一致
- **WHEN** 仓库中的 `code/version.json` 版本号与推送的标签不一致
- **THEN** 发布任务以失败结束并给出明确原因，不产出内容互相矛盾的 Release

### Requirement: 客户端从 Release 稳定地址读取版本清单

客户端 SHALL 通过 `https://github.com/absolutelyZero/piaoyihe/releases/latest/download/version.json` 这一不随版本变化的稳定地址获取版本清单；该请求 SHALL NOT 依赖 GitHub API 鉴权，也 SHALL NOT 再访问任何阿里云 OSS 上的版本文件或更新日志图片。

#### Scenario: 正常读取清单
- **WHEN** 应用启动并执行自动检查更新
- **THEN** 客户端只向上述稳定地址发起一次 HTTPS 请求，解析返回 JSON 的 `version` 字段作为远程版本

#### Scenario: 不再访问 OSS
- **WHEN** 审查版本检查相关的全部网络请求
- **THEN** 请求目标中不存在 `piaoyihe.oss-cn-hangzhou.aliyuncs.com` 下的任何地址

### Requirement: 新版本判定与忽略规则

客户端 SHALL 以点分数字段逐段比较远程版本与本地版本，仅当远程版本严格大于本地版本时判定为有新版本；用户选择「忽略当前版本」时 SHALL 把该版本写入配置的 `ignored_version` 字段，后续自动检查 SHALL 跳过不高于该版本的提示，用户手动检查时 SHALL 忽略该字段照常提示。

#### Scenario: 远程版本更高
- **WHEN** 本地版本为 `0.1.15`、清单版本为 `0.1.16`
- **THEN** 判定存在新版本，并在满足忽略规则时弹出更新提示

#### Scenario: 已忽略的版本不再自动提示
- **WHEN** 用户对 `0.1.16` 选择「忽略当前版本」后重启应用
- **THEN** 自动检查不再为 `0.1.16` 弹出提示，而手动点击版本号仍会提示

### Requirement: 自动检查的静默降级

应用启动时触发的自动检查在请求超时、网络不可达、响应非 JSON 或字段缺失时 SHALL 静默结束，不弹出任何窗口、不阻塞主窗口启动；只有确实发现更高版本时才 SHALL 弹出更新提示。用户点击状态栏版本号触发的手动检查 SHALL 始终先显示更新弹窗，其进行中与失败的呈现由「检查更新弹窗」相关能力规定。

#### Scenario: 无法访问 GitHub 时启动
- **WHEN** 用户所在网络无法访问 `github.com` 并启动应用
- **THEN** 主窗口正常显示且不出现任何更新提示或错误弹窗，用户仍可通过既有入口使用全部功能

#### Scenario: 无更新时不弹窗
- **WHEN** 自动检查完成且远程版本不高于本地版本
- **THEN** 不出现任何窗口，状态栏与主窗口保持原样
