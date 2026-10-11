-- Objetivo: identificar pedidos sem itens correspondentes.
-- Tabela de origem: olist_orders.
-- Granularidade de origem: uma linha por pedido.
-- Relacionamento: order_id.
-- Validação: identificar pedidos sem correspondência na tabela de itens.
-- Resultado da auditoria anterior: 775 pedidos sem itens.

SELECT
  COUNT(*) AS pedidos_sem_itens
FROM `projeto-dash-vendas.raw.olist_orders` o
LEFT JOIN (
  SELECT DISTINCT order_id
  FROM `projeto-dash-vendas.raw.olist_order_items`
) i
  ON o.order_id = i.order_id
WHERE i.order_id IS NULL;
