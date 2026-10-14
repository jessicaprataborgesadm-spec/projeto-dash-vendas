-- Projeto Dash Vendas
-- Objetivo: adicionar a feature media_7d à série diária de treinamento.
-- Fonte: projeto-dash-vendas.raw.olist_orders e raw.olist_order_items.
-- Granularidade final: uma linha por dia corrido.
-- Target preservado: faturamento_diario.
-- media_7d: média do faturamento dos 7 dias corridos ANTERIORES à data da linha.
-- Importante: a data atual não participa da média; os 7 dias incluem dias com faturamento zero.
-- Para os primeiros 7 dias, media_7d fica NULL porque não há 7 dias anteriores no período elegível.
-- Mantém a regra operacional: status atual 'delivered', SUM(price), sem frete,
-- atribuição à DATE(order_purchase_timestamp), treinamento de 2017-01-01 a 2018-08-29.
-- Não cria tabela física.

WITH parametros AS (
  SELECT
    DATE '2017-01-01' AS data_inicial_treinamento,
    DATE '2018-08-29' AS data_final_treinamento
),

calendario AS (
  SELECT data
  FROM parametros,
  UNNEST(
    GENERATE_DATE_ARRAY(
      data_inicial_treinamento,
      data_final_treinamento
    )
  ) AS data
),

pedidos_entregues AS (
  SELECT
    order_id,
    DATE(order_purchase_timestamp) AS data_compra
  FROM `projeto-dash-vendas.raw.olist_orders`
  CROSS JOIN parametros
  WHERE order_status = 'delivered'
    AND DATE(order_purchase_timestamp) >= data_inicial_treinamento
    AND DATE(order_purchase_timestamp) <= data_final_treinamento
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

base_diaria AS (
  SELECT
    c.data,
    COALESCE(f.faturamento_diario, NUMERIC '0') AS faturamento_diario,
    COALESCE(f.qtd_pedidos_entregues, 0) AS qtd_pedidos_entregues,
    COALESCE(f.qtd_linhas_itens_entregues, 0) AS qtd_linhas_itens_entregues
  FROM calendario AS c
  LEFT JOIN faturamento_por_dia AS f
    ON c.data = f.data
),

janelas AS (
  SELECT
    *,
    AVG(faturamento_diario) OVER (
      ORDER BY data
      ROWS BETWEEN 7 PRECEDING AND 1 PRECEDING
    ) AS media_7d_calculada,
    COUNT(*) OVER (
      ORDER BY data
      ROWS BETWEEN 7 PRECEDING AND 1 PRECEDING
    ) AS qtd_dias_janela
  FROM base_diaria
)

SELECT
  data,
  faturamento_diario,
  qtd_pedidos_entregues,
  qtd_linhas_itens_entregues,
  IF(qtd_dias_janela = 7, media_7d_calculada, NULL) AS media_7d
FROM janelas
ORDER BY data;
