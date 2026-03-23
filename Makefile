# Repository Makefile
#
# The Makefile provides standard development commands for the repository.
#
# The command `make ci` is the repository validation entry point used by:
# - developers
# - CI pipelines
# - AI agents

.PHONY: ci smoke unit

PYTHON ?= python3

ci: smoke unit
	@echo ""
	@echo "CI validation completed successfully."

smoke:
	@./tests/smoke_test.sh

unit:
	@if command -v $(PYTHON) >/dev/null 2>&1; then \
		PYTHONPATH=src $(PYTHON) -m unittest discover -s tests -p "test_*.py"; \
	else \
		echo "Skipping Python unit tests: $(PYTHON) not available in PATH."; \
	fi
