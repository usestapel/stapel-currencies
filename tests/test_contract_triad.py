"""Per-module contract triad + drift gate (contract-pipeline.md §2-3).

stapel-currencies emits its own triad — ``docs/schema.json`` (OpenAPI),
``docs/flows.json`` (``[]``: a read-only catalog annotates no ``@flow_step``)
and ``docs/errors.json`` — from a single-module ``{currencies + core}`` Django
instance mounted at the canonical ``/currencies/api/v1/`` prefix.

stapel-currencies is not mounted in stapel-example-monolith, so there is no
aggregate slice to diff these artifacts against for byte-identity —
validation is standalone (contract-pipeline.md §9 fallback): determinism,
self-contained ``$ref`` closure, canonical-prefix paths, and the module's own
error keys present in the registry.

Regenerate after any change to a serializer/view/url/error key:

    make contract

then commit docs/{schema,flows,errors}.json.

The llms.txt / README.md halves of the pipeline live in ``test_contract.py``;
they run on any interpreter, this file only on the 3.12 emission pin.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

_PY = sys.version_info[:2]
if _PY != (3, 12):
    _GOT = f"{_PY[0]}.{_PY[1]}"
    pytest.skip(
        "stapel-currencies contract tests require Python 3.12 (the CI/monolith "
        f"pin) — running {_GOT}. drf-spectacular renders component descriptions "
        "(Optional[X] vs X | None) differently across Python minor versions, so "
        "drift/identity checks emitted+compared under any other minor produce "
        "false diffs. Skipping on any non-3.12 interpreter.",
        allow_module_level=True,
    )

REPO = Path(__file__).resolve().parent.parent
DOCS = REPO / "docs"
TRIAD = ("schema.json", "flows.json", "errors.json")


def _emit(out_dir: Path) -> None:
    subprocess.run(
        [sys.executable, "-m", "stapel_currencies._codegen", "--out", str(out_dir)],
        cwd=str(REPO),
        check=True,
        capture_output=True,
    )


def test_triad_is_committed():
    for name in TRIAD:
        assert (DOCS / name).is_file(), f"missing docs/{name} — run `make contract`"


def test_triad_has_no_drift(tmp_path):
    _emit(tmp_path)
    for name in TRIAD:
        assert (DOCS / name).read_bytes() == (tmp_path / name).read_bytes(), (
            f"docs/{name} drifted — run `make contract` and commit docs/{name}"
        )


def test_emission_is_deterministic(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    _emit(a)
    _emit(b)
    for name in TRIAD:
        assert (a / name).read_bytes() == (b / name).read_bytes()


def test_paths_carry_the_canonical_prefix():
    schema = json.loads((DOCS / "schema.json").read_text())
    assert schema["paths"], "schema has no paths"
    assert all(p.startswith("/currencies/api/v1/") for p in schema["paths"]), (
        "schema paths are not mounted at the canonical /currencies/api/v1/ prefix"
    )


def test_the_catalog_is_two_read_only_operations():
    """The whole HTTP surface: list + retrieve, both GET. Writes are the
    admin, the management commands and the rate task — never this API, and a
    new verb appearing here is a contract change, not a detail."""
    schema = json.loads((DOCS / "schema.json").read_text())
    operations = sorted(
        f"{method.upper()} {path}"
        for path, ops in schema["paths"].items()
        for method in ops
        if method in ("get", "post", "put", "patch", "delete")
    )
    assert operations == [
        "GET /currencies/api/v1/",
        "GET /currencies/api/v1/{code}/",
    ], operations


def _all_refs(obj) -> set[str]:
    return set(re.findall(r'"#/components/schemas/([^"]+)"', json.dumps(obj)))


def test_schema_refs_are_self_contained():
    schema = json.loads((DOCS / "schema.json").read_text())
    comps = schema.get("components", {}).get("schemas", {})
    seen: set[str] = set()
    stack = list(_all_refs(schema["paths"]))
    while stack:
        name = stack.pop()
        if name in seen:
            continue
        seen.add(name)
        if name in comps:
            stack.extend(_all_refs(comps[name]))
    dangling = seen - set(comps)
    assert not dangling, f"dangling $ref(s) with no component definition: {dangling}"


def test_flows_are_empty_no_flow_step_annotations():
    flows = json.loads((DOCS / "flows.json").read_text())
    assert flows == [], (
        "docs/flows.json is non-empty but no @flow_step annotation exists in "
        "stapel_currencies — investigate before assuming [] is still correct"
    )


def test_errors_json_carries_this_module_keys():
    from stapel_currencies.errors import STAPEL_CURRENCIES_ERRORS

    entries = {e["code"]: e for e in json.loads((DOCS / "errors.json").read_text())}
    for code, english in STAPEL_CURRENCIES_ERRORS.items():
        assert code in entries, f"{code} missing from docs/errors.json"
        assert entries[code]["en"] == english
        assert entries[code]["owner"] == "stapel_currencies", (
            f"{code} is attributed to {entries[code]['owner']!r} — this module "
            "owns the key and therefore owes its catalogues"
        )
