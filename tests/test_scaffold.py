"""Configuration checks runnable with the system Python and PyYAML."""
import ast
from pathlib import Path
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]


class ScaffoldTests(unittest.TestCase):
    def test_network_isolation(self):
        compose = yaml.safe_load((ROOT / "compose.yaml").read_text())
        self.assertTrue(compose["networks"]["internal"]["internal"])
        self.assertNotIn("ports", compose["services"]["db"])
        self.assertEqual(compose["services"]["api"]["ports"], ["127.0.0.1:8000:8000"])
        for name, service in compose["services"].items():
            expected = ["api_network", "internal"] if name == "api" else ["internal"]
            self.assertEqual(service["networks"], expected)
            self.assertNotIn("network_mode", service)
            if name != 'api':
                self.assertNotIn('ports', service)
        self.assertFalse(compose['networks']['api_network']['internal'])
        self.assertEqual(compose["services"]["api"]["depends_on"]["migrate"]["condition"], "service_completed_successfully")

    def test_python_syntax(self):
        for directory in ("backend", "database"):
            for source in (ROOT / directory).rglob("*.py"):
                ast.parse(source.read_text(), filename=str(source))

    def test_secret_not_populated(self):
        values = dict(line.split("=", 1) for line in (ROOT / ".env.example").read_text().splitlines() if line and not line.startswith("#"))
        self.assertEqual(values["POSTGRES_PASSWORD"], "")


if __name__ == "__main__":
    unittest.main()
