## ADDED Requirements

### Requirement: Crop mark toggle in UI
The system SHALL provide a checkbox labeled "裁切线" in the mode and order settings card, positioned after the print order dropdown.

#### Scenario: Toggle crop marks on
- **WHEN** the user checks the "裁切线" checkbox
- **THEN** the layout config SHALL include `show_crop_marks: true`
- **THEN** the merged PDF output SHALL include dashed crop marks along the four margins

#### Scenario: Toggle crop marks off
- **WHEN** the user unchecks the "裁切线" checkbox
- **THEN** the layout config SHALL include `show_crop_marks: false`
- **THEN** the merged PDF output SHALL NOT include crop marks

### Requirement: Crop mark appearance
When crop marks are enabled, the system SHALL draw dashed lines along the four margin edges, extending from the page edge to the content area edge.

#### Scenario: Top crop mark
- **WHEN** crop marks are enabled and a page is generated
- **THEN** a dashed line SHALL be drawn at `y = margin_top` from `x = 0` to `x = page_width`
- **THEN** the line style SHALL be gray, dash=5, gap=3, width=0.5

#### Scenario: Bottom crop mark
- **WHEN** crop marks are enabled and a page is generated
- **THEN** a dashed line SHALL be drawn at `y = page_height - margin_bottom` from `x = 0` to `x = page_width`

#### Scenario: Left crop mark
- **WHEN** crop marks are enabled and a page is generated
- **THEN** a dashed line SHALL be drawn at `x = margin_left` from `y = 0` to `y = page_height`

#### Scenario: Right crop mark
- **WHEN** crop marks are enabled and a page is generated
- **THEN** a dashed line SHALL be drawn at `x = page_width - margin_right` from `y = 0` to `y = page_height`

### Requirement: Crop mark state persistence
The system SHALL save the crop mark toggle state to config.json and restore it on restart.

#### Scenario: Save and restore crop mark state
- **WHEN** the user checks the "裁切线" checkbox and exits the application
- **THEN** upon restarting the application, the checkbox SHALL remain checked
- **THEN** the merged PDF SHALL still include crop marks

#### Scenario: Default state (off)
- **WHEN** no config.json exists or the config lacks `show_crop_marks`
- **THEN** the checkbox SHALL be unchecked (default off)