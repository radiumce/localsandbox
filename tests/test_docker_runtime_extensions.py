"""
Unit tests for DockerRuntime extensions for the pin sandbox feature.

These tests verify the new functionality added to DockerRuntime including:
- Container renaming functionality
- Container label operations (add, update)
- Container search by labels
- Modified stop_and_remove behavior with pinned containers
"""

import asyncio
import json
import pytest
import uuid
from unittest.mock import AsyncMock, patch, MagicMock

from python.sandbox.container_runtime import DockerRuntime, ContainerConfig


class TestDockerRuntimeExtensions:
    """Test DockerRuntime extensions for pin sandbox functionality."""
    
    @pytest.fixture
    def runtime(self):
        """Create a DockerRuntime instance for testing."""
        return DockerRuntime("docker")
    
    @pytest.fixture
    def container_id(self):
        """Generate a test container ID."""
        return f"container_{uuid.uuid4().hex[:12]}"
    
    @pytest.fixture
    def container_name(self):
        """Generate a test container name."""
        return f"test_container_{uuid.uuid4().hex[:8]}"


class TestContainerRenaming:
    """Test container renaming functionality."""
    
    @pytest.fixture
    def runtime(self):
        """Create a DockerRuntime instance for testing."""
        return DockerRuntime("docker")
    
    @pytest.mark.asyncio
    async def test_rename_container_success(self, runtime):
        """Test successful container renaming."""
        container_id = "container123"
        new_name = "new_container_name"
        
        with patch.object(runtime, '_run_command') as mock_run:
            mock_run.return_value = {
                "returncode": 0,
                "stdout": "",
                "stderr": ""
            }
            
            await runtime.rename_container(container_id, new_name)
            
            mock_run.assert_called_once_with(
                ["rename", container_id, new_name], 
                timeout=30
            )
    
    @pytest.mark.asyncio
    async def test_rename_container_failure(self, runtime):
        """Test container renaming failure."""
        container_id = "nonexistent"
        new_name = "new_name"
        
        with patch.object(runtime, '_run_command') as mock_run:
            mock_run.return_value = {
                "returncode": 1,
                "stdout": "",
                "stderr": "No such container: nonexistent"
            }
            
            with pytest.raises(RuntimeError, match="Failed to rename container nonexistent to new_name"):
                await runtime.rename_container(container_id, new_name)
    
    @pytest.mark.asyncio
    async def test_rename_container_name_conflict(self, runtime):
        """Test container renaming with name conflict."""
        container_id = "container123"
        new_name = "existing_name"
        
        with patch.object(runtime, '_run_command') as mock_run:
            mock_run.return_value = {
                "returncode": 1,
                "stdout": "",
                "stderr": "Conflict. The container name '/existing_name' is already in use"
            }
            
            with pytest.raises(RuntimeError, match="Failed to rename container"):
                await runtime.rename_container(container_id, new_name)


class TestContainerLabelOperations:
    """Test container label operations (add, update)."""
    
    @pytest.fixture
    def runtime(self):
        """Create a DockerRuntime instance for testing."""
        return DockerRuntime("docker")
    
    @pytest.fixture
    def mock_container_info(self):
        """Mock container inspection data."""
        return {
            "Name": "/test_container",
            "Config": {
                "Labels": {
                    "existing_label": "existing_value"
                },
                "Env": ["PATH=/usr/local/bin:/usr/bin:/bin"],
                "WorkingDir": "/workspace",
                "Cmd": ["python", "-c", "import time; time.sleep(3600)"]
            },
            "HostConfig": {
                "Memory": 268435456,  # 256MB in bytes
                "NanoCpus": 500000000  # 0.5 CPU
            },
            "Mounts": [
                {
                    "Type": "bind",
                    "Source": "/host/path",
                    "Destination": "/container/path"
                }
            ]
        }
    
    @pytest.mark.asyncio
    async def test_update_container_labels_success(self, runtime, mock_container_info):
        """Test successful container label update."""
        container_id = "container123"
        new_labels = {
            "pinned": "true",
            "pinned_name": "my_sandbox"
        }
        
        with patch.object(runtime, '_run_command') as mock_run, \
             patch.object(runtime, 'is_container_running') as mock_running:
            
            # Mock container inspection
            mock_run.side_effect = [
                # inspect command
                {
                    "returncode": 0,
                    "stdout": json.dumps([mock_container_info]),
                    "stderr": ""
                },
                # stop command (container was running)
                {
                    "returncode": 0,
                    "stdout": "",
                    "stderr": ""
                },
                # commit command
                {
                    "returncode": 0,
                    "stdout": "",
                    "stderr": ""
                },
                # run command (create new container)
                {
                    "returncode": 0,
                    "stdout": "",
                    "stderr": ""
                },
                # rm command (remove old container)
                {
                    "returncode": 0,
                    "stdout": "",
                    "stderr": ""
                },
                # rename command
                {
                    "returncode": 0,
                    "stdout": "",
                    "stderr": ""
                },
                # start command (container was originally running)
                {
                    "returncode": 0,
                    "stdout": "",
                    "stderr": ""
                },
                # rmi command (cleanup temp image)
                {
                    "returncode": 0,
                    "stdout": "",
                    "stderr": ""
                }
            ]
            
            mock_running.return_value = True
            
            await runtime.update_container_labels(container_id, new_labels)
            
            # Verify the sequence of calls
            assert mock_run.call_count == 8
            
            # Check inspect call
            inspect_call = mock_run.call_args_list[0]
            assert inspect_call[0][0] == ["inspect", container_id]
            
            # Check commit call
            commit_call = mock_run.call_args_list[2]
            assert "commit" in commit_call[0][0]
            assert container_id in commit_call[0][0]
            
            # Check run call has new labels
            run_call = mock_run.call_args_list[3]
            run_args = run_call[0][0]
            assert "run" in run_args
            assert "--label" in run_args
            
            # Verify labels are included
            label_args = []
            for i, arg in enumerate(run_args):
                if arg == "--label" and i + 1 < len(run_args):
                    label_args.append(run_args[i + 1])
            
            assert "existing_label=existing_value" in label_args
            assert "pinned=true" in label_args
            assert "pinned_name=my_sandbox" in label_args
    
    @pytest.mark.asyncio
    async def test_update_container_labels_stopped_container(self, runtime, mock_container_info):
        """Test label update on stopped container."""
        container_id = "container123"
        new_labels = {"pinned": "true"}
        
        with patch.object(runtime, '_run_command') as mock_run, \
             patch.object(runtime, 'is_container_running') as mock_running:
            
            mock_run.side_effect = [
                # inspect command
                {
                    "returncode": 0,
                    "stdout": json.dumps([mock_container_info]),
                    "stderr": ""
                },
                # commit command
                {
                    "returncode": 0,
                    "stdout": "",
                    "stderr": ""
                },
                # run command
                {
                    "returncode": 0,
                    "stdout": "",
                    "stderr": ""
                },
                # rm command
                {
                    "returncode": 0,
                    "stdout": "",
                    "stderr": ""
                },
                # rename command
                {
                    "returncode": 0,
                    "stdout": "",
                    "stderr": ""
                },
                # rmi command
                {
                    "returncode": 0,
                    "stdout": "",
                    "stderr": ""
                }
            ]
            
            mock_running.return_value = False  # Container is stopped
            
            await runtime.update_container_labels(container_id, new_labels)
            
            # Should not call stop or start since container was already stopped
            assert mock_run.call_count == 6
            
            # Verify no stop/start calls
            for call in mock_run.call_args_list:
                assert "stop" not in call[0][0]
                assert "start" not in call[0][0]
    
    @pytest.mark.asyncio
    async def test_update_container_labels_inspect_failure(self, runtime):
        """Test label update with container inspection failure."""
        container_id = "nonexistent"
        new_labels = {"pinned": "true"}
        
        with patch.object(runtime, '_run_command') as mock_run:
            mock_run.return_value = {
                "returncode": 1,
                "stdout": "",
                "stderr": "No such container: nonexistent"
            }
            
            with pytest.raises(RuntimeError, match="Failed to inspect container"):
                await runtime.update_container_labels(container_id, new_labels)
    
    @pytest.mark.asyncio
    async def test_update_container_labels_invalid_json(self, runtime):
        """Test label update with invalid JSON from inspect."""
        container_id = "container123"
        new_labels = {"pinned": "true"}
        
        with patch.object(runtime, '_run_command') as mock_run:
            mock_run.return_value = {
                "returncode": 0,
                "stdout": "invalid json",
                "stderr": ""
            }
            
            with pytest.raises(RuntimeError, match="Failed to parse container inspection data"):
                await runtime.update_container_labels(container_id, new_labels)
    
    @pytest.mark.asyncio
    async def test_update_container_labels_commit_failure(self, runtime, mock_container_info):
        """Test label update with commit failure."""
        container_id = "container123"
        new_labels = {"pinned": "true"}
        
        with patch.object(runtime, '_run_command') as mock_run, \
             patch.object(runtime, 'is_container_running') as mock_running:
            
            mock_run.side_effect = [
                # inspect command succeeds
                {
                    "returncode": 0,
                    "stdout": json.dumps([mock_container_info]),
                    "stderr": ""
                },
                # commit command fails
                {
                    "returncode": 1,
                    "stdout": "",
                    "stderr": "Failed to commit container"
                }
            ]
            
            mock_running.return_value = False
            
            with pytest.raises(RuntimeError, match="Failed to commit container"):
                await runtime.update_container_labels(container_id, new_labels)
    
    @pytest.mark.asyncio
    async def test_update_container_labels_run_failure(self, runtime, mock_container_info):
        """Test label update with run command failure."""
        container_id = "container123"
        new_labels = {"pinned": "true"}
        
        with patch.object(runtime, '_run_command') as mock_run, \
             patch.object(runtime, 'is_container_running') as mock_running:
            
            mock_run.side_effect = [
                # inspect command succeeds
                {
                    "returncode": 0,
                    "stdout": json.dumps([mock_container_info]),
                    "stderr": ""
                },
                # commit command succeeds
                {
                    "returncode": 0,
                    "stdout": "",
                    "stderr": ""
                },
                # run command fails
                {
                    "returncode": 1,
                    "stdout": "",
                    "stderr": "Failed to create container with updated labels"
                },
                # rmi command (cleanup)
                {
                    "returncode": 0,
                    "stdout": "",
                    "stderr": ""
                }
            ]
            
            mock_running.return_value = False
            
            with pytest.raises(RuntimeError, match="Failed to create container with updated labels"):
                await runtime.update_container_labels(container_id, new_labels)


class TestContainerSearchByLabels:
    """Test container search by labels functionality."""
    
    @pytest.fixture
    def runtime(self):
        """Create a DockerRuntime instance for testing."""
        return DockerRuntime("docker")
    
    @pytest.fixture
    def mock_container_list_output(self):
        """Mock output from docker ps command."""
        return [
            '{"ID":"abc123","Names":"container1","Labels":"pinned=true,pinned_name=sandbox1","Status":"Up 5 minutes"}',
            '{"ID":"def456","Names":"container2","Labels":"pinned=true,pinned_name=sandbox2","Status":"Exited (0) 2 minutes ago"}',
            '{"ID":"ghi789","Names":"container3","Labels":"app=test","Status":"Up 1 hour"}'
        ]
    
    @pytest.mark.asyncio
    async def test_get_containers_by_label_success(self, runtime, mock_container_list_output):
        """Test successful container search by labels."""
        label_filters = {"pinned": "true"}
        
        with patch.object(runtime, '_run_command') as mock_run:
            mock_run.return_value = {
                "returncode": 0,
                "stdout": "\n".join(mock_container_list_output),
                "stderr": ""
            }
            
            containers = await runtime.get_containers_by_label(label_filters)
            
            assert len(containers) == 3  # All containers returned from mock
            
            # Verify the command was called correctly
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert "ps" in args
            assert "-a" in args
            assert "--filter" in args
            assert "label=pinned=true" in args
            assert "--format" in args
            assert "{{json .}}" in args
    
    @pytest.mark.asyncio
    async def test_get_containers_by_label_multiple_filters(self, runtime):
        """Test container search with multiple label filters."""
        label_filters = {"pinned": "true", "pinned_name": "sandbox1"}
        
        with patch.object(runtime, '_run_command') as mock_run:
            mock_run.return_value = {
                "returncode": 0,
                "stdout": '{"ID":"abc123","Names":"container1","Labels":"pinned=true,pinned_name=sandbox1","Status":"Up 5 minutes"}',
                "stderr": ""
            }
            
            containers = await runtime.get_containers_by_label(label_filters)
            
            assert len(containers) == 1
            assert containers[0]["id"] == "abc123"
            assert containers[0]["name"] == "container1"
            assert containers[0]["labels"]["pinned"] == "true"
            assert containers[0]["labels"]["pinned_name"] == "sandbox1"
            assert containers[0]["running"] is True
            
            # Verify both filters were applied
            args = mock_run.call_args[0][0]
            assert "label=pinned=true" in args
            assert "label=pinned_name=sandbox1" in args
    
    @pytest.mark.asyncio
    async def test_get_containers_by_label_no_results(self, runtime):
        """Test container search with no matching containers."""
        label_filters = {"nonexistent": "label"}
        
        with patch.object(runtime, '_run_command') as mock_run:
            mock_run.return_value = {
                "returncode": 0,
                "stdout": "",
                "stderr": ""
            }
            
            containers = await runtime.get_containers_by_label(label_filters)
            
            assert len(containers) == 0
    
    @pytest.mark.asyncio
    async def test_get_containers_by_label_command_failure(self, runtime):
        """Test container search with command failure."""
        label_filters = {"pinned": "true"}
        
        with patch.object(runtime, '_run_command') as mock_run:
            mock_run.return_value = {
                "returncode": 1,
                "stdout": "",
                "stderr": "Docker daemon not running"
            }
            
            with pytest.raises(RuntimeError, match="Failed to list containers"):
                await runtime.get_containers_by_label(label_filters)
    
    @pytest.mark.asyncio
    async def test_get_containers_by_label_malformed_json(self, runtime):
        """Test container search with malformed JSON output."""
        label_filters = {"pinned": "true"}
        
        with patch.object(runtime, '_run_command') as mock_run:
            mock_run.return_value = {
                "returncode": 0,
                "stdout": "invalid json line\n{\"valid\": \"json\"}",
                "stderr": ""
            }
            
            containers = await runtime.get_containers_by_label(label_filters)
            
            # Should skip malformed lines and return valid ones
            # The second line is valid JSON but doesn't have container fields, so it creates a container with None values
            assert len(containers) == 1  # One valid JSON line (even if incomplete container data)
    
    @pytest.mark.asyncio
    async def test_get_containers_by_label_empty_labels(self, runtime):
        """Test container search with containers that have no labels."""
        label_filters = {"pinned": "true"}
        
        with patch.object(runtime, '_run_command') as mock_run:
            mock_run.return_value = {
                "returncode": 0,
                "stdout": '{"ID":"abc123","Names":"container1","Labels":"<none>","Status":"Up 5 minutes"}',
                "stderr": ""
            }
            
            containers = await runtime.get_containers_by_label(label_filters)
            
            assert len(containers) == 1
            assert containers[0]["labels"] == {}
    
    @pytest.mark.asyncio
    async def test_list_containers_integration(self, runtime):
        """Test list_containers method which is used by get_containers_by_label."""
        with patch.object(runtime, '_run_command') as mock_run:
            mock_run.return_value = {
                "returncode": 0,
                "stdout": '{"ID":"abc123","Names":"test_container","Labels":"pinned=true,env=test","Status":"Up 5 minutes"}',
                "stderr": ""
            }
            
            containers = await runtime.list_containers(
                all=True,
                label_filters={"pinned": "true"},
                timeout=15
            )
            
            assert len(containers) == 1
            container = containers[0]
            assert container["id"] == "abc123"
            assert container["name"] == "test_container"
            assert container["labels"]["pinned"] == "true"
            assert container["labels"]["env"] == "test"
            assert container["running"] is True
            assert "Up 5 minutes" in container["status"]


class TestModifiedStopAndRemove:
    """Test modified stop_and_remove behavior with pinned containers."""
    
    @pytest.fixture
    def runtime(self):
        """Create a DockerRuntime instance for testing."""
        return DockerRuntime("docker")
    
    @pytest.fixture
    def mock_pinned_container_info(self):
        """Mock container info for a pinned container."""
        return {
            "Config": {
                "Labels": {
                    "pinned": "true",
                    "pinned_name": "my_sandbox"
                }
            }
        }
    
    @pytest.fixture
    def mock_unpinned_container_info(self):
        """Mock container info for an unpinned container."""
        return {
            "Config": {
                "Labels": {
                    "app": "test"
                }
            }
        }
    
    @pytest.mark.asyncio
    async def test_stop_and_remove_pinned_container(self, runtime, mock_pinned_container_info):
        """Test stop_and_remove only stops pinned containers (doesn't remove them)."""
        container_id = "pinned_container123"
        
        with patch.object(runtime, '_run_command') as mock_run, \
             patch.object(runtime, 'is_container_running') as mock_running:
            
            # Mock container inspection to show it's pinned
            mock_run.side_effect = [
                # inspect command
                {
                    "returncode": 0,
                    "stdout": json.dumps([mock_pinned_container_info]),
                    "stderr": ""
                },
                # stop command
                {
                    "returncode": 0,
                    "stdout": "",
                    "stderr": ""
                }
                # No remove command should be called
            ]
            
            mock_running.return_value = True  # Container is running
            
            await runtime.stop_and_remove(container_id)
            
            # Verify inspect and stop were called, but not remove
            assert mock_run.call_count == 2
            
            # Check inspect call
            inspect_call = mock_run.call_args_list[0]
            assert inspect_call[0][0] == ["inspect", container_id]
            
            # Check stop call
            stop_call = mock_run.call_args_list[1]
            assert stop_call[0][0] == ["stop", container_id]
            
            # Verify remove was not called
            for call in mock_run.call_args_list:
                assert "rm" not in call[0][0]
    
    @pytest.mark.asyncio
    async def test_stop_and_remove_unpinned_container(self, runtime, mock_unpinned_container_info):
        """Test stop_and_remove stops and removes unpinned containers."""
        container_id = "unpinned_container123"
        
        with patch.object(runtime, '_run_command') as mock_run, \
             patch.object(runtime, 'is_container_running') as mock_running:
            
            # Mock container inspection to show it's not pinned
            mock_run.side_effect = [
                # inspect command
                {
                    "returncode": 0,
                    "stdout": json.dumps([mock_unpinned_container_info]),
                    "stderr": ""
                },
                # stop command
                {
                    "returncode": 0,
                    "stdout": "",
                    "stderr": ""
                },
                # remove command
                {
                    "returncode": 0,
                    "stdout": "",
                    "stderr": ""
                }
            ]
            
            mock_running.return_value = True  # Container is running
            
            await runtime.stop_and_remove(container_id)
            
            # Verify inspect, stop, and remove were all called
            assert mock_run.call_count == 3
            
            # Check calls in order
            inspect_call = mock_run.call_args_list[0]
            assert inspect_call[0][0] == ["inspect", container_id]
            
            stop_call = mock_run.call_args_list[1]
            assert stop_call[0][0] == ["stop", container_id]
            
            remove_call = mock_run.call_args_list[2]
            assert remove_call[0][0] == ["rm", container_id]
    
    @pytest.mark.asyncio
    async def test_stop_and_remove_stopped_pinned_container(self, runtime, mock_pinned_container_info):
        """Test stop_and_remove with already stopped pinned container."""
        container_id = "stopped_pinned_container"
        
        with patch.object(runtime, '_run_command') as mock_run, \
             patch.object(runtime, 'is_container_running') as mock_running:
            
            # Mock container inspection to show it's pinned
            mock_run.return_value = {
                "returncode": 0,
                "stdout": json.dumps([mock_pinned_container_info]),
                "stderr": ""
            }
            
            mock_running.return_value = False  # Container is already stopped
            
            await runtime.stop_and_remove(container_id)
            
            # Should only call inspect, not stop or remove
            assert mock_run.call_count == 1
            
            inspect_call = mock_run.call_args_list[0]
            assert inspect_call[0][0] == ["inspect", container_id]
    
    @pytest.mark.asyncio
    async def test_stop_and_remove_stopped_unpinned_container(self, runtime, mock_unpinned_container_info):
        """Test stop_and_remove with already stopped unpinned container."""
        container_id = "stopped_unpinned_container"
        
        with patch.object(runtime, '_run_command') as mock_run, \
             patch.object(runtime, 'is_container_running') as mock_running:
            
            # Mock container inspection and remove
            mock_run.side_effect = [
                # inspect command
                {
                    "returncode": 0,
                    "stdout": json.dumps([mock_unpinned_container_info]),
                    "stderr": ""
                },
                # remove command
                {
                    "returncode": 0,
                    "stdout": "",
                    "stderr": ""
                }
            ]
            
            mock_running.return_value = False  # Container is already stopped
            
            await runtime.stop_and_remove(container_id)
            
            # Should call inspect and remove, but not stop
            assert mock_run.call_count == 2
            
            inspect_call = mock_run.call_args_list[0]
            assert inspect_call[0][0] == ["inspect", container_id]
            
            remove_call = mock_run.call_args_list[1]
            assert remove_call[0][0] == ["rm", container_id]
    
    @pytest.mark.asyncio
    async def test_stop_and_remove_inspect_failure(self, runtime):
        """Test stop_and_remove with container inspection failure."""
        container_id = "nonexistent_container"
        
        with patch.object(runtime, '_run_command') as mock_run, \
             patch.object(runtime, 'is_container_running') as mock_running:
            
            # Mock inspect failure (container doesn't exist)
            mock_run.return_value = {
                "returncode": 1,
                "stdout": "",
                "stderr": "No such container: nonexistent_container"
            }
            
            mock_running.return_value = False
            
            # Should not raise exception for missing containers (cleanup scenario)
            await runtime.stop_and_remove(container_id)
            
            # Should call inspect (1 call) and is_container_running makes another call (1 call)
            assert mock_run.call_count == 2  # inspect + is_container_running calls
            assert mock_running.call_count == 1  # is_container_running is called
    
    @pytest.mark.asyncio
    async def test_stop_and_remove_malformed_labels(self, runtime):
        """Test stop_and_remove with malformed container labels."""
        container_id = "container_with_bad_labels"
        
        with patch.object(runtime, '_run_command') as mock_run, \
             patch.object(runtime, 'is_container_running') as mock_running:
            
            # Mock container with malformed JSON
            mock_run.side_effect = [
                # inspect command returns malformed JSON
                {
                    "returncode": 0,
                    "stdout": "invalid json",
                    "stderr": ""
                },
                # stop command
                {
                    "returncode": 0,
                    "stdout": "",
                    "stderr": ""
                },
                # remove command (should be called since we can't determine if pinned)
                {
                    "returncode": 0,
                    "stdout": "",
                    "stderr": ""
                }
            ]
            
            mock_running.return_value = True
            
            await runtime.stop_and_remove(container_id)
            
            # Should assume not pinned and do full stop+remove
            assert mock_run.call_count == 3
    
    @pytest.mark.asyncio
    async def test_stop_and_remove_no_labels(self, runtime):
        """Test stop_and_remove with container that has no labels."""
        container_id = "container_no_labels"
        
        mock_container_info = {
            "Config": {
                "Labels": None
            }
        }
        
        with patch.object(runtime, '_run_command') as mock_run, \
             patch.object(runtime, 'is_container_running') as mock_running:
            
            mock_run.side_effect = [
                # inspect command
                {
                    "returncode": 0,
                    "stdout": json.dumps([mock_container_info]),
                    "stderr": ""
                },
                # stop command
                {
                    "returncode": 0,
                    "stdout": "",
                    "stderr": ""
                },
                # remove command
                {
                    "returncode": 0,
                    "stdout": "",
                    "stderr": ""
                }
            ]
            
            mock_running.return_value = True
            
            await runtime.stop_and_remove(container_id)
            
            # Should do full stop+remove since no pinned label
            assert mock_run.call_count == 3
    
    @pytest.mark.asyncio
    async def test_stop_and_remove_pinned_false(self, runtime):
        """Test stop_and_remove with container that has pinned=false."""
        container_id = "container_pinned_false"
        
        mock_container_info = {
            "Config": {
                "Labels": {
                    "pinned": "false",
                    "app": "test"
                }
            }
        }
        
        with patch.object(runtime, '_run_command') as mock_run, \
             patch.object(runtime, 'is_container_running') as mock_running:
            
            mock_run.side_effect = [
                # inspect command
                {
                    "returncode": 0,
                    "stdout": json.dumps([mock_container_info]),
                    "stderr": ""
                },
                # stop command
                {
                    "returncode": 0,
                    "stdout": "",
                    "stderr": ""
                },
                # remove command
                {
                    "returncode": 0,
                    "stdout": "",
                    "stderr": ""
                }
            ]
            
            mock_running.return_value = True
            
            await runtime.stop_and_remove(container_id)
            
            # Should do full stop+remove since pinned=false
            assert mock_run.call_count == 3
    
    @pytest.mark.asyncio
    async def test_stop_and_remove_stop_failure_unpinned(self, runtime, mock_unpinned_container_info):
        """Test stop_and_remove with stop command failure on unpinned container."""
        container_id = "container_stop_fail"
        
        with patch.object(runtime, '_run_command') as mock_run, \
             patch.object(runtime, 'is_container_running') as mock_running:
            
            mock_run.side_effect = [
                # inspect command
                {
                    "returncode": 0,
                    "stdout": json.dumps([mock_unpinned_container_info]),
                    "stderr": ""
                },
                # stop command fails
                {
                    "returncode": 1,
                    "stdout": "",
                    "stderr": "Failed to stop container"
                }
            ]
            
            mock_running.return_value = True
            
            # Should propagate the stop failure
            with pytest.raises(RuntimeError, match="Failed to stop container"):
                await runtime.stop_and_remove(container_id)
    
    @pytest.mark.asyncio
    async def test_stop_and_remove_stop_failure_pinned(self, runtime, mock_pinned_container_info):
        """Test stop_and_remove with stop command failure on pinned container."""
        container_id = "pinned_container_stop_fail"
        
        with patch.object(runtime, '_run_command') as mock_run, \
             patch.object(runtime, 'is_container_running') as mock_running:
            
            mock_run.side_effect = [
                # inspect command
                {
                    "returncode": 0,
                    "stdout": json.dumps([mock_pinned_container_info]),
                    "stderr": ""
                },
                # stop command fails
                {
                    "returncode": 1,
                    "stdout": "",
                    "stderr": "Failed to stop container"
                }
            ]
            
            mock_running.return_value = True
            
            # Should propagate the stop failure even for pinned containers
            with pytest.raises(RuntimeError, match="Failed to stop container"):
                await runtime.stop_and_remove(container_id)