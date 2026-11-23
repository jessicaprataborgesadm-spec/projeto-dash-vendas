from __future__ import annotations

import unittest
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]


class StreamlitAppSyntaxTests(unittest.TestCase):
    def test_app_py_compila_sem_erro_de_sintaxe(self):
        app_path = APP_DIR / "app.py"
        source = app_path.read_text(encoding="utf-8")
        compile(source, str(app_path), "exec")


if __name__ == "__main__":
    unittest.main()
