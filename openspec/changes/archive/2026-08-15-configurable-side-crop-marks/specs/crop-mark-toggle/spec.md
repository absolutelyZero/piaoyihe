## MODIFIED Requirements

### Requirement: Crop mark toggle in UI
The system SHALL provide a "显示轮廓裁切线" checkbox and left/right distance spinboxes in the layout settings card, positioned after the margin spinboxes.

#### Scenario: Toggle crop marks on
- **WHEN** the user checks the "显示轮廓裁切线" checkbox
- **THEN** the layout config SHALL include `show_crop_marks: true`
- **THEN** the merged PDF output SHALL include vertical dashed crop marks on the left and right sides

#### Scenario: Toggle crop marks off
- **WHEN** the user unchecks the "显示轮廓裁切线" checkbox
- **THEN** the layout config SHALL include `show_crop_marks: false`
- **THEN** the merged PDF output SHALL NOT include crop marks

### Requirement: Crop mark distance configuration
The system SHALL provide left and right distance spinboxes (mm) for configuring the crop mark position from the page edge.

#### Scenario: Configure left crop mark distance
- **WHEN** the user sets the left crop mark distance to 5mm and enables crop marks
- **THEN** a vertical dashed line SHALL be drawn 5mm from the left page edge

#### Scenario: Configure right crop mark distance
- **WHEN** the user sets the right crop mark distance to 10mm and enables crop marks
- **THEN** a vertical dashed line SHALL be drawn 10mm from the right page edge

#### Scenario: Distance is 0
- **WHEN** the left or right crop mark distance is 0mm
- **THEN** the corresponding crop mark SHALL NOT be drawn

### Requirement: Crop mark appearance
When crop marks are enabled, the system SHALL draw vertical dashed lines at the configured distances from the left and right page edges, extending from the top to the bottom of the page.

#### Scenario: Left crop mark
- **WHEN** crop marks are enabled and left distance > 0
- **THEN** a vertical dashed line SHALL be drawn at `x = distance_left_pt` from `y = 0` to `y = page_height`
- **THEN** the line style SHALL be gray, dash=5, gap=3, width=0.5

#### Scenario: Right crop mark
- **WHEN** crop marks are enabled and right distance > 0
- **THEN** a vertical dashed line SHALL be drawn at `x = page_width - distance_right_pt` from `y = 0` to `y = page_height`

### Requirement: Crop mark state persistence
The system SHALL save the crop mark toggle and distance settings to config.json and restore them on restart.

#### Scenario: Save and restore crop mark settings
- **WHEN** the user configures crop marks and exits the application
- **THEN** upon restarting, the checkbox and distance values SHALL be restored

#### Scenario: Default state
- **WHEN** no config.json exists or the config lacks crop mark settings
- **THEN** the checkbox SHALL be unchecked, left and right distances SHALL be 0