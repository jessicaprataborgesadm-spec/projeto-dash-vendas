-- Projeto Dash Vendas
-- Etapa: auditoria da tabela de pedidos antes de definir o faturamento diário.
-- Fonte: `projeto-dash-vendas.raw.olist_orders`
-- Granularidade esperada: uma linha por pedido (validar, não assumir).
-- Importante: não filtra status de pedido nesta etapa.
-- A distribuição dos status será usada para apoiar a decisão posterior sobre
-- quais pedidos entram na métrica de faturamento. Essa decisão ainda não está tomada.

-- 1. Validar volume, unicidade da chave e cobertura temporal geral.
SELECT
  COUNT(*) AS total_linhas,
  COUNT(DISTINCT order_id) AS pedidos_unicos,
  COUNTIF(order_id IS NULL) AS order_id_nulo,
  COUNTIF(order_purchase_timestamp IS NULL) AS timestamp_compra_nulo,
  MIN(order_purchase_timestamp) AS primeira_compra_timestamp,
  MAX(order_purchase_timestamp) AS ultima_compra_timestamp
FROM `projeto-dash-vendas.raw.olist_orders`;

-- 2. Inspecionar a distribuição de pedidos por status, sem excluir categorias.
SELECT
  order_status,
  COUNT(*) AS qtd_pedidos
FROM `projeto-dash-vendas.raw.olist_orders`
GROUP BY order_status
ORDER BY qtd_pedidos DESC;

-- 3. Inspecionar a cobertura e o volume de pedidos por mês.
-- Atenção: o primeiro e o último mês do período podem estar incompletos.
SELECT
  DATE_TRUNC(DATE(order_purchase_timestamp), MONTH) AS mes,
  COUNT(*) AS total_linhas,
  COUNT(DISTINCT order_id) AS pedidos_unicos
FROM `projeto-dash-vendas.raw.olist_orders`
WHERE order_purchase_timestamp IS NOT NULL
GROUP BY mes
ORDER BY mes;
