## Context

合并输出由 `PDFHandler._merge_files_into_doc` 生成：每新建一页时先调用 `_draw_dividers` 绘制页内分割线（当 `rows * cols > 1`），再按 `show_crop_marks` 与左右裁切线距离绘制裁切线。预览与最终合并共用该函数，因此只改这一处即可同时影响预览、导出与 MCP 调用（`crop_marks.show` 已映射为 `show_crop_marks`）。

约束：
- 不新增配置字段，`config.json` 的 `layout_config` 结构保持不变
- 裁切线外观与绘制条件（`show_crop_marks` 为真且左右裁切线距离大于 0）保持不变
- 旧配置无需迁移

## Goals / Non-Goals

**Goals:**
- 分割线仅在「裁切线」复选框勾选时绘制，未勾选时完全不出现
- 勾选时分割线的位置、样式（灰虚线、dash=5、gap=3、width=0.5）与现在完全一致
- 预览、合并导出、MCP 调用三种入口行为一致

**Non-Goals:**
- 不为分割线提供独立开关
- 不修改裁切线的绘制逻辑、默认值或配置键名
- 不调整 UI 中「裁切线」复选框的位置与文案

## Decisions

1. **在 `prepare_output_page` 的分割线分支追加 `show_crop_marks` 判断**
   - 方案：`if layout_config['rows'] * layout_config['cols'] > 1 and layout_config.get('show_crop_marks', False):`
   - 理由：改动最小，单一判定点覆盖所有页面创建路径；不需要给 `_draw_dividers` 增加参数或改动其内部逻辑。
   - 备选：把开关判断下沉到 `_draw_dividers` 内部。否决原因：该方法职责是「绘制」，是否绘制的决策应留在调用方，且现有裁切线判断同样在调用方，保持一致性。

2. **复用 `show_crop_marks` 而不新增 `show_dividers`**
   - 理由：需求是「分割线纳入裁切线配置项管理」，新增字段会造成两个开关语义重叠、配置迁移与 UI 冗余。
   - 备选：新增独立字段并在 UI 上把分割线选项并入裁切线卡片。否决原因：超出需求范围（用户明确要求二者同步显隐）。

3. **默认值保持 `False`**
   - 未配置或旧配置缺字段时 `layout_config.get('show_crop_marks', False)` 为 `False`，分割线不绘制，与「复选框默认不勾选」一致。

## Risks / Trade-offs

- [旧用户升级后默认看不到分割线] → 与需求一致（默认不勾选即不显示），UI 上勾选「裁切线」即可恢复；在 `说明文档.md` 中说明。
- [勾选裁切线但左右裁切线距离为 0 时，只见分割线不见裁切线] → 属既有裁切线绘制条件（距离需 > 0），本次不改变；文档中说明该现象。
- [若未来需要「只显示分割线不显示裁切线」] → 可在后续变更中拆分独立开关，本次不预先设计。
