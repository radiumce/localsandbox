#!/bin/bash

# LocalSandbox MCP Server Installation Script

set -e

echo "🚀 Installing LocalSandbox MCP Server..."

# Function to check for command availability
has_command() {
    command -v "$1" >/dev/null 2>&1
}

# Check if uv is installed
if has_command uv; then
    echo "✨ uv detected! Using modern installation..."
    
    # Create valid venv if not exists
    if [ ! -d ".venv" ]; then
        echo "📦 Creating virtual environment with uv..."
        uv venv --python 3.10
    fi
    
    echo "📦 Installing dependencies with uv..."
    # Install editable with dev dependencies for development
    uv pip install -e ".[dev]"
    
    echo "🎉 Installation completed successfully with uv!"
    echo "To activate environment: source .venv/bin/activate"
    
else
    # Fallback to standard pip
    echo "⚠️  uv not found. Using standard pip..."
    
    # Check for python3
    if ! has_command python3; then
        echo "❌ Python 3 is required."
        exit 1
    fi
    
    # Create venv if not exists (Standard best practice)
    if [ ! -d ".venv" ]; then
        echo "📦 Creating virtual environment..."
        python3 -m venv .venv
    fi
    
    # Activate venv for installation
    source .venv/bin/activate || source .venv/Scripts/activate
    
    echo "📦 Installing package and dependencies..."
    pip install .
    
    echo "🎉 Installation completed successfully!"
    echo "To activate environment: source .venv/bin/activate"
fi

echo ""
echo "🔧 You can now use the following commands (after activating venv):"
echo "   lsb start         # Start the LocalSandbox server"
echo "   lsb stop          # Stop the server"
echo ""
echo "📚 For more information, run: lsb --help"