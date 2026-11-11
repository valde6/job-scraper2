import json

from scraper import health


def h(ok=True, listed=10, date="2026-11-01"):
    return {"date": date, "ok": ok, "listed": listed if ok else None}


def codes(history):
    return [c for c, _ in health.problems(history)]


# ---------------------------------------------------------------- regel 1: fejl i 2 kørsler i træk
def test_en_enkelt_fejl_giver_ikke_alarm():
    assert codes([h(), h(), h(ok=False)]) == []


def test_to_fejl_i_traek_giver_alarm():
    found = health.problems([h(), h(ok=False), h(ok=False)])
    assert [c for c, _ in found] == ["fejl"]
    assert "2 kørsler i træk" in found[0][1]


def test_fejl_afbrudt_af_succes_taeller_ikke():
    assert codes([h(ok=False), h(), h(ok=False)]) == []


# ---------------------------------------------------------------- regel 2: listed 0 i 3 kørsler i træk
def test_listed_nul_to_gange_giver_ikke_alarm():
    assert codes([h(), h(listed=0), h(listed=0)]) == []


def test_listed_nul_tre_gange_i_traek_giver_alarm():
    assert "tom" in codes([h(), h(listed=0), h(listed=0), h(listed=0)])


def test_listed_nul_afbrudt_af_fejl_taeller_ikke():
    assert "tom" not in codes([h(listed=0), h(ok=False), h(listed=0), h(listed=0)])


def test_kilde_der_altid_har_nul_alarmerer_efter_tre():
    assert codes([h(listed=0)] * 3) == ["tom"]


# ---------------------------------------------------------------- regel 3: under 20 % af median
def test_fald_under_20_procent_af_median_giver_alarm():
    found = health.problems([h(listed=100)] * 7 + [h(listed=19)])
    assert [c for c, _ in found] == ["fald"]
    assert "median på 100" in found[0][1]


def test_præcis_20_procent_giver_ikke_alarm():
    assert codes([h(listed=100)] * 7 + [h(listed=20)]) == []


def test_median_bruger_kun_de_7_seneste_kørsler_med_data():
    # de gamle 1000'er ligger uden for vinduet, og fejl-kørslen tæller ikke med som data
    hist = [h(listed=1000)] * 3 + [h(listed=100)] * 6 + [h(ok=False), h(listed=15)]
    assert codes(hist) == ["fald"]
    assert codes(hist[:-1] + [h(listed=25)]) == []


def test_fald_kraever_nok_data_og_en_vis_stoerrelse():
    assert codes([h(listed=100), h(listed=100), h(listed=1)]) == []      # kun 2 kørsler med data
    assert codes([h(listed=2)] * 5 + [h(listed=0)]) == []               # median 2: for lille til at sige noget


def test_listed_nul_paa_stor_kilde_er_et_fald_med_det_samme():
    assert codes([h(listed=50)] * 4 + [h(listed=0)]) == ["fald"]


def test_sund_kilde_har_ingen_problemer():
    assert codes([h(listed=100), h(listed=90), h(listed=110), h(listed=95)]) == []


# ---------------------------------------------------------------- historik
def src(company="A", label=None, ok=True, listed=10, error=None, type_="successfactors"):
    return {"company": company, "label": label, "type": type_, "ok": ok, "listed": listed, "matched": 0,
            "error": error, "seconds": 1.0, "last_ok": None}


def test_historik_holder_14_kørsler_og_bruger_label_i_navnet():
    state = {}
    for i in range(1, 21):
        state = health.update_history(state, [src("KPMG", "Danmark"), src("Ambu")], f"2026-10-{i:02d}")
    assert set(state["sources"]) == {"KPMG – Danmark", "Ambu"}
    rows = state["sources"]["Ambu"]
    assert len(rows) == 14
    assert rows[0]["date"] == "2026-10-07" and rows[-1]["date"] == "2026-10-20"


def test_samme_dato_to_gange_erstatter_i_stedet_for_at_taelle_dobbelt():
    state = health.update_history({}, [src(ok=False, listed=0, error="boom")], "2026-11-11")
    state = health.update_history(state, [src(ok=False, listed=0, error="boom")], "2026-11-11")
    assert state["sources"]["A"] == [{"date": "2026-11-11", "ok": False, "listed": None}]


def test_kilder_der_er_fjernet_fra_config_glemmes():
    state = health.update_history({}, [src("A"), src("B")], "2026-11-10")
    state = health.update_history(state, [src("A")], "2026-11-11")
    assert list(state["sources"]) == ["A"]


# ---------------------------------------------------------------- main: filer
def write_jobs(path, day, sources):
    path.write_text(json.dumps({"generated_at": f"{day}T04:20:00+00:00", "sources": sources}), encoding="utf-8")


def run_health(tmp_path, day, sources):
    jobs, hfile, alert = tmp_path / "jobs.json", tmp_path / "health.json", tmp_path / "health_alert.md"
    write_jobs(jobs, day, sources)
    assert health.main([], jobs_file=jobs, health_file=hfile, alert_file=alert) == 0
    return alert


def test_main_skriver_alarm_naar_kilde_fejler_to_gange_og_fjerner_den_igen(tmp_path):
    bad = src("Ambu", ok=False, listed=0, error="HTTPError: 503", type_="successfactors")
    assert not run_health(tmp_path, "2026-11-10", [bad, src("Nordea", type_="nordea")]).exists()   # første fejl: stille
    alert = run_health(tmp_path, "2026-11-11", [bad, src("Nordea", type_="nordea")])
    text = alert.read_text(encoding="utf-8")
    assert "**Ambu** (successfactors): fejl" in text
    assert "HTTPError: 503" in text
    assert "docs/KILDER.md" in text
    assert "Nordea" not in text
    assert text.count("\n- ") == 1                                                                # én linje pr. kilde
    assert not run_health(tmp_path, "2026-11-12", [src("Ambu"), src("Nordea", type_="nordea")]).exists()


def test_main_uden_jobs_json_fejler_uden_at_skrive_noget(tmp_path):
    assert health.main([], jobs_file=tmp_path / "findes_ikke.json", health_file=tmp_path / "h.json",
                       alert_file=tmp_path / "a.md") == 1
    assert not (tmp_path / "h.json").exists()
