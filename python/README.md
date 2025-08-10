# LocalSandbox Python SDK

A Python SDK for running code in local Docker containers, providing a secure and isolated execution environment.

## Installation

```bash
# Install from PyPI
pip install localsandbox

# Or install from source
git clone https://github.com/localsandbox/localsandbox.git
cd localsandbox/python
pip install -e .
```

## Requirements

- Python 3.8+
- Docker or Podman installed and running
- Sufficient permissions to run containers

## Usage

### Running Code

```python
import asyncio
from localsandbox import PythonSandbox

async def main():
    # Using the context manager (automatically starts and stops the sandbox)
    async with PythonSandbox.create() as sandbox:
        # Run code in the sandbox
        await sandbox.run("name = 'Python'")
        execution = await sandbox.run("print(f'Hello {name}!')")

        # Get the output
        output = await execution.output()
        print(output)  # prints Hello Python!

# Run the async main function
asyncio.run(main())
```

### Volume Mapping

Share files between your host system and the sandbox using volume mappings:

```python
import asyncio
from localsandbox import PythonSandbox

async def main():
    # Create sandbox with volume mappings
    async with PythonSandbox.create(
        volumes=["/path/on/host:/path/in/sandbox", "./local:/shared"]
    ) as sandbox:
        # Write a file from sandbox to host
        await sandbox.run("""
with open("/shared/hello.txt", "w") as f:
    f.write("Hello from sandbox!")
print("File written to shared volume")
""")
        
        # Read a file from host in sandbox
        execution = await sandbox.run("""
with open("/path/in/sandbox/data.txt", "r") as f:
    content = f.read()
print(f"Read from host: {content}")
""")
        
        print(await execution.output())

asyncio.run(main())
```

### Advanced Configuration

```python
import asyncio
from localsandbox import PythonSandbox

async def main():
    # Create sandbox with custom configuration
    async with PythonSandbox.create(
        name="my-custom-sandbox",
        image="python:3.11-slim",            # Custom image
        memory=1024,                         # Memory in MB
        cpus=2.0,                           # CPU cores
        timeout=300.0,                      # Start timeout in seconds
        volumes=[                           # Volume mappings
            "/home/user/data:/data",
            "./output:/results"
        ]
    ) as sandbox:
        # Your code here
        execution = await sandbox.run("print('Custom sandbox ready!')")
        print(await execution.output())

asyncio.run(main())
```

### Executing Shell Commands

```python
import asyncio
from localsandbox import PythonSandbox

async def main():
    async with PythonSandbox.create() as sandbox:
        # Execute a command with arguments
        execution = await sandbox.command.run("echo", ["Hello", "World"])

        # Get the command output
        print(await execution.output())  # prints "Hello World"

        # Check the exit code and success status
        print(f"Exit code: {execution.exit_code}")
        print(f"Success: {execution.success}")

        # Handle command errors
        error_cmd = await sandbox.command.run("ls", ["/nonexistent"])
        print(await error_cmd.error())  # prints error message

        # Specify a timeout (in seconds)
        try:
            await sandbox.command.run("sleep", ["10"], timeout=2)
        except RuntimeError as e:
            print(f"Command timed out: {e}")

asyncio.run(main())
```

## Configuration

LocalSandbox can be configured using environment variables:

### Container Runtime

- `CONTAINER_RUNTIME`: Container runtime to use (`docker` or `podman`, default: `docker`)

### Default Images

- `LOCALSANDBOX_PYTHON_IMAGE`: Default Python container image (default: `python:3.11-slim`)
- `LOCALSANDBOX_NODE_IMAGE`: Default Node.js container image (default: `node:18-slim`)

### Resource Limits

- `LOCALSANDBOX_DEFAULT_MEMORY`: Default memory limit in MB (default: `512`)
- `LOCALSANDBOX_DEFAULT_CPU`: Default CPU limit (default: `1.0`)
- `LOCALSANDBOX_DEFAULT_TIMEOUT`: Default command execution timeout in seconds (default: `30`)

### Container Configuration

- `LOCALSANDBOX_WORKING_DIR`: Default working directory inside containers (default: `/workspace`)

### Example Configuration

Create a `.env` file in your project root:

```bash
# Container Runtime Configuration
CONTAINER_RUNTIME=docker

# Default Container Images
LOCALSANDBOX_PYTHON_IMAGE=python:3.11-slim
LOCALSANDBOX_NODE_IMAGE=node:18-slim

# Default Resource Limits
LOCALSANDBOX_DEFAULT_MEMORY=1024
LOCALSANDBOX_DEFAULT_CPU=2.0
LOCALSANDBOX_DEFAULT_TIMEOUT=60

# Container Configuration
LOCALSANDBOX_WORKING_DIR=/workspace
```

## Examples

### Volume Mapping Examples

Volume mappings allow you to share files between your host filesystem and the sandbox. The format is `"host_path:container_path"`.

**Supported formats:**
- Absolute paths: `"/home/user/data:/data"`
- Relative paths: `"./local:/shared"` (relative to current directory)
- Multiple mappings: `["/data:/data", "/config:/config", "./output:/results"]`

**Example use cases:**
- Share configuration files with the sandbox
- Process data files from your host system
- Save sandbox output to your local filesystem
- Create persistent storage for sandbox sessions

### Using Different Container Runtimes

```python
import asyncio
from localsandbox import PythonSandbox

async def main():
    # Use Docker (default)
    async with PythonSandbox.create(container_runtime="docker") as sandbox:
        execution = await sandbox.run("print('Running with Docker')")
        print(await execution.output())
    
    # Use Podman
    async with PythonSandbox.create(container_runtime="podman") as sandbox:
        execution = await sandbox.run("print('Running with Podman')")
        print(await execution.output())

asyncio.run(main())
```

### Error Handling

```python
import asyncio
from localsandbox import PythonSandbox

async def main():
    try:
        async with PythonSandbox.create() as sandbox:
            # This will raise an exception
            execution = await sandbox.run("raise ValueError('Test error')")
            print(await execution.output())
    except RuntimeError as e:
        print(f"Sandbox error: {e}")

asyncio.run(main())
```

## License

[Apache 2.0](https://www.apache.org/licenses/LICENSE-2.0)