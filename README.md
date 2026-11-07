# Projeto Dash Vendas

Projeto de portfólio em **Análise de Dados, Engenharia Analítica e Machine Learning**, desenvolvido com dados públicos do e-commerce brasileiro da Olist.

O objetivo é transformar dados transacionais em uma base analítica diária, investigar padrões de vendas e avaliar abordagens para previsão de faturamento, documentando decisões, limitações e resultados.

> **Status:** pipeline analítico e experimentos preditivos desenvolvidos; scripts Python, dashboard Streamlit, dependências e seis CSVs agregados publicados no repositório, dentro de `dash_vendas_python_streamlit_publicacao/`. O dashboard ainda não está hospedado nem conectado diretamente ao BigQuery.

## Problema de negócio

Como transformar dados transacionais de e-commerce em informações confiáveis para acompanhar o comportamento das vendas e apoiar o planejamento por meio de previsões de faturamento diário?

## Fonte de dados

**Brazilian E-Commerce Public Dataset by Olist**

- Fonte: [Kaggle — Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)
- Dados públicos de pedidos, itens de pedidos e outras dimensões de um marketplace brasileiro.
- As tabelas de pedidos e itens foram carregadas no BigQuery no projeto `projeto-dash-vendas`, dataset `raw`, região `southamerica-east1`.
- A cobertura observada nas fontes de pedidos auditadas vai de setembro de 2016 a outubro de 2018. A cobertura não é uniforme em todo o período.

## Definição da métrica

A primeira versão da série utiliza uma **métrica operacional de valor dos itens**:

- considera pedidos cujo status atual na fonte é `delivered`;
- soma `olist_order_items.price`;
- agrupa pela data de compra: `DATE(order_purchase_timestamp)`;
- exclui `freight_value`;
- granularidade final: **uma linha por dia corrido**.

Essa definição foi adotada para o experimento preditivo e **não representa faturamento contábil ou receita líquida reconciliada**. O status atual do pedido pode refletir eventos posteriores à compra, por isso essa limitação precisa acompanhar a interpretação dos resultados.

## Arquitetura e fluxo implementado

```text
Dataset público Olist (Kaggle)
          |
          v
BigQuery — camada RAW
  |-- olist_orders
  |-- olist_order_items
          |
          v
SQL / ELT
  |-- auditorias de qualidade e cobertura
  |-- base diária de valor dos itens
  |-- features temporais e de calendário
          |
          v
Exportação da base analítica
          |
          v
Python
  |-- baseline
  |-- Random Forest
  |-- validação temporal
  |-- previsão recursiva de 30 dias
          |
          v
Arquivos de resultados (CSV)
          |
          v
Dashboard Streamlit local
          |
          v
IA Analista (planejada; não implementada)
```

O fluxo Python e o dashboard utilizam arquivos CSV exportados. Os scripts, a aplicação e os seis CSVs necessários ao dashboard estão versionados em `dash_vendas_python_streamlit_publicacao/`. A aplicação não está hospedada e não consulta o BigQuery em tempo real.

## Engenharia analítica: SQL e features

As consultas SQL versionadas neste repositório cobrem auditorias iniciais das tabelas RAW, análise de status e cobertura, construção da série diária e criação/validação das features.

Features utilizadas nos experimentos:

- `dia_semana`: dia da semana da data prevista;
- `media_7d`: média dos sete dias anteriores, sem incluir o próprio dia;
- `faturamento_ano_anterior`: valor observado na mesma data do ano anterior, quando há cobertura disponível;
- flags e rótulos de calendário, incluindo feriados e datas comerciais relevantes.

Na previsão recursiva de vários dias, a `media_7d` é atualizada com previsões anteriores, nunca com faturamento real futuro.

## Experimentos preditivos

### Baseline

Foi construído um baseline simples usando a média dos sete dias anteriores como previsão constante durante o horizonte de teste. Ele funciona como referência para avaliar se um modelo mais elaborado agrega valor.

No teste histórico de 01/07/2018 a 30/07/2018:

| Métrica | Baseline |
|---|---:|
| MAE | R$ 6.873,94 |
| RMSE | R$ 8.368,83 |
| WAPE | 25,05% |

### Random Forest

O primeiro modelo de Machine Learning foi um Random Forest, treinado com features temporais e de calendário.

No mesmo teste histórico de 01/07/2018 a 30/07/2018:

| Métrica | Random Forest |
|---|---:|
| MAE | R$ 6.390,11 |
| RMSE | R$ 7.734,12 |
| WAPE | 23,29% |

Nesse teste específico, o Random Forest apresentou WAPE 1,76 ponto percentual menor que o baseline.

### Validação temporal

Foram avaliadas cinco janelas históricas de 30 dias, sem incluir o teste original de julho:

| Resultado agregado das cinco janelas | Baseline | Random Forest |
|---|---:|---:|
| MAE | R$ 7.757,00 | R$ 6.966,16 |
| RMSE | R$ 9.539,33 | R$ 8.617,60 |
| WAPE | 25,27% | 22,70% |

O Random Forest teve WAPE menor em **três das cinco janelas**, mas não venceu em todas. O resultado agregado é promissor, porém não deve ser interpretado como garantia de desempenho futuro.

Uma janela recente de 31/07/2018 a 29/08/2018 apresentou WAPE de 36,39% para o Random Forest e 38,67% para o baseline. Esse período foi sinalizado como potencialmente afetado por maturidade/cobertura incompleta dos pedidos e não deve ser usado isoladamente para declarar o modelo vencedor.

## Previsão simulada de 30 dias

Após observar uma queda acentuada no valor associado a pedidos atualmente `delivered` no fim de agosto de 2018, foi adotado **22/08/2018 como corte provisório** para uma simulação retrospectiva.

- treinamento até: 22/08/2018;
- horizonte: 23/08/2018 a 21/09/2018;
- previsão total Random Forest: R$ 907.929,42;
- previsão total baseline: R$ 840.885,00.

Esses valores são previsões simuladas. Não há faturamento realizado maduro no arquivo de saída para calcular MAE, RMSE ou WAPE desse horizonte. O corte de 22/08/2018 é provisório e deve ser interpretado como uma decisão de controle de qualidade da série, não como uma regra definitiva já comprovada.

A base CSV usada pelos experimentos mantém observações até 29/08/2018 porque também sustenta os backtests e a investigação da janela recente. No script de previsão 30 dias, somente as linhas até 22/08/2018 entram no treinamento. Para as datas previstas de 23 a 29/08, o script utiliza apenas features conhecidas (referência do ano anterior e calendário), sem usar o `faturamento_diario` real desses dias nem atualizar a média móvel com valores reais futuros.

### Sensibilidade do corte temporal

Foi comparada a média dos sete dias encerrados em cada data de corte com a média dos 28 dias anteriores. A variação do valor diário médio foi de +5,61% em 15/08, -0,74% em 18/08, -4,77% em 20/08, -23,26% em 22/08, -38,59% em 24/08, -50,89% em 26/08 e -77,32% em 29/08. O resultado indica uma deterioração acentuada entre 20/08 e 22/08. **20/08/2018 passa a ser recomendado como candidato mais prudente para o próximo experimento de corte**, mas ainda não foi aplicado ao script publicado: os totais e o CSV desta seção continuam sendo da simulação com corte em 22/08/2018. A comparação é um diagnóstico descritivo, não uma detecção estatística definitiva de mudança de regime.

## Análises documentadas

- [Análise de variação de preços](docs/analise-variacao-precos.md): investigação exploratória do histórico de preços de um produto.
- [Análise do pico da Black Friday de 2017](docs/analise_pico_black_friday_2017.md): investigação do pico de 24/11/2017. O registro foi mantido na série; os dados são compatíveis com aumento de volume associado à Black Friday, sem afirmação causal definitiva.

## Dashboard

Foi desenvolvido localmente um dashboard em **Streamlit**, com navegação lateral e cinco áreas:

1. Visão geral;
2. Histórico;
3. Modelos;
4. Validação temporal;
5. Previsão de 30 dias.

As telas foram revisadas visualmente e os principais indicadores foram comparados com os resultados dos experimentos. O código e os CSVs usados pelo dashboard estão publicados em `dash_vendas_python_streamlit_publicacao/`. As instruções de instalação e execução estão em [README_PYTHON.md](dash_vendas_python_streamlit_publicacao/README_PYTHON.md). A instalação das dependências e a execução do dashboard foram validadas a partir de um clone limpo do repositório, usando Python 3.14.2.

## Estrutura atualmente publicada

```text
projeto-dash-vendas/
├── dash_vendas_python_streamlit_publicacao/
│   ├── app.py
│   ├── requirements.txt
│   ├── README_PYTHON.md
│   ├── 19_avaliacao_baseline.py ... 23_previsao_30_dias_corte_22_08.py
│   └── seis arquivos CSV usados nos experimentos e no dashboard
├── docs/
│   ├── analise-variacao-precos.md
│   └── analise_pico_black_friday_2017.md
├── sql/
│   ├── 01_auditoria_order_items.sql
│   ├── ...
│   └── 18_feature_faturamento_ano_anterior.sql
├── .gitignore
└── README.md
```

O repositório contém as consultas SQL 01 a 18, os documentos listados acima e a camada Python/Streamlit com seus seis CSVs agregados. Os arquivos Python estão agrupados em `dash_vendas_python_streamlit_publicacao/` para preservar a estrutura efetivamente publicada.

## Limitações conhecidas

- O dataset é histórico e termina em 2018; a simulação não é uma previsão do mercado atual.
- A métrica baseada no status atual `delivered` não equivale a faturamento contábil reconciliado.
- A cobertura temporal é irregular em partes do dataset, especialmente no fim da série.
- O corte em 22/08/2018 é provisório.
- A validação temporal contém poucas janelas e o Random Forest não venceu todas.
- A análise da Black Friday foi feita sobre a base diária agregada; não foi concluída a decomposição dos pedidos individuais diretamente nas tabelas RAW.
- A IA Analista com Gemini/Vertex AI é uma possibilidade planejada e ainda não foi implementada.

## Próximas etapas

- [x] Carregar e auditar as tabelas iniciais de pedidos e itens no BigQuery.
- [x] Construir a base diária e as features temporais.
- [x] Executar e avaliar um baseline.
- [x] Treinar e avaliar o primeiro Random Forest.
- [x] Realizar validação temporal em cinco janelas.
- [x] Gerar uma previsão retrospectiva simulada de 30 dias.
- [x] Construir e revisar visualmente o dashboard Streamlit local.
- [ ] Concluir revisão de qualidade e estabilidade do modelo e do corte temporal.
- [x] Revisar e versionar os scripts Python, a aplicação Streamlit e os seis CSVs agregados.
- [x] Documentar as dependências e as instruções de execução em `dash_vendas_python_streamlit_publicacao/README_PYTHON.md`.
- [x] Validar a instalação e a execução a partir de um clone limpo do repositório.
- [ ] Implementar a IA Analista depois da validação da camada analítica.

## Princípios analíticos

- Validar a granularidade antes de agregar ou relacionar tabelas.
- Verificar cardinalidade e possíveis duplicações após JOINs.
- Investigar NULLs, duplicidades, valores negativos, extremos e cobertura temporal.
- Diferenciar fato observado, hipótese, inferência e causalidade.
- Evitar vazamento de dados na preparação das features e na avaliação temporal.
- Comparar modelos com o mesmo horizonte e o mesmo conjunto de teste.
- Não excluir pontos extremos sem evidência.
- Documentar decisões, limitações e critérios de validação.

---

**Projeto de portfólio com dados públicos.** Resultados e conclusões se limitam às definições, recortes e validações descritos neste documento.
