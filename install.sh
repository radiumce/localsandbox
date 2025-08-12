#!/bin/bash

# Microsandbox MCP Server Installation Script

set -e

echo "🚀 Installing Microsandbox MCP Server..."

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed. Please install Python 3.8+ first."
    exit 1
fi

# Check Python version
python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
required_version="3.8"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Python $required_version or higher is required. Found: $python_version"
    exit 1
fi

echo "✅ Python $python_version detected"

# Install the package
echo "📦 Installing package and dependencies..."
pip install .

echo "🎉 Installation completed successfully!"
echo ""
echo "🔧 You can now use the following commands:"
echo "   start-localsandbox                         # Start with LocalSandbox (recommended)"
echo "   microsandbox-mcp-server                    # Start with stdio transport"
echo "   microsandbox-mcp-server --transport streamable-http --port 8775  # HTTP transport"
echo "   microsandbox-mcp-server --transport sse --enable-cors             # SSE transport"
echo ""
echo "🐳 For LocalSandbox:"
echo "   Make sure Docker is installed and running"
echo "   Copy .env.example to .env.local and configure as needed"
echo "   The server will automatically pull required images on first run"
echo ""
echo "📚 For more information, run: microsandbox-mcp-server --help"