"""Cálculos do dashboard sobre a base tratada, separados da tela para poderem ser testados.

As tabelas por segmento vêm de src/mine.py; aqui ficam só o filtro da lateral, os
indicadores do topo e os recortes que a mineração não grava.
"""

from dataclasses import dataclass

import pandas as pd

from mine import BUSINESS_HOURS, WEEKDAYS

ORIGINS = ("Todos", "Anúncio", "Cadastro manual")
PLATFORMS = {"INSTAGRAM": "Instagram", "FACEBOOK": "Facebook"}
STAGES = [
    ("Novo Lead", None),
    ("Em Contato", "em_contato"),
    ("Agendado", "agendou"),
    ("Avaliado", "avaliado"),
    ("Venda Realizada", "vendeu"),
]
HOUR_BANDS = [
    (0, 8, "00h a 08h"),
    (8, 12, "08h a 12h"),
    (12, 18, "12h a 18h"),
    (18, 24, "18h a 24h"),
]


@dataclass(frozen=True)
class Kpis:
    leads: int
    booking_rate: float  # agendados / em contato
    show_rate: float  # avaliados / agendados
    close_rate: float  # vendas / avaliados
    sales: int
    revenue: float
    ticket: float
    median_response_h: float  # só no recorte atual, onde existe histórico de mensagens


def ratio(num: float, den: float) -> float:
    return num / den if den else float("nan")


def apply_filters(
    df: pd.DataFrame, origin: str, platforms: list[str], ad_ids: list[str]
) -> pd.DataFrame:
    """Lista vazia em plataforma ou anúncio significa 'todos', como no multiselect da lateral."""
    if origin not in ORIGINS:
        raise ValueError(f"origem desconhecida: {origin}")
    out = df
    if origin == "Anúncio":
        out = out[~out["cadastro_manual"]]
    elif origin == "Cadastro manual":
        out = out[out["cadastro_manual"]]
    if platforms:
        out = out[out["platform"].map(PLATFORMS).fillna("Sem dado").isin(platforms)]
    if ad_ids:
        out = out[out["ad_id"].isin(ad_ids)]
    return out


def compute_kpis(df: pd.DataFrame) -> Kpis:
    sold = df[df["vendeu"]]
    covered = df[df["mensagens_cobertas"] & ~df["cadastro_manual"]]
    return Kpis(
        leads=len(df),
        booking_rate=ratio(df["agendou"].sum(), df["em_contato"].sum()),
        show_rate=ratio(df["avaliado"].sum(), df["agendou"].sum()),
        close_rate=ratio(len(sold), df["avaliado"].sum()),
        sales=len(sold),
        revenue=float(df["receita"].sum()),
        ticket=ratio(sold["receita"].sum(), len(sold)),
        median_response_h=float(covered["tempo_resposta_min"].median()) / 60
        if len(covered)
        else float("nan"),
    )


def funnel(df: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por período e etapa: leads, passagem da etapa anterior e conversão desde o topo."""
    rows = []
    for period, g in df.groupby("periodo"):
        counts = [len(g) if col is None else int(g[col].sum()) for _, col in STAGES]
        for i, (name, _) in enumerate(STAGES):
            rows.append(
                {
                    "periodo": period,
                    "etapa": name,
                    "leads": counts[i],
                    "passagem": ratio(counts[i], counts[i - 1]) if i else float("nan"),
                    "conversao": ratio(counts[i], counts[0]),
                }
            )
    return pd.DataFrame(rows)


def entry_heatmap(df: pd.DataFrame) -> pd.DataFrame:
    """Leads por dia da semana e faixa de hora de entrada, com agendados de cada célula."""
    hour = df["created_at"].dt.hour
    band = pd.Series(pd.NA, index=df.index, dtype="object")
    for start, end, label in HOUR_BANDS:
        band = band.mask(hour.ge(start) & hour.lt(end), label)
    day = df["created_at"].dt.weekday.map(dict(enumerate(WEEKDAYS)))
    grid = (
        df.assign(dia=day, faixa=band)
        .groupby(["dia", "faixa"])
        .agg(leads=("lead_key", "size"), agendou=("agendou", "sum"))
        .reset_index()
    )
    full = pd.MultiIndex.from_product(
        [WEEKDAYS, [b[2] for b in HOUR_BANDS]], names=["dia", "faixa"]
    )
    return grid.set_index(["dia", "faixa"]).reindex(full, fill_value=0).reset_index()


def business_hours_label() -> str:
    return f"seg a sex, {BUSINESS_HOURS[0]}h às {BUSINESS_HOURS[1]}h"
