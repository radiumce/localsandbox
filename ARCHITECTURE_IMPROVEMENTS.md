# Architecture Improvements: Sandbox SDK Abstraction

## Overview

This document describes the architectural improvements made to properly isolate the wrapper layer from direct container runtime dependencies, ensuring clean separation of concerns and proper abstraction layers.

## Problem Statement

The original implementation violated the design principle that the wrapper layer should only interact with the sandbox SDK, not directly with container runtime implementations. The wrapper was directly importing and using `DockerRuntime`, which created tight coupling and violated the abstraction boundary.

## Solution

### 1. Extended Sandbox SDK with Pin/Attach Functionality

**Added to `python/sandbox/base_sandbox.py`:**
- `async def pin(pinned_name: str)` - Pin a sandbox with a persistent name
- `@classmethod async def attach_to_pinned(...)` - Attach to an existing pinned sandbox
- `@classmethod async def list_pinned(...)` - List all pinned sandboxes

**Added to `python/sandbox/container_runtime.py`:**
- `async def get_container_info(container_name_or_id: str)` - Get detailed container information

### 2. Updated Wrapper Layer to Use Sandbox SDK

**Modified `mcp-server/microsandbox_wrapper/session_manager.py`:**
- `pin_session()` now uses `session._sandbox.pin(pinned_name)` instead of direct DockerRuntime calls
- `attach_to_pinned_sandbox()` now uses `PythonSandbox.attach_to_pinned()` and `NodeSandbox.attach_to_pinned()` instead of direct container operations

### 3. Updated Terminology and Exceptions

**Added new sandbox-focused exceptions:**
- `SandboxNotFoundError` - Replaces container-specific errors in wrapper context
- `SandboxStartError` - Sandbox-specific startup errors

**Updated models and configuration:**
- `VolumeMapping.container_path` → `VolumeMapping.sandbox_path`
- Updated documentation to use "sandbox" terminology instead of "container"
- Configuration examples now use sandbox terminology

### 4. Maintained Backward Compatibility

- Container-related exceptions still exist for compatibility
- Existing APIs remain functional
- Tests updated to reflect new architecture

## Benefits

### 1. **Proper Abstraction**
- Wrapper layer no longer directly depends on container runtime
- Clean separation between sandbox SDK and container implementation
- Easier to add new runtime backends (e.g., Podman, containerd)

### 2. **Improved Maintainability**
- Changes to container runtime don't affect wrapper layer
- Clearer responsibility boundaries
- Easier to test and mock

### 3. **Better Terminology**
- Consistent use of "sandbox" terminology in wrapper layer
- "Container" terminology isolated to runtime implementation
- More intuitive for users who think in terms of sandboxes

### 4. **Enhanced Testability**
- Wrapper tests can mock sandbox SDK instead of container runtime
- Integration tests verify proper SDK usage
- Architecture compliance tests prevent regression

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    MCP Server                               │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                Wrapper Layer                               │
│  - session_manager.py (uses sandbox SDK only)             │
│  - wrapper.py                                             │
│  - Uses sandbox terminology                               │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                 Sandbox SDK                                │
│  - PythonSandbox, NodeSandbox                             │
│  - pin(), attach_to_pinned(), list_pinned()               │
│  - Abstracts container operations                         │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│              Container Runtime                             │
│  - DockerRuntime                                          │
│  - get_container_info(), rename_container(), etc.         │
│  - Uses container terminology                             │
└─────────────────────────────────────────────────────────────┘
```

## Testing

### Architecture Compliance Tests
- `test_wrapper_no_direct_container_imports()` - Ensures no direct container runtime imports
- `test_wrapper_uses_sandbox_terminology()` - Verifies sandbox terminology usage
- `test_session_manager_uses_sandbox_sdk()` - Confirms SDK method usage
- `test_sandbox_sdk_has_pin_methods()` - Validates SDK has required methods

### Integration Tests
- Updated to mock sandbox SDK instead of container runtime
- Test pin → cleanup → attach workflows
- Test multiple pin/attach cycles
- Test concurrent operations
- Test resource management

## Migration Guide

### For Developers

**Before:**
```python
from python.sandbox.container_runtime import DockerRuntime

docker_runtime = DockerRuntime("docker")
await docker_runtime.rename_container(old_name, new_name)
await docker_runtime.update_container_labels(name, labels)
```

**After:**
```python
# In wrapper layer - use sandbox SDK
await session._sandbox.pin(pinned_name)

# In sandbox SDK - container runtime is abstracted
sandbox = await PythonSandbox.attach_to_pinned(pinned_name)
```

### For Tests

**Before:**
```python
with patch('python.sandbox.container_runtime.DockerRuntime') as mock_docker:
    mock_docker.return_value.rename_container = AsyncMock()
    # Test wrapper functionality
```

**After:**
```python
with patch('sandbox.PythonSandbox.attach_to_pinned') as mock_attach:
    mock_attach.return_value = mock_sandbox
    # Test wrapper functionality
```

## Conclusion

These architectural improvements establish proper abstraction boundaries, improve maintainability, and ensure the wrapper layer correctly uses the sandbox SDK instead of directly depending on container runtime implementations. The changes maintain backward compatibility while providing a cleaner, more maintainable architecture.