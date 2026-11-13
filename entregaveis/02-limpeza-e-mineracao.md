# Entregável 2. Limpeza e mineração dos dados

Nexus Assessoria. Diagnóstico de funil comercial, fase 2.

Os passos estão em `src/clean.py` (limpeza) e `src/mine.py` (mineração). A cada execução, a limpeza grava
`data/processed/limpeza_log.csv` com as linhas que entraram e saíram de cada passo. Os números abaixo
vêm desse log, na extração de 12/11/2026.

## Visão geral do fluxo

```
CRM da clínica ──extração──> data/raw/       (anonimizado na coleta)
                                │
                           clean.py           (11 passos, log por passo)
                                │
                                v
                      data/processed/leads_tratados.csv
                      data/processed/funil_resumo.csv
                                │
                            mine.py           (8 recortes)
                                │
                                v
                      data/processed/mineracao_*.csv  ──> dashboard (Streamlit)
```

## Parte A: limpeza

### Passos e resultado

| # | Passo | Antes | Depois | O que foi feito |
|---|---|---|---|---|
| 0 | Anonimização | | | na extração: nome, telefone, e-mail, foto e texto descartados; ids trocados por hash com sal |
| 1 | Carga | 1.073 | 1.073 | leads dos dois trimestres (611 atual, 462 anterior) |
| 2 | Tipos | 1.073 | 1.073 | datas ISO 8601 em UTC convertidas para o horário de São Paulo; valores para número |
| 3 | Registros inválidos | 1.073 | 1.073 | regra para lead excluído, sem data ou sem etapa; nenhum caso |
| 4 | Duplicatas | 1.073 | 1.064 | 9 reentradas removidas (ver abaixo) |
| 5 | Funil derivado | 1.064 | 1.064 | etapa atual vira as flags `em_contato`, `agendou`, `faltou`, `avaliado`, `vendeu`; 35 cadastros manuais marcados (23 no recorte atual) |
| 6 | Inconsistências | 1.064 | 1.064 | marcadas, não removidas: 1 venda sem valor, 1 consulta antes da entrada, 3 agendados sem data |
| 7 | Mensagens | 2.654 | 2.632 | 22 mensagens repetidas ou sem horário removidas |
| 8 | Cobertura de mensagens | 602 | 215 | só leads que entraram depois de 07/08/2026 têm histórico de WhatsApp |
| 9 | Tempo de resposta | 602 | 602 | primeira resposta da equipe depois da primeira mensagem do lead |
| 10 | Follow-ups | 602 | 602 | 11 leads com follow-up; ausência vira zero |
| 11 | Meta Ads | | | gasto por anúncio, quando `data/raw/meta_ads.csv` existe |

### Decisões de limpeza

**Q1. Qual data define o trimestre do lead?**
Decisão: a data de entrada no CRM (análise por safra).
Por quê: a pergunta acompanha o paciente que chegou no trimestre até o fim do funil. Com essa âncora, o
recorte fecha com 611 leads brutos e 602 depois da limpeza. A contagem por data do evento, que conta cada etapa pela
data em que aconteceu, dá 614 leads e 11 vendas. É esse o número que aparece em outras telas do CRM e na
fase 1. A diferença foi checada e não é erro.

**Q2. O que é lead duplicado?**
Decisão: só sai o lead que ficou parado em Novo Lead quando a mesma pessoa tem outro lead no trimestre.
Por quê: a pessoa clica de novo no anúncio, o CRM abre um lead novo, e esse lead nunca é trabalhado
porque o atendimento segue no original. A primeira versão da regra mantinha só um lead por pessoa e
apagou uma venda real: o mesmo contato fechou dois tratamentos no mesmo dia (R$ 9.620 e R$ 6.465).
Dois leads que avançaram são dois atendimentos, e ficam.

**Q3. Como saber até onde o lead chegou, se o CRM só guarda a etapa atual?**
Decisão: a etapa atual vale como a mais avançada alcançada. Exemplo: quem está em Avaliado passou por
Em Contato e Agendado.
Por quê: o CRM não exporta histórico de etapas. A exceção é **Faltante**. Ela fica na posição 4, entre
Agendado e Avaliado, mas é um desvio, não um degrau. O contador do CRM conta como "passou por Faltante"
todo mundo que está em Avaliado ou depois, e por isso mostrava 50 faltantes. Na limpeza, falta real é só
quem está parado em Faltante: **27**.

**Q4. A etapa Perdido zerada é um dado?**
Decisão: não. Lead parado em Em Contato fica em aberto, e a análise não conta isso como perda.
Por quê: em vez de mover o lead para Perdido, a equipe deixa ele parado. São 494 leads em Em Contato no
fim do recorte e 1 em Perdido. O motivo da perda não existe na base, e a análise diagnóstica precisa
chegar a ele por outros sinais (tempo de resposta, engajamento).

**Q5. Lead cadastrado à mão é igual a lead do anúncio?**
Decisão: não. O cadastro manual ganha uma flag (`cadastro_manual`) e sai das análises de horário e de
anúncio.
Por quê: o CRM grava só o dia do cadastro manual, então a hora sai meia-noite exata. A análise de horário
leria essa meia-noite como "lead que chegou de madrugada". Além disso, são pacientes que já chegam
agendados: no recorte, os 23 agendaram e 9 compraram.

**Q6. Lead sem mensagem é lead que ninguém atendeu?**
Decisão: só a partir de 07/08/2026. Antes disso, "sem mensagem" vira "sem dado".
Por quê: a primeira mensagem guardada no CRM é de 07/08/2026, e nenhum lead de junho ou julho tem
mensagem. A integração com o WhatsApp não guardava o histórico anterior. As análises de atendimento usam
só os 212 leads de anúncio que entraram depois dessa data.

**Q7. Tempo de resposta de quanto?**
Decisão: o tempo vai da primeira mensagem do lead até a primeira mensagem da equipe **depois dela**.
Resposta depois de 72 horas não conta como primeira resposta.
Por quê: mensagem automática da equipe enviada antes do lead falar não é resposta. Depois de 72 horas, a
mensagem é retomada de contato, e misturar as duas coisas puxaria a média para dias.

**Q8. Inconsistência é apagada?**
Decisão: não. Ela é marcada na coluna `inconsistencias`. Só a data de consulta anterior à entrada do lead
vira vazio, porque é erro de digitação e não serve para medir espera.
Por quê: apagar o lead mudaria o funil. Quem lê a base consegue filtrar o problema e ver quantos casos há.

### Vieses que sobram

| Viés | Efeito | Como a análise lida |
|---|---|---|
| Histórico de mensagens só desde 07/08 | atendimento medido em 1/3 dos leads | resultado de atendimento vale para agosto, e o documento diz isso |
| Sem histórico de etapas | não dá para medir quanto tempo o lead ficou em cada etapa | só a etapa final é usada |
| Perdido sem uso, sem motivo de perda | o "porquê" da perda não está na base | inferido por tempo de resposta e engajamento |
| Follow-up quase não registrado (11 leads) | impossível medir efeito do follow-up | o próprio baixo registro é o achado |
| Gasto do Meta fora do CRM | custo por lead e por venda dependem da exportação manual | colunas ficam vazias até o CSV existir |

## Parte B: mineração

A mineração procura o que separa o lead que avança do que para. A técnica é a **segmentação**: cada lead
ganha um atributo derivado (faixa de tempo de resposta, horário de entrada, número de mensagens, dias até
a consulta, anúncio), e a taxa de agendamento ou de comparecimento é comparada entre as faixas. A análise
é descritiva e diagnóstica, então descreve associação. Ela não prova causa.

### Atributos derivados

| Atributo | Regra | Faixas |
|---|---|---|
| `faixa_resposta` | `tempo_resposta_min` | até 5 min, 5 a 30 min, 30 min a 2 h, 2 a 24 h, 24 a 72 h, sem resposta |
| `entrada` | dia útil entre 8h e 18h | horário comercial, fora do horário (8h às 18h é suposição: a clínica não informou o horário dela) |
| `msgs_do_lead` | mensagens do lead em 30 dias | 0, 1, 2 a 3, 4+ |
| `espera` | dias entre a entrada e a Data da Consulta | 0 a 2, 3 a 7, 8 a 14, 15+ |
| `ad_id` | anúncio de origem | um grupo por anúncio |

### Primeiros resultados (recorte atual)

| Recorte | Achado | Base |
|---|---|---|
| Origem do lead | 579 leads vieram do anúncio e geraram **1 venda**; os 23 cadastros manuais geraram **9** | 602 |
| Trimestres | agendamento dos leads de anúncio caiu de 8,4% (38 de 450) para 4,7% (27 de 579) | 1.029 |
| Tempo de resposta | mediana de **5,4 horas** até a primeira resposta; 75% esperam até 15 horas | 198 |
| Horário | quem entra fora do horário espera em mediana **13 h**, contra 1 h em horário comercial; agenda 4,2% contra 6,5% | 212 |
| Engajamento | 47% dos leads mandam uma mensagem só (o texto pronto do anúncio) e nenhum deles agenda; quem troca 4 ou mais agenda 15,9% | 212 |
| Falta | 27 de 50 agendados faltaram (54%); com 3 a 7 dias de espera, a falta sobe para 75% | 50 |
| Follow-up | 11 leads com follow-up registrado, em 602 | 602 |

As tabelas completas estão em `data/processed/mineracao_*.csv`. A leitura de negócio, com as perguntas
que cada uma responde, está em [03-regra-de-negocio.md](03-regra-de-negocio.md).

## Como validar

```bash
python -m pytest -q tests     # regras de limpeza: primeira resposta, funil, duplicata
python src/clean.py           # imprime o log passo a passo
python src/mine.py            # imprime cada tabela de mineração
```
