"""Limpeza e preparação dos dados extraídos (data/raw -> data/processed).

Cada passo grava uma linha em data/processed/limpeza_log.csv com quantas linhas
entraram, quantas saíram e o que foi feito. Esse log é a evidência do método
descrito em entregaveis/02-limpeza-e-mineracao.md.

Uso:
    python src/clean.py
"""

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"
TZ = "America/Sao_Paulo"

# Ordem das etapas no pipeline (data/raw/etapas.csv). Perdido fica fora da escada.
ORDER_CONTACT, ORDER_SCHEDULED, ORDER_NO_SHOW, ORDER_EVALUATED, ORDER_SALE, ORDER_LOST = 2, 3, 4, 5, 6, 7
# Resposta da equipe depois desse prazo não conta como "primeira resposta" do atendimento.
MAX_RESPONSE_HOURS = 72

log: list[dict] = []


def step(name: str, before: int, after: int, detail: str) -> None:
    log.append({"passo": len(log) + 1, "etapa": name, "linhas_antes": before,
                "linhas_depois": after, "descricao": detail})
    print(f"[{len(log):02d}] {name}: {before} -> {after}  {detail}")


def to_local(series: pd.Series) -> pd.Series:
    """Texto ISO em UTC para horário de São Paulo. Valor inválido vira NaT, não erro."""
    return pd.to_datetime(series, errors="coerce", utc=True, format="ISO8601").dt.tz_convert(TZ)


def load_leads() -> pd.DataFrame:
    df = pd.read_csv(RAW / "leads.csv", dtype={"ad_id": "string", "ddd": "string"})
    step("carga", len(df), len(df), "leads.csv lido, dois trimestres (atual e anterior)")
    return df


def fix_types(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in ["created_at", "last_contact_at", "last_lead_contact_at", "closed_at", "quoted_at"]:
        df[col] = to_local(df[col])
    # Data da Consulta chega como meia-noite de São Paulo em UTC (03:00Z): converter antes de tirar o dia.
    df["data_consulta"] = to_local(df["data_consulta"]).dt.date
    for col in ["quoted_value", "closed_value"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["stage_order"] = pd.to_numeric(df["stage_order"], errors="coerce").astype("Int64")
    invalid_dates = int(df["created_at"].isna().sum())
    step("tipos", len(df), len(df),
         f"datas convertidas de UTC para {TZ}, valores para número; {invalid_dates} data(s) de entrada inválida(s)")
    return df


def drop_invalid(df: pd.DataFrame) -> pd.DataFrame:
    before = len(df)
    df = df[df["status"] != "DELETED"]
    df = df[df["created_at"].notna() & df["stage_order"].notna()]
    step("registros inválidos", before, len(df), "removidos leads excluídos no CRM, sem data de entrada ou sem etapa")
    return df


def drop_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    before = len(df)
    df = df.drop_duplicates(subset="lead_key")
    exact = before - len(df)
    # Reentrada: a pessoa clica de novo no anúncio e o CRM abre outro lead, que fica parado em
    # Novo Lead enquanto o original segue. Só esse lead parado sai. Dois leads que avançaram são
    # dois atendimentos reais (caso visto: a mesma pessoa com duas vendas no mesmo dia).
    same_person = df.duplicated(subset=["contact_key", "periodo"], keep=False)
    stalled = df["stage_order"] == 1
    has_other_progress = (df.assign(_moved=~stalled)
                            .groupby(["contact_key", "periodo"])["_moved"].transform("any"))
    reentry = same_person & stalled & has_other_progress
    # Dois leads parados da mesma pessoa: fica o primeiro.
    both_stalled = same_person & stalled & ~has_other_progress
    reentry |= both_stalled & df.sort_values("created_at").duplicated(subset=["contact_key", "periodo"])
    df = df[~reentry]
    step("duplicatas", before, len(df),
         f"{exact} repetido(s) por paginação; {int(reentry.sum())} reentrada(s) parada(s) em Novo Lead")
    return df


def derive_funnel(df: pd.DataFrame) -> pd.DataFrame:
    """Etapa atual -> etapas alcançadas. O CRM só guarda a etapa atual, não o histórico."""
    df = df.copy()
    order = df["stage_order"]
    reached = order.where(order != ORDER_LOST, 0)
    df["em_contato"] = reached >= ORDER_CONTACT
    df["agendou"] = reached >= ORDER_SCHEDULED
    # Faltante fica entre Agendado e Avaliado: quem está em Avaliado passou pela posição dela
    # na escada, mas não faltou. Falta real é só quem está parado em Faltante.
    df["faltou"] = order == ORDER_NO_SHOW
    df["avaliado"] = reached >= ORDER_EVALUATED
    df["vendeu"] = (reached >= ORDER_SALE) | (df["status"] == "CONVERTED") | (df["deal_status"] == "WON")
    df["perdido"] = order == ORDER_LOST
    df["receita"] = df["closed_value"].where(df["vendeu"], 0).fillna(0)
    # Lead lançado à mão pela equipe: o CRM grava só o dia, então a hora sai meia-noite exata.
    # A hora de entrada dele não é a hora em que o paciente chegou.
    if "created_at" in df:
        c = df["created_at"]
        df["cadastro_manual"] = (c.dt.hour == 0) & (c.dt.minute == 0) & (c.dt.second == 0) & (c.dt.microsecond == 0)
    step("funil derivado", len(df), len(df),
         "flags em_contato/agendou/faltou/avaliado/vendeu a partir da etapa atual; Faltante tratado como desvio")
    return df


def flag_inconsistencies(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    issues = pd.DataFrame(index=df.index)
    issues["venda_sem_valor"] = df["vendeu"] & df["closed_value"].isna()
    issues["status_etapa_divergem"] = (df["status"] == "CONVERTED") != (df["stage_order"] == ORDER_SALE)
    created_day = df["created_at"].dt.date
    issues["consulta_antes_entrada"] = df["data_consulta"].notna() & (df["data_consulta"] < created_day)
    issues["agendado_sem_data"] = df["agendou"] & ~df["perdido"] & df["data_consulta"].isna()
    df["inconsistencias"] = issues.apply(lambda r: ";".join(c for c in issues.columns if r[c]), axis=1)
    counts = ", ".join(f"{c}={int(issues[c].sum())}" for c in issues.columns)
    step("inconsistências", len(df), len(df), f"marcadas, não removidas: {counts}")
    # Data de consulta anterior à entrada do lead é erro de digitação: não serve para medir espera.
    df.loc[issues["consulta_antes_entrada"], "data_consulta"] = pd.NaT
    df["dias_ate_consulta"] = (pd.to_datetime(df["data_consulta"]) - pd.to_datetime(created_day)).dt.days
    return df


def first_response(messages: pd.DataFrame) -> pd.DataFrame:
    """Por lead: primeira mensagem do lead, primeira resposta da equipe depois dela, e volumes."""
    msgs = messages.dropna(subset=["sent_at"]).sort_values("sent_at")
    inbound = msgs[msgs["direction"] == "INBOUND"].groupby("lead_key")["sent_at"].min().rename("primeira_msg_lead")
    joined = msgs[msgs["direction"] == "OUTBOUND"].join(inbound, on="lead_key")
    answer = (joined[joined["sent_at"] > joined["primeira_msg_lead"]]
              .groupby("lead_key")["sent_at"].min().rename("primeira_resposta"))
    counts = msgs.pivot_table(index="lead_key", columns="direction", values="sent_at",
                              aggfunc="count", fill_value=0)
    counts = counts.reindex(columns=["INBOUND", "OUTBOUND"], fill_value=0)
    counts.columns = ["msgs_lead", "msgs_equipe"]
    out = pd.concat([inbound, answer, counts], axis=1)
    minutes = (out["primeira_resposta"] - out["primeira_msg_lead"]).dt.total_seconds() / 60
    out["tempo_resposta_min"] = minutes.where(minutes <= MAX_RESPONSE_HOURS * 60)
    return out


def attach_messages(df: pd.DataFrame) -> pd.DataFrame:
    path = RAW / "mensagens.csv"
    msgs = pd.read_csv(path)
    msgs["sent_at"] = to_local(msgs["sent_at"])
    before = len(msgs)
    msgs = msgs.dropna(subset=["sent_at", "direction"]).drop_duplicates()
    step("mensagens", before, len(msgs), "removidas mensagens sem horário ou direção e repetidas")
    per_lead = first_response(msgs)
    df = df.merge(per_lead, left_on="lead_key", right_index=True, how="left")
    df[["msgs_lead", "msgs_equipe"]] = df[["msgs_lead", "msgs_equipe"]].fillna(0).astype(int)
    df["sem_conversa"] = (df["msgs_lead"] + df["msgs_equipe"]) == 0
    # O CRM só guarda mensagens a partir da primeira que existe na base. Lead que entrou antes
    # disso não tem "zero mensagens": tem mensagens que a fonte não registrou.
    coverage_start = msgs["sent_at"].min().normalize()
    df["mensagens_cobertas"] = df["created_at"] >= coverage_start
    step("cobertura de mensagens", len(df), int(df["mensagens_cobertas"].sum()),
         f"histórico do WhatsApp começa em {coverage_start:%d/%m/%Y}; só leads a partir daí entram nas análises de atendimento")
    no_answer = int((df["msgs_lead"] > 0).sum() - df["primeira_resposta"].notna().sum())
    step("tempo de resposta", len(df), len(df),
         f"calculado por lead; respostas acima de {MAX_RESPONSE_HOURS}h viram vazio; {no_answer} lead(s) sem resposta da equipe")
    return df


def attach_follow_ups(df: pd.DataFrame) -> pd.DataFrame:
    fu = pd.read_csv(RAW / "follow_ups.csv")
    df = df.merge(fu[["lead_key", "done_count"]], on="lead_key", how="left")
    df["follow_ups"] = df["done_count"].fillna(0).astype(int)
    step("follow-ups", len(df), len(df.drop(columns="done_count")),
         f"{int((df['follow_ups'] > 0).sum())} lead(s) com follow-up registrado; ausência = zero")
    return df.drop(columns="done_count")


def parse_brl(values: pd.Series) -> pd.Series:
    """Valor da exportação do Meta: '1.234,56' (pt-BR) ou '1234.56' (en). Com vírgula, o ponto é milhar."""
    text = values.astype("string").str.strip().str.replace("R$", "", regex=False).str.strip()
    has_comma = text.str.contains(",", regex=False, na=False)
    text = text.where(~has_comma, text.str.replace(".", "", regex=False).str.replace(",", ".", regex=False))
    return pd.to_numeric(text, errors="coerce")


def spend_by_ad(ads: pd.DataFrame) -> pd.DataFrame:
    ads = ads.rename(columns={c: c.strip().lower() for c in ads.columns})
    id_col = next((c for c in ads.columns if c in ("ad_id", "id do anúncio", "ad id")), None)
    spend_col = next((c for c in ads.columns
                      if c.startswith(("amount_spent", "valor usado", "amount spent"))), None)
    if id_col is None or spend_col is None:
        raise SystemExit(f"meta_ads.csv sem coluna de id ou de gasto; cabeçalhos: {list(ads.columns)}")
    ads = ads.rename(columns={id_col: "ad_id", spend_col: "gasto"})
    ads["gasto"] = parse_brl(ads["gasto"])
    unreadable = int(ads["gasto"].isna().sum())
    if unreadable:
        print(f"aviso: {unreadable} linha(s) de gasto ilegível(is) em meta_ads.csv", file=sys.stderr)
    return ads.groupby("ad_id", as_index=False)["gasto"].sum()


def attach_ads(df: pd.DataFrame) -> pd.DataFrame:
    """Gasto do Meta Ads por anúncio, se o CSV exportado do Gerenciador estiver em data/raw."""
    path = RAW / "meta_ads.csv"
    if not path.exists():
        step("meta ads", len(df), len(df), "data/raw/meta_ads.csv ausente: custo por lead fica de fora")
        return df
    ads = spend_by_ad(pd.read_csv(path, dtype=str))
    current = df[df["periodo"] == "atual"]
    matched = current["ad_id"].isin(ads["ad_id"]).mean()
    step("meta ads", len(ads), len(ads), f"gasto somado por anúncio; {matched:.0%} dos leads do recorte casam com um anúncio")
    ads.to_csv(OUT / "gasto_por_anuncio.csv", index=False)
    return df


def anonymize_check(df: pd.DataFrame) -> None:
    """Falha alto se alguma coluna com cara de dado pessoal chegar ao arquivo tratado."""
    forbidden = {"contactname", "contactphone", "contactemail", "nome", "telefone", "email", "avatarurl"}
    leaked = forbidden & {c.lower() for c in df.columns}
    if leaked:
        raise SystemExit(f"coluna pessoal no resultado: {sorted(leaked)}")


def funnel_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for period, g in df.groupby("periodo"):
        stages = [("Novo Lead", len(g)), ("Em Contato", int(g["em_contato"].sum())),
                  ("Agendado", int(g["agendou"].sum())), ("Avaliado", int(g["avaliado"].sum())),
                  ("Venda Realizada", int(g["vendeu"].sum()))]
        for i, (name, n) in enumerate(stages):
            prev = stages[i - 1][1] if i else None
            rows.append({"periodo": period, "etapa": name, "leads": n,
                         "passagem": round(n / prev, 4) if prev else None,
                         "conversao_total": round(n / len(g), 4)})
        rows.append({"periodo": period, "etapa": "Faltante (desvio)", "leads": int(g["faltou"].sum()),
                     "passagem": round(g["faltou"].sum() / max(g["agendou"].sum(), 1), 4),
                     "conversao_total": None})
    return pd.DataFrame(rows)


def main() -> int:
    if not (RAW / "leads.csv").exists():
        print("data/raw/leads.csv não encontrado.", file=sys.stderr)
        return 2
    OUT.mkdir(parents=True, exist_ok=True)
    df = load_leads()
    df = fix_types(df)
    df = drop_invalid(df)
    df = drop_duplicates(df)
    df = derive_funnel(df)
    df = flag_inconsistencies(df)
    current = df[df["periodo"] == "atual"]
    current = attach_messages(current)
    current = attach_follow_ups(current)
    attach_ads(current)
    df = pd.concat([current, df[df["periodo"] != "atual"]], ignore_index=True)
    anonymize_check(df)

    df.to_csv(OUT / "leads_tratados.csv", index=False)
    funnel_summary(df).to_csv(OUT / "funil_resumo.csv", index=False)
    pd.DataFrame(log).to_csv(OUT / "limpeza_log.csv", index=False)
    print(f"\n{len(df)} leads tratados -> data/processed/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
