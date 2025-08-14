#!/usr/bin/env python3
"""
Test pinned container detection.
"""

import asyncio
import sys
import os
import uuid

# Add the parent directory to the path so we can import the MCP server modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'mcp-server'))
# Also add the python directory to use our local sandbox code
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python'))

from mcp_server.server import get_or_create_wrapper

async def test_pinned_check():
    """Test that pinned containers are correctly detected."""
    
    print("🧪 Testing Pinned Container Detection")
    print("=" * 50)
    
    # Generate unique test ID
    test_id = str(uuid.uuid4())[:8]
    pinned_name = f"test_pinned_{test_id}"
    
    try:
        # Get wrapper instance
        wrapper = await get_or_create_wrapper()
        
        print("📝 Step 1: Creating session")
        # Create session
        result = await wrapper.execute_code("print('Hello from test session')")
        print(f"   Session ID: {result.session_id}")
        
        original_session_id = result.session_id
        
        print(f"📌 Step 2: Pinning sandbox as '{pinned_name}'")
        # Pin the sandbox
        pin_result = await wrapper.pin_session(original_session_id, pinned_name)
        print(f"   Result: {pin_result}")
        
        print("🔍 Step 3: Checking if container is detected as pinned")
        # Get the session to access the sandbox
        session_manager = wrapper._session_manager
        session = session_manager._sessions.get(original_session_id)
        
        if session and session._sandbox:
            container_id = session._sandbox._container_id
            runtime = session._sandbox._runtime
            
            print(f"   Container ID: {container_id}")
            
            # Check if container is pinned
            is_pinned = await runtime.is_container_pinned(container_id)
            print(f"   Is pinned: {is_pinned}")
            
            if is_pinned:
                print("✅ Container correctly detected as pinned!")
                return True
            else:
                print("❌ Container not detected as pinned!")
                return False
        else:
            print("❌ Could not access sandbox or container!")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_pinned_check())
    sys.exit(0 if success else 1)