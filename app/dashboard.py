"""Dashboard do diagnóstico de funil comercial.

Uso:
    streamlit run app/dashboard.py
"""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "app"))
import charts as ch
from charts import Segment

import dashboard_data as dd
import mine

st.set_page_config(
    page_title="Diagnóstico de funil comercial",
    layout="wide",
    initial_sidebar_state="expanded",
)

CSS = """
<style>
.block-container { padding-top: 2rem; max-width: 1320px; }
h1 { font-size: 1.6rem !important; font-weight: 600 !important; letter-spacing: -0.01em; margin-bottom: 0 !important; }
.sub { color: #6b6a66; font-size: .95rem; margin: .2rem 0 1rem; }
.finding { font-size: 1.05rem; color: #0b0b0b; max-width: 68ch; margin: 0 0 1.2rem; line-height: 1.5; }
.strip { display: grid; grid-template-columns: repeat(6, 1fr); border: 1px solid #e7e6e2; border-radius: 10px;
         background: #fff; margin-bottom: 1.4rem; }
.strip > div { padding: 14px 18px; border-left: 1px solid #e7e6e2; }
.strip > div:first-child { border-left: 0; }
.strip .k { color: #6b6a66; font-size: .85rem; }
.strip .v { color: #0b0b0b; font-size: 1.55rem; font-weight: 500; line-height: 1.3; font-variant-numeric: tabular-nums; }
.strip .d { font-size: .82rem; color: #6b6a66; font-variant-numeric: tabular-nums; }
.q { font-weight: 600; color: #0b0b0b; font-size: 1rem; margin: .4rem 0 0; }
.qn { color: #6b6a66; font-size: .88rem; margin: .1rem 0 .4rem; max-width: 70ch; }
@media (max-width: 900px) { .strip { grid-template-columns: repeat(2, 1fr); }
  .strip > div:nth-child(odd) { border-left: 0; } .strip > div { border-top: 1px solid #e7e6e2; } }
</style>
"""
PERIOD_NAMES = {"atual": "01/06 a 31/08/2026", "anterior": "01/03 a 31/05/2026"}
TONES = {"good": "#1d7f4e", "bad": "#c0392b", "flat": "#6b6a66"}
RESPONSE_ORDER = mine.RESPONSE_LABELS + ["sem resposta em 72 h", "sem conversa"]


@st.cache_data
def load() -> pd.DataFrame:
    return mine.load()


def delta(current: float, previous: float, kind: str, good_when_up: bool = True) -> str:
    """Texto da variação contra o trimestre anterior, colorido por bom ou ruim, nunca por subir ou descer."""
    if current != current or previous != previous:
        return "<span class='d'>sem comparação</span>"
    diff = current - previous
    if kind == "pp":
        text = f"{diff * 100:+.1f}".replace(".", ",") + " p.p."
    elif kind == "pct":
        text = f"{diff / previous * 100:+.0f}%" if previous else "novo"
    else:
        text = f"{diff:+.0f}"
    # Cor inline: o markdown do Streamlit descarta class em span aninhado.
    tone = (
        TONES["flat"]
        if abs(diff) < 1e-9
        else TONES["good" if (diff > 0) == good_when_up else "bad"]
    )
    return f"<span class='d'><span style='color:{tone};font-weight:500'>{text}</span> vs mar a mai</span>"


def kpi_strip(now: dd.Kpis, before: dd.Kpis) -> str:
    response = (
        "-"
        if now.median_response_h != now.median_response_h
        else f"{now.median_response_h:.1f} h"
    )
    cells = [
        ("Leads", f"{now.leads}", delta(now.leads, before.leads, "pct")),
        (
            "Agendamento",
            ch.pct(now.booking_rate),
            delta(now.booking_rate, before.booking_rate, "pp"),
        ),
        (
            "Comparecimento",
            ch.pct(now.show_rate, 0),
            delta(now.show_rate, before.show_rate, "pp"),
        ),
        ("Vendas", f"{now.sales}", delta(now.sales, before.sales, "abs")),
        (
            "Receita",
            ch.brl(now.revenue),
            f"<span class='d'>ticket {ch.brl(now.ticket)}</span>",
        ),
        (
            "1ª resposta",
            response.replace(".", ","),
            "<span class='d'>mediana, desde 07/08</span>",
        ),
    ]
    body = "".join(
        f"<div><div class='k'>{k}</div><div class='v'>{v}</div>{d}</div>"
        for k, v, d in cells
    )
    return f"<div class='strip'>{body}</div>"


def finding(now: dd.Kpis, before: dd.Kpis) -> str:
    if now.leads == 0:
        return "Nenhum lead no filtro escolhido."
    if before.leads == 0:
        return (
            f"Em jun a ago, {ch.pct(now.booking_rate)} dos atendidos agendaram, {ch.pct(now.show_rate, 0)} "
            f"dos agendados compareceram e {ch.pct(now.close_rate, 0)} dos avaliados fecharam. "
            "Sem leads deste filtro em mar a mai para comparar."
        )
    return (
        f"De mar a mai para jun a ago, o agendamento foi de {ch.pct(before.booking_rate)} para "
        f"{ch.pct(now.booking_rate)} dos atendidos e o comparecimento de {ch.pct(before.show_rate, 0)} para "
        f"{ch.pct(now.show_rate, 0)} dos agendados. O fechamento de quem foi avaliado ficou em "
        f"{ch.pct(now.close_rate, 0)} (antes {ch.pct(before.close_rate, 0)})."
    )


def heading(question: str, note: str) -> None:
    st.markdown(
        f"<p class='q'>{question}</p><p class='qn'>{note}</p>", unsafe_allow_html=True
    )


def chart(fig) -> None:
    st.plotly_chart(fig, width="stretch", config=ch.CHART_CONFIG)


def booking_split(
    labels: list[str],
    booked: list[int],
    bases: list[int],
    x_title: str,
    extras: list[str] | None = None,
) -> None:
    """Agendou contra não agendou por grupo: o desenho comum de P1, P3 e P5."""
    extras = extras or [""] * len(labels)
    chart(
        ch.split_bars(
            labels,
            [
                Segment("Agendou", booked, ch.ADVANCED),
                Segment(
                    "Não agendou",
                    [b - a for a, b in zip(booked, bases)],
                    ch.STOPPED,
                    ch.INK,
                ),
            ],
            [
                ch.share_note(a, b, "agendou", e)
                for a, b, e in zip(booked, bases, extras)
            ],
            x_title,
        )
    )


@st.cache_data
def ad_names(df: pd.DataFrame) -> pd.Series:
    """Nome curto por anúncio, numerado pelo volume de jun a ago sem filtro: o nome não muda com o filtro."""
    counts = df[df["periodo"] == "atual"]["ad_id"].value_counts().reset_index()
    counts = counts.sort_values(["count", "ad_id"], ascending=[False, True])
    return pd.Series(
        [f"Anúncio {i + 1}" for i in range(len(counts))], index=counts["ad_id"].tolist()
    )


def sidebar(df: pd.DataFrame) -> tuple[str, list[str], list[str]]:
    with st.sidebar:
        st.markdown("**Filtros**")
        st.caption(
            f"Recorte {PERIOD_NAMES['atual']}, comparado a {PERIOD_NAMES['anterior']}."
        )
        origin = st.radio("Origem do lead", dd.ORIGINS)
        platforms = st.multiselect(
            "Plataforma do anúncio",
            ["Instagram", "Facebook", "Sem dado"],
            placeholder="Todas",
        )
        names = ad_names(df)
        ad_ids = st.multiselect(
            "Anúncio",
            list(names.index),
            placeholder="Todos os anúncios",
            format_func=lambda a: names[a],
        )
        st.divider()
        st.caption(
            "Fonte: CRM da clínica (leads, etapas, mensagens) e Meta Ads. Dados anonimizados."
        )
    return origin, platforms, ad_ids


def tab_funnel(df: pd.DataFrame) -> None:
    f = dd.funnel(df)
    now, before = (
        f[f["periodo"] == "atual"],
        f[f["periodo"] == "anterior"].set_index("etapa"),
    )
    left, right = st.columns([1, 1.25], gap="large")
    with left:
        heading(
            "Quantos chegam a cada etapa",
            "Jun a ago. Rótulo: leads e % do total que entrou.",
        )
        chart(
            ch.funnel_bars(
                now["etapa"].tolist(), now["leads"].tolist(), int(now["leads"].iloc[0])
            )
        )
    with right:
        heading(
            "Onde a passagem piorou",
            "Cada barra são os leads de uma etapa em jun a ago, divididos entre quem avançou para a "
            "seguinte e quem parou. Ao lado, a taxa de mar a mai para comparar.",
        )
        stages, counts = now["etapa"].tolist(), now["leads"].astype(int).tolist()
        labels = [f"{stages[i - 1]} → {stages[i]}" for i in range(1, len(stages))]
        advanced, bases = counts[1:], counts[:-1]
        extras = [
            f"antes {ch.pct(before['passagem'].get(s, float('nan')))}"
            for s in stages[1:]
        ]
        chart(
            ch.split_bars(
                labels,
                [
                    Segment("Avançou", advanced, ch.ADVANCED),
                    Segment(
                        "Parou",
                        [b - a for a, b in zip(advanced, bases)],
                        ch.STOPPED,
                        ch.INK,
                    ),
                ],
                [
                    ch.share_note(a, b, "avançou", e)
                    for a, b, e in zip(advanced, bases, extras)
                ],
                "leads",
            )
        )
    show = f.assign(
        passagem=f["passagem"].map(ch.pct),
        conversao=f["conversao"].map(ch.pct),
        periodo=f["periodo"].map({"atual": "Jun a ago", "anterior": "Mar a mai"}),
    )
    with st.expander("Tabela do funil"):
        st.dataframe(show, hide_index=True, width="stretch")


def tab_service(current: pd.DataFrame) -> None:
    covered = current[current["mensagens_cobertas"] & ~current["cadastro_manual"]]
    st.caption(
        f"Só leads de anúncio que entraram a partir de 07/08/2026, quando começa o histórico de "
        f"mensagens: {len(covered)} leads no filtro."
    )
    if covered.empty:
        st.info("Nenhum lead com histórico de mensagens neste filtro.")
        return
    left, right = st.columns(2, gap="large")
    with left:
        rt = (
            mine.response_time(covered)
            .set_index("faixa_resposta")
            .reindex(RESPONSE_ORDER)
            .dropna(subset=["leads"])
        )
        heading(
            "P1. Responder rápido faz agendar mais?",
            "Leads por tempo até a 1ª resposta da equipe, divididos entre quem agendou e quem não. "
            "Faixas com poucos leads oscilam muito.",
        )
        booking_split(
            rt.index.tolist(),
            rt["agendou"].astype(int).tolist(),
            rt["leads"].astype(int).tolist(),
            "leads",
        )
        eng = mine.engagement(covered)
        heading(
            "P3. Quem conversa, agenda?",
            "Leads pelo número de mensagens que mandaram, divididos entre "
            "quem agendou e quem não.",
        )
        booking_split(
            [f"{m} msg" for m in eng["msgs_do_lead"]],
            eng["agendou"].tolist(),
            eng["leads"].tolist(),
            "leads",
        )
    with right:
        grid = dd.entry_heatmap(current[~current["cadastro_manual"]])
        days, bands = mine.WEEKDAYS, [b[2] for b in dd.HOUR_BANDS]
        leads = grid.pivot(index="dia", columns="faixa", values="leads").reindex(
            index=days, columns=bands
        )
        booked = grid.pivot(index="dia", columns="faixa", values="agendou").reindex(
            index=days, columns=bands
        )
        heading(
            "P2. Quando o lead chega?",
            "Leads de anúncio por dia e hora de entrada, jun a ago. "
            "Passe o mouse para ver quantos agendaram.",
        )
        chart(ch.heatmap(days, bands, leads.values.tolist(), booked.values.tolist()))
        hours = mine.entry_time(covered).set_index("entrada")
        for col, (name, row) in zip(st.columns(len(hours)), hours.iterrows()):
            wait = row["mediana_resposta_min"]
            col.metric(
                f"1ª resposta, {name}",
                "-" if wait != wait else f"{wait / 60:.1f} h".replace(".", ","),
                help=f"Mediana. Horário comercial presumido: {dd.business_hours_label()}.",
            )


def tab_show_up(current: pd.DataFrame) -> None:
    ns = mine.no_show(current)
    ns = ns[ns["espera"] != "sem data"] if not ns.empty else ns
    if ns.empty:
        st.info("Nenhum agendamento com data de consulta neste filtro.")
        return
    booked, missed = int(current["agendou"].sum()), int(current["faltou"].sum())
    left, right = st.columns([1.4, 1], gap="large")
    with left:
        heading(
            "P4. Esperar mais pela consulta faz faltar mais?",
            "Cada barra são as consultas marcadas na faixa de espera (dias entre a entrada do lead "
            "e a data da consulta), divididas entre quem compareceu e quem faltou.",
        )
        pending = (
            (ns["agendados"] - ns["faltou"] - ns["avaliado"]).clip(lower=0).tolist()
        )
        segments = [
            Segment("Compareceu", ns["avaliado"].tolist(), ch.ADVANCED),
            Segment("Faltou", ns["faltou"].tolist(), ch.MISSED),
        ]
        if any(pending):
            segments.append(Segment("Ainda sem desfecho", pending, ch.STOPPED, ch.INK))
        chart(
            ch.split_bars(
                ns["espera"].astype(str).tolist(),
                segments,
                [
                    ch.share_note(m, t, "faltou")
                    for m, t in zip(ns["faltou"], ns["agendados"])
                ],
                "consultas marcadas",
            )
        )
    with right:
        st.metric("Agendados", booked)
        st.metric("Faltaram", missed, help="Lead que está na etapa Faltante do CRM.")
        st.metric(
            "Taxa de falta", ch.pct(missed / booked if booked else float("nan"), 0)
        )
        worst = ns.loc[ns["faltou"].idxmax()]
        if worst["faltou"] > 0:
            st.caption(
                f"A faixa de {worst['espera']} concentra as faltas: {int(worst['faltou'])} de {missed}. "
                "Lembrete na véspera e confirmação no dia atacam essa janela."
            )


def tab_ads(current: pd.DataFrame, names: pd.Series) -> None:
    from_ads = current[~current["cadastro_manual"]]
    table = mine.ads(from_ads)
    if table.empty:
        st.info("Nenhum lead de anúncio neste filtro.")
        return
    order = pd.Series(range(len(names)), index=names.index)
    table = table.assign(
        anuncio=table["ad_id"].map(names).fillna("Anúncio sem id"),
        ordem=table["ad_id"].map(order),
    ).sort_values(["leads", "ordem"], ascending=[False, True], na_position="last")
    top = table.head(10)
    left, right = st.columns([1.4, 1], gap="large")
    with left:
        heading(
            "P5. Quais anúncios trazem paciente que agenda?",
            "Os 10 anúncios com mais leads no recorte, divididos entre quem agendou e quem não.",
        )
        sales = [
            f"{v} venda" + ("s" if v > 1 else "") if v else "" for v in top["vendeu"]
        ]
        booking_split(
            top["anuncio"].tolist(),
            top["agendou"].tolist(),
            top["leads"].tolist(),
            "leads",
            sales,
        )
    with right:
        st.metric("Leads de anúncio", len(from_ads))
        st.metric("Vendas vindas de anúncio", int(from_ads["vendeu"].sum()))
        if "custo_por_lead" not in table.columns:
            st.warning(
                "Custo por lead, CAC e ROAS aguardam a exportação do Meta Ads (data/raw/meta_ads.csv)."
            )
    cols = [
        "anuncio",
        "ad_id",
        "leads",
        "agendou",
        "taxa_agendamento",
        "vendeu",
        "receita",
    ]
    cols += [
        c for c in ("gasto", "custo_por_lead", "custo_por_venda") if c in table.columns
    ]
    with st.expander("Todos os anúncios"):
        st.dataframe(
            table[cols],
            hide_index=True,
            width="stretch",
            column_config={
                "taxa_agendamento": st.column_config.NumberColumn(format="percent"),
                "receita": st.column_config.NumberColumn(format="R$ %.0f"),
            },
        )


def tab_revenue(df: pd.DataFrame, current: pd.DataFrame) -> None:
    left, right = st.columns([1.3, 1], gap="large")
    with left:
        heading(
            "De onde vem a receita",
            "Receita fechada de cada trimestre, dividida entre paciente vindo do anúncio e paciente "
            "cadastrado à mão pela equipe.",
        )
        sold = df[df["vendeu"]]
        periods = [("atual", "Jun a ago"), ("anterior", "Mar a mai")]
        by = {k: sold[sold["periodo"] == k] for k, _ in periods}
        ads_rev = [
            float(by[k].loc[~by[k]["cadastro_manual"], "receita"].sum())
            for k, _ in periods
        ]
        manual_rev = [
            float(by[k].loc[by[k]["cadastro_manual"], "receita"].sum())
            for k, _ in periods
        ]
        notes = [
            f"<b>{ch.brl(by[k]['receita'].sum())}</b><br><span style='color:{ch.MUTED}'>({len(by[k])} vendas, "
            f"{int(by[k]['cadastro_manual'].sum())} de cadastro manual)</span>"
            for k, _ in periods
        ]
        chart(
            ch.split_bars(
                [name for _, name in periods],
                [
                    Segment("Anúncio", ads_rev, ch.ADVANCED),
                    Segment("Cadastro manual", manual_rev, ch.MANUAL),
                ],
                notes,
                "receita (R$)",
                money=True,
            )
        )
    with right:
        heading(
            "Quanto vale fechar cada vazamento",
            "Estimativa mantendo as taxas seguintes e o ticket médio do recorte.",
        )
        lost = mine.lost_revenue(current).dropna(subset=["vendas_extra"])
        for row in lost.itertuples():
            st.metric(
                row.cenario[:1].upper() + row.cenario[1:],
                ch.brl(row.valor),
                help=f"cerca de {row.vendas_extra:.1f} venda(s) a mais".replace(
                    ".", ","
                ),
            )
        if lost.empty:
            st.caption("Nenhum vazamento a estimar neste filtro.")


def main() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
    df = load()
    origin, platforms, ad_ids = sidebar(df)
    view = dd.apply_filters(df, origin, platforms, ad_ids)
    current, previous = (
        view[view["periodo"] == "atual"],
        view[view["periodo"] == "anterior"],
    )
    now, before = dd.compute_kpis(current), dd.compute_kpis(previous)

    st.markdown(
        "<h1>Diagnóstico de funil comercial</h1>"
        "<p class='sub'>Clínica odontológica em Campina Grande - PB · Nexus Assessoria</p>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<p class='finding'>{finding(now, before)}</p>", unsafe_allow_html=True
    )
    st.markdown(kpi_strip(now, before), unsafe_allow_html=True)
    if current.empty:
        st.info(
            "Nenhum lead no recorte com esses filtros. Limpe algum filtro na lateral."
        )
        return

    tabs = st.tabs(["Funil", "Atendimento", "Comparecimento", "Anúncios", "Receita"])
    with tabs[0]:
        tab_funnel(view)
    with tabs[1]:
        tab_service(current)
    with tabs[2]:
        tab_show_up(current)
    with tabs[3]:
        tab_ads(current, ad_names(df))
    with tabs[4]:
        tab_revenue(view, current)


main()
