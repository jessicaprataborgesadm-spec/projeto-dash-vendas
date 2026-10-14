-- Projeto Dash Vendas
-- Objetivo: construir a série diária inicial para análise e previsão de faturamento.
-- Fontes: projeto-dash-vendas.raw.olist_orders e raw.olist_order_items.
-- Granularidade final: uma linha por dia corrido.
-- Métrica operacional: SUM(price) dos itens de pedidos cujo status atual é 'delivered'.
-- Frete: excluído; freight_value não compõe faturamento_diario.
-- Data de referência: DATE(order_purchase_timestamp), ou seja, data da compra.
-- Importante: o filtro usa o status atual do pedido, mas atribui o valor à data da compra.
-- A métrica é uma proxy analítica do valor dos itens de pedidos entregues, não uma receita contábil reconciliada.
-- Calendário: cobre da primeira à última data observada em olist_orders, incluindo dias sem pedidos entregues.
-- Não cria tabela física nesta etapa; execute e valide o resultado antes de definir o destino final.

WITH calendario AS (
  SELECT data
  FROM UNNEST(
    GENERATE_DATE_ARRAY(
      (SELECT MIN(DATE(order_purchase_timestamp))
       FROM `projeto-dash-vendas.raw.olist_orders`),
      (SELECT MAX(DATE(order_purchase_timestamp))
       FROM `projeto-dash-vendas.raw.olist_orders`)
    )
  ) AS data
),

pedidos_entregues AS (
  SELECT
    order_id,
    DATE(order_purchase_timestamp) AS data_compra
  FROM `projeto-dash-vendas.raw.olist_orders`
  WHERE order_status = 'delivered'
),

faturamento_por_dia AS (
  SELECT
    p.data_compra AS data,
    SUM(CAST(oi.price AS NUMERIC)) AS faturamento_diario,
    COUNT(DISTINCT p.order_id) AS qtd_pedidos_entregues,
    COUNT(*) AS qtd_linhas_itens_entregues
  FROM pedidos_entregues AS p
  INNER JOIN `projeto-dash-vendas.raw.olist_order_items` AS oi
    ON p.order_id = oi.order_id
  GROUP BY p.data_compra
)

SELECT
  c.data,
  COALESCE(f.faturamento_diario, 0) AS faturamento_diario,
  COALESCE(f.qtd_pedidos_entregues, 0) AS qtd_pedidos_entregues,
  COALESCE(f.qtd_linhas_itens_entregues, 0) AS qtd_linhas_itens_entregues
FROM calendario AS c
LEFT JOIN faturamento_por_dia AS f
  ON c.data = f.data
ORDER BY c.data;
