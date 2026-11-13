import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import clean  # noqa: E402


def ts(text: str) -> pd.Timestamp:
    return pd.Timestamp(text, tz=clean.TZ)


def test_first_response_ignores_team_message_sent_before_the_lead():
    msgs = pd.DataFrame({
        "lead_key": ["a", "a", "a"],
        "direction": ["OUTBOUND", "INBOUND", "OUTBOUND"],
        "sent_at": [ts("2026-06-01 08:00"), ts("2026-06-01 09:00"), ts("2026-06-01 09:30")],
    })
    out = clean.first_response(msgs)
    assert out.loc["a", "tempo_resposta_min"] == 30
    assert out.loc["a", "msgs_equipe"] == 2


def test_first_response_beyond_cap_is_empty_and_no_reply_is_empty():
    msgs = pd.DataFrame({
        "lead_key": ["a", "a", "b"],
        "direction": ["INBOUND", "OUTBOUND", "INBOUND"],
        "sent_at": [ts("2026-06-01 09:00"), ts("2026-06-05 09:00"), ts("2026-06-01 09:00")],
    })
    out = clean.first_response(msgs)
    assert pd.isna(out.loc["a", "tempo_resposta_min"])
    assert pd.isna(out.loc["b", "primeira_resposta"])
    assert out.loc["b", "msgs_equipe"] == 0


def test_funnel_flags_treat_no_show_as_detour_and_lost_as_nothing_reached():
    df = pd.DataFrame({
        "stage_order": pd.array([2, 3, 4, 5, 6, 7], dtype="Int64"),
        "status": ["OPEN", "OPEN", "OPEN", "OPEN", "CONVERTED", "LOST"],
        "deal_status": [None, None, None, None, "WON", None],
        "closed_value": [None, None, None, None, 5000.0, None],
    })
    out = clean.derive_funnel(df)
    assert out["agendou"].tolist() == [False, True, True, True, True, False]
    assert out["faltou"].tolist() == [False, False, True, False, False, False]
    assert out["avaliado"].tolist() == [False, False, False, True, True, False]
    assert out["receita"].tolist() == [0, 0, 0, 0, 5000.0, 0]


def test_meta_spend_reads_brazilian_and_english_number_formats():
    ads = pd.DataFrame({
        "ID do anúncio": ["1", "1", "2", "3"],
        "Valor usado (BRL)": ["1.234,56", "980,00", "1234.56", "R$ 10,5"],
    })
    out = clean.spend_by_ad(ads).set_index("ad_id")["gasto"]
    assert round(out["1"], 2) == 2214.56
    assert round(out["2"], 2) == 1234.56
    assert round(out["3"], 2) == 10.5


def test_meta_spend_without_expected_columns_stops_with_headers():
    import pytest
    with pytest.raises(SystemExit, match="cabeçalhos"):
        clean.spend_by_ad(pd.DataFrame({"Nome": ["x"], "Gasto": ["1"]}))


def test_reentry_stalled_in_new_lead_is_dropped_but_two_real_sales_stay():
    df = pd.DataFrame({
        "lead_key": ["l1", "l2", "s1", "s2", "n1", "n2"],
        "contact_key": ["c1", "c1", "c2", "c2", "c3", "c3"],
        "periodo": ["atual"] * 6,
        "stage_order": pd.array([5, 1, 6, 6, 1, 1], dtype="Int64"),
        "created_at": [ts("2026-06-01"), ts("2026-07-01"), ts("2026-08-26"), ts("2026-08-26"),
                       ts("2026-06-02"), ts("2026-06-09")],
    })
    out = clean.drop_duplicates(df)
    assert sorted(out["lead_key"]) == ["l1", "n1", "s1", "s2"]
