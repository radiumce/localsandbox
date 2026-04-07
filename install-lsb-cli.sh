#!/usr/bin/env bash

set -e

# Config
CLI_NAME="lsb-cli"
INSTALL_DIR="${HOME}/.local/bin"
OS=$(uname | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)

echo "🚀 Installing $CLI_NAME..."

if [[ "$OS" != "linux" && "$OS" != "darwin" ]]; then
    echo "❌ Unsupported OS: $OS. Please install manually."
    exit 1
fi

if [[ "$ARCH" == "aarch64" || "$ARCH" == "arm64" ]]; then
    ARCH_MAP="arm64"
elif [[ "$ARCH" == "x86_64" ]]; then
    ARCH_MAP="amd64"
else
    echo "❌ Unsupported Architecture: $ARCH."
    exit 1
fi

DOWNLOAD_URL="https://github.com/radiumce/localsandbox/releases/latest/download/${CLI_NAME}-${OS}-${ARCH_MAP}"

echo "ℹ️  Creating directory ${INSTALL_DIR}..."
mkdir -p "$INSTALL_DIR"

if command -v go >/dev/null 2>&1 && [ -d "cli" ] && [ -f "cli/main.go" ]; then
    echo "📦 Go compiler found. Compiling lsb-cli locally..."
    (cd cli && go build -o "${INSTALL_DIR}/${CLI_NAME}")
elif [ -f "dist/${CLI_NAME}" ]; then
    echo "📦 Local build found. Copying from dist/${CLI_NAME}..."
    cp "dist/${CLI_NAME}" "${INSTALL_DIR}/${CLI_NAME}"
else
    echo "⬇️  Downloading from ${DOWNLOAD_URL}..."
    if ! curl -fsSL -o "${INSTALL_DIR}/${CLI_NAME}" "$DOWNLOAD_URL"; then
        echo "❌ Download failed. The latest release might not exist."
        echo "Please build from source using 'make build-cli', or verify the GitHub release."
        rm -f "${INSTALL_DIR}/${CLI_NAME}"
        exit 1
    fi
fi

chmod +x "${INSTALL_DIR}/${CLI_NAME}"

export PATH="${INSTALL_DIR}:$PATH"

echo "✓ $CLI_NAME installed successfully to ${INSTALL_DIR}/${CLI_NAME}"

# Check shell PATH
if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
    echo "⚠️  WARNING: ${INSTALL_DIR} is not in your PATH."
    echo "    Please add the following line to your shell profile (.bashrc, .zshrc, etc.):"
    echo "    export PATH=\"$INSTALL_DIR:\$PATH\""
else
    echo "✨ You can now use '$CLI_NAME' anywhere."
fi
