"""Valida o baseline e o Random Forest na janela recente de 30 dias.

Projeto Dash Vendas
- Treinamento: até 30/07/2018.
- Teste: 31/07/2018 a 29/08/2018.
- Usa o mesmo modelo e as mesmas regras do script 20, sem alterá-lo.
- A média móvel no teste é recursiva: usa previsões anteriores, não realizados futuros.

Uso:
    python 22_validacao_janela_recente.py

Arquivos esperados na mesma pasta:
    base_treinamento_faturamento_teste.csv
    20_modelo_random_forest_teste.py

Saída:
    22_resultado_janela_recente.csv
"""
from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path

import pandas as pd

DATA_TESTE_INICIO = pd.Timestamp("2018-07-31")
DATA_TESTE_FIM = pd.Timestamp("2018-08-29")


def carregar_modulo_modelo(caminho: Path):
    if not caminho.is_file():
        raise FileNotFoundError(
            f"Script do modelo não encontrado: {caminho}. "
            "Coloque 20_modelo_random_forest_teste.py na mesma pasta."
        )
    spec = importlib.util.spec_from_file_location("modelo_rf_janela_recente", caminho)
    if spec is None or spec.loader is None:
        raise ImportError(f"Não foi possível carregar o script: {caminho}")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compara baseline e Random Forest no período de 31/07 a 29/08/2018."
    )
    parser.add_argument(
        "arquivo_csv", nargs="?", default="base_treinamento_faturamento_teste.csv",
        help="CSV histórico validado da SQL 18.",
    )
    parser.add_argument(
        "--modelo", default="20_modelo_random_forest_teste.py",
        help="Script do modelo já validado.",
    )
    parser.add_argument(
        "--saida", default="22_resultado_janela_recente.csv",
        help="CSV de previsões diárias gerado pelo teste.",
    )
    args = parser.parse_args()

    modulo = carregar_modulo_modelo(Path(args.modelo))
    base = modulo.carregar_base(Path(args.arquivo_csv))
    modulo.DATA_TESTE_INICIO = DATA_TESTE_INICIO
    modulo.DATA_TESTE_FIM = DATA_TESTE_FIM

    previsoes, metricas, linhas_treino = modulo.treinar_e_prever(base)
    saida = Path(args.saida)
    previsoes.to_csv(saida, index=False, date_format="%Y-%m-%d", float_format="%.2f")

    print("VALIDAÇÃO DA JANELA RECENTE | PROJETO DASH VENDAS")
    print(f"Treinamento até: {DATA_TESTE_INICIO - pd.Timedelta(days=1):%d/%m/%Y}")
    print(f"Linhas utilizadas no treinamento: {linhas_treino}")
    print(f"Período de teste: {DATA_TESTE_INICIO:%d/%m/%Y} a {DATA_TESTE_FIM:%d/%m/%Y}")
    print("A média móvel do teste usa previsões anteriores, nunca faturamento realizado futuro.")
    modulo.imprimir_metricas("RANDOM FOREST", metricas["random_forest"])
    modulo.imprimir_metricas("BASELINE DE REFERÊNCIA", metricas["baseline"])
    diferenca = metricas["random_forest"]["wape_percentual"] - metricas["baseline"]["wape_percentual"]
    if diferenca < 0:
        print(f"\nWAPE: Random Forest ficou {abs(diferenca):.2f} ponto(s) percentual(is) abaixo do baseline.")
    elif diferenca > 0:
        print(f"\nWAPE: Random Forest ficou {diferenca:.2f} ponto(s) percentual(is) acima do baseline.")
    else:
        print("\nWAPE: Random Forest empatou com o baseline.")
    print(f"Previsões diárias salvas em: {saida.resolve()}")
    print("Nota: o target é definido por pedidos atualmente 'delivered'; o resultado deve ser interpretado considerando possível maturidade incompleta de pedidos recentes.")


if __name__ == "__main__":
    main()
