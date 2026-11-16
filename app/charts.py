"""Gráficos Plotly do dashboard.

Toda pergunta de taxa usa o mesmo desenho: uma barra por grupo com o tamanho da base,
dividida entre quem avançou e quem não avançou, e ao lado o percentual com "x de y".
Assim o leitor vê ao mesmo tempo quantas pessoas são e qual fração delas.
"""

from typing import NamedTuple

import plotly.graph_objects as go

ADVANCED = "#2a78d6"  # quem avançou: o tom principal da tela
STOPPED = "#cfcdc6"  # quem não avançou: neutro, para não gritar mais que o resultado
MISSED = "#d95926"  # faltou à consulta: evento ruim, só na P4, sempre com legenda
MANUAL = "#6250d6"  # cadastro manual, na aba Receita
INK, MUTED, GRID, SURFACE = "#0b0b0b", "#6b6a66", "#e7e6e2", "#ffffff"
SEQUENTIAL = ["#eef4fc", "#b7d3f6", "#6da7ec", "#2a78d6", "#1c5cab", "#0d366b"]
FONT = "Inter, -apple-system, Segoe UI, sans-serif"
CHART_CONFIG = {"displayModeBar": False}


class Segment(NamedTuple):
    name: str
    values: list[float]
    color: str
    text_color: str = SURFACE


def pct(value: float, digits: int = 1) -> str:
    if value != value:  # NaN: base vazia no filtro
        return "-"
    return f"{value * 100:.{digits}f}%".replace(".", ",")


def brl(value: float) -> str:
    if value != value:
        return "-"
    return "R$ " + f"{value:,.0f}".replace(",", ".")


def share_note(part: int, total: int, verb: str, extra: str = "") -> str:
    """Rótulo ao lado da barra: '16,7% agendou (4 de 24)'."""
    if not total:
        return f"<span style='color:{MUTED}'>sem base</span>"
    tail = f"({part} de {total}" + (f" · {extra}" if extra else "") + ")"
    # Contagem na segunda linha: a nota fica estreita e não estoura a borda do gráfico.
    return f"<b>{pct(part / total)}</b> {verb}<br><span style='color:{MUTED}'>{tail}</span>"


def _style(fig: go.Figure, height: int) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=16, t=8, b=8),
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        separators=",.",
        font=dict(family=FONT, size=12, color=MUTED),
        barcornerradius=4,
        bargap=0.38,
        uniformtext=dict(mode="hide", minsize=10),
        legend=dict(
            orientation="h",
            y=1.02,
            yanchor="bottom",
            x=0,
            font=dict(color=INK),
            title=None,
            traceorder="normal",
        ),
        hoverlabel=dict(
            bgcolor=SURFACE, bordercolor=GRID, font=dict(family=FONT, color=INK)
        ),
    )
    fig.update_xaxes(showline=False, gridcolor=GRID, zeroline=False)
    fig.update_yaxes(showline=False, showgrid=False, zeroline=False)
    return fig


def split_bars(
    categories: list[str],
    segments: list[Segment],
    notes: list[str],
    x_title: str,
    money: bool = False,
) -> go.Figure:
    """Barra horizontal empilhada por categoria; o comprimento total é a base do grupo.

    Contagem leva o número dentro de cada parte; dinheiro não (o valor vai na nota ao lado).
    """
    number = ",.0f" if money else "d"
    totals = [sum(seg.values[i] for seg in segments) for i in range(len(categories))]
    min_label = max(totals + [1]) * 0.06  # parte estreita demais não leva número dentro
    fig = go.Figure()
    for seg in segments:
        fig.add_bar(
            name=seg.name,
            y=categories,
            x=seg.values,
            orientation="h",
            marker=dict(color=seg.color, line=dict(color=SURFACE, width=2)),
            text=None
            if money
            else [int(v) if v >= min_label else "" for v in seg.values],
            textposition="inside",
            insidetextanchor="middle",
            textfont=dict(color=seg.text_color, size=12),
            hovertemplate="%{y}<br>"
            + seg.name
            + ": %{x:"
            + number
            + "}<extra></extra>",
        )
    for category, total, note in zip(categories, totals, notes):
        fig.add_annotation(
            y=category,
            x=total,
            xanchor="left",
            align="left",
            xshift=8,
            showarrow=False,
            font=dict(color=INK, size=12),
            text=note,
        )
    fig.update_layout(barmode="stack")
    fig.update_yaxes(autorange="reversed", tickfont=dict(color=INK, size=13))
    fig.update_xaxes(
        range=[0, max(totals + [1]) * 1.9],
        nticks=5,
        tickformat=",.0f",
        title=dict(text=x_title, font=dict(size=12)),
    )
    return _style(fig, 54 * len(categories) + 120)


def funnel_bars(stages: list[str], counts: list[int], top: int) -> go.Figure:
    """Etapas do recorte atual como barras horizontais, do topo para baixo, rotuladas com o % do topo."""
    labels = [f"{n}  ·  {pct(n / top) if top else '-'}" for n in counts]
    fig = go.Figure(
        go.Bar(
            x=counts,
            y=stages,
            orientation="h",
            marker=dict(color=ADVANCED, line=dict(color=SURFACE, width=2)),
            text=labels,
            textposition="outside",
            textfont=dict(color=INK),
            cliponaxis=False,
            hovertemplate="%{y}: %{x} leads<extra></extra>",
        )
    )
    fig.update_yaxes(autorange="reversed", tickfont=dict(color=INK, size=13))
    fig.update_xaxes(
        showgrid=False, showticklabels=False, range=[0, max(counts + [1]) * 1.5]
    )
    return _style(fig, 300)


def heatmap(
    days: list[str], bands: list[str], leads: list[list[int]], booked: list[list[int]]
) -> go.Figure:
    fig = go.Figure(
        go.Heatmap(
            z=leads,
            x=bands,
            y=days,
            customdata=booked,
            colorscale=[[i / 5, c] for i, c in enumerate(SEQUENTIAL)],
            xgap=2,
            ygap=2,
            text=leads,
            texttemplate="%{text}",
            textfont=dict(size=12),
            colorbar=dict(
                title=dict(text="leads", side="top"), thickness=10, outlinewidth=0
            ),
            hovertemplate="%{y}, %{x}<br>%{z} leads, %{customdata} agendaram<extra></extra>",
        )
    )
    fig.update_yaxes(autorange="reversed", tickfont=dict(color=INK))
    fig.update_xaxes(showgrid=False, side="top", tickfont=dict(color=INK))
    return _style(fig, 300)
