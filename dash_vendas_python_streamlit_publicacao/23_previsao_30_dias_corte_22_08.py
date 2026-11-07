"""Gera uma previsão simulada de 30 dias usando corte provisório em 22/08/2018.

Projeto Dash Vendas | Olist

Objetivo:
- Treinar o Random Forest somente com datas até 22/08/2018.
- Prever recursivamente de 23/08/2018 a 21/09/2018.
- Comparar as previsões com um baseline constante baseado nos sete dias
  anteriores ao corte.
- Não usar o faturamento real das datas previstas como feature ou avaliação.

Cuidados metodológicos:
- O target permanece faturamento_diario, conforme a definição já aprovada.
- A previsão é uma simulação histórica, não uma previsão do faturamento atual.
- faturamento_ano_anterior só é usado até 29/08/2018, limite da cobertura
  considerado utilizável na auditoria anterior. Depois disso, fica NULL e o
  pipeline existente faz a imputação aprendida no treinamento.
- Para 07/09/2018, preserva-se a flag de feriado nacional já documentada na SQL 16.

Entrada padrão: base_treinamento_faturamento_teste.csv
Script do modelo: 20_modelo_random_forest_teste.py
Saída padrão: 23_previsao_30_dias_corte_22_08.csv
"""
from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd

CORTE_TREINAMENTO = pd.Timestamp("2018-08-22")
DIAS_PREVISAO = 30
DIAS_MEDIA = 7
ULTIMA_DATA_REFERENCIA_ANUAL_CONFIAVEL = pd.Timestamp("2018-08-29")

DIAS_SEMANA_PT = {
    0: "segunda-feira",
    1: "terça-feira",
    2: "quarta-feira",
    3: "quinta-feira",
    4: "sexta-feira",
    5: "sábado",
    6: "domingo",
}


def carregar_modulo_modelo(caminho: Path):
    if not caminho.is_file():
        raise FileNotFoundError(
            f"Script do modelo não encontrado: {caminho}. "
            "Coloque 20_modelo_random_forest_teste.py na mesma pasta."
        )
    spec = importlib.util.spec_from_file_location("modelo_rf_corte_22_08", caminho)
    if spec is None or spec.loader is None:
        raise ImportError(f"Não foi possível carregar o script do modelo: {caminho}")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def construir_features_futuras(
    data: pd.Timestamp,
    base_por_data: pd.DataFrame,
) -> dict[str, object]:
    """Cria features conhecidas na data de previsão, sem consultar target futuro."""
    if data in base_por_data.index:
        linha = base_por_data.loc[data]
        faturamento_ano_anterior = np.nan
        # A auditoria prévia considerou utilizável a referência anual somente
        # até 29/08/2018. Para 23-29/08, usar a feature já validada na SQL 18.
        if data <= ULTIMA_DATA_REFERENCIA_ANUAL_CONFIAVEL:
            faturamento_ano_anterior = pd.to_numeric(
                pd.Series([linha["faturamento_ano_anterior"]]), errors="coerce"
            ).iloc[0]
        flags = {
            "eh_feriado_nacional": int(linha["eh_feriado_nacional"]),
            "eh_data_movel": int(linha["eh_data_movel"]),
            "eh_data_comercial": int(linha["eh_data_comercial"]),
        }
    else:
        # O calendário da SQL 16 lista as datas relevantes de 2018. No horizonte
        # 30 dias iniciado em 23/08, o evento listado é o feriado de 07/09.
        faturamento_ano_anterior = np.nan
        flags = {
            "eh_feriado_nacional": int(data == pd.Timestamp("2018-09-07")),
            "eh_data_movel": 0,
            "eh_data_comercial": 0,
        }

    return {
        "dia_semana": DIAS_SEMANA_PT[data.dayofweek],
        "faturamento_ano_anterior": faturamento_ano_anterior,
        "media_7d": np.nan,  # preenchida recursivamente antes de cada previsão
        **flags,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prevê 30 dias com Random Forest usando corte de 22/08/2018."
    )
    parser.add_argument(
        "arquivo_csv",
        nargs="?",
        default="base_treinamento_faturamento_teste.csv",
        help="CSV diário derivado da SQL 18.",
    )
    parser.add_argument(
        "--modelo",
        default="20_modelo_random_forest_teste.py",
        help="Script existente do Random Forest.",
    )
    parser.add_argument(
        "--saida",
        default="23_previsao_30_dias_corte_22_08.csv",
        help="CSV de saída com as previsões diárias.",
    )
    args = parser.parse_args()

    caminho_csv = Path(args.arquivo_csv)
    modulo = carregar_modulo_modelo(Path(args.modelo))
    base = modulo.carregar_base(caminho_csv)

    historico = base[base["data"] <= CORTE_TREINAMENTO].copy()
    if historico.empty or historico["data"].max() != CORTE_TREINAMENTO:
        raise ValueError("A base precisa conter dados diários até 22/08/2018.")

    datas_previstas = pd.date_range(
        CORTE_TREINAMENTO + pd.Timedelta(days=1), periods=DIAS_PREVISAO, freq="D"
    )
    if len(historico) < DIAS_MEDIA:
        raise ValueError("Histórico insuficiente para calcular a média dos sete dias.")

    # Mesma pipeline e mesmas features do Random Forest já usado no projeto.
    treino_modelo = historico.dropna(subset=["media_7d"]).copy()
    if treino_modelo.empty:
        raise ValueError("Não há linhas com media_7d para treinar o modelo.")

    modelo = modulo.criar_modelo()
    modelo.fit(
        treino_modelo[modulo.COLUNAS_FEATURES],
        treino_modelo["faturamento_diario"],
    )

    base_por_data = base.set_index("data", drop=False)
    historico_previsto = historico["faturamento_diario"].astype(float).tolist()
    baseline_janela = historico[
        historico["data"].between(
            CORTE_TREINAMENTO - pd.Timedelta(days=DIAS_MEDIA - 1),
            CORTE_TREINAMENTO,
        )
    ]
    if len(baseline_janela) != DIAS_MEDIA:
        raise ValueError("Não há sete dias completos antes do corte para calcular o baseline.")
    previsao_baseline = float(baseline_janela["faturamento_diario"].mean())

    linhas_saida: list[dict[str, object]] = []
    for data in datas_previstas:
        features = construir_features_futuras(data, base_por_data)
        features["media_7d"] = float(np.mean(historico_previsto[-DIAS_MEDIA:]))
        entrada = pd.DataFrame([features], columns=modulo.COLUNAS_FEATURES)
        previsao_rf = max(0.0, float(modelo.predict(entrada)[0]))

        linhas_saida.append(
            {
                "data": data.strftime("%Y-%m-%d"),
                "dia_semana": features["dia_semana"],
                "faturamento_ano_anterior": features["faturamento_ano_anterior"],
                "eh_feriado_nacional": features["eh_feriado_nacional"],
                "eh_data_movel": features["eh_data_movel"],
                "eh_data_comercial": features["eh_data_comercial"],
                "media_7d_usada": round(float(features["media_7d"]), 2),
                "previsao_random_forest": round(previsao_rf, 2),
                "previsao_baseline": round(previsao_baseline, 2),
                "diferenca_rf_menos_baseline": round(previsao_rf - previsao_baseline, 2),
                "tipo_resultado": "previsao_simulada_sem_realizado_maduro",
            }
        )
        # Alimenta a média dos próximos dias apenas com o valor previsto.
        historico_previsto.append(previsao_rf)

    resultado = pd.DataFrame(linhas_saida)
    saida = Path(args.saida)
    resultado.to_csv(saida, index=False, float_format="%.2f")

    print("PREVISÃO SIMULADA DE 30 DIAS | CORTE PROVISÓRIO 22/08/2018")
    print(f"Treinamento até: {CORTE_TREINAMENTO:%d/%m/%Y}")
    print(f"Linhas usadas no treinamento: {len(treino_modelo)}")
    print(
        f"Período previsto: {datas_previstas.min():%d/%m/%Y} a "
        f"{datas_previstas.max():%d/%m/%Y} ({len(resultado)} dias)"
    )
    print(f"Baseline constante (média de {DIAS_MEDIA} dias): R$ {previsao_baseline:,.2f}")
    print(f"Total previsto pelo Random Forest: R$ {resultado['previsao_random_forest'].sum():,.2f}")
    print(f"Total previsto pelo baseline: R$ {resultado['previsao_baseline'].sum():,.2f}")
    print(f"Previsões salvas em: {saida.resolve()}")
    print("Não há faturamento realizado no arquivo de saída; não são calculadas métricas de erro.")
    print("Nota: previsão retrospectiva simulada; o corte de 22/08/2018 é provisório.")


if __name__ == "__main__":
    main()
