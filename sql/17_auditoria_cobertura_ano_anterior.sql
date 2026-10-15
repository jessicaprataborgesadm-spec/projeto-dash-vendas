-- Projeto Dash Vendas
-- Objetivo: auditar a disponibilidade do mesmo período no ano anterior antes de criar
-- a feature faturamento_ano_anterior.
-- Fontes: projeto-dash-vendas.raw.olist_orders e raw.olist_order_items.
-- Granularidade final: uma linha por mês do período de treinamento.
-- Período de treinamento auditado: 2017-01-01 a 2018-08-29.
-- Regra operacional preservada para o faturamento: status atual 'delivered', SUM(price),
-- frete excluído e data atribuída a DATE(order_purchase_timestamp).
--
-- IMPORTANTE:
-- 1. Uma data sem pedidos na tabela transacional não prova, sozinha, falha de cobertura.
-- 2. Meses anteriores ao início da fonte não recebem faturamento zero: recebem NULL,
--    pois não há observação disponível para comparar.
-- 3. Set-Dez/2016 é sinalizado como cobertura conhecida por ser irregular na auditoria
--    temporal anterior. O volume observado não deve ser tratado como referência anual confiável.
-- 4. A consulta é diagnóstica: não cria tabela física nem implementa a feature final.

WITH parametros AS (
  SELECT
    DATE '2017-01-01' AS data_inicial_treinamento,
    DATE '2018-08-29' AS data_final_treinamento
),

calendario_treinamento AS (
  SELECT data
  FROM parametros,
  UNNEST(
    GENERATE_DATE_ARRAY(
      data_inicial_treinamento,
      data_final_treinamento
    )
  ) AS data
),

datas_comparacao AS (
  SELECT
    data AS data_treinamento,
    DATE_SUB(data, INTERVAL 1 YEAR) AS data_comparacao
  FROM calendario_treinamento
),

cobertura_origem AS (
  SELECT
    MIN(DATE(order_purchase_timestamp)) AS primeira_data_compra_fonte,
    MAX(DATE(order_purchase_timestamp)) AS ultima_data_compra_fonte
  FROM `projeto-dash-vendas.raw.olist_orders`
),

pedidos_por_dia AS (
  SELECT
    DATE(o.order_purchase_timestamp) AS data,
    COUNT(*) AS qtd_pedidos_origem,
    COUNTIF(o.order_status = 'delivered') AS qtd_pedidos_status_delivered
  FROM `projeto-dash-vendas.raw.olist_orders` AS o
  CROSS JOIN parametros AS p
  WHERE DATE(o.order_purchase_timestamp)
    BETWEEN DATE_SUB(p.data_inicial_treinamento, INTERVAL 1 YEAR)
        AND DATE_SUB(p.data_final_treinamento, INTERVAL 1 YEAR)
  GROUP BY data
),

pedidos_entregues AS (
  SELECT
    o.order_id,
    DATE(o.order_purchase_timestamp) AS data_compra
  FROM `projeto-dash-vendas.raw.olist_orders` AS o
  CROSS JOIN parametros AS p
  WHERE o.order_status = 'delivered'
    AND DATE(o.order_purchase_timestamp)
      BETWEEN DATE_SUB(p.data_inicial_treinamento, INTERVAL 1 YEAR)
          AND DATE_SUB(p.data_final_treinamento, INTERVAL 1 YEAR)
),

faturamento_entregue_por_dia AS (
  SELECT
    p.data_compra AS data,
    SUM(CAST(oi.price AS NUMERIC)) AS faturamento_diario,
    COUNT(DISTINCT p.order_id) AS qtd_pedidos_entregues_com_itens,
    COUNT(*) AS qtd_linhas_itens_entregues
  FROM pedidos_entregues AS p
  INNER JOIN `projeto-dash-vendas.raw.olist_order_items` AS oi
    ON p.order_id = oi.order_id
  GROUP BY p.data_compra
),

comparacao_diaria AS (
  SELECT
    d.data_treinamento,
    d.data_comparacao,
    COALESCE(o.qtd_pedidos_origem, 0) AS qtd_pedidos_origem,
    COALESCE(o.qtd_pedidos_status_delivered, 0) AS qtd_pedidos_status_delivered,
    f.faturamento_diario,
    COALESCE(f.qtd_pedidos_entregues_com_itens, 0) AS qtd_pedidos_entregues_com_itens,
    COALESCE(f.qtd_linhas_itens_entregues, 0) AS qtd_linhas_itens_entregues
  FROM datas_comparacao AS d
  LEFT JOIN pedidos_por_dia AS o
    ON d.data_comparacao = o.data
  LEFT JOIN faturamento_entregue_por_dia AS f
    ON d.data_comparacao = f.data
)

SELECT
  DATE_TRUNC(data_treinamento, MONTH) AS mes_treinamento,
  DATE_TRUNC(data_comparacao, MONTH) AS mes_referencia_ano_anterior,
  MIN(data_comparacao) AS primeira_data_referencia_esperada,
  MAX(data_comparacao) AS ultima_data_referencia_esperada,
  COUNT(*) AS qtd_dias_calendario_comparados,

  cobertura.primeira_data_compra_fonte,
  cobertura.ultima_data_compra_fonte,

  COUNTIF(qtd_pedidos_origem > 0) AS qtd_dias_com_registro_de_pedido,
  SUM(qtd_pedidos_origem) AS qtd_pedidos_origem,
  SUM(qtd_pedidos_status_delivered) AS qtd_pedidos_status_delivered,
  COUNTIF(qtd_pedidos_status_delivered > 0) AS qtd_dias_com_pedido_delivered,
  SUM(qtd_pedidos_entregues_com_itens) AS qtd_pedidos_entregues_com_itens,
  SUM(qtd_linhas_itens_entregues) AS qtd_linhas_itens_entregues,

  CASE
    WHEN MAX(data_comparacao) < cobertura.primeira_data_compra_fonte
      THEN CAST(NULL AS NUMERIC)
    ELSE SUM(COALESCE(faturamento_diario, NUMERIC '0'))
  END AS faturamento_itens_delivered_ano_anterior,

  CASE
    WHEN MAX(data_comparacao) < cobertura.primeira_data_compra_fonte
      THEN 'SEM DADOS DA FONTE PARA O PERIODO COMPARAVEL'
    WHEN DATE_TRUNC(MIN(data_comparacao), MONTH) < DATE '2017-01-01'
      THEN '2016: COBERTURA CONHECIDAMENTE IRREGULAR; NAO USAR SEM RESSALVA'
    ELSE 'REFERENCIA EM 2017: POTENCIALMENTE UTILIZAVEL; VALIDAR RESULTADO'
  END AS classificacao_cobertura

FROM comparacao_diaria
CROSS JOIN cobertura_origem AS cobertura
GROUP BY
  mes_treinamento,
  mes_referencia_ano_anterior,
  cobertura.primeira_data_compra_fonte,
  cobertura.ultima_data_compra_fonte
ORDER BY mes_treinamento;
