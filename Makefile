# stapel-currencies — contract emission + drift gate (contract-pipeline.md §2-3).
#
# This module emits its OWN contract triad (schema.json + flows.json +
# errors.json) from a single-module {currencies + core} Django instance mounted
# at the canonical /currencies/api/v1/ prefix (see _codegen.py /
# _codegen_settings.py / codegen_urls.py). PYTHON must have the module + its
# deps importable (the workspace venv, or a CI venv) and be a 3.12 interpreter
# (emission pin: drf-spectacular renders component descriptions differently
# across minors, so a contract emitted on the wrong one diffs forever).
PYTHON ?= python3

.PHONY: migration-lint contract contract-check lint test

# Expand/contract gate for Django migrations (release-management.md §3;
# stapel_tools.migration_lint). Requires stapel-tools importable (the
# workspace venv, or `pip install stapel-tools` once published).
migration-lint:
	$(PYTHON) -m stapel_tools.migration_lint . --strict


# First: the contract triad. docs/schema.json is what makes this module
# consumable by a frontend codegen (@stapel/currencies-react) and by
# `stapel-catalog --from-installed` — a module whose only schema lives in some
# host's aggregate is a module nobody can generate a client for.
# docs/flows.json is [] here on purpose: a read-only catalog is not a flow.
#
# Second: the `surface` section of docs/capabilities.json — the symbols a
# product is meant to CALL (discoverability-design.md §1.2). This is the whole
# point of the section: a DRF gate got hand-rolled in a product because nobody
# knew stapel-core already shipped IsNotAnonymousUser, and nothing in any
# module's contract could even name a mechanism you are supposed to reach for.
# Entries are derived by AST from the roots declared in
# docs/capabilities.meta.json; a selected export with no curated intent line
# fails this target naming it.
#
# NOTE the rest of docs/capabilities.json in this module is still HAND-AUTHORED
# (git log: "author capabilities.json for the stapel-catalog sweep") — no
# generator exists for provides/axes/extension_points/operations_total here.
# `--patch` refreshes only the derivable parts: module/version and `surface`.
#
# Third: docs/llms.txt — the fifth contract artifact (badge-canon §3,
# stapel_tools.llms_txt), an agent-sized slice of docs/capabilities.json,
# rendered straight from the capabilities.json the step above produces.
#
# Fourth: assemble README.md (stapel_tools.readme) from docs/readme.md — the
# human half, the only file a person edits — plus the artifacts above. The
# badge row, the version, the surface counts and every doc link are generated,
# so they cannot lag a release the way a hand-written README always has.
contract:
	$(PYTHON) -m stapel_currencies._codegen --out docs
	$(PYTHON) -m stapel_tools.surface . --patch
	$(PYTHON) -m stapel_tools.llms_txt .
	$(PYTHON) -m stapel_tools.readme .

# Drift gate. The triad regenerates into a temp dir and is diffed there; the
# capabilities `surface` patch runs against the real repo (it AST-scans the
# actual source files named by surface_roots, so it cannot run against a
# docs/-only temp dir) and compares in memory.
contract-check:
	@$(PYTHON) -m stapel_tools.surface . --patch --check || exit 1; \
	tmp=$$(mktemp -d); \
	$(PYTHON) -m stapel_currencies._codegen --out "$$tmp" || { rm -rf "$$tmp"; exit 1; }; \
	rc=0; \
	for f in schema.json flows.json errors.json; do \
		if ! cmp -s "docs/$$f" "$$tmp/$$f"; then \
			echo "DRIFT: docs/$$f is stale — run 'make contract' and commit it"; \
			diff "docs/$$f" "$$tmp/$$f" | head -20; rc=1; \
		fi; \
	done; \
	rm -rf "$$tmp"; \
	$(PYTHON) -m stapel_tools.llms_txt . --check || rc=1; \
	$(PYTHON) -m stapel_tools.readme . --check || rc=1; \
	if [ $$rc -eq 0 ]; then echo "contract-check: docs/{schema,flows,errors,capabilities,llms.txt} + README.md up to date"; fi; \
	exit $$rc

lint:
	ruff check . --select E,F,W --ignore E501

test:
	$(PYTHON) -m pytest tests/ -q
