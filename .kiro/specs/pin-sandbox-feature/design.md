# Design Document

## Overview

The pin_sandbox feature adds persistent sandbox functionality to the MCP server, allowing users to preserve specific sandboxes beyond normal session cleanup cycles. This feature leverages Docker container labels to mark containers as "pinned" and modifies the cleanup logic to preserve these containers while only stopping them during cleanup operations.

The feature consists of two main tools:
1. `pin_sandbox` - Pins a sandbox with a custom name and marks it for persistence
2. `attach_sandbox_by_name` - Attaches to a previously pinned sandbox by name

## Architecture

### Core Components

#### 1. Container Labeling System
- Uses Docker container labels to mark pinned sandboxes
- Labels used:
  - `pinned=true` - Indicates the container is pinned
  - `pinned_name=<name>` - The human-readable name assigned to the pinned sandbox

#### 2. Modified Cleanup Logic
- Session cleanup: Pinned containers are stopped but not removed
- Orphan cleanup: Pinned containers are stopped but not removed
- LRU eviction: Pinned containers are stopped but not removed
- Container labels are checked during all cleanup operations

#### 3. Session Management Integration
- Modified session manager to handle pinned sandbox reattachment
- Support for creating sessions from existing stopped containers

### Data Flow

#### Pin Sandbox Flow
1. User calls `pin_sandbox(session_id, pinned_name)`
2. System validates session exists and is active
3. Container is located using session information
4. Container is renamed to the pinned_name
5. Container labels are updated with pinned status and name
6. Session mapping is updated to use the new pinned_name

#### Attach Sandbox Flow
1. User calls `attach_sandbox_by_name(pinned_name)`
2. System searches for container with matching pinned_name (by container name or label)
3. Container status is checked (running/stopped)
4. If stopped, container is started
5. New session ID is generated and associated with the container
6. Session manager is updated with the new mapping
7. Session ID is returned to user

## Components and Interfaces

### New MCP Tools

#### pin_sandbox Tool
```python
@mcp.tool()
async def pin_sandbox(
    session_id: str = Field(description="ID of the session to pin"),
    pinned_name: str = Field(description="Human-readable name for the pinned sandbox"),
    ctx: Context = None,
) -> str:
    """Pin a sandbox with a custom name for persistence beyond session cleanup."""
```

#### attach_sandbox_by_name Tool
```python
@mcp.tool()
async def attach_sandbox_by_name(
    pinned_name: str = Field(description="Name of the pinned sandbox to attach to"),
    ctx: Context = None,
) -> str:
    """Attach to a previously pinned sandbox by name and return session ID."""
```

### Modified Components

#### 1. ManagedSession Class
- Modify `stop()` method to handle pinned containers differently (stop but don't remove)
- Update `sandbox_name` when container is renamed during pinning

#### 2. SessionManager Class
- Add `pin_session()` method
- Add `attach_to_pinned_sandbox()` method
- Modify cleanup logic to preserve pinned containers
- Update session-to-sandbox name mapping when containers are renamed

#### 3. ResourceManager Class
- Modify `_stop_orphan_sandbox()` to check for pinned status
- Update orphan cleanup to only stop (not remove) pinned containers
- Modify LRU eviction logic to only stop (not remove) pinned containers

#### 4. DockerRuntime Class
- Add `rename_container()` method
- Add `update_container_labels()` method
- Modify `stop_and_remove()` to handle pinned containers

### Data Model Changes

No new data models are required. The existing models will be used as follows:
- Container labels serve as the source of truth for pin status
- `SessionInfo.sandbox_name` is updated to reflect the pinned name when a sandbox is pinned
- Pin status is determined by checking container labels, not session state

## Error Handling

### Pin Operation Errors
- **SessionNotFoundError**: When session_id doesn't exist
- **ContainerNotFoundError**: When session's container cannot be located
- **RuntimeError**: When container operations (rename, label update) fail - passes through underlying container engine errors

### Attach Operation Errors
- **PinnedSandboxNotFoundError**: When pinned_name doesn't match any container
- **ContainerStartError**: When stopped container cannot be started
- **SessionCreationError**: When new session cannot be created for attachment

### Cleanup Operation Handling
- Pinned containers that fail to stop are logged but don't block cleanup
- Container label checks are wrapped in try-catch to handle missing containers
- Cleanup operations continue even if some pinned containers have issues

## Testing Strategy

### Unit Tests
1. **Container Labeling Tests**
   - Test label addition and update operations
   - Test label-based container filtering
   - Test label validation and error handling

2. **Pin Operation Tests**
   - Test successful pinning of active sessions
   - Test error cases (invalid session, container not found)
   - Test label application and session mapping updates

3. **Attach Operation Tests**
   - Test attachment to running pinned containers
   - Test attachment to stopped pinned containers
   - Test error cases (non-existent pinned sandbox)

4. **Cleanup Logic Tests**
   - Test session cleanup preserves pinned containers
   - Test orphan cleanup preserves pinned containers
   - Test LRU eviction preserves pinned containers
   - Test cleanup behavior with mixed pinned/unpinned containers

### Integration Tests
1. **End-to-End Workflow Tests**
   - Pin sandbox → cleanup → attach → verify continuity
   - Multiple pin/attach cycles
   - Concurrent operations on pinned sandboxes

2. **Resource Management Tests**
   - Pinned containers and resource limit calculations
   - LRU eviction behavior with pinned containers (stop but don't remove)
   - Resource cleanup with pinned containers

3. **Error Recovery Tests**
   - Recovery from failed pin operations
   - Recovery from failed attach operations
   - Cleanup behavior with corrupted container labels

## Implementation Notes

### Container Runtime Integration
- Leverage existing DockerRuntime class for container operations
- Use Docker CLI label operations for maximum compatibility
- Support both Docker and Podman through existing abstraction

### Backward Compatibility
- New tools are additive and don't affect existing functionality
- Existing cleanup logic is modified but maintains same behavior for unpinned containers
- No changes to existing MCP tool interfaces
