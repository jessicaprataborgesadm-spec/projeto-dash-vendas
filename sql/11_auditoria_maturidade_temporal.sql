-- Projeto Dash Vendas
-- Objetivo: investigar se a parte final da série temporal tem pedidos ainda sem conclusão.
-- Fonte: projeto-dash-vendas.raw.olist_orders.
-- Granularidade de origem: uma linha por pedido.
-- Contexto: a série preliminar de faturamento por data da compra tem valor zero
-- em todos os dias após 2018-08-29, apesar de a tabela de pedidos conter compras
-- até 2018-10-17. Isso pode refletir pedidos que ainda não estavam entregues
-- no momento representado pela fonte, e não necessariamente ausência de vendas.
-- Estas consultas são diagnósticas; não definem automaticamente o cutoff do modelo.

-- 1. Evolução mensal: pedidos por status e percentual com status delivered.
SELECT
  DATE_TRUNC(DATE(order_purchase_timestamp), MONTH) AS mes_compra,
  COUNT(*) AS total_pedidos,
  COUNTIF(order_status = 'delivered') AS pedidos_delivered,
  COUNTIF(order_status != 'delivered') AS pedidos_outros_status,
  ROUND(
    100 * SAFE_DIVIDE(COUNTIF(order_status = 'delivered'), COUNT(*)),
    2
  ) AS percentual_delivered,
  COUNTIF(
    order_status = 'delivered'
    AND order_delivered_customer_date IS NULL
  ) AS delivered_sem_data_entrega
FROM `projeto-dash-vendas.raw.olist_orders`
GROUP BY mes_compra
ORDER BY mes_compra;

-- 2. Comparar a data mais recente de compra na tabela com as datas mais recentes
-- de compra de pedidos atualmente marcados como delivered.
SELECT
  MAX(DATE(order_purchase_timestamp)) AS ultima_data_compra_geral,
  MAX(IF(
    order_status = 'delivered',
    DATE(order_purchase_timestamp),
    NULL
  )) AS ultima_data_compra_status_delivered,
  MAX(IF(
    order_status = 'delivered',
    DATE(order_delivered_customer_date),
    NULL
  )) AS ultima_data_entrega_cliente,
  COUNTIF(
    order_status = 'delivered'
    AND order_delivered_customer_date IS NULL
  ) AS pedidos_delivered_sem_data_entrega,
  COUNTIF(
    order_status != 'delivered'
    AND order_delivered_customer_date IS NOT NULL
  ) AS outros_status_com_data_entrega
FROM `projeto-dash-vendas.raw.olist_orders`;

-- 3. Distribuição dos dias entre a compra e a entrega para pedidos entregues
-- com data de entrega preenchida. Os percentis ajudam a avaliar uma possível
-- janela de maturação, mas não determinam sozinhos o cutoff final da série.
WITH entregas AS (
  SELECT
    DATE_DIFF(
      DATE(order_delivered_customer_date),
      DATE(order_purchase_timestamp),
      DAY
    ) AS dias_entre_compra_e_entrega
  FROM `projeto-dash-vendas.raw.olist_orders`
  WHERE order_status = 'delivered'
    AND order_delivered_customer_date IS NOT NULL
)
SELECT
  COUNT(*) AS pedidos_com_data_entrega,
  COUNTIF(dias_entre_compra_e_entrega < 0) AS entregas_antes_da_compra,
  MIN(dias_entre_compra_e_entrega) AS menor_intervalo_dias,
  APPROX_QUANTILES(dias_entre_compra_e_entrega, 100)[OFFSET(50)] AS mediana_dias,
  APPROX_QUANTILES(dias_entre_compra_e_entrega, 100)[OFFSET(90)] AS p90_dias,
  APPROX_QUANTILES(dias_entre_compra_e_entrega, 100)[OFFSET(95)] AS p95_dias,
  MAX(dias_entre_compra_e_entrega) AS maior_intervalo_dias
FROM entregas;
