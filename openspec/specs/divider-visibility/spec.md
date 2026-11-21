# divider-visibility 能力规范

## Purpose

（待补充：该能力用于控制发票之间分割线的显示与隐藏，使分割线随「裁切线」配置项显隐，避免为分割线单独提供开关）

## Requirements

### Requirement: 分割线随裁切线开关显隐

系统 SHALL 将发票之间的分割线与「裁切线」配置项绑定：`layout_config.show_crop_marks` 为 `false` 时不绘制任何分割线，为 `true` 时按现有规则绘制分割线。系统 SHALL NOT 为分割线提供独立于裁切线的开关。

#### Scenario: 裁切线未勾选时不显示分割线
- **WHEN** 用户未勾选「裁切线」并执行合并预览或导出
- **THEN** 输出 PDF 中所有页面均不绘制发票之间的水平或垂直分割线

#### Scenario: 裁切线勾选时显示分割线
- **WHEN** 用户勾选「裁切线」且布局为多发票页面（`rows * cols > 1`）
- **THEN** 输出 PDF 中按现有位置绘制水平与垂直分割线

#### Scenario: 单发票页面不绘制分割线
- **WHEN** 布局为单发票页面（`rows * cols == 1`）且裁切线已勾选
- **THEN** 输出 PDF 中不绘制分割线（无分割线需求）

#### Scenario: MCP 调用同样受开关控制
- **WHEN** MCP 调用 `merge_invoices` 时 `crop_marks.show` 为 `false`
- **THEN** 合并结果不包含分割线；当 `crop_marks.show` 为 `true` 时合并结果包含分割线

### Requirement: 分割线外观保持不变

裁切线勾选时，系统 SHALL 保持分割线的几何位置与样式与变更前完全一致：沿单元格边界绘制，颜色为灰度 0.7、虚线 dash=5、gap=3、线宽 0.5。

#### Scenario: 分割线位置与样式一致
- **WHEN** 裁切线已勾选且布局为 2x2
- **THEN** 水平分割线位于可用区域高度 1/2 处、垂直分割线位于可用区域宽度 1/2 处，样式为灰色虚线（dash=5、gap=3、width=0.5）

#### Scenario: 分割线范围限定在可用区域内
- **WHEN** 裁切线已勾选且设置了非零页边距
- **THEN** 分割线仅绘制在四边页边距围成的可用区域内，不越过页边距

### Requirement: 默认关闭与配置兼容

系统 SHALL 在配置缺失 `show_crop_marks` 时按 `false` 处理，即旧配置或首次启动默认不显示分割线与裁切线；系统 SHALL NOT 为分割线新增任何配置字段。

#### Scenario: 旧配置无该字段
- **WHEN** 加载的 `config.json` 中 `layout_config` 不含 `show_crop_marks`
- **THEN** 「裁切线」复选框为未勾选状态，合并结果不包含分割线

#### Scenario: 勾选状态持久化
- **WHEN** 用户勾选「裁切线」并退出应用后重新启动
- **THEN** 复选框保持勾选，合并结果同时包含分割线与裁切线
