.PHONY: build-cli install-cli run-server

build-cli:
	uv add --dev pyinstaller
	uv run pyinstaller --onefile --name lsb-cli mcp-server/server/cli_client.py
	@echo "Build successful! Binary is in dist/lsb-cli"

install-cli:
	./install-lsb-cli.sh

run-server:
	uv run lsb start
