#!/usr/bin/env python3
"""
Pin-Sandbox End-to-End Test Runner

This script provides a convenient way to run pin-sandbox end-to-end tests
with proper environment setup and configuration.

Usage:
    python run_pin_sandbox_e2e.py [options]

Options:
    --simple        Run only the simple e2e test
    --full          Run the full comprehensive e2e test
    --all           Run all e2e tests (default)
    --timeout=N     Set session timeout in seconds (default: 8)
    --cleanup=N     Set cleanup interval in seconds (default: 3)
    --debug         Enable debug logging
    --no-docker     Skip Docker availability check
    --dry-run       Show what would be run without executing
"""

import argparse
import asyncio
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Dict, Any


class PinSandboxE2ERunner:
    """Runner for pin-sandbox end-to-end tests."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.tests_dir = Path(__file__).parent
        self.default_config = {
            'session_timeout': 8,
            'cleanup_interval': 3,
            'max_concurrent_sessions': 5,
            'log_level': 'INFO'
        }
    
    def check_prerequisites(self, skip_docker: bool = False) -> bool:
        """Check if all prerequisites are met."""
        print("🔍 Checking prerequisites...")
        
        # Check Python version
        if sys.version_info < (3, 8):
            print("❌ Python 3.8+ required")
            return False
        print(f"✅ Python {sys.version.split()[0]}")
        
        # Check MCP client
        try:
            import mcp
            print("✅ MCP client available")
        except ImportError:
            print("❌ MCP client not available. Install with: pip install mcp")
            return False
        
        # Check pytest
        try:
            import pytest
            print("✅ pytest available")
        except ImportError:
            print("❌ pytest not available. Install with: pip install pytest pytest-asyncio")
            return False
        
        # Check Docker (if not skipped)
        if not skip_docker:
            try:
                result = subprocess.run(['docker', 'ps'], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    print("✅ Docker available")
                else:
                    print("❌ Docker not available or not running")
                    return False
            except (subprocess.TimeoutExpired, FileNotFoundError):
                print("❌ Docker command not found or not responding")
                return False
        else:
            print("⚠️  Docker check skipped")
        
        # Check MCP server files
        server_paths = [
            self.project_root / "mcp-server" / "mcp_server" / "main.py",
            self.project_root / "mcp-server" / "main.py"
        ]
        
        server_found = False
        for server_path in server_paths:
            if server_path.exists():
                print(f"✅ MCP server found: {server_path}")
                server_found = True
                break
        
        if not server_found:
            print("❌ MCP server main.py not found")
            print("   Looked in:")
            for path in server_paths:
                print(f"     {path}")
            return False
        
        print("✅ All prerequisites met")
        return True
    
    def prepare_environment(self, config: Dict[str, Any]) -> Dict[str, str]:
        """Prepare environment variables for testing."""
        env = os.environ.copy()
        
        # Set test configuration
        env.update({
            'SESSION_TIMEOUT': str(config['session_timeout']),
            'CLEANUP_INTERVAL': str(config['cleanup_interval']),
            'MAX_CONCURRENT_SESSIONS': str(config['max_concurrent_sessions']),
            'LOG_LEVEL': config['log_level'],
            'DEFAULT_EXECUTION_TIMEOUT': '30',
            'SANDBOX_START_TIMEOUT': '60'
        })
        
        # Ensure Docker socket is available
        if 'DOCKER_HOST' not in env:
            env['DOCKER_HOST'] = 'unix:///var/run/docker.sock'
        
        return env
    
    async def run_test(self, test_file: str, config: Dict[str, Any], dry_run: bool = False) -> bool:
        """Run a specific test file."""
        print(f"🚀 Running test: {test_file}")
        print(f"   Session timeout: {config['session_timeout']}s")
        print(f"   Cleanup interval: {config['cleanup_interval']}s")
        print(f"   Log level: {config['log_level']}")
        
        if dry_run:
            print("   (DRY RUN - not actually executing)")
            return True
        
        # Prepare environment
        env = self.prepare_environment(config)
        
        # Prepare command
        test_path = self.tests_dir / test_file
        if not test_path.exists():
            print(f"❌ Test file not found: {test_path}")
            return False
        
        # Run with pytest
        cmd = [
            sys.executable, '-m', 'pytest',
            str(test_path),
            '-v', '-s',
            '--tb=short',
            f'--timeout={config["session_timeout"] * 10}'  # Overall test timeout
        ]
        
        print(f"   Command: {' '.join(cmd)}")
        print("   " + "="*50)
        
        start_time = time.time()
        
        try:
            # Run the test
            process = await asyncio.create_subprocess_exec(
                *cmd,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=self.project_root
            )
            
            # Stream output in real-time
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                print(line.decode().rstrip())
            
            # Wait for completion
            await process.wait()
            
            duration = time.time() - start_time
            
            if process.returncode == 0:
                print("   " + "="*50)
                print(f"✅ Test passed in {duration:.1f}s")
                return True
            else:
                print("   " + "="*50)
                print(f"❌ Test failed in {duration:.1f}s (exit code: {process.returncode})")
                return False
                
        except Exception as e:
            duration = time.time() - start_time
            print("   " + "="*50)
            print(f"❌ Test error in {duration:.1f}s: {e}")
            return False
    
    async def run_direct_test(self, test_file: str, config: Dict[str, Any], dry_run: bool = False) -> bool:
        """Run test directly as Python script."""
        print(f"🚀 Running test directly: {test_file}")
        
        if dry_run:
            print("   (DRY RUN - not actually executing)")
            return True
        
        # Prepare environment
        env = self.prepare_environment(config)
        
        # Prepare command
        test_path = self.tests_dir / test_file
        if not test_path.exists():
            print(f"❌ Test file not found: {test_path}")
            return False
        
        cmd = [sys.executable, str(test_path)]
        
        print(f"   Command: {' '.join(cmd)}")
        print("   " + "="*50)
        
        start_time = time.time()
        
        try:
            # Run the test
            process = await asyncio.create_subprocess_exec(
                *cmd,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=self.tests_dir
            )
            
            # Stream output in real-time
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                print(line.decode().rstrip())
            
            # Wait for completion
            await process.wait()
            
            duration = time.time() - start_time
            
            if process.returncode == 0:
                print("   " + "="*50)
                print(f"✅ Test passed in {duration:.1f}s")
                return True
            else:
                print("   " + "="*50)
                print(f"❌ Test failed in {duration:.1f}s (exit code: {process.returncode})")
                return False
                
        except Exception as e:
            duration = time.time() - start_time
            print("   " + "="*50)
            print(f"❌ Test error in {duration:.1f}s: {e}")
            return False
    
    async def run_tests(self, test_files: List[str], config: Dict[str, Any], 
                       dry_run: bool = False, use_pytest: bool = True) -> bool:
        """Run multiple tests."""
        print("🎯 Pin-Sandbox End-to-End Test Runner")
        print("="*60)
        
        if not self.check_prerequisites(skip_docker=dry_run):
            return False
        
        print("\n📋 Test Configuration:")
        for key, value in config.items():
            print(f"   {key}: {value}")
        
        print(f"\n📝 Tests to run ({len(test_files)}):")
        for test_file in test_files:
            print(f"   - {test_file}")
        
        if dry_run:
            print("\n⚠️  DRY RUN MODE - Tests will not actually execute")
        
        print("\n" + "="*60)
        
        # Run tests
        results = []
        for i, test_file in enumerate(test_files, 1):
            print(f"\n[{i}/{len(test_files)}] " + "="*40)
            
            if use_pytest:
                success = await self.run_test(test_file, config, dry_run)
            else:
                success = await self.run_direct_test(test_file, config, dry_run)
            
            results.append((test_file, success))
            
            if not success and not dry_run:
                print(f"\n⚠️  Test {test_file} failed. Continue with remaining tests? (y/n)")
                if input().lower().strip() != 'y':
                    break
        
        # Summary
        print("\n" + "="*60)
        print("📊 Test Results Summary:")
        
        passed = sum(1 for _, success in results if success)
        total = len(results)
        
        for test_file, success in results:
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"   {status} {test_file}")
        
        print(f"\nOverall: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed!")
            return True
        else:
            print("❌ Some tests failed")
            return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run pin-sandbox end-to-end tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_pin_sandbox_e2e.py --simple
  python run_pin_sandbox_e2e.py --timeout=5 --cleanup=2 --debug
  python run_pin_sandbox_e2e.py --all --dry-run
        """
    )
    
    # Test selection
    test_group = parser.add_mutually_exclusive_group()
    test_group.add_argument('--simple', action='store_true',
                           help='Run only the simple e2e test')
    test_group.add_argument('--full', action='store_true',
                           help='Run the full comprehensive e2e test')
    test_group.add_argument('--all', action='store_true', default=True,
                           help='Run all e2e tests (default)')
    
    # Configuration
    parser.add_argument('--timeout', type=int, default=8,
                       help='Session timeout in seconds (default: 8)')
    parser.add_argument('--cleanup', type=int, default=3,
                       help='Cleanup interval in seconds (default: 3)')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug logging')
    
    # Execution options
    parser.add_argument('--no-docker', action='store_true',
                       help='Skip Docker availability check')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be run without executing')
    parser.add_argument('--direct', action='store_true',
                       help='Run tests directly instead of using pytest')
    
    args = parser.parse_args()
    
    # Determine which tests to run
    if args.simple:
        test_files = ['test_pin_sandbox_e2e_simple.py']
    elif args.full:
        test_files = ['test_pin_sandbox_end_to_end.py']
    else:  # --all or default
        test_files = [
            'test_pin_sandbox_e2e_simple.py',
            'test_pin_sandbox_end_to_end.py'
        ]
    
    # Prepare configuration
    config = {
        'session_timeout': args.timeout,
        'cleanup_interval': args.cleanup,
        'max_concurrent_sessions': 5,
        'log_level': 'DEBUG' if args.debug else 'INFO'
    }
    
    # Run tests
    runner = PinSandboxE2ERunner()
    
    try:
        success = asyncio.run(runner.run_tests(
            test_files, 
            config, 
            dry_run=args.dry_run,
            use_pytest=not args.direct
        ))
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()