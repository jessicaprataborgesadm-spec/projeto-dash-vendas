"""Validação temporal por janelas de 30 dias: Random Forest vs. baseline.

Reutiliza o script 20_modelo_random_forest_teste.py, sem alterá-lo.
Cada janela é prevista usando somente dados anteriores ao seu início.
As previsões são recursivas: media_7d usa previsões anteriores dentro do horizonte,
sem consultar o faturamento real dos dias de teste.

Entradas padrão:
- base_treinamento_faturamento_teste.csv
- 20_modelo_random_forest_teste.py (na mesma pasta)

Saída padrão:
- 21_resultado_validacao_temporal.csv
"""
from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd

# Cinco janelas consecutivas de 30 dias. A primeira começa em 31/01/2018,
# para que o treino já contenha observações de faturamento_ano_anterior.
# O teste original de julho fica separado destas janelas.
DATAS_INICIO_JANELAS = [
    "2018-01-31",
    "2018-03-02",
    "2018-04-01",
    "2018-05-01",
    "2018-05-31",
]
DURACAO_TESTE_DIAS = 30


def carregar_modulo_modelo(caminho: Path):
    if not caminho.is_file():
        raise FileNotFoundError(
            f"Script do modelo não encontrado: {caminho}. "
            "Coloque 20_modelo_random_forest_teste.py na mesma pasta."
        )
    spec = importlib.util.spec_from_file_location("modelo_rf_teste", caminho)
    if spec is None or spec.loader is None:
        raise ImportError(f"Não foi possível carregar o script: {caminho}")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Valida baseline e Random Forest em várias janelas cronológicas de 30 dias."
    )
    parser.add_argument(
        "arquivo_csv",
        nargs="?",
        default="base_treinamento_faturamento_teste.csv",
        help="CSV da SQL 18 (padrão: base_treinamento_faturamento_teste.csv)",
    )
    parser.add_argument(
        "--modelo",
        default="20_modelo_random_forest_teste.py",
        help="Script do Random Forest já existente.",
    )
    parser.add_argument(
        "--saida",
        default="21_resultado_validacao_temporal.csv",
        help="CSV de saída com métricas por janela e resumo agregado.",
    )
    args = parser.parse_args()

    pasta = Path.cwd()
    modulo = carregar_modulo_modelo(Path(args.modelo))
    base = modulo.carregar_base(Path(args.arquivo_csv))

    linhas_metricas: list[dict] = []
    resultados_diarios: list[pd.DataFrame] = []

    for inicio_texto in DATAS_INICIO_JANELAS:
        inicio = pd.Timestamp(inicio_texto)
        fim = inicio + pd.Timedelta(days=DURACAO_TESTE_DIAS - 1)

        if fim > base["data"].max():
            raise ValueError(
                f"A janela {inicio:%Y-%m-%d} a {fim:%Y-%m-%d} excede a base disponível."
            )

        modulo.DATA_TESTE_INICIO = inicio
        modulo.DATA_TESTE_FIM = fim
        diarios, metricas, qtd_treino = modulo.treinar_e_prever(base)
        diarios = diarios.copy()
        diarios["janela_inicio"] = inicio.strftime("%Y-%m-%d")
        diarios["janela_fim"] = fim.strftime("%Y-%m-%d")
        resultados_diarios.append(diarios)

        rf = metricas["random_forest"]
        bl = metricas["baseline"]
        linhas_metricas.append({
            "tipo_resultado": "janela",
            "inicio_teste": inicio.strftime("%Y-%m-%d"),
            "fim_teste": fim.strftime("%Y-%m-%d"),
            "linhas_treinamento": qtd_treino,
            "mae_random_forest": round(rf["mae"], 2),
            "rmse_random_forest": round(rf["rmse"], 2),
            "wape_random_forest_pct": round(rf["wape_percentual"], 2),
            "mae_baseline": round(bl["mae"], 2),
            "rmse_baseline": round(bl["rmse"], 2),
            "wape_baseline_pct": round(bl["wape_percentual"], 2),
            "diferenca_wape_pontos_pct": round(
                rf["wape_percentual"] - bl["wape_percentual"], 2
            ),
        })

    diario_agregado = pd.concat(resultados_diarios, ignore_index=True)
    real = diario_agregado["faturamento_real"].to_numpy(dtype=float)
    rf_pred = diario_agregado["previsao_random_forest"].to_numpy(dtype=float)
    bl_pred = diario_agregado["previsao_baseline"].to_numpy(dtype=float)
    metricas_rf_total = modulo.calcular_metricas(real, rf_pred)
    metricas_bl_total = modulo.calcular_metricas(real, bl_pred)

    linhas_metricas.append({
        "tipo_resultado": "agregado_5_janelas",
        "inicio_teste": DATAS_INICIO_JANELAS[0],
        "fim_teste": (pd.Timestamp(DATAS_INICIO_JANELAS[-1]) + pd.Timedelta(days=29)).strftime("%Y-%m-%d"),
        "linhas_treinamento": np.nan,
        "mae_random_forest": round(metricas_rf_total["mae"], 2),
        "rmse_random_forest": round(metricas_rf_total["rmse"], 2),
        "wape_random_forest_pct": round(metricas_rf_total["wape_percentual"], 2),
        "mae_baseline": round(metricas_bl_total["mae"], 2),
        "rmse_baseline": round(metricas_bl_total["rmse"], 2),
        "wape_baseline_pct": round(metricas_bl_total["wape_percentual"], 2),
        "diferenca_wape_pontos_pct": round(
            metricas_rf_total["wape_percentual"] - metricas_bl_total["wape_percentual"], 2
        ),
    })

    saida = Path(args.saida)
    pd.DataFrame(linhas_metricas).to_csv(saida, index=False, float_format="%.2f")

    print("VALIDAÇÃO TEMPORAL | RANDOM FOREST VS. BASELINE")
    print("Janelas de 30 dias; treino usa somente datas anteriores a cada janela.")
    print("O teste original de 01/07/2018 a 30/07/2018 não foi incluído nestas cinco janelas.")
    print("Diferença de WAPE = Random Forest menos baseline; valor negativo favorece o Random Forest.")
    print()
    tabela = pd.DataFrame(linhas_metricas)
    print(tabela.to_string(index=False))
    print(f"\nResultados salvos em: {saida.resolve()}")


if __name__ == "__main__":
    main()
