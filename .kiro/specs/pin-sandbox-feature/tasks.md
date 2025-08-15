# Implementation Plan

- [x] 1. Extend DockerRuntime with container management methods in python/sandbox/container_runtime.py
  - Add `rename_container()` method to rename containers
  - Add `update_container_labels()` method to add/update container labels
  - Add `get_containers_by_label()` method to find containers by label filters (needed for attach_sandbox_by_name)
  - Modify `stop_and_remove()` method to check for pinned status and only stop pinned containers
  - _Requirements: 1.1, 1.2, 1.5, 2.1, 2.2, 2.3, 3.1, 3.2, 3.3, 4.1, 4.2, 4.3, 4.4, 5.1, 5.2, 5.3_

- [x] 2. Implement pin_sandbox functionality in SessionManager in mcp-server/wrapper/session_manager.py
  - Add `pin_session()` method to handle sandbox pinning logic
  - Validate session exists and is active
  - Get container information from the managed session
  - Rename container to pinned_name using DockerRuntime
  - Update container labels with pinned=true and pinned_name
  - Update session's sandbox_name to reflect the new pinned name
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 5.1, 5.2, 6.1, 6.2_

- [x] 3. Implement attach_sandbox_by_name functionality in SessionManager in mcp-server/wrapper/session_manager.py
  - Add `attach_to_pinned_sandbox()` method to handle sandbox attachment
  - Search for containers by pinned_name (check container name first, then use label-based search)
  - Check container status (running/stopped)
  - Start container if stopped using DockerRuntime
  - Generate new session ID and create ManagedSession
  - Associate new session with existing container
  - Return session ID to caller
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 6.3, 6.4_

- [x] 4. Update container engine layer to handle pinned containers automatically
  - Modify `stop_and_remove()` method in python/sandbox/container_runtime.py to check container labels
  - For containers with `pinned=true` label: only stop the container, skip removal
  - For containers without pinned label: maintain existing stop and remove behavior
  - This ensures all cleanup operations (session, orphan, LRU) automatically preserve pinned containers
  - _Requirements: 2.1, 2.2, 2.3, 3.1, 3.2, 3.3, 5.3_

- [x] 5. Add pin_sandbox MCP tool to server
  - Create `pin_sandbox` tool in mcp_server/server.py
  - Accept session_id and pinned_name parameters
  - Call SessionManager.pin_session() method
  - Handle and return appropriate error messages from underlying operations
  - Return success message with pinned sandbox information
  - _Requirements: 1.1, 1.5, 6.1, 6.2, 6.4_

- [x] 6. Add attach_sandbox_by_name MCP tool to server
  - Create `attach_sandbox_by_name` tool in mcp_server/server.py
  - Accept pinned_name parameter
  - Call SessionManager.attach_to_pinned_sandbox() method
  - Handle and return appropriate error messages
  - Return session_id for successful attachment
  - _Requirements: 4.1, 4.5, 6.3, 6.4_

- [x] 7. Add error handling for pin operations
  - Handle SessionNotFoundError when session_id doesn't exist
  - Handle ContainerNotFoundError when session's container cannot be located
  - Pass through RuntimeError from container operations (rename, label update)
  - Provide clear error messages to users
  - _Requirements: 6.1, 6.2, 6.4_

- [x] 8. Add error handling for attach operations
  - Handle PinnedSandboxNotFoundError when pinned_name doesn't match any container
  - Handle ContainerStartError when stopped container cannot be started
  - Handle SessionCreationError when new session cannot be created
  - Provide clear error messages to users
  - _Requirements: 6.3, 6.4_

- [x] 9. Write unit tests for DockerRuntime extensions
  - Test container renaming functionality
  - Test container label operations (add, update)
  - Test container search by labels
  - Test modified stop_and_remove behavior with pinned containers
  - Test scripts must be placed in the /tests directory
  - _Requirements: All requirements - testing coverage_

- [x] 10. Write unit tests for pin_sandbox functionality
  - Test successful pinning of active sessions
  - Test error cases (invalid session, container not found)
  - Test label application and session mapping updates
  - Test container renaming during pin operation
  - Test scripts must be placed in the /tests directory
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 6.1, 6.2_

- [x] 11. Write unit tests for attach_sandbox_by_name functionality
  - Test attachment to running pinned containers
  - Test attachment to stopped pinned containers (with container start)
  - Test error cases (non-existent pinned sandbox)
  - Test session creation and association
  - Test scripts must be placed in the /tests directory
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 6.3_

- [x] 12. Write unit tests for modified cleanup logic
  - Test that `stop_and_remove()` only stops pinned containers (doesn't remove them)
  - Test that `stop_and_remove()` maintains existing behavior for unpinned containers
  - Test cleanup behavior with mixed pinned/unpinned containers
  - Test scripts must be placed in the /tests directory
  - _Requirements: 2.1, 2.2, 2.3, 3.1, 3.2, 3.3_

- [x] 13. Write integration tests for end-to-end workflows
  - Test pin sandbox → cleanup → attach → verify continuity
  - Test multiple pin/attach cycles
  - Test concurrent operations on pinned sandboxes
  - Test resource management with pinned containers
  - Test scripts must be placed in the /tests directory
  - _Requirements: All requirements - integration testing_