#!/usr/bin/env python3
"""
Test runner script for localsandbox integration tests.

This script provides a convenient way to run different types of tests
with appropriate configurations and options.
"""

import argparse
import subprocess
import sys
from pathlib import Path


def run_command(cmd, description):
    """Run a command and handle the result."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(cmd, check=True)
        print(f"\n✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ {description} failed with exit code {e.returncode}")
        return False
    except FileNotFoundError:
        print(f"\n❌ pytest not found. Please install pytest: pip install pytest pytest-asyncio")
        return False


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(
        description="Run localsandbox integration tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_tests.py                    # Run all unit tests
  python run_tests.py --integration      # Run all tests including integration
  python run_tests.py --unit-only        # Run only unit tests
  python run_tests.py --container        # Run only container runtime tests
  python run_tests.py --sandbox          # Run only sandbox execution tests
  python run_tests.py --command          # Run only command execution tests
  python run_tests.py --verbose          # Run with verbose output
  python run_tests.py --coverage         # Run with coverage report
        """
    )
    
    # Test selection options
    parser.add_argument(
        "--integration", 
        action="store_true",
        help="Include integration tests (requires Docker)"
    )
    parser.add_argument(
        "--unit-only", 
        action="store_true",
        help="Run only unit tests (no Docker required)"
    )
    parser.add_argument(
        "--container", 
        action="store_true",
        help="Run only container runtime tests"
    )
    parser.add_argument(
        "--sandbox", 
        action="store_true",
        help="Run only sandbox execution tests"
    )
    parser.add_argument(
        "--command", 
        action="store_true",
        help="Run only command execution tests"
    )
    
    # Output options
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Run with coverage report"
    )
    parser.add_argument(
        "--html-coverage",
        action="store_true",
        help="Generate HTML coverage report"
    )
    
    # Pytest options
    parser.add_argument(
        "--pytest-args",
        nargs=argparse.REMAINDER,
        help="Additional arguments to pass to pytest"
    )
    
    args = parser.parse_args()
    
    # Change to tests directory
    tests_dir = Path(__file__).parent
    original_cwd = Path.cwd()
    
    try:
        # Build pytest command
        cmd = ["python", "-m", "pytest"]
        
        # Add configuration
        cmd.extend(["-c", "pytest.ini"])
        
        # Test selection
        if args.unit_only:
            cmd.extend(["-m", "unit"])
        elif args.integration:
            # Run all tests including integration
            pass
        else:
            # Default: run unit tests only
            cmd.extend(["-m", "not integration"])
        
        # Specific test modules
        if args.container:
            cmd.append("test_container_runtime.py")
        elif args.sandbox:
            cmd.append("test_sandbox_execution.py")
        elif args.command:
            cmd.append("test_command_execution.py")
        
        # Output options
        if args.verbose:
            cmd.append("-v")
        
        # Coverage options
        if args.coverage or args.html_coverage:
            cmd.extend(["--cov=python.sandbox"])
            cmd.extend(["--cov-report=term-missing"])
            
            if args.html_coverage:
                cmd.extend(["--cov-report=html"])
        
        # Additional pytest arguments
        if args.pytest_args:
            cmd.extend(args.pytest_args)
        
        # Run the tests
        success = run_command(cmd, "Integration Tests")
        
        if success:
            print(f"\n🎉 All tests passed!")
            if args.html_coverage:
                print(f"📊 Coverage report generated in htmlcov/index.html")
        else:
            print(f"\n💥 Some tests failed!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print(f"\n⚠️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error running tests: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()