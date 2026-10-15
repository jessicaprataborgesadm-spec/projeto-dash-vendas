-- Projeto Dash Vendas
-- Objetivo: adicionar a feature faturamento_ano_anterior à base diária com calendário.
-- Fontes: projeto-dash-vendas.raw.olist_orders e raw.olist_order_items.
-- Granularidade final: uma linha por dia corrido.
-- Target preservado: faturamento_diario.
--
-- Regra da feature faturamento_ano_anterior:
--   * Só usa referências do período 2017-01-01 a 2017-08-29, cuja cobertura foi
--     considerada potencialmente utilizável na auditoria mensal.
--   * A referência é o mesmo dia/mês do ano anterior e mantém a mesma definição
--     operacional: pedidos atualmente 'delivered', SUM(price), sem frete,
--     pela data de compra.
--   * Datas sem referência anual confiável recebem NULL, nunca zero artificial.
--   * 29 de fevereiro recebe NULL porque não existe a mesma data no ano anterior.
--
-- Preserva as features existentes: media_7d, dia_semana, indicadores e eventos de calendário.
-- Mantém período de treinamento 2017-01-01 a 2018-08-29.
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

-- A referência anual é confiável apenas para datas de 2017 entre janeiro e 29 de agosto.
-- O auto-join usa a série diária já agregada, preservando a granularidade de 1 linha por dia.
base_com_ano_anterior AS (
  SELECT
    atual.*,
    CASE
      WHEN EXTRACT(MONTH FROM atual.data) = 2
       AND EXTRACT(DAY FROM atual.data) = 29
        THEN CAST(NULL AS NUMERIC)
      WHEN DATE_SUB(atual.data, INTERVAL 1 YEAR)
        BETWEEN DATE '2017-01-01' AND DATE '2017-08-29'
        THEN historico.faturamento_diario
      ELSE CAST(NULL AS NUMERIC)
    END AS faturamento_ano_anterior
  FROM base_diaria AS atual
  LEFT JOIN base_diaria AS historico
    ON historico.data = DATE_SUB(atual.data, INTERVAL 1 YEAR)
   AND historico.data BETWEEN DATE '2017-01-01' AND DATE '2017-08-29'
   AND NOT (
     EXTRACT(MONTH FROM atual.data) = 2
     AND EXTRACT(DAY FROM atual.data) = 29
   )
),

eventos_base AS (
  SELECT *
  FROM UNNEST([
    -- 2017: feriados fixos nacionais, datas móveis e datas comerciais
    STRUCT(DATE '2017-01-01' AS data, 'Confraternização Universal / Ano-Novo' AS nome_evento, TRUE AS eh_feriado_nacional, FALSE AS eh_data_movel, TRUE AS eh_data_comercial),
    STRUCT(DATE '2017-02-27' AS data, 'Segunda-feira de Carnaval' AS nome_evento, FALSE AS eh_feriado_nacional, TRUE AS eh_data_movel, TRUE AS eh_data_comercial),
    STRUCT(DATE '2017-02-28' AS data, 'Terça-feira de Carnaval' AS nome_evento, FALSE AS eh_feriado_nacional, TRUE AS eh_data_movel, TRUE AS eh_data_comercial),
    STRUCT(DATE '2017-03-01' AS data, 'Quarta-feira de Cinzas' AS nome_evento, FALSE AS eh_feriado_nacional, TRUE AS eh_data_movel, TRUE AS eh_data_comercial),
    STRUCT(DATE '2017-03-15' AS data, 'Dia do Consumidor' AS nome_evento, FALSE AS eh_feriado_nacional, FALSE AS eh_data_movel, TRUE AS eh_data_comercial),
    STRUCT(DATE '2017-04-14' AS data, 'Sexta-feira Santa' AS nome_evento, FALSE AS eh_feriado_nacional, TRUE AS eh_data_movel, FALSE AS eh_data_comercial),
    STRUCT(DATE '2017-04-16' AS data, 'Páscoa' AS nome_evento, FALSE AS eh_feriado_nacional, TRUE AS eh_data_movel, TRUE AS eh_data_comercial),
    STRUCT(DATE '2017-04-21' AS data, 'Tiradentes' AS nome_evento, TRUE AS eh_feriado_nacional, FALSE AS eh_data_movel, FALSE AS eh_data_comercial),
    STRUCT(DATE '2017-05-01' AS data, 'Dia do Trabalho' AS nome_evento, TRUE AS eh_feriado_nacional, FALSE AS eh_data_movel, FALSE AS eh_data_comercial),
    STRUCT(DATE '2017-05-14' AS data, 'Dia das Mães' AS nome_evento, FALSE AS eh_feriado_nacional, FALSE AS eh_data_movel, TRUE AS eh_data_comercial),
    STRUCT(DATE '2017-06-12' AS data, 'Dia dos Namorados' AS nome_evento, FALSE AS eh_feriado_nacional, FALSE AS eh_data_movel, TRUE AS eh_data_comercial),
    STRUCT(DATE '2017-06-15' AS data, 'Corpus Christi' AS nome_evento, FALSE AS eh_feriado_nacional, TRUE AS eh_data_movel, FALSE AS eh_data_comercial),
    STRUCT(DATE '2017-08-13' AS data, 'Dia dos Pais' AS nome_evento, FALSE AS eh_feriado_nacional, FALSE AS eh_data_movel, TRUE AS eh_data_comercial),
    STRUCT(DATE '2017-09-07' AS data, 'Independência do Brasil' AS nome_evento, TRUE AS eh_feriado_nacional, FALSE AS eh_data_movel, FALSE AS eh_data_comercial),
    STRUCT(DATE '2017-10-12' AS data, 'Nossa Senhora Aparecida' AS nome_evento, TRUE AS eh_feriado_nacional, FALSE AS eh_data_movel, FALSE AS eh_data_comercial),
    STRUCT(DATE '2017-10-12' AS data, 'Dia das Crianças' AS nome_evento, FALSE AS eh_feriado_nacional, FALSE AS eh_data_movel, TRUE AS eh_data_comercial),
    STRUCT(DATE '2017-11-02' AS data, 'Finados' AS nome_evento, TRUE AS eh_feriado_nacional, FALSE AS eh_data_movel, FALSE AS eh_data_comercial),
    STRUCT(DATE '2017-11-15' AS data, 'Proclamação da República' AS nome_evento, TRUE AS eh_feriado_nacional, FALSE AS eh_data_movel, FALSE AS eh_data_comercial),
    STRUCT(DATE '2017-11-24' AS data, 'Black Friday' AS nome_evento, FALSE AS eh_feriado_nacional, FALSE AS eh_data_movel, TRUE AS eh_data_comercial),
    STRUCT(DATE '2017-11-27' AS data, 'Cyber Monday' AS nome_evento, FALSE AS eh_feriado_nacional, FALSE AS eh_data_movel, TRUE AS eh_data_comercial),
    STRUCT(DATE '2017-12-24' AS data, 'Véspera de Natal' AS nome_evento, FALSE AS eh_feriado_nacional, FALSE AS eh_data_movel, TRUE AS eh_data_comercial),
    STRUCT(DATE '2017-12-25' AS data, 'Natal' AS nome_evento, TRUE AS eh_feriado_nacional, FALSE AS eh_data_movel, TRUE AS eh_data_comercial),
    STRUCT(DATE '2017-12-31' AS data, 'Véspera de Ano-Novo' AS nome_evento, FALSE AS eh_feriado_nacional, FALSE AS eh_data_movel, TRUE AS eh_data_comercial),

    -- 2018: feriados fixos nacionais, datas móveis e datas comerciais
    STRUCT(DATE '2018-01-01' AS data, 'Confraternização Universal / Ano-Novo' AS nome_evento, TRUE AS eh_feriado_nacional, FALSE AS eh_data_movel, TRUE AS eh_data_comercial),
    STRUCT(DATE '2018-02-12' AS data, 'Segunda-feira de Carnaval' AS nome_evento, FALSE AS eh_feriado_nacional, TRUE AS eh_data_movel, TRUE AS eh_data_comercial),
    STRUCT(DATE '2018-02-13' AS data, 'Terça-feira de Carnaval' AS nome_evento, FALSE AS eh_feriado_nacional, TRUE AS eh_data_movel, TRUE AS eh_data_comercial),
    STRUCT(DATE '2018-02-14' AS data, 'Quarta-feira de Cinzas' AS nome_evento, FALSE AS eh_feriado_nacional, TRUE AS eh_data_movel, TRUE AS eh_data_comercial),
    STRUCT(DATE '2018-03-15' AS data, 'Dia do Consumidor' AS nome_evento, FALSE AS eh_feriado_nacional, FALSE AS eh_data_movel, TRUE AS eh_data_comercial),
    STRUCT(DATE '2018-03-30' AS data, 'Sexta-feira Santa' AS nome_evento, FALSE AS eh_feriado_nacional, TRUE AS eh_data_movel, FALSE AS eh_data_comercial),
    STRUCT(DATE '2018-04-01' AS data, 'Páscoa' AS nome_evento, FALSE AS eh_feriado_nacional, TRUE AS eh_data_movel, TRUE AS eh_data_comercial),
    STRUCT(DATE '2018-04-21' AS data, 'Tiradentes' AS nome_evento, TRUE AS eh_feriado_nacional, FALSE AS eh_data_movel, FALSE AS eh_data_comercial),
    STRUCT(DATE '2018-05-01' AS data, 'Dia do Trabalho' AS nome_evento, TRUE AS eh_feriado_nacional, FALSE AS eh_data_movel, FALSE AS eh_data_comercial),
    STRUCT(DATE '2018-05-13' AS data, 'Dia das Mães' AS nome_evento, FALSE AS eh_feriado_nacional, FALSE AS eh_data_movel, TRUE AS eh_data_comercial),
    STRUCT(DATE '2018-05-31' AS data, 'Corpus Christi' AS nome_evento, FALSE AS eh_feriado_nacional, TRUE AS eh_data_movel, FALSE AS eh_data_comercial),
    STRUCT(DATE '2018-06-12' AS data, 'Dia dos Namorados' AS nome_evento, FALSE AS eh_feriado_nacional, FALSE AS eh_data_movel, TRUE AS eh_data_comercial),
    STRUCT(DATE '2018-08-12' AS data, 'Dia dos Pais' AS nome_evento, FALSE AS eh_feriado_nacional, FALSE AS eh_data_movel, TRUE AS eh_data_comercial),
    STRUCT(DATE '2018-09-07' AS data, 'Independência do Brasil' AS nome_evento, TRUE AS eh_feriado_nacional, FALSE AS eh_data_movel, FALSE AS eh_data_comercial),
    STRUCT(DATE '2018-10-12' AS data, 'Nossa Senhora Aparecida' AS nome_evento, TRUE AS eh_feriado_nacional, FALSE AS eh_data_movel, FALSE AS eh_data_comercial),
    STRUCT(DATE '2018-10-12' AS data, 'Dia das Crianças' AS nome_evento, FALSE AS eh_feriado_nacional, FALSE AS eh_data_movel, TRUE AS eh_data_comercial),
    STRUCT(DATE '2018-11-02' AS data, 'Finados' AS nome_evento, TRUE AS eh_feriado_nacional, FALSE AS eh_data_movel, FALSE AS eh_data_comercial),
    STRUCT(DATE '2018-11-15' AS data, 'Proclamação da República' AS nome_evento, TRUE AS eh_feriado_nacional, FALSE AS eh_data_movel, FALSE AS eh_data_comercial),
    STRUCT(DATE '2018-11-23' AS data, 'Black Friday' AS nome_evento, FALSE AS eh_feriado_nacional, FALSE AS eh_data_movel, TRUE AS eh_data_comercial),
    STRUCT(DATE '2018-11-26' AS data, 'Cyber Monday' AS nome_evento, FALSE AS eh_feriado_nacional, FALSE AS eh_data_movel, TRUE AS eh_data_comercial),
    STRUCT(DATE '2018-12-24' AS data, 'Véspera de Natal' AS nome_evento, FALSE AS eh_feriado_nacional, FALSE AS eh_data_movel, TRUE AS eh_data_comercial),
    STRUCT(DATE '2018-12-25' AS data, 'Natal' AS nome_evento, TRUE AS eh_feriado_nacional, FALSE AS eh_data_movel, TRUE AS eh_data_comercial),
    STRUCT(DATE '2018-12-31' AS data, 'Véspera de Ano-Novo' AS nome_evento, FALSE AS eh_feriado_nacional, FALSE AS eh_data_movel, TRUE AS eh_data_comercial)
  ])
),

eventos_por_data AS (
  SELECT
    data,
    LOGICAL_OR(eh_feriado_nacional) AS eh_feriado_nacional,
    LOGICAL_OR(eh_data_movel) AS eh_data_movel,
    LOGICAL_OR(eh_data_comercial) AS eh_data_comercial,
    STRING_AGG(DISTINCT nome_evento, ' | ' ORDER BY nome_evento) AS eventos_calendario
  FROM eventos_base
  GROUP BY data
),

base_com_eventos AS (
  SELECT
    b.*,
    COALESCE(e.eh_feriado_nacional, FALSE) AS eh_feriado_nacional,
    COALESCE(e.eh_data_movel, FALSE) AS eh_data_movel,
    COALESCE(e.eh_data_comercial, FALSE) AS eh_data_comercial,
    e.eventos_calendario
  FROM base_com_ano_anterior AS b
  LEFT JOIN eventos_por_data AS e
    ON b.data = e.data
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
  FROM base_com_eventos
)

SELECT
  data,
  CASE EXTRACT(DAYOFWEEK FROM data)
    WHEN 1 THEN 'domingo'
    WHEN 2 THEN 'segunda-feira'
    WHEN 3 THEN 'terça-feira'
    WHEN 4 THEN 'quarta-feira'
    WHEN 5 THEN 'quinta-feira'
    WHEN 6 THEN 'sexta-feira'
    WHEN 7 THEN 'sábado'
  END AS dia_semana,
  faturamento_diario,
  faturamento_ano_anterior,
  qtd_pedidos_entregues,
  qtd_linhas_itens_entregues,
  IF(qtd_dias_janela = 7, media_7d_calculada, NULL) AS media_7d,
  eh_feriado_nacional,
  eh_data_movel,
  eh_data_comercial,
  eventos_calendario
FROM janelas
ORDER BY data;
