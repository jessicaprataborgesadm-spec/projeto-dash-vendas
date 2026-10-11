-- Projeto Dash Vendas
-- Objetivo: explorar a distribuição dos preços dos itens.
-- Fonte: tabela raw.olist_order_items
-- Granularidade de origem: uma linha por item do pedido.
-- Observação: quartis aproximados; valores extremos não são necessariamente erros.

SELECT
  APPROX_QUANTILES(price, 4) AS quartis
FROM `projeto-dash-vendas.raw.olist_order_items`;
