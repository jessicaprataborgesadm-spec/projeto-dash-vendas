# Catálogo de Intenções — IA Analista | Projeto Dash Vendas

Status: catálogo inicial da IA Analista, alinhado à base e aos resultados publicados.
Escopo: primeira versão funcional integrada ao dashboard Streamlit.

## 1. Objetivo

A IA Analista deve entender perguntas de negócio, selecionar uma intenção conhecida, solicitar os parâmetros necessários, chamar uma rotina determinística e explicar somente os fatos retornados.

O LLM não deve calcular valores, inventar métricas, escolher livremente tabelas ou receber a base inteira para produzir uma análise genérica.

## 2. Dados disponíveis para o MVP

### Base diária

Arquivo: `base_treinamento_faturamento_teste.csv`

Granularidade: uma linha por dia corrido.
Cobertura: 01/01/2017 a 29/08/2018 (606 linhas).

Colunas disponíveis:
- `data`
- `dia_semana`
- `faturamento_diario`
- `faturamento_ano_anterior`
- `qtd_pedidos_entregues`
- `qtd_linhas_itens_entregues`
- `media_7d`
- `eh_feriado_nacional`
- `eh_data_movel`
- `eh_data_comercial`
- `eventos_calendario`

A métrica chamada `faturamento_diario` é uma aproximação operacional: soma de `olist_order_items.price` para pedidos cujo status atual é `delivered`, agrupada por data da compra, sem frete. Não é faturamento contábil nem receita líquida reconciliada.

A referência anual tem cobertura parcial. Na exportação atual, `faturamento_ano_anterior` possui 365 valores nulos e só deve ser utilizada nos dias em que o valor está presente.

### Arquivos de avaliação e previsão

- `20_previsoes_random_forest_teste.csv`: teste inicial de 01/07/2018 a 30/07/2018, com realizado, previsão RF, baseline e erros.
- `21_resultado_validacao_temporal.csv`: cinco janelas de 30 dias e uma linha agregada das cinco janelas.
- `22_resultado_janela_recente.csv`: diagnóstico recente de 31/07/2018 a 29/08/2018.
- `24_previsao_30_dias_corte_20_08.csv`: simulação de 21/08/2018 a 19/09/2018, sem faturamento realizado para o horizonte.

## 3. Intenções do MVP

IDs técnicos usados no motor determinístico (`ia_analista/analytics.py`):

| ID funcional | Intenção | Função |
|---|---|---|
| `period_evolution` | INT-01 · Evolução do indicador | `analisar_evolucao` |
| `period_comparison` | INT-02 · Comparação entre períodos | `comparar_periodos` |
| `weekday_pattern` | INT-03 · Padrão por dia da semana | `analisar_dia_semana` |
| `calendar_analysis` | INT-04 · Calendário e feriados | `analisar_calendario` |
| `change_diagnosis` | INT-05 · Diagnóstico de queda/aumento | `diagnosticar_variacao` |
| `forecast_summary` | INT-06 · Consulta da previsão | `consultar_previsao_30_dias` |
| `model_performance` | INT-07 · Desempenho dos modelos | `avaliar_modelos` |

`executar_intencao` recebe esses identificadores explícitos. Ele ainda não interpreta texto livre; o roteador de linguagem natural será implementado na etapa seguinte.


### INT-01 — Evolução do indicador

**Perguntas de exemplo**
- Como o faturamento evoluiu no período?
- Qual foi o faturamento total em julho de 2018?
- Qual foi a média diária no período selecionado?

**Fonte:** base diária.

**Parâmetros:** data inicial e final. Se ausentes, pedir o período em vez de adivinhar.

**Cálculos determinísticos:** soma, média diária, mínimo, máximo, contagem de dias, série por dia/mês e variação entre períodos quando solicitada.

**Resposta deve trazer:** período, total, média diária, quantidade de dias e observação sobre a definição operacional da métrica.

**Limite:** não chamar o valor de receita contábil.

### INT-02 — Comparação entre períodos / ano anterior

**Perguntas de exemplo**
- Como o período atual se compara ao mesmo período do ano anterior?
- O valor dos itens cresceu ou caiu em relação ao ano anterior?
- Compare julho de 2018 com julho de 2017.

**Fonte:** base diária, usando `faturamento_diario` e `faturamento_ano_anterior`.

**Parâmetros:** período de referência e tipo de comparação (período anterior ou mesmo período do ano anterior).

**Cálculos determinísticos:** total e média diária dos períodos comparáveis, diferença absoluta, variação percentual e quantidade de pares de datas válidos.

**Regra de cobertura:** excluir pares sem referência anual e informar quantas datas foram comparadas. Se não houver pares suficientes, retornar `partial_data` ou `insufficient_data`, sem preencher NULL com zero.

**Limite:** não afirmar crescimento anual para datas sem valor comparável.

### INT-03 — Padrão por dia da semana

**Perguntas de exemplo**
- Qual dia da semana costuma ter maior valor diário?
- Segunda-feira vende menos que sexta-feira?
- Como se distribui o valor diário por dia da semana?

**Fonte:** base diária, campos `dia_semana` e `faturamento_diario`.

**Parâmetros:** período opcional.

**Cálculos determinísticos:** média, mediana, mínimo, máximo e quantidade de dias por dia da semana.

**Regra de comparação:** classificar os dias pela média diária, não pelo total bruto, para não favorecer dias com mais ocorrências no período.

**Limite:** associação descritiva. Não concluir que o dia da semana causa a diferença.

### INT-04 — Calendário e feriados

**Perguntas de exemplo**
- O que aconteceu nos feriados observados?
- Como foi o valor diário em datas comerciais?
- Há diferença descritiva entre dias sinalizados como feriado e os demais?

**Fonte:** base diária, campos `eh_feriado_nacional`, `eh_data_movel`, `eh_data_comercial`, `eventos_calendario` e `faturamento_diario`.

**Parâmetros:** período opcional e categoria do calendário.

**Cálculos determinísticos:** quantidade de dias por categoria, média/mediana diária, soma e comparação com dias não sinalizados.

**Regra de resposta:** apresentar sempre o tamanho da amostra. Comparações com poucos feriados ou eventos devem ser rotuladas como evidência limitada.

**Limite:** não atribuir causalidade ao feriado, campanha ou evento.

### INT-05 — Diagnóstico de queda ou aumento

**Perguntas de exemplo**
- Por que o faturamento caiu neste período?
- O que mudou nos dias de maior queda?
- A redução ocorreu junto com menos pedidos ou menos itens?

**Fonte:** base diária, campos `faturamento_diario`, `qtd_pedidos_entregues`, `qtd_linhas_itens_entregues`, `media_7d`, calendário e dia da semana.

**Parâmetros:** período analisado e período de comparação. Se o usuário não especificar comparação, propor o intervalo imediatamente anterior de mesma duração e informar essa escolha.

**Cálculos determinísticos:** variação do valor diário, quantidade de pedidos atualmente `delivered`, quantidade de linhas de itens, valor operacional médio por pedido quando a contagem for maior que zero, dias de maior contribuição para a variação e comparação com calendário/dia da semana.

**Resposta obrigatória:** separar:
1. fatos observados (o que variou);
2. associações que merecem investigação;
3. hipóteses não comprovadas;
4. dados que faltam para atribuir a causa.

**Limites importantes:** a base diária não contém produto, categoria, estado, cidade ou cliente. Não atribuir a queda a essas dimensões. O status atual `delivered` e a queda de cobertura na cauda histórica impedem afirmar automaticamente que houve queda real de demanda.

### INT-06 — Consulta da previsão de 30 dias

**Perguntas de exemplo**
- Qual é a previsão dos próximos 30 dias?
- Quanto o Random Forest prevê no horizonte?
- Como a previsão se compara ao baseline?
- Quais datas têm as maiores previsões?

**Fonte:** `24_previsao_30_dias_corte_20_08.csv`.

**Parâmetros:** modelo (RF, baseline ou ambos) e nível de detalhe (total ou diário). Se não forem informados, apresentar os dois totais e oferecer a série diária.

**Cálculos determinísticos:** soma, média, mínimo, máximo, diferença RF-baseline e ordenação das datas.

**Aviso obrigatório:** trata-se de simulação retrospectiva com corte em 20/08/2018, para 21/08/2018 a 19/09/2018. Não é previsão atual. O arquivo não contém realizado maduro, portanto não há métrica de erro para esse horizonte.

### INT-07 — Desempenho e comparação dos modelos

**Perguntas de exemplo**
- O Random Forest foi melhor que o baseline?
- Qual modelo teve menor WAPE?
- O Random Forest venceu em todas as janelas?
- Como foi o desempenho no período recente?

**Fontes:**
- `20_previsoes_random_forest_teste.csv`: teste inicial de julho.
- `21_resultado_validacao_temporal.csv`: cinco janelas e agregado.
- `22_resultado_janela_recente.csv`: diagnóstico separado recente.

**Cálculos determinísticos:** MAE, RMSE e WAPE nas linhas com realizado; comparação de WAPE por janela; contagem de janelas vencidas por cada modelo.

**Regra de interpretação:** não misturar o teste inicial, o agregado de cinco janelas e a janela recente como se fossem um único teste. Explicar período e quantidade de janelas.

**Fato conhecido a preservar:** nas cinco janelas, o Random Forest teve WAPE agregado menor que o baseline, mas venceu somente três das cinco janelas.

**Limite:** o resultado histórico não garante desempenho futuro.

## 4. Perguntas fora do escopo inicial

Responder de forma explícita que os dados atuais não permitem calcular:
- qual estado/cidade contribuiu mais;
- qual produto ou categoria explica a variação;
- qual cliente comprou mais;
- impacto por forma de pagamento;
- previsão atual ou previsão alimentada por dados recentes.

Essas perguntas podem virar intenções futuras depois de carregar e auditar as tabelas/dimensões necessárias. Não simular respostas usando a série diária agregada.

## 5. Contrato de entrada do roteador

O roteador deve converter a mensagem em uma estrutura validável antes de chamar qualquer função analítica. Esquema conceitual:

```json
{
  "intent": "period_evolution",
  "period": {
    "start_date": "2018-07-01",
    "end_date": "2018-07-30"
  },
  "comparison": null,
  "filters": {},
  "detail_level": "summary"
}
```

A intenção e os nomes de campos acima são identificadores internos propostos para a implementação. Datas são exemplos, não valores padrão.

Validações:
- intenção deve pertencer ao catálogo;
- datas devem ser válidas e estar na cobertura da fonte, ou a resposta deve indicar cobertura parcial;
- início não pode ser posterior ao fim;
- filtros devem corresponder a colunas disponíveis;
- parâmetros ambíguos devem gerar pedido de esclarecimento, não suposição silenciosa.

## 6. Contrato de saída analítica

As rotinas determinísticas devem devolver fatos estruturados. Esquema conceitual:

```json
{
  "status": "ok",
  "intent": "period_evolution",
  "metric": {
    "name": "faturamento_diario",
    "definition": "Soma de price dos itens em pedidos atualmente delivered, por data de compra, sem frete"
  },
  "period": {
    "start_date": "2018-07-01",
    "end_date": "2018-07-30"
  },
  "facts": {},
  "coverage": {
    "rows_used": 30,
    "rows_excluded": 0
  },
  "limitations": []
}
```

Status possíveis:
- `ok`: dados suficientes para responder;
- `partial_data`: resposta possível, mas com cobertura parcial;
- `insufficient_data`: dados insuficientes;
- `ambiguous`: falta esclarecer período ou parâmetro;
- `out_of_scope`: intenção não suportada pela versão atual.

O LLM recebe somente esse resultado estruturado e a pergunta original. Sua função é explicar os fatos, não recalcular ou inventar números.

## 7. Próxima etapa de implementação

Implementar primeiro as funções analíticas determinísticas em Python, usando os CSVs existentes. Cada função deve ter testes unitários com entradas conhecidas e resultados esperados. Só depois construir o roteador e conectar o provedor de LLM.

Não implementar SQL gerada livremente pelo LLM. Não enviar a base inteira ao modelo. Não escolher o provedor de LLM antes de avaliar requisitos, custos, credenciais e integração.
