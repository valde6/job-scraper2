"""Den eneste definition af et match: søgeord i titlen og land i lokationen. Læser config/settings.yaml én gang."""
from __future__ import annotations

import re
import unicodedata
from functools import lru_cache
from pathlib import Path

import yaml

SETTINGS_FILE = Path(__file__).resolve().parent.parent / "config" / "settings.yaml"
# Landekoder (DE, CH …) må kun stå som selvstændigt led – ellers rammer "DE" ordet "Dear" og "CH" "Munich"
_CODE_BEFORE = r"(?<![^\s,;|/(])"
_CODE_AFTER = r"(?![^\s,;|/)])"


@lru_cache(maxsize=1)
def settings() -> dict:
    return yaml.safe_load(SETTINGS_FILE.read_text(encoding="utf-8"))


def _fold(s: str) -> str:
    """Små bogstaver uden accenter: "Göteborg" → "goteborg"."""
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)).lower()


def _is_code(alias: str) -> bool:
    return alias.isascii() and alias.isalpha() and alias.isupper() and len(alias) <= 3


@lru_cache(maxsize=1)
def _compiled() -> tuple[list[tuple[str, re.Pattern]], list[tuple[str, re.Pattern]]]:
    keywords = [(k["name"], re.compile(k["pattern"], re.I)) for k in settings()["keywords"]]
    countries = []
    for code, aliases in settings()["countries"].items():
        parts = []
        for a in aliases:
            if _is_code(a):
                parts.append(("code", re.escape(a)))
            else:
                parts.append(("word", r"\s+".join(re.escape(w) for w in _fold(a).split())))
        words = "|".join(p for kind, p in parts if kind == "word")
        codes = "|".join(p for kind, p in parts if kind == "code")
        countries.append((code, (re.compile(rf"(?<!\w)(?:{words})(?!\w)") if words else None,
                                 re.compile(rf"{_CODE_BEFORE}(?:{codes}){_CODE_AFTER}") if codes else None)))
    return keywords, countries


def country_codes() -> list[str]:
    return list(settings()["countries"])


def keyword_names() -> list[str]:
    return [k["name"] for k in settings()["keywords"]]


def title_keywords(title: str) -> list[str]:
    """Navnene på de søgeord (fra settings.yaml), der matcher titlen."""
    return [name for name, rx in _compiled()[0] if rx.search(title or "")]


def countries_in(text: str) -> list[str]:
    """ISO-koder for de lande i settings, som teksten nævner – i den rækkefølge de første gang optræder."""
    text = text or ""
    folded = _fold(text)
    found: list[tuple[int, str]] = []
    for code, (words_rx, codes_rx) in _compiled()[1]:
        pos = [m.start() for m in (words_rx.finditer(folded) if words_rx else [])]
        pos += [m.start() for m in (codes_rx.finditer(text) if codes_rx else [])]
        if pos:
            found.append((min(pos), code))
    return [code for _, code in sorted(found)]
