"""
Unit tests for modified cleanup logic in DockerRuntime.

These tests verify that the stop_and_remove method correctly handles pinned containers
by only stopping them (not removing) while maintaining existing behavior for unpinned containers.

Requirements tested:
- 2.1: Session cleanup stops but doesn't delete pinned containers
- 2.2: Session cleanup preserves all container data and state for pinned containers  
- 2.3: Session cleanup removes session association but keeps pinned containers
- 3.1: Orphan cleanup stops but doesn't delete pinned containers
- 3.2: Orphan cleanup preserves pinned containers for future reattachment
- 3.3: Orphan cleanup logs preservation action for pinned containers
"""

import asyncio
import json
import pytest
import uuid
from unittest.mock import AsyncMock, patch, MagicMock

from python.sandbox.container_runtime import DockerRuntime, ContainerConfig


class TestCleanupLogicModifications:
    """Test modified cleanup logic for pinned containers."""
    
    @pytest.fixture
    def runtime(self):
        """Create a DockerRuntime instance for testing."""
        return DockerRuntime("docker")
    
    @pytest.fixture
    def container_id(self):
        """Generate a test container ID."""
        return f"container_{uuid.uuid4().hex[:12]}"
    
    @pytest.fixture
    def mock_pinned_container_info(self):
        """Mock container info for a pinned container."""
        return {
            "Config": {
                "Labels": {
                    "pinned": "true",
                    "pinned_name": "my_sandbox",
                    "app": "test"
                }
            }
        }
    
    @pytest.fixture
    def mock_unpinned_container_info(self):
        """Mock container info for an unpinned container."""
        return {
            "Config": {
                "Labels": {
                    "app": "test",
                    "environment": "development"
                }
            }
        }
    
    @pytest.fixture
    def mock_no_labels_container_info(self):
        """Mock container info for a container with no labels."""
        return {
            "Config": {
                "Labels": None
            }
        }


class TestStopAndRemovePinnedContainers:
    """Test that stop_and_remove only stops pinned containers (doesn't remove them)."""
    
    @pytest.fixture
    def runtime(self):
        return DockerRuntime("docker")
    
    @pytest.mark.asyncio
    async def test_stop_and_remove_running_pinned_container(self, runtime):
        """Test stop_and_remove only stops a running pinned container."""
        container_id = "pinned_running_container"
        mock_pinned_info = {
            "Config": {
                "Labels": {
                    "pinned": "true",
                    "pinned_name": "my_dev_env"
                }
            }
        }
        
        with patch.object(runtime, '_run_command') as mock_run, \
             patch.object(runtime, 'is_container_running') as mock_running:
            
            # Mock container inspection showing it's pinned
            mock_run.side_effect = [
                # inspect command
                {
                    "returncode": 0,
                    "stdout": json.dumps([mock_pinned_info]),
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
            
            # Verify only inspect and stop were called
            assert mock_run.call_count == 2
            
            # Verify inspect call
            inspect_call = mock_run.call_args_list[0]
            assert inspect_call[0][0] == ["inspect", container_id]
            
            # Verify stop call
            stop_call = mock_run.call_args_list[1]
            assert stop_call[0][0] == ["stop", container_id]
            
            # Verify remove was NOT called
            for call in mock_run.call_args_list:
                assert "rm" not in call[0][0]
    
    @pytest.mark.asyncio
    async def test_stop_and_remove_stopped_pinned_container(self, runtime):
        """Test stop_and_remove with already stopped pinned container."""
        container_id = "pinned_stopped_container"
        mock_pinned_info = {
            "Config": {
                "Labels": {
                    "pinned": "true",
                    "pinned_name": "persistent_workspace"
                }
            }
        }
        
        with patch.object(runtime, '_run_command') as mock_run, \
             patch.object(runtime, 'is_container_running') as mock_running:
            
            # Mock container inspection showing it's pinned
            mock_run.return_value = {
                "returncode": 0,
                "stdout": json.dumps([mock_pinned_info]),
                "stderr": ""
            }
            
            mock_running.return_value = False  # Container is already stopped
            
            await runtime.stop_and_remove(container_id)
            
            # Should only call inspect, not stop or remove
            assert mock_run.call_count == 1
            
            inspect_call = mock_run.call_args_list[0]
            assert inspect_call[0][0] == ["inspect", container_id]
            
            # Verify no stop or remove calls
            for call in mock_run.call_args_list:
                assert "stop" not in call[0][0]
                assert "rm" not in call[0][0]
    
    @pytest.mark.asyncio
    async def test_stop_and_remove_pinned_case_insensitive(self, runtime):
        """Test stop_and_remove handles pinned label case-insensitively."""
        container_id = "case_test_container"
        
        # Test different case variations of "true"
        test_cases = ["True", "TRUE", "tRuE"]
        
        for pinned_value in test_cases:
            mock_pinned_info = {
                "Config": {
                    "Labels": {
                        "pinned": pinned_value,
                        "pinned_name": "case_test"
                    }
                }
            }
            
            with patch.object(runtime, '_run_command') as mock_run, \
                 patch.object(runtime, 'is_container_running') as mock_running:
                
                mock_run.side_effect = [
                    # inspect command
                    {
                        "returncode": 0,
                        "stdout": json.dumps([mock_pinned_info]),
                        "stderr": ""
                    },
                    # stop command
                    {
                        "returncode": 0,
                        "stdout": "",
                        "stderr": ""
                    }
                ]
                
                mock_running.return_value = True
                
                await runtime.stop_and_remove(container_id)
                
                # Should only stop, not remove
                assert mock_run.call_count == 2
                
                # Verify remove was NOT called
                for call in mock_run.call_args_list:
                    assert "rm" not in call[0][0]


class TestStopAndRemoveUnpinnedContainers:
    """Test that stop_and_remove maintains existing behavior for unpinned containers."""
    
    @pytest.fixture
    def runtime(self):
        return DockerRuntime("docker")
    
    @pytest.mark.asyncio
    async def test_stop_and_remove_running_unpinned_container(self, runtime):
        """Test stop_and_remove stops and removes running unpinned container."""
        container_id = "unpinned_running_container"
        mock_unpinned_info = {
            "Config": {
                "Labels": {
                    "app": "test_app",
                    "environment": "development"
                }
            }
        }
        
        with patch.object(runtime, '_run_command') as mock_run, \
             patch.object(runtime, 'is_container_running') as mock_running:
            
            mock_run.side_effect = [
                # inspect command
                {
                    "returncode": 0,
                    "stdout": json.dumps([mock_unpinned_info]),
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
            
            # Verify calls in correct order
            inspect_call = mock_run.call_args_list[0]
            assert inspect_call[0][0] == ["inspect", container_id]
            
            stop_call = mock_run.call_args_list[1]
            assert stop_call[0][0] == ["stop", container_id]
            
            remove_call = mock_run.call_args_list[2]
            assert remove_call[0][0] == ["rm", container_id]
    
    @pytest.mark.asyncio
    async def test_stop_and_remove_stopped_unpinned_container(self, runtime):
        """Test stop_and_remove removes already stopped unpinned container."""
        container_id = "unpinned_stopped_container"
        mock_unpinned_info = {
            "Config": {
                "Labels": {
                    "app": "test_app"
                }
            }
        }
        
        with patch.object(runtime, '_run_command') as mock_run, \
             patch.object(runtime, 'is_container_running') as mock_running:
            
            mock_run.side_effect = [
                # inspect command
                {
                    "returncode": 0,
                    "stdout": json.dumps([mock_unpinned_info]),
                    "stderr": ""
                },
                # remove command (no stop needed)
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
            
            # Verify stop was not called
            for call in mock_run.call_args_list:
                assert "stop" not in call[0][0]
    
    @pytest.mark.asyncio
    async def test_stop_and_remove_container_with_no_labels(self, runtime):
        """Test stop_and_remove treats containers with no labels as unpinned."""
        container_id = "no_labels_container"
        mock_no_labels_info = {
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
                    "stdout": json.dumps([mock_no_labels_info]),
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
            
            # Should do full stop and remove
            assert mock_run.call_count == 3
            
            # Verify remove was called
            remove_call = mock_run.call_args_list[2]
            assert remove_call[0][0] == ["rm", container_id]
    
    @pytest.mark.asyncio
    async def test_stop_and_remove_container_with_empty_labels(self, runtime):
        """Test stop_and_remove treats containers with empty labels as unpinned."""
        container_id = "empty_labels_container"
        mock_empty_labels_info = {
            "Config": {
                "Labels": {}
            }
        }
        
        with patch.object(runtime, '_run_command') as mock_run, \
             patch.object(runtime, 'is_container_running') as mock_running:
            
            mock_run.side_effect = [
                # inspect command
                {
                    "returncode": 0,
                    "stdout": json.dumps([mock_empty_labels_info]),
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
            
            # Should do full stop and remove
            assert mock_run.call_count == 3
            
            # Verify remove was called
            remove_call = mock_run.call_args_list[2]
            assert remove_call[0][0] == ["rm", container_id]
    
    @pytest.mark.asyncio
    async def test_stop_and_remove_pinned_false_container(self, runtime):
        """Test stop_and_remove treats pinned=false containers as unpinned."""
        container_id = "pinned_false_container"
        mock_pinned_false_info = {
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
                    "stdout": json.dumps([mock_pinned_false_info]),
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
            
            # Should do full stop and remove
            assert mock_run.call_count == 3
            
            # Verify remove was called
            remove_call = mock_run.call_args_list[2]
            assert remove_call[0][0] == ["rm", container_id]


class TestMixedPinnedUnpinnedContainers:
    """Test cleanup behavior with mixed pinned/unpinned containers."""
    
    @pytest.fixture
    def runtime(self):
        return DockerRuntime("docker")
    
    @pytest.mark.asyncio
    async def test_cleanup_mixed_containers_sequential(self, runtime):
        """Test sequential cleanup of mixed pinned and unpinned containers."""
        # Test data for mixed containers
        containers = [
            {
                "id": "pinned_container_1",
                "info": {
                    "Config": {
                        "Labels": {
                            "pinned": "true",
                            "pinned_name": "dev_env_1"
                        }
                    }
                },
                "running": True,
                "should_remove": False
            },
            {
                "id": "unpinned_container_1", 
                "info": {
                    "Config": {
                        "Labels": {
                            "app": "temp_service"
                        }
                    }
                },
                "running": True,
                "should_remove": True
            },
            {
                "id": "pinned_container_2",
                "info": {
                    "Config": {
                        "Labels": {
                            "pinned": "true",
                            "pinned_name": "persistent_db"
                        }
                    }
                },
                "running": False,
                "should_remove": False
            },
            {
                "id": "unpinned_container_2",
                "info": {
                    "Config": {
                        "Labels": {
                            "environment": "test"
                        }
                    }
                },
                "running": False,
                "should_remove": True
            }
        ]
        
        # Test each container cleanup
        for container in containers:
            with patch.object(runtime, '_run_command') as mock_run, \
                 patch.object(runtime, 'is_container_running') as mock_running:
                
                # Setup mocks based on container state
                mock_running.return_value = container["running"]
                
                expected_calls = []
                
                # Always inspect first
                expected_calls.append({
                    "returncode": 0,
                    "stdout": json.dumps([container["info"]]),
                    "stderr": ""
                })
                
                # Stop if running
                if container["running"]:
                    expected_calls.append({
                        "returncode": 0,
                        "stdout": "",
                        "stderr": ""
                    })
                
                # Remove if unpinned
                if container["should_remove"]:
                    expected_calls.append({
                        "returncode": 0,
                        "stdout": "",
                        "stderr": ""
                    })
                
                mock_run.side_effect = expected_calls
                
                await runtime.stop_and_remove(container["id"])
                
                # Verify correct number of calls
                expected_call_count = len(expected_calls)
                assert mock_run.call_count == expected_call_count
                
                # Verify inspect was called
                inspect_call = mock_run.call_args_list[0]
                assert inspect_call[0][0] == ["inspect", container["id"]]
                
                # Verify remove behavior
                remove_called = any("rm" in call[0][0] for call in mock_run.call_args_list)
                assert remove_called == container["should_remove"]
    
    @pytest.mark.asyncio
    async def test_cleanup_preserves_pinned_data_and_state(self, runtime):
        """Test that cleanup preserves all container data and state for pinned containers."""
        container_id = "data_preservation_test"
        mock_pinned_info = {
            "Config": {
                "Labels": {
                    "pinned": "true",
                    "pinned_name": "data_container",
                    "project": "important_work",
                    "version": "1.2.3"
                }
            }
        }
        
        with patch.object(runtime, '_run_command') as mock_run, \
             patch.object(runtime, 'is_container_running') as mock_running:
            
            mock_run.side_effect = [
                # inspect command
                {
                    "returncode": 0,
                    "stdout": json.dumps([mock_pinned_info]),
                    "stderr": ""
                },
                # stop command
                {
                    "returncode": 0,
                    "stdout": "",
                    "stderr": ""
                }
            ]
            
            mock_running.return_value = True
            
            await runtime.stop_and_remove(container_id)
            
            # Verify only stop was called (preserving container and all its data)
            assert mock_run.call_count == 2
            
            # Verify no destructive operations
            for call in mock_run.call_args_list:
                # Should not call remove, kill, or any other destructive commands
                destructive_commands = ["rm", "kill", "prune", "system"]
                assert not any(cmd in call[0][0] for cmd in destructive_commands)
    
    @pytest.mark.asyncio
    async def test_cleanup_batch_mixed_containers(self, runtime):
        """Test cleanup behavior when processing multiple mixed containers."""
        # Simulate batch cleanup scenario
        container_data = {
            "pinned_web_server": {
                "info": {"Config": {"Labels": {"pinned": "true", "pinned_name": "web_server"}}},
                "running": True,
                "expected_calls": 2  # inspect + stop
            },
            "temp_worker": {
                "info": {"Config": {"Labels": {"app": "worker", "temporary": "true"}}},
                "running": True,
                "expected_calls": 3  # inspect + stop + remove
            },
            "pinned_database": {
                "info": {"Config": {"Labels": {"pinned": "true", "pinned_name": "main_db"}}},
                "running": False,
                "expected_calls": 1  # inspect only
            },
            "test_container": {
                "info": {"Config": {"Labels": {"environment": "test"}}},
                "running": False,
                "expected_calls": 2  # inspect + remove
            }
        }
        
        cleanup_results = {}
        
        # Process each container
        for container_id, data in container_data.items():
            with patch.object(runtime, '_run_command') as mock_run, \
                 patch.object(runtime, 'is_container_running') as mock_running:
                
                mock_running.return_value = data["running"]
                
                # Setup mock responses
                responses = [
                    # Always inspect first
                    {
                        "returncode": 0,
                        "stdout": json.dumps([data["info"]]),
                        "stderr": ""
                    }
                ]
                
                # Add stop response if running
                if data["running"]:
                    responses.append({
                        "returncode": 0,
                        "stdout": "",
                        "stderr": ""
                    })
                
                # Add remove response if unpinned
                is_pinned = data["info"]["Config"]["Labels"].get("pinned", "").lower() == "true"
                if not is_pinned:
                    responses.append({
                        "returncode": 0,
                        "stdout": "",
                        "stderr": ""
                    })
                
                mock_run.side_effect = responses
                
                await runtime.stop_and_remove(container_id)
                
                cleanup_results[container_id] = {
                    "call_count": mock_run.call_count,
                    "calls": [call[0][0] for call in mock_run.call_args_list]
                }
        
        # Verify results
        for container_id, data in container_data.items():
            result = cleanup_results[container_id]
            assert result["call_count"] == data["expected_calls"]
            
            # Verify inspect was always called
            assert any("inspect" in call for call in result["calls"])
            
            # Verify remove behavior based on pinned status
            is_pinned = data["info"]["Config"]["Labels"].get("pinned", "").lower() == "true"
            remove_called = any("rm" in call for call in result["calls"])
            assert remove_called != is_pinned  # Remove called only for unpinned containers


class TestCleanupErrorHandling:
    """Test error handling during cleanup operations."""
    
    @pytest.fixture
    def runtime(self):
        return DockerRuntime("docker")
    
    @pytest.mark.asyncio
    async def test_stop_and_remove_nonexistent_container(self, runtime):
        """Test stop_and_remove gracefully handles nonexistent containers."""
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
            
            # Should attempt inspect and is_container_running
            assert mock_run.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_stop_and_remove_malformed_container_data(self, runtime):
        """Test stop_and_remove handles malformed container inspection data."""
        container_id = "malformed_data_container"
        
        with patch.object(runtime, '_run_command') as mock_run, \
             patch.object(runtime, 'is_container_running') as mock_running:
            
            mock_run.side_effect = [
                # inspect returns malformed JSON
                {
                    "returncode": 0,
                    "stdout": "invalid json data",
                    "stderr": ""
                },
                # stop command
                {
                    "returncode": 0,
                    "stdout": "",
                    "stderr": ""
                },
                # remove command (assumes unpinned due to parse error)
                {
                    "returncode": 0,
                    "stdout": "",
                    "stderr": ""
                }
            ]
            
            mock_running.return_value = True
            
            await runtime.stop_and_remove(container_id)
            
            # Should assume unpinned and do full cleanup when can't parse labels
            assert mock_run.call_count == 3
            
            # Verify remove was called (default behavior when labels can't be determined)
            remove_call = mock_run.call_args_list[2]
            assert remove_call[0][0] == ["rm", container_id]
    
    @pytest.mark.asyncio
    async def test_stop_and_remove_missing_config_section(self, runtime):
        """Test stop_and_remove handles containers with missing Config section."""
        container_id = "missing_config_container"
        mock_incomplete_info = {
            "Name": "/test_container",
            "State": {"Running": False}
            # Missing Config section
        }
        
        with patch.object(runtime, '_run_command') as mock_run, \
             patch.object(runtime, 'is_container_running') as mock_running:
            
            mock_run.side_effect = [
                # inspect returns container without Config
                {
                    "returncode": 0,
                    "stdout": json.dumps([mock_incomplete_info]),
                    "stderr": ""
                },
                # remove command (assumes unpinned)
                {
                    "returncode": 0,
                    "stdout": "",
                    "stderr": ""
                }
            ]
            
            mock_running.return_value = False
            
            await runtime.stop_and_remove(container_id)
            
            # Should assume unpinned and remove
            assert mock_run.call_count == 2
            
            remove_call = mock_run.call_args_list[1]
            assert remove_call[0][0] == ["rm", container_id]
    
    @pytest.mark.asyncio
    async def test_stop_and_remove_stop_failure_pinned_container(self, runtime):
        """Test stop_and_remove handles stop failure for pinned containers."""
        container_id = "stop_failure_pinned"
        mock_pinned_info = {
            "Config": {
                "Labels": {
                    "pinned": "true",
                    "pinned_name": "failing_container"
                }
            }
        }
        
        with patch.object(runtime, '_run_command') as mock_run, \
             patch.object(runtime, 'is_container_running') as mock_running:
            
            mock_run.side_effect = [
                # inspect succeeds
                {
                    "returncode": 0,
                    "stdout": json.dumps([mock_pinned_info]),
                    "stderr": ""
                },
                # stop fails
                {
                    "returncode": 1,
                    "stdout": "",
                    "stderr": "Failed to stop container"
                }
            ]
            
            mock_running.return_value = True
            
            # Should propagate the stop error
            with pytest.raises(RuntimeError, match="Failed to stop container"):
                await runtime.stop_and_remove(container_id)
            
            # Should not attempt remove after stop failure
            assert mock_run.call_count == 2
            
            # Verify no remove call
            for call in mock_run.call_args_list:
                assert "rm" not in call[0][0]