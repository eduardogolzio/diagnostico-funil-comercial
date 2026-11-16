import math
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import dashboard_data as dd


def lead(**kw) -> dict:
    base = {
        "lead_key": "x",
        "periodo": "atual",
        "created_at": pd.Timestamp("2026-08-12 10:00", tz="America/Sao_Paulo"),
        "platform": "INSTAGRAM",
        "ad_id": "a1",
        "cadastro_manual": False,
        "mensagens_cobertas": True,
        "em_contato": True,
        "agendou": False,
        "avaliado": False,
        "vendeu": False,
        "receita": 0.0,
        "tempo_resposta_min": 60.0,
    }
    return base | kw


def frame(*rows: dict) -> pd.DataFrame:
    return pd.DataFrame([lead(lead_key=str(i), **r) for i, r in enumerate(rows)])


def test_filters_split_origin_and_treat_empty_lists_as_all():
    df = frame({}, {"cadastro_manual": True, "ad_id": None, "platform": None})
    assert len(dd.apply_filters(df, "Todos", [], [])) == 2
    assert len(dd.apply_filters(df, "Anúncio", [], [])) == 1
    assert dd.apply_filters(df, "Cadastro manual", [], [])["cadastro_manual"].all()
    assert len(dd.apply_filters(df, "Todos", ["Sem dado"], [])) == 1
    assert len(dd.apply_filters(df, "Todos", [], ["a1"])) == 1
    with pytest.raises(ValueError):
        dd.apply_filters(df, "Outro", [], [])


def test_kpis_use_contacted_and_booked_as_bases_and_ignore_manual_for_response():
    df = frame(
        {"agendou": True, "avaliado": True, "vendeu": True, "receita": 5000.0},
        {"agendou": True},
        {"em_contato": False},
        {"cadastro_manual": True, "tempo_resposta_min": 6000.0},
    )
    k = dd.compute_kpis(df)
    assert k.leads == 4
    assert k.booking_rate == pytest.approx(2 / 3)
    assert k.show_rate == pytest.approx(0.5)
    assert k.close_rate == pytest.approx(1.0)
    assert (k.sales, k.revenue, k.ticket) == (1, 5000.0, 5000.0)
    assert k.median_response_h == pytest.approx(1.0)


def test_kpis_on_empty_filter_are_nan_not_division_error():
    k = dd.compute_kpis(frame({}).iloc[0:0])
    assert k.leads == 0 and k.sales == 0
    assert all(
        math.isnan(v)
        for v in (k.booking_rate, k.show_rate, k.ticket, k.median_response_h)
    )


def test_funnel_passage_is_relative_to_previous_stage():
    df = frame(
        {"agendou": True, "avaliado": True},
        {"agendou": True},
        {},
        {"em_contato": False},
    )
    f = dd.funnel(df).set_index("etapa")
    assert f.loc["Em Contato", "passagem"] == pytest.approx(0.75)
    assert f.loc["Agendado", "passagem"] == pytest.approx(2 / 3)
    assert f.loc["Avaliado", "conversao"] == pytest.approx(0.25)
    assert (
        math.isnan(f.loc["Venda Realizada", "passagem"]) is False
        and f.loc["Venda Realizada", "leads"] == 0
    )


def test_heatmap_has_every_cell_and_puts_hour_18_in_evening_band():
    df = frame(
        {
            "created_at": pd.Timestamp("2026-08-12 18:00", tz="America/Sao_Paulo"),
            "agendou": True,
        }
    )
    grid = dd.entry_heatmap(df)
    assert len(grid) == 7 * 4
    hit = grid[grid["leads"] > 0]
    assert hit[["dia", "faixa", "agendou"]].values.tolist() == [["qua", "18h a 24h", 1]]
