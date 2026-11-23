from __future__ import annotations

import sys
import unittest
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_DIR))

from ia_analista.analytics import carregar_fontes
from ia_analista.router import executar_pergunta, route_question


class IntentRouterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fontes = carregar_fontes(APP_DIR)

    def test_rota_evolucao_por_mes(self):
        rota = route_question("Qual foi o faturamento em julho de 2018?", self.fontes)
        self.assertEqual(rota["status"], "ready")
        self.assertEqual(rota["intent"], "period_evolution")
        self.assertEqual(rota["parameters"]["data_inicio"], "2018-07-01")
        self.assertEqual(rota["parameters"]["data_fim"], "2018-07-31")

    def test_rota_comparacao_mantem_mes_mais_recente(self):
        rota = route_question("Compare julho de 2018 com julho de 2017", self.fontes)
        self.assertEqual(rota["status"], "ready")
        self.assertEqual(rota["intent"], "period_comparison")
        self.assertEqual(rota["parameters"]["data_inicio"], "2018-07-01")
        self.assertEqual(rota["parameters"]["tipo_comparacao"], "ano_anterior")

    def test_rota_data_explicita_brasileira(self):
        rota = route_question("Analise o faturamento de 01/07/2018 a 30/07/2018", self.fontes)
        self.assertEqual(rota["status"], "ready")
        self.assertEqual(rota["parameters"]["data_inicio"], "2018-07-01")
        self.assertEqual(rota["parameters"]["data_fim"], "2018-07-30")

    def test_rota_padrao_por_dia_da_semana_usa_cobertura_total(self):
        rota = route_question("Qual dia da semana costuma ter maior faturamento?", self.fontes)
        self.assertEqual(rota["intent"], "weekday_pattern")
        self.assertEqual(rota["status"], "ready")
        self.assertEqual(rota["parameters"]["data_inicio"], "2017-01-01")
        self.assertEqual(rota["parameters"]["data_fim"], "2018-08-29")
        self.assertTrue(rota["limitations"])

    def test_rota_calendario_detecta_feriados(self):
        rota = route_question("Como foram os feriados em janeiro de 2018?", self.fontes)
        self.assertEqual(rota["intent"], "calendar_analysis")
        self.assertEqual(rota["parameters"]["categoria"], "feriado_nacional")
        self.assertEqual(rota["parameters"]["data_inicio"], "2018-01-01")

    def test_rota_diagnostico_de_queda(self):
        rota = route_question("Por que o faturamento caiu de 01/08/2018 a 20/08/2018?", self.fontes)
        self.assertEqual(rota["intent"], "change_diagnosis")
        self.assertEqual(rota["status"], "ready")

    def test_rota_previsao_nao_exige_periodo(self):
        rota = route_question("Qual é a previsão dos próximos 30 dias?", self.fontes)
        self.assertEqual(rota["intent"], "forecast_summary")
        self.assertEqual(rota["status"], "ready")
        self.assertEqual(rota["parameters"], {})

    def test_rota_desempenho_modelos_nao_exige_periodo(self):
        rota = route_question("O Random Forest foi melhor que o baseline?", self.fontes)
        self.assertEqual(rota["intent"], "model_performance")
        self.assertEqual(rota["status"], "ready")

    def test_periodo_ausente_pede_esclarecimento(self):
        rota = route_question("Como evoluiu o faturamento?", self.fontes)
        self.assertEqual(rota["status"], "ambiguous")
        self.assertIn("Informe o período", rota["clarification"])

    def test_pergunta_por_estado_fica_fora_do_escopo(self):
        rota = route_question("Qual estado teve maior faturamento em julho de 2018?", self.fontes)
        self.assertEqual(rota["status"], "out_of_scope")

    def test_pergunta_com_duas_intencoes_pede_esclarecimento(self):
        rota = route_question("Compare o faturamento e analise por dia da semana em julho de 2018", self.fontes)
        self.assertEqual(rota["status"], "ambiguous")

    def test_data_invalida_e_rejeitada(self):
        rota = route_question("Qual foi o faturamento em 32/13/2018?", self.fontes)
        self.assertEqual(rota["status"], "invalid")

    def test_execucao_de_pergunta_entrega_resultado_deterministico(self):
        resposta = executar_pergunta("Qual foi o faturamento em julho de 2018?", self.fontes)
        self.assertEqual(resposta["status"], "ok")
        self.assertEqual(resposta["result"]["facts"]["total"], 867953.46)

    def test_periodo_sem_cobertura_retorna_resultado_parcial(self):
        resposta = executar_pergunta("Qual foi o faturamento de 25/08/2018 a 05/09/2018?", self.fontes)
        self.assertEqual(resposta["status"], "partial_data")
        self.assertEqual(resposta["result"]["coverage"]["dias_faltantes"], 7)


if __name__ == "__main__":
    unittest.main()
