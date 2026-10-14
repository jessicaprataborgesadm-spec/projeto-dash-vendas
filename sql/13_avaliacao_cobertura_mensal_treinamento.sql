-- Projeto Dash Vendas
-- Objetivo: avaliar a cobertura mensal da série elegível para treinamento.
-- Fontes: projeto-dash-vendas.raw.olist_orders e raw.olist_order_items.
-- Granularidade final: uma linha por mês dentro do período avaliado.
-- Regra operacional: somente pedidos cujo status atual é 'delivered'.
-- Métrica: soma de price dos itens, excluindo freight_value.
-- Data atribuída: data da compra (order_purchase_timestamp).
-- Período avaliado: 2016-09-04 a 2018-08-29.
-- Importante: meses sem pedidos ou com poucos dias positivos podem indicar baixa
-- atividade ou cobertura incompleta. Esta consulta subsidia a decisão sobre o
-- início do treinamento; não determina o corte automaticamente.

WITH parametros AS (
  SELECT
    DATE '2016-09-04' AS data_inicio,
    DATE '2018-08-29' AS data_fim
),

calendario AS (
  SELECT data
  FROM parametros,
  UNNEST(GENERATE_DATE_ARRAY(data_inicio, data_fim)) AS data
),

pedidos_entregues AS (
  SELECT
    order_id,
    DATE(order_purchase_timestamp) AS data_compra
  FROM `projeto-dash-vendas.raw.olist_orders`
  WHERE order_status = 'delivered'
    AND DATE(order_purchase_timestamp)
      BETWEEN DATE '2016-09-04' AND DATE '2018-08-29'
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
),

serie_diaria AS (
  SELECT
    c.data,
    COALESCE(f.faturamento_diario, NUMERIC '0') AS faturamento_diario,
    COALESCE(f.qtd_pedidos_entregues, 0) AS qtd_pedidos_entregues,
    COALESCE(f.qtd_linhas_itens_entregues, 0) AS qtd_linhas_itens_entregues
  FROM calendario AS c
  LEFT JOIN faturamento_por_dia AS f
    ON c.data = f.data
)

SELECT
  DATE_TRUNC(data, MONTH) AS mes,
  MIN(data) AS primeira_data_incluida,
  MAX(data) AS ultima_data_incluida,
  COUNT(*) AS dias_calendario,
  COUNTIF(faturamento_diario > 0) AS dias_com_faturamento,
  COUNTIF(faturamento_diario = 0) AS dias_com_faturamento_zero,
  ROUND(
    100 * SAFE_DIVIDE(COUNTIF(faturamento_diario > 0), COUNT(*)),
    2
  ) AS percentual_dias_com_faturamento,
  SUM(faturamento_diario) AS faturamento_mensal,
  SUM(qtd_pedidos_entregues) AS qtd_pedidos_entregues,
  SUM(qtd_linhas_itens_entregues) AS qtd_linhas_itens_entregues
FROM serie_diaria
GROUP BY mes
ORDER BY mes;
