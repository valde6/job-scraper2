"""Optager en virksomheds svar til tests/fixtures/<navn>/ (til tests uden netværk).

    python -m scraper.record "Wärtsilä"

Kører `python -m scraper.run --only <navn> --dry-run` med SCRAPER_RECORD sat. Brug SCRAPER_REPLAY=<mappen> til at afspille.
"""
from __future__ import annotations

import os
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def slug(name: str) -> str:
    folded = "".join(c for c in unicodedata.normalize("NFKD", name) if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "_", folded.lower()).strip("_")


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print(__doc__)
        return 2
    target = ROOT / "tests" / "fixtures" / slug(argv[0])
    os.environ["SCRAPER_RECORD"] = str(target)
    from scraper import run
    code = run.main(["--only", argv[0], "--dry-run"])
    print(f"Svar gemt i {target}")
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
