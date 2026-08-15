## ADDED Requirements

### Requirement: Margin adjustment triggers preview update
When the user modifies any of the four margin values (top/bottom/left/right), the system SHALL automatically update the merge preview on the right side within 500ms to reflect the new margin configuration.

#### Scenario: Adjust top margin via spinbox
- **WHEN** the user changes the value of the "上" (top) margin spinbox
- **THEN** the right-side merge preview updates within 500ms to show the new layout with the adjusted top margin

#### Scenario: Adjust bottom margin via spinbox
- **WHEN** the user changes the value of the "下" (bottom) margin spinbox
- **THEN** the right-side merge preview updates within 500ms to show the new layout with the adjusted bottom margin

#### Scenario: Adjust left margin via spinbox
- **WHEN** the user changes the value of the "左" (left) margin spinbox
- **THEN** the right-side merge preview updates within 500ms to show the new layout with the adjusted left margin

#### Scenario: Adjust right margin via spinbox
- **WHEN** the user changes the value of the "右" (right) margin spinbox
- **THEN** the right-side merge preview updates within 500ms to show the new layout with the adjusted right margin

### Requirement: Preset selection triggers preview update
When the user selects a margin preset from the dropdown, the system SHALL update all four margin values and trigger the preview update within 500ms.

#### Scenario: Select preset margin
- **WHEN** the user selects "窄边距" from the preset dropdown
- **THEN** all four margin spinboxes update to the preset values (5mm each)
- **THEN** the right-side merge preview updates within 500ms to reflect the new margins

### Requirement: Reset margins triggers preview update
When the user clicks the "恢复默认" (reset default) button, the system SHALL restore all four margins to their default values and trigger the preview update.

#### Scenario: Reset to default margins
- **WHEN** the user clicks the "恢复默认" button
- **THEN** all four margin spinboxes reset to their default values (10mm each)
- **THEN** the right-side merge preview updates within 500ms to reflect the default margins