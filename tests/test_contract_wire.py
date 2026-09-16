"""Every response body the contract declares is a body the views actually send.

``docs/schema.json`` is emitted from the views' ``@extend_schema``
annotations, and an annotation is a CLAIM: it says what the view returns, and
the generator has no way to check it against the method body.
``tests/test_contract.py`` compares the committed document against a FRESH
EMISSION of the same annotations — it proves the file is not stale, and
nothing else, because both sides come from the claim. stapel-alerts 0.2.0
shipped ``GET /issues`` declared as ``Issue[]`` while the wire carried
``{count, offset, limit, results}``: the drift gate was green and the
frontend pair rendered ``undefined``.

This is the gate the generator cannot be: it performs every operation the
committed schema declares with a JSON response body, and validates the body
it gets against the schema it was promised.

Rules this file holds itself to:

* an operation with a declared JSON response and no entry in ``RECIPES``
  FAILS LOUDLY — a gate that quietly covers one of two rows is the family of
  green that proves nothing;
* a path parameter the gate cannot fill fails at the point of substitution,
  naming the operation;
* the operations that genuinely cannot be driven in-process are listed by
  name in ``UNDRIVABLE`` with a one-line reason each. That list is asserted
  to be exactly current: a stale entry, or a missing reason, fails;
* a collection that comes back empty fails in the populated pass — an empty
  array validates against any item schema, so an empty answer is a check
  that looked at nothing;
* every read is driven a SECOND time in its emptiest legal state
  (``EMPTY_STATE``): a catalog holding nothing, and a row carrying none of
  its optional values (no symbol, the default rate). Every null finding in
  the first wave of this gate was on an empty state.

Runs on every interpreter: it reads the committed schema and never emits.

THE MOUNT. ``codegen_urls.py`` mounts ``currencies/`` →
``stapel_currencies.urls``, and the router inside contributes ``api/v1``.
``tests/urls.py`` mounts the identical prefix, so this module's suite has
always been looking where the document points — unlike five of the first
eight libraries in this wave, whose test urlconf pointed somewhere the
document does not describe. The emission mount is declared here rather than
borrowed, so ``test_every_declared_path_resolves_under_this_urlconf`` fails
at the one moment it is cheap to fix: when somebody changes a mount.

What it found on its first run: 2 of 2 operations driven, 0 red. The claims
this module makes about its own wire are honest in both states. Two of them
are worth naming because they are the kind that usually is not:

* ``value`` is declared ``{"type": "string", "format": "decimal", "pattern":
  "^-?\\d{0,12}(?:\\.\\d{0,8})?$"}`` and the wire really does send a
  DECIMAL STRING — DRF's ``COERCE_DECIMAL_TO_STRING`` is on, so a rate never
  arrives as a float. The gate asserts the pattern rather than trusting it,
  which is the one place in this contract a JSON number would silently pass
  a reader's eye and lose a cent;
* ``symbol`` is declared OPTIONAL and non-nullable, and a currency with no
  symbol answers ``""`` rather than ``null`` — the model's ``blank=True,
  default=""`` is what makes that true, and it is exactly the shape that was
  a lie in stapel-auth (a field typed non-optional over a service that
  returns ``None``).

``test_the_gate_is_not_blind`` proves that is a finding rather than a gate
that never looked: it re-validates every driven body against
``{"type": "string"}`` and requires all of them to fail.
"""
import copy
import json
import re
from decimal import Decimal
from pathlib import Path

import jsonschema
import pytest
from django.test import override_settings
from django.urls import include, path as url_path
from rest_framework.test import APIClient

REPO = Path(__file__).resolve().parent.parent
SCHEMA = json.loads((REPO / "docs" / "schema.json").read_text())

#: The mount the contract is emitted at, reproduced for the test client
#: (``codegen_urls.py``: ``currencies/`` → ``stapel_currencies.urls``, whose
#: router contributes ``api/v1``).
urlpatterns = [
    url_path("currencies/", include("stapel_currencies.urls")),
]

pytestmark = [pytest.mark.django_db, pytest.mark.urls(__name__)]

V1 = "/currencies/api/v1"


@pytest.fixture(autouse=True)
def _media_root(tmp_path):
    """Nothing here writes files today; pin the root so nothing ever does.

    ``MEDIA_ROOT`` is unset in this module's harness settings (conftest.py),
    so it defaults to the working directory — in stapel-auth that put a data
    export into the checkout, where under a flat package layout a stray
    directory also shadowed a real submodule.
    """
    with override_settings(MEDIA_ROOT=str(tmp_path)):
        yield


# ─────────────────────────────────────────────────────────────────────────────
# The contract side: what the document declares
# ─────────────────────────────────────────────────────────────────────────────


def _json_schema(node):
    """OpenAPI 3.0 → JSON Schema, for the divergences that could matter here.

    OAS 3.0 spells "may be null" as ``nullable: true`` beside a ``type``;
    JSON Schema has no such keyword and would refuse the null. Nothing in
    this one-component contract is nullable today, and the conversion stays
    anyway: the day a field becomes nullable, the gate must keep testing the
    claim rather than start failing on the conversion. Everything else
    drf-spectacular emits here (``required``, ``pattern``, ``maxLength``,
    ``format``) is JSON Schema as written.
    """
    if isinstance(node, list):
        return [_json_schema(item) for item in node]
    if not isinstance(node, dict):
        return node
    rebuilt = {k: _json_schema(v) for k, v in node.items() if k != "nullable"}
    if node.get("nullable"):
        return {"anyOf": [rebuilt, {"type": "null"}]}
    return rebuilt


def _validator(response_schema):
    root = copy.deepcopy(response_schema)
    root["components"] = copy.deepcopy(SCHEMA["components"])
    return jsonschema.Draft202012Validator(_json_schema(root))


def _operations():
    """Every ``(method, path, 2xx code, JSON body schema)`` the contract declares."""
    ops = []
    for path, methods in SCHEMA["paths"].items():
        for method, op in methods.items():
            if method not in {"get", "post", "put", "patch", "delete"}:
                continue
            for code, response in op.get("responses", {}).items():
                body = (
                    response.get("content", {})
                    .get("application/json", {})
                    .get("schema")
                )
                if body is not None and code.startswith("2"):
                    ops.append((method.upper(), path, int(code), body))
    return sorted(ops, key=lambda o: (o[1], o[0], o[2]))


OPERATIONS = _operations()


# ─────────────────────────────────────────────────────────────────────────────
# The wire side: harness
# ─────────────────────────────────────────────────────────────────────────────


def anonymous():
    """``AllowAny``: a public read-only catalog, and the caller it serves."""
    return APIClient()


def make_currency(code, **kwargs):
    """The code IS the primary key, and ``test_the_gate_is_not_blind``
    re-drives every recipe inside one test — so a row is written rather than
    inserted, and a second pass over the same recipe is idempotent instead of
    an IntegrityError the canary would report as "the gate looked"."""
    from stapel_currencies.models import Currency

    row, _ = Currency.objects.update_or_create(code=code, defaults=kwargs)
    return row


def rich_currency(code="EUR"):
    """Every declared field carrying a real value, symbol included."""
    return make_currency(
        code,
        display_name=f"currency.{code.lower()}",
        value=Decimal("1.23456789"),
        symbol="€",
        is_active=True,
    )


def bare_currency(code="XXX"):
    """A row carrying none of its optional values.

    No symbol (the model's ``blank=True, default=""`` — so the wire sends
    ``""``, never ``null``) and the default rate. This is the row the
    ``symbol`` claim is actually tested against: a populated pass with a
    symbol on every currency never asks what the field holds when there is
    nothing to hold.
    """
    return make_currency(code, display_name=f"currency.{code.lower()}")


# ─────────────────────────────────────────────────────────────────────────────
# The recipe table
# ─────────────────────────────────────────────────────────────────────────────


class Call:
    """Performs one declared operation, and refuses to guess a path parameter."""

    def __init__(self, method, path):
        self.method = method
        self.path = path

    def __call__(self, client, params=None, data=None, query="", **extra):
        url = self.path
        for name, value in (params or {}).items():
            url = url.replace("{%s}" % name, str(value))
        assert "{" not in url, (
            f"{self.method} {self.path}: a path parameter this gate does not "
            "know how to fill — teach its recipe, or the operation goes unchecked"
        )
        send = getattr(client, self.method.lower())
        if self.method in ("GET", "DELETE"):
            return send(url + query, **extra)
        return send(url + query, data if data is not None else {}, format="json", **extra)


#: How to perform each operation the contract declares with a JSON response
#: body, keyed by ``(METHOD, path template)``. A recipe returns the response it
#: produced, or a list of ``(label, response)`` pairs when one operation has
#: more than one answering state worth asking.
RECIPES = {}

#: The same operations again, in the emptiest state the contract still has to
#: describe: a catalog holding nothing, and a row carrying nothing optional.
EMPTY_STATE = {}


def recipe(method, path, table=None):
    def register(fn):
        target = RECIPES if table is None else table
        key = (method, V1 + path)
        assert key not in target, f"duplicate recipe for {method} {path}"
        target[key] = fn
        return fn

    return register


def empty_state(method, path):
    return recipe(method, path, table=EMPTY_STATE)


#: Operations that cannot be driven in-process, by name and with the reason.
#: A short, visible list is acceptable here; a silent skip is not.
#:
#: EMPTY. Both operations are anonymous reads over rows a factory creates.
UNDRIVABLE: dict = {}


# ── the catalog ──────────────────────────────────────────────────────────────


@recipe("GET", "/")
def _currency_list(call):
    rich_currency("EUR")
    rich_currency("USD")
    return call(anonymous())


@empty_state("GET", "/")
def _currency_list_empty(call):
    """Two kinds of empty: a catalog with nothing in it, and a catalog whose
    only row carries nothing optional. An empty ARRAY validates against any
    item schema, so the second branch is the one that does the work.

    The first branch is also the only way to see an empty list at all: the
    viewset's queryset is ``is_active=True``, so an inactive currency is not
    a row that comes back false — it is a row that does not come back.
    """
    nothing = call(anonymous())
    bare_currency("XXX")
    make_currency("ZZZ", display_name="currency.zzz", is_active=False)
    one_bare_row = call(anonymous())
    return [
        ("an empty catalog", nothing),
        ("one row carrying nothing optional (and one inactive, filtered out)",
         one_bare_row),
    ]


@recipe("GET", "/{code}/")
def _currency_detail(call):
    """Both spellings of the same code: the router's ``[A-Za-z]{3}`` admits
    ``eur``, and ``get_object`` upper-cases it before the lookup."""
    currency = rich_currency("EUR")
    client = anonymous()
    return [
        ("the canonical upper-case code", call(client, params={"code": currency.code})),
        ("the lower-case spelling the router admits", call(client, params={"code": "eur"})),
    ]


@empty_state("GET", "/{code}/")
def _currency_detail_empty(call):
    """A currency with no symbol and the default rate — ``symbol`` is the
    field whose declared shape (optional, non-nullable string) is a claim
    only this state can check."""
    currency = bare_currency("XXX")
    return call(anonymous(), params={"code": currency.code})


# ─────────────────────────────────────────────────────────────────────────────
# The gate
# ─────────────────────────────────────────────────────────────────────────────


#: Operations whose declared body the wire does not send, with the defect and
#: its owner. ``strict=True``: a fixed entry fails until it is deleted, so a
#: finding can be neither forgotten nor quietly kept.
#:
#: EMPTY, and that is the finding rather than the absence of one: 2 of 2
#: operations answer the shape they declare, in both states. The mechanism
#: stays because the next wave will need it.
KNOWN_MISMATCHES: dict = {}


def test_the_contract_declares_something_to_check():
    assert OPERATIONS, "docs/schema.json declares no JSON responses at all"


def test_every_declared_path_resolves_under_this_urlconf():
    """The suite must be looking where the document describes.

    Five of the first eight libraries this gate was written for had a
    committed contract that nothing had ever driven, because the test urlconf
    mounted somewhere the document does not describe: one mounted a different
    prefix AND one segment short, one mounted the paths bare, one mounted a
    doubled segment, one mounted less than the emission did. In every case
    the operations were "covered" by a file that could not have reached a
    single one of them.

    Currencies is not one of them — ``tests/urls.py`` and ``codegen_urls.py``
    mount the identical ``currencies/`` prefix — and this assertion is what
    keeps saying so. A missing recipe already fails loudly; this fails when
    the MOUNT is wrong, which no per-operation check can see, because when
    the mount is wrong every operation is equally and silently unreachable.
    """
    from django.urls import Resolver404, resolve

    # Resolution cares about the SHAPE of a segment, and a urlconf may use
    # several converters or, as here, a ``lookup_value_regex``. A path counts
    # as reachable if any one shape resolves: the question here is whether
    # the mount exists, not whether a particular id does. ``eur`` is the
    # shape this module's viewset admits (``[A-Za-z]{3}``) and none of the
    # other three match it — the uuid/int/slug trio alone would call every
    # detail route unreachable and say nothing about the mount.
    candidates = (
        "00000000-0000-4000-8000-000000000000",
        "1",
        "a-slug",
        "eur",
    )

    unreachable = []
    for _method, path, _code, _schema in OPERATIONS:
        for value in candidates:
            try:
                resolve(re.sub(r"\{[^}]+\}", value, path))
                break
            except Resolver404:
                continue
        else:
            unreachable.append(path)

    assert not unreachable, (
        "these declared paths do not resolve under this module's urlconf, so "
        "nothing here can be driving them — the mount is wrong, not the "
        "recipes:\n  " + "\n  ".join(sorted(set(unreachable)))
    )


def test_every_declared_operation_is_driven_or_named_undrivable():
    """No operation is covered by silence, and no entry outlives its operation."""
    declared = {(method, path) for method, path, _code, _schema in OPERATIONS}
    covered = set(RECIPES) | set(UNDRIVABLE)

    missing = sorted(declared - covered)
    assert not missing, (
        "operations with a declared JSON response body and no recipe:\n"
        + "\n".join(f"  {m} {p}" for m, p in missing)
    )
    stale = sorted(covered - declared)
    assert not stale, (
        "recipes/exclusions for operations the contract no longer declares:\n"
        + "\n".join(f"  {m} {p}" for m, p in stale)
    )
    both = sorted(set(RECIPES) & set(UNDRIVABLE))
    assert not both, f"driven AND excluded: {both}"
    for key, reason in UNDRIVABLE.items():
        assert reason and reason.strip(), f"{key} is excluded with no reason"


def test_every_read_is_also_driven_in_its_emptiest_state():
    """A populated answer cannot say what a field holds when there is nothing.

    Every null finding in the first wave of this gate was on the empty state.
    A gate that only ever seeds three rows and asks never sees any of them.
    """
    reads = {
        (method, path)
        for method, path, _code, _schema in OPERATIONS
        if method == "GET"
    }
    missing = sorted(reads - set(EMPTY_STATE))
    assert not missing, (
        "reads driven only against a populated database — the state where "
        "every null claim in this gate's history was found is unchecked:\n"
        + "\n".join(f"  {m} {p}" for m, p in missing)
    )
    declared = {(m, p) for m, p, _c, _s in OPERATIONS}
    stale = sorted(set(EMPTY_STATE) - declared)
    assert not stale, f"empty-state recipes for undeclared operations: {stale}"


def test_every_known_mismatch_is_still_declared_and_explained():
    """A recorded defect must name a live operation and carry its reason.

    Without this, an operation that is renamed or removed leaves an entry that
    silences nothing and reads like a known problem forever.
    """
    declared = {(method, path) for method, path, _code, _schema in OPERATIONS}
    for key, reason in KNOWN_MISMATCHES.items():
        assert key in declared, (
            f"{key} is recorded as a known mismatch but the contract no longer "
            "declares it — delete the entry"
        )
        assert reason and reason.strip(), f"{key} is recorded with no reason"


def _labelled(result):
    """A recipe answers with one response, or with labelled branches."""
    if isinstance(result, list):
        return result
    return [("", result)]


def _drive(table, method, path, code, body_schema, *, expect_rows):
    perform = table.get((method, path))
    assert perform is not None, (
        f"{method} {path} declares a response body and has no recipe — an "
        "unchecked operation is a schema nobody proves. Teach RECIPES, or "
        "name it in UNDRIVABLE with a reason."
    )

    bodies = []
    for label, response in _labelled(perform(Call(method, path))):
        where = f"{method} {path}" + (f" [{label}]" if label else "")
        assert response.status_code == code, (
            f"{where}: expected the declared {code}, got "
            f"{response.status_code}: {response.content[:400]}"
        )

        body = response.json()
        errors = sorted(
            _validator(body_schema).iter_errors(body), key=lambda e: list(e.path)
        )
        assert not errors, (
            f"{where} answers a body the contract does not describe:\n"
            + "\n".join(f"  at {list(e.path) or '<root>'}: {e.message}" for e in errors[:10])
            + f"\n  body: {json.dumps(body)[:600]}"
        )

        # An empty list validates against any item schema, so a collection
        # must actually carry a row for the check to have looked at anything.
        if expect_rows and isinstance(body, list):
            assert body, f"{where}: the declared list came back empty"
        bodies.append(body)
    return bodies


def _rows(body):
    return body if isinstance(body, list) else [body]


@pytest.mark.parametrize(
    "method,path,code,body_schema",
    OPERATIONS,
    ids=[f"{m} {p}" for m, p, _c, _s in OPERATIONS],
)
def test_the_wire_matches_the_declared_response(method, path, code, body_schema, request):
    if (method, path) in UNDRIVABLE:
        pytest.skip(f"excluded by name: {UNDRIVABLE[(method, path)]}")

    if (method, path) in KNOWN_MISMATCHES:
        request.node.add_marker(
            pytest.mark.xfail(
                strict=True,
                reason=f"{method} {path}: {KNOWN_MISMATCHES[(method, path)]}",
            )
        )

    _drive(RECIPES, method, path, code, body_schema, expect_rows=True)


_EMPTY_OPERATIONS = [
    (method, path, code, schema)
    for method, path, code, schema in OPERATIONS
    if (method, path) in EMPTY_STATE
]


@pytest.mark.parametrize(
    "method,path,code,body_schema",
    _EMPTY_OPERATIONS,
    ids=[f"{m} {p}" for m, p, _c, _s in _EMPTY_OPERATIONS],
)
def test_the_wire_matches_the_declared_response_when_there_is_nothing_there(
    method, path, code, body_schema, request
):
    """The same claim, asked in the state where the nulls live."""
    if (method, path) in KNOWN_MISMATCHES:
        request.node.add_marker(
            pytest.mark.xfail(
                strict=True,
                reason=f"{method} {path}: {KNOWN_MISMATCHES[(method, path)]}",
            )
        )

    _drive(EMPTY_STATE, method, path, code, body_schema, expect_rows=False)


def test_money_really_travels_as_a_decimal_string():
    """The one claim a green schema check could make for the wrong reason.

    ``value`` is declared ``type: string`` with a decimal ``pattern``, and
    JSON Schema's ``type`` keyword is what enforces it — but a validator only
    ever sees what the renderer produced, and the question this contract
    exists to answer is whether a RATE can arrive as a JSON number. Flipping
    ``COERCE_DECIMAL_TO_STRING`` off in a host's ``REST_FRAMEWORK`` does
    exactly that, silently, and the emitted document does not change. So the
    received value is asserted to be a ``str`` and to match the declared
    pattern, rather than inferred from a passing validator.
    """
    pattern = SCHEMA["components"]["schemas"]["Currency"]["properties"]["value"][
        "pattern"
    ]
    for method, path, code, body_schema in OPERATIONS:
        for body in _drive(RECIPES, method, path, code, body_schema, expect_rows=True):
            for row in _rows(body):
                value = row["value"]
                assert isinstance(value, str), (
                    f"{method} {path}: `value` arrived as {type(value).__name__} "
                    f"({value!r}) — money on the wire as a JSON number is the "
                    "rounding this contract declares a string to prevent"
                )
                assert re.fullmatch(pattern, value), (
                    f"{method} {path}: `value` {value!r} does not match the "
                    f"declared pattern {pattern!r}"
                )


def test_the_gate_is_not_blind():
    """A canary: swap a declared schema for one the wire cannot satisfy.

    Everything above can be green for two reasons — the claims are honest, or
    the check never looks at the body. This tells them apart by validating a
    real response against ``{"type": "string"}``: every operation here answers
    an object or an array, so every one of them must fail. If any passes, the
    validation in ``_drive`` is not reaching the received body and this whole
    file proves nothing. With ``KNOWN_MISMATCHES`` empty this covers the
    entire declared surface.
    """
    honest = [
        (method, path, code)
        for method, path, code, _schema in OPERATIONS
        if (method, path) not in KNOWN_MISMATCHES and (method, path) not in UNDRIVABLE
    ]
    assert honest, "nothing left to canary"

    survivors = []
    for method, path, code in honest:
        try:
            _drive(RECIPES, method, path, code, {"type": "string"}, expect_rows=False)
        except AssertionError:
            continue
        survivors.append(f"{method} {path}")
    assert not survivors, (
        "these operations passed validation against {'type': 'string'} — the "
        "gate is not looking at the body it received:\n  " + "\n  ".join(survivors)
    )
