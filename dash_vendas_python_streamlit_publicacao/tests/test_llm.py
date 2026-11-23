from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

APP_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_DIR))

from ia_analista.llm import MODELO_PADRAO, interpretar_resultado


class FakeModels:
    def __init__(self, response_text):
        self.response_text = response_text
        self.called_with = None

    def generate_content(self, **kwargs):
        self.called_with = kwargs
        return SimpleNamespace(text=self.response_text)


class FakeClient:
    def __init__(self, response_text):
        self.models = FakeModels(response_text)


class LLMInterpretationTests(unittest.TestCase):
    def setUp(self):
        self.resultado = {
            "status": "ok",
            "intent": "change_diagnosis",
            "metric": {"name": "faturamento_diario", "definition": "Métrica operacional."},
            "period": {"start_date": "2018-08-01", "end_date": "2018-08-20"},
            "facts": {
                "variacao_percentual": 16.03,
                "maiores_quedas_diarias": [{"data": "2018-08-19", "diferenca": -12119.57}],
            },
            "coverage": {"dias_pareados": 20},
            "limitations": ["Diagnóstico descritivo; não comprova causalidade."],
            "csv_completo": "NAO_DEVE_IR_PARA_O_MODELO",
        }
        self.resposta_valida = {
            "resumo": "O acumulado cresceu na comparação, embora alguns dias tenham apresentado quedas.",
            "pontos_chave": ["As quedas diárias indicam pontos específicos para investigação."],
            "cuidados": ["A comparação é descritiva e não comprova a causa das variações."],
        }

    def test_sem_chave_nao_tenta_chamar_modelo(self):
        resposta = interpretar_resultado(
            "Por que o faturamento mudou?", self.resultado, api_key=None
        )
        self.assertEqual(resposta["status"], "not_configured")

    def test_envia_somente_pergunta_atual_e_resultado_estruturado(self):
        cliente = FakeClient(json.dumps(self.resposta_valida, ensure_ascii=False))
        resposta = interpretar_resultado(
            "Por que o faturamento mudou?",
            self.resultado,
            api_key="chave-de-teste",
            client=cliente,
        )
        chamada = cliente.models.called_with
        payload = json.loads(chamada["contents"].split("\n\n", 1)[1])

        self.assertEqual(resposta["status"], "ok")
        self.assertEqual(chamada["model"], MODELO_PADRAO)
        self.assertEqual(payload["pergunta_atual"], "Por que o faturamento mudou?")
        self.assertNotIn("csv_completo", payload["resultado_deterministico"])
        self.assertNotIn("NAO_DEVE_IR_PARA_O_MODELO", chamada["contents"])
        self.assertEqual(chamada["config"]["response_mime_type"], "application/json")
        self.assertEqual(chamada["config"]["temperature"], 0.2)

    def test_nao_chama_llm_para_status_fora_de_escopo(self):
        cliente = FakeClient(json.dumps(self.resposta_valida, ensure_ascii=False))
        resultado = {**self.resultado, "status": "out_of_scope"}
        resposta = interpretar_resultado(
            "Qual estado vendeu mais?", resultado,
            api_key="chave-de-teste", client=cliente,
        )
        self.assertEqual(resposta["status"], "not_applicable")
        self.assertIsNone(cliente.models.called_with)

    def test_rejeita_narrativa_com_algarismos(self):
        resposta_com_numero = {
            **self.resposta_valida,
            "resumo": "O faturamento aumentou 16,03 por cento.",
        }
        cliente = FakeClient(json.dumps(resposta_com_numero, ensure_ascii=False))
        resposta = interpretar_resultado(
            "Por que o faturamento mudou?", self.resultado,
            api_key="chave-de-teste", client=cliente,
        )
        self.assertEqual(resposta["status"], "error")
        self.assertEqual(resposta["error_type"], "ValueError")

    def test_rejeita_resposta_json_invalida(self):
        cliente = FakeClient("não é json")
        resposta = interpretar_resultado(
            "Por que o faturamento mudou?", self.resultado,
            api_key="chave-de-teste", client=cliente,
        )
        self.assertEqual(resposta["status"], "error")
        self.assertEqual(resposta["error_type"], "JSONDecodeError")

    def test_limita_tamanho_da_pergunta_enviada(self):
        pergunta = "A" * 700
        cliente = FakeClient(json.dumps(self.resposta_valida, ensure_ascii=False))
        interpretar_resultado(
            pergunta, self.resultado, api_key="chave-de-teste", client=cliente
        )
        payload = json.loads(cliente.models.called_with["contents"].split("\n\n", 1)[1])
        self.assertEqual(len(payload["pergunta_atual"]), 500)


if __name__ == "__main__":
    unittest.main()
