# Entregável 3. Regra de negócio, objetivo e métricas

Atualiza o documento da fase 1 (diagnóstico) com as regras de negócio que a análise segue, as métricas e
cinco perguntas complementares à premissa inicial.

Assessoria: Nexus Assessoria (Eduardo e Henrique). Cliente: Clínica odontológica em Campina Grande - PB. Recorte: 01/06 a 31/08/2026.

## Premissa inicial (fase 1)

A clínica recebe pacientes pelo anúncio do Meta Ads, que chegam pelo WhatsApp e são atendidos pela equipe da
clínica. De junho a agosto de 2026 entraram mais leads que no trimestre anterior, e as vendas caíram: a
conversão foi de 3,0% para 1,7%.

**Pergunta de negócio:** em quais etapas do funil a clínica perde os pacientes, por quê, e quanto de
receita isso representa?

## Objetivo

Mostrar à clínica e à agência **onde** o funil vaza, **qual comportamento** acompanha o vazamento, e
**quanto vale** recuperar cada um. O resultado é um dashboard que a clínica e a agência acompanham toda
semana.

| Objetivo específico | Como se mede |
|---|---|
| Localizar a etapa que mais perde | taxa de passagem entre etapas, comparada ao trimestre anterior |
| Explicar a perda | taxa de agendamento e de falta por segmento (tempo de resposta, horário, engajamento, espera) |
| Dar valor à perda | receita que cada vazamento deixa de gerar, mantidas as outras taxas |
| Separar mídia de atendimento | resultado por anúncio contra resultado por etapa de atendimento |

## Regras de negócio

| Código | Regra |
|---|---|
| RN01 | O lead pertence ao trimestre em que **entrou** no CRM (análise por safra), e todas as etapas dele contam nesse trimestre, mesmo as que aconteceram depois. |
| RN02 | Lead é **duplicado** quando a mesma pessoa tem outro lead no trimestre e este ficou parado em Novo Lead. Dois leads da mesma pessoa que avançaram são dois atendimentos. |
| RN03 | A etapa atual é a etapa mais avançada que o lead alcançou. Quem está em Avaliado também conta como Em Contato e Agendado. |
| RN04 | **Faltante** é desvio, não degrau. Falta é só o lead parado em Faltante. Quem está em Avaliado ou depois compareceu. |
| RN05 | **Venda** é o lead em Venda Realizada, com status CONVERTED ou com negócio WON. A receita é o `closedValue` do negócio. |
| RN06 | **Lead de anúncio** é o criado automaticamente pela mensagem do anúncio. **Cadastro manual** é o lançado pela equipe (hora gravada como meia-noite exata). Os dois são analisados em separado. |
| RN07 | **Tempo de primeira resposta** vai da primeira mensagem do lead até a primeira mensagem da equipe depois dela. Mais de 72 horas não conta como primeira resposta. |
| RN08 | **Horário comercial** é segunda a sexta, das 8h às 18h, no horário de São Paulo. É suposição da Nexus: a clínica não informou o horário dela. |
| RN09 | Análise de atendimento (resposta, engajamento) só usa leads que entraram a partir de **07/08/2026**, a data da primeira mensagem guardada no CRM. |
| RN10 | Lead parado em Em Contato está **em aberto**, não perdido, porque a clínica não usa a etapa Perdido. |

## Métricas

| Métrica | Fórmula | Trimestre anterior | Recorte atual |
|---|---|---|---|
| Leads | leads após limpeza | 462 | 602 |
| Taxa de atendimento | Em Contato ÷ Leads | 87,4% | 90,4% |
| Taxa de agendamento | Agendado ÷ Em Contato | 12,4% | **9,2%** |
| Taxa de comparecimento | Avaliado ÷ Agendado | 62,0% | **46,0%** |
| Taxa de falta | Faltante ÷ Agendado | 38,0% | **54,0%** |
| Taxa de fechamento | Venda ÷ Avaliado | 45,2% | 43,5% |
| Conversão total | Venda ÷ Leads | 3,0% | **1,7%** |
| Vendas | contagem (RN05) | 14 | 10 |
| Receita | soma de `closedValue` | R$ 45.665 | R$ 54.105 |
| Ticket médio | Receita ÷ Vendas | R$ 3.262 | R$ 5.411 |
| Tempo de primeira resposta | mediana (RN07) | sem dado | 5,4 h |
| Custo por lead (CPL) | Gasto Meta ÷ Leads de anúncio | pendente | pendente |
| Custo por venda (CAC) | Gasto Meta ÷ Vendas de anúncio | pendente | pendente |
| ROAS | Receita ÷ Gasto Meta | pendente | pendente |

CPL, CAC e ROAS dependem da exportação do Meta Ads ([fontes, F5](01-fontes-de-dados.md#f5-meta-ads)).

A receita deste documento (R$ 54.105 em 10 vendas) é menor que a da fase 1 (R$ 66.105 em 11 vendas)
por causa da âncora. A fase 1 contou as vendas fechadas no trimestre (data do evento), e este documento conta as
vendas dos leads que entraram no trimestre (RN01).

### Leitura

- O ticket médio subiu e a taxa de fechamento ficou estável. Quando o paciente chega à avaliação, a
  clínica vende igual.
- A perda está antes da avaliação, em duas etapas. O agendamento caiu de 12,4% para 9,2% dos atendidos, e
  a falta subiu de 38% para 54% dos agendados.

### Quanto vale cada vazamento

O cálculo mantém as demais taxas do recorte atual: comparecimento de 46%, fechamento de 43,5% e ticket
de R$ 5.411.

| Cenário | Vendas a mais | Receita a mais |
|---|---|---|
| Os 27 faltantes comparecem | 11,7 | R$ 63.515 |
| O agendamento volta para 15% dos atendidos (de 50 para 82 agendados) | 6,3 | R$ 34.194 |

## Achado que reformula a premissa

A premissa trata os 602 leads como um funil só. A limpeza separou duas origens (RN06), e elas se comportam
de forma oposta:

| Origem | Leads | Agendou | Vendeu | Receita |
|---|---|---|---|---|
| Anúncio (automático) | 579 | 27 (4,7%) | **1** | R$ 9.000 |
| Cadastro manual da equipe | 23 | 23 (100%) | **9** | R$ 45.105 |

No trimestre anterior foram 5 vendas de anúncio e 9 de cadastro manual. Toda a queda de vendas veio do
lead de anúncio: de 5 para 1. O agendamento desse lead caiu de 8,4% para 4,7%.

O cadastro manual pode ser paciente do próprio anúncio que a equipe atendeu por outro número e lançou
depois. Também pode vir de indicação ou de quem chegou direto na clínica. A base não diz qual é o caso.
Essa resposta vem da clínica, e é ela que diz se o anúncio está gerando venda ou só volume.

## Perguntas complementares

Cinco perguntas que desdobram o "por quê" da pergunta de negócio. Cada uma tem a métrica que a responde e
o primeiro resultado da mineração. As bases são pequenas, então o resultado é indício, não conclusão.

### P1. O tempo até a primeira resposta muda a chance de o lead agendar?

- **Hipótese:** lead que espera horas esfria e procura outra clínica.
- **Métrica:** taxa de agendamento por faixa de tempo de resposta (RN07, RN09).
- **Primeiro resultado:** a mediana de resposta é 5,4 horas. Quem recebeu resposta entre 5 e 30 minutos
  agendou 16,7% das vezes (4 de 24). Quem esperou de 2 a 24 horas agendou 4,1% (4 de 97).
- **Tabela:** `mineracao_tempo_resposta.csv`.

### P2. O lead que chega fora do horário comercial é atendido mais tarde e agenda menos?

- **Hipótese:** 57% dos leads de anúncio de agosto (120 de 212) chegam à noite ou no fim de semana,
  quando ninguém responde.
- **Métrica:** mediana de resposta e taxa de agendamento, dentro e fora do horário (RN08).
- **Primeiro resultado:** fora do horário, a primeira resposta leva em mediana 13 horas, contra 1 hora
  em horário comercial. O agendamento fica em 4,2%, contra 6,5%.
- **Tabela:** `mineracao_horario_entrada.csv`, `mineracao_dia_semana.csv`.

### P3. Que parte dos leads do anúncio tem intenção real de conversa?

- **Hipótese:** o anúncio traz volume de quem clica e manda só a mensagem pronta, sem intenção de
  agendar. Isso explicaria mais leads com menos vendas.
- **Métrica:** distribuição de mensagens do lead em 30 dias, e taxa de agendamento por faixa.
- **Primeiro resultado:** 47% dos leads mandam uma mensagem só, e nenhum deles agenda. Quem troca 4 ou
  mais mensagens agenda 15,9%. Problema de mídia (público errado) e problema de abordagem (a primeira
  resposta não engaja) ficam assim lado a lado, e o cruzamento com a P1 ajuda a separar os dois.
- **Tabela:** `mineracao_engajamento.csv`.

### P4. O prazo entre o agendamento e a consulta influencia a falta?

- **Hipótese:** consulta marcada para muitos dias depois é esquecida, e sem lembrete o paciente falta.
- **Métrica:** taxa de falta por faixa de espera (dias entre a entrada e a Data da Consulta).
- **Primeiro resultado:** com 3 a 7 dias de espera, 75% faltaram (18 de 24). Com 0 a 2 dias, 47%. Com
  15 dias ou mais, nenhum faltou, mas são só 5 casos (3 de anúncio, 2 manuais). Sem registro de lembrete
  ou confirmação no CRM, a hipótese do lembrete não tem como ser testada direto.
- **Tabela:** `mineracao_falta_por_espera.csv`.

### P5. Quais anúncios trazem paciente que agenda e compra, e quanto custa cada venda por anúncio?

- **Hipótese:** parte do orçamento vai para anúncios que geram conversa e não geram agendamento.
- **Métrica:** leads, agendamentos e vendas por anúncio, e, com o gasto do Meta, custo por lead e por venda.
- **Primeiro resultado:** o anúncio que mais trouxe leads (`120245518413860438`, 203 leads, 35% do
  volume) teve a menor taxa de agendamento entre os grandes (2,5%) e nenhuma venda. O custo por venda
  depende do CSV do Meta.
- **Tabela:** `mineracao_anuncios.csv`.

## Próximos passos

1. Exportar o gasto por anúncio do Meta Ads e rodar de novo `clean.py` e `mine.py`. Isso fecha CPL, CAC,
   ROAS e a P5.
2. Perguntar à clínica de onde vem o cadastro manual (ver o achado acima).
3. Montar o dashboard em Streamlit sobre `data/processed/`.
