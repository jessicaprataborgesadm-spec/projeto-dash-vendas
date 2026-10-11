-- Objetivo: validar o volume da tabela e a quantidade de pedidos distintos.
-- Granularidade: uma linha por item do pedido.
-- Validação: comparar o total de linhas com os pedidos únicos.

SELECT
  COUNT(*) AS total_linhas,
  COUNT(DISTINCT order_id) AS pedidos_unicos
FROM `projeto-dash-vendas.raw.olist_order_items`;
