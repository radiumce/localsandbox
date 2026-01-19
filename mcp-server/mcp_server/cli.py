"""
LocalSandbox CLI (lsb)

This module provides the main entry point for the 'lsb' command line interface.
Supported commands:
  - start: Start the LocalSandbox server
  - stop: Stop the running LocalSandbox server
"""

import argparse
import os
import sys
import signal
import psutil
from pathlib import Path
from mcp_server.scripts import (
    find_env_file,
    load_env_file,
    check_runtime,
    setup_directories,
    pull_images,
)

PID_FILE = Path("logs/server.pid")

def save_pid(pid):
    """Save the process ID to a file."""
    os.makedirs(PID_FILE.parent, exist_ok=True)
    with open(PID_FILE, "w") as f:
        f.write(str(pid))

def get_pid():
    """Get the process ID from file"""
    if PID_FILE.exists():
        try:
            return int(PID_FILE.read_text().strip())
        except ValueError:
            return None
    return None

def remove_pid():
    """Remove the PID file."""
    if PID_FILE.exists():
        PID_FILE.unlink()

def start_server(args):
    """Start the LocalSandbox server."""
    print("🚀 Starting LocalSandbox Server (lsb)...")

    # Load environment
    env_file = args.env_file or find_env_file()
    if env_file:
        load_env_file(env_file)
        print(f"✓ Environment loaded from: {env_file}")
    else:
        print("⚠️  No .env.local file found, using default configuration")

    # Check runtime (Docker/Podman)
    runtime_cmd = (os.getenv('CONTAINER_RUNTIME', 'docker') or 'docker').strip().lower()
    if not args.skip_runtime_check:
        if not check_runtime(runtime_cmd):
            print(f"❌ {runtime_cmd} is not available. Please install it.")
            sys.exit(1)
        print(f"✓ {runtime_cmd} is running")

    # Setup directories
    setup_directories()
    
    # Pull images
    if not args.skip_pull:
        if not pull_images(runtime_cmd):
            print("❌ Failed to pull required images")
            sys.exit(1)

    # Add python module path
    current_dir = Path.cwd()
    python_dir = current_dir / "python"
    if python_dir.exists():
        python_path = os.environ.get('PYTHONPATH', '')
        os.environ['PYTHONPATH'] = f"{python_dir}:{python_path}" if python_path else str(python_dir)

    print("\n📋 Server Configuration:")
    host = os.getenv('MCP_SERVER_HOST', 'localhost')
    port = os.getenv('MCP_SERVER_PORT', '8775')
    print(f"  URL: http://{host}:{port}")
    print(f"  Logs: logs/server.log")

    save_pid(os.getpid())
    
    try:
        from mcp_server.main import start_mcp_server
        
        host = os.getenv('MCP_SERVER_HOST', 'localhost')
        port = int(os.getenv('MCP_SERVER_PORT', '8775'))
        enable_cors = os.getenv('MCP_ENABLE_CORS', 'false').lower() == 'true'
        
        start_mcp_server(host, port, enable_cors)
        
    except KeyboardInterrupt:
        print("\n👋 Server stopped")
    finally:
        remove_pid()

def stop_server(args):
    """Stop the running server."""
    pid = get_pid()
    if not pid:
        print("⚠️  No PID file found. Is the server running?")
        # Try to find by name maybe?
        return

    print(f"🛑 Stopping server (PID: {pid})...")
    try:
        process = psutil.Process(pid)
        process.terminate()
        try:
            process.wait(timeout=5)
            print("✓ Server stopped successfully")
        except psutil.TimeoutExpired:
            print("⚠️  Server did not stop gracefully, forcing kill...")
            process.kill()
            print("✓ Server killed")
    except psutil.NoSuchProcess:
        print("⚠️  Process not found (already stopped?)")
    except Exception as e:
        print(f"❌ Error stopping server: {e}")
    finally:
        remove_pid()

def main():
    parser = argparse.ArgumentParser(description="LocalSandbox CLI (lsb)")
    # Global arguments
    parser.add_argument("--env-file", dest="global_env_file", help="Path to .env file (global)")
    
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Start command
    start_parser = subparsers.add_parser("start", help="Start the server")
    start_parser.add_argument("--env-file", dest="local_env_file", help="Path to .env file (command specific)")
    start_parser.add_argument("--skip-runtime-check", action="store_true", help="Skip container runtime check")
    start_parser.add_argument("--skip-pull", action="store_true", help="Skip image pulling")

    # Stop command
    stop_parser = subparsers.add_parser("stop", help="Stop the server")

    args = parser.parse_args()

    # Unify env_file argument
    args.env_file = getattr(args, 'local_env_file', None) or args.global_env_file

    if args.command == "start":
        start_server(args)
    elif args.command == "stop":
        stop_server(args)

if __name__ == "__main__":
    main()
