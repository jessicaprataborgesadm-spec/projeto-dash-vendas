# Análise do pico de faturamento — novembro de 2017

**Projeto:** Dash Vendas  
**Fonte analisada:** `base_treinamento_faturamento_teste.csv`  
**Granularidade da fonte:** uma linha por dia  
**Data do pico:** 24/11/2017

## 1. Objetivo

Investigar o pico observado no gráfico histórico de faturamento diário em novembro de 2017 e verificar se a data e as características do registro são compatíveis com um evento comercial conhecido.

## 2. Resultado observado

Na base diária, o maior faturamento de novembro de 2017 ocorreu em **24/11/2017**:

| Indicador | 24/11/2017 |
|---|---:|
| Faturamento diário | R$ 149.916,58 |
| Pedidos atualmente `delivered` | 1.147 |
| Linhas de itens | 1.345 |
| Dia da semana | Sexta-feira |
| `eh_data_comercial` | TRUE |
| `eventos_calendario` | Black Friday |

## 3. Comparação com novembro de 2017

| Indicador | Novembro/2017 | 24/11/2017 |
|---|---:|---:|
| Faturamento dos itens | R$ 987.765,37 | R$ 149.916,58 |
| Pedidos atualmente `delivered` | 7.289 | 1.147 |
| Linhas de itens | 8.475 | 1.345 |
| Faturamento diário mediano | R$ 24.129,53 | — |
| Média diária de pedidos | 242,97 | — |

O dia 24/11 respondeu por aproximadamente **15,18% do faturamento mensal** e **15,74% dos pedidos entregues do mês**. A quantidade de pedidos nesse dia foi aproximadamente **4,72 vezes a média diária de novembro**.

O valor médio de itens por pedido, calculado como `faturamento_diario / qtd_pedidos_entregues`, foi de aproximadamente **R$ 130,70** no dia do pico, contra **R$ 135,51** no mês. Essa métrica é uma razão operacional simples, não um ticket contábil ou financeiro reconciliado.

## 4. Interpretação

Os dados são compatíveis com um pico associado à Black Friday. A feature de calendário identifica 24/11/2017 como `Black Friday`, e o aumento observado está concentrado principalmente no volume de pedidos, não em um valor médio por pedido excepcionalmente elevado.

Essa evidência sustenta a hipótese de um evento comercial, mas **não prova causalidade**. A base analisada já está agregada por dia e considera pedidos cujo status atual é `delivered`.

## 5. Decisão analítica

- Manter o registro de 24/11/2017 na série histórica.
- Não excluir, substituir, suavizar ou limitar artificialmente o valor por ser um ponto extremo.
- Preservar a feature de calendário que identifica Black Friday.
- Documentar o evento como uma observação comercial relevante e uma possível fonte de sazonalidade.

## 6. Limitações e auditoria ainda não realizada

Esta análise foi feita sobre a base diária agregada. Ela **não decompõe os pedidos individuais diretamente nas tabelas RAW**, nem valida os 20 maiores pedidos, vendedores ou produtos do dia.

Além disso, a definição operacional do projeto considera `SUM(oi.price)` para pedidos cujo status atual é `delivered`, agrupado pela data da compra. Frete é excluído. Isso não equivale a faturamento contábil reconciliado e pode refletir a maturidade dos pedidos na extração do dataset.

Portanto, a conclusão apropriada é: **pico compatível com Black Friday e explicado principalmente por maior volume de pedidos, sujeito à limitação da métrica e sem afirmação causal definitiva**.

## 7. Reprodutibilidade

Os indicadores desta análise podem ser recalculados a partir das colunas existentes na base diária:

- `data`
- `faturamento_diario`
- `qtd_pedidos_entregues`
- `qtd_linhas_itens_entregues`
- `eh_data_comercial`
- `eventos_calendario`

Nenhuma SQL, tabela RAW, feature, previsão ou modelo foi alterado para produzir este documento.
