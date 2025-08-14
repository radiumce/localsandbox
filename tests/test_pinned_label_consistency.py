#!/usr/bin/env python3
"""
Test that pinned containers have consistent labels to prevent orphan cleanup issues.
"""

import asyncio
import sys
import os
import uuid
import json

# Add the parent directory to the path so we can import the MCP server modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'mcp-server'))
# Also add the python directory to use our local sandbox code
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python'))

from mcp_server.server import get_or_create_wrapper

async def test_pinned_label_consistency():
    """Test that pinned containers have consistent localsandbox.name labels."""
    
    print("🧪 Testing Pinned Container Label Consistency")
    print("=" * 60)
    
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
        
        print("🔍 Step 3: Checking container labels")
        # Get the session to access the sandbox
        session_manager = wrapper._session_manager
        session = session_manager._sessions.get(original_session_id)
        
        if session and session._sandbox:
            container_id = session._sandbox._container_id
            runtime = session._sandbox._runtime
            
            print(f"   Container ID: {container_id}")
            
            # Get container info to check labels
            try:
                inspect_result = await runtime._run_command(["inspect", container_id], timeout=10)
                if inspect_result["returncode"] == 0:
                    container_info = json.loads(inspect_result["stdout"])[0]
                    labels = container_info.get("Config", {}).get("Labels") or {}
                    
                    print("   Container Labels:")
                    for key, value in labels.items():
                        print(f"     {key}: {value}")
                    
                    # Check critical labels
                    pinned_label = labels.get("pinned", "")
                    pinned_name_label = labels.get("pinned_name", "")
                    localsandbox_name_label = labels.get("localsandbox.name", "")
                    
                    print(f"\n   Label Analysis:")
                    print(f"     pinned: {pinned_label}")
                    print(f"     pinned_name: {pinned_name_label}")
                    print(f"     localsandbox.name: {localsandbox_name_label}")
                    
                    # Verify consistency
                    success = True
                    if pinned_label.lower() != "true":
                        print("   ❌ pinned label is not 'true'")
                        success = False
                    
                    if pinned_name_label != pinned_name:
                        print(f"   ❌ pinned_name label '{pinned_name_label}' doesn't match expected '{pinned_name}'")
                        success = False
                    
                    if localsandbox_name_label != pinned_name:
                        print(f"   ❌ localsandbox.name label '{localsandbox_name_label}' doesn't match expected '{pinned_name}'")
                        success = False
                    
                    if success:
                        print("   ✅ All labels are consistent!")
                        print("\n" + "=" * 60)
                        print("🎉 PINNED LABEL CONSISTENCY TEST PASSED!")
                        print("✅ pinned=true")
                        print(f"✅ pinned_name={pinned_name}")
                        print(f"✅ localsandbox.name={pinned_name}")
                        print("✅ Labels are consistent - orphan cleanup will work correctly")
                        return True
                    else:
                        print("\n" + "=" * 60)
                        print("❌ PINNED LABEL CONSISTENCY TEST FAILED!")
                        print("❌ Labels are inconsistent - may cause orphan cleanup issues")
                        return False
                        
                else:
                    print(f"   ❌ Failed to inspect container: {inspect_result['stderr']}")
                    return False
                    
            except Exception as e:
                print(f"   ❌ Error inspecting container: {e}")
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
    success = asyncio.run(test_pinned_label_consistency())
    sys.exit(0 if success else 1)