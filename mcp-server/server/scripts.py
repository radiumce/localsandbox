"""
MCP Server Scripts Module

This module provides command-line scripts for starting the MCP server
with different configurations, including Docker-based sandbox support.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def find_env_file():
    """Find the .env.local file in the package or current directory."""
    # Try current directory first
    current_dir = Path.cwd()
    env_file = current_dir / ".env.local"
    if env_file.exists():
        return str(env_file)
    
    # Try legacy .env.docker in current directory for backward compatibility
    env_file = current_dir / ".env.docker"
    if env_file.exists():
        return str(env_file)
    
    # Try mcp-server subdirectory for legacy support
    mcp_server_dir = current_dir / "mcp-server"
    env_file = mcp_server_dir / ".env.docker"
    if env_file.exists():
        return str(env_file)
    
    # Try package installation directory
    try:
        import server
        package_dir = Path(server.__file__).parent.parent
        env_file = package_dir / ".env.local"
        if env_file.exists():
            return str(env_file)
    except ImportError:
        pass
    
    return None


def load_env_file(env_file_path):
    """Load environment variables from .env file."""
    if not env_file_path or not os.path.exists(env_file_path):
        return
    
    print(f"Loading environment from: {env_file_path}")
    
    with open(env_file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                # Remove quotes if present
                value = value.strip('"\'')
                os.environ[key] = value


def check_runtime(runtime_cmd: str):
    """Check if the configured container runtime is available and running."""
    try:
        subprocess.run([runtime_cmd, 'info'],
                       stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL,
                       check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def setup_directories():
    """Create necessary directories for Docker sandbox."""
    directories = [
        "./tmp/mcp-docker",
        "./data", 
        "./logs",
        "/tmp/mcp-sandbox"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
    
    # Create sample README in shared directory
    readme_path = "/tmp/mcp-sandbox/README.txt"
    if not os.path.exists(readme_path):
        with open(readme_path, 'w') as f:
            f.write("""MCP Docker Sandbox Shared Directory

This directory is shared between the host and Docker containers.
- Host path: /tmp/mcp-sandbox
- Container path: /workspace

You can:
1. Create files here and access them in the sandbox
2. Create files in the sandbox and see them here
3. Test Docker volume mapping functionality

Example usage in sandbox:
  with open('/workspace/test.txt', 'w') as f:
      f.write('Hello from Docker sandbox!')
""")


def pull_images(runtime_cmd: str):
    """Ensure required images are present for the selected container runtime."""
    python_image = os.getenv('LOCALSANDBOX_PYTHON_IMAGE', 'python:3.11-slim')
    node_image = os.getenv('LOCALSANDBOX_NODE_IMAGE', 'node:18-slim')

    images = [python_image, node_image]

    for image in images:
        print(f"Checking {runtime_cmd} image: {image}")
        try:
            subprocess.run([runtime_cmd, 'image', 'inspect', image],
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL,
                           check=True)
            print(f"✓ Image {image} is available")
        except subprocess.CalledProcessError:
            print(f"Pulling image: {image}")
            try:
                subprocess.run([runtime_cmd, 'pull', image], check=True)
                print(f"✓ Image {image} pulled successfully")
            except subprocess.CalledProcessError as e:
                print(f"❌ Failed to pull image {image}: {e}")
                return False

    return True


def start_docker_server():
    """Start MCP server with Docker-based sandbox configuration."""
    parser = argparse.ArgumentParser(
        description="Start MCP Server with Docker-based sandbox",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument(
        "--env-file",
        type=str,
        default=None,
        help="Path to .env.local file (auto-detected if not specified)",
    )
    
    parser.add_argument(
        "--skip-docker-check",
        action="store_true",
        help="Skip Docker availability check",
    )
    
    parser.add_argument(
        "--skip-image-pull",
        action="store_true", 
        help="Skip Docker image pulling",
    )
    
    args = parser.parse_args()
    
    print("🚀 Starting LocalSandbox MCP Server")
    
    # Find and load environment file
    env_file = args.env_file or find_env_file()
    if env_file:
        load_env_file(env_file)
        print(f"✓ Environment loaded from: {env_file}")
    else:
        print("⚠️  No .env.local file found, using default configuration")
    
    # Determine runtime command from environment (default: docker)
    runtime_cmd = (os.getenv('CONTAINER_RUNTIME', 'docker') or 'docker').strip().lower()
    
    # Check container runtime availability
    if not args.skip_docker_check:
        if not check_runtime(runtime_cmd):
            print(f"❌ {runtime_cmd} is not available or not running")
            print(f"Please install {runtime_cmd} and ensure it's running")
            sys.exit(1)
        print(f"✓ {runtime_cmd} is available and running")
    
    # Setup directories
    setup_directories()
    print("✓ Directories setup complete")
    
    # Pull required images for the selected runtime
    if not args.skip_image_pull:
        if not pull_images(runtime_cmd):
            print("❌ Failed to pull required images")
            sys.exit(1)
    
    # Add sandbox package to Python path
    current_dir = Path.cwd()
    python_dir = current_dir / "python"
    if python_dir.exists():
        python_path = os.environ.get('PYTHONPATH', '')
        if python_path:
            os.environ['PYTHONPATH'] = f"{python_dir}:{python_path}"
        else:
            os.environ['PYTHONPATH'] = str(python_dir)
        print("✓ Python path updated to include sandbox package")
    
    # Display configuration
    print("\n📋 Configuration:")
    print(f"  Server: http://{os.getenv('MCP_SERVER_HOST', 'localhost')}:{os.getenv('MCP_SERVER_PORT', '8775')}")
    print(f"  CORS: {os.getenv('MCP_ENABLE_CORS', 'false')}")
    print(f"  Max Sessions: {os.getenv('MSB_MAX_SESSIONS', '5')}")
    print(f"  Log Level: {os.getenv('MSB_LOG_LEVEL', 'DEBUG')}")
    print(f"  Container Runtime: {os.getenv('CONTAINER_RUNTIME', 'docker')}")
    print(f"  Python Image: {os.getenv('LOCALSANDBOX_PYTHON_IMAGE', 'python:3.11-slim')}")
    print(f"  Node Image: {os.getenv('LOCALSANDBOX_NODE_IMAGE', 'node:18-slim')}")
    
    print("\n🎯 Starting MCP Server...")
    print("Press Ctrl+C to stop")
    
    # Import and run the main server
    try:
        from server.main import main
        
        # Override sys.argv to pass the correct arguments
        sys.argv = [
            'mcp-server',
            '--port', os.getenv('MCP_SERVER_PORT', '8775'),
            '--host', os.getenv('MCP_SERVER_HOST', 'localhost'),
        ]
        
        if os.getenv('MCP_ENABLE_CORS', 'false').lower() == 'true':
            sys.argv.append('--enable-cors')
        
        main()
        
    except KeyboardInterrupt:
        print("\n👋 Server stopped")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    start_docker_server()