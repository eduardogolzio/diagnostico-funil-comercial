"""Gráficos Plotly do dashboard, num estilo só: um tom para o recorte atual, cinza para a comparação."""

import plotly.graph_objects as go

CURRENT = "#2a78d6"  # recorte atual: o dado principal leva o único tom da tela
PREVIOUS = "#b4b2ab"  # trimestre anterior: contexto, em neutro
INK, MUTED, GRID, SURFACE = "#0b0b0b", "#6b6a66", "#e7e6e2", "#ffffff"
SEQUENTIAL = ["#eef4fc", "#b7d3f6", "#6da7ec", "#2a78d6", "#1c5cab", "#0d366b"]
FONT = "Inter, -apple-system, Segoe UI, sans-serif"


def pct(value: float, digits: int = 1) -> str:
    if value != value:  # NaN: base vazia no filtro
        return "-"
    return f"{value * 100:.{digits}f}%".replace(".", ",")


def brl(value: float) -> str:
    if value != value:
        return "-"
    return "R$ " + f"{value:,.0f}".replace(",", ".")


def _style(
    fig: go.Figure, height: int, x_pct: bool = False, y_pct: bool = False
) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=16, t=8, b=8),
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        font=dict(family=FONT, size=12, color=MUTED),
        barcornerradius=4,
        bargap=0.35,
        bargroupgap=0.12,
        legend=dict(orientation="h", y=1.08, x=0, font=dict(color=INK), title=None),
        hoverlabel=dict(
            bgcolor=SURFACE, bordercolor=GRID, font=dict(family=FONT, color=INK)
        ),
    )
    fig.update_xaxes(
        showline=False,
        gridcolor=GRID,
        zeroline=False,
        tickformat=".0%" if x_pct else None,
    )
    fig.update_yaxes(
        showline=False,
        gridcolor=GRID,
        zeroline=False,
        tickformat=".0%" if y_pct else None,
    )
    return fig


def funnel_bars(stages: list[str], counts: list[int], top: int) -> go.Figure:
    """Etapas do recorte atual como barras horizontais, do topo para baixo, rotuladas com o % do topo."""
    labels = [f"{n}  ·  {pct(n / top) if top else '-'}" for n in counts]
    fig = go.Figure(
        go.Bar(
            x=counts,
            y=stages,
            orientation="h",
            marker=dict(color=CURRENT, line=dict(color=SURFACE, width=2)),
            text=labels,
            textposition="outside",
            textfont=dict(color=INK),
            cliponaxis=False,
            hovertemplate="%{y}: %{x} leads<extra></extra>",
        )
    )
    fig.update_yaxes(
        autorange="reversed",
        gridcolor="rgba(0,0,0,0)",
        tickfont=dict(color=INK, size=13),
    )
    fig.update_xaxes(
        showgrid=False, showticklabels=False, range=[0, max(counts + [1]) * 1.5]
    )
    return _style(fig, 300)


def compare_bars(
    categories: list[str],
    current: list[float],
    previous: list[float] | None,
    height: int = 300,
    names: tuple[str, str] = ("Jun a ago", "Mar a mai"),
) -> go.Figure:
    """Taxa por categoria, atual contra anterior lado a lado, no mesmo eixo."""
    fig = go.Figure()
    if previous is not None:
        fig.add_bar(
            name=names[1],
            x=categories,
            y=previous,
            marker=dict(color=PREVIOUS, line=dict(color=SURFACE, width=2)),
            hovertemplate="%{x}<br>" + names[1] + ": %{y:.1%}<extra></extra>",
        )
    fig.add_bar(
        name=names[0],
        x=categories,
        y=current,
        marker=dict(color=CURRENT, line=dict(color=SURFACE, width=2)),
        text=[pct(v) for v in current],
        textposition="outside",
        textfont=dict(color=INK),
        cliponaxis=False,
        hovertemplate="%{x}<br>" + names[0] + ": %{y:.1%}<extra></extra>",
    )
    top = max([v for v in current + (previous or []) if v == v] + [0.01])
    fig.update_yaxes(range=[0, top * 1.2], nticks=5)
    fig.update_xaxes(showgrid=False, tickfont=dict(color=INK))
    fig.update_layout(showlegend=previous is not None, barmode="group")
    return _style(fig, height, y_pct=True)


def rate_bars(
    categories: list[str],
    rates: list[float],
    bases: list[int],
    base_label: str,
    height: int = 260,
) -> go.Figure:
    """Uma taxa por categoria em barra horizontal, com a base (n) no rótulo: amostra pequena fica visível."""
    ticks = [
        f"{c}  <span style='color:{MUTED}'>n={b}</span>"
        for c, b in zip(categories, bases)
    ]
    fig = go.Figure(
        go.Bar(
            x=rates,
            y=ticks,
            orientation="h",
            marker=dict(color=CURRENT, line=dict(color=SURFACE, width=2)),
            text=[pct(r) for r in rates],
            textposition="outside",
            textfont=dict(color=INK),
            cliponaxis=False,
            customdata=bases,
            hovertemplate="%{x:.1%} de %{customdata} " + base_label + "<extra></extra>",
        )
    )
    top = max([r for r in rates if r == r] + [0.01])
    fig.update_xaxes(range=[0, top * 1.25], nticks=5)
    fig.update_yaxes(autorange="reversed", showgrid=False, tickfont=dict(color=INK))
    return _style(fig, max(height, 34 * len(categories) + 50), x_pct=True)


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
    fig.update_yaxes(autorange="reversed", showgrid=False, tickfont=dict(color=INK))
    fig.update_xaxes(showgrid=False, side="top", tickfont=dict(color=INK))
    return _style(fig, 300)


def hbar_list(
    labels: list[str],
    values: list[float],
    text: list[str],
    hover: list[str],
    height: int,
) -> go.Figure:
    """Lista ordenada como barra horizontal (quem ranqueia), maior no topo."""
    fig = go.Figure(
        go.Bar(
            x=values,
            y=labels,
            orientation="h",
            marker=dict(color=CURRENT, line=dict(color=SURFACE, width=2)),
            text=text,
            textposition="outside",
            textfont=dict(color=INK),
            cliponaxis=False,
            hovertext=hover,
            hovertemplate="%{hovertext}<extra></extra>",
        )
    )
    fig.update_yaxes(autorange="reversed", showgrid=False, tickfont=dict(color=INK))
    fig.update_xaxes(
        showgrid=False, showticklabels=False, range=[0, max(values + [1]) * 1.6]
    )
    return _style(fig, height)


MISSED = "#d95926"  # faltou: segundo tom, só neste gráfico, sempre com legenda e rótulo


def outcome_bars(
    bands: list[str], attended: list[int], missed: list[int], pending: list[int]
) -> go.Figure:
    """Cada barra é o total de agendados da faixa, dividido em quem compareceu e quem faltou."""
    segments = [("Compareceu", attended, CURRENT), ("Faltou", missed, MISSED)]
    if any(pending):
        segments.append(("Ainda sem desfecho", pending, PREVIOUS))
    fig = go.Figure()
    for name, values, color in segments:
        fig.add_bar(
            name=name,
            y=bands,
            x=values,
            orientation="h",
            marker=dict(color=color, line=dict(color=SURFACE, width=2)),
            text=[v if v else "" for v in values],
            textposition="inside",
            insidetextanchor="middle",
            textfont=dict(color=SURFACE, size=13),
            hovertemplate="%{y}: %{x} " + name.lower() + "<extra></extra>",
        )
    totals = [a + m + p for a, m, p in zip(attended, missed, pending)]
    for band, total, miss in zip(bands, totals, missed):
        fig.add_annotation(
            y=band,
            x=total,
            xanchor="left",
            xshift=8,
            showarrow=False,
            font=dict(color=INK, size=13),
            text=f"<b>{pct(miss / total, 0) if total else '-'}</b> faltou  "
            f"<span style='color:{MUTED}'>({miss} de {total})</span>",
        )
    fig.update_layout(barmode="stack", showlegend=True, legend_traceorder="normal")
    fig.update_yaxes(autorange="reversed", showgrid=False, tickfont=dict(color=INK, size=13))
    fig.update_xaxes(
        range=[0, max(totals + [1]) * 1.55],
        nticks=5,
        title=dict(text="consultas marcadas", font=dict(size=12)),
    )
    return _style(fig, 60 * len(bands) + 110)
