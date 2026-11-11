import pytest

from scraper.match import countries_in, title_keywords


@pytest.mark.parametrize("title", ["SAP SuccessFactors Consultant", "Success Factors Specialist", "HRIS Analyst",
                                   "Senior HRIS-specialist"])
def test_titler_der_matcher(title):
    assert title_keywords(title)


@pytest.mark.parametrize("title", ["Chris Hansen Assistant", "HR Business Partner"])
def test_titler_der_ikke_matcher(title):
    assert title_keywords(title) == []


def test_soegeordets_navn():
    assert title_keywords("HRIS Analyst") == ["HRIS"]
    assert title_keywords("SAP SuccessFactors Consultant") == ["SuccessFactors"]


@pytest.mark.parametrize("text,expected", [
    ("Helsinki, FI", ["FI"]),
    ("London, United Kingdom", ["GB"]),
    ("Zürich, ZH, CH", ["CH"]),
    ("Munich, Bavaria, Germany", ["DE"]),
    ("Remote", []),
    ("Bucharest, Bucharest, RO", []),
    ("Dear colleagues, Munich", ["DE"]),          # "Dear" rammer ikke DE – kun Munich gør
    ("Dear Sir", []),
    ("Berlin | Stockholm", ["DE", "SE"]),
    ("Göteborg", ["SE"]),
    ("GOTEBORG, sweden", ["SE"]),
    ("Zurich", ["CH"]),
    ("Rue de Paris, Lyon", []),
    ("København K, DK", ["DK"]),
    ("", []),
])
def test_lande(text, expected):
    assert countries_in(text) == expected


def test_landekode_kun_som_selvstaendigt_led():
    assert countries_in("Munich") == ["DE"]            # via bynavnet
    assert countries_in("Chicago") == []               # "CH" er ikke et led
    assert countries_in("Finance Hub FIN") == ["FI"]   # FIN er selv et led
    assert countries_in("Berlin,DE") == ["DE"]
