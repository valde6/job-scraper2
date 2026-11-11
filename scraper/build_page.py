"""Indsætter data/jobs.json i site/template.html og skriver site/jobradar.html (artefakt-fragmentet).

    python -m scraper.build_page
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "jobs.json"
TEMPLATE_FILE = ROOT / "site" / "template.html"
OUT_FILE = ROOT / "site" / "jobradar.html"

JOB_FIELDS = ("title", "company", "url", "location", "country", "countries", "posted", "first_seen", "date_basis", "active")
SOURCE_FIELDS = ("company", "label", "ok", "matched", "error")

# Markøren: alt mellem <script ... id="jobdata"> og </script> er indholdet, der erstattes.
_MARKER = re.compile(r'(<script type="application/json" id="jobdata">)(.*?)(</script>)', re.S)


def load_data(path: Path = DATA_FILE) -> dict:
    if not path.exists():
        return {"generated_at": None, "keywords": [], "countries": [], "jobs": [], "sources": [], "not_covered": []}
    return json.loads(path.read_text(encoding="utf-8"))


def make_payload(data: dict) -> dict:
    """Kun aktive job og kun de felter, siden bruger."""
    return {
        "generated_at": data.get("generated_at"),
        "keywords": data.get("keywords", []),
        "countries": data.get("countries", []),
        "jobs": [{k: j.get(k) for k in JOB_FIELDS} for j in data.get("jobs", []) if j.get("active", True)],
        "sources": [{k: s.get(k) for k in SOURCE_FIELDS} for s in data.get("sources", [])],
        "not_covered": data.get("not_covered", []),
    }


def render(template: str, payload: dict) -> str:
    if len(_MARKER.findall(template)) != 1:
        raise ValueError('skabelonen skal indeholde præcis én <script type="application/json" id="jobdata">…</script>')
    blob = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    return _MARKER.sub(lambda m: m.group(1) + blob + m.group(3), template, count=1)


def build(data_file: Path = DATA_FILE, template_file: Path = TEMPLATE_FILE, out_file: Path = OUT_FILE) -> Path:
    html = render(template_file.read_text(encoding="utf-8"), make_payload(load_data(data_file)))
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(html, encoding="utf-8")
    return out_file


def main() -> int:
    try:
        out = build()
    except (ValueError, OSError) as e:
        print(f"build_page fejlede: {e}", file=sys.stderr)
        return 1
    print(f"Skrev {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
