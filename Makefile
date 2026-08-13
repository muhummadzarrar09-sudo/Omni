# OMNI V3 - Makefile
# Convenience targets for source-checkout workflows.
# These index-resolved installs are not B01 qualification evidence. For the
# qualified hash-lock + local-wheel workflow, use docs/TROUBLESHOOTING.md.
# For the core Python CLI, see `omni` after `pip install '.[core]'`.

.PHONY: help install install-minimal install-all install-dev \
        test test-verbose test-fast test-hermes test-skills \
        brain brain-test brain-shell \
        model-download model-info \
        start ui dev \
        status clean clean-data clean-models

PY := $(shell which python3 || which python)
PIP := $(PY) -m pip

help:
	@echo "OMNI V3 - Source-checkout convenience tasks:"
	@echo "  Install targets resolve ranges from an index; they are not B01 evidence."
	@echo "  See docs/TROUBLESHOOTING.md for the qualified lock + wheel workflow."
	@echo "  make install-minimal  - Build from source with the core profile"
	@echo "  make install-all      - Build from source with all runtime capabilities"
	@echo "  make install-dev      - Build from source with core development tools"
	@echo ""
	@echo "  make test             - Run all 4 test suites"
	@echo "  make test-fast        - Just the 10-command multi-agent test"
	@echo "  make brain-shell      - Interactive brain REPL"
	@echo ""
	@echo "  make model-download   - Fetch the 1.1GB Qwen2.5-1.5B GGUF"
	@echo "  make model-info       - Show which model is loaded"
	@echo ""
	@echo "  make start            - Run FastAPI backend on :8765"
	@echo "  make ui               - Run Next.js UI on :3000"
	@echo "  make dev              - Start both, open browser"
	@echo ""
	@echo "  make status           - Health check"
	@echo "  make clean            - Remove __pycache__ and build artifacts"

install-minimal:
	$(PIP) install ".[core]"

install-all:
	$(PIP) install ".[all]"

install-dev:
	$(PIP) install ".[dev]"

install: install-all

test:
	$(PY) -m omni.cli test

test-verbose:
	$(PY) -m omni.cli test -v

test-fast:
	$(PY) omni.py --test

test-hermes:
	$(PY) -m omni_v2.tests.test_hermes_refinement

test-skills:
	$(PY) -m omni_v2.tests.test_skill_synthesis

brain:
	@echo "  Starting OMNI brain interactive REPL..."
	@$(PY) -m omni.cli shell

brain-test:
	@echo "  Brain self-test (open github, search, etc.)..."
	@$(PY) -m omni.cli test

brain-shell:
	$(PY) -m omni.cli shell

model-download:
	$(PY) -m omni.cli model download

model-info:
	$(PY) -m omni.cli model info

start:
	$(PY) -m omni.cli start

ui:
	$(PY) -m omni.cli ui

dev:
	$(PY) -m omni.cli dev

status:
	$(PY) -m omni.cli status

clean:
	find . -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name '*.egg-info' -exec rm -rf {} + 2>/dev/null || true
	rm -rf build/ dist/ .eggs/ 2>/dev/null || true
	@echo "  ✅ Cleaned"

clean-data:
	$(PY) -c 'from pathlib import Path; import shutil; from omni_v2.core.paths import get_data_dir; p=get_data_dir(create=False); shutil.rmtree(p) if p.exists() else None; print(f"  Removed OMNI user data: {p}")'

clean-models:
	$(PY) -c 'import shutil; from omni_v2.core.paths import get_data_dir; p=get_data_dir(create=False) / "models"; shutil.rmtree(p) if p.exists() else None; print(f"  Removed OMNI models: {p}")'
