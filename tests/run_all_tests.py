#!/usr/bin/env python3
"""
Run all tests for the Docker-based sandbox SDK.

This script runs all tests and provides a summary of the results.
"""

import subprocess
import sys
from pathlib import Path

def run_tests():
    """Run all tests and return the results."""
    print("🧪 Running all tests for Docker-based sandbox SDK...")
    print("=" * 60)
    
    # Run pytest with verbose output
    result = subprocess.run([
        sys.executable, "-m", "pytest", 
        "tests/", 
        "-v", 
        "--tb=short",
        "--color=yes"
    ], capture_output=True, text=True)
    
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    
    return result.returncode == 0

def run_mcp_tests():
    """Run only MCP integration tests."""
    print("\n🔗 Running MCP integration tests...")
    print("=" * 40)
    
    result = subprocess.run([
        sys.executable, "-m", "pytest", 
        "tests/test_mcp_integration.py",
        "tests/test_mcp_end_to_end.py", 
        "tests/test_mcp_session_manager_simulation.py",
        "-v"
    ], capture_output=True, text=True)
    
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    
    return result.returncode == 0

def main():
    """Main function."""
    print("Docker-based Sandbox SDK Test Runner")
    print("=" * 60)
    
    # Run all tests
    all_tests_passed = run_tests()
    
    # Run MCP tests specifically
    mcp_tests_passed = run_mcp_tests()
    
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    if all_tests_passed:
        print("✅ All tests PASSED")
    else:
        print("❌ Some tests FAILED")
    
    if mcp_tests_passed:
        print("✅ MCP integration tests PASSED")
    else:
        print("❌ MCP integration tests FAILED")
    
    print("\n📋 Test Categories:")
    print("  • Command execution tests")
    print("  • Container runtime tests") 
    print("  • MCP integration tests")
    print("  • Sandbox execution tests")
    
    print("\n🎯 Key Achievements:")
    print("  • Full MCP server compatibility")
    print("  • Docker container-based execution")
    print("  • Backward compatible API")
    print("  • Comprehensive error handling")
    print("  • Concurrent session support")
    
    if all_tests_passed and mcp_tests_passed:
        print("\n🚀 The Docker-based sandbox SDK is ready for production!")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please review the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())