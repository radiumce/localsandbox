.PHONY: build-cli install-cli run-server

build-cli:
	cd cli && go build -o ../dist/lsb-cli
	@echo "Build successful! Binary is in dist/lsb-cli"

install-cli:
	./install-lsb-cli.sh

run-server:
	uv run lsb start
