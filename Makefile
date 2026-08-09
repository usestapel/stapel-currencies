PYTHON ?= python3

.PHONY: migration-lint contract contract-check

# Expand/contract gate for Django migrations (release-management.md §3;
# stapel_tools.migration_lint). Requires stapel-tools importable (the
# workspace venv, or `pip install stapel-tools` once published).
migration-lint:
	$(PYTHON) -m stapel_tools.migration_lint . --strict


# The `surface` section of docs/capabilities.json — the symbols a product is
# meant to CALL (discoverability-design.md §1.2). This is the whole point of
# the section: a DRF gate got hand-rolled in a product because nobody knew
# stapel-core already shipped IsNotAnonymousUser, and nothing in any module's
# contract could even name a mechanism you are supposed to reach for. Entries
# are derived by AST from the roots declared in docs/capabilities.meta.json; a
# selected export with no curated intent line fails this target naming it.
#
# NOTE the rest of docs/capabilities.json in this module is still HAND-AUTHORED
# (git log: "author capabilities.json for the stapel-catalog sweep") — no
# generator exists for provides/axes/extension_points/operations_total here.
# `--patch` refreshes only the derivable parts: module/version and `surface`.
#
# Second: docs/llms.txt — the fifth contract artifact (badge-canon §3,
# stapel_tools.llms_txt), an agent-sized slice of docs/capabilities.json,
# rendered straight from the capabilities.json the step above produces.
#
# Third: assemble README.md (stapel_tools.readme) from docs/readme.md — the
# human half, the only file a person edits — plus the artifacts above. The
# badge row, the version, the surface counts and every doc link are generated,
# so they cannot lag a release the way a hand-written README always has.
contract:
	$(PYTHON) -m stapel_tools.surface . --patch
	$(PYTHON) -m stapel_tools.llms_txt .
	$(PYTHON) -m stapel_tools.readme .

contract-check:
	$(PYTHON) -m stapel_tools.surface . --patch --check
	$(PYTHON) -m stapel_tools.llms_txt . --check
	$(PYTHON) -m stapel_tools.readme . --check
