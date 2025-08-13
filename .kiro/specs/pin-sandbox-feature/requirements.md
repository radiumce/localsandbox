# Requirements Document

## Introduction

This feature adds sandbox pinning functionality to the MCP server, allowing users to persist specific sandboxes beyond normal session cleanup cycles. Pinned sandboxes are preserved during cleanup operations and can be reattached to new sessions, enabling long-running development environments and persistent workspaces.

## Requirements

### Requirement 1

**User Story:** As a developer, I want to pin a sandbox with a custom name, so that I can preserve my development environment beyond the current session.

#### Acceptance Criteria

1. WHEN a user calls pin_sandbox with session_id and pinned_name parameters THEN the system SHALL identify the sandbox associated with the session_id and rename it to the specified pinned_name
2. WHEN a sandbox is pinned THEN the system SHALL mark the associated container with a "pinned" label
3. WHEN a sandbox is pinned and currently running THEN the system SHALL update the session_id to pinned_name mapping
4. WHEN a sandbox is pinned THEN the system SHALL ensure the sandbox persists through normal cleanup cycles

### Requirement 2

**User Story:** As a developer, I want pinned sandboxes to survive session cleanup, so that my work environment is preserved when sessions end.

#### Acceptance Criteria

1. WHEN session cleanup occurs AND a sandbox is pinned THEN the system SHALL stop the container but NOT delete it
2. WHEN session cleanup occurs AND a sandbox is pinned THEN the system SHALL preserve all container data and state
3. WHEN session cleanup occurs AND a sandbox is pinned THEN the system SHALL remove the session association but keep the container

### Requirement 3

**User Story:** As a developer, I want pinned sandboxes to survive orphan cleanup, so that my persistent environments are not accidentally removed.

#### Acceptance Criteria

1. WHEN orphan cleanup occurs AND a container is marked as pinned THEN the system SHALL stop the container but NOT delete it
2. WHEN orphan cleanup occurs AND a container is marked as pinned THEN the system SHALL preserve the container for future reattachment
3. WHEN orphan cleanup occurs AND a container is marked as pinned THEN the system SHALL log the preservation action

### Requirement 4

**User Story:** As a developer, I want to attach to a pinned sandbox by name, so that I can resume work in my preserved environment.

#### Acceptance Criteria

1. WHEN a user calls attach_sandbox_by_name with a pinned sandbox name THEN the system SHALL check the sandbox status
2. WHEN attaching to a running non-orphan pinned sandbox THEN the system SHALL return the existing session_id
3. WHEN attaching to a running orphan pinned sandbox THEN the system SHALL assign a new session_id and return it
4. WHEN attaching to a stopped pinned sandbox THEN the system SHALL start the container, assign a new session_id, and return it
5. WHEN attaching to a non-existent sandbox name THEN the system SHALL return an appropriate error

### Requirement 5

**User Story:** As a system administrator, I want container labels to identify pinned sandboxes, so that the system can properly manage them during cleanup operations.

#### Acceptance Criteria

1. WHEN a sandbox is pinned THEN the system SHALL add a "pinned=true" label to the container
2. WHEN a sandbox is pinned THEN the system SHALL add a "pinned_name" label with the custom name
3. WHEN cleanup operations run THEN the system SHALL check container labels to determine pinned status
4. WHEN a pinned container is processed THEN the system SHALL use label information to preserve the container

### Requirement 6

**User Story:** As a developer, I want proper error handling for pin operations, so that I receive clear feedback when operations fail.

#### Acceptance Criteria

1. WHEN pin_sandbox is called with a pinned_name that is invalid according to the underlying container engine THEN the system SHALL return the container engine's error message
2. WHEN pin_sandbox is called on a non-existent sandbox THEN the system SHALL return an appropriate error
3. WHEN attach_sandbox_by_name is called with a non-existent name THEN the system SHALL return an appropriate error
4. WHEN container operations fail during pinning THEN the system SHALL return detailed error information