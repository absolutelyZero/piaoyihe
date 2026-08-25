## MODIFIED Requirements

### Requirement: Crop mark appearance
When crop marks are enabled, the system SHALL draw dashed lines along the four margin edges, extending from the page edge to the content area edge. The system SHALL skip drawing a crop mark on any edge where the corresponding margin value is 0.

#### Scenario: Top margin is 0
- **WHEN** the top margin is set to 0mm and crop marks are enabled
- **THEN** the top crop mark SHALL NOT be drawn
- **THEN** the other three crop marks SHALL still be drawn

#### Scenario: Bottom margin is 0
- **WHEN** the bottom margin is set to 0mm and crop marks are enabled
- **THEN** the bottom crop mark SHALL NOT be drawn

#### Scenario: Left margin is 0
- **WHEN** the left margin is set to 0mm and crop marks are enabled
- **THEN** the left crop mark SHALL NOT be drawn

#### Scenario: Right margin is 0
- **WHEN** the right margin is set to 0mm and crop marks are enabled
- **THEN** the right crop mark SHALL NOT be drawn

#### Scenario: All margins are 0
- **WHEN** all four margins are set to 0mm and crop marks are enabled
- **THEN** no crop marks SHALL be drawn