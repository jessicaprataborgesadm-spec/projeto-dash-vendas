# PROJECT_MEMORY.md

Memória de continuidade e fonte de referência do Projeto Dash Vendas. Atualizada em 23/11/2026.

## 1. Objetivo e escopo da versão de portfólio

Construir uma solução de Dados + Machine Learning com dados públicos do e-commerce Olist para:
- transformar dados transacionais em uma série diária analítica;
- investigar qualidade, cobertura e comportamento temporal;
- comparar um baseline com Random Forest;
- produzir uma simulação retrospectiva de previsão diária por 30 dias;
- apresentar histórico, validação e previsão em um dashboard Streamlit local.

**Escopo da V1 considerado concluído:** base analítica, features, baseline, Random Forest, backtests, previsão simulada, dashboard local, documentação e reprodução em clone limpo.

**Fora do escopo da V1:** IA Analista conversacional, inferência local/WebGPU, publicação/hospedagem do dashboard e conexão em tempo real do Streamlit com BigQuery. São evoluções futuras, não bloqueiam o encerramento da V1.

## 2. Fonte e definição da métrica

- Fonte pública: Brazilian E-Commerce Public Dataset by Olist (Kaggle).
- Projeto GCP: `projeto-dash-vendas`.
- Dataset BigQuery: `raw`.
- Região: `southamerica-east1`.
- Tabelas RAW usadas na métrica: `raw.olist_orders` e `raw.olist_order_items`.
- Join: `order_id`.
- Filtro: status atual do pedido `delivered`.
- Métrica: soma de `olist_order_items.price`, sem `freight_value`.
- Data de agregação: `DATE(order_purchase_timestamp)`.
- Granularidade final: **uma linha por dia corrido**.

A métrica é uma aproximação operacional do valor dos itens associados a pedidos atualmente `delivered`. Não é faturamento contábil nem receita líquida reconciliada. O status atual pode refletir eventos posteriores à compra; a cobertura temporal da cauda da série é irregular e exige cautela.

## 3. Arquitetura existente

```text
Olist / Kaggle
    -> BigQuery RAW
    -> SQL / ELT (consultas versionadas 01 a 18)
    -> base diária e features
    -> exportação CSV
    -> Python (baseline, Random Forest, backtests e previsão)
    -> CSVs de resultados
    -> Streamlit local
```

O dashboard lê seis CSVs locais e não consulta BigQuery diretamente. A camada Streamlit está em `dash_vendas_python_streamlit_publicacao/`. O dashboard não está hospedado.

## 4. SQL e dados

- Consultas SQL 01 a 18 estão publicadas em `sql/`.
- SQL 10: base diária de valor dos itens.
- SQL 11: auditoria de maturidade/cobertura temporal.
- SQL 12: base de treinamento.
- SQL 14: média móvel de sete dias.
- SQL 15: dia da semana.
- SQL 16: calendário e feriados/datas relevantes.
- SQL 17: auditoria da cobertura da referência anual.
- SQL 18: feature de faturamento do ano anterior.

Base analítica exportada:
- arquivo: `base_treinamento_faturamento_teste.csv`;
- 606 linhas diárias;
- período: 01/01/2017 a 29/08/2018;
- quatro dias com target zero; nenhum target negativo ou nulo na auditoria registrada;
- `media_7d` possui sete NULLs iniciais por falta de histórico anterior.

Auditoria de chaves:
- 99.441 pedidos;
- nenhum `order_id` nulo ou duplicado na tabela de pedidos;
- nenhum par `(order_id, order_item_id)` nulo ou duplicado na tabela de itens;
- nenhum item sem pedido na auditoria executada.

Evitar JOIN com `order_payments` sem auditoria de cardinalidade, pois pode multiplicar linhas. Não alterar a definição da métrica sem revisar a documentação e as consultas.

## 5. Features e prevenção de vazamento

Features documentadas:
- `dia_semana`;
- `media_7d`;
- `faturamento_ano_anterior`, quando há cobertura;
- `eh_feriado_nacional`;
- `eh_data_movel`;
- `eh_data_comercial`.

`media_7d` usa os sete dias anteriores e nunca inclui o próprio dia previsto. Em previsão recursiva, atualiza-se com previsões anteriores, nunca com target real futuro.

## 6. Modelagem e resultados registrados

### Teste inicial: 01/07/2018 a 30/07/2018

| Métrica | Baseline | Random Forest |
|---|---:|---:|
| MAE | R$ 6.873,94 | R$ 6.390,11 |
| RMSE | R$ 8.368,83 | R$ 7.734,12 |
| WAPE | 25,05% | 23,29% |

### Validação temporal: cinco janelas de 30 dias

| Métrica agregada | Baseline | Random Forest |
|---|---:|---:|
| MAE | R$ 7.757,00 | R$ 6.966,16 |
| RMSE | R$ 9.539,33 | R$ 8.617,60 |
| WAPE | 25,27% | 22,70% |

Random Forest teve WAPE menor em três das cinco janelas, não em todas. A vantagem agregada não deve ser interpretada como garantia de desempenho futuro.

### Diagnóstico recente: 31/07/2018 a 29/08/2018

- WAPE Random Forest: 36,39%.
- WAPE baseline: 38,67%.
- Houve queda acentuada no volume/valor diário observado no fim de agosto.
- A causa da queda não foi comprovada. Não atribuir definitivamente a maturidade, falha de coleta ou mudança real de demanda.

## 7. Corte e previsão ativa de 30 dias

A análise de sensibilidade comparou a média dos sete dias encerrados na data de corte com a média dos 28 dias anteriores:
- 20/08: variação de -4,77%;
- 22/08: -23,26%;
- 24/08: -38,59%;
- 26/08: -50,89%;
- 29/08: -77,32%.

20/08/2018 foi escolhido como corte provisório mais prudente para a simulação. É uma decisão descritiva, não uma detecção estatística definitiva de ponto de mudança.

Arquivos:
- script ativo: `24_previsao_30_dias_corte_20_08.py`;
- CSV ativo no dashboard: `24_previsao_30_dias_corte_20_08.csv`;
- script e CSV anteriores de corte 22/08 permanecem preservados (versão 23).

Configuração e resultado:
- treinamento até 20/08/2018;
- 597 observações históricas até o corte;
- 590 linhas utilizáveis para treinamento após remover os sete valores iniciais sem `media_7d`;
- horizonte: 21/08/2018 a 19/09/2018, 30 dias;
- baseline constante: R$ 34.137,47 por dia;
- total Random Forest: R$ 993.231,78;
- total baseline: R$ 1.024.124,10.

O CSV foi auditado: 30 datas únicas e consecutivas, sem datas ausentes, previsões nulas ou valores negativos. Dia da semana confere com a data. Referência anual está disponível apenas de 21 a 29/08, conforme limite de cobertura adotado. 07/09/2018 está marcado como feriado nacional.

**Reprodução confirmada:** reexecução do script 24 com a base CSV e o script do modelo reproduziu exatamente os valores do CSV 24, inclusive as 30 previsões e os totais.

O arquivo de previsão não contém faturamento realizado para o horizonte. Portanto, não calcular nem alegar MAE, RMSE ou WAPE para os 30 dias previstos.

## 8. Dashboard

- Tecnologia: Streamlit, pandas, NumPy, Plotly e scikit-learn.
- Arquivo principal: `dash_vendas_python_streamlit_publicacao/app.py`.
- Lê seis CSVs locais.
- CSV de previsão ativo: `24_previsao_30_dias_corte_20_08.csv`.
- Página Previsão 30 dias conferida visualmente após atualizar o clone local; corte, datas, totais e gráfico aparecem corretamente.
- Instalação e execução foram validadas em clone limpo com Python 3.14.2.
- O dashboard não lê diretamente do BigQuery e não está publicado na nuvem.

Comando Windows, a partir da pasta `dash_vendas_python_streamlit_publicacao`:
```cmd
.venv\Scripts\python.exe -m streamlit run app.py
```

## 9. Regras de continuidade

- Preservar a arquitetura atual.
- Não refatorar nem alterar SQL, tabelas, colunas, funções ou bibliotecas sem pedido explícito.
- Não mudar a granularidade (uma linha por dia) nem a definição do target sem registrar a decisão.
- Verificar cardinalidade e duplicações em JOINs.
- Distinguir observações, hipóteses e causalidade.
- Não afirmar precisão da previsão de 30 dias sem realizado futuro para comparação.
- Usar dados públicos/autorizados; não incluir dados corporativos confidenciais.
- Ao retomar, consultar este arquivo e o README antes de qualquer alteração.

## 10. Encerramento da V1

A V1 de portfólio está concluída em seu escopo atual: pipeline analítico documentado, experimentos reproduzidos, limitações registradas, dashboard local revisado visualmente, dependências e instruções documentadas.

IA Analista, inferência local/WebGPU, implantação e atualização com dados atuais ficam como possíveis projetos/fases futuras, não como pendências obrigatórias para encerrar esta versão.
