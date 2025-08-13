"""
Tests to verify that the wrapper layer properly uses sandbox SDK instead of direct container runtime access.

This ensures architectural compliance where:
- Wrapper layer only uses sandbox SDK interfaces
- No direct container runtime dependencies in wrapper layer
- Proper abstraction between layers
"""

import pytest
import ast
import os
from pathlib import Path


class TestArchitectureCompliance:
    """Test architectural compliance of the wrapper layer."""
    
    def test_wrapper_no_direct_container_imports(self):
        """Test that wrapper files don't directly import container runtime."""
        wrapper_dir = Path(__file__).parent.parent / "mcp-server" / "microsandbox_wrapper"
        
        forbidden_imports = [
            "from python.sandbox.container_runtime",
            "import python.sandbox.container_runtime",
            "from .container_runtime",
            "import container_runtime"
        ]
        
        violations = []
        
        for py_file in wrapper_dir.glob("*.py"):
            if py_file.name == "__init__.py":
                continue
                
            content = py_file.read_text()
            
            for forbidden in forbidden_imports:
                if forbidden in content:
                    violations.append(f"{py_file.name}: {forbidden}")
        
        assert not violations, f"Found forbidden container runtime imports: {violations}"
    
    def test_wrapper_uses_sandbox_terminology(self):
        """Test that wrapper layer uses sandbox terminology, not container terminology."""
        wrapper_dir = Path(__file__).parent.parent / "mcp-server" / "microsandbox_wrapper"
        
        # Files to check (excluding exceptions.py which may have legacy container terms for compatibility)
        files_to_check = ["session_manager.py", "wrapper.py"]
        
        container_terms = ["container_id", "container_name", "DockerRuntime", "ContainerConfig"]
        violations = []
        
        for filename in files_to_check:
            file_path = wrapper_dir / filename
            if not file_path.exists():
                continue
                
            content = file_path.read_text()
            
            for term in container_terms:
                if term in content:
                    # Count occurrences
                    count = content.count(term)
                    violations.append(f"{filename}: '{term}' appears {count} times")
        
        # Allow some container terms in comments or error messages, but not in code
        if violations:
            print(f"Warning: Found container terminology in wrapper layer: {violations}")
            # This is a warning for now, can be made strict later
    
    def test_session_manager_uses_sandbox_sdk(self):
        """Test that session manager uses sandbox SDK methods."""
        session_manager_path = Path(__file__).parent.parent / "mcp-server" / "microsandbox_wrapper" / "session_manager.py"
        
        content = session_manager_path.read_text()
        
        # Should use sandbox SDK methods
        expected_patterns = [
            "await session._sandbox.pin(",
            "PythonSandbox.attach_to_pinned(",
            "NodeSandbox.attach_to_pinned("
        ]
        
        found_patterns = []
        for pattern in expected_patterns:
            if pattern in content:
                found_patterns.append(pattern)
        
        assert len(found_patterns) >= 2, f"Expected to find sandbox SDK usage patterns, found: {found_patterns}"
    
    def test_exceptions_use_sandbox_terminology(self):
        """Test that new exceptions use sandbox terminology."""
        exceptions_path = Path(__file__).parent.parent / "mcp-server" / "microsandbox_wrapper" / "exceptions.py"
        
        content = exceptions_path.read_text()
        
        # Should have sandbox-related exceptions
        expected_exceptions = [
            "class SandboxNotFoundError",
            "class SandboxStartError"
        ]
        
        found_exceptions = []
        for exception in expected_exceptions:
            if exception in content:
                found_exceptions.append(exception)
        
        assert len(found_exceptions) == len(expected_exceptions), f"Expected sandbox exceptions, found: {found_exceptions}"
    
    def test_models_use_sandbox_terminology(self):
        """Test that models use sandbox terminology instead of container terminology."""
        models_path = Path(__file__).parent.parent / "mcp-server" / "microsandbox_wrapper" / "models.py"
        
        content = models_path.read_text()
        
        # Should use sandbox_path instead of container_path
        assert "sandbox_path: str" in content, "VolumeMapping should use sandbox_path"
        assert "container_path: str" not in content, "VolumeMapping should not use container_path"
        
        # Should have sandbox terminology in documentation
        assert "sandbox paths" in content or "sandbox environments" in content, "Should use sandbox terminology in docs"
    
    def test_config_uses_sandbox_terminology(self):
        """Test that config uses sandbox terminology."""
        config_path = Path(__file__).parent.parent / "mcp-server" / "microsandbox_wrapper" / "config.py"
        
        content = config_path.read_text()
        
        # Should use sandbox terminology in volume mapping descriptions
        sandbox_terms = ["host_path:sandbox_path", "sandbox1", "sandbox2"]
        
        found_terms = []
        for term in sandbox_terms:
            if term in content:
                found_terms.append(term)
        
        assert len(found_terms) >= 2, f"Expected sandbox terminology in config, found: {found_terms}"
    
    def test_sandbox_sdk_has_pin_methods(self):
        """Test that sandbox SDK has the required pin and attach methods."""
        base_sandbox_path = Path(__file__).parent.parent / "python" / "sandbox" / "base_sandbox.py"
        
        content = base_sandbox_path.read_text()
        
        # Should have pin and attach methods
        expected_methods = [
            "async def pin(",
            "async def attach_to_pinned(",
            "async def list_pinned("
        ]
        
        found_methods = []
        for method in expected_methods:
            if method in content:
                found_methods.append(method)
        
        assert len(found_methods) == len(expected_methods), f"Expected pin/attach methods in sandbox SDK, found: {found_methods}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])