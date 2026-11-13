# Entregável 1. Fontes de dados

Diagnóstico de funil comercial, fase 2. Cliente: Clínica odontológica em Campina Grande - PB. A clínica
anuncia no Meta Ads por meio de uma agência de publicidade e atende os pacientes num CRM. Os nomes da
clínica, da agência e dos sistemas foram omitidos por confidencialidade.
Recorte: 01/06/2026 a 31/08/2026, com o trimestre anterior (01/03 a 31/05/2026) como base de comparação.

## Visão geral

| # | Fonte | Sistema | O que fornece | Como foi obtida | Arquivo |
|---|---|---|---|---|---|
| F1 | Leads do funil | CRM da clínica | um registro por lead: entrada, etapa atual, anúncio de origem, data da consulta, valor da venda | extração automatizada, anonimizada na coleta | `data/raw/leads.csv` |
| F2 | Etapas do funil | CRM da clínica | as 7 etapas do funil, em ordem | extração automatizada | `data/raw/etapas.csv` |
| F3 | Mensagens do WhatsApp | CRM da clínica | direção (lead ou equipe), tipo e horário de cada mensagem nos 30 dias após a entrada | extração automatizada, sem o texto | `data/raw/mensagens.csv` |
| F4 | Follow-ups | CRM da clínica | quantos contatos ativos a equipe registrou por lead | extração automatizada | `data/raw/follow_ups.csv` |
| F5 | Investimento em anúncios | Meta Ads | gasto por anúncio no período | exportação manual do Gerenciador de Anúncios | `data/raw/meta_ads.csv` |

## F1 a F4: CRM da clínica

**O que é.** O CRM é o sistema onde a clínica atende os pacientes que chegam pelo anúncio. Cada clique
em "Enviar mensagem" no anúncio abre uma conversa no WhatsApp e cria um lead na primeira etapa do funil.
A equipe da clínica move o lead pelas etapas conforme o atendimento avança.

- Funil analisado: Funil de Vendas, o único da clínica
- Acesso: somente leitura, com autorização da clínica

**Etapas do funil (F2).**

| Ordem | Etapa | Significado |
|---|---|---|
| 1 | Novo Lead | entrou pelo anúncio, ninguém atendeu ainda |
| 2 | Em Contato | a equipe iniciou o atendimento |
| 3 | Agendado | consulta de avaliação marcada (campo obrigatório: Data da Consulta) |
| 4 | Faltante | agendou e não compareceu |
| 5 | Avaliado | compareceu e recebeu orçamento |
| 6 | Venda Realizada | fechou tratamento |
| 7 | Perdido | desistiu ou foi descartado |

**Âncora de data.** O lead pertence ao trimestre em que **entrou** no CRM (`created_at`), a chamada
análise por safra (coorte). A alternativa é contar cada etapa pela data em que ela aconteceu; ela gera
os 614 leads e as 11 vendas que aparecem em outras telas do CRM. Este projeto usa a safra em tudo, porque
a pergunta é "o que aconteceu com os pacientes que chegaram neste trimestre".

**Campos de F1 (`leads.csv`).**

| Campo | Tipo | Descrição |
|---|---|---|
| `lead_key` | texto | identificador do lead, pseudonimizado (hash) |
| `contact_key` | texto | identificador da pessoa, pseudonimizado; a mesma pessoa pode ter mais de um lead |
| `periodo` | texto | `atual` (jun a ago) ou `anterior` (mar a mai) |
| `created_at` | data e hora UTC | entrada do lead no CRM |
| `source`, `platform`, `channel` | texto | origem (META_ADS), rede do anúncio (Instagram, Facebook), canal (WhatsApp) |
| `ad_id` | texto | id do anúncio no Meta Ads; liga F1 com F5 |
| `ddd` | texto | DDD do telefone, único resto do número |
| `status` | texto | OPEN, CONVERTED, LOST |
| `stage_order`, `stage_name` | número, texto | etapa atual |
| `data_consulta` | data | Data da Consulta digitada pela equipe ao agendar |
| `last_contact_at`, `last_lead_contact_at` | data e hora | última mensagem de qualquer lado, e última do lead |
| `closed_at`, `deal_status`, `quoted_value`, `quoted_at`, `closed_value` | vários | orçamento e venda |
| `responsible_key` | texto | atendente responsável, pseudonimizado |

**Mensagens (F3).** Para cada lead do recorte, a extração lê as mensagens da conversa do dia anterior
à entrada até 30 dias depois. Guarda só `direction` (INBOUND do lead, OUTBOUND da equipe), `type`
(texto, áudio, imagem) e `sent_at`. O conteúdo nunca é gravado.

**Follow-ups (F4).** Contagem de follow-ups realizados por lead entre 01/03/2026 e a data da extração.
Só vêm os leads com pelo menos um follow-up; os demais têm zero.

## F5: Meta Ads

**O que é.** O Gerenciador de Anúncios do Meta, onde a agência gere as campanhas da clínica
(nome e id da conta omitidos).

**Por que manual.** A conta não permite exportação automática para este projeto. A exportação é feita à mão:

1. Gerenciador de Anúncios, conta de anúncios da clínica, aba **Anúncios**.
2. Período: 01/06/2026 a 31/08/2026.
3. Colunas: **ID do anúncio**, **Nome do anúncio**, **Valor usado (BRL)**.
4. Exportar como CSV e salvar em `data/raw/meta_ads.csv`.

`src/clean.py` reconhece os cabeçalhos em português e em inglês e soma o gasto por anúncio. Sem o arquivo,
a limpeza roda normalmente e o custo por lead e por venda fica de fora.

## Privacidade (LGPD)

Os dados são de pacientes reais, então a anonimização acontece **na extração**, antes de qualquer arquivo
chegar ao disco:

| Dado pessoal | Tratamento |
|---|---|
| Nome, e-mail, foto | descartados |
| Telefone | descartado; fica só o DDD |
| Id do lead, do contato e do atendente | substituídos por hash SHA-256 com sal secreto (`data/.salt`, fora do repositório) |
| Texto das mensagens | nunca lido para o disco |

`src/clean.py` termina com uma checagem que falha se alguma coluna com nome de dado pessoal aparecer
no resultado.

## Como reproduzir

```bash
pip install -r requirements.txt
python src/clean.py
python src/mine.py
```

O script de extração depende de acesso ao CRM da clínica e fica fora do repositório. A limpeza e a
mineração rodam sobre os CSVs já anonimizados em `data/raw/`.
