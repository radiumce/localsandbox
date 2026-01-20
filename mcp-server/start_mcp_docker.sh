#!/bin/bash
#
# MCP Server Startup Script for Docker-based Sandbox
# 
# This script starts the MCP server using the new Docker-based sandbox implementation
# instead of the old microsandbox server.
#

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Detect Python command
if command -v python &> /dev/null && python -c "import mcp" 2>/dev/null; then
    PYTHON_CMD="python"
elif command -v python3 &> /dev/null && python3 -c "import mcp" 2>/dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
elif command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
else
    log_error "Python is not installed or not in PATH"
    exit 1
fi

log_info "Starting MCP Server with Docker-based Sandbox"
log_info "Using Python command: $PYTHON_CMD"

# =============================================================================
# LOAD DOCKER CONFIGURATION
# =============================================================================

# Load Docker-specific environment configuration
if [[ -f ".env.docker" ]]; then
    log_info "Loading Docker-based sandbox configuration from .env.docker"
    set -a && source ".env.docker" && set +a
    log_info "✓ Docker configuration loaded"
else
    log_error ".env.docker file not found. Please create it with Docker sandbox configuration."
    exit 1
fi

# =============================================================================
# SETUP DEVELOPMENT ENVIRONMENT
# =============================================================================

# Create development directories
mkdir -p "./tmp/mcp-docker"
mkdir -p "./data"
mkdir -p "./logs"

# Create shared directory for Docker containers
mkdir -p "/tmp/mcp-sandbox"

# Create sample files for testing
if [[ ! -f "/tmp/mcp-sandbox/README.txt" ]]; then
    cat > "/tmp/mcp-sandbox/README.txt" << EOF
MCP Docker Sandbox Shared Directory

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
EOF
fi

log_info "Docker sandbox environment setup complete"

# =============================================================================
# PRE-FLIGHT CHECKS
# =============================================================================

# Check Docker availability
if ! command -v docker &> /dev/null; then
    log_error "Docker is not installed or not in PATH"
    log_error "Please install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! docker info > /dev/null 2>&1; then
    log_error "Docker daemon is not running"
    log_error "Please start Docker daemon"
    exit 1
fi

log_info "✓ Docker is available and running"

# Check if required Docker images are available
PYTHON_IMAGE="${LOCALSANDBOX_PYTHON_IMAGE:-python:3.11-slim}"
NODE_IMAGE="${LOCALSANDBOX_NODE_IMAGE:-node:18-slim}"

log_info "Checking Docker images..."
if ! docker image inspect "$PYTHON_IMAGE" > /dev/null 2>&1; then
    log_info "Pulling Python image: $PYTHON_IMAGE"
    docker pull "$PYTHON_IMAGE"
fi

if ! docker image inspect "$NODE_IMAGE" > /dev/null 2>&1; then
    log_info "Pulling Node.js image: $NODE_IMAGE"
    docker pull "$NODE_IMAGE"
fi

log_info "✓ Docker images are ready"

# Check if port is available
MCP_PORT="${MCP_SERVER_PORT:-8775}"
if command -v lsof &> /dev/null && lsof -i :${MCP_PORT} > /dev/null 2>&1; then
    log_error "Port ${MCP_PORT} is already in use"
    exit 1
fi

# Install requirements if needed
if ! $PYTHON_CMD -c "import fastapi, uvicorn, mcp" &> /dev/null; then
    log_info "Installing requirements..."
    if $PYTHON_CMD -m pip install -r requirements.txt; then
        log_info "✓ Requirements installed successfully"
    else
        log_error "Failed to install requirements"
        exit 1
    fi
else
    log_info "✓ All required packages are already installed"
fi

# =============================================================================
# START SERVER
# =============================================================================

log_info "Configuration:"
echo "  Server: http://${MCP_SERVER_HOST:-localhost}:${MCP_SERVER_PORT:-8775}"
echo "  CORS: ${MCP_ENABLE_CORS:-false}"
echo "  Max Sessions: ${LSB_MAX_SESSIONS:-5}"
echo "  Log Level: ${LSB_LOG_LEVEL:-DEBUG}"
echo "  Container Runtime: ${CONTAINER_RUNTIME:-docker}"
echo "  Python Image: ${LOCALSANDBOX_PYTHON_IMAGE:-python:3.11-slim}"
echo "  Node Image: ${LOCALSANDBOX_NODE_IMAGE:-node:18-slim}"

log_info "Starting MCP Server with Docker-based sandbox..."
log_info "Press Ctrl+C to stop"

# Add the sandbox package to Python path
export PYTHONPATH="$SCRIPT_DIR/../python:$PYTHONPATH"

log_info "Python path updated to include sandbox package"

# Change to script directory and start server
cd "$SCRIPT_DIR"
exec $PYTHON_CMD -m server.main --transport streamable-http --port ${MCP_SERVER_PORT:-8775}