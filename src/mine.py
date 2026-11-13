"""Mineração sobre os dados tratados: procura o que separa quem avança de quem para.

Lê data/processed/leads_tratados.csv e grava uma tabela por recorte em
data/processed/mineracao_<recorte>.csv. Cada tabela responde uma das perguntas
complementares de entregaveis/03-regra-de-negocio.md.

Uso:
    python src/mine.py
"""

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "processed"

RESPONSE_BINS = [0, 5, 30, 120, 24 * 60, 72 * 60]
RESPONSE_LABELS = ["até 5 min", "5 a 30 min", "30 min a 2 h", "2 a 24 h", "24 a 72 h"]
WAIT_BINS = [-1, 2, 7, 14, 10_000]
WAIT_LABELS = ["0 a 2 dias", "3 a 7 dias", "8 a 14 dias", "15+ dias"]
WEEKDAYS = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
BUSINESS_HOURS = (8, 18)  # horário comercial presumido; LIMITE: a clínica não informou o dela


def rate(group: pd.DataFrame, num: str, den: str | None = None) -> float:
    base = len(group) if den is None else int(group[den].sum())
    return round(group[num].sum() / base, 4) if base else float("nan")


def summarize(df: pd.DataFrame, by: str) -> pd.DataFrame:
    rows = []
    for key, g in df.groupby(by, observed=True, dropna=False):
        rows.append({by: "sem dado" if pd.isna(key) else key, "leads": len(g),
                     "agendou": int(g["agendou"].sum()), "taxa_agendamento": rate(g, "agendou"),
                     "vendeu": int(g["vendeu"].sum()), "taxa_venda": rate(g, "vendeu"),
                     "receita": round(g["receita"].sum(), 2)})
    return pd.DataFrame(rows)


def response_time(df: pd.DataFrame) -> pd.DataFrame:
    band = pd.cut(df["tempo_resposta_min"], RESPONSE_BINS, labels=RESPONSE_LABELS, include_lowest=True)
    band = band.astype("object").where(df["tempo_resposta_min"].notna(),
                                      df["msgs_lead"].gt(0).map({True: "sem resposta em 72 h", False: "sem conversa"}))
    return summarize(df.assign(faixa_resposta=band), "faixa_resposta")


def entry_time(df: pd.DataFrame) -> pd.DataFrame:
    created = df["created_at"]
    inside = created.dt.weekday.lt(5) & created.dt.hour.between(BUSINESS_HOURS[0], BUSINESS_HOURS[1] - 1)
    out = summarize(df.assign(entrada=inside.map({True: "horário comercial", False: "fora do horário"})), "entrada")
    median = df.assign(entrada=inside).groupby("entrada")["tempo_resposta_min"].median()
    out["mediana_resposta_min"] = out["entrada"].map(
        {"horário comercial": median.get(True), "fora do horário": median.get(False)}).round(1)
    return out


def weekday(df: pd.DataFrame) -> pd.DataFrame:
    day = pd.Categorical(df["created_at"].dt.weekday.map(dict(enumerate(WEEKDAYS))), WEEKDAYS, ordered=True)
    return summarize(df.assign(dia_entrada=day), "dia_entrada")


def engagement(df: pd.DataFrame) -> pd.DataFrame:
    # Uma mensagem só costuma ser o texto pronto do anúncio: o lead clicou e não conversou.
    level = pd.cut(df["msgs_lead"], [-1, 0, 1, 3, 10_000], labels=["0", "1", "2 a 3", "4+"])
    return summarize(df.assign(msgs_do_lead=level), "msgs_do_lead")


def no_show(df: pd.DataFrame) -> pd.DataFrame:
    booked = df[df["agendou"]].copy()
    booked["espera"] = pd.cut(booked["dias_ate_consulta"], WAIT_BINS, labels=WAIT_LABELS)
    rows = []
    for key, g in booked.groupby("espera", observed=True, dropna=False):
        rows.append({"espera": "sem data" if pd.isna(key) else key, "agendados": len(g),
                     "faltou": int(g["faltou"].sum()), "taxa_falta": rate(g, "faltou"),
                     "avaliado": int(g["avaliado"].sum())})
    return pd.DataFrame(rows)


def ads(df: pd.DataFrame) -> pd.DataFrame:
    out = summarize(df, "ad_id").sort_values("leads", ascending=False)
    spend_path = OUT / "gasto_por_anuncio.csv"
    if spend_path.exists():
        spend = pd.read_csv(spend_path, dtype={"ad_id": str})
        out = out.merge(spend, on="ad_id", how="left")
        out["custo_por_lead"] = (out["gasto"] / out["leads"]).round(2)
        out["custo_por_venda"] = (out["gasto"] / out["vendeu"].where(out["vendeu"] > 0)).round(2)
    return out


def lost_revenue(df: pd.DataFrame) -> pd.DataFrame:
    """Quanto valeria recuperar cada vazamento, mantendo as taxas seguintes como estão."""
    sales = df[df["vendeu"]]
    ticket = sales["receita"].mean() if len(sales) else 0
    contacted, booked = int(df["em_contato"].sum()), int(df["agendou"].sum())
    evaluated, sold = int(df["avaliado"].sum()), len(sales)
    eval_to_sale = sold / evaluated if evaluated else 0
    show_rate = evaluated / booked if booked else 0
    no_shows = int(df["faltou"].sum())
    rows = [
        {"cenario": "ticket médio observado", "valor": round(ticket, 2)},
        {"cenario": "receita observada", "valor": round(df["receita"].sum(), 2)},
        {"cenario": "faltantes que comparecem (todos)",
         "vendas_extra": round(no_shows * eval_to_sale, 1),
         "valor": round(no_shows * eval_to_sale * ticket, 2)},
        {"cenario": "agendamento sobe de "
                    f"{booked / contacted:.0%} para 15% dos atendidos" if contacted else "agendamento",
         "vendas_extra": round((0.15 * contacted - booked) * show_rate * eval_to_sale, 1),
         "valor": round((0.15 * contacted - booked) * show_rate * eval_to_sale * ticket, 2)},
    ]
    return pd.DataFrame(rows)


def main() -> int:
    path = OUT / "leads_tratados.csv"
    if not path.exists():
        print("Rode src/clean.py antes.", file=sys.stderr)
        return 2
    df = pd.read_csv(path, dtype={"ad_id": str})
    df["created_at"] = pd.to_datetime(df["created_at"], utc=True, format="ISO8601").dt.tz_convert("America/Sao_Paulo")
    for col in ["em_contato", "agendou", "faltou", "avaliado", "vendeu"]:
        df[col] = df[col].astype(bool)
    for col in ["mensagens_cobertas", "cadastro_manual"]:
        df[col] = df[col].fillna(False).astype(bool)
    current = df[df["periodo"] == "atual"]
    # Atendimento só onde existe histórico de mensagens; horário só onde a hora é real.
    covered = current[current["mensagens_cobertas"] & ~current["cadastro_manual"]]
    from_ads = current[~current["cadastro_manual"]]
    print(f"leads do recorte: {len(current)} | com mensagens: {len(covered)} | vindos do anúncio: {len(from_ads)}")

    tables = {
        "tempo_resposta": response_time(covered),
        "horario_entrada": entry_time(covered),
        "dia_semana": weekday(from_ads),
        "engajamento": engagement(covered),
        "falta_por_espera": no_show(current),
        "anuncios": ads(from_ads),
        "receita_perdida": lost_revenue(current),
        "trimestres": summarize(df, "periodo"),
    }
    for name, table in tables.items():
        table.to_csv(OUT / f"mineracao_{name}.csv", index=False)
        print(f"\n## {name}\n{table.to_string(index=False)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
