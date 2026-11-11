from datetime import date

import pytest

from scraper.common import parse_date, today_utc

TODAY = date(2026, 11, 12)


@pytest.mark.parametrize("text,expected", [
    ("2026-11-10", "2026-11-10"),
    ("2026-11-10T08:30:00+01:00", "2026-11-10"),
    ("10 Nov 2026", "2026-11-10"),
    ("10 November 2026", "2026-11-10"),
    ("10.11.2026", "2026-11-10"),
    ("1.2.2026", "2026-02-01"),
    ("Nov 10, 2026", "2026-11-10"),
    ("November 10th, 2026", "2026-11-10"),
    ("Posted on 3 Mar 2026", "2026-03-03"),
    # tysk, dansk, svensk, finsk
    ("10. November 2026", "2026-11-10"),
    ("3. März 2026", "2026-03-03"),
    ("15. Dezember 2026", "2026-12-15"),
    ("10. november 2026", "2026-11-10"),
    ("5. maj 2026", "2026-05-05"),
    ("12 augusti 2026", "2026-08-12"),
    ("10. marraskuuta 2026", "2026-11-10"),
    ("2. tammikuuta 2026", "2026-01-02"),
    ("20. joulukuuta 2026", "2026-12-20"),
    # unix
    (1762732800, "2025-11-10"),
    ("1762732800", "2025-11-10"),
    (1762732800000, "2025-11-10"),
    ("1762732800000", "2025-11-10"),
    # relative
    ("Posted 3 Days Ago", "2026-11-09"),
    ("Posted 1 Day Ago", "2026-11-11"),
    ("today", "2026-11-12"),
    ("Posted Today", "2026-11-12"),
    ("yesterday", "2026-11-11"),
    ("Posted Yesterday", "2026-11-11"),
    ("i dag", "2026-11-12"),
    ("i går", "2026-11-11"),
    ("heute", "2026-11-12"),
    ("gestern", "2026-11-11"),
    ("5 dage siden", "2026-11-07"),
    # ikke en dato
    ("Posted 30+ Days Ago", None),
    ("", None),
    (None, None),
    ("snart", None),
    ("31.02.2026", None),
    ("2026-13-01", None),
])
def test_parse_date(text, expected):
    assert parse_date(text, today=TODAY) == expected


def test_relativ_dato_bruger_dagens_dato_som_standard():
    assert parse_date("today") == today_utc().isoformat()
