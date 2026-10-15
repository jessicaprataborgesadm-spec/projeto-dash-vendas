-- Projeto Dash Vendas
-- Objetivo: adicionar indicadores de calendário que podem influenciar o comportamento do consumidor.
-- Fontes de dados: projeto-dash-vendas.raw.olist_orders e raw.olist_order_items.
-- Granularidade final: uma linha por dia corrido, sem multiplicação por eventos coincidentes.
-- Target preservado: faturamento_diario.
-- Features adicionadas:
--   eh_feriado_nacional: feriados nacionais aplicáveis no período histórico.
--   eh_data_movel: Carnaval, Quarta-feira de Cinzas, Sexta-feira Santa, Páscoa e Corpus Christi.
--   eh_data_comercial: datas de varejo/consumo, como Dia das Mães, Dia dos Namorados,
--                      Dia dos Pais, Dia das Crianças, Black Friday e Cyber Monday.
--   eventos_calendario: descrição legível dos eventos associados à data.
--
-- A lista de eventos abaixo cobre 2017 e 2018, período de dados da fonte Olist usada aqui.
-- Para previsões em anos posteriores, ampliar/atualizar a lista de eventos antes de usar.
-- Feriados nacionais: Lei 662/1949 (texto atualizado) e Lei 6.802/1980 (12 de outubro).
-- Referências legais: https://www.planalto.gov.br/ccivil_03/leis/l0662.htm
--                     https://www.planalto.gov.br/ccivil_03/leis/l6802.htm
-- Referência de datas móveis: Carnaval, Sexta-feira Santa, Páscoa e Corpus Christi são móveis;
-- suas datas históricas foram conferidas com calendários brasileiros.
-- Ex.: https://www.calendarr.com/brasil/calendario-2017/
--      https://www.calendarr.com/brasil/feriados-2018/
--
-- Mantém as regras anteriores: status atual 'delivered', SUM(price), sem frete,
-- data de compra (DATE(order_purchase_timestamp)), janela de treino 2017-01-01 a 2018-08-29.
-- media_7d usa somente os 7 dias corridos anteriores, incluindo dias com faturamento zero.
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
  FROM base_diaria AS b
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
  qtd_pedidos_entregues,
  qtd_linhas_itens_entregues,
  IF(qtd_dias_janela = 7, media_7d_calculada, NULL) AS media_7d,
  eh_feriado_nacional,
  eh_data_movel,
  eh_data_comercial,
  eventos_calendario
FROM janelas
ORDER BY data;
