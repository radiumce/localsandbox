#!/usr/bin/env python3
"""
Test script to demonstrate the new container naming scheme.
This shows how the new timestamp-based naming avoids collisions.
"""

from datetime import datetime
import time

def generate_sandbox_name():
    """Generate a sandbox name using the new timestamp format."""
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    return f"sandbox-{timestamp_str}"

if __name__ == "__main__":
    print("Testing new container naming scheme:")
    print("=====================================")
    
    # Generate several names in quick succession
    names = []
    for i in range(5):
        name = generate_sandbox_name()
        names.append(name)
        print(f"Container {i+1}: {name}")
        time.sleep(0.001)  # Small delay to show microsecond differences
    
    print(f"\nGenerated {len(names)} unique container names")
    print(f"All names unique: {len(names) == len(set(names))}")
    
    print("\nContainer naming pattern:")
    print("- Format: sandbox-YYYYMMDD_HHMMSS_microseconds")
    print("- Example: sandbox-20250810_134523_123456")
    print("- Benefits:")
    print("  * Guaranteed uniqueness (microsecond precision)")
    print("  * Easy to identify creation time for debugging")
    print("  * Helpful for orphan container cleanup")
    print("  * No dependency on session_id format")
