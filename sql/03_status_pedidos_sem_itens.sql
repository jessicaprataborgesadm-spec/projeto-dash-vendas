-- Objetivo: analisar os status dos pedidos que não possuem itens correspondentes.
-- Tabela principal: olist_orders.
-- Granularidade de origem: uma linha por pedido.
-- Relacionamento: order_id com os pedidos distintos de olist_order_items.
-- Filtro: pedidos sem correspondência na tabela de itens.
-- Resultado da auditoria anterior: 775 pedidos sem itens, distribuídos por status.

SELECT
  o.order_status,
  COUNT(*) AS qtd_pedidos
FROM `projeto-dash-vendas.raw.olist_orders` o
LEFT JOIN (
  SELECT DISTINCT order_id
  FROM `projeto-dash-vendas.raw.olist_order_items`
) i
  ON o.order_id = i.order_id
WHERE i.order_id IS NULL
GROUP BY o.order_status
ORDER BY qtd_pedidos DESC;
