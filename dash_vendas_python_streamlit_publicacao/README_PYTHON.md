# Camada Python e Dashboard | Projeto Dash Vendas

Esta pasta contém os scripts Python, o dashboard Streamlit, as dependências e os CSVs agregados usados pela aplicação.

## Estrutura

Mantenha os arquivos desta pasta juntos. O dashboard lê seis arquivos CSV locais e não consulta o BigQuery diretamente. O CSV da previsão ativa é `24_previsao_30_dias_corte_20_08.csv`; o arquivo 23 permanece preservado como experimento anterior.

## Executar o dashboard (Windows)

Abra o terminal na raiz do repositório e entre nesta pasta:

```bash
cd dash_vendas_python_streamlit_publicacao
```

Crie e ative um ambiente virtual, instale as dependências e inicie o dashboard:

```bash
py -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

O Streamlit abrirá o endereço local informado no terminal.

## Reproduzir os experimentos

Execute os comandos a partir desta pasta, onde estão os scripts e a base CSV:

```bash
python 19_avaliacao_baseline.py
python 20_modelo_random_forest_teste.py
python 21_validacao_temporal_modelos.py
python 22_validacao_janela_recente.py
python 23_previsao_30_dias_corte_22_08.py
python 24_previsao_30_dias_corte_20_08.py
```

A base `base_treinamento_faturamento_teste.csv` é a exportação agregada da SQL 18 e mantém o período de 01/01/2017 a 29/08/2018. Ela é compartilhada pelos experimentos de validação histórica e pela simulação de previsão. Para atualizar os resultados, exporte novamente a saída da consulta e substitua esse arquivo, preservando o nome e as colunas esperadas.

**Importante sobre os cortes:** os testes históricos precisam das observações até 29/08/2018 para avaliar a janela recente. O script `23_previsao_30_dias_corte_22_08.py` permanece como experimento anterior, treinado até 22/08/2018. O script `24_previsao_30_dias_corte_20_08.py`, usado pelo dashboard, treina somente até 20/08/2018 e prevê de 21/08 a 19/09. Para prever 21 a 29/08, usa apenas features conhecidas de calendário e faturamento do ano anterior; não usa o `faturamento_diario` real dessas datas nem atualiza `media_7d` com valores realizados futuros.

Uma comparação de sensibilidade dos cortes mostrou variação de -4,77% no valor médio dos últimos sete dias em 20/08, contra -23,26% em 22/08 e quedas ainda maiores nos cortes posteriores. Por isso, 20/08/2018 foi adotado como corte provisório mais prudente para esta simulação. O script `24_previsao_30_dias_corte_20_08.py` foi executado e gerou 30 previsões de 21/08 a 19/09. O Random Forest totaliza R$ 993.231,78 e o baseline R$ 1.024.124,10. O CSV passou por verificações estruturais; não contém faturamento realizado, portanto não permite calcular métricas de erro para esse horizonte. O corte continua sendo uma decisão provisória, não um ponto de mudança estatisticamente comprovado.

Os scripts geram os CSVs de resultados utilizados pelo dashboard. A previsão de vários dias atualiza a média móvel com previsões anteriores, sem usar faturamento real futuro.

## Definição e limites dos dados

A série representa o valor dos itens (`olist_order_items.price`) de pedidos cujo status atual na fonte é `delivered`, agrupado pela data de compra. Não inclui frete e não deve ser interpretada como faturamento contábil ou receita líquida reconciliada.

O dataset é histórico (2016–2018). A previsão de 30 dias exibida no dashboard é uma simulação retrospectiva com corte provisório em 20/08/2018, não uma previsão para o mercado atual. O arquivo de previsão não contém realizado maduro para calcular métricas de erro.


## Roteador determinístico de perguntas

O roteador está em `ia_analista/router.py`. A primeira versão usa padrões explícitos em português, sem LLM, para:
- reconhecer as sete intenções do catálogo;
- extrair datas em `DD/MM/AAAA` ou `AAAA-MM-DD`, mês/ano por extenso, semestre e ano;
- pedir esclarecimento quando a intenção exige período e ele não foi informado;
- sinalizar perguntas que misturam mais de uma intenção;
- encaminhar perguntas sem dimensão disponível para `out_of_scope`;
- chamar o motor analítico por meio de `executar_pergunta` somente quando a rota estiver pronta.

Status de roteamento: `ready`, `ambiguous`, `invalid` e `out_of_scope`. Essa versão é baseada em regras e não compreende todas as variações de linguagem. O roteador já é chamado pela página `IA Analista` no Streamlit; ainda não há LLM conectado.

## Motor determinístico da IA Analista

O módulo está em `ia_analista/analytics.py`. Ele calcula os fatos das sete intenções cadastradas no catálogo, usando os CSVs existentes. A página `IA Analista` carrega essas fontes sob demanda e usa `ia_analista/router.py` para encaminhar perguntas. As respostas são apresentadas por templates determinísticos; não há LLM conectado.

Funções disponíveis:
- `analisar_evolucao`: total, média, mediana e extremos do período;
- `comparar_periodos`: mesmo período do ano anterior ou período imediatamente anterior;
- `analisar_dia_semana`: estatísticas por dia da semana;
- `analisar_calendario`: comparação descritiva de feriados/datas sinalizadas;
- `diagnosticar_variacao`: comparação de janelas equivalentes e maiores diferenças diárias;
- `consultar_previsao_30_dias`: resumo da simulação ativa;
- `avaliar_modelos`: teste inicial, cinco janelas e diagnóstico recente;
- `executar_intencao`: dispatcher explícito para as intenções cadastradas.

As respostas usam um contrato estruturado com `status`, `intent`, `metric`, `period`, `facts`, `coverage` e `limitations`. Os status incluem `ok`, `partial_data`, `insufficient_data` e `out_of_scope`.

Exemplo de uso a partir desta pasta:

```python
from ia_analista.analytics import carregar_fontes, executar_intencao

fontes = carregar_fontes()
resultado = executar_intencao(
    "period_evolution",
    fontes,
    {"data_inicio": "2018-07-01", "data_fim": "2018-07-30"},
)
print(resultado)
```

### Executar os testes do motor

Com as dependências instaladas, execute a partir desta pasta:

```bash
python -m unittest discover -s tests -v
```

Os testes usam a biblioteca padrão `unittest`; não exigem instalar pytest. A bateria atual cobre as sete intenções, cobertura parcial, datas inválidas/duplicadas, serialização JSON e valores de referência conhecidos.



## Interface conversacional no Streamlit

A página **IA Analista** foi adicionada ao menu do `app.py`. Ela usa `st.chat_input` e `st.chat_message`, mantendo o histórico em `st.session_state` durante a sessão atual. O botão **Limpar** apaga a conversa da sessão.

As cinco fontes analíticas são carregadas somente ao abrir essa página, por meio de `carregar_fontes()` com cache do Streamlit. As demais páginas continuam usando o carregamento de CSVs que já existia.

Nesta etapa, a resposta é determinística e formatada por intenção. Não existe chamada a LLM, e a interface informa essa limitação. Perguntas sem período, ambíguas, inválidas ou fora do escopo exibem o esclarecimento retornado pelo roteador.

### Validar a aplicação e os testes

A suíte completa inclui:
- `tests/test_analytics.py`: motor analítico;
- `tests/test_router.py`: roteamento e execução;
- `tests/test_app_syntax.py`: compilação sintática do `app.py`.

Execute a partir desta pasta:

```bash
python -W error::DeprecationWarning -m unittest discover -s tests -v
```

Depois inicie o dashboard:

```bash
python -m streamlit run app.py
```

A suíte anterior de 28 testes do motor e do roteador já passou localmente. O teste sintático novo e a validação manual da interface ainda precisam ser executados no ambiente local.
