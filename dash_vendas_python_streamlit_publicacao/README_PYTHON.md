# Camada Python e Dashboard | Projeto Dash Vendas

Este pacote contém os scripts Python, o dashboard Streamlit e os CSVs agregados usados pela aplicação.

## Estrutura

Mantenha os arquivos deste pacote na raiz do repositório, junto ao `README.md`, `sql/` e `docs/`.

O dashboard lê seis arquivos CSV locais. Ele não consulta o BigQuery diretamente.

## Ambiente (Windows)

```bash
py -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Reproduzir os experimentos

A base `base_treinamento_faturamento_teste.csv` é a exportação agregada da SQL 18. Para atualizar os resultados, exporte novamente a saída da consulta com esse nome e execute, na raiz do projeto:

```bash
python 19_avaliacao_baseline.py
python 20_modelo_random_forest_teste.py
python 21_validacao_temporal_modelos.py
python 22_validacao_janela_recente.py
python 23_previsao_30_dias_corte_22_08.py
```

Os scripts geram os CSVs de resultados utilizados pelo dashboard. A execução dos scripts 20 a 23 reutiliza as regras do modelo e mantém a média móvel recursiva sem usar faturamento real futuro.

## Definição e limites dos dados

A série representa o valor dos itens (`olist_order_items.price`) de pedidos cujo status atual na fonte é `delivered`, agrupado pela data de compra. Não inclui frete e não deve ser interpretada como faturamento contábil ou receita líquida reconciliada.

O dataset é histórico (2016–2018). A previsão de 30 dias incluída é uma simulação retrospectiva com corte provisório em 22/08/2018, não uma previsão para o mercado atual. O arquivo de previsão não contém realizado maduro para calcular métricas de erro.
