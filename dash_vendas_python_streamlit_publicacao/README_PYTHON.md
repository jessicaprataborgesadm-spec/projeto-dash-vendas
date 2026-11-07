# Camada Python e Dashboard | Projeto Dash Vendas

Esta pasta contém os scripts Python, o dashboard Streamlit, as dependências e os CSVs agregados usados pela aplicação.

## Estrutura

Mantenha os arquivos desta pasta juntos. O dashboard lê seis arquivos CSV locais e não consulta o BigQuery diretamente.

## Executar o dashboard (Windows)

Abra o terminal na raiz do repositório e entre nesta pasta:

```bash
cd dash_vendas_python_streamlit_publicacao
```

Crie e ative um ambiente virtual, instale as dependências e inicie o dashboard:

```bash
py -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

O Streamlit abrirá o endereço local informado no terminal.

## Reproduzir os experimentos

Execute os comandos a partir desta pasta, onde estão os scripts e a base CSV:

```bash
python 19_avaliacao_baseline.py
python 20_modelo_random_forest_teste.py
python 21_validacao_temporal_modelos.py
python 22_validacao_janela_recente.py
python 23_previsao_30_dias_corte_22_08.py
```

A base `base_treinamento_faturamento_teste.csv` é a exportação agregada da SQL 18 e mantém o período de 01/01/2017 a 29/08/2018. Ela é compartilhada pelos experimentos de validação histórica e pela simulação de previsão. Para atualizar os resultados, exporte novamente a saída da consulta e substitua esse arquivo, preservando o nome e as colunas esperadas.

**Importante sobre os cortes:** os testes históricos precisam das observações até 29/08/2018 para avaliar a janela recente. Já o script `23_previsao_30_dias_corte_22_08.py` filtra a base e treina somente com datas até 22/08/2018. Para prever 23 a 29/08, usa apenas as features conhecidas de calendário e faturamento do ano anterior; não usa o `faturamento_diario` real dessas datas nem atualiza `media_7d` com valores realizados futuros.

Os scripts geram os CSVs de resultados utilizados pelo dashboard. A previsão de vários dias atualiza a média móvel com previsões anteriores, sem usar faturamento real futuro.

## Definição e limites dos dados

A série representa o valor dos itens (`olist_order_items.price`) de pedidos cujo status atual na fonte é `delivered`, agrupado pela data de compra. Não inclui frete e não deve ser interpretada como faturamento contábil ou receita líquida reconciliada.

O dataset é histórico (2016–2018). A previsão de 30 dias incluída é uma simulação retrospectiva com corte provisório em 22/08/2018, não uma previsão para o mercado atual. O arquivo de previsão não contém realizado maduro para calcular métricas de erro.
