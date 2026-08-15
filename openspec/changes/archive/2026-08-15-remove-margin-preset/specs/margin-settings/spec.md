## REMOVED Requirements

### Requirement: Margin preset selection
**Reason**: 预设方案选择增加了界面复杂度且引入了循环触发 Bug，用户直接输入数值即可满足需求。
**Migration**: 用户直接在四个输入框中输入数值即可设置页边距，无需通过预设下拉框。

#### Scenario: Preset dropdown no longer exists
- **WHEN** the user opens the margin settings area
- **THEN** there is no preset dropdown or "恢复默认" button visible

### Requirement: Reset to default margins
**Reason**: 移除恢复默认按钮，用户可通过输入框手动调整数值。
**Migration**: 无替代方案，直接输入所需数值即可。