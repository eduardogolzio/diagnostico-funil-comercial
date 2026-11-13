# Diagnóstico de funil comercial | Nexus Assessoria

**Cliente:** Clínica odontológica em Campina Grande - PB
**Assessoria:** Nexus Assessoria (Eduardo e Henrique)
**Status:** fase 2 entregue (fontes, limpeza e regra de negócio)

Projeto da Nexus Assessoria, assessoria comercial, desenvolvido na disciplina de Análise de Dados e BI. Os nomes da clínica, da
agência de publicidade que gere os anúncios e dos sistemas usados foram omitidos por confidencialidade.

## O problema

A clínica atrai pacientes com anúncios no Meta Ads. O paciente clica, manda mensagem no WhatsApp e é atendido
pela equipe, que registra o andamento num CRM. Entre junho e agosto de 2026 a clínica recebeu mais contatos
que no trimestre anterior e vendeu menos: a conversão de contato em venda caiu de 3,0% para 1,7%.

**Pergunta de negócio:** em quais etapas do funil a clínica perde os pacientes, por quê, e quanto de receita
isso representa?

## Escopo

| Entra | Fica fora |
|---|---|
| Funil do contato à venda, de 01/06 a 31/08/2026, comparado ao trimestre anterior | Criação ou ajuste de campanhas |
| Atendimento no WhatsApp: tempo de resposta, engajamento, horário | Conteúdo das conversas (não é lido) |
| Comparecimento à consulta de avaliação | Dados clínicos e de tratamento |
| Receita das vendas e investimento em anúncios | Margem e custo do tratamento |

## Entregas

| Fase | Entrega | Status |
|---|---|---|
| 1 | Diagnóstico inicial e pergunta de negócio | entregue |
| 2 | [Fontes de dados](entregaveis/01-fontes-de-dados.md) | entregue |
| 2 | [Limpeza e mineração dos dados](entregaveis/02-limpeza-e-mineracao.md) | entregue |
| 2 | [Regra de negócio, objetivo, métricas e perguntas complementares](entregaveis/03-regra-de-negocio.md) | entregue |
| 3 | Dashboard de acompanhamento (Streamlit) | próxima fase |

## Principais achados até aqui

- A clínica vende igual quando o paciente chega à avaliação (fechamento estável: 45,2% antes, 43,5% agora).
  A perda está antes: o agendamento caiu de 12,4% para 9,2% dos atendidos, e a falta à consulta subiu
  de 38% para 54% dos agendados.
- Dos 579 contatos vindos do anúncio, 1 virou venda. As outras 9 vendas do trimestre vieram de pacientes
  cadastrados à mão pela equipe.
- A primeira resposta da equipe leva em mediana 5,4 horas, e 13 horas para quem escreve fora do horário
  comercial.
- Os 27 pacientes que faltaram à avaliação representam até R$ 63 mil em vendas, mantidas as taxas atuais.

Detalhe e ressalvas de cada número em [entregaveis/03-regra-de-negocio.md](entregaveis/03-regra-de-negocio.md).

## Metodologia

Análise descritiva e diagnóstica pelo método DEILAS. O fluxo dos dados:

```
CRM e Meta Ads ──extração anonimizada──> data/raw/ ──src/clean.py──> data/processed/ ──src/mine.py──> tabelas de mineração
```

## Estrutura do repositório

```
entregaveis/     documentos entregues ao cliente
src/clean.py     limpeza, com log por passo em data/processed/limpeza_log.csv
src/mine.py      mineração por segmento, uma tabela por pergunta
tests/           testes das regras de limpeza
data/raw/        dados extraídos, já sem dado pessoal
data/processed/  base tratada, resumo do funil e tabelas de mineração
```

## Como reproduzir

```bash
pip install -r requirements.txt
python -m pytest -q tests
python src/clean.py
python src/mine.py
```

## Confidencialidade

Os dados são de pacientes reais. Nome, telefone, e-mail, foto e texto das mensagens foram descartados na
extração, e os identificadores viraram hash com sal secreto, que não está no repositório. Detalhe em
[entregaveis/01-fontes-de-dados.md](entregaveis/01-fontes-de-dados.md#privacidade-lgpd).
