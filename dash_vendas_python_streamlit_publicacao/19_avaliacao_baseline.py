"""Avalia um baseline de faturamento diário para o Projeto Dash Vendas.

Como usar:
1. Exporte a saída da SQL 18 do BigQuery para CSV.
2. Salve o arquivo como base_treinamento_faturamento.csv neste diretório,
   ou informe o caminho como primeiro argumento.
3. Execute: python 19_avaliacao_baseline.py

O teste usa 01/07/2018 a 30/07/2018. A previsão para todos os 30 dias
é a média do faturamento dos sete dias anteriores ao início do teste.
Os valores reais do período de teste não atualizam a previsão, evitando
vazamento de dados em um horizonte de 30 dias.

Dependências: pandas e numpy.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

DATA_TESTE_INICIO = pd.Timestamp("2018-07-01")
DATA_TESTE_FIM = pd.Timestamp("2018-07-30")
JANELA_HISTORICA_DIAS = 7


def carregar_base(caminho: Path) -> pd.DataFrame:
    """Carrega e valida as colunas mínimas da base diária exportada do BigQuery."""
    if not caminho.is_file():
        raise FileNotFoundError(
            f"Arquivo não encontrado: {caminho}\n"
            "Exporte a saída da SQL 18 para CSV ou informe o caminho correto."
        )

    df = pd.read_csv(caminho)
    colunas_obrigatorias = {"data", "faturamento_diario"}
    ausentes = colunas_obrigatorias.difference(df.columns)
    if ausentes:
        raise ValueError(
            "Colunas obrigatórias ausentes no CSV: " + ", ".join(sorted(ausentes))
        )

    df = df[["data", "faturamento_diario"]].copy()
    df["data"] = pd.to_datetime(df["data"], errors="coerce")
    df["faturamento_diario"] = pd.to_numeric(
        df["faturamento_diario"], errors="coerce"
    )

    if df["data"].isna().any():
        raise ValueError("Há datas nulas ou inválidas na coluna 'data'.")
    if df["faturamento_diario"].isna().any():
        raise ValueError("Há faturamentos nulos ou não numéricos.")
    if df["data"].duplicated().any():
        datas = df.loc[df["data"].duplicated(keep=False), "data"].dt.strftime(
            "%Y-%m-%d"
        ).tolist()
        raise ValueError(f"Há datas duplicadas na base diária: {datas[:10]}")
    if (df["faturamento_diario"] < 0).any():
        raise ValueError("Há faturamentos negativos. Valide a base antes de avaliar.")

    df = df.sort_values("data").reset_index(drop=True)
    calendario_esperado = pd.date_range(df["data"].min(), df["data"].max(), freq="D")
    if not df["data"].reset_index(drop=True).equals(
        pd.Series(calendario_esperado, name="data")
    ):
        raise ValueError("A série tem lacunas ou não contém exatamente uma linha por dia.")

    return df


def avaliar_baseline(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, float]]:
    """Gera previsão constante e métricas no período de teste fixado."""
    datas_teste = pd.date_range(DATA_TESTE_INICIO, DATA_TESTE_FIM, freq="D")
    teste = df[df["data"].between(DATA_TESTE_INICIO, DATA_TESTE_FIM)].copy()

    if len(teste) != len(datas_teste) or not teste["data"].reset_index(drop=True).equals(
        pd.Series(datas_teste, name="data")
    ):
        raise ValueError(
            "O período de teste não contém os 30 dias esperados, de "
            f"{DATA_TESTE_INICIO:%Y-%m-%d} a {DATA_TESTE_FIM:%Y-%m-%d}."
        )

    inicio_historico = DATA_TESTE_INICIO - pd.Timedelta(days=JANELA_HISTORICA_DIAS)
    fim_historico = DATA_TESTE_INICIO - pd.Timedelta(days=1)
    historico = df[df["data"].between(inicio_historico, fim_historico)].copy()

    if len(historico) != JANELA_HISTORICA_DIAS:
        raise ValueError(
            "Não há exatamente sete dias disponíveis antes do teste: "
            f"{inicio_historico:%Y-%m-%d} a {fim_historico:%Y-%m-%d}."
        )

    # Previsão para o horizonte inteiro: não atualiza com os valores reais do teste.
    previsao = round(float(historico["faturamento_diario"].mean()), 2)
    teste["previsao_baseline"] = previsao
    teste["erro"] = teste["faturamento_diario"] - teste["previsao_baseline"]
    teste["erro_absoluto"] = teste["erro"].abs()

    mae = float(teste["erro_absoluto"].mean())
    rmse = float(np.sqrt(np.mean(np.square(teste["erro"].to_numpy()))))
    denominador_wape = float(teste["faturamento_diario"].abs().sum())
    if denominador_wape == 0:
        raise ValueError("WAPE não pode ser calculado: soma dos valores reais é zero.")
    wape = float(teste["erro_absoluto"].sum() / denominador_wape * 100)

    metricas = {
        "previsao_diaria_baseline": previsao,
        "mae": mae,
        "rmse": rmse,
        "wape_percentual": wape,
        "faturamento_real_total_teste": float(teste["faturamento_diario"].sum()),
        "faturamento_previsto_total_teste": float(teste["previsao_baseline"].sum()),
    }
    return teste, metricas


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Avalia um baseline constante para um horizonte de 30 dias."
    )
    parser.add_argument(
        "arquivo_csv",
        nargs="?",
        default="base_treinamento_faturamento_teste.csv",
        help="CSV exportado da SQL 18 (padrão: base_treinamento_faturamento_teste.csv)",
    )
    parser.add_argument(
        "--saida",
        default="19_previsoes_baseline_teste.csv",
        help="Caminho do CSV com realizado, previsão e erros.",
    )
    args = parser.parse_args()

    base = carregar_base(Path(args.arquivo_csv))
    previsoes, metricas = avaliar_baseline(base)
    caminho_saida = Path(args.saida)
    previsoes.to_csv(caminho_saida, index=False, date_format="%Y-%m-%d", float_format="%.2f")

    data_hist_inicio = DATA_TESTE_INICIO - pd.Timedelta(days=JANELA_HISTORICA_DIAS)
    data_hist_fim = DATA_TESTE_INICIO - pd.Timedelta(days=1)
    print("AVALIAÇÃO DO BASELINE | PROJETO DASH VENDAS")
    print(f"Histórico da média: {data_hist_inicio:%d/%m/%Y} a {data_hist_fim:%d/%m/%Y}")
    print(f"Período de teste: {DATA_TESTE_INICIO:%d/%m/%Y} a {DATA_TESTE_FIM:%d/%m/%Y}")
    print(f"Previsão constante por dia: R$ {metricas['previsao_diaria_baseline']:,.2f}")
    print(f"MAE: R$ {metricas['mae']:,.2f}")
    print(f"RMSE: R$ {metricas['rmse']:,.2f}")
    print(f"WAPE: {metricas['wape_percentual']:.2f}%")
    print(f"Realizado total no teste: R$ {metricas['faturamento_real_total_teste']:,.2f}")
    print(f"Previsto total no teste: R$ {metricas['faturamento_previsto_total_teste']:,.2f}")
    print(f"Previsões salvas em: {caminho_saida.resolve()}")


if __name__ == "__main__":
    main()
