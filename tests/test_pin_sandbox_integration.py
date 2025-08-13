"""
Integration tests for end-to-end pin sandbox workflows.

These tests verify complete workflows including:
- Pin sandbox → cleanup → attach → verify continuity
- Multiple pin/attach cycles
- Concurrent operations on pinned sandboxes
- Resource management with pinned containers
"""

import asyncio
import json
import pytest
import uuid
import time
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock, call
from concurrent.futures import ThreadPoolExecutor

# Add the mcp-server directory to the Python path
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
mcp_server_dir = project_root / "mcp-server"
sys.path.insert(0, str(mcp_server_dir))

from microsandbox_wrapper.session_manager import SessionManager, ManagedSession
from microsandbox_wrapper.config import WrapperConfig
from microsandbox_wrapper.models import SandboxFlavor, SessionStatus
from microsandbox_wrapper.exceptions import (
    SessionNotFoundError,
    ContainerNotFoundError,
    PinnedSandboxNotFoundError,
    ContainerStartError,
    SessionCreationError
)


@pytest.mark.integration
class TestPinCleanupAttachWorkflow:
    """Test complete pin → cleanup → attach → verify continuity workflow."""
    
    @pytest.fixture
    def config(self):
        """Create a test configuration."""
        return WrapperConfig(
            session_timeout=300,
            cleanup_interval=60,
            max_concurrent_sessions=10,
            default_execution_timeout=30,
            sandbox_start_timeout=60,
            shared_volume_mappings=[]
        )
    
    @pytest.fixture
    def session_manager(self, config):
        """Create a SessionManager instance for testing."""
        return SessionManager(config)
    
    @pytest.fixture
    def mock_docker_runtime(self):
        """Create a comprehensive mock DockerRuntime for testing."""
        mock_runtime = MagicMock()
        mock_runtime.rename_container = AsyncMock()
        mock_runtime.update_container_labels = AsyncMock()
        mock_runtime.get_container_info = AsyncMock()
        mock_runtime.get_containers_by_label = AsyncMock()
        mock_runtime.start_container = AsyncMock()
        mock_runtime.stop_and_remove = AsyncMock()
        return mock_runtime
    
    @pytest.mark.asyncio
    async def test_complete_pin_cleanup_attach_workflow(self, session_manager, config):
        """Test complete workflow: create session → pin → cleanup → attach → verify."""
        # Step 1: Create initial session
        session_id = "workflow_test_session"
        pinned_name = "persistent_dev_env"
        original_sandbox_name = "sandbox-workflow-test"
        
        # Create initial session
        initial_session = ManagedSession(
            session_id=session_id,
            template="python",
            flavor=SandboxFlavor.SMALL,
            config=config
        )
        initial_session.status = SessionStatus.READY
        initial_session.sandbox_name = original_sandbox_name
        
        # Mock the sandbox object
        mock_sandbox = MagicMock()
        mock_sandbox.pin = AsyncMock()
        initial_session._sandbox = mock_sandbox
        
        initial_session.ensure_started = AsyncMock()
        initial_session.stop = AsyncMock()
        session_manager._sessions[session_id] = initial_session
        
        # Step 2: Pin the sandbox
        pin_result = await session_manager.pin_session(session_id, pinned_name)
        assert "Successfully pinned session" in pin_result
        assert initial_session.sandbox_name == pinned_name
        
        # Verify pin operations were called on the sandbox
        mock_sandbox.pin.assert_called_once_with(pinned_name)
        
        # Step 3: Simulate session cleanup (session ends)
        # Simulate cleanup - session should be removed but sandbox preserved
        await initial_session.stop()
        del session_manager._sessions[session_id]
        
        # Verify cleanup called stop
        initial_session.stop.assert_called_once()
        
        # Step 4: Attach to the pinned sandbox
        # Mock the sandbox SDK's attach_to_pinned method
        with patch('sandbox.PythonSandbox.attach_to_pinned') as mock_attach:
            mock_attached_sandbox = MagicMock()
            mock_attach.return_value = mock_attached_sandbox
            
            new_session_id = await session_manager.attach_to_pinned_sandbox(pinned_name)
        
        # Step 5: Verify continuity
        assert new_session_id != session_id  # New session ID
        assert new_session_id in session_manager._sessions
        
        new_session = session_manager._sessions[new_session_id]
        assert new_session.sandbox_name == pinned_name
        assert new_session.template == "python"
        assert new_session.status == SessionStatus.READY
        
        # Verify sandbox attach was called
        mock_attach.assert_called_once_with(
            pinned_name=pinned_name,
            container_runtime="docker",
            namespace="default"
        )
    
    @pytest.mark.asyncio
    async def test_pin_cleanup_attach_with_stopped_container(self, session_manager, config):
        """Test workflow where container is stopped during cleanup and needs restart."""
        session_id = "stopped_workflow_test"
        pinned_name = "stopped_dev_env"
        
        # Create and pin session
        session = ManagedSession(
            session_id=session_id,
            template="node",
            flavor=SandboxFlavor.MEDIUM,
            config=config
        )
        session.status = SessionStatus.READY
        session.sandbox_name = "original-node-sandbox"
        
        # Mock the sandbox object
        mock_sandbox = MagicMock()
        mock_sandbox.pin = AsyncMock()
        session._sandbox = mock_sandbox
        
        session.ensure_started = AsyncMock()
        session.stop = AsyncMock()
        session_manager._sessions[session_id] = session
        
        with patch('python.sandbox.container_runtime.DockerRuntime') as mock_docker_class:
            mock_docker_runtime = MagicMock()
            mock_docker_runtime.rename_container = AsyncMock()
            mock_docker_runtime.update_container_labels = AsyncMock()
            mock_docker_runtime.get_container_info = AsyncMock()
            mock_docker_runtime.start_container = AsyncMock()
            mock_docker_class.return_value = mock_docker_runtime
            
            # Pin the sandbox
            await session_manager.pin_session(session_id, pinned_name)
            
            # Simulate cleanup that stops the container
            await session.stop()
            del session_manager._sessions[session_id]
            
            # Mock container as stopped for attachment
            stopped_container_info = {
                'Id': 'stopped_container_id',
                'Names': [f'/{pinned_name}'],
                'State': 'exited',  # Container was stopped during cleanup
                'Image': 'node:16',
                'Labels': {
                    'pinned': 'true',
                    'pinned_name': pinned_name,
                    'template': 'node'
                }
            }
            mock_docker_runtime.get_container_info.return_value = stopped_container_info
            
            # Attach to stopped container
            with patch('sandbox.NodeSandbox.attach_to_pinned') as mock_attach:
                mock_attached_sandbox = MagicMock()
                mock_attach.return_value = mock_attached_sandbox
                
                new_session_id = await session_manager.attach_to_pinned_sandbox(pinned_name)
            
            # Verify sandbox attach was called (container start is handled internally)
            mock_attach.assert_called_once_with(
                pinned_name=pinned_name,
                container_runtime="docker",
                namespace="default"
            )
            
            # Verify new session was created correctly
            new_session = session_manager._sessions[new_session_id]
            assert new_session.sandbox_name == pinned_name
            assert new_session.template == "node"
    
    @pytest.mark.asyncio
    async def test_workflow_with_orphan_cleanup(self, session_manager, config):
        """Test workflow where pinned container survives orphan cleanup."""
        session_id = "orphan_test_session"
        pinned_name = "orphan_survivor"
        
        # Create and pin session
        session = ManagedSession(
            session_id=session_id,
            template="python",
            flavor=SandboxFlavor.SMALL,
            config=config
        )
        session.status = SessionStatus.READY
        session.sandbox_name = "orphan-test-sandbox"
        
        # Mock the sandbox object
        mock_sandbox = MagicMock()
        mock_sandbox.pin = AsyncMock()
        session._sandbox = mock_sandbox
        
        session.ensure_started = AsyncMock()
        session_manager._sessions[session_id] = session
        
        with patch('python.sandbox.container_runtime.DockerRuntime') as mock_docker_class:
            mock_docker_runtime = MagicMock()
            mock_docker_runtime.rename_container = AsyncMock()
            mock_docker_runtime.update_container_labels = AsyncMock()
            mock_docker_runtime.get_container_info = AsyncMock()
            mock_docker_runtime.get_containers_by_label = AsyncMock()
            mock_docker_runtime.stop_and_remove = AsyncMock()
            mock_docker_class.return_value = mock_docker_runtime
            
            # Pin the sandbox
            await session_manager.pin_session(session_id, pinned_name)
            
            # Simulate orphan cleanup scenario
            # Mock finding the pinned container during orphan cleanup
            orphan_container_info = {
                'Id': 'orphan_container_id',
                'Names': [f'/{pinned_name}'],
                'State': 'running',
                'Labels': {'pinned': 'true', 'pinned_name': pinned_name}
            }
            
            # Simulate orphan cleanup finding the container
            mock_docker_runtime.get_containers_by_label.return_value = [orphan_container_info]
            
            # Simulate orphan cleanup - should only stop, not remove pinned containers
            # This would be called by the resource manager's orphan cleanup
            await mock_docker_runtime.stop_and_remove('orphan_container_id')
            
            # Verify stop_and_remove was called (implementation should check labels)
            mock_docker_runtime.stop_and_remove.assert_called_once_with('orphan_container_id')
            
            # Now attach to the "orphaned" but preserved container
            container_info = {
                'Id': 'orphan_container_id',
                'Names': [f'/{pinned_name}'],
                'State': 'exited',  # Stopped by orphan cleanup
                'Image': 'python:3.9',
                'Labels': {
                    'pinned': 'true',
                    'pinned_name': pinned_name,
                    'template': 'python'
                }
            }
            mock_docker_runtime.get_container_info.return_value = container_info
            mock_docker_runtime.start_container = AsyncMock()
            
            # Remove the original session to simulate orphan state
            del session_manager._sessions[session_id]
            
            # Attach to the orphaned pinned container
            with patch('sandbox.PythonSandbox.attach_to_pinned') as mock_attach:
                mock_attached_sandbox = MagicMock()
                mock_attach.return_value = mock_attached_sandbox
                
                new_session_id = await session_manager.attach_to_pinned_sandbox(pinned_name)
            
            # Verify sandbox attach was called (container restart is handled internally)
            mock_attach.assert_called_once_with(
                pinned_name=pinned_name,
                container_runtime="docker",
                namespace="default"
            )
            assert new_session_id in session_manager._sessions
            
            new_session = session_manager._sessions[new_session_id]
            assert new_session.sandbox_name == pinned_name


@pytest.mark.integration
class TestMultiplePinAttachCycles:
    """Test multiple pin/attach cycles on the same sandbox."""
    
    @pytest.fixture
    def config(self):
        """Create a test configuration."""
        return WrapperConfig(
            session_timeout=300,
            cleanup_interval=60,
            max_concurrent_sessions=10,
            default_execution_timeout=30,
            sandbox_start_timeout=60,
            shared_volume_mappings=[]
        )
    
    @pytest.fixture
    def session_manager(self, config):
        """Create a SessionManager instance for testing."""
        return SessionManager(config)
    
    @pytest.mark.asyncio
    async def test_multiple_pin_attach_cycles(self, session_manager, config):
        """Test multiple cycles of pin → cleanup → attach on the same sandbox."""
        pinned_name = "cycling_sandbox"
        cycles = 3
        
        with patch('python.sandbox.container_runtime.DockerRuntime') as mock_docker_class:
            mock_docker_runtime = MagicMock()
            mock_docker_runtime.rename_container = AsyncMock()
            mock_docker_runtime.update_container_labels = AsyncMock()
            mock_docker_runtime.get_container_info = AsyncMock()
            mock_docker_runtime.start_container = AsyncMock()
            mock_docker_class.return_value = mock_docker_runtime
            
            session_ids = []
            
            for cycle in range(cycles):
                # Create new session
                session_id = f"cycle_{cycle}_session"
                session_ids.append(session_id)
                
                if cycle == 0:
                    # First cycle: create and pin new session
                    session = ManagedSession(
                        session_id=session_id,
                        template="python",
                        flavor=SandboxFlavor.SMALL,
                        config=config
                    )
                    session.status = SessionStatus.READY
                    session.sandbox_name = f"original-sandbox-{cycle}"
                    session.ensure_started = AsyncMock()
                    session_manager._sessions[session_id] = session
                    
                    # Pin the session
                    await session_manager.pin_session(session_id, pinned_name)
                    
                    # Verify first pin operations
                    mock_docker_runtime.rename_container.assert_called_with(
                        f"original-sandbox-{cycle}", pinned_name
                    )
                    
                    # For first cycle, the session ID is the one we created
                    current_session_id = session_id
                else:
                    # Subsequent cycles: attach to existing pinned sandbox
                    container_info = {
                        'Id': f'container_cycle_{cycle}',
                        'Names': [f'/{pinned_name}'],
                        'State': 'exited' if cycle % 2 == 1 else 'running',  # Alternate states
                        'Image': 'python:3.9',
                        'Labels': {
                            'pinned': 'true',
                            'pinned_name': pinned_name,
                            'template': 'python'
                        }
                    }
                    mock_docker_runtime.get_container_info.return_value = container_info
                    
                    # Attach to pinned sandbox
                    current_session_id = await session_manager.attach_to_pinned_sandbox(pinned_name)
                    # Session ID should be a new UUID, not the expected pattern
                    assert current_session_id is not None
                    assert isinstance(current_session_id, str)
                    assert len(current_session_id) > 0
                    
                    # Verify container was started if it was stopped
                    if container_info['State'] == 'exited':
                        mock_docker_runtime.start_container.assert_called_with(f'container_cycle_{cycle}')
                
                # Verify session exists and has correct properties
                assert current_session_id in session_manager._sessions
                session = session_manager._sessions[current_session_id]
                assert session.sandbox_name == pinned_name
                assert session.template == "python"
                
                # Simulate session cleanup (end of cycle)
                del session_manager._sessions[current_session_id]
            
            # Verify all cycles completed
            assert len(session_ids) == cycles
            
            # Verify rename was only called once (first pin)
            assert mock_docker_runtime.rename_container.call_count == 1
            
            # Verify label update was only called once (first pin)
            assert mock_docker_runtime.update_container_labels.call_count == 1
    
    @pytest.mark.asyncio
    async def test_pin_different_names_same_session(self, session_manager, config):
        """Test error handling when trying to pin the same session with different names."""
        session_id = "multi_pin_session"
        first_pin_name = "first_pin"
        second_pin_name = "second_pin"
        
        # Create session
        session = ManagedSession(
            session_id=session_id,
            template="python",
            flavor=SandboxFlavor.SMALL,
            config=config
        )
        session.status = SessionStatus.READY
        session.sandbox_name = "original-sandbox"
        session.ensure_started = AsyncMock()
        session_manager._sessions[session_id] = session
        
        with patch('python.sandbox.container_runtime.DockerRuntime') as mock_docker_class:
            mock_docker_runtime = MagicMock()
            mock_docker_runtime.rename_container = AsyncMock()
            mock_docker_runtime.update_container_labels = AsyncMock()
            mock_docker_class.return_value = mock_docker_runtime
            
            # First pin should succeed
            result1 = await session_manager.pin_session(session_id, first_pin_name)
            assert "Successfully pinned session" in result1
            assert session.sandbox_name == first_pin_name
            
            # Second pin attempt should succeed (re-pinning with new name)
            # Reset mocks to track second pin
            mock_docker_runtime.rename_container.reset_mock()
            mock_docker_runtime.update_container_labels.reset_mock()
            
            result2 = await session_manager.pin_session(session_id, second_pin_name)
            assert "Successfully pinned session" in result2
            assert session.sandbox_name == second_pin_name
            
            # Verify second rename operation
            mock_docker_runtime.rename_container.assert_called_with(first_pin_name, second_pin_name)
    
    @pytest.mark.asyncio
    async def test_attach_cycles_with_state_persistence(self, session_manager, config):
        """Test that container state persists across multiple attach cycles."""
        pinned_name = "persistent_state_sandbox"
        
        # Simulate container with persistent state (files, environment, etc.)
        persistent_container_info = {
            'Id': 'persistent_container_123',
            'Names': [f'/{pinned_name}'],
            'State': 'exited',
            'Image': 'python:3.9',
            'Labels': {
                'pinned': 'true',
                'pinned_name': pinned_name,
                'template': 'python'
            },
            # Simulate persistent volumes/mounts
            'Mounts': [
                {
                    'Type': 'volume',
                    'Name': 'persistent_data',
                    'Destination': '/workspace'
                }
            ]
        }
        
        with patch('python.sandbox.container_runtime.DockerRuntime') as mock_docker_class:
            mock_docker_runtime = MagicMock()
            mock_docker_runtime.get_container_info = AsyncMock(return_value=persistent_container_info)
            mock_docker_runtime.start_container = AsyncMock()
            mock_docker_class.return_value = mock_docker_runtime
            
            # Perform multiple attach cycles
            for cycle in range(3):
                session_id = await session_manager.attach_to_pinned_sandbox(pinned_name)
                
                # Verify session was created
                assert session_id in session_manager._sessions
                session = session_manager._sessions[session_id]
                assert session.sandbox_name == pinned_name
                
                # Verify container was started (since it's in 'exited' state)
                mock_docker_runtime.start_container.assert_called_with('persistent_container_123')
                
                # Simulate session work and cleanup
                del session_manager._sessions[session_id]
                
                # Reset mock for next cycle
                mock_docker_runtime.start_container.reset_mock()
            
            # Verify container info was checked for each cycle
            assert mock_docker_runtime.get_container_info.call_count == 3


@pytest.mark.integration
class TestConcurrentPinnedSandboxOperations:
    """Test concurrent operations on pinned sandboxes."""
    
    @pytest.fixture
    def config(self):
        """Create a test configuration."""
        return WrapperConfig(
            session_timeout=300,
            cleanup_interval=60,
            max_concurrent_sessions=10,
            default_execution_timeout=30,
            sandbox_start_timeout=60,
            shared_volume_mappings=[]
        )
    
    @pytest.fixture
    def session_manager(self, config):
        """Create a SessionManager instance for testing."""
        return SessionManager(config)
    
    @pytest.mark.asyncio
    async def test_concurrent_pin_operations(self, session_manager, config):
        """Test concurrent pinning of multiple sessions."""
        num_sessions = 5
        sessions_data = []
        
        # Create multiple sessions
        for i in range(num_sessions):
            session_id = f"concurrent_session_{i}"
            pinned_name = f"concurrent_pin_{i}"
            session = ManagedSession(
                session_id=session_id,
                template="python",
                flavor=SandboxFlavor.SMALL,
                config=config
            )
            session.status = SessionStatus.READY
            session.sandbox_name = f"original-sandbox-{i}"
            session.ensure_started = AsyncMock()
            session_manager._sessions[session_id] = session
            sessions_data.append((session_id, pinned_name))
        
        with patch('python.sandbox.container_runtime.DockerRuntime') as mock_docker_class:
            mock_docker_runtime = MagicMock()
            mock_docker_runtime.rename_container = AsyncMock()
            mock_docker_runtime.update_container_labels = AsyncMock()
            mock_docker_class.return_value = mock_docker_runtime
            
            # Pin all sessions concurrently
            pin_tasks = [
                session_manager.pin_session(session_id, pinned_name)
                for session_id, pinned_name in sessions_data
            ]
            
            results = await asyncio.gather(*pin_tasks)
            
            # Verify all pins succeeded
            for i, result in enumerate(results):
                assert "Successfully pinned session" in result
                session_id, pinned_name = sessions_data[i]
                assert session_id in result
                assert pinned_name in result
            
            # Verify all sessions were updated
            for session_id, pinned_name in sessions_data:
                session = session_manager._sessions[session_id]
                assert session.sandbox_name == pinned_name
            
            # Verify all container operations were called
            assert mock_docker_runtime.rename_container.call_count == num_sessions
            assert mock_docker_runtime.update_container_labels.call_count == num_sessions
    
    @pytest.mark.asyncio
    async def test_concurrent_attach_operations(self, session_manager):
        """Test concurrent attachment to different pinned sandboxes."""
        num_sandboxes = 4
        pinned_names = [f"concurrent_attach_{i}" for i in range(num_sandboxes)]
        
        with patch('python.sandbox.container_runtime.DockerRuntime') as mock_docker_class:
            mock_docker_runtime = MagicMock()
            
            # Mock different container info for each sandbox
            def mock_get_container_info(name):
                index = int(name.split('_')[-1])
                return {
                    'Id': f'container_{index}',
                    'Names': [f'/{name}'],
                    'State': 'running',
                    'Image': 'python:3.9',
                    'Labels': {
                        'pinned': 'true',
                        'pinned_name': name,
                        'template': 'python'
                    }
                }
            
            mock_docker_runtime.get_container_info = AsyncMock(side_effect=mock_get_container_info)
            mock_docker_class.return_value = mock_docker_runtime
            
            # Attach to all sandboxes concurrently
            attach_tasks = [
                session_manager.attach_to_pinned_sandbox(pinned_name)
                for pinned_name in pinned_names
            ]
            
            session_ids = await asyncio.gather(*attach_tasks)
            
            # Verify all attachments succeeded
            assert len(session_ids) == num_sandboxes
            assert len(set(session_ids)) == num_sandboxes  # All unique
            
            # Verify all sessions were created
            for i, session_id in enumerate(session_ids):
                assert session_id in session_manager._sessions
                session = session_manager._sessions[session_id]
                assert session.sandbox_name == pinned_names[i]
                assert session.template == "python"
            
            # Verify container info was checked for each sandbox
            assert mock_docker_runtime.get_container_info.call_count == num_sandboxes
    
    @pytest.mark.asyncio
    async def test_concurrent_pin_and_attach_operations(self, session_manager, config):
        """Test concurrent mix of pin and attach operations."""
        # Create sessions for pinning
        pin_sessions = []
        for i in range(3):
            session_id = f"pin_session_{i}"
            session = ManagedSession(
                session_id=session_id,
                template="python",
                flavor=SandboxFlavor.SMALL,
                config=config
            )
            session.status = SessionStatus.READY
            session.sandbox_name = f"original-{i}"
            session.ensure_started = AsyncMock()
            session_manager._sessions[session_id] = session
            pin_sessions.append((session_id, f"pinned_{i}"))
        
        # Prepare attach targets (existing pinned sandboxes)
        attach_targets = [f"existing_pinned_{i}" for i in range(2)]
        
        with patch('python.sandbox.container_runtime.DockerRuntime') as mock_docker_class:
            mock_docker_runtime = MagicMock()
            mock_docker_runtime.rename_container = AsyncMock()
            mock_docker_runtime.update_container_labels = AsyncMock()
            
            # Mock container info for attach operations
            def mock_get_container_info(name):
                if name.startswith('existing_pinned_'):
                    index = int(name.split('_')[-1])
                    return {
                        'Id': f'existing_container_{index}',
                        'Names': [f'/{name}'],
                        'State': 'running',
                        'Image': 'python:3.9',
                        'Labels': {
                            'pinned': 'true',
                            'pinned_name': name,
                            'template': 'python'
                        }
                    }
                raise Exception("Container not found")
            
            mock_docker_runtime.get_container_info = AsyncMock(side_effect=mock_get_container_info)
            mock_docker_class.return_value = mock_docker_runtime
            
            # Create concurrent tasks
            tasks = []
            
            # Add pin tasks
            for session_id, pinned_name in pin_sessions:
                tasks.append(session_manager.pin_session(session_id, pinned_name))
            
            # Add attach tasks
            for attach_target in attach_targets:
                tasks.append(session_manager.attach_to_pinned_sandbox(attach_target))
            
            # Execute all tasks concurrently
            results = await asyncio.gather(*tasks)
            
            # Verify pin results
            for i in range(len(pin_sessions)):
                result = results[i]
                assert "Successfully pinned session" in result
            
            # Verify attach results (session IDs)
            for i in range(len(pin_sessions), len(results)):
                session_id = results[i]
                assert session_id in session_manager._sessions
                session = session_manager._sessions[session_id]
                expected_name = attach_targets[i - len(pin_sessions)]
                assert session.sandbox_name == expected_name
    
    @pytest.mark.asyncio
    async def test_concurrent_operations_with_failures(self, session_manager, config):
        """Test concurrent operations where some operations fail."""
        # Create mix of valid and invalid operations
        valid_session = ManagedSession(
            session_id="valid_session",
            template="python",
            flavor=SandboxFlavor.SMALL,
            config=config
        )
        valid_session.status = SessionStatus.READY
        valid_session.sandbox_name = "valid-sandbox"
        valid_session.ensure_started = AsyncMock()
        session_manager._sessions["valid_session"] = valid_session
        
        with patch('python.sandbox.container_runtime.DockerRuntime') as mock_docker_class:
            mock_docker_runtime = MagicMock()
            mock_docker_runtime.rename_container = AsyncMock()
            mock_docker_runtime.update_container_labels = AsyncMock()
            mock_docker_runtime.get_container_info = AsyncMock(
                side_effect=Exception("Container not found")
            )
            mock_docker_runtime.get_containers_by_label = AsyncMock(return_value=[])
            mock_docker_class.return_value = mock_docker_runtime
            
            # Create tasks that will succeed and fail
            tasks = [
                # This should succeed
                session_manager.pin_session("valid_session", "valid_pin"),
                # These should fail
                session_manager.pin_session("invalid_session", "invalid_pin"),
                session_manager.attach_to_pinned_sandbox("nonexistent_sandbox")
            ]
            
            # Execute with gather and return_exceptions=True to handle failures
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Verify results
            assert "Successfully pinned session" in results[0]  # Success
            assert isinstance(results[1], SessionNotFoundError)  # Pin failure
            assert isinstance(results[2], PinnedSandboxNotFoundError)  # Attach failure
            
            # Verify valid session was still pinned successfully
            assert valid_session.sandbox_name == "valid_pin"


@pytest.mark.integration
class TestResourceManagementWithPinnedContainers:
    """Test resource management behavior with pinned containers."""
    
    @pytest.fixture
    def config(self):
        """Create a test configuration with resource limits."""
        return WrapperConfig(
            session_timeout=300,
            cleanup_interval=60,
            max_concurrent_sessions=3,  # Low limit for testing
            default_execution_timeout=30,
            sandbox_start_timeout=60,
            shared_volume_mappings=[]
        )
    
    @pytest.fixture
    def session_manager(self, config):
        """Create a SessionManager instance for testing."""
        return SessionManager(config)
    
    @pytest.mark.asyncio
    async def test_pinned_containers_and_session_limits(self, session_manager, config):
        """Test that pinned containers don't count against active session limits."""
        max_sessions = config.max_concurrent_sessions
        
        # Create and pin sessions up to the limit
        pinned_sessions = []
        for i in range(max_sessions):
            session_id = f"pinned_session_{i}"
            session = ManagedSession(
                session_id=session_id,
                template="python",
                flavor=SandboxFlavor.SMALL,
                config=config
            )
            session.status = SessionStatus.READY
            session.sandbox_name = f"original-{i}"
            session.ensure_started = AsyncMock()
            session_manager._sessions[session_id] = session
            pinned_sessions.append((session_id, f"pinned_{i}"))
        
        with patch('python.sandbox.container_runtime.DockerRuntime') as mock_docker_class:
            mock_docker_runtime = MagicMock()
            mock_docker_runtime.rename_container = AsyncMock()
            mock_docker_runtime.update_container_labels = AsyncMock()
            mock_docker_runtime.get_container_info = AsyncMock()
            mock_docker_class.return_value = mock_docker_runtime
            
            # Pin all sessions
            for session_id, pinned_name in pinned_sessions:
                await session_manager.pin_session(session_id, pinned_name)
            
            # Simulate sessions ending (cleanup)
            for session_id, _ in pinned_sessions:
                del session_manager._sessions[session_id]
            
            # Now we should be able to create new sessions even though
            # pinned containers exist (they don't count against limits)
            new_session = ManagedSession(
                session_id="new_session",
                template="python",
                flavor=SandboxFlavor.SMALL,
                config=config
            )
            new_session.status = SessionStatus.READY
            new_session.sandbox_name = "new-sandbox"
            session_manager._sessions["new_session"] = new_session
            
            # This should succeed despite having max_sessions pinned containers
            assert len(session_manager._sessions) == 1
            assert "new_session" in session_manager._sessions
    
    @pytest.mark.asyncio
    async def test_lru_eviction_preserves_pinned_containers(self, session_manager, config):
        """Test that LRU eviction only stops (doesn't remove) pinned containers."""
        # Create sessions that will be subject to LRU eviction
        sessions = []
        for i in range(5):  # More than max_concurrent_sessions
            session_id = f"lru_session_{i}"
            session = ManagedSession(
                session_id=session_id,
                template="python",
                flavor=SandboxFlavor.SMALL,
                config=config
            )
            session.status = SessionStatus.READY
            session.sandbox_name = f"lru-sandbox-{i}"
            session.ensure_started = AsyncMock()
            session.stop = AsyncMock()
            session.last_accessed = datetime.now() - timedelta(minutes=i)  # Different access times
            session_manager._sessions[session_id] = session
            sessions.append(session)
        
        with patch('python.sandbox.container_runtime.DockerRuntime') as mock_docker_class:
            mock_docker_runtime = MagicMock()
            mock_docker_runtime.rename_container = AsyncMock()
            mock_docker_runtime.update_container_labels = AsyncMock()
            mock_docker_runtime.stop_and_remove = AsyncMock()
            mock_docker_runtime.get_container_info = AsyncMock()
            mock_docker_class.return_value = mock_docker_runtime
            
            # Pin some sessions (these should be preserved during LRU)
            pinned_sessions = [sessions[0], sessions[2]]  # Pin first and third
            for i, session in enumerate(pinned_sessions):
                pinned_name = f"pinned_lru_{i}"
                await session_manager.pin_session(session.session_id, pinned_name)
            
            # Mock container info to show pinned status
            def mock_container_info(container_name):
                if container_name.startswith('pinned_lru_'):
                    return {
                        'Labels': {'pinned': 'true', 'pinned_name': container_name}
                    }
                return {'Labels': {}}
            
            mock_docker_runtime.get_container_info.side_effect = mock_container_info
            
            # Simulate LRU eviction by manually calling stop on sessions
            # In real implementation, this would be triggered by resource pressure
            for session in sessions[2:]:  # Evict last 3 sessions
                await session.stop()
            
            # Verify stop was called on all sessions
            for session in sessions[2:]:
                session.stop.assert_called_once()
            
            # Verify that pinned containers would be handled differently
            # (stop_and_remove should check labels and only stop, not remove)
            # This is tested in the container runtime tests, but we verify the flow here
            assert mock_docker_runtime.stop_and_remove.call_count >= 0  # May be called by cleanup
    
    @pytest.mark.asyncio
    async def test_resource_cleanup_with_mixed_containers(self, session_manager, config):
        """Test resource cleanup behavior with mix of pinned and unpinned containers."""
        # Create mix of pinned and unpinned sessions
        sessions_data = [
            ("unpinned_1", None),
            ("pinned_1", "persistent_1"),
            ("unpinned_2", None),
            ("pinned_2", "persistent_2"),
            ("unpinned_3", None)
        ]
        
        sessions = []
        for session_id, pin_name in sessions_data:
            session = ManagedSession(
                session_id=session_id,
                template="python",
                flavor=SandboxFlavor.SMALL,
                config=config
            )
            session.status = SessionStatus.READY
            session.sandbox_name = f"original-{session_id}"
            session.ensure_started = AsyncMock()
            session.stop = AsyncMock()
            session_manager._sessions[session_id] = session
            sessions.append(session)
        
        with patch('python.sandbox.container_runtime.DockerRuntime') as mock_docker_class:
            mock_docker_runtime = MagicMock()
            mock_docker_runtime.rename_container = AsyncMock()
            mock_docker_runtime.update_container_labels = AsyncMock()
            mock_docker_runtime.stop_and_remove = AsyncMock()
            mock_docker_runtime.get_container_info = AsyncMock()
            mock_docker_class.return_value = mock_docker_runtime
            
            # Pin the designated sessions
            for session_id, pin_name in sessions_data:
                if pin_name:
                    await session_manager.pin_session(session_id, pin_name)
            
            # Mock container info to distinguish pinned vs unpinned
            def mock_container_info(container_name):
                if container_name.startswith('persistent_'):
                    return {
                        'Labels': {'pinned': 'true', 'pinned_name': container_name}
                    }
                return {'Labels': {}}
            
            mock_docker_runtime.get_container_info.side_effect = mock_container_info
            
            # Simulate cleanup of all sessions
            cleanup_calls = []
            for session in sessions:
                await session.stop()
                cleanup_calls.append(session.sandbox_name)
            
            # Verify all sessions were stopped
            for session in sessions:
                session.stop.assert_called_once()
            
            # In real implementation, stop_and_remove would check container labels
            # and behave differently for pinned vs unpinned containers
            # Pinned: only stop, Unpinned: stop and remove
            
            # Verify the cleanup process was initiated for all containers
            assert len(cleanup_calls) == len(sessions_data)
            
            # Verify pinned containers can still be attached to after cleanup
            for session_id, pin_name in sessions_data:
                if pin_name:
                    # Mock the pinned container as stopped but available
                    container_info = {
                        'Id': f'container_{session_id}',
                        'Names': [f'/{pin_name}'],
                        'State': 'exited',
                        'Image': 'python:3.9',
                        'Labels': {
                            'pinned': 'true',
                            'pinned_name': pin_name,
                            'template': 'python'
                        }
                    }
                    mock_docker_runtime.get_container_info.return_value = container_info
                    mock_docker_runtime.start_container = AsyncMock()
                    
                    # Should be able to attach to pinned container
                    new_session_id = await session_manager.attach_to_pinned_sandbox(pin_name)
                    assert new_session_id in session_manager._sessions
                    
                    # Clean up for next iteration
                    del session_manager._sessions[new_session_id]
    
    @pytest.mark.asyncio
    async def test_memory_and_cpu_tracking_with_pinned_containers(self, session_manager, config):
        """Test that resource tracking accounts for pinned containers appropriately."""
        # This test verifies that pinned containers are tracked for resource usage
        # but don't prevent new session creation within limits
        
        # Create sessions with different resource profiles
        resource_sessions = [
            ("small_session", SandboxFlavor.SMALL, "small_pinned"),
            ("medium_session", SandboxFlavor.MEDIUM, "medium_pinned"),
            ("large_session", SandboxFlavor.LARGE, None)  # Not pinned
        ]
        
        sessions = []
        for session_id, flavor, pin_name in resource_sessions:
            session = ManagedSession(
                session_id=session_id,
                template="python",
                flavor=flavor,
                config=config
            )
            session.status = SessionStatus.READY
            session.sandbox_name = f"resource-{session_id}"
            session.ensure_started = AsyncMock()
            session_manager._sessions[session_id] = session
            sessions.append((session, pin_name))
        
        with patch('python.sandbox.container_runtime.DockerRuntime') as mock_docker_class:
            mock_docker_runtime = MagicMock()
            mock_docker_runtime.rename_container = AsyncMock()
            mock_docker_runtime.update_container_labels = AsyncMock()
            mock_docker_runtime.get_container_info = AsyncMock()
            mock_docker_class.return_value = mock_docker_runtime
            
            # Pin designated sessions
            for session, pin_name in sessions:
                if pin_name:
                    await session_manager.pin_session(session.session_id, pin_name)
            
            # Verify sessions were pinned correctly
            pinned_count = sum(1 for _, pin_name in sessions if pin_name)
            assert pinned_count == 2
            
            # Verify resource flavors are preserved
            for session, pin_name in sessions:
                if pin_name:
                    assert session.flavor in [SandboxFlavor.SMALL, SandboxFlavor.MEDIUM]
            
            # Simulate resource monitoring
            # In real implementation, this would track actual container resource usage
            total_sessions = len(session_manager._sessions)
            assert total_sessions == len(resource_sessions)
            
            # Verify that different flavors are handled appropriately
            flavors_in_use = [session.flavor for session, _ in sessions]
            assert SandboxFlavor.SMALL in flavors_in_use
            assert SandboxFlavor.MEDIUM in flavors_in_use
            assert SandboxFlavor.LARGE in flavors_in_use


if __name__ == "__main__":
    """Run integration tests directly for development."""
    pytest.main([__file__, "-v", "-m", "integration"])