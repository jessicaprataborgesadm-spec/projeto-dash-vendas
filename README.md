# Projeto Dash Vendas

Projeto de portfólio em análise de dados com foco em SQL, BigQuery, Python e Machine Learning, utilizando dados públicos de e-commerce brasileiro.

O objetivo é desenvolver um pipeline analítico para investigar o comportamento das vendas e construir uma base que permita analisar e prever o faturamento diário.

## Problema de negócio

Como transformar dados transacionais de e-commerce em informações confiáveis para acompanhar o desempenho das vendas e apoiar o planejamento por meio de previsões de faturamento?

## Fonte de dados

**Brazilian E-Commerce Public Dataset by Olist**

- Fonte: [Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)
- Dados públicos de pedidos e itens de pedidos de um marketplace brasileiro.
- Período observado nas tabelas já auditadas: setembro de 2016 a outubro de 2018.

## Tecnologias

- **BigQuery:** armazenamento e consultas analíticas.
- **SQL:** exploração, validação e transformação dos dados.
- **Python:** análise de dados e desenvolvimento do modelo preditivo.
- **Machine Learning:** previsão de faturamento diário.
- **Streamlit:** dashboard interativo planejado.
- **GitHub:** versionamento e documentação do projeto.

## Arquitetura planejada

Fonte de dados → BigQuery (RAW) → SQL/ELT → Base analítica diária → Python e avaliação do modelo → Previsões → Dashboard.

A arquitetura será implementada e validada progressivamente.

## Etapas do projeto

- [x] Carregar as tabelas iniciais de pedidos e itens no BigQuery.
- [x] Auditar aspectos iniciais da qualidade e da granularidade dessas tabelas.
- [x] Realizar uma investigação exploratória complementar sobre variações de preços.
- [ ] Organizar e documentar as consultas SQL de validação.
- [ ] Definir e validar a métrica de faturamento diário.
- [ ] Construir e validar a base analítica diária.
- [ ] Criar features temporais e um modelo baseline.
- [ ] Avaliar a previsão para os próximos 30 dias.
- [ ] Desenvolver o dashboard interativo.
- [ ] Documentar os resultados, as limitações e as recomendações.

## Princípios analíticos

- Validar a granularidade antes de agregar ou relacionar tabelas.
- Investigar duplicidades, valores ausentes e inconsistências.
- Verificar possíveis multiplicações de registros após JOINs.
- Diferenciar fatos observados, hipóteses e conclusões.
- Evitar vazamento de dados na construção de modelos preditivos.
- Documentar as decisões e limitações das análises.

## Status atual

O projeto está na etapa de exploração e validação das tabelas de origem. A investigação de preços foi documentada como estudo complementar.

A próxima prioridade é definir a métrica de faturamento e construir uma base diária validada antes de avançar para o modelo preditivo e o dashboard.

## Estrutura do repositório


projeto-dash-vendas/
├── docs/
│   └── analise-variacao-precos.md
├── .gitignore
└── README.md
```

A estrutura será ampliada conforme novas etapas forem concluídas.

## Limitações

Os resultados dependerão da qualidade, da cobertura temporal e das características do dataset público. As métricas de faturamento, os filtros de pedidos e as regras de agregação ainda precisam ser definidos e validados antes da construção da base diária.
