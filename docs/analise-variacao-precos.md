# Análise exploratória de variação de preços

## 1. Objetivo

Investigar diferenças nos preços observados de produtos do dataset público da Olist em torno de março de 2018, verificando se os resultados oferecem evidências de um movimento generalizado de aumento de preços.

## 2. Fonte de dados

Dataset: [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)

Tabelas utilizadas no BigQuery:

- `projeto-dash-vendas.raw.olist_orders`
- `projeto-dash-vendas.raw.olist_order_items`

O relacionamento foi realizado pela chave `order_id`. Como a tabela de itens possui granularidade por item do pedido, um mesmo pedido pode aparecer em várias linhas após o relacionamento.

## 3. Metodologia

Foram comparados os preços observados em duas janelas:

- **Janela anterior:** 21/02/2018 a 19/03/2018.
- **Janela posterior:** 21/03/2018 a 17/04/2018.

O dia 20/03/2018 foi excluído da comparação.

Para cada produto presente nas duas janelas, foram selecionados:

- O último preço observado na janela anterior.
- O primeiro preço observado na janela posterior.

Em seguida, os dois valores foram comparados.

## 4. Resultados

| Indicador | Resultado |
|---|---:|
| Produtos comparáveis | 1.160 |
| Produtos com preços diferentes | 222 |
| Produtos com preço maior na observação posterior | 116 |
| Produtos com preço menor na observação posterior | 106 |
| Produtos com preços diferentes entre os comparáveis | 19,1% |

Entre os 222 produtos com preços diferentes, aproximadamente 52,3% apresentaram um valor maior na observação posterior e 47,7% apresentaram um valor menor.

## 5. Interpretação analítica

Os resultados mostram que houve diferenças entre os preços selecionados para uma parcela dos produtos comparáveis.

A quantidade de aumentos e reduções foi relativamente próxima. Portanto, os resultados desta comparação não são suficientes para sustentar a hipótese de um reajuste generalizado de preços.

Essa conclusão é restrita às observações e ao período analisados.

## 6. Limitações

- A comparação utiliza apenas o último preço observado antes e o primeiro preço observado depois, não todos os preços praticados nas janelas.
- As diferenças encontradas não identificam a data exata em que uma alteração ocorreu.
- Não é possível concluir, com esta análise, se as diferenças foram permanentes.
- A análise não identifica as causas das variações.
- Os resultados não devem ser generalizados automaticamente para todos os produtos ou para todo o mercado.

## 7. Conclusão

A investigação identificou diferenças de preços em 222 dos 1.160 produtos comparáveis nas duas janelas temporais.

Foram observados 116 preços maiores e 106 preços menores na observação posterior. A distribuição não fornece evidência suficiente para afirmar que ocorreu um reajuste generalizado.

O estudo será mantido como uma análise exploratória complementar do portfólio, demonstrando o uso de SQL, comparação temporal, formulação de hipóteses e interpretação cautelosa dos resultados.

## 8. Próximas etapas do projeto

A prioridade do Projeto Dash Vendas permanece:

1. Consolidar as validações das tabelas de origem.
2. Definir a métrica de faturamento e os filtros aplicáveis aos pedidos.
3. Construir a base diária no BigQuery.
4. Validar granularidade, totais e cobertura temporal.
5. Avançar para as features, o baseline preditivo e o dashboard.

Esta investigação de preços não substitui nem altera as próximas etapas do pipeline.
