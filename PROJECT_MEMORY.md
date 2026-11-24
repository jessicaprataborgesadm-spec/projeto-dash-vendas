# PROJECT_MEMORY.md

Memória de continuidade e fonte de referência do Projeto Dash Vendas. Atualizada em 24/11/2026.

## 1. Objetivo e escopo da versão de portfólio

Construir uma solução de Dados + IA com dados públicos do e-commerce Olist para:
- transformar dados transacionais em uma série diária analítica;
- investigar qualidade, cobertura e comportamento temporal;
- comparar um baseline com Random Forest;
- produzir uma simulação retrospectiva de previsão diária por 30 dias;
- apresentar histórico, validação e previsão em um dashboard Streamlit local;
- implementar uma IA Analista conversacional que responda perguntas de negócio usando fatos calculados de forma determinística.

**Status atual:** a fundação analítica/preditiva e o dashboard local estão concluídos. A IA Analista determinística (roteador por regras, motor Python e interface conversacional) está implementada e foi validada nas sete intenções do MVP e em uma pergunta fora do escopo. Duas chamadas reais com `gemini-3.8-flash` retornaram `503 UNAVAILABLE` por alta demanda reportada pelo provedor. A usuária autorizou uma única tentativa adicional controlada com `gemini-3.5-flash-lite`, selecionado localmente no arquivo `.streamlit/secrets.toml`, sem alterar o código Python. Essa tentativa ainda está pendente. Não haverá billing, cartão, upgrade nem nova chamada caso essa tentativa falhe. Permanecem pendentes os seis testes simulados do LLM, a revisão da suíte completa, alguns casos de borda, a melhoria do diagnóstico e o fechamento documental do portfólio.

**Decisão atual:** após duas respostas `503 UNAVAILABLE` de `gemini-3.8-flash`, foi autorizada uma única tentativa final com o modelo alternativo `gemini-3.5-flash-lite`. A troca é feita pela configuração local `GEMINI_MODEL` em `.streamlit/secrets.toml`, editável pelo Bloco de Notas, sem alterar código Python. Não habilitar faturamento, não adicionar cartão e não fazer upgrade. Se a tentativa alternativa falhar, não realizar novas chamadas nesta versão; preservar a IA Analista determinística e seguir com as revisões do portfólio. Inferência local/WebGPU, hospedagem pública e automação de atualização dos dados são expansões opcionais.

## 2. Fonte e definição da métrica

- Fonte pública: Brazilian E-Commerce Public Dataset by Olist (Kaggle).
- Projeto GCP: `projeto-dash-vendas`.
- Dataset BigQuery: `raw`.
- Região: `southamerica-east1`.
- Tabelas RAW usadas na métrica: `raw.olist_orders` e `raw.olist_order_items`.
- Join: `order_id`.
- Filtro: status atual do pedido `delivered`.
- Métrica: soma de `olist_order_items.price`, sem `freight_value`.
- Data de agregação: `DATE(order_purchase_timestamp)`.
- Granularidade final: **uma linha por dia corrido**.

A métrica é uma aproximação operacional do valor dos itens associados a pedidos atualmente `delivered`. Não é faturamento contábil nem receita líquida reconciliada. O status atual pode refletir eventos posteriores à compra; a cobertura temporal da cauda da série é irregular e exige cautela.

## 3. Arquitetura existente

```text
Olist / Kaggle
    -> BigQuery RAW
    -> SQL / ELT (consultas versionadas 01 a 18)
    -> base diária e features
    -> exportação CSV
    -> Python (baseline, Random Forest, backtests e previsão)
    -> CSVs de resultados
    -> Streamlit local
```

O dashboard lê seis CSVs locais e não consulta BigQuery diretamente. A camada Streamlit está em `dash_vendas_python_streamlit_publicacao/`. A página IA Analista carrega, sob demanda, as cinco fontes analíticas definidas em `ia_analista/analytics.py`. O dashboard não está hospedado. O módulo `ia_analista/llm.py` envia ao Gemini somente a pergunta atual e o envelope estruturado do motor; não envia CSVs nem histórico completo da conversa.

## 4. SQL e dados

- Consultas SQL 01 a 18 estão publicadas em `sql/`.
- SQL 10: base diária de valor dos itens.
- SQL 11: auditoria de maturidade/cobertura temporal.
- SQL 12: base de treinamento.
- SQL 14: média móvel de sete dias.
- SQL 15: dia da semana.
- SQL 16: calendário e feriados/datas relevantes.
- SQL 17: auditoria da cobertura da referência anual.
- SQL 18: feature de faturamento do ano anterior.

Base analítica exportada:
- arquivo: `base_treinamento_faturamento_teste.csv`;
- 606 linhas diárias;
- período: 01/01/2017 a 29/08/2018;
- quatro dias com target zero; nenhum target negativo ou nulo na auditoria registrada;
- `media_7d` possui sete NULLs iniciais por falta de histórico anterior.

Auditoria de chaves:
- 99.441 pedidos;
- nenhum `order_id` nulo ou duplicado na tabela de pedidos;
- nenhum par `(order_id, order_item_id)` nulo ou duplicado na tabela de itens;
- nenhum item sem pedido na auditoria executada.

Evitar JOIN com `order_payments` sem auditoria de cardinalidade, pois pode multiplicar linhas. Não alterar a definição da métrica sem revisar a documentação e as consultas.

## 5. Features e prevenção de vazamento

Features documentadas:
- `dia_semana`;
- `media_7d`;
- `faturamento_ano_anterior`, quando há cobertura;
- `eh_feriado_nacional`;
- `eh_data_movel`;
- `eh_data_comercial`.

`media_7d` usa os sete dias anteriores e nunca inclui o próprio dia previsto. Em previsão recursiva, atualiza-se com previsões anteriores, nunca com target real futuro.

## 6. Modelagem e resultados registrados

### Teste inicial: 01/07/2018 a 30/07/2018

| Métrica | Baseline | Random Forest |
|---|---:|---:|
| MAE | R$ 6.873,94 | R$ 6.390,11 |
| RMSE | R$ 8.368,83 | R$ 7.734,12 |
| WAPE | 25,05% | 23,29% |

### Validação temporal: cinco janelas de 30 dias

| Métrica agregada | Baseline | Random Forest |
|---|---:|---:|
| MAE | R$ 7.757,00 | R$ 6.966,16 |
| RMSE | R$ 9.539,33 | R$ 8.617,60 |
| WAPE | 25,27% | 22,70% |

Random Forest teve WAPE menor em três das cinco janelas, não em todas. A vantagem agregada não deve ser interpretada como garantia de desempenho futuro.

### Diagnóstico recente: 31/07/2018 a 29/08/2018

- WAPE Random Forest: 36,39%.
- WAPE baseline: 38,67%.
- Houve queda acentuada no volume/valor diário observado no fim de agosto.
- A causa da queda não foi comprovada. Não atribuir definitivamente a maturidade, falha de coleta ou mudança real de demanda.

## 7. Corte e previsão ativa de 30 dias

A análise de sensibilidade comparou a média dos sete dias encerrados na data de corte com a média dos 28 dias anteriores:
- 20/08: variação de -4,77%;
- 22/08: -23,26%;
- 24/08: -38,59%;
- 26/08: -50,89%;
- 29/08: -77,32%.

20/08/2018 foi escolhido como corte provisório mais prudente para a simulação. É uma decisão descritiva, não uma detecção estatística definitiva de ponto de mudança.

Arquivos:
- script ativo: `24_previsao_30_dias_corte_20_08.py`;
- CSV ativo no dashboard: `24_previsao_30_dias_corte_20_08.csv`;
- script e CSV anteriores de corte 22/08 permanecem preservados (versão 23).

Configuração e resultado:
- treinamento até 20/08/2018;
- 597 observações históricas até o corte;
- 590 linhas utilizáveis para treinamento após remover os sete valores iniciais sem `media_7d`;
- horizonte: 21/08/2018 a 19/09/2018, 30 dias;
- baseline constante: R$ 34.137,47 por dia;
- total Random Forest: R$ 993.231,78;
- total baseline: R$ 1.024.124,10.

O CSV foi auditado: 30 datas únicas e consecutivas, sem datas ausentes, previsões nulas ou valores negativos. Dia da semana confere com a data. Referência anual está disponível apenas de 21 a 29/08, conforme limite de cobertura adotado. 07/09/2018 está marcado como feriado nacional.

**Reprodução confirmada:** reexecução do script 24 com a base CSV e o script do modelo reproduziu exatamente os valores do CSV 24, inclusive as 30 previsões e os totais.

O arquivo de previsão não contém faturamento realizado para o horizonte. Portanto, não calcular nem alegar MAE, RMSE ou WAPE para os 30 dias previstos.

## 8. Dashboard

- Tecnologia: Streamlit, pandas, NumPy, Plotly e scikit-learn.
- Arquivo principal: `dash_vendas_python_streamlit_publicacao/app.py`.
- Lê seis CSVs locais.
- CSV de previsão ativo: `24_previsao_30_dias_corte_20_08.csv`.
- Página Previsão 30 dias conferida visualmente após atualizar o clone local; corte, datas, totais e gráfico aparecem corretamente.
- Instalação e execução foram validadas em clone limpo com Python 3.14.2.
- O dashboard não lê diretamente do BigQuery e não está publicado na nuvem.

Comando Windows, a partir da pasta `dash_vendas_python_streamlit_publicacao`:
```cmd
.venv\Scripts\python.exe -m streamlit run app.py
```

## 9. Regras de continuidade

- Preservar a arquitetura atual.
- Não refatorar nem alterar SQL, tabelas, colunas, funções ou bibliotecas sem pedido explícito.
- Não mudar a granularidade (uma linha por dia) nem a definição do target sem registrar a decisão.
- Verificar cardinalidade e duplicações em JOINs.
- Distinguir observações, hipóteses e causalidade.
- Não afirmar precisão da previsão de 30 dias sem realizado futuro para comparação.
- Usar dados públicos/autorizados; não incluir dados corporativos confidenciais.
- Ao retomar, consultar este arquivo e o README antes de qualquer alteração.

## 10. IA Analista: motor determinístico funcional e integração generativa não validada

A camada determinística da IA Analista está integrada ao dashboard e validada nas sete intenções do MVP. A integração generativa com Gemini foi implementada, mas não foi validada por indisponibilidade reportada pelo provedor; por decisão da usuária, não haverá novas tentativas nesta versão. O escopo entregue deve ser descrito sem afirmar que a interpretação generativa está operacional.

### Catálogo de intenções

Documento: [docs/catalogo_intencoes_ia_analista.md](docs/catalogo_intencoes_ia_analista.md).

O MVP tem sete intenções:
1. evolução do indicador;
2. comparação entre períodos/ano anterior;
3. padrão por dia da semana;
4. calendário e feriados;
5. diagnóstico de queda/aumento, sem afirmar causalidade;
6. consulta da previsão simulada;
7. desempenho e comparação dos modelos.

Perguntas por estado/cidade, produto/categoria, cliente ou forma de pagamento estão fora do escopo inicial, pois a base diária atual não possui essas dimensões.

### Motor analítico determinístico

**Implementado e publicado:** `dash_vendas_python_streamlit_publicacao/ia_analista/analytics.py`.

Funções:
- `analisar_evolucao`;
- `comparar_periodos`;
- `analisar_dia_semana`;
- `analisar_calendario`;
- `diagnosticar_variacao`;
- `consultar_previsao_30_dias`;
- `avaliar_modelos`;
- `executar_intencao`, dispatcher explícito para intenções cadastradas.

O motor lê os CSVs locais existentes e retorna fatos em contrato estruturado:
`status`, `intent`, `metric`, `period`, `facts`, `coverage`, `limitations`.

Status previstos: `ok`, `partial_data`, `insufficient_data`, `out_of_scope`. Períodos sem cobertura são sinalizados; referências anuais nulas não são substituídas por zero; a previsão simulada não recebe métricas de erro sem realizado.

**Testes já executados localmente:** `tests/test_analytics.py`, `tests/test_router.py` e `tests/test_app_syntax.py` somam 29 testes, todos aprovados com `DeprecationWarning` tratado como erro. Foram adicionados seis testes simulados em `tests/test_llm.py`; eles ainda precisam ser executados localmente. A suíte completa esperada agora é de 35 testes, sem necessidade de chave nem chamadas pagas para os testes simulados.

**Roteador determinístico implementado:** `dash_vendas_python_streamlit_publicacao/ia_analista/router.py`.

Funções:
- `route_question`: classifica texto em português por regras explícitas, identifica período e valida parâmetros;
- `executar_pergunta`: encaminha uma pergunta classificada ao motor analítico e devolve o resultado estruturado.

Regras já cobertas: datas em DD/MM/AAAA e AAAA-MM-DD; mês/ano por extenso; semestre e ano; pedido de esclarecimento quando falta período obrigatório; detecção de pergunta ambígua com mais de uma intenção; rejeição de perguntas por estado/cidade, produto/categoria, cliente ou pagamento; status de roteamento `ready`, `ambiguous`, `invalid` e `out_of_scope`.

Testes do roteador: `tests/test_router.py`, 14 testes. A suíte combinada passou com **28 testes**. A execução local foi feita com `python -W error::DeprecationWarning -m unittest discover -s tests -v`, sem warnings de depreciação após corrigir o uso de `pd.Timedelta` com unidade explícita.

**Interface conversacional integrada e validada localmente:** a página `IA Analista` usa `st.chat_input` e `st.chat_message`, carrega as fontes analíticas apenas quando acessada, mantém o histórico durante a sessão do Streamlit e permite limpar a conversa. As sete intenções do MVP foram exercitadas manualmente no dashboard e uma pergunta por estado foi corretamente recusada por ausência da dimensão geográfica. Os seis painéis originais permanecem no menu.

**Integração Gemini implementada, mas não validada remotamente devido a indisponibilidade do provedor:** `ia_analista/llm.py` usa o SDK oficial `google-genai` e o modelo `gemini-3.8-flash`. O LLM recebe a pergunta atual e apenas os campos `status`, `intent`, `metric`, `period`, `facts`, `coverage` e `limitations`, além de eventuais limitações do roteamento. Não recebe CSVs, DataFrames, histórico completo, ferramentas ou acesso a SQL. A saída é JSON com resumo, pontos-chave e cuidados; algarismos são rejeitados na narrativa para manter os números exclusivamente nos componentes calculados pelo Python. Se não houver chave ou a chamada falhar, a interface mantém os resultados determinísticos.

**Credenciais e seleção do modelo:** `GEMINI_API_KEY` e `GEMINI_MODEL` ficam em `.streamlit/secrets.toml` local ou variáveis de ambiente. O `.gitignore` exclui `.streamlit/secrets.toml` e `.env`. O `app.py` lê `GEMINI_MODEL` por `st.secrets`/ambiente e encaminha o valor ao `interpretar_resultado`; portanto, é possível trocar o modelo sem editar `app.py` ou `ia_analista/llm.py`. No Windows, abrir o arquivo com `notepad .streamlit\\secrets.toml`, editar somente a linha `GEMINI_MODEL`, salvar com `Ctrl + S` e reiniciar o Streamlit para aplicar. Nunca publicar nem compartilhar a chave.

**Provedor escolhido:** Gemini Developer API (Google AI Studio), em vez de Vertex AI nesta primeira versão, pela configuração mais simples para um portfólio local. SDK: `google-genai`. Modelo: `gemini-3.8-flash`. A decisão do projeto é usar exclusivamente o nível gratuito, sem configurar ou vincular faturamento e sem qualquer compromisso de upgrade. A tabela oficial lista entrada e saída de tokens sem custo para `gemini-3.8-flash` no nível gratuito, sujeito aos limites de uso e à disponibilidade da conta. O Google informa que o conteúdo desse nível pode ser usado para melhorar seus produtos. Como o projeto usa a base pública Olist, enviar somente a pergunta atual e fatos agregados autorizados; não incluir dados pessoais, confidenciais ou segredos. Se a interface exigir faturamento, cartão, upgrade ou indicar cobrança, interromper a configuração e manter o modo determinístico.

**Observação de UX pendente:** no teste de diagnóstico formulado como queda (01/08 a 20/08/2018), o acumulado comparado foi positivo em 16,03%, embora houvesse quedas em dias isolados. A tela exibe os números e as maiores quedas, mas a interpretação textual deve explicitar que não houve queda no acumulado e separar o resultado agregado dos dias individuais.

### Fluxo arquitetural desejado

```text
Pergunta do usuário
    -> identificação/roteamento da intenção
    -> validação de parâmetros
    -> função analítica determinística (Python/SQL)
    -> validação e estruturação dos fatos
    -> envio somente dos resultados relevantes ao LLM
    -> interpretação e resposta em linguagem natural
```

Regras:
- O LLM não calcula métricas por conta própria nem recebe automaticamente toda a base.
- Valores, comparações, agregações e indicadores devem ser calculados por SQL/Python de forma reproduzível.
- Entregar ao LLM somente fatos estruturados necessários à pergunta, incluindo período, filtros, definições e limitações.
- A resposta deve distinguir dado observado, inferência e hipótese.
- Intenções desconhecidas, períodos sem cobertura ou perguntas sem dados suficientes devem receber respostas explícitas, sem inventar números.
- Não executar SQL gerada livremente pelo LLM.

### Próximas etapas da IA

1. [x] Fechar o catálogo de intenções e exemplos de perguntas.
2. [x] Implementar funções analíticas determinísticas em Python e resultados estruturados.
3. [x] Implementar roteador por regras explícitas e validação de parâmetros, sem LLM.
4. [x] Escolher Gemini Developer API e modelo `gemini-3.8-flash`; configurar credenciais fora do Git.
5. [x] Implementar chamada opcional ao LLM somente para interpretar o envelope de fatos estruturados, sem acesso à base, histórico integral, ferramentas ou SQL.
6. [x] Implementar a primeira interface conversacional determinística no Streamlit, com histórico de sessão e carregamento sob demanda.
7. [x] Validar manualmente no dashboard as sete intenções do MVP e uma pergunta por estado fora do escopo; números exibidos conferem com os resultados automatizados.
   - [ ] Validar também casos de borda na interface: pergunta ambígua/inválida, ausência de CSV, cobertura parcial e limpeza da conversa.
   - [ ] Melhorar a apresentação textual do diagnóstico para distinguir crescimento acumulado de quedas diárias.
8. [x] Implementar a integração opcional com Gemini e documentar arquitetura, segurança, custos/limites e configuração.
9. [ ] Executar os seis novos testes simulados do LLM e validar localmente uma chamada real com chave própria; revisar o fallback sem chave. A primeira tentativa real foi feita em 24/11/2026 e retornou `503 UNAVAILABLE` (mensagem do provedor: modelo temporariamente com alta demanda); não houve resposta do modelo.

**Próxima tarefa:** reabrir o dashboard e fazer uma única chamada controlada com `gemini-3.5-flash-lite`, selecionado em `.streamlit/secrets.toml`. Se falhar, não repetir. Em seguida, executar os seis testes simulados do LLM e a suíte completa; testar fallback sem chave/erro, limites de escopo e perguntas ambíguas; melhorar a comunicação do diagnóstico; revisar os READMEs no GitHub; preparar o post do LinkedIn e fazer a conferência final. Não habilitar billing, não adicionar cartão e não executar SQL livre gerada pelo modelo.

**Critério de conclusão:** o usuário consegue fazer as perguntas do MVP no dashboard e recebe respostas em linguagem natural ancoradas em resultados determinísticos, com período, métrica e limitações claros.

## 11. Encerramento e expansões opcionais

A fundação analítica/preditiva, o dashboard local e o motor determinístico estão concluídos. O **Projeto Dash Vendas como solução Dados + IA permanece em andamento até a entrega e validação da IA Analista conversacional**.

Depois da IA funcional, podem ser avaliadas como expansões opcionais: publicar/hospedar o dashboard, conectar atualização operacional de dados ao BigQuery, incluir dimensões adicionais com auditoria e avaliar inferência local/WebGPU. Essas expansões não são pré-requisitos para concluir o MVP da IA Analista.


## 12. Continuidade e encerramento do portfólio (24/11/2026)

### Diagnóstico da primeira chamada real ao Gemini

- A chave foi configurada localmente em `.streamlit/secrets.toml`.
- O arquivo foi confirmado como ignorado pelo Git com `git check-ignore .streamlit/secrets.toml`; não deve ser publicado.
- O dashboard Streamlit iniciou normalmente e os indicadores determinísticos do Python foram exibidos.
- Uma chamada de teste direta ao modelo `gemini-3.8-flash` retornou `503 UNAVAILABLE`, com mensagem do provedor indicando alta demanda temporária ("This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again later.").
- O painel de uso do AI Studio exibiu nível gratuito, 1 solicitação, 686 tokens de entrada, 0 tokens de saída e 1 erro 503. O painel de limites exibiu 1/5 RPM, 686/250K TPM e 1/20 RPD. Esses números são a evidência visual apresentada pela usuária; não indicam cota excedida.
- Interpretação atual: a chamada alcançou o serviço e falhou por indisponibilidade temporária reportada pelo provedor. Não há evidência, até aqui, de chave inválida ou limite excedido. A integração não foi validada com uma resposta válida. A usuária decidiu não realizar novas tentativas.
- Conduta: aguardar antes de uma nova tentativa; não habilitar faturamento, não adicionar cartão e não repetir chamadas em sequência. Se persistir a indisponibilidade, preservar o modo determinístico gratuito e reavaliar sem custos.

### Pendências para declarar o Projeto Dash Vendas concluído

1. [ ] Fazer uma nova tentativa controlada ao Gemini e confirmar uma resposta válida, sem cobrança.
2. [ ] Executar os seis testes simulados de `tests/test_llm.py` e conferir a suíte completa esperada de 35 testes.
3. [ ] Concluir os testes de borda da IA Analista: pergunta ambígua/inválida, ausência de CSV, cobertura parcial, limpeza da conversa e fallback sem chave/erro.
4. [ ] Melhorar a apresentação textual do diagnóstico, separando variação acumulada e quedas diárias.
5. [ ] Fazer revisão final do README no GitHub: conferir arquitetura, resultados, limitações, status real de cada etapa, comandos de execução, configuração segura da chave e descrição da IA. Não marcar como concluído o que ainda não foi validado.
6. [ ] Preparar e publicar o post do LinkedIn, apresentando problema, dados públicos Olist, arquitetura Dados + IA, decisões de segurança, resultados e limitações de forma verdadeira e adequada ao portfólio.
7. [ ] Fazer uma conferência final do repositório e declarar o Dash Vendas encerrado somente depois dos itens aplicáveis acima.

**Ordem combinada:** nova tentativa controlada do Gemini → validações técnicas e casos de borda → revisão/atualização do README no GitHub → criação do post do LinkedIn → checklist final de encerramento → migração do foco para os outros projetos.

Não iniciar os outros projetos como prioridade principal antes dessa revisão final, salvo solicitação expressa da usuária.


## 13. Resultado final da tentativa Gemini e decisão de encerramento (24/11/2026)

### Segunda e última execução manual do teste

A usuária executou a segunda tentativa manual de validação real, conforme combinado como última tentativa. O traceback terminou em:

`google.genai.errors.ServerError: 503 UNAVAILABLE`

Mensagem retornada pelo provedor:

`This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again later.`

A execução anterior já havia retornado o mesmo código e mensagem. Portanto:
- duas execuções manuais de teste foram feitas;
- as duas falharam com 503 por alta demanda reportada pelo provedor;
- nenhuma resposta textual do modelo foi obtida;
- não há evidência nos logs apresentados de chave inválida ou de cota excedida;
- o painel do AI Studio anteriormente mostrou o nível gratuito e uso abaixo dos limites exibidos;
- a integração Gemini permanece implementada no código, mas **não pode ser descrita como validada em produção nem como funcionando em chamada real**.

### Decisão registrada inicialmente e atualização posterior

A decisão inicial após as duas respostas 503 foi encerrar as tentativas. Em uma conversa posterior, a usuária reconsiderou essa decisão e autorizou **uma única tentativa adicional**, trocando o modelo pelo arquivo local de configuração. A autorização posterior prevalece somente para essa tentativa controlada; caso falhe, não haverá nova chamada.

- Não realizar chamadas repetidas nem tentar novamente o `gemini-3.8-flash`.
- Não fazer outras chamadas de teste.
- Não configurar faturamento, não adicionar cartão e não realizar upgrade.
- Preservar a interface conversacional, o roteador e o motor analítico determinístico, que continuam sendo a via funcional do dashboard.
- Registrar Gemini como integração opcional implementada, porém não validada por indisponibilidade externa do modelo.
- Encerrar o projeto de portfólio com a limitação explícita, após concluir a revisão documental e a apresentação pública.

### Plano final acordado

1. [ ] Executar os seis testes simulados do LLM e a suíte completa de testes, incluindo o fallback sem chamada real.
2. [ ] Concluir os testes de borda relevantes e o ajuste de comunicação do diagnóstico (acumulado versus variações diárias).
3. [ ] Revisar o README no GitHub, corrigindo o status desatualizado da chave e da validação Gemini, confirmando arquitetura, resultados, limitações e instruções.
4. [ ] Criar o post do LinkedIn com descrição fiel: IA Analista determinística funcional; integração Gemini desenvolvida, mas não validada em chamadas reais devido a duas respostas 503 do provedor; sem billing e sem cartão.
5. [ ] Fazer a conferência final e considerar o Dash Vendas encerrado nesta versão.
6. [ ] Depois, migrar o foco para os demais projetos.

**Critério de comunicação pública:** nunca afirmar que a Gemini respondeu com sucesso, que a integração remota foi validada ou que a IA generativa está operacional. É correto dizer que a integração foi implementada e que sua validação real foi bloqueada pela indisponibilidade 503 do provedor. Não ocultar que a IA Analista mantém a camada determinística em funcionamento.


## 14. Configuração editável do modelo Gemini pelo Bloco de Notas (24/11/2026)

### Decisão de configuração

O nome do modelo da camada LLM deve permanecer configurável fora do código para facilitar testes controlados e futuras substituições, sem exigir alteração em Python.

- Arquivo local: `dash_vendas_python_streamlit_publicacao/.streamlit/secrets.toml`.
- Campos: `GEMINI_API_KEY` e `GEMINI_MODEL`.
- A chave permanece privada no arquivo local e o `.gitignore` impede seu versionamento.
- O `app.py` lê `GEMINI_MODEL` via `st.secrets` (ou variável de ambiente) e passa esse valor a `interpretar_resultado` em `ia_analista/llm.py`.
- Para alterar o modelo, abrir o arquivo pelo CMD com `notepad .streamlit\\secrets.toml`, trocar somente o valor de `GEMINI_MODEL`, salvar e reiniciar o Streamlit. Não modificar `app.py` nem `llm.py` para uma simples troca de identificador.
- O identificador selecionado localmente para a tentativa atual é `gemini-3.5-flash-lite`. A chave real não deve ser copiada para a documentação do GitHub.

### Modelo alternativo selecionado

A documentação oficial do Google lista o ID `gemini-3.5-flash-lite` e descreve o modelo como voltado a tarefas de alto volume e processamento simples. A página oficial de preços lista entrada e saída sem custo no nível gratuito, sujeitas à disponibilidade e aos limites de uso da conta. Isso não garante disponibilidade para esta conta nem sucesso da próxima chamada. Referências: [modelos](https://ai.google.dev/gemini-api/docs/models) e [preços](https://ai.google.dev/gemini-api/docs/pricing).

As duas tentativas anteriores com `gemini-3.8-flash` retornaram `503 UNAVAILABLE` por alta demanda. A usuária autorizou uma única tentativa final com `gemini-3.5-flash-lite`. Caso falhe, não haverá nova chamada nesta versão. Não habilitar billing, não adicionar cartão e não fazer upgrade.
