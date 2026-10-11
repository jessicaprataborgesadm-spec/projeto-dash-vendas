-- Projeto Dash Vendas
-- Objetivo: investigar como os valores registrados nos itens se distribuem por status do pedido.
-- Fontes: olist_orders e olist_order_items.
-- Granularidade de origem:
--   olist_orders: uma linha por pedido.
--   olist_order_items: uma linha por item do pedido.
-- Granularidade intermediaria: uma linha por pedido, agregando seus itens antes do JOIN.
-- Granularidade final: uma linha por status do pedido.
-- Importante: soma de price representa o valor dos itens; nao define, por si so, a metrica oficial de faturamento.
-- A soma de freight_value e exibida separadamente para apoiar a decisao sobre incluir ou nao frete.
-- Nenhum status e filtrado nesta etapa: a consulta serve para diagnostico, nao para definir a regra final.

WITH itens_por_pedido AS (
  SELECT
    order_id,
    COUNT(*) AS qtd_linhas_itens,
    SUM(price) AS soma_price_itens,
    SUM(freight_value) AS soma_frete_itens
  FROM `projeto-dash-vendas.raw.olist_order_items`
  GROUP BY order_id
)

SELECT
  o.order_status,
  COUNT(*) AS qtd_pedidos,
  COUNTIF(i.order_id IS NOT NULL) AS pedidos_com_itens,
  COUNTIF(i.order_id IS NULL) AS pedidos_sem_itens,
  SUM(i.qtd_linhas_itens) AS total_linhas_itens,
  SUM(i.soma_price_itens) AS soma_price_itens,
  SUM(i.soma_frete_itens) AS soma_frete_itens
FROM `projeto-dash-vendas.raw.olist_orders` AS o
LEFT JOIN itens_por_pedido AS i
  ON o.order_id = i.order_id
GROUP BY o.order_status
ORDER BY qtd_pedidos DESC;
