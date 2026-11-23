"""Motor analítico determinístico da IA Analista do Projeto Dash Vendas.

Este módulo calcula fatos a partir dos CSVs locais. Não chama LLM, não gera SQL
livre e não tenta inferir dimensões que não existem na base diária.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]

ARQUIVOS = {
    "base_diaria": "base_treinamento_faturamento_teste.csv",
    "teste_inicial": "20_previsoes_random_forest_teste.csv",
    "validacao_temporal": "21_resultado_validacao_temporal.csv",
    "janela_recente": "22_resultado_janela_recente.csv",
    "previsao_30_dias": "24_previsao_30_dias_corte_20_08.csv",
}

COLUNAS_BASE = {
    "data",
    "faturamento_diario",
    "faturamento_ano_anterior",
    "dia_semana",
    "qtd_pedidos_entregues",
    "qtd_linhas_itens_entregues",
    "eh_feriado_nacional",
    "eh_data_movel",
    "eh_data_comercial",
}
COLUNAS_PREVISAO = {"data", "previsao_random_forest", "previsao_baseline"}
COLUNAS_TESTE = {"data", "faturamento_real", "previsao_random_forest", "previsao_baseline"}
ORDEM_DIAS = [
    "segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
    "sexta-feira", "sábado", "domingo",
]
COLUNAS_CALENDARIO = {
    "feriado_nacional": "eh_feriado_nacional",
    "data_movel": "eh_data_movel",
    "data_comercial": "eh_data_comercial",
}


def _data(valor: Any, nome: str) -> pd.Timestamp:
    data = pd.to_datetime(valor, errors="coerce")
    if pd.isna(data):
        raise ValueError(f"{nome} inválida: {valor!r}.")
    return pd.Timestamp(data).normalize()


def _periodo(data_inicio: Any, data_fim: Any) -> tuple[pd.Timestamp, pd.Timestamp]:
    inicio = _data(data_inicio, "data_inicio")
    fim = _data(data_fim, "data_fim")
    if inicio > fim:
        raise ValueError("data_inicio não pode ser posterior a data_fim.")
    return inicio, fim


def _normalizar_flag(coluna: pd.Series, nome: str) -> pd.Series:
    if pd.api.types.is_bool_dtype(coluna):
        return coluna.astype("boolean")
    mapa = {
        "true": True, "false": False, "1": True, "0": False,
        "sim": True, "não": False, "nao": False,
    }
    convertido = coluna.astype("string").str.strip().str.lower().map(mapa)
    invalidos = coluna.notna() & convertido.isna()
    if invalidos.any():
        exemplos = coluna.loc[invalidos].astype(str).unique().tolist()[:5]
        raise ValueError(f"Valores inválidos na coluna {nome}: {exemplos}.")
    return convertido.astype("boolean")


def preparar_base_diaria(df: pd.DataFrame) -> pd.DataFrame:
    """Valida o esquema mínimo e prepara uma cópia da base diária."""
    if not isinstance(df, pd.DataFrame):
        raise TypeError("A base diária precisa ser um pandas.DataFrame.")
    ausentes = COLUNAS_BASE.difference(df.columns)
    if ausentes:
        raise ValueError("Colunas obrigatórias ausentes na base diária: " + ", ".join(sorted(ausentes)))

    base = df.copy()
    base["data"] = pd.to_datetime(base["data"], errors="coerce").dt.normalize()
    if base["data"].isna().any():
        raise ValueError("A base diária contém datas nulas ou inválidas.")
    if base["data"].duplicated().any():
        duplicadas = base.loc[base["data"].duplicated(keep=False), "data"].dt.strftime("%Y-%m-%d")
        raise ValueError("A base diária contém datas duplicadas: " + ", ".join(duplicadas.head(10)))

    for coluna in [
        "faturamento_diario", "faturamento_ano_anterior",
        "qtd_pedidos_entregues", "qtd_linhas_itens_entregues",
    ]:
        base[coluna] = pd.to_numeric(base[coluna], errors="coerce")
    if base["faturamento_diario"].isna().any():
        raise ValueError("faturamento_diario contém NULL ou valor não numérico.")
    if (base["faturamento_diario"] < 0).any():
        raise ValueError("faturamento_diario contém valores negativos.")

    for coluna in COLUNAS_CALENDARIO.values():
        base[coluna] = _normalizar_flag(base[coluna], coluna)

    if base["dia_semana"].isna().any():
        raise ValueError("dia_semana contém valores nulos.")
    dias_invalidos = sorted(set(base["dia_semana"].astype(str)) - set(ORDEM_DIAS))
    if dias_invalidos:
        raise ValueError("Valores inesperados em dia_semana: " + ", ".join(dias_invalidos))

    return base.sort_values("data").reset_index(drop=True)


def carregar_fontes(pasta_dados: str | Path | None = None) -> dict[str, pd.DataFrame]:
    """Carrega os CSVs usados no MVP. Por padrão, usa a pasta desta aplicação."""
    pasta = Path(pasta_dados) if pasta_dados is not None else BASE_DIR
    fontes: dict[str, pd.DataFrame] = {}
    for chave, nome in ARQUIVOS.items():
        caminho = pasta / nome
        if not caminho.is_file():
            raise FileNotFoundError(f"Fonte obrigatória não encontrada: {caminho}")
        fontes[chave] = pd.read_csv(caminho)

    fontes["base_diaria"] = preparar_base_diaria(fontes["base_diaria"])
    for chave in ["teste_inicial", "janela_recente"]:
        df = fontes[chave].copy()
        faltantes = COLUNAS_TESTE.difference(df.columns)
        if faltantes:
            raise ValueError(f"Colunas ausentes em {ARQUIVOS[chave]}: " + ", ".join(sorted(faltantes)))
        df["data"] = pd.to_datetime(df["data"], errors="coerce").dt.normalize()
        for coluna in ["faturamento_real", "previsao_random_forest", "previsao_baseline"]:
            df[coluna] = pd.to_numeric(df[coluna], errors="coerce")
        fontes[chave] = df.sort_values("data").reset_index(drop=True)

    previsao = fontes["previsao_30_dias"].copy()
    faltantes = COLUNAS_PREVISAO.difference(previsao.columns)
    if faltantes:
        raise ValueError("Colunas ausentes na previsão de 30 dias: " + ", ".join(sorted(faltantes)))
    previsao["data"] = pd.to_datetime(previsao["data"], errors="coerce").dt.normalize()
    for coluna in ["previsao_random_forest", "previsao_baseline"]:
        previsao[coluna] = pd.to_numeric(previsao[coluna], errors="coerce")
    fontes["previsao_30_dias"] = previsao.sort_values("data").reset_index(drop=True)

    validacao = fontes["validacao_temporal"].copy()
    obrigatorias_validacao = {
        "tipo_resultado", "inicio_teste", "fim_teste", "wape_random_forest_pct",
        "wape_baseline_pct", "diferenca_wape_pontos_pct",
    }
    faltantes = obrigatorias_validacao.difference(validacao.columns)
    if faltantes:
        raise ValueError("Colunas ausentes na validação temporal: " + ", ".join(sorted(faltantes)))
    for coluna in ["inicio_teste", "fim_teste"]:
        validacao[coluna] = pd.to_datetime(validacao[coluna], errors="coerce").dt.normalize()
    for coluna in ["wape_random_forest_pct", "wape_baseline_pct", "diferenca_wape_pontos_pct"]:
        validacao[coluna] = pd.to_numeric(validacao[coluna], errors="coerce")
    fontes["validacao_temporal"] = validacao
    return fontes


def _recorte_periodo(base: pd.DataFrame, inicio: pd.Timestamp, fim: pd.Timestamp) -> tuple[pd.DataFrame, dict[str, int]]:
    recorte = base.loc[base["data"].between(inicio, fim)].copy()
    dias_solicitados = len(pd.date_range(inicio, fim, freq="D"))
    datas_disponiveis = set(recorte["data"].tolist())
    dias_faltantes = sum(dia not in datas_disponiveis for dia in pd.date_range(inicio, fim, freq="D"))
    cobertura = {
        "dias_solicitados": int(dias_solicitados),
        "dias_disponiveis": int(recorte["data"].nunique()),
        "dias_faltantes": int(dias_faltantes),
        "linhas_utilizadas": int(len(recorte)),
    }
    return recorte, cobertura


def _resumo_valor(df: pd.DataFrame, coluna: str = "faturamento_diario") -> dict[str, Any]:
    valores = pd.to_numeric(df[coluna], errors="coerce").dropna()
    if valores.empty:
        return {"total": None, "media_diaria": None, "mediana_diaria": None, "minimo": None, "maximo": None, "dias_com_valor": 0}
    idx_min = valores.idxmin()
    idx_max = valores.idxmax()
    return {
        "total": round(float(valores.sum()), 2),
        "media_diaria": round(float(valores.mean()), 2),
        "mediana_diaria": round(float(valores.median()), 2),
        "minimo": round(float(valores.min()), 2),
        "maximo": round(float(valores.max()), 2),
        "dias_com_valor": int(valores.size),
        "data_minimo": pd.Timestamp(df.loc[idx_min, "data"]).strftime("%Y-%m-%d") if "data" in df else None,
        "data_maximo": pd.Timestamp(df.loc[idx_max, "data"]).strftime("%Y-%m-%d") if "data" in df else None,
    }


def _status_cobertura(cobertura: dict[str, int], linhas_validas: int) -> str:
    if linhas_validas == 0:
        return "insufficient_data"
    if cobertura["dias_faltantes"] > 0 or linhas_validas < cobertura["dias_solicitados"]:
        return "partial_data"
    return "ok"


def _envelope(intent: str, metric: str, inicio: pd.Timestamp, fim: pd.Timestamp,
              facts: dict[str, Any], coverage: dict[str, Any], status: str,
              limitations: list[str] | None = None) -> dict[str, Any]:
    return {
        "status": status,
        "intent": intent,
        "metric": {
            "name": metric,
            "definition": "Soma de price dos itens associados a pedidos cujo status atual é delivered, por data da compra, sem frete.",
        },
        "period": {"start_date": inicio.strftime("%Y-%m-%d"), "end_date": fim.strftime("%Y-%m-%d")},
        "facts": facts,
        "coverage": coverage,
        "limitations": limitations or [],
    }


def analisar_evolucao(base_diaria: pd.DataFrame, data_inicio: Any, data_fim: Any,
                      incluir_serie: bool = False) -> dict[str, Any]:
    """INT-01: totais, médias, extremos e opcionalmente série diária."""
    base = preparar_base_diaria(base_diaria)
    inicio, fim = _periodo(data_inicio, data_fim)
    recorte, cobertura = _recorte_periodo(base, inicio, fim)
    resumo = _resumo_valor(recorte)
    status = _status_cobertura(cobertura, resumo["dias_com_valor"])
    facts: dict[str, Any] = dict(resumo)
    facts["dias_com_valor_zero"] = int(recorte["faturamento_diario"].eq(0).sum())
    if incluir_serie:
        facts["serie_diaria"] = [
            {"data": row.data.strftime("%Y-%m-%d"), "valor": round(float(row.faturamento_diario), 2)}
            for row in recorte[["data", "faturamento_diario"]].itertuples(index=False)
        ]
    return _envelope("period_evolution", "faturamento_diario", inicio, fim, facts, cobertura, status)


def comparar_periodos(base_diaria: pd.DataFrame, data_inicio: Any, data_fim: Any,
                      tipo_comparacao: str = "ano_anterior") -> dict[str, Any]:
    """INT-02: compara mesmo período do ano anterior ou período anterior equivalente."""
    base = preparar_base_diaria(base_diaria)
    inicio, fim = _periodo(data_inicio, data_fim)
    atual, cobertura_atual = _recorte_periodo(base, inicio, fim)

    if tipo_comparacao == "ano_anterior":
        comparador = atual[["data", "faturamento_diario", "faturamento_ano_anterior"]].copy()
        comparador["faturamento_ano_anterior"] = pd.to_numeric(comparador["faturamento_ano_anterior"], errors="coerce")
        pares = comparador.dropna(subset=["faturamento_diario", "faturamento_ano_anterior"])
        comp_inicio, comp_fim = inicio - pd.DateOffset(years=1), fim - pd.DateOffset(years=1)
        tipo = "mesmo_periodo_ano_anterior"
        coluna_comp = "faturamento_ano_anterior"
    elif tipo_comparacao == "periodo_anterior":
        quantidade_dias = len(pd.date_range(inicio, fim, freq="D"))
        comp_inicio = inicio - pd.Timedelta(value=int(quantidade_dias), unit="D")
        comp_fim = inicio - pd.Timedelta(value=1, unit="D")
        anterior, cobertura_anterior = _recorte_periodo(base, comp_inicio, comp_fim)
        pares = pd.DataFrame()
        tipo = "periodo_anterior_equivalente"
        coluna_comp = "faturamento_diario"
    else:
        raise ValueError("tipo_comparacao deve ser 'ano_anterior' ou 'periodo_anterior'.")

    if tipo_comparacao == "ano_anterior":
        atual_total = float(pares["faturamento_diario"].sum()) if not pares.empty else 0.0
        comparador_total = float(pares[coluna_comp].sum()) if not pares.empty else 0.0
        quantidade_pares = int(len(pares))
        cobertura = {
            **cobertura_atual,
            "pares_comparaveis": quantidade_pares,
            "dias_sem_referencia_anual": int(len(atual) - quantidade_pares),
        }
        dias_faltantes = cobertura_atual["dias_faltantes"]
        status = "insufficient_data" if quantidade_pares == 0 else ("partial_data" if dias_faltantes or quantidade_pares < cobertura_atual["dias_solicitados"] else "ok")
    else:
        atual_validos = atual.dropna(subset=["faturamento_diario"])
        anterior_validos = anterior.dropna(subset=["faturamento_diario"])
        atual_total = float(atual_validos["faturamento_diario"].sum())
        comparador_total = float(anterior_validos["faturamento_diario"].sum())
        quantidade_pares = min(len(atual_validos), len(anterior_validos))
        cobertura = {
            "dias_solicitados_por_periodo": int(len(pd.date_range(inicio, fim, freq="D"))),
            "dias_disponiveis_periodo_atual": int(len(atual_validos)),
            "dias_disponiveis_periodo_comparacao": int(len(anterior_validos)),
            "dias_faltantes_periodo_atual": cobertura_atual["dias_faltantes"],
            "dias_faltantes_periodo_comparacao": cobertura_anterior["dias_faltantes"],
        }
        status = "insufficient_data" if not len(atual_validos) or not len(anterior_validos) else (
            "partial_data" if cobertura_atual["dias_faltantes"] or cobertura_anterior["dias_faltantes"] else "ok"
        )

    diferenca = atual_total - comparador_total
    variacao_pct = (diferenca / abs(comparador_total) * 100) if comparador_total != 0 else None
    facts = {
        "tipo_comparacao": tipo,
        "total_periodo_atual_pares_comparaveis": round(atual_total, 2),
        "total_periodo_comparacao": round(comparador_total, 2),
        "diferenca_absoluta": round(diferenca, 2),
        "variacao_percentual": round(variacao_pct, 2) if variacao_pct is not None else None,
        "dias_comparaveis": int(quantidade_pares),
        "data_inicio_comparacao": comp_inicio.strftime("%Y-%m-%d"),
        "data_fim_comparacao": comp_fim.strftime("%Y-%m-%d"),
    }
    limites = []
    if status == "partial_data":
        limites.append("Comparação parcial: nem todos os dias possuem observações válidas nos dois períodos.")
    if variacao_pct is None:
        limites.append("Não foi possível calcular variação percentual porque o total do período de comparação é zero.")
    return _envelope("period_comparison", "faturamento_diario", inicio, fim, facts, cobertura, status, limites)


def analisar_dia_semana(base_diaria: pd.DataFrame, data_inicio: Any, data_fim: Any) -> dict[str, Any]:
    """INT-03: estatísticas por dia da semana, ordenadas pela média diária."""
    base = preparar_base_diaria(base_diaria)
    inicio, fim = _periodo(data_inicio, data_fim)
    recorte, cobertura = _recorte_periodo(base, inicio, fim)
    linhas = []
    for dia in ORDEM_DIAS:
        grupo = recorte.loc[recorte["dia_semana"].eq(dia), "faturamento_diario"].dropna()
        if grupo.empty:
            continue
        linhas.append({
            "dia_semana": dia,
            "dias_observados": int(len(grupo)),
            "total": round(float(grupo.sum()), 2),
            "media_diaria": round(float(grupo.mean()), 2),
            "mediana_diaria": round(float(grupo.median()), 2),
        })
    ordenados = sorted(linhas, key=lambda item: item["media_diaria"], reverse=True)
    status = _status_cobertura(cobertura, len(recorte))
    return _envelope(
        "weekday_pattern", "faturamento_diario", inicio, fim,
        {"por_dia_semana": linhas, "ranking_por_media_diaria": ordenados,
         "maior_media": ordenados[0] if ordenados else None,
         "menor_media": ordenados[-1] if ordenados else None},
        cobertura, status,
        ["Padrão descritivo; não demonstra que o dia da semana cause a diferença."],
    )


def analisar_calendario(base_diaria: pd.DataFrame, data_inicio: Any, data_fim: Any,
                        categoria: str = "feriado_nacional") -> dict[str, Any]:
    """INT-04: compara dias sinalizados e não sinalizados por uma flag de calendário."""
    if categoria not in COLUNAS_CALENDARIO:
        raise ValueError("categoria deve ser feriado_nacional, data_movel ou data_comercial.")
    base = preparar_base_diaria(base_diaria)
    inicio, fim = _periodo(data_inicio, data_fim)
    recorte, cobertura = _recorte_periodo(base, inicio, fim)
    coluna = COLUNAS_CALENDARIO[categoria]
    conhecidos = recorte.dropna(subset=[coluna]).copy()
    grupos: dict[str, Any] = {}
    for nome, mascara in [("sinalizado", conhecidos[coluna].eq(True)), ("nao_sinalizado", conhecidos[coluna].eq(False))]:
        grupo = conhecidos.loc[mascara]
        grupos[nome] = {
            "dias_observados": int(len(grupo)),
            "total": round(float(grupo["faturamento_diario"].sum()), 2) if not grupo.empty else None,
            "media_diaria": round(float(grupo["faturamento_diario"].mean()), 2) if not grupo.empty else None,
            "mediana_diaria": round(float(grupo["faturamento_diario"].median()), 2) if not grupo.empty else None,
        }
    cobertura["dias_com_flag_desconhecida"] = int(len(recorte) - len(conhecidos))
    status = "insufficient_data" if grupos["sinalizado"]["dias_observados"] == 0 else _status_cobertura(cobertura, len(conhecidos))
    return _envelope(
        "calendar_analysis", "faturamento_diario", inicio, fim,
        {"categoria": categoria, "comparacao": grupos}, cobertura, status,
        ["Comparação descritiva. Não atribuir causalidade ao feriado, data móvel ou data comercial.",
         "Sempre considerar a quantidade de dias observados em cada grupo."],
    )


def diagnosticar_variacao(base_diaria: pd.DataFrame, data_inicio: Any, data_fim: Any,
                          comparacao_inicio: Any | None = None,
                          comparacao_fim: Any | None = None) -> dict[str, Any]:
    """INT-05: compara períodos equivalentes e identifica maiores diferenças diárias."""
    base = preparar_base_diaria(base_diaria)
    inicio, fim = _periodo(data_inicio, data_fim)
    if (comparacao_inicio is None) != (comparacao_fim is None):
        raise ValueError("Informe comparacao_inicio e comparacao_fim juntos.")
    quantidade_dias = len(pd.date_range(inicio, fim, freq="D"))
    if comparacao_inicio is None:
        comp_inicio = inicio - pd.Timedelta(value=int(quantidade_dias), unit="D")
        comp_fim = inicio - pd.Timedelta(value=1, unit="D")
    else:
        comp_inicio, comp_fim = _periodo(comparacao_inicio, comparacao_fim)
        if len(pd.date_range(comp_inicio, comp_fim, freq="D")) != quantidade_dias:
            raise ValueError("Os períodos precisam ter a mesma quantidade de dias para o diagnóstico diário.")

    atual, cov_atual = _recorte_periodo(base, inicio, fim)
    anterior, cov_anterior = _recorte_periodo(base, comp_inicio, comp_fim)
    resumo_atual = _resumo_valor(atual)
    resumo_anterior = _resumo_valor(anterior)

    atual_cols = ["data", "faturamento_diario", "qtd_pedidos_entregues", "qtd_linhas_itens_entregues"]
    anterior_cols = ["data", "faturamento_diario"]
    atual_alinhado = atual[atual_cols].copy()
    anterior_alinhado = anterior[anterior_cols].copy()
    anterior_alinhado["data"] = anterior_alinhado["data"] + pd.Timedelta(value=int(quantidade_dias), unit="D")
    anterior_alinhado = anterior_alinhado.rename(columns={"faturamento_diario": "faturamento_comparacao"})
    pareado = atual_alinhado.merge(anterior_alinhado, on="data", how="inner")
    pareado["diferenca_diaria"] = pareado["faturamento_diario"] - pareado["faturamento_comparacao"]
    maiores_altas = pareado.nlargest(5, "diferenca_diaria")
    maiores_quedas = pareado.nsmallest(5, "diferenca_diaria")

    total_atual = resumo_atual["total"]
    total_anterior = resumo_anterior["total"]
    total_atual_pareado = float(pareado["faturamento_diario"].sum()) if not pareado.empty else None
    total_comparacao_pareado = float(pareado["faturamento_comparacao"].sum()) if not pareado.empty else None
    diferenca_total = (total_atual_pareado - total_comparacao_pareado) if not pareado.empty else None
    variacao_pct = (diferenca_total / abs(total_comparacao_pareado) * 100) if diferenca_total is not None and total_comparacao_pareado not in (None, 0) else None
    pedidos_atual = pd.to_numeric(atual["qtd_pedidos_entregues"], errors="coerce").sum(min_count=1)
    pedidos_anterior = pd.to_numeric(anterior["qtd_pedidos_entregues"], errors="coerce").sum(min_count=1)
    itens_atual = pd.to_numeric(atual["qtd_linhas_itens_entregues"], errors="coerce").sum(min_count=1)
    itens_anterior = pd.to_numeric(anterior["qtd_linhas_itens_entregues"], errors="coerce").sum(min_count=1)

    def lista_dias(df: pd.DataFrame) -> list[dict[str, Any]]:
        return [{
            "data": row.data.strftime("%Y-%m-%d"),
            "faturamento_atual": round(float(row.faturamento_diario), 2),
            "faturamento_comparacao": round(float(row.faturamento_comparacao), 2),
            "diferenca": round(float(row.diferenca_diaria), 2),
        } for row in df.itertuples(index=False)]

    cobertura = {
        "dias_solicitados_por_periodo": int(quantidade_dias),
        "dias_disponiveis_periodo_atual": cov_atual["dias_disponiveis"],
        "dias_disponiveis_periodo_comparacao": cov_anterior["dias_disponiveis"],
        "dias_pareados": int(len(pareado)),
        "dias_faltantes_periodo_atual": cov_atual["dias_faltantes"],
        "dias_faltantes_periodo_comparacao": cov_anterior["dias_faltantes"],
    }
    status = "insufficient_data" if pareado.empty else ("partial_data" if len(pareado) < quantidade_dias else "ok")
    facts = {
        "periodo_atual": resumo_atual,
        "periodo_comparacao": resumo_anterior,
        "total_periodo_atual_pareado": round(total_atual_pareado, 2) if total_atual_pareado is not None else None,
        "total_periodo_comparacao_pareado": round(total_comparacao_pareado, 2) if total_comparacao_pareado is not None else None,
        "variacao_total": round(diferenca_total, 2) if diferenca_total is not None else None,
        "variacao_percentual": round(variacao_pct, 2) if variacao_pct is not None else None,
        "pedidos_delivered_atual": int(pedidos_atual) if pd.notna(pedidos_atual) else None,
        "pedidos_delivered_comparacao": int(pedidos_anterior) if pd.notna(pedidos_anterior) else None,
        "linhas_itens_atual": int(itens_atual) if pd.notna(itens_atual) else None,
        "linhas_itens_comparacao": int(itens_anterior) if pd.notna(itens_anterior) else None,
        "valor_medio_por_pedido_atual": round(total_atual / pedidos_atual, 2) if total_atual is not None and pd.notna(pedidos_atual) and pedidos_atual > 0 else None,
        "valor_medio_por_pedido_comparacao": round(total_anterior / pedidos_anterior, 2) if total_anterior is not None and pd.notna(pedidos_anterior) and pedidos_anterior > 0 else None,
        "maiores_altas_diarias": lista_dias(maiores_altas),
        "maiores_quedas_diarias": lista_dias(maiores_quedas),
    }
    limitations = [
        "Diagnóstico descritivo: as diferenças identificam onde investigar, mas não comprovam a causa da variação.",
        "A métrica usa o status atual delivered e pode refletir cobertura/maturidade incompleta na cauda histórica.",
        "A base diária não contém dimensões de estado, cidade, produto, categoria ou cliente.",
    ]
    return _envelope("change_diagnosis", "faturamento_diario", inicio, fim, facts, cobertura, status, limitations)


def consultar_previsao_30_dias(fontes: dict[str, pd.DataFrame]) -> dict[str, Any]:
    """INT-06: resume a previsão simulada publicada, sem métricas de erro."""
    if "previsao_30_dias" not in fontes:
        raise ValueError("Fonte 'previsao_30_dias' não foi carregada.")
    df = fontes["previsao_30_dias"].copy()
    faltantes = COLUNAS_PREVISAO.difference(df.columns)
    if faltantes:
        raise ValueError("Colunas ausentes na previsão: " + ", ".join(sorted(faltantes)))
    df["data"] = pd.to_datetime(df["data"], errors="coerce").dt.normalize()
    for coluna in ["previsao_random_forest", "previsao_baseline"]:
        df[coluna] = pd.to_numeric(df[coluna], errors="coerce")
    if df["data"].isna().any() or df["data"].duplicated().any():
        raise ValueError("A previsão possui datas inválidas ou duplicadas.")
    if df[["previsao_random_forest", "previsao_baseline"]].isna().any().any():
        raise ValueError("A previsão contém valores nulos.")
    if (df[["previsao_random_forest", "previsao_baseline"]] < 0).any().any():
        raise ValueError("A previsão contém valores negativos.")
    df = df.sort_values("data").reset_index(drop=True)
    datas_esperadas = pd.date_range(df["data"].min(), df["data"].max(), freq="D")
    if len(df) != 30 or not df["data"].reset_index(drop=True).equals(pd.Series(datas_esperadas, name="data")):
        raise ValueError("A previsão ativa deve conter 30 datas diárias consecutivas.")

    rf = df["previsao_random_forest"]
    baseline = df["previsao_baseline"]
    total_rf = float(rf.sum())
    total_baseline = float(baseline.sum())
    diferenca = total_rf - total_baseline
    rf_top = df.nlargest(5, "previsao_random_forest")
    rf_bottom = df.nsmallest(5, "previsao_random_forest")
    facts = {
        "modelo": "Random Forest",
        "total_random_forest": round(total_rf, 2),
        "total_baseline": round(total_baseline, 2),
        "media_diaria_random_forest": round(float(rf.mean()), 2),
        "media_diaria_baseline": round(float(baseline.mean()), 2),
        "diferenca_rf_menos_baseline": round(diferenca, 2),
        "diferenca_percentual_sobre_baseline": round(diferenca / total_baseline * 100, 2) if total_baseline else None,
        "maiores_previsoes_rf": [{"data": row.data.strftime("%Y-%m-%d"), "valor": round(float(row.previsao_random_forest), 2)} for row in rf_top.itertuples(index=False)],
        "menores_previsoes_rf": [{"data": row.data.strftime("%Y-%m-%d"), "valor": round(float(row.previsao_random_forest), 2)} for row in rf_bottom.itertuples(index=False)],
        "quantidade_dias": int(len(df)),
        "tipo_previsao": "simulacao_retrospectiva",
        "corte_treinamento": "2018-08-20",
    }
    return {
        "status": "ok",
        "intent": "forecast_summary",
        "metric": {"name": "previsao_random_forest", "definition": "Simulação retrospectiva de 30 dias; corte em 20/08/2018."},
        "period": {"start_date": df["data"].min().strftime("%Y-%m-%d"), "end_date": df["data"].max().strftime("%Y-%m-%d")},
        "facts": facts,
        "coverage": {"dias_solicitados": 30, "dias_disponiveis": 30, "dias_faltantes": 0, "linhas_utilizadas": 30},
        "limitations": [
            "É uma simulação retrospectiva histórica, não uma previsão para o mercado atual.",
            "O CSV não contém faturamento realizado maduro; não há MAE, RMSE ou WAPE para este horizonte.",
        ],
    }


def _metricas_modelo(df: pd.DataFrame, coluna_real: str, coluna_prevista: str) -> dict[str, Any]:
    valores = df[[coluna_real, coluna_prevista]].apply(pd.to_numeric, errors="coerce").dropna()
    if valores.empty:
        return {"mae": None, "rmse": None, "wape_pct": None, "n": 0}
    erro = valores[coluna_real] - valores[coluna_prevista]
    soma_real = float(valores[coluna_real].abs().sum())
    wape = float(erro.abs().sum() / soma_real * 100) if soma_real else None
    return {
        "mae": round(float(erro.abs().mean()), 2),
        "rmse": round(float(np.sqrt(np.square(erro).mean())), 2),
        "wape_pct": round(wape, 2) if wape is not None else None,
        "n": int(len(valores)),
    }


def avaliar_modelos(fontes: dict[str, pd.DataFrame]) -> dict[str, Any]:
    """INT-07: compara teste inicial, cinco janelas e diagnóstico recente separadamente."""
    obrigatorias = ["teste_inicial", "validacao_temporal", "janela_recente"]
    ausentes = [chave for chave in obrigatorias if chave not in fontes]
    if ausentes:
        raise ValueError("Fontes ausentes para avaliar modelos: " + ", ".join(ausentes))

    def avaliar_teste(chave: str) -> dict[str, Any]:
        df = fontes[chave].copy()
        m_rf = _metricas_modelo(df, "faturamento_real", "previsao_random_forest")
        m_base = _metricas_modelo(df, "faturamento_real", "previsao_baseline")
        datas = pd.to_datetime(df["data"], errors="coerce").dropna()
        return {
            "periodo": {"inicio": datas.min().strftime("%Y-%m-%d"), "fim": datas.max().strftime("%Y-%m-%d")} if not datas.empty else None,
            "random_forest": m_rf,
            "baseline": m_base,
            "diferenca_wape_pontos_percentuais": round(m_rf["wape_pct"] - m_base["wape_pct"], 2) if m_rf["wape_pct"] is not None and m_base["wape_pct"] is not None else None,
        }

    validacao = fontes["validacao_temporal"].copy()
    janelas = validacao.loc[validacao["tipo_resultado"].eq("janela")].copy()
    agregado = validacao.loc[validacao["tipo_resultado"].eq("agregado_5_janelas")]
    if janelas.empty or agregado.empty:
        raise ValueError("A validação temporal precisa conter linhas 'janela' e 'agregado_5_janelas'.")
    wins_rf = int((janelas["wape_random_forest_pct"] < janelas["wape_baseline_pct"]).sum())
    linha_agregada = agregado.iloc[0]
    resumo_validacao = {
        "quantidade_janelas": int(len(janelas)),
        "janelas_vencidas_random_forest": wins_rf,
        "wape_agregado_random_forest_pct": round(float(linha_agregada["wape_random_forest_pct"]), 2),
        "wape_agregado_baseline_pct": round(float(linha_agregada["wape_baseline_pct"]), 2),
        "diferenca_wape_agregada_pontos_percentuais": round(float(linha_agregada["diferenca_wape_pontos_pct"]), 2),
        "por_janela": [{
            "inicio": row.inicio_teste.strftime("%Y-%m-%d"),
            "fim": row.fim_teste.strftime("%Y-%m-%d"),
            "wape_random_forest_pct": round(float(row.wape_random_forest_pct), 2),
            "wape_baseline_pct": round(float(row.wape_baseline_pct), 2),
            "vencedor": "Random Forest" if row.wape_random_forest_pct < row.wape_baseline_pct else ("Baseline" if row.wape_baseline_pct < row.wape_random_forest_pct else "Empate"),
        } for row in janelas.itertuples(index=False)],
    }
    return {
        "status": "ok",
        "intent": "model_performance",
        "metric": {"name": "MAE, RMSE e WAPE", "definition": "Métricas calculadas sobre previsões com faturamento realizado disponível. WAPE = soma dos erros absolutos / soma do realizado em módulo."},
        "period": None,
        "facts": {
            "teste_inicial_julho": avaliar_teste("teste_inicial"),
            "validacao_temporal_5_janelas": resumo_validacao,
            "diagnostico_janela_recente": avaliar_teste("janela_recente"),
        },
        "coverage": {
            "linhas_teste_inicial": int(len(fontes["teste_inicial"])),
            "janelas_temporais": int(len(janelas)),
            "linhas_diagnostico_recente": int(len(fontes["janela_recente"])),
        },
        "limitations": [
            "O teste inicial, as cinco janelas e a janela recente são avaliações separadas e não devem ser somadas como um único teste.",
            "O Random Forest não venceu todas as janelas temporais.",
            "Resultados históricos não garantem desempenho futuro.",
        ],
    }


def executar_intencao(intent: str, fontes: dict[str, pd.DataFrame], parametros: dict[str, Any]) -> dict[str, Any]:
    """Dispatcher explícito do catálogo; não interpreta linguagem natural."""
    base = fontes.get("base_diaria")
    if intent == "period_evolution":
        return analisar_evolucao(base, parametros["data_inicio"], parametros["data_fim"], parametros.get("incluir_serie", False))
    if intent == "period_comparison":
        return comparar_periodos(base, parametros["data_inicio"], parametros["data_fim"], parametros.get("tipo_comparacao", "ano_anterior"))
    if intent == "weekday_pattern":
        return analisar_dia_semana(base, parametros["data_inicio"], parametros["data_fim"])
    if intent == "calendar_analysis":
        return analisar_calendario(base, parametros["data_inicio"], parametros["data_fim"], parametros.get("categoria", "feriado_nacional"))
    if intent == "change_diagnosis":
        return diagnosticar_variacao(base, parametros["data_inicio"], parametros["data_fim"], parametros.get("comparacao_inicio"), parametros.get("comparacao_fim"))
    if intent == "forecast_summary":
        return consultar_previsao_30_dias(fontes)
    if intent == "model_performance":
        return avaliar_modelos(fontes)
    return {
        "status": "out_of_scope",
        "intent": intent,
        "metric": None,
        "period": None,
        "facts": {},
        "coverage": {},
        "limitations": ["Intenção não cadastrada no catálogo da IA Analista."],
    }
