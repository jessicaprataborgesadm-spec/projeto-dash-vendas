-- Objetivo: verificar preenchimento e amplitude dos valores de price.
-- Tabela: olist_order_items.
-- Granularidade: uma linha por item do pedido.
-- Validações: total de linhas, preços não nulos, preços nulos,
-- menor preço e maior preço.
-- Resultado da auditoria anterior: 112.650 linhas,
-- 112.650 preços preenchidos, nenhum preço nulo,
-- mínimo de 0,85 e máximo de 6.735,00.

SELECT
  COUNT(*) AS total_linhas,
  COUNT(price) AS price_preenchido,
  COUNTIF(price IS NULL) AS price_nulo,
  MIN(price) AS menor_price,
  MAX(price) AS maior_price
FROM `projeto-dash-vendas.raw.olist_order_items`;
