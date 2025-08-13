"""
Unit tests for pin_sandbox functionality in SessionManager.

These tests verify the pin_sandbox method including:
- Successful pinning of active sessions
- Error cases (invalid session, container not found)
- Label application and session mapping updates
- Container renaming during pin operation
"""

import asyncio
import json
import pytest
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock

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
    ContainerNotFoundError
)


class TestPinSandboxFunctionality:
    """Test pin_sandbox functionality in SessionManager."""
    
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
    def mock_session(self, config):
        """Create a mock ManagedSession for testing."""
        session = ManagedSession(
            session_id="test_session_123",
            template="python",
            flavor=SandboxFlavor.SMALL,
            config=config
        )
        session.status = SessionStatus.READY
        session.sandbox_name = "sandbox-20240101_120000_123456"
        return session
    
    @pytest.fixture
    def mock_docker_runtime(self):
        """Create a mock DockerRuntime for testing."""
        mock_runtime = MagicMock()
        mock_runtime.rename_container = AsyncMock()
        mock_runtime.update_container_labels = AsyncMock()
        return mock_runtime


class TestSuccessfulPinning:
    """Test successful pinning scenarios."""
    
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
    def mock_session(self, config):
        """Create a mock ManagedSession for testing."""
        session = ManagedSession(
            session_id="test_session_123",
            template="python",
            flavor=SandboxFlavor.SMALL,
            config=config
        )
        session.status = SessionStatus.READY
        session.sandbox_name = "sandbox-20240101_120000_123456"
        session.ensure_started = AsyncMock()
        return session
    
    @pytest.mark.asyncio
    async def test_pin_active_session_success(self, session_manager, mock_session):
        """Test successful pinning of an active session."""
        session_id = "test_session_123"
        pinned_name = "my_dev_environment"
        original_sandbox_name = mock_session.sandbox_name
        
        # Add session to manager
        session_manager._sessions[session_id] = mock_session
        
        with patch('python.sandbox.container_runtime.DockerRuntime') as mock_docker_class:
            mock_docker_runtime = MagicMock()
            mock_docker_runtime.rename_container = AsyncMock()
            mock_docker_runtime.update_container_labels = AsyncMock()
            mock_docker_class.return_value = mock_docker_runtime
            
            result = await session_manager.pin_session(session_id, pinned_name)
            
            # Verify the result
            assert "Successfully pinned session" in result
            assert session_id in result
            assert pinned_name in result
            
            # Verify session.ensure_started was called
            mock_session.ensure_started.assert_called_once()
            
            # Verify container was renamed
            mock_docker_runtime.rename_container.assert_called_once_with(
                original_sandbox_name, pinned_name
            )
            
            # Verify labels were updated
            expected_labels = {
                "pinned": "true",
                "pinned_name": pinned_name
            }
            mock_docker_runtime.update_container_labels.assert_called_once_with(
                pinned_name, expected_labels
            )
            
            # Verify session sandbox_name was updated
            assert mock_session.sandbox_name == pinned_name
    
    @pytest.mark.asyncio
    async def test_pin_session_with_special_characters(self, session_manager, mock_session):
        """Test pinning with special characters in pinned name."""
        session_id = "test_session_123"
        pinned_name = "my-dev_environment.v2"
        
        session_manager._sessions[session_id] = mock_session
        
        with patch('python.sandbox.container_runtime.DockerRuntime') as mock_docker_class:
            mock_docker_runtime = MagicMock()
            mock_docker_runtime.rename_container = AsyncMock()
            mock_docker_runtime.update_container_labels = AsyncMock()
            mock_docker_class.return_value = mock_docker_runtime
            
            result = await session_manager.pin_session(session_id, pinned_name)
            
            assert "Successfully pinned session" in result
            assert mock_session.sandbox_name == pinned_name
    
    @pytest.mark.asyncio
    async def test_pin_session_updates_mapping(self, session_manager, mock_session):
        """Test that pinning updates the session's sandbox name mapping."""
        session_id = "test_session_123"
        pinned_name = "persistent_workspace"
        original_name = mock_session.sandbox_name
        
        session_manager._sessions[session_id] = mock_session
        
        with patch('python.sandbox.container_runtime.DockerRuntime') as mock_docker_class:
            mock_docker_runtime = MagicMock()
            mock_docker_runtime.rename_container = AsyncMock()
            mock_docker_runtime.update_container_labels = AsyncMock()
            mock_docker_class.return_value = mock_docker_runtime
            
            # Verify original name
            assert mock_session.sandbox_name == original_name
            
            await session_manager.pin_session(session_id, pinned_name)
            
            # Verify name was updated
            assert mock_session.sandbox_name == pinned_name
            assert mock_session.sandbox_name != original_name


class TestPinningErrorCases:
    """Test error cases for pin_sandbox functionality."""
    
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
    def mock_session(self, config):
        """Create a mock ManagedSession for testing."""
        session = ManagedSession(
            session_id="test_session_123",
            template="python",
            flavor=SandboxFlavor.SMALL,
            config=config
        )
        session.status = SessionStatus.READY
        session.sandbox_name = "sandbox-20240101_120000_123456"
        session.ensure_started = AsyncMock()
        return session
    
    @pytest.mark.asyncio
    async def test_pin_nonexistent_session(self, session_manager):
        """Test pinning a non-existent session raises SessionNotFoundError."""
        session_id = "nonexistent_session"
        pinned_name = "my_sandbox"
        
        with pytest.raises(SessionNotFoundError) as exc_info:
            await session_manager.pin_session(session_id, pinned_name)
        
        assert session_id in str(exc_info.value)
        assert "not found" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_pin_stopped_session(self, session_manager, mock_session):
        """Test pinning a stopped session raises SessionNotFoundError."""
        session_id = "stopped_session"
        pinned_name = "my_sandbox"
        
        # Set session status to stopped
        mock_session.status = SessionStatus.STOPPED
        session_manager._sessions[session_id] = mock_session
        
        with pytest.raises(SessionNotFoundError) as exc_info:
            await session_manager.pin_session(session_id, pinned_name)
        
        assert "Cannot pin stopped session" in str(exc_info.value)
        assert session_id in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_pin_session_ensure_started_fails(self, session_manager, mock_session):
        """Test pinning when ensure_started fails raises ContainerNotFoundError."""
        session_id = "test_session_123"
        pinned_name = "my_sandbox"
        
        # Mock ensure_started to raise an exception
        mock_session.ensure_started = AsyncMock(side_effect=Exception("Container not accessible"))
        session_manager._sessions[session_id] = mock_session
        
        with pytest.raises(ContainerNotFoundError) as exc_info:
            await session_manager.pin_session(session_id, pinned_name)
        
        assert "Failed to access container" in str(exc_info.value)
        assert session_id in str(exc_info.value)
        assert "Container not accessible" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_pin_session_rename_fails(self, session_manager, mock_session):
        """Test pinning when container rename fails raises RuntimeError."""
        session_id = "test_session_123"
        pinned_name = "my_sandbox"
        
        session_manager._sessions[session_id] = mock_session
        
        with patch('python.sandbox.container_runtime.DockerRuntime') as mock_docker_class:
            mock_docker_runtime = MagicMock()
            mock_docker_runtime.rename_container = AsyncMock(
                side_effect=Exception("Container rename failed")
            )
            mock_docker_class.return_value = mock_docker_runtime
            
            with pytest.raises(RuntimeError) as exc_info:
                await session_manager.pin_session(session_id, pinned_name)
            
            assert "Failed to pin session" in str(exc_info.value)
            assert session_id in str(exc_info.value)
            assert pinned_name in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_pin_session_label_update_fails(self, session_manager, mock_session):
        """Test pinning when label update fails raises RuntimeError."""
        session_id = "test_session_123"
        pinned_name = "my_sandbox"
        
        session_manager._sessions[session_id] = mock_session
        
        with patch('python.sandbox.container_runtime.DockerRuntime') as mock_docker_class:
            mock_docker_runtime = MagicMock()
            mock_docker_runtime.rename_container = AsyncMock()  # Succeeds
            mock_docker_runtime.update_container_labels = AsyncMock(
                side_effect=Exception("Label update failed")
            )
            mock_docker_class.return_value = mock_docker_runtime
            
            with pytest.raises(RuntimeError) as exc_info:
                await session_manager.pin_session(session_id, pinned_name)
            
            assert "Failed to pin session" in str(exc_info.value)
            assert "Label update failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_pin_session_container_not_found_error(self, session_manager, mock_session):
        """Test pinning when container is not found raises ContainerNotFoundError."""
        session_id = "test_session_123"
        pinned_name = "my_sandbox"
        original_sandbox_name = mock_session.sandbox_name
        
        session_manager._sessions[session_id] = mock_session
        
        with patch('python.sandbox.container_runtime.DockerRuntime') as mock_docker_class:
            mock_docker_runtime = MagicMock()
            mock_docker_runtime.rename_container = AsyncMock(
                side_effect=Exception("No such container: " + original_sandbox_name)
            )
            mock_docker_class.return_value = mock_docker_runtime
            
            with pytest.raises(ContainerNotFoundError) as exc_info:
                await session_manager.pin_session(session_id, pinned_name)
            
            assert "Container for session" in str(exc_info.value)
            assert "not found" in str(exc_info.value)
            assert session_id in str(exc_info.value)


class TestLabelApplicationAndMapping:
    """Test label application and session mapping updates during pinning."""
    
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
    def mock_session(self, config):
        """Create a mock ManagedSession for testing."""
        session = ManagedSession(
            session_id="test_session_123",
            template="python",
            flavor=SandboxFlavor.SMALL,
            config=config
        )
        session.status = SessionStatus.READY
        session.sandbox_name = "sandbox-20240101_120000_123456"
        session.ensure_started = AsyncMock()
        return session
    
    @pytest.mark.asyncio
    async def test_correct_labels_applied(self, session_manager, mock_session):
        """Test that correct labels are applied during pinning."""
        session_id = "test_session_123"
        pinned_name = "my_development_env"
        
        session_manager._sessions[session_id] = mock_session
        
        with patch('python.sandbox.container_runtime.DockerRuntime') as mock_docker_class:
            mock_docker_runtime = MagicMock()
            mock_docker_runtime.rename_container = AsyncMock()
            mock_docker_runtime.update_container_labels = AsyncMock()
            mock_docker_class.return_value = mock_docker_runtime
            
            await session_manager.pin_session(session_id, pinned_name)
            
            # Verify the exact labels that were applied
            expected_labels = {
                "pinned": "true",
                "pinned_name": pinned_name
            }
            mock_docker_runtime.update_container_labels.assert_called_once_with(
                pinned_name, expected_labels
            )
    
    @pytest.mark.asyncio
    async def test_session_mapping_updated_correctly(self, session_manager, mock_session):
        """Test that session mapping is updated correctly during pinning."""
        session_id = "test_session_123"
        pinned_name = "persistent_sandbox"
        original_name = mock_session.sandbox_name
        
        session_manager._sessions[session_id] = mock_session
        
        # Verify initial state
        assert mock_session.sandbox_name == original_name
        
        with patch('python.sandbox.container_runtime.DockerRuntime') as mock_docker_class:
            mock_docker_runtime = MagicMock()
            mock_docker_runtime.rename_container = AsyncMock()
            mock_docker_runtime.update_container_labels = AsyncMock()
            mock_docker_class.return_value = mock_docker_runtime
            
            await session_manager.pin_session(session_id, pinned_name)
            
            # Verify session mapping was updated
            assert mock_session.sandbox_name == pinned_name
            assert mock_session.sandbox_name != original_name
            
            # Verify the session is still in the manager with the same session_id
            assert session_id in session_manager._sessions
            assert session_manager._sessions[session_id] is mock_session
    
    @pytest.mark.asyncio
    async def test_partial_failure_doesnt_update_mapping(self, session_manager, mock_session):
        """Test that session mapping is not updated if container operations fail."""
        session_id = "test_session_123"
        pinned_name = "my_sandbox"
        original_name = mock_session.sandbox_name
        
        session_manager._sessions[session_id] = mock_session
        
        with patch('python.sandbox.container_runtime.DockerRuntime') as mock_docker_class:
            mock_docker_runtime = MagicMock()
            mock_docker_runtime.rename_container = AsyncMock()  # Succeeds
            mock_docker_runtime.update_container_labels = AsyncMock(
                side_effect=Exception("Label update failed")
            )
            mock_docker_class.return_value = mock_docker_runtime
            
            with pytest.raises(RuntimeError):
                await session_manager.pin_session(session_id, pinned_name)
            
            # Verify session mapping was NOT updated due to failure
            assert mock_session.sandbox_name == original_name
            assert mock_session.sandbox_name != pinned_name


class TestContainerRenaming:
    """Test container renaming during pin operation."""
    
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
    def mock_session(self, config):
        """Create a mock ManagedSession for testing."""
        session = ManagedSession(
            session_id="test_session_123",
            template="python",
            flavor=SandboxFlavor.SMALL,
            config=config
        )
        session.status = SessionStatus.READY
        session.sandbox_name = "sandbox-20240101_120000_123456"
        session.ensure_started = AsyncMock()
        return session
    
    @pytest.mark.asyncio
    async def test_container_renamed_with_correct_names(self, session_manager, mock_session):
        """Test that container is renamed with correct old and new names."""
        session_id = "test_session_123"
        pinned_name = "my_renamed_container"
        original_name = mock_session.sandbox_name
        
        session_manager._sessions[session_id] = mock_session
        
        with patch('python.sandbox.container_runtime.DockerRuntime') as mock_docker_class:
            mock_docker_runtime = MagicMock()
            mock_docker_runtime.rename_container = AsyncMock()
            mock_docker_runtime.update_container_labels = AsyncMock()
            mock_docker_class.return_value = mock_docker_runtime
            
            await session_manager.pin_session(session_id, pinned_name)
            
            # Verify rename was called with correct parameters
            mock_docker_runtime.rename_container.assert_called_once_with(
                original_name, pinned_name
            )
    
    @pytest.mark.asyncio
    async def test_rename_operation_order(self, session_manager, mock_session):
        """Test that rename happens before label update."""
        session_id = "test_session_123"
        pinned_name = "ordered_operations_test"
        
        session_manager._sessions[session_id] = mock_session
        
        call_order = []
        
        async def track_rename(*args, **kwargs):
            call_order.append("rename")
        
        async def track_labels(*args, **kwargs):
            call_order.append("labels")
        
        with patch('python.sandbox.container_runtime.DockerRuntime') as mock_docker_class:
            mock_docker_runtime = MagicMock()
            mock_docker_runtime.rename_container = AsyncMock(side_effect=track_rename)
            mock_docker_runtime.update_container_labels = AsyncMock(side_effect=track_labels)
            mock_docker_class.return_value = mock_docker_runtime
            
            await session_manager.pin_session(session_id, pinned_name)
            
            # Verify operation order
            assert call_order == ["rename", "labels"]
    
    @pytest.mark.asyncio
    async def test_rename_failure_prevents_label_update(self, session_manager, mock_session):
        """Test that label update is not called if rename fails."""
        session_id = "test_session_123"
        pinned_name = "failing_rename"
        
        session_manager._sessions[session_id] = mock_session
        
        with patch('python.sandbox.container_runtime.DockerRuntime') as mock_docker_class:
            mock_docker_runtime = MagicMock()
            mock_docker_runtime.rename_container = AsyncMock(
                side_effect=Exception("Rename failed")
            )
            mock_docker_runtime.update_container_labels = AsyncMock()
            mock_docker_class.return_value = mock_docker_runtime
            
            with pytest.raises(RuntimeError):
                await session_manager.pin_session(session_id, pinned_name)
            
            # Verify rename was attempted
            mock_docker_runtime.rename_container.assert_called_once()
            
            # Verify label update was NOT called due to rename failure
            mock_docker_runtime.update_container_labels.assert_not_called()


class TestPinSessionIntegration:
    """Integration tests for pin_sandbox functionality."""
    
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
    async def test_pin_session_end_to_end(self, session_manager, config):
        """Test complete pin_session workflow end-to-end."""
        session_id = "integration_test_session"
        pinned_name = "integration_test_sandbox"
        template = "python"
        flavor = SandboxFlavor.SMALL
        
        # Create a real session (but mock the underlying sandbox)
        session = ManagedSession(
            session_id=session_id,
            template=template,
            flavor=flavor,
            config=config
        )
        session.status = SessionStatus.READY
        session.sandbox_name = "sandbox-integration-test"
        session.ensure_started = AsyncMock()
        
        # Add session to manager
        session_manager._sessions[session_id] = session
        
        original_name = session.sandbox_name
        
        with patch('python.sandbox.container_runtime.DockerRuntime') as mock_docker_class:
            mock_docker_runtime = MagicMock()
            mock_docker_runtime.rename_container = AsyncMock()
            mock_docker_runtime.update_container_labels = AsyncMock()
            mock_docker_class.return_value = mock_docker_runtime
            
            # Execute the pin operation
            result = await session_manager.pin_session(session_id, pinned_name)
            
            # Verify all aspects of the operation
            assert "Successfully pinned session" in result
            assert session_id in result
            assert pinned_name in result
            
            # Verify session state changes
            assert session.sandbox_name == pinned_name
            assert session.sandbox_name != original_name
            
            # Verify container operations were called
            mock_docker_runtime.rename_container.assert_called_once_with(
                original_name, pinned_name
            )
            
            expected_labels = {
                "pinned": "true",
                "pinned_name": pinned_name
            }
            mock_docker_runtime.update_container_labels.assert_called_once_with(
                pinned_name, expected_labels
            )
            
            # Verify session is still accessible in manager
            retrieved_session = session_manager._sessions[session_id]
            assert retrieved_session is session
            assert retrieved_session.sandbox_name == pinned_name
    
    @pytest.mark.asyncio
    async def test_multiple_pin_operations(self, session_manager, config):
        """Test multiple pin operations on different sessions."""
        sessions_data = [
            ("session_1", "pinned_sandbox_1"),
            ("session_2", "pinned_sandbox_2"),
            ("session_3", "pinned_sandbox_3")
        ]
        
        # Create multiple sessions
        for session_id, _ in sessions_data:
            session = ManagedSession(
                session_id=session_id,
                template="python",
                flavor=SandboxFlavor.SMALL,
                config=config
            )
            session.status = SessionStatus.READY
            session.sandbox_name = f"original_{session_id}"
            session.ensure_started = AsyncMock()
            session_manager._sessions[session_id] = session
        
        with patch('python.sandbox.container_runtime.DockerRuntime') as mock_docker_class:
            mock_docker_runtime = MagicMock()
            mock_docker_runtime.rename_container = AsyncMock()
            mock_docker_runtime.update_container_labels = AsyncMock()
            mock_docker_class.return_value = mock_docker_runtime
            
            # Pin all sessions
            for session_id, pinned_name in sessions_data:
                result = await session_manager.pin_session(session_id, pinned_name)
                assert "Successfully pinned session" in result
                
                # Verify session was updated
                session = session_manager._sessions[session_id]
                assert session.sandbox_name == pinned_name
            
            # Verify all rename operations were called
            assert mock_docker_runtime.rename_container.call_count == len(sessions_data)
            
            # Verify all label operations were called
            assert mock_docker_runtime.update_container_labels.call_count == len(sessions_data)