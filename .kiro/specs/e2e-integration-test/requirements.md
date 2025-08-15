# Requirements Document

## Introduction

This feature implements a comprehensive end-to-end integration test script for the MCP (Model Context Protocol) server that validates the complete sandbox lifecycle including session management, file persistence, pinning functionality, and volume mapping. The test will use the official MCP SDK client to ensure standards compliance and will follow the exact environment configuration specified in .env.example.

## Requirements

### Requirement 1

**User Story:** As a developer, I want an automated E2E test that validates the complete MCP server functionality, so that I can ensure all components work together correctly in a production-like environment.

#### Acceptance Criteria

1. WHEN the E2E test is executed THEN the system SHALL start the MCP server using environment variables from .env.example
2. WHEN the MCP server starts THEN the system SHALL use the official MCP SDK client for all communications
3. WHEN the test completes THEN the system SHALL provide a comprehensive test report showing all step results
4. IF any step fails THEN the system SHALL provide detailed error information and cleanup resources

### Requirement 2

**User Story:** As a developer, I want the E2E test to validate sandbox code execution capabilities, so that I can ensure basic functionality works correctly.

#### Acceptance Criteria

1. WHEN the test starts THEN the system SHALL execute a Python "hello world" script in a new sandbox
2. WHEN the Python script executes THEN the system SHALL capture and validate the output
3. WHEN the script execution completes THEN the system SHALL return a valid session_id for subsequent operations
4. IF the script execution fails THEN the system SHALL report the failure with detailed error information

### Requirement 3

**User Story:** As a developer, I want the E2E test to validate volume mapping functionality, so that I can ensure shared directories work correctly between host and container.

#### Acceptance Criteria

1. WHEN the sandbox is created THEN the system SHALL mount the shared volume as specified in MSB_SHARED_VOLUME_PATH
2. WHEN the test executes "ls /shared" THEN the system SHALL show the contents of the mapped host directory
3. WHEN files exist in the host shared directory THEN the system SHALL make them accessible in the container at /shared
4. IF volume mapping fails THEN the system SHALL report the mapping error with specific details

### Requirement 4

**User Story:** As a developer, I want the E2E test to validate file persistence within sandbox sessions, so that I can ensure state is maintained across multiple operations.

#### Acceptance Criteria

1. WHEN the test writes a file to /hello.txt with content "hello sandbox" THEN the system SHALL successfully create the file
2. WHEN the file is written THEN the system SHALL use the same session_id to maintain sandbox state
3. WHEN the file creation completes THEN the system SHALL verify the file exists and contains the correct content
4. IF file operations fail THEN the system SHALL report the specific file system error

### Requirement 5

**User Story:** As a developer, I want the E2E test to validate sandbox pinning functionality, so that I can ensure sandboxes can be preserved beyond session cleanup.

#### Acceptance Criteria

1. WHEN the test calls pin_sandbox with a session_id and pinned_name THEN the system SHALL successfully pin the sandbox
2. WHEN the sandbox is pinned THEN the system SHALL preserve all files and state from the original session
3. WHEN the pin operation completes THEN the system SHALL return confirmation of successful pinning
4. IF pinning fails THEN the system SHALL report the specific pinning error with session details

### Requirement 6

**User Story:** As a developer, I want the E2E test to validate session lifecycle management, so that I can ensure proper cleanup and resource management.

#### Acceptance Criteria

1. WHEN the test calls stop_session with a session_id THEN the system SHALL successfully terminate the session
2. WHEN the session stops THEN the system SHALL clean up associated container resources
3. WHEN session cleanup completes THEN the system SHALL confirm the session is no longer active
4. IF session cleanup fails THEN the system SHALL report the cleanup error with resource details

### Requirement 7

**User Story:** As a developer, I want the E2E test to validate sandbox reattachment functionality, so that I can ensure pinned sandboxes can be restored with preserved state.

#### Acceptance Criteria

1. WHEN the test calls attach_sandbox_by_name with a pinned_name THEN the system SHALL create a new session attached to the pinned sandbox
2. WHEN the attachment succeeds THEN the system SHALL return a new session_id for the restored sandbox
3. WHEN the sandbox is reattached THEN the system SHALL preserve all files and state from the original pinned sandbox
4. IF attachment fails THEN the system SHALL report the specific attachment error with pinned sandbox details

### Requirement 8

**User Story:** As a developer, I want the E2E test to validate state persistence across the complete pin-attach cycle, so that I can ensure data integrity throughout the sandbox lifecycle.

#### Acceptance Criteria

1. WHEN the test reads /hello.txt from the reattached sandbox THEN the system SHALL return the original content "hello sandbox"
2. WHEN the test executes "ls /shared" in the reattached sandbox THEN the system SHALL show the same volume mapping as the original session
3. WHEN all validation checks complete THEN the system SHALL confirm complete state preservation
4. IF state validation fails THEN the system SHALL report specific differences between original and restored state

### Requirement 9

**User Story:** As a developer, I want comprehensive documentation for running the E2E test, so that I can easily configure and execute the test in different environments.

#### Acceptance Criteria

1. WHEN the E2E test is implemented THEN the system SHALL provide an E2ETEST.md documentation file
2. WHEN the documentation is created THEN it SHALL include step-by-step configuration instructions
3. WHEN the documentation is created THEN it SHALL include example commands for running the test
4. WHEN the documentation is created THEN it SHALL include troubleshooting guidance for common issues