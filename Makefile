SHELL := /bin/bash

.PHONY: help test lint app-deb kernel iso clean

help:
	@echo "Cartheon OS build targets"
	@echo "  make test      Run launcher and manifest tests"
	@echo "  make lint      Compile-check all Python sources"
	@echo "  make app-deb   Build the Cartheon shell Debian package"
	@echo "  make kernel    Build the pinned Kernel 7 Debian package (Linux x86_64)"
	@echo "  make iso       Build the full x86_64 hybrid live/install ISO (Linux x86_64)"

test:
	PYTHONPATH=src python3 -m unittest discover -s tests -v

lint:
	python3 -m compileall -q src tests

app-deb:
	./scripts/build-app-deb.sh

kernel:
	./scripts/build-kernel.sh

iso:
	./scripts/build-iso.sh

clean:
	./auto/clean
