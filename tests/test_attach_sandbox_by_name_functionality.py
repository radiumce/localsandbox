"""
Unit tests for attach_sandbox_by_name functionality in SessionManager.

These tests verify the attach_sandbox_by_name method including:
- Test attachment to running pinned containers
- Test attachment to stopped pinned containers (with container start)
- Test error cases (non-existent pinned sandbox)
- Test session creation and association
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
    PinnedSandboxNotFoundError,
    ContainerStartError,
    SessionCreationError
)


class TestAttachSandboxByNameFunctionality:
    """Test attach_sandbox_by_name functionality in SessionManager."""
    
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
        """Create a mock DockerRuntime for testing."""
        mock_runtime = MagicMock()
        mock_runtime.get_container_info = AsyncMock()
        mock_runtime.get_containers_by_label = AsyncMock()
        mock_runtime.start_container = AsyncMock()
        return mock_runtime
    
    @pytest.fixture
    def running_container_info(self):
        """Create mock container info for a running container."""
        return {
            'Id': 'container123456789abcdef',
            'Names': ['/my_pinned_sandbox'],
            'State': 'running',
            'Image': 'python:3.9',
            'Labels': {
                'pinned': 'true',
                'pinned_name': 'my_pinned_sandbox',
                'template': 'python'
            }
        }
    
    @pytest.fixture
    def stopped_container_info(self):
        """Create mock container info for a stopped container."""
        return {
            'Id': 'container987654321fedcba',
            'Names': ['/my_stopped_sandbox'],
            'State': 'exited',
            'Image': 'python:3.9',
            'Labels': {
                'pinned': 'true',
                'pinned_name': 'my_stopped_sandbox',
                'template': 'python'
            }
        }


class TestAttachToRunningContainers:
    """Test attachment to running pinned containers."""
    
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
    def running_container_info(self):
        """Create mock container info for a running container."""
        return {
            'Id': 'container123456789abcdef',
            'Names': ['/my_running_sandbox'],
            'State': 'running',
            'Image': 'python:3.9',
            'Labels': {
                'pinned': 'true',
                'pinned_name': 'my_running_sandbox',
                'template': 'python'
            }
        }
    
    @pytest.mark.asyncio
    async def test_attach_to_running_container_by_name(self, session_manager, running_container_info):
        """Test successful attachment to a running container found by name."""
        pinned_name = "my_running_sandbox"
        
        with patch('python.sandbox.container_runtime.DockerRuntime') as mock_docker_class:
            mock_docker_runtime = MagicMock()
            mock_docker_runtime.get_container_info = AsyncMock(return_value=running_container_info)
            mock_docker_runtime.start_container = AsyncMock()
            mock_docker_class.return_value = mock_docker_runtime
            
            session_id = await session_manager.attach_to_pinned_sandbox(pinned_name)
            
            # Verify session ID was returned
            assert session_id is not None
            assert isinstance(session_id, str)
            assert len(session_id) > 0
            
            # Verify container info was retrieved by name
            mock_docker_runtime.get_container_info.assert_called_once_with(pinned_name)
            
            # Verify container was not started (already running)
            mock_docker_runtime.start_container.assert_not_called()
            
            # Verify session was created and registered
            assert session_id in session_manager._sessions
            session = session_manager._sessions[session_id]
            assert session.sandbox_name == "my_running_sandbox"
            assert session.status == SessionStatus.READY
            assert session.template == "python"
    
    @pytest.mark.asyncio
    async def test_attach_to_running_container_by_label(self, session_manager, running_container_info):
        """Test successful attachment to a running container found by label."""
        pinned_name = "my_running_sandbox"
        
        with patch('python.sandbox.container_runtime.DockerRuntime') as mock_docker_class:
            mock_docker_runtime = MagicMock()
            # First call (by name) fails, second call (by label) succeeds
            mock_docker_runtime.get_container_info = AsyncMock(side_effect=Exception("Container not found"))
            mock_docker_runtime.get_containers_by_label = AsyncMock(return_value=[running_container_info])
            mock_docker_runtime.start_container = AsyncMock()
            mock_docker_class.return_value = mock_docker_runtime
            
            session_id = await session_manager.attach_to_pinned_sandbox(pinned_name)
            
            # Verify session ID was returned
            assert session_id is not None
            assert isinstance(session_id, str)
            
            # Verify container info was first attempted by name, then by label
            mock_docker_runtime.get_container_info.assert_called_once_with(pinned_name)
            mock_docker_runtime.get_containers_by_label.assert_called_once_with({"pinned_name": pinned_name})
            
            # Verify container was not started (already running)
            mock_docker_runtime.start_container.assert_not_called()
            
            # Verify session was created
            assert session_id in session_manager._sessions
            session = session_manager._sessions[session_id]
            assert session.sandbox_name == "my_running_sandbox"
    
    @pytest.mark.asyncio
    async def test_attach_to_existing_active_session(self, session_manager, running_container_info):
        """Test attachment to container that already has an active session."""
        pinned_name = "my_running_sandbox"
        container_name = "my_running_sandbox"
        
        # Create an existing active session for the container
        existing_session_id = "existing_session_123"
        existing_session = ManagedSession(
            session_id=existing_session_id,
            template="python",
            flavor=SandboxFlavor.SMALL,
            config=session_manager._config
        )
        existing_session.sandbox_name = container_name
        existing_session.status = SessionStatus.READY
        existing_session.last_accessed = datetime.now()
        existing_session.touch = MagicMock()
        session_manager._sessions[existing_session_id] = existing_session
        
        with patch('python.sandbox.container_runtime.DockerRuntime') as mock_docker_class:
            mock_docker_runtime = MagicMock()
            mock_docker_runtime.get_container_info = AsyncMock(return_value=running_container_info)
            mock_docker_class.return_value = mock_docker_runtime
            
            session_id = await session_manager.attach_to_pinned_sandbox(pinned_name)
            
            # Verify existing session ID was returned
            assert session_id == existing_session_id
            
            # Verify existing session was touched
            existing_session.touch.assert_called_once()
            
            # Verify no new session was created
            assert len(session_manager._sessions) == 1
    
    @pytest.mark.asyncio
    async def test_attach_determines_template_from_labels(self, session_manager):
        """Test that template is correctly determined from container labels."""
        pinned_name = "node_sandbox"
        container_info = {
            'Id': 'container123456789abcdef',
            'Names': ['/node_sandbox'],
            'State': 'running',
            'Image': 'node:16',
            'Labels': {
                'pinned': 'true',
                'pinned_name': 'node_sandbox',
                'template': 'node'
            }
        }
        
        with patch('python.sandbox.container_runtime.DockerRuntime') as mock_docker_class:
            mock_docker_runtime = MagicMock()
            mock_docker_runtime.get_container_info = AsyncMock(return_value=container_info)
            mock_docker_class.return_value = mock_docker_runtime
            
            session_id = await session_manager.attach_to_pinned_sandbox(pinned_name)
            
            # Verify session was created with correct template
            session = session_manager._sessions[session_id]
            assert session.template == "node"
    
    @pytest.mark.asyncio
    async def test_attach_infers_template_from_image(self, session_manager):
        """Test that template is inferred from image name when labels are missing."""
        pinned_name = "node_sandbox"
        container_info = {
            'Id': 'container123456789abcdef',
            'Names': ['/node_sandbox'],
            'State': 'running',
            'Image': 'node:16-alpine',
            'Labels': {
                'pinned': 'true',
                'pinned_name': 'node_sandbox'
                # No template label
            }
        }
        
        with patch('python.sandbox.container_runtime.DockerRuntime') as mock_docker_class:
            mock_docker_runtime = MagicMock()
            mock_docker_runtime.get_container_info = AsyncMock(return_value=container_info)
            mock_docker_class.return_value = mock_docker_runtime
            
            session_id = await session_manager.attach_to_pinned_sandbox(pinned_name)
            
            # Verify session was created with inferred template
            session = session_manager._sessions[session_id]
            assert session.template == "node"


class TestAttachToStoppedContainers:
    """Test attachment to stopped pinned containers (with container start)."""
    
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
    def stopped_container_info(self):
        """Create mock container info for a stopped container."""
        return {
            'Id': 'container987654321fedcba',
            'Names': ['/my_stopped_sandbox'],
            'State': 'exited',
            'Image': 'python:3.9',
            'Labels': {
                'pinned': 'true',
                'pinned_name': 'my_stopped_sandbox',
                'template': 'python'
            }
        }
    
    @pytest.mark.asyncio
    async def test_attach_to_stopped_container_starts_it(self, session_manager, stopped_container_info):
        """Test that stopped containers are started during attachment."""
        pinned_name = "my_stopped_sandbox"
        container_id = stopped_container_info['Id']
        
        with patch('python.sandbox.container_runtime.DockerRuntime') as mock_docker_class:
            mock_docker_runtime = MagicMock()
            mock_docker_runtime.get_container_info = AsyncMock(return_value=stopped_container_info)
            mock_docker_runtime.start_container = AsyncMock()
            mock_docker_class.return_value = mock_docker_runtime
            
            session_id = await session_manager.attach_to_pinned_sandbox(pinned_name)
            
            # Verify session ID was returned
            assert session_id is not None
            assert isinstance(session_id, str)
            
            # Verify container was started
            mock_docker_runtime.start_container.assert_called_once_with(container_id)
            
            # Verify session was created
            assert session_id in session_manager._sessions
            session = session_manager._sessions[session_id]
            assert session.sandbox_name == "my_stopped_sandbox"
            assert session.status == SessionStatus.READY
    
    @pytest.mark.asyncio
    async def test_attach_to_stopped_container_various_states(self, session_manager):
        """Test attachment to containers in various stopped states."""
        test_cases = [
            ("exited", "my_exited_sandbox"),
            ("stopped", "my_stopped_sandbox"),
            ("created", "my_created_sandbox")
        ]
        
        for state, container_name in test_cases:
            container_info = {
                'Id': f'container_{state}_123',
                'Names': [f'/{container_name}'],
                'State': state,
                'Image': 'python:3.9',
                'Labels': {
                    'pinned': 'true',
                    'pinned_name': container_name,
                    'template': 'python'
                }
            }
            
            with patch('python.sandbox.container_runtime.DockerRuntime') as mock_docker_class:
                mock_docker_runtime = MagicMock()
                mock_docker_runtime.get_container_info = AsyncMock(return_value=container_info)
                mock_docker_runtime.start_container = AsyncMock()
                mock_docker_class.return_value = mock_docker_runtime
                
                session_id = await session_manager.attach_to_pinned_sandbox(container_name)
                
                # Verify container was started (since state is not 'running')
                mock_docker_runtime.start_container.assert_called_once_with(container_info['Id'])
                
                # Verify session was created
                assert session_id in session_manager._sessions
                session = session_manager._sessions[session_id]
                assert session.sandbox_name == container_name
                
                # Clean up for next iteration
                del session_manager._sessions[session_id]
    
    @pytest.mark.asyncio
    async def test_attach_container_start_failure(self, session_manager, stopped_container_info):
        """Test handling of container start failure."""
        pinned_name = "my_stopped_sandbox"
        container_id = stopped_container_info['Id']
        
        with patch('python.sandbox.container_runtime.DockerRuntime') as mock_docker_class:
            mock_docker_runtime = MagicMock()
            mock_docker_runtime.get_container_info = AsyncMock(return_value=stopped_container_info)
            mock_docker_runtime.start_container = AsyncMock(
                side_effect=Exception("Failed to start container: resource constraints")
            )
            mock_docker_class.return_value = mock_docker_runtime
            
            with pytest.raises(ContainerStartError) as exc_info:
                await session_manager.attach_to_pinned_sandbox(pinned_name)
            
            # Verify error details
            assert pinned_name in str(exc_info.value)
            assert "Failed to start pinned container" in str(exc_info.value)
            assert "resource constraints" in str(exc_info.value)
            
            # Verify start was attempted
            mock_docker_runtime.start_container.assert_called_once_with(container_id)
            
            # Verify no session was created
            assert len(session_manager._sessions) == 0


class TestAttachErrorCases:
    """Test error cases for attach_sandbox_by_name functionality."""
    
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
    async def test_attach_nonexistent_pinned_sandbox(self, session_manager):
        """Test attachment to non-existent pinned sandbox."""
        pinned_name = "nonexistent_sandbox"
        
        with patch('python.sandbox.container_runtime.DockerRuntime') as mock_docker_class:
            mock_docker_runtime = MagicMock()
            # Both name and label searches fail
            mock_docker_runtime.get_container_info = AsyncMock(side_effect=Exception("Container not found"))
            mock_docker_runtime.get_containers_by_label = AsyncMock(return_value=[])
            mock_docker_class.return_value = mock_docker_runtime
            
            with pytest.raises(PinnedSandboxNotFoundError) as exc_info:
                await session_manager.attach_to_pinned_sandbox(pinned_name)
            
            # Verify error details
            assert pinned_name in str(exc_info.value)
            assert "No pinned sandbox found" in str(exc_info.value)
            
            # Verify both search methods were attempted
            mock_docker_runtime.get_container_info.assert_called_once_with(pinned_name)
            mock_docker_runtime.get_containers_by_label.assert_called_once_with({"pinned_name": pinned_name})
    
    @pytest.mark.asyncio
    async def test_attach_empty_label_search_results(self, session_manager):
        """Test attachment when label search returns empty results."""
        pinned_name = "missing_sandbox"
        
        with patch('python.sandbox.container_runtime.DockerRuntime') as mock_docker_class:
            mock_docker_runtime = MagicMock()
            mock_docker_runtime.get_container_info = AsyncMock(side_effect=Exception("Not found"))
            mock_docker_runtime.get_containers_by_label = AsyncMock(return_value=[])
            mock_docker_class.return_value = mock_docker_runtime
            
            with pytest.raises(PinnedSandboxNotFoundError) as exc_info:
                await session_manager.attach_to_pinned_sandbox(pinned_name)
            
            assert "No pinned sandbox found" in str(exc_info.value)
            assert pinned_name in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_attach_session_creation_failure(self, session_manager):
        """Test handling of session creation failure during attachment."""
        pinned_name = "test_sandbox"
        container_info = {
            'Id': 'container123456789abcdef',
            'Names': ['/test_sandbox'],
            'State': 'running',
            'Image': 'python:3.9',
            'Labels': {
                'pinned': 'true',
                'pinned_name': 'test_sandbox',
                'template': 'python'
            }
        }
        
        with patch('python.sandbox.container_runtime.DockerRuntime') as mock_docker_class:
            mock_docker_runtime = MagicMock()
            mock_docker_runtime.get_container_info = AsyncMock(return_value=container_info)
            mock_docker_class.return_value = mock_docker_runtime
            
            # Mock ManagedSession constructor to fail
            with patch('microsandbox_wrapper.session_manager.ManagedSession') as mock_session_class:
                mock_session_class.side_effect = Exception("Session creation failed")
                
                with pytest.raises(SessionCreationError) as exc_info:
                    await session_manager.attach_to_pinned_sandbox(pinned_name)
                
                # Verify error details
                assert pinned_name in str(exc_info.value)
                assert "Failed to create session" in str(exc_info.value)
                assert "Session creation failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_attach_unexpected_error_handling(self, session_manager):
        """Test handling of unexpected errors during attachment."""
        pinned_name = "test_sandbox"
        
        with patch('python.sandbox.container_runtime.DockerRuntime') as mock_docker_class:
            mock_docker_runtime = MagicMock()
            mock_docker_runtime.get_container_info = AsyncMock(
                side_effect=RuntimeError("Unexpected Docker error")
            )
            mock_docker_runtime.get_containers_by_label = AsyncMock(
                side_effect=RuntimeError("Unexpected Docker error")
            )
            mock_docker_class.return_value = mock_docker_runtime
            
            with pytest.raises(SessionCreationError) as exc_info:
                await session_manager.attach_to_pinned_sandbox(pinned_name)
            
            # Verify error details
            assert "Unexpected error while attaching" in str(exc_info.value)
            assert pinned_name in str(exc_info.value)
            assert "Unexpected Docker error" in str(exc_info.value)


class TestSessionCreationAndAssociation:
    """Test session creation and association during attachment."""
    
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
    def container_info(self):
        """Create mock container info."""
        return {
            'Id': 'container123456789abcdef',
            'Names': ['/test_sandbox'],
            'State': 'running',
            'Image': 'python:3.9',
            'Labels': {
                'pinned': 'true',
                'pinned_name': 'test_sandbox',
                'template': 'python'
            }
        }
    
    @pytest.mark.asyncio
    async def test_session_creation_with_correct_attributes(self, session_manager, container_info):
        """Test that session is created with correct attributes."""
        pinned_name = "test_sandbox"
        
        with patch('python.sandbox.container_runtime.DockerRuntime') as mock_docker_class:
            mock_docker_runtime = MagicMock()
            mock_docker_runtime.get_container_info = AsyncMock(return_value=container_info)
            mock_docker_class.return_value = mock_docker_runtime
            
            session_id = await session_manager.attach_to_pinned_sandbox(pinned_name)
            
            # Verify session was created and registered
            assert session_id in session_manager._sessions
            session = session_manager._sessions[session_id]
            
            # Verify session attributes
            assert session.session_id == session_id
            assert session.sandbox_name == "test_sandbox"
            assert session.template == "python"
            assert session.status == SessionStatus.READY
            assert session.flavor == SandboxFlavor.SMALL  # Default flavor
    
    @pytest.mark.asyncio
    async def test_session_id_generation(self, session_manager, container_info):
        """Test that unique session IDs are generated."""
        pinned_name = "test_sandbox"
        
        with patch('python.sandbox.container_runtime.DockerRuntime') as mock_docker_class:
            mock_docker_runtime = MagicMock()
            mock_docker_runtime.get_container_info = AsyncMock(return_value=container_info)
            mock_docker_class.return_value = mock_docker_runtime
            
            # Create multiple sessions
            session_ids = []
            for i in range(3):
                session_id = await session_manager.attach_to_pinned_sandbox(pinned_name)
                session_ids.append(session_id)
                
                # Clean up session for next iteration
                del session_manager._sessions[session_id]
            
            # Verify all session IDs are unique
            assert len(set(session_ids)) == len(session_ids)
            
            # Verify session IDs are valid UUIDs
            for session_id in session_ids:
                uuid.UUID(session_id)  # Will raise ValueError if invalid
    
    @pytest.mark.asyncio
    async def test_session_association_with_container(self, session_manager, container_info):
        """Test that session is properly associated with the container."""
        pinned_name = "test_sandbox"
        container_name = "test_sandbox"
        
        with patch('python.sandbox.container_runtime.DockerRuntime') as mock_docker_class:
            mock_docker_runtime = MagicMock()
            mock_docker_runtime.get_container_info = AsyncMock(return_value=container_info)
            mock_docker_class.return_value = mock_docker_runtime
            
            session_id = await session_manager.attach_to_pinned_sandbox(pinned_name)
            
            # Verify session is associated with correct container
            session = session_manager._sessions[session_id]
            assert session.sandbox_name == container_name
            
            # Verify session can be retrieved by session_id
            retrieved_sessions = await session_manager.get_sessions(session_id)
            assert len(retrieved_sessions) == 1
            assert retrieved_sessions[0].session_id == session_id
            assert retrieved_sessions[0].sandbox_name == container_name
    
    @pytest.mark.asyncio
    async def test_multiple_sessions_for_different_containers(self, session_manager):
        """Test creating sessions for multiple different pinned containers."""
        containers = [
            {
                'name': 'sandbox_1',
                'info': {
                    'Id': 'container1',
                    'Names': ['/sandbox_1'],
                    'State': 'running',
                    'Image': 'python:3.9',
                    'Labels': {'pinned': 'true', 'pinned_name': 'sandbox_1', 'template': 'python'}
                }
            },
            {
                'name': 'sandbox_2',
                'info': {
                    'Id': 'container2',
                    'Names': ['/sandbox_2'],
                    'State': 'running',
                    'Image': 'node:16',
                    'Labels': {'pinned': 'true', 'pinned_name': 'sandbox_2', 'template': 'node'}
                }
            }
        ]
        
        session_ids = []
        
        for container in containers:
            with patch('python.sandbox.container_runtime.DockerRuntime') as mock_docker_class:
                mock_docker_runtime = MagicMock()
                mock_docker_runtime.get_container_info = AsyncMock(return_value=container['info'])
                mock_docker_class.return_value = mock_docker_runtime
                
                session_id = await session_manager.attach_to_pinned_sandbox(container['name'])
                session_ids.append(session_id)
        
        # Verify all sessions were created
        assert len(session_manager._sessions) == len(containers)
        
        # Verify each session has correct attributes
        for i, container in enumerate(containers):
            session = session_manager._sessions[session_ids[i]]
            assert session.sandbox_name == container['name']
            expected_template = container['info']['Labels']['template']
            assert session.template == expected_template
    
    @pytest.mark.asyncio
    async def test_session_registration_in_manager(self, session_manager, container_info):
        """Test that session is properly registered in the session manager."""
        pinned_name = "test_sandbox"
        
        # Verify no sessions initially
        assert len(session_manager._sessions) == 0
        
        with patch('python.sandbox.container_runtime.DockerRuntime') as mock_docker_class:
            mock_docker_runtime = MagicMock()
            mock_docker_runtime.get_container_info = AsyncMock(return_value=container_info)
            mock_docker_class.return_value = mock_docker_runtime
            
            session_id = await session_manager.attach_to_pinned_sandbox(pinned_name)
            
            # Verify session was registered
            assert len(session_manager._sessions) == 1
            assert session_id in session_manager._sessions
            
            # Verify session can be retrieved
            session = session_manager._sessions[session_id]
            assert session is not None
            assert session.session_id == session_id
            
            # Verify session appears in get_sessions()
            all_sessions = await session_manager.get_sessions()
            assert len(all_sessions) == 1
            assert all_sessions[0].session_id == session_id


class TestAttachIntegrationScenarios:
    """Integration tests for attach_sandbox_by_name functionality."""
    
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
    async def test_attach_end_to_end_workflow(self, session_manager):
        """Test complete attach workflow end-to-end."""
        pinned_name = "integration_test_sandbox"
        container_info = {
            'Id': 'container_integration_test',
            'Names': ['/integration_test_sandbox'],
            'State': 'exited',  # Stopped container that needs starting
            'Image': 'python:3.9',
            'Labels': {
                'pinned': 'true',
                'pinned_name': 'integration_test_sandbox',
                'template': 'python'
            }
        }
        
        with patch('python.sandbox.container_runtime.DockerRuntime') as mock_docker_class:
            mock_docker_runtime = MagicMock()
            mock_docker_runtime.get_container_info = AsyncMock(return_value=container_info)
            mock_docker_runtime.start_container = AsyncMock()
            mock_docker_class.return_value = mock_docker_runtime
            
            # Execute the attach operation
            session_id = await session_manager.attach_to_pinned_sandbox(pinned_name)
            
            # Verify complete workflow
            assert session_id is not None
            assert isinstance(session_id, str)
            
            # Verify container operations
            mock_docker_runtime.get_container_info.assert_called_once_with(pinned_name)
            mock_docker_runtime.start_container.assert_called_once_with(container_info['Id'])
            
            # Verify session creation
            assert session_id in session_manager._sessions
            session = session_manager._sessions[session_id]
            assert session.sandbox_name == pinned_name
            assert session.template == "python"
            assert session.status == SessionStatus.READY
            
            # Verify session is accessible through manager methods
            retrieved_sessions = await session_manager.get_sessions(session_id)
            assert len(retrieved_sessions) == 1
            assert retrieved_sessions[0].session_id == session_id
    
    @pytest.mark.asyncio
    async def test_attach_fallback_from_name_to_label_search(self, session_manager):
        """Test fallback from name search to label search."""
        pinned_name = "fallback_test_sandbox"
        container_info = {
            'Id': 'container_fallback_test',
            'Names': ['/different_actual_name'],  # Different from pinned_name
            'State': 'running',
            'Image': 'python:3.9',
            'Labels': {
                'pinned': 'true',
                'pinned_name': 'fallback_test_sandbox',  # Matches pinned_name
                'template': 'python'
            }
        }
        
        with patch('python.sandbox.container_runtime.DockerRuntime') as mock_docker_class:
            mock_docker_runtime = MagicMock()
            # Name search fails, label search succeeds
            mock_docker_runtime.get_container_info = AsyncMock(side_effect=Exception("Not found by name"))
            mock_docker_runtime.get_containers_by_label = AsyncMock(return_value=[container_info])
            mock_docker_class.return_value = mock_docker_runtime
            
            session_id = await session_manager.attach_to_pinned_sandbox(pinned_name)
            
            # Verify both search methods were used
            mock_docker_runtime.get_container_info.assert_called_once_with(pinned_name)
            mock_docker_runtime.get_containers_by_label.assert_called_once_with({"pinned_name": pinned_name})
            
            # Verify session was created with container's actual name
            session = session_manager._sessions[session_id]
            assert session.sandbox_name == "different_actual_name"
    
    @pytest.mark.asyncio
    async def test_attach_multiple_containers_sequentially(self, session_manager):
        """Test attaching to multiple containers sequentially."""
        containers = [
            ("sandbox_a", "python"),
            ("sandbox_b", "node"),
            ("sandbox_c", "python")
        ]
        
        session_ids = []
        
        for pinned_name, template in containers:
            container_info = {
                'Id': f'container_{pinned_name}',
                'Names': [f'/{pinned_name}'],
                'State': 'running',
                'Image': f'{template}:latest',
                'Labels': {
                    'pinned': 'true',
                    'pinned_name': pinned_name,
                    'template': template
                }
            }
            
            with patch('python.sandbox.container_runtime.DockerRuntime') as mock_docker_class:
                mock_docker_runtime = MagicMock()
                mock_docker_runtime.get_container_info = AsyncMock(return_value=container_info)
                mock_docker_class.return_value = mock_docker_runtime
                
                session_id = await session_manager.attach_to_pinned_sandbox(pinned_name)
                session_ids.append(session_id)
        
        # Verify all sessions were created
        assert len(session_manager._sessions) == len(containers)
        assert len(set(session_ids)) == len(containers)  # All unique
        
        # Verify each session has correct attributes
        for i, (pinned_name, template) in enumerate(containers):
            session = session_manager._sessions[session_ids[i]]
            assert session.sandbox_name == pinned_name
            assert session.template == template