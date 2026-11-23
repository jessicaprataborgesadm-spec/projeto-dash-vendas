"""Roteador determinístico de perguntas para a IA Analista.

Classifica perguntas em português por regras explícitas, extrai períodos simples
e valida parâmetros. Não usa LLM, não executa SQL livre e não inventa dimensões.
"""
from __future__ import annotations

import re
import unicodedata
from calendar import monthrange
from datetime import date
from typing import Any

import pandas as pd

from ia_analista.analytics import executar_intencao

MESES = {
    "janeiro": 1, "jan": 1,
    "fevereiro": 2, "fev": 2,
    "marco": 3, "mar": 3,
    "abril": 4, "abr": 4,
    "maio": 5, "mai": 5,
    "junho": 6, "jun": 6,
    "julho": 7, "jul": 7,
    "agosto": 8, "ago": 8,
    "setembro": 9, "set": 9,
    "outubro": 10, "out": 10,
    "novembro": 11, "nov": 11,
    "dezembro": 12, "dez": 12,
}

# A prioridade evita que palavras genéricas, como "faturamento", escondam
# intenções mais específicas, como previsão, comparação ou calendário.
PADROES_INTENCAO = {
    "model_performance": [
        r"\brandom\s*forest\b", r"\bbaseline\b", r"\bwape\b", r"\bmae\b", r"\brmse\b",
        r"\bdesempenho\b", r"\bperformance\b", r"\bmodelos?\b", r"\bvenceu\b",
    ],
    "forecast_summary": [
        r"\bprevis[aã]o\b", r"\bprever\b", r"\bprevisto\b", r"\bproje[cç][aã]o\b",
        r"\bpr[oó]ximos?\s+(?:30|trinta)\s+dias\b",
    ],
    "change_diagnosis": [
        r"\bqueda\b", r"\bcaiu\b", r"\bredu[cç][aã]o\b", r"\breduziu\b", r"\baumentou\b",
        r"\bcresceu\b", r"\bvaria[cç][aã]o\b", r"\bmudou\b", r"\bmudan[cç]a\b",
        r"\bpor\s+que\b.*\b(?:faturamento|vendas|valor)\b",
    ],
    "calendar_analysis": [
        r"\bferiados?\b", r"\bcalend[aá]rio\b", r"\bdatas?\s+comerciais?\b",
        r"\bdatas?\s+m[oó]veis?\b", r"\bblack\s+friday\b", r"\bnatal\b", r"\bdia das m[aã]es\b",
    ],
    "weekday_pattern": [
        r"\bdia(?:s)?\s+da\s+semana\b", r"\bsegunda-feira\b", r"\bter[cç]a-feira\b",
        r"\bquarta-feira\b", r"\bquinta-feira\b", r"\bsexta-feira\b", r"\bs[aá]bado\b", r"\bdomingo\b",
    ],
    "period_comparison": [
        r"\bcompar(?:a|ar|e|ativo|ação|acao)\b", r"\bversus\b", r"\bvs\.?\b",
        r"\bano anterior\b", r"\bmesmo per[ií]odo\b", r"\bem rela[cç][aã]o\b",
    ],
}

PADROES_FORA_ESCOPO = [
    r"\bpor estado\b", r"\bem cada estado\b", r"\bqual estado\b", r"\bpor cidade\b",
    r"\bem cada cidade\b", r"\bqual cidade\b", r"\bpor produto\b", r"\bquais produtos\b",
    r"\bpor categoria\b", r"\bqual categoria\b", r"\bpor cliente\b", r"\bquais clientes\b",
    r"\bforma[s]? de pagamento\b", r"\bpor pagamento\b",
]

PADRAO_DATA_ISO = re.compile(r"\b(20\d{2})-(\d{1,2})-(\d{1,2})\b")
PADRAO_DATA_BR = re.compile(r"\b(\d{1,2})/(\d{1,2})/(20\d{2})\b")
PADRAO_MES_ANO = re.compile(
    r"\b(janeiro|jan|fevereiro|fev|mar[cç]o|mar|abril|abr|maio|mai|junho|jun|julho|jul|agosto|ago|"
    r"setembro|set|outubro|out|novembro|nov|dezembro|dez)\s*(?:de\s*|/\s*)?(20\d{2})\b",
    re.IGNORECASE,
)
PADRAO_ANO = re.compile(r"\b(2017|2018)\b")
PADRAO_SEMESTRE = re.compile(r"\b(primeiro|1[oº]?|segundo|2[oº]?)\s+semestre\s+(?:de\s+)?(20\d{2})\b", re.IGNORECASE)


def _normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto.casefold())
    return "".join(ch for ch in texto if not unicodedata.combining(ch))


def _mes_nome(nome: str) -> int:
    return MESES[_normalizar(nome)]


def _extrair_periodo(pergunta: str) -> tuple[date, date] | None:
    """Extrai período explícito: datas, mês/ano, semestre ou ano completo."""
    datas: list[date] = []
    invalid_date_found = False

    for match in PADRAO_DATA_ISO.finditer(pergunta):
        try:
            datas.append(date(int(match.group(1)), int(match.group(2)), int(match.group(3))))
        except ValueError:
            invalid_date_found = True
    for match in PADRAO_DATA_BR.finditer(pergunta):
        try:
            datas.append(date(int(match.group(3)), int(match.group(2)), int(match.group(1))))
        except ValueError:
            invalid_date_found = True

    if invalid_date_found:
        raise ValueError("A pergunta contém uma data inválida. Confira dia, mês e ano.")
    if len(datas) > 2:
        raise ValueError("Encontrei mais de duas datas. Informe apenas o início e o fim do período.")
    if len(datas) == 2:
        if datas[0] > datas[1]:
            raise ValueError("A data inicial é posterior à data final.")
        return datas[0], datas[1]
    if len(datas) == 1:
        return datas[0], datas[0]

    semestres = list(PADRAO_SEMESTRE.finditer(_normalizar(pergunta)))
    if semestres:
        match = semestres[-1]
        termo, ano_txt = match.groups()
        ano = int(ano_txt)
        segundo = termo.startswith("segundo") or termo.startswith("2")
        return (date(ano, 7, 1), date(ano, 12, 31)) if segundo else (date(ano, 1, 1), date(ano, 6, 30))

    meses = list(PADRAO_MES_ANO.finditer(pergunta))
    if meses:
        periodos = []
        for match in meses:
            mes, ano_txt = match.groups()
            mes_num = _mes_nome(mes)
            ano = int(ano_txt)
            periodos.append((ano, mes_num))
        # Em uma comparação explícita entre o mesmo mês de anos diferentes,
        # considera o ano mais recente como período principal.
        anos_meses_unicos = sorted(set(periodos))
        if len(anos_meses_unicos) > 1 and len({mes for _, mes in anos_meses_unicos}) == 1:
            ano, mes = anos_meses_unicos[-1]
        else:
            ano, mes = anos_meses_unicos[0]
        return date(ano, mes, 1), date(ano, mes, monthrange(ano, mes)[1])

    anos = list(PADRAO_ANO.finditer(pergunta))
    if anos:
        ano = int(anos[0].group(1))
        return date(ano, 1, 1), date(ano, 12, 31)
    return None


def _detectar_intencoes(pergunta_normalizada: str) -> list[str]:
    encontradas = []
    for intent, padroes in PADROES_INTENCAO.items():
        if any(re.search(padrao, pergunta_normalizada) for padrao in padroes):
            encontradas.append(intent)

    # INT-01 é o fallback para perguntas gerais sobre a métrica. Só é usado
    # quando nenhuma intenção mais específica foi identificada.
    if not encontradas and re.search(
        r"\bfaturamento\b|\bvendas\b|\bevolu[cç][aã]o\b|\bquanto\s+vendeu\b|\bm[eé]dia\s+di[aá]ria\b|\btotal\b",
        pergunta_normalizada,
    ):
        encontradas.append("period_evolution")
    return encontradas


def _resultado(status: str, question: str, intent: str | None = None,
               parameters: dict[str, Any] | None = None, clarification: str | None = None,
               limitations: list[str] | None = None) -> dict[str, Any]:
    return {
        "status": status,
        "question": question,
        "intent": intent,
        "parameters": parameters or {},
        "clarification": clarification,
        "limitations": limitations or [],
    }


def route_question(question: str, fontes: dict[str, pd.DataFrame]) -> dict[str, Any]:
    """Classifica uma pergunta em português e valida os parâmetros extraídos.

    Status de roteamento: ready, ambiguous, invalid, out_of_scope.
    """
    if not isinstance(question, str) or not question.strip():
        return _resultado("invalid", str(question), clarification="Envie uma pergunta em texto.")

    original = question.strip()
    normalizada = _normalizar(original)

    if any(re.search(padrao, normalizada) for padrao in PADROES_FORA_ESCOPO):
        return _resultado(
            "out_of_scope", original,
            clarification=(
                "A base diária atual não contém as dimensões solicitadas. "
                "O MVP responde sobre períodos, dias da semana, calendário, previsão e modelos."
            ),
            limitations=["Análises por estado/cidade, produto/categoria, cliente ou pagamento exigem novas fontes e auditoria."],
        )

    intencoes = _detectar_intencoes(normalizada)
    if not intencoes:
        return _resultado(
            "out_of_scope", original,
            clarification="Não identifiquei uma das sete intenções do MVP. Reformule a pergunta usando um tema do catálogo.",
        )
    if len(intencoes) > 1:
        nomes = ", ".join(intencoes)
        return _resultado(
            "ambiguous", original,
            clarification=f"Sua pergunta mistura mais de um tipo de análise ({nomes}). Qual deles você quer priorizar?",
            limitations=["O roteador não combina duas intenções em uma única consulta."],
        )

    intent = intencoes[0]
    try:
        periodo = _extrair_periodo(original)
    except ValueError as exc:
        return _resultado("invalid", original, intent=intent, clarification=str(exc))

    parametros: dict[str, Any] = {}
    avisos: list[str] = []
    intents_com_periodo_obrigatorio = {
        "period_evolution", "period_comparison", "change_diagnosis",
    }

    if intent in intents_com_periodo_obrigatorio and periodo is None:
        return _resultado(
            "ambiguous", original, intent=intent,
            clarification="Informe o período da análise. Pode usar, por exemplo, 'julho de 2018' ou '01/07/2018 a 30/07/2018'.",
        )

    if periodo is not None and intent in {
        "period_evolution", "period_comparison", "weekday_pattern", "calendar_analysis", "change_diagnosis",
    }:
        parametros["data_inicio"] = periodo[0].isoformat()
        parametros["data_fim"] = periodo[1].isoformat()
    elif intent in {"weekday_pattern", "calendar_analysis"}:
        base = fontes.get("base_diaria") if fontes else None
        if base is None or base.empty:
            return _resultado("invalid", original, intent=intent, clarification="Não foi possível obter a cobertura temporal da base diária.")
        datas = pd.to_datetime(base["data"], errors="coerce").dropna()
        if datas.empty:
            return _resultado("invalid", original, intent=intent, clarification="A base não possui datas válidas.")
        parametros["data_inicio"] = datas.min().date().isoformat()
        parametros["data_fim"] = datas.max().date().isoformat()
        avisos.append("Como nenhum período foi informado, foi usada toda a cobertura disponível da base diária.")

    if intent == "period_comparison":
        parametros["tipo_comparacao"] = (
            "periodo_anterior" if re.search(r"\bper[ií]odo anterior\b|\bm[eê]s anterior\b|\bm[eê]s passado\b", normalizada)
            else "ano_anterior"
        )
    elif intent == "calendar_analysis":
        if re.search(r"\bdatas?\s+comerciais?\b|\bblack\s+friday\b", normalizada):
            parametros["categoria"] = "data_comercial"
        elif re.search(r"\bdatas?\s+m[oó]veis?\b", normalizada):
            parametros["categoria"] = "data_movel"
        else:
            parametros["categoria"] = "feriado_nacional"

    if "data_inicio" in parametros and parametros["data_inicio"] > parametros["data_fim"]:
        return _resultado("invalid", original, intent=intent, clarification="A data inicial precisa ser anterior ou igual à data final.")

    return _resultado("ready", original, intent=intent, parameters=parametros, limitations=avisos)


def executar_pergunta(question: str, fontes: dict[str, pd.DataFrame]) -> dict[str, Any]:
    """Roteia a pergunta e executa o motor determinístico quando os parâmetros estão prontos."""
    rota = route_question(question, fontes)
    if rota["status"] != "ready":
        return rota
    try:
        resultado = executar_intencao(rota["intent"], fontes, rota["parameters"])
    except (KeyError, TypeError, ValueError) as exc:
        return {
            **rota,
            "status": "invalid",
            "clarification": f"Não foi possível executar a análise com os parâmetros informados: {exc}",
        }
    return {
        "status": resultado["status"],
        "question": rota["question"],
        "intent": rota["intent"],
        "parameters": rota["parameters"],
        "clarification": None,
        "routing_limitations": rota["limitations"],
        "result": resultado,
    }
