-- Projeto Dash Vendas
-- Objetivo: preparar a série diária elegível para o primeiro baseline preditivo.
-- Fontes: projeto-dash-vendas.raw.olist_orders e raw.olist_order_items.
-- Granularidade final: uma linha por dia corrido.
-- Métrica operacional: SUM(price) dos itens de pedidos cujo status atual é 'delivered'.
-- Frete: excluído; freight_value não compõe faturamento_diario.
-- Data de referência: DATE(order_purchase_timestamp), ou seja, data da compra.
-- Corte final provisório para treinamento: 2018-08-29, última data de compra
-- encontrada para pedidos atualmente marcados como 'delivered' na auditoria temporal.
-- A série completa continua disponível na consulta 10; este arquivo aplica o corte
-- apenas à série destinada ao treinamento. Não cria tabela física.
-- Limitação: status atual 'delivered' não equivale a uma medida contábil reconciliada.

WITH parametros AS (
  SELECT DATE '2018-08-29' AS data_final_treinamento
),

calendario AS (
  SELECT data
  FROM parametros,
  UNNEST(
    GENERATE_DATE_ARRAY(
      (SELECT MIN(DATE(order_purchase_timestamp))
       FROM `projeto-dash-vendas.raw.olist_orders`),
      data_final_treinamento
    )
  ) AS data
),

pedidos_entregues AS (
  SELECT
    order_id,
    DATE(order_purchase_timestamp) AS data_compra
  FROM `projeto-dash-vendas.raw.olist_orders`
  WHERE order_status = 'delivered'
    AND DATE(order_purchase_timestamp) <= DATE '2018-08-29'
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
  COALESCE(f.faturamento_diario, NUMERIC '0') AS faturamento_diario,
  COALESCE(f.qtd_pedidos_entregues, 0) AS qtd_pedidos_entregues,
  COALESCE(f.qtd_linhas_itens_entregues, 0) AS qtd_linhas_itens_entregues
FROM calendario AS c
LEFT JOIN faturamento_por_dia AS f
  ON c.data = f.data
ORDER BY c.data;
