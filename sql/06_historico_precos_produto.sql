-- Projeto Dash Vendas
-- Objetivo: analisar a evolução dos preços observados de um produto.
-- Fontes: olist_order_items e olist_orders.
-- Granularidade do resultado: uma linha por registro de item do produto.
-- Relacionamento: order_id.
-- Observação: o histórico de observações não prova preço contínuo nem causa da variação.

SELECT
  oi.product_id,
  oi.order_id,
  oi.price,
  o.order_purchase_timestamp
FROM `projeto-dash-vendas.raw.olist_order_items` AS oi
JOIN `projeto-dash-vendas.raw.olist_orders` AS o
  ON oi.order_id = o.order_id
WHERE oi.product_id = 'bb50f2e236e5eea0100680137654686c'
ORDER BY o.order_purchase_timestamp;
