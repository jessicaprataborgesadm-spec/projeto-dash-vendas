-- Projeto Dash Vendas
-- Objetivo: comparar o último preço observado antes com o primeiro depois.
-- Fontes: olist_order_items e olist_orders.
-- Granularidade final: uma linha agregada com indicadores por conjunto comparável.
-- Janelas:
--   Antes: 21/02/2018 a 19/03/2018.
--   Depois: 21/03/2018 a 17/04/2018.
-- O dia 20/03/2018 é excluído.
-- Limitações: seleciona observações pontuais; não prova vigência contínua ou causa.

WITH vendas AS (
  SELECT
    oi.product_id,
    oi.price,
    o.order_purchase_timestamp
  FROM `projeto-dash-vendas.raw.olist_order_items` AS oi
  JOIN `projeto-dash-vendas.raw.olist_orders` AS o
    ON oi.order_id = o.order_id
  WHERE DATE(o.order_purchase_timestamp)
    BETWEEN '2018-02-21' AND '2018-04-17'
),

antes AS (
  SELECT
    product_id,
    ARRAY_AGG(
      STRUCT(price, order_purchase_timestamp)
      ORDER BY order_purchase_timestamp DESC
      LIMIT 1
    )[OFFSET(0)] AS ultimo_antes
  FROM vendas
  WHERE DATE(order_purchase_timestamp)
    BETWEEN '2018-02-21' AND '2018-03-19'
  GROUP BY product_id
),

depois AS (
  SELECT
    product_id,
    ARRAY_AGG(
      STRUCT(price, order_purchase_timestamp)
      ORDER BY order_purchase_timestamp
      LIMIT 1
    )[OFFSET(0)] AS primeiro_depois
  FROM vendas
  WHERE DATE(order_purchase_timestamp)
    BETWEEN '2018-03-21' AND '2018-04-17'
  GROUP BY product_id
)

SELECT
  COUNT(*) AS produtos_comparaveis,
  COUNTIF(
    a.ultimo_antes.price != d.primeiro_depois.price
  ) AS produtos_com_preco_diferente,
  COUNTIF(
    a.ultimo_antes.price < d.primeiro_depois.price
  ) AS produtos_com_aumento,
  COUNTIF(
    a.ultimo_antes.price > d.primeiro_depois.price
  ) AS produtos_com_reducao
FROM antes AS a
JOIN depois AS d
  ON a.product_id = d.product_id;
