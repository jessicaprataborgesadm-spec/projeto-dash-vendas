from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

import pandas as pd

APP_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_DIR))

from ia_analista.analytics import (
    analisar_calendario,
    analisar_dia_semana,
    analisar_evolucao,
    avaliar_modelos,
    carregar_fontes,
    comparar_periodos,
    consultar_previsao_30_dias,
    diagnosticar_variacao,
    executar_intencao,
    preparar_base_diaria,
)


class AnalyticsEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fontes = carregar_fontes(APP_DIR)
        cls.base = cls.fontes["base_diaria"]

    def test_evolucao_periodo_julho_2018(self):
        resultado = analisar_evolucao(self.base, "2018-07-01", "2018-07-30")
        self.assertEqual(resultado["status"], "ok")
        self.assertEqual(resultado["coverage"]["linhas_utilizadas"], 30)
        self.assertEqual(resultado["facts"]["dias_com_valor"], 30)
        self.assertEqual(resultado["facts"]["total"], 823149.44)

    def test_periodo_fora_da_cobertura_retorna_parcial(self):
        resultado = analisar_evolucao(self.base, "2018-08-25", "2018-09-05")
        self.assertEqual(resultado["status"], "partial_data")
        self.assertEqual(resultado["coverage"]["dias_faltantes"], 7)

    def test_comparacao_ano_anterior_informa_pares(self):
        resultado = comparar_periodos(self.base, "2018-07-01", "2018-07-30", "ano_anterior")
        self.assertEqual(resultado["coverage"]["pares_comparaveis"], 30)
        self.assertEqual(resultado["facts"]["total_periodo_comparacao"], 464628.33)
        self.assertAlmostEqual(resultado["facts"]["variacao_percentual"], 77.16)

    def test_comparacao_periodo_anterior_equivalente(self):
        resultado = comparar_periodos(self.base, "2018-07-01", "2018-07-30", "periodo_anterior")
        self.assertEqual(resultado["facts"]["data_inicio_comparacao"], "2018-06-01")
        self.assertEqual(resultado["facts"]["dias_comparaveis"], 30)
        self.assertEqual(resultado["facts"]["total_periodo_comparacao"], 856077.86)

    def test_dia_semana_tem_sete_grupos(self):
        resultado = analisar_dia_semana(self.base, "2018-07-01", "2018-07-30")
        self.assertEqual(len(resultado["facts"]["por_dia_semana"]), 7)
        self.assertEqual(resultado["facts"]["maior_media"]["dia_semana"], "quarta-feira")
        self.assertEqual(resultado["facts"]["menor_media"]["dia_semana"], "sábado")

    def test_calendario_contabiliza_grupos(self):
        resultado = analisar_calendario(self.base, "2018-01-01", "2018-12-31", "feriado_nacional")
        grupos = resultado["facts"]["comparacao"]
        self.assertEqual(grupos["sinalizado"]["dias_observados"], 3)
        self.assertEqual(grupos["sinalizado"]["dias_observados"] + grupos["nao_sinalizado"]["dias_observados"], 241)
        self.assertEqual(resultado["status"], "partial_data")

    def test_diagnostico_compara_janelas_equivalentes(self):
        resultado = diagnosticar_variacao(self.base, "2018-08-01", "2018-08-20")
        self.assertEqual(resultado["coverage"]["dias_pareados"], 20)
        self.assertEqual(resultado["period"]["start_date"], "2018-08-01")
        self.assertEqual(len(resultado["facts"]["maiores_quedas_diarias"]), 5)
        self.assertIsNotNone(resultado["facts"]["total_periodo_atual_pareado"])

    def test_previsao_30_dias_bate_totais_publicados(self):
        resultado = consultar_previsao_30_dias(self.fontes)
        self.assertEqual(resultado["facts"]["total_random_forest"], 993231.78)
        self.assertEqual(resultado["facts"]["total_baseline"], 1024124.10)
        self.assertEqual(resultado["coverage"]["dias_disponiveis"], 30)
        self.assertTrue(any("não há MAE" in item for item in resultado["limitations"]))

    def test_avaliacao_modelos_mantem_tres_janelas_vencidas(self):
        resultado = avaliar_modelos(self.fontes)
        validacao = resultado["facts"]["validacao_temporal_5_janelas"]
        self.assertEqual(validacao["quantidade_janelas"], 5)
        self.assertEqual(validacao["janelas_vencidas_random_forest"], 3)
        self.assertAlmostEqual(validacao["wape_agregado_random_forest_pct"], 22.70)
        self.assertAlmostEqual(validacao["wape_agregado_baseline_pct"], 25.27)
        self.assertAlmostEqual(resultado["facts"]["teste_inicial_julho"]["random_forest"]["wape_pct"], 23.29)
        self.assertAlmostEqual(resultado["facts"]["diagnostico_janela_recente"]["random_forest"]["wape_pct"], 36.39)

    def test_dispatcher_executa_intencao_conhecida(self):
        resultado = executar_intencao(
            "period_evolution", self.fontes,
            {"data_inicio": "2018-07-01", "data_fim": "2018-07-30"},
        )
        self.assertEqual(resultado["status"], "ok")
        self.assertEqual(resultado["facts"]["total"], 823149.44)

    def test_saida_e_serializavel_em_json(self):
        resultados = [
            analisar_evolucao(self.base, "2018-07-01", "2018-07-30", incluir_serie=True),
            comparar_periodos(self.base, "2018-07-01", "2018-07-30"),
            analisar_dia_semana(self.base, "2018-07-01", "2018-07-30"),
            analisar_calendario(self.base, "2018-01-01", "2018-12-31"),
            diagnosticar_variacao(self.base, "2018-08-01", "2018-08-20"),
            consultar_previsao_30_dias(self.fontes),
            avaliar_modelos(self.fontes),
        ]
        for resultado in resultados:
            json.dumps(resultado, ensure_ascii=False, allow_nan=False)

    def test_data_inicio_maior_que_fim_rejeitada(self):
        with self.assertRaises(ValueError):
            analisar_evolucao(self.base, "2018-07-30", "2018-07-01")

    def test_duplicidade_de_data_rejeitada(self):
        duplicada = pd.concat([self.base, self.base.iloc[[0]]], ignore_index=True)
        with self.assertRaises(ValueError):
            preparar_base_diaria(duplicada)

    def test_intencao_desconhecida_fica_fora_de_escopo(self):
        resultado = executar_intencao("state_contribution", self.fontes, {})
        self.assertEqual(resultado["status"], "out_of_scope")


if __name__ == "__main__":
    unittest.main()
