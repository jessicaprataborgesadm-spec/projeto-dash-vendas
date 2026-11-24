# Projeto Dash Vendas

Projeto de portfólio em **Análise de Dados, Engenharia Analítica e Machine Learning**, desenvolvido com dados públicos do e-commerce brasileiro da Olist.

O objetivo é transformar dados transacionais em uma base analítica diária, investigar padrões de vendas e avaliar abordagens para previsão de faturamento, documentando decisões, limitações e resultados.

> **Status desta versão:** fundação analítica/preditiva e dashboard local concluídos. A IA Analista determinística (roteamento por regras, cálculos em Python e interface conversacional) foi validada nas sete intenções do MVP e em uma pergunta fora do escopo. A integração com Gemini foi implementada, mas duas tentativas reais retornaram `503 UNAVAILABLE`, com mensagem do provedor sobre alta demanda. Não foi obtida resposta generativa e, por decisão do projeto, não haverá novas tentativas nem configuração de faturamento. A execução dos seis testes simulados do LLM, a suíte completa e alguns casos de borda ainda precisam ser revisados. O dashboard é local, não está hospedado e não consulta o BigQuery em tempo real.

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
IA Analista
  |-- roteador determinístico
  |-- motor analítico Python
  |-- interface conversacional local
  |-- Gemini Developer API (camada opcional implementada no código)
         `-- chamada real não validada: duas respostas 503 UNAVAILABLE por alta demanda
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

Após observar uma queda acentuada no valor associado a pedidos atualmente `delivered` no fim de agosto de 2018, foi adotado **20/08/2018 como corte provisório** para a simulação retrospectiva exibida no dashboard.

- treinamento até: 20/08/2018;
- horizonte: 21/08/2018 a 19/09/2018;
- previsão total Random Forest: R$ 993.231,78;
- previsão total baseline: R$ 1.024.124,10.

Esses valores são previsões simuladas. Não há faturamento realizado maduro no arquivo de saída para calcular MAE, RMSE ou WAPE desse horizonte. O corte de 20/08/2018 é provisório e deve ser interpretado como uma decisão de controle de qualidade da série, não como uma regra definitiva já comprovada.

A base CSV usada pelos experimentos mantém observações até 29/08/2018 porque também sustenta os backtests e a investigação da janela recente. No script de previsão 30 dias ativo no dashboard, somente as linhas até 20/08/2018 entram no treinamento. Para as datas previstas de 21 a 29/08, o script utiliza apenas features conhecidas (referência do ano anterior e calendário), sem usar o `faturamento_diario` real desses dias nem atualizar a média móvel com valores reais futuros.

### Sensibilidade do corte temporal

Foi comparada a média dos sete dias encerrados em cada data de corte com a média dos 28 dias anteriores. A variação do valor diário médio foi de +5,61% em 15/08, -0,74% em 18/08, -4,77% em 20/08, -23,26% em 22/08, -38,59% em 24/08, -50,89% em 26/08 e -77,32% em 29/08. O resultado indica uma deterioração acentuada entre 20/08 e 22/08. **20/08/2018 foi recomendado como candidato mais prudente para o experimento separado de corte.** O script `24_previsao_30_dias_corte_20_08.py` foi executado; o CSV gerado passou pela validação estrutural de 30 datas consecutivas, sem duplicidades, dias faltantes, previsões nulas ou valores negativos. O dashboard passou a utilizar esse novo arquivo. A simulação anterior com corte em 22/08 permanece preservada pelo script 23 e seu CSV. A comparação é um diagnóstico descritivo, não uma detecção estatística definitiva de mudança de regime.

## Análises documentadas

- [Análise de variação de preços](docs/analise-variacao-precos.md): investigação exploratória do histórico de preços de um produto.
- [Análise do pico da Black Friday de 2017](docs/analise_pico_black_friday_2017.md): investigação do pico de 24/11/2017. O registro foi mantido na série; os dados são compatíveis com aumento de volume associado à Black Friday, sem afirmação causal definitiva.

## Dashboard

Foi desenvolvido localmente um dashboard em **Streamlit**, com navegação lateral e seis áreas: Visão geral, Histórico, Modelos, Validação temporal, Previsão de 30 dias e IA Analista. A página IA Analista usa roteamento por regras e cálculos determinísticos em Python. A camada opcional de interpretação com Gemini foi implementada, mas duas chamadas reais de teste retornaram `503 UNAVAILABLE` por alta demanda reportada pelo provedor; portanto, a interpretação generativa não foi validada e não é apresentada como funcional nesta versão.

As telas foram revisadas visualmente e os principais indicadores foram comparados com os resultados dos experimentos. O código e os CSVs usados pelo dashboard estão publicados em `dash_vendas_python_streamlit_publicacao/`. As instruções de instalação e execução estão em [README_PYTHON.md](dash_vendas_python_streamlit_publicacao/README_PYTHON.md). A instalação das dependências e a execução do dashboard foram validadas a partir de um clone limpo do repositório, usando Python 3.14.2.

## Estrutura atualmente publicada

```text
projeto-dash-vendas/
├── dash_vendas_python_streamlit_publicacao/
│   ├── app.py
│   ├── requirements.txt
│   ├── README_PYTHON.md
│   ├── 19_avaliacao_baseline.py ... 24_previsao_30_dias_corte_20_08.py
│   └── sete arquivos CSV de resultados, incluindo a simulação anterior e a nova previsão ativa
├── docs/
│   ├── analise-variacao-precos.md
│   └── analise_pico_black_friday_2017.md
├── sql/
│   ├── 01_auditoria_order_items.sql
│   ├── ...
│   └── 18_feature_faturamento_ano_anterior.sql
├── PROJECT_MEMORY.md
├── .gitignore
└── README.md
```

O repositório contém as consultas SQL 01 a 18, os documentos listados acima e a camada Python/Streamlit com seus sete CSVs agregados. Os arquivos Python estão agrupados em `dash_vendas_python_streamlit_publicacao/` para preservar a estrutura efetivamente publicada.

## Limitações conhecidas

- O dataset é histórico e termina em 2018; a simulação não é uma previsão do mercado atual.
- A métrica baseada no status atual `delivered` não equivale a faturamento contábil reconciliado.
- A cobertura temporal é irregular em partes do dataset, especialmente no fim da série.
- O corte em 20/08/2018 é provisório.
- A validação temporal contém poucas janelas e o Random Forest não venceu todas.
- A análise da Black Friday foi feita sobre a base diária agregada; não foi concluída a decomposição dos pedidos individuais diretamente nas tabelas RAW.
- A IA Analista determinística usa roteamento por regras e cálculos em Python. A interface conversacional foi validada nas sete intenções do MVP e em uma pergunta fora do escopo.
- A integração opcional com Gemini Developer API (`gemini-3.8-flash`) está implementada no código, mas duas tentativas reais retornaram `503 UNAVAILABLE` com mensagem de alta demanda do provedor. Nenhuma resposta generativa foi obtida; por decisão do projeto, não haverá novas tentativas nem ativação de billing nesta versão.
- Permanecem pendentes a execução dos seis testes simulados do LLM, a suíte completa de testes, alguns casos de borda da interface e o ajuste textual do diagnóstico para distinguir o acumulado das quedas diárias.

## Roadmap do Projeto Dash Vendas

### Fundação analítica e preditiva

- [x] Carregar e auditar as tabelas iniciais de pedidos e itens no BigQuery.
- [x] Construir a base diária e as features temporais.
- [x] Executar e avaliar um baseline.
- [x] Treinar e avaliar o primeiro Random Forest.
- [x] Realizar validação temporal em cinco janelas.
- [x] Gerar e validar a previsão simulada de 30 dias.
- [x] Construir e revisar visualmente o dashboard Streamlit local.
- [x] Documentar dependências, instruções de execução e limitações.
- [x] Validar instalação e execução a partir de um clone limpo.

### Próxima etapa principal: IA Analista

- [x] Definir catálogo de sete intenções, perguntas de exemplo, fontes, parâmetros e limites de resposta ([documento](docs/catalogo_intencoes_ia_analista.md)).
- [x] Criar camada determinística em Python para as sete intenções, calculando métricas fora do LLM (`ia_analista/analytics.py`).
- [x] Padronizar resultados estruturados com status, intenção, métrica, período, fatos, cobertura e limitações.
- [x] Criar 35 testes automatizados para motor, roteador, sintaxe do app e camada Gemini.
- [x] Executar localmente 29 testes do motor, roteador e sintaxe do `app.py`.
- [ ] Executar os seis novos testes simulados do LLM (`tests/test_llm.py`), sem consumir tokens.
- [x] Criar roteador determinístico por regras explícitas e validação de parâmetros (`ia_analista/router.py`).
- [x] Escolher Gemini Developer API e modelo `gemini-3.8-flash` para a primeira integração.
- [x] Implementar a chamada opcional ao Gemini somente com a pergunta atual e o envelope determinístico, sem CSVs, histórico completo, ferramentas ou SQL.
- [x] Configurar a chave local no nível gratuito, sem billing, e realizar duas tentativas reais de chamada ao Gemini. Ambas retornaram `503 UNAVAILABLE` por alta demanda reportada pelo provedor; nenhuma resposta generativa foi obtida. Por decisão da usuária, não serão feitas novas tentativas nem ativado billing.
- [x] Integrar a interface conversacional ao Streamlit (página `IA Analista`).
- [x] Validar localmente as sete intenções do MVP e uma pergunta geográfica fora do escopo.
- [ ] Validar manualmente casos de borda: pergunta ambígua/inválida, CSV ausente, cobertura parcial e limpeza da conversa.
- [ ] Melhorar o texto do diagnóstico para destacar quando o acumulado é positivo apesar de quedas diárias.
- [x] Registrar que a interpretação generativa não foi validada: as duas chamadas reais retornaram `503 UNAVAILABLE`; a camada Gemini permanece opcional e não operacionalmente confirmada nesta versão.
- [x] Documentar catálogo, motor determinístico, roteador, Gemini, segurança e configuração.

### Evoluções opcionais após o MVP

- [ ] Adicionar análises por estado/região após carregar e auditar as dimensões necessárias (a base diária atual não contém localização).
- [ ] Conectar o dashboard a dados atualizados do BigQuery.
- [ ] Hospedar/publicar o dashboard.
- [ ] Avaliar inferência local/WebGPU.

**Escopo entregue nesta versão:** dashboard local com IA Analista determinística, roteamento por regras, cálculos reproduzíveis e apresentação dos fatos estruturados. A integração Gemini está presente no código, mas não foi validada por indisponibilidade reportada pelo provedor e não faz parte das capacidades confirmadas desta entrega.

## Memória de continuidade

As decisões do projeto estão em [PROJECT_MEMORY.md](PROJECT_MEMORY.md). O catálogo de intenções da IA Analista está em [docs/catalogo_intencoes_ia_analista.md](docs/catalogo_intencoes_ia_analista.md). Consulte ambos antes de retomar ou alterar a implementação.

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


### Integração Gemini

A primeira integração usa a **Gemini Developer API** com o modelo `gemini-3.8-flash`, pelo SDK oficial `google-genai`. O LLM atua apenas como camada de interpretação: o Python continua responsável pelos cálculos e validações.

O módulo `ia_analista/llm.py` envia somente a pergunta atual e os campos estruturados do resultado determinístico (`status`, `intent`, `metric`, `period`, `facts`, `coverage` e `limitations`). Não envia CSVs, DataFrames, histórico completo da conversa, nem permite ferramentas ou execução de SQL. O retorno é estruturado em JSON. A narrativa do LLM não pode conter algarismos; os números continuam sendo exibidos diretamente pelos componentes calculados no Python.

Configure a chave somente no ambiente local. A partir de `dash_vendas_python_streamlit_publicacao`, crie `.streamlit/secrets.toml` com:

```toml
GEMINI_API_KEY = "SUA_CHAVE"
GEMINI_MODEL = "gemini-3.8-flash"
```

O arquivo `.streamlit/secrets.toml` já está coberto pelo `.gitignore`. **Nunca envie a chave pelo chat nem a publique no GitHub.**

O projeto adotará exclusivamente o nível gratuito da Gemini Developer API. A tabela oficial lista entrada e saída de tokens sem custo para `gemini-3.8-flash` nesse nível, sujeito a limites de uso e disponibilidade da conta. **Não configure faturamento, não vincule cartão e não faça upgrade.** O Google informa que pode usar o conteúdo do nível gratuito para melhorar seus produtos. Por isso, a integração está limitada à pergunta atual e a fatos agregados derivados da base pública Olist. Não envie dados pessoais, confidenciais, chaves ou credenciais. Se o Google exigir configuração de billing ou indicar qualquer cobrança, interrompa e mantenha o modo determinístico.

Preços publicados para `gemini-3.8-flash` no nível Standard: US$ 0,75 por milhão de tokens de entrada e US$ 3,75 por milhão de tokens de saída até 31/12/2026; a página oficial informa US$ 1,50 e US$ 7,50 a partir de 01/01/2027. Preços podem mudar; consulte a [tabela oficial de preços](https://ai.google.dev/gemini-api/docs/pricing).

Links oficiais: [Google AI Studio / chaves de API](https://aistudio.google.com/api-keys) · [SDK Google Gen AI para Python](https://googleapis.github.io/python-genai/) · [preços da Gemini API](https://ai.google.dev/gemini-api/docs/pricing).

A chave foi configurada localmente e protegida pelo `.gitignore`. Em 24/11/2026, foram feitas duas tentativas manuais de chamada real ao modelo `gemini-3.8-flash`; ambas retornaram `503 UNAVAILABLE` com a mensagem do provedor de que o modelo estava enfrentando alta demanda. O painel do AI Studio mostrou o projeto no nível gratuito e uso abaixo dos limites exibidos naquele momento. Não foi obtida resposta do modelo, portanto a integração remota não está validada. Por decisão da usuária, não haverá novas tentativas, ativação de billing, associação de cartão ou upgrade nesta versão. Quando o Gemini está indisponível, a interface continua exibindo os fatos e indicadores calculados deterministicamente pelo Python.
