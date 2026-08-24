"""Shipped error catalogues (i18n-shipping.md §5).

Owning an error key means shipping its translations in the same release —
otherwise a translated deployment renders this module's refusals in English
and nobody notices, because an English sentence in a Spanish page looks like
a sentence, not like a gap. ``translations/errors.<lang>.json`` is the
catalogue; this gate is the reason it cannot silently fall behind
``errors.py``.
"""
import json
from pathlib import Path

import pytest

from stapel_currencies.errors import STAPEL_CURRENCIES_ERRORS

REPO = Path(__file__).resolve().parent.parent
CATALOGS = REPO / "translations"
LANGUAGES = ["ru", "es"]


@pytest.mark.parametrize("language", LANGUAGES)
def test_catalog_covers_every_owned_key(language):
    catalog = json.loads((CATALOGS / f"errors.{language}.json").read_text())
    assert set(catalog) == set(STAPEL_CURRENCIES_ERRORS), (
        f"errors.{language}.json does not cover exactly the keys this module "
        "owns — run `translate_catalogs --domain errors` and review"
    )
    assert all(text.strip() for text in catalog.values())


@pytest.mark.parametrize("language", LANGUAGES)
def test_catalog_is_byte_stable(language):
    """Sorted keys, 2-space indent, unicode kept readable, trailing newline —
    the encoding the fleet's catalogue tooling writes, so a re-run diffs
    empty instead of reshuffling the file."""
    path = CATALOGS / f"errors.{language}.json"
    catalog = json.loads(path.read_text())
    expected = (
        json.dumps(
            {k: catalog[k] for k in sorted(catalog)},
            indent=2,
            ensure_ascii=False,
            separators=(",", ": "),
        )
        + "\n"
    )
    assert path.read_text() == expected


@pytest.mark.parametrize("language", LANGUAGES)
def test_catalog_passes_the_core_gate(language):
    """The real gate (`manage.py check_translation_catalogs --domain errors`),
    run in-process: coverage, ``{param}`` parity against the English canon,
    freshness, and the registry-export pairing that makes a translated key
    with no docs/errors.json entry an error."""
    from stapel_core.i18n import check_translation_catalogs, summarize

    issues = check_translation_catalogs(
        "errors",
        CATALOGS,
        source_texts=dict(STAPEL_CURRENCIES_ERRORS),
        languages=[language],
        owner="stapel_currencies",
        owners={code: "stapel_currencies" for code in STAPEL_CURRENCIES_ERRORS},
    )
    errors, _warnings = summarize(issues)
    assert errors == 0, [i.message for i in issues if i.level == "error"]
