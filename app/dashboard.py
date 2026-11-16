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
.strip .bad { color: #c0392b; } .strip .good { color: #1d7f4e; }
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
            "-"
            if now.median_response_h != now.median_response_h
            else f"{now.median_response_h:.1f} h".replace(".", ","),
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


def sidebar(df: pd.DataFrame) -> tuple[str, list[str], list[str]]:
    with st.sidebar:
        st.markdown("**Filtros**")
        st.caption(
            f"Recorte {PERIOD_NAMES['atual']}, comparado a {PERIOD_NAMES['anterior']}."
        )
        origin = st.radio("Origem do lead", dd.ORIGINS, horizontal=False)
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


@st.cache_data
def ad_names(df: pd.DataFrame) -> pd.Series:
    """Nome curto por anúncio, numerado pelo volume de jun a ago sem filtro: o nome não muda com o filtro."""
    counts = df[df["periodo"] == "atual"]["ad_id"].value_counts().reset_index()
    counts = counts.sort_values(["count", "ad_id"], ascending=[False, True])
    return pd.Series(
        [f"Anúncio {i + 1}" for i in range(len(counts))],
        index=counts["ad_id"].tolist(),
    )


def tab_funnel(df: pd.DataFrame) -> None:
    f = dd.funnel(df)
    now, before = f[f["periodo"] == "atual"], f[f["periodo"] == "anterior"]
    left, right = st.columns([1, 1.15], gap="large")
    with left:
        heading(
            "Quantos chegam a cada etapa",
            "Jun a ago. Rótulo: leads e % do total que entrou.",
        )
        st.plotly_chart(
            ch.funnel_bars(
                now["etapa"].tolist(), now["leads"].tolist(), int(now["leads"].iloc[0])
            ),
            width="stretch",
            config={"displayModeBar": False},
        )
    with right:
        heading(
            "Onde a passagem piorou",
            "Percentual que avança da etapa anterior para esta.",
        )
        steps = now["etapa"].tolist()[1:]
        prev = (
            before.set_index("etapa").reindex(steps)["passagem"].tolist()
            if len(before)
            else None
        )
        st.plotly_chart(
            ch.compare_bars(steps, now["passagem"].tolist()[1:], prev),
            width="stretch",
            config={"displayModeBar": False},
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
            "Taxa de agendamento por tempo da 1ª resposta da equipe. Faixas com poucos leads oscilam muito.",
        )
        st.plotly_chart(
            ch.rate_bars(
                rt.index.tolist(),
                rt["taxa_agendamento"].tolist(),
                rt["leads"].astype(int).tolist(),
                "leads",
            ),
            width="stretch",
            config={"displayModeBar": False},
        )
        eng = mine.engagement(covered)
        heading(
            "P3. Quem conversa, agenda?",
            "Taxa de agendamento por número de mensagens enviadas pelo lead.",
        )
        st.plotly_chart(
            ch.rate_bars(
                [f"{m} msg" for m in eng["msgs_do_lead"]],
                eng["taxa_agendamento"].tolist(),
                eng["leads"].tolist(),
                "leads",
            ),
            width="stretch",
            config={"displayModeBar": False},
        )
    with right:
        from_ads = current[~current["cadastro_manual"]]
        grid = dd.entry_heatmap(from_ads)
        days, bands = mine.WEEKDAYS, [b[2] for b in dd.HOUR_BANDS]
        pivot = grid.pivot(index="dia", columns="faixa", values="leads").reindex(
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
        st.plotly_chart(
            ch.heatmap(days, bands, pivot.values.tolist(), booked.values.tolist()),
            width="stretch",
            config={"displayModeBar": False},
        )
        hours = mine.entry_time(covered).set_index("entrada")
        cols = st.columns(len(hours))
        for col, (name, row) in zip(cols, hours.iterrows()):
            wait = row["mediana_resposta_min"]
            col.metric(
                f"1ª resposta, {name}",
                "-" if wait != wait else f"{wait / 60:.1f} h".replace(".", ","),
                help=f"Mediana. Horário comercial presumido: {dd.business_hours_label()}.",
            )


def tab_show_up(current: pd.DataFrame) -> None:
    ns = mine.no_show(current)
    if ns.empty:
        st.info("Nenhum agendamento neste filtro.")
        return
    ns = ns[ns["espera"] != "sem data"]
    left, right = st.columns([1.4, 1], gap="large")
    with left:
        heading(
            "P4. Esperar mais pela consulta faz faltar mais?",
            "Taxa de falta por dias entre a entrada do lead e a consulta marcada.",
        )
        st.plotly_chart(
            ch.rate_bars(
                ns["espera"].astype(str).tolist(),
                ns["taxa_falta"].tolist(),
                ns["agendados"].tolist(),
                "agendados",
            ),
            width="stretch",
            config={"displayModeBar": False},
        )
    with right:
        booked, missed = int(current["agendou"].sum()), int(current["faltou"].sum())
        st.metric("Agendados", booked)
        st.metric("Faltaram", missed, help="Lead que está na etapa Faltante do CRM.")
        st.metric(
            "Taxa de falta", ch.pct(missed / booked if booked else float("nan"), 0)
        )
        st.caption(
            "A faixa de 3 a 7 dias concentra as faltas. Lembrete na véspera e confirmação no dia "
            "atacam essa janela."
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
    left, right = st.columns([1.2, 1], gap="large")
    with left:
        heading(
            "P5. Quais anúncios trazem paciente que agenda?",
            "Os 10 anúncios com mais leads no recorte. Rótulo: taxa de agendamento.",
        )
        hover = [
            f"{r.anuncio}: {r.leads} leads, {r.agendou} agendaram, {r.vendeu} venda(s)"
            for r in top.itertuples()
        ]
        st.plotly_chart(
            ch.hbar_list(
                top["anuncio"].tolist(),
                top["leads"].tolist(),
                [
                    f"{r.leads} leads · {ch.pct(r.taxa_agendamento)} agenda"
                    for r in top.itertuples()
                ],
                hover,
                40 * len(top) + 40,
            ),
            width="stretch",
            config={"displayModeBar": False},
        )
    with right:
        st.metric("Leads de anúncio", len(from_ads))
        st.metric("Vendas vindas de anúncio", int(from_ads["vendeu"].sum()))
        if "custo_por_lead" not in table.columns:
            st.warning(
                "Custo por lead, CAC e ROAS aguardam a exportação do Meta Ads "
                "(data/raw/meta_ads.csv)."
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
    by_period = mine.summarize(df, "periodo").set_index("periodo")
    left, right = st.columns(2, gap="large")
    with left:
        heading("Receita do trimestre", "Soma do valor fechado das vendas.")
        cols = st.columns(2)
        for col, key, name in zip(
            cols, ("atual", "anterior"), ("Jun a ago", "Mar a mai")
        ):
            value = by_period["receita"].get(key, 0.0)
            sales = int(by_period["vendeu"].get(key, 0))
            col.metric(name, ch.brl(value), help=f"{sales} venda(s)")
        sold = current[current["vendeu"]]
        st.caption(
            f"{len(sold)} venda(s) no recorte; {int(sold['cadastro_manual'].sum())} de cadastro manual."
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
