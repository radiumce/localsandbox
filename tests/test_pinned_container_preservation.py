#!/usr/bin/env python3
"""
Test that pinned containers are preserved when sessions are stopped.
"""

import asyncio
import sys
import os
import time
import uuid

# Add the parent directory to the path so we can import the MCP server modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'mcp-server'))
# Also add the python directory to use our local sandbox code
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python'))

from mcp_server.server import get_or_create_wrapper

async def test_pinned_container_preservation():
    """Test that pinned containers are not deleted when sessions are stopped."""
    
    print("🧪 Testing Pinned Container Preservation")
    print("=" * 60)
    
    # Generate unique test ID
    test_id = str(uuid.uuid4())[:8]
    pinned_name = f"test_pinned_{test_id}"
    
    try:
        # Get wrapper instance
        wrapper = await get_or_create_wrapper()
        
        print("📝 Step 1: Creating session and writing test file")
        # Create session and write a test file
        result = await wrapper.execute_code(f"""
import os
with open('/workspace/test_file.txt', 'w') as f:
    f.write('Test file for pinned container preservation - ID: {test_id}')
print(f"Created file: /workspace/test_file.txt")
print(f"Content: Test file for pinned container preservation - ID: {test_id}")
""")
        
        print(f"   Session ID: {result.session_id}")
        print(f"   Result: {result.stdout}")
        
        original_session_id = result.session_id
        
        print(f"📌 Step 2: Pinning sandbox as '{pinned_name}'")
        # Pin the sandbox
        pin_result = await wrapper.pin_session(original_session_id, pinned_name)
        print(f"   Result: {pin_result}")
        
        print("🔍 Step 3: Verifying file exists after pin")
        # Verify file exists
        verify_result = await wrapper.execute_code("""
import os
if os.path.exists('/workspace/test_file.txt'):
    with open('/workspace/test_file.txt', 'r') as f:
        content = f.read()
    print(f"✅ File exists: /workspace/test_file.txt")
    print(f"Content: {content}")
else:
    print("❌ File does not exist")
""", session_id=original_session_id)
        
        print(f"   {verify_result.stdout}")
        
        print("🛑 Step 4: Stopping the session")
        # Stop the session
        stop_result = await wrapper.stop_session(original_session_id)
        print(f"   Stop result: {stop_result}")
        
        # Wait a moment for cleanup
        await asyncio.sleep(2)
        
        print(f"🔗 Step 5: Attaching to pinned sandbox '{pinned_name}'")
        # Try to attach to the pinned sandbox
        try:
            attach_result = await wrapper.attach_to_pinned_sandbox(pinned_name)
            print(f"   Attach result: {attach_result}")
            
            # The attach result is the session ID directly
            new_session_id = attach_result.strip()
                
        except Exception as e:
            print(f"❌ Failed to attach to pinned sandbox: {e}")
            return False
        
        print("🔍 Step 6: Verifying file still exists after attach")
        # Verify file still exists after attach
        final_verify_result = await wrapper.execute_code("""
import os
if os.path.exists('/workspace/test_file.txt'):
    with open('/workspace/test_file.txt', 'r') as f:
        content = f.read()
    print(f"✅ File exists: /workspace/test_file.txt")
    print(f"Content: {content}")
    print("✅ Container was preserved during session stop!")
else:
    print("❌ File does not exist - container was deleted!")
""", session_id=new_session_id)
        
        print(f"   {final_verify_result.stdout}")
        
        # Check if test passed
        if "✅ Container was preserved during session stop!" in final_verify_result.stdout:
            print("\n" + "=" * 60)
            print("🎉 PINNED CONTAINER PRESERVATION TEST PASSED!")
            print("✅ Pinned container was preserved when session was stopped")
            print("✅ File persistence verified after session stop and attach")
            return True
        else:
            print("\n" + "=" * 60)
            print("❌ PINNED CONTAINER PRESERVATION TEST FAILED!")
            print("❌ Container was deleted when session was stopped")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_pinned_container_preservation())
    sys.exit(0 if success else 1)