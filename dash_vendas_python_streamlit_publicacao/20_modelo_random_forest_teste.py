"""Treina e avalia um primeiro modelo de Machine Learning para o Projeto Dash Vendas.

Objetivo:
- Treinar um Random Forest usando somente dados anteriores a 01/07/2018.
- Prever 01/07/2018 a 30/07/2018 sem consultar o faturamento real desses dias
  para construir features ao longo do horizonte.
- Comparar o modelo com o baseline constante da etapa anterior.

Entrada padrão: base_treinamento_faturamento_teste.csv
Saída padrão: 20_previsoes_random_forest_teste.csv

Dependências: pandas, numpy e scikit-learn.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

DATA_TESTE_INICIO = pd.Timestamp("2018-07-01")
DATA_TESTE_FIM = pd.Timestamp("2018-07-30")
JANELA_MEDIA_DIAS = 7
SEMENTE = 42

COLUNAS_OBRIGATORIAS = {
    "data",
    "dia_semana",
    "faturamento_diario",
    "faturamento_ano_anterior",
    "media_7d",
    "eh_feriado_nacional",
    "eh_data_movel",
    "eh_data_comercial",
}
COLUNAS_CATEGORICAS = ["dia_semana"]
COLUNAS_NUMERICAS = [
    "faturamento_ano_anterior",
    "media_7d",
    "eh_feriado_nacional",
    "eh_data_movel",
    "eh_data_comercial",
]
COLUNAS_FEATURES = COLUNAS_CATEGORICAS + COLUNAS_NUMERICAS


def carregar_base(caminho: Path) -> pd.DataFrame:
    """Carrega a base diária e valida esquema, datas e valores do target."""
    if not caminho.is_file():
        raise FileNotFoundError(
            f"Arquivo não encontrado: {caminho}\n"
            "Coloque o CSV exportado da SQL 18 na mesma pasta do script ou informe o caminho."
        )

    df = pd.read_csv(caminho)
    ausentes = COLUNAS_OBRIGATORIAS.difference(df.columns)
    if ausentes:
        raise ValueError("Colunas obrigatórias ausentes: " + ", ".join(sorted(ausentes)))

    df = df.copy()
    df["data"] = pd.to_datetime(df["data"], errors="coerce")
    if df["data"].isna().any():
        raise ValueError("Há datas nulas ou inválidas na coluna 'data'.")
    if df["data"].duplicated().any():
        datas = df.loc[df["data"].duplicated(keep=False), "data"].dt.strftime("%Y-%m-%d")
        raise ValueError("Há datas duplicadas: " + ", ".join(datas.tolist()[:10]))

    df["faturamento_diario"] = pd.to_numeric(df["faturamento_diario"], errors="coerce")
    if df["faturamento_diario"].isna().any():
        raise ValueError("Há faturamentos nulos ou não numéricos.")
    if (df["faturamento_diario"] < 0).any():
        raise ValueError("Há faturamentos negativos. Valide a base antes de treinar.")

    df = df.sort_values("data").reset_index(drop=True)
    calendario_esperado = pd.date_range(df["data"].min(), df["data"].max(), freq="D")
    if not df["data"].reset_index(drop=True).equals(
        pd.Series(calendario_esperado, name="data")
    ):
        raise ValueError("A série contém lacunas; é esperado exatamente um registro por dia.")

    # Normaliza flags para 0/1; aceita CSV com booleanos ou texto.
    for coluna in ["eh_feriado_nacional", "eh_data_movel", "eh_data_comercial"]:
        if df[coluna].dtype == bool:
            df[coluna] = df[coluna].astype(int)
        else:
            mapeamento = {
                "true": 1, "false": 0, "1": 1, "0": 0,
                "sim": 1, "não": 0, "nao": 0,
            }
            convertido = df[coluna].astype(str).str.strip().str.lower().map(mapeamento)
            if convertido.isna().any():
                raise ValueError(f"Valores inesperados na feature '{coluna}'.")
            df[coluna] = convertido.astype(int)

    for coluna in ["faturamento_ano_anterior", "media_7d"]:
        df[coluna] = pd.to_numeric(df[coluna], errors="coerce")

    if df["dia_semana"].isna().any():
        raise ValueError("Há valores ausentes em 'dia_semana'.")
    return df


def criar_modelo() -> Pipeline:
    """Cria pipeline com imputação e codificação aprendidas só no treinamento."""
    preprocessamento = ColumnTransformer(
        transformers=[
            (
                "dia_semana",
                OneHotEncoder(handle_unknown="ignore"),
                COLUNAS_CATEGORICAS,
            ),
            (
                "numericas",
                SimpleImputer(strategy="median", add_indicator=True),
                COLUNAS_NUMERICAS,
            ),
        ],
        remainder="drop",
    )

    regressor = RandomForestRegressor(
        n_estimators=300,
        min_samples_leaf=5,
        random_state=SEMENTE,
        n_jobs=-1,
    )
    return Pipeline(
        steps=[("preprocessamento", preprocessamento), ("modelo", regressor)]
    )


def calcular_metricas(real: np.ndarray, previsto: np.ndarray) -> dict[str, float]:
    erro = real - previsto
    erro_absoluto = np.abs(erro)
    denominador_wape = float(np.abs(real).sum())
    wape = float(erro_absoluto.sum() / denominador_wape * 100) if denominador_wape else float("nan")
    return {
        "mae": float(erro_absoluto.mean()),
        "rmse": float(np.sqrt(np.mean(np.square(erro)))),
        "wape_percentual": wape,
        "realizado_total": float(real.sum()),
        "previsto_total": float(previsto.sum()),
    }


def treinar_e_prever(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, dict[str, float]], int]:
    """Treina antes do teste e prevê recursivamente sem usar realizados futuros."""
    treino = df[df["data"] < DATA_TESTE_INICIO].copy()
    teste = df[df["data"].between(DATA_TESTE_INICIO, DATA_TESTE_FIM)].copy()
    datas_esperadas = pd.date_range(DATA_TESTE_INICIO, DATA_TESTE_FIM, freq="D")

    if len(teste) != len(datas_esperadas) or not teste["data"].reset_index(drop=True).equals(
        pd.Series(datas_esperadas, name="data")
    ):
        raise ValueError(
            "O teste precisa conter todos os 30 dias de 2018-07-01 a 2018-07-30."
        )
    if treino.empty or treino["data"].max() != DATA_TESTE_INICIO - pd.Timedelta(days=1):
        raise ValueError("Treinamento precisa ter dados até 2018-06-30, sem incluir o teste.")

    # Treino em datas em que media_7d existe; é calculada só com dias anteriores.
    treino_modelo = treino.dropna(subset=["media_7d"]).copy()
    if treino_modelo.empty:
        raise ValueError("Não há linhas suficientes com 'media_7d' para treinar.")

    modelo = criar_modelo()
    modelo.fit(treino_modelo[COLUNAS_FEATURES], treino_modelo["faturamento_diario"])

    # A previsão é recursiva: após cada dia previsto, esse valor passa a compor
    # a janela dos 7 dias seguintes. O faturamento real do teste nunca é usado aqui.
    historico_previsto = treino["faturamento_diario"].astype(float).tolist()
    previsoes_modelo: list[float] = []
    for _, linha in teste.iterrows():
        if len(historico_previsto) < JANELA_MEDIA_DIAS:
            raise ValueError("Histórico insuficiente para calcular a média dos 7 dias.")
        linha_modelo = linha[COLUNAS_FEATURES].copy()
        linha_modelo["media_7d"] = float(np.mean(historico_previsto[-JANELA_MEDIA_DIAS:]))
        entrada = pd.DataFrame([linha_modelo], columns=COLUNAS_FEATURES)
        valor_previsto = float(modelo.predict(entrada)[0])
        # Faturamento não deve ser negativo; mantém o piso em zero se o modelo prever negativo.
        valor_previsto = max(0.0, valor_previsto)
        previsoes_modelo.append(valor_previsto)
        historico_previsto.append(valor_previsto)

    # Recria o baseline constante a partir dos mesmos 7 dias anteriores ao teste.
    historico_baseline = df[
        df["data"].between(
            DATA_TESTE_INICIO - pd.Timedelta(days=JANELA_MEDIA_DIAS),
            DATA_TESTE_INICIO - pd.Timedelta(days=1),
        )
    ]
    if len(historico_baseline) != JANELA_MEDIA_DIAS:
        raise ValueError("Não há sete dias completos para calcular o baseline.")
    previsao_baseline = float(historico_baseline["faturamento_diario"].mean())

    resultado = teste[["data", "faturamento_diario"]].copy()
    resultado = resultado.rename(columns={"faturamento_diario": "faturamento_real"})
    resultado["previsao_random_forest"] = np.round(previsoes_modelo, 2)
    resultado["previsao_baseline"] = round(previsao_baseline, 2)
    resultado["erro_modelo"] = resultado["faturamento_real"] - resultado["previsao_random_forest"]
    resultado["erro_absoluto_modelo"] = resultado["erro_modelo"].abs()
    resultado["erro_baseline"] = resultado["faturamento_real"] - resultado["previsao_baseline"]
    resultado["erro_absoluto_baseline"] = resultado["erro_baseline"].abs()

    real = resultado["faturamento_real"].to_numpy(dtype=float)
    previsto_modelo = resultado["previsao_random_forest"].to_numpy(dtype=float)
    previsto_baseline = resultado["previsao_baseline"].to_numpy(dtype=float)
    metricas = {
        "random_forest": calcular_metricas(real, previsto_modelo),
        "baseline": calcular_metricas(real, previsto_baseline),
    }
    return resultado, metricas, len(treino_modelo)


def imprimir_metricas(nome: str, metricas: dict[str, float]) -> None:
    print(f"\n{nome}")
    print(f"MAE: R$ {metricas['mae']:,.2f}")
    print(f"RMSE: R$ {metricas['rmse']:,.2f}")
    print(f"WAPE: {metricas['wape_percentual']:.2f}%")
    print(f"Faturamento previsto total: R$ {metricas['previsto_total']:,.2f}")
    print(f"Faturamento real total: R$ {metricas['realizado_total']:,.2f}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compara Random Forest com baseline no teste de 30 dias."
    )
    parser.add_argument(
        "arquivo_csv",
        nargs="?",
        default="base_treinamento_faturamento_teste.csv",
        help="CSV da SQL 18 (padrão: base_treinamento_faturamento_teste.csv)",
    )
    parser.add_argument(
        "--saida",
        default="20_previsoes_random_forest_teste.csv",
        help="CSV de saída com previsões e erros por dia.",
    )
    args = parser.parse_args()

    base = carregar_base(Path(args.arquivo_csv))
    previsoes, metricas, qtd_treino = treinar_e_prever(base)
    caminho_saida = Path(args.saida)
    previsoes.to_csv(caminho_saida, index=False, date_format="%Y-%m-%d", float_format="%.2f")

    print("MODELO RANDOM FOREST | PROJETO DASH VENDAS")
    print(f"Período de treinamento: até {DATA_TESTE_INICIO - pd.Timedelta(days=1):%d/%m/%Y}")
    print(f"Linhas utilizadas no treinamento: {qtd_treino}")
    print(f"Período de teste: {DATA_TESTE_INICIO:%d/%m/%Y} a {DATA_TESTE_FIM:%d/%m/%Y}")
    print("Features usadas: dia_semana, faturamento_ano_anterior, media_7d e flags de calendário.")
    print("A media_7d do teste é atualizada com previsões anteriores, nunca com realizados futuros.")
    imprimir_metricas("RANDOM FOREST", metricas["random_forest"])
    imprimir_metricas("BASELINE DE REFERÊNCIA", metricas["baseline"])

    diferenca_wape = metricas["random_forest"]["wape_percentual"] - metricas["baseline"]["wape_percentual"]
    if diferenca_wape < 0:
        print(f"\nWAPE: o Random Forest ficou {abs(diferenca_wape):.2f} ponto(s) percentual(is) abaixo do baseline.")
    elif diferenca_wape > 0:
        print(f"\nWAPE: o Random Forest ficou {diferenca_wape:.2f} ponto(s) percentual(is) acima do baseline.")
    else:
        print("\nWAPE: o Random Forest empatou com o baseline.")
    print(f"Previsões diárias salvas em: {caminho_saida.resolve()}")


if __name__ == "__main__":
    main()
