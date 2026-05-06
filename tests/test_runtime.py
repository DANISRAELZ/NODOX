from __future__ import annotations

import unittest

from src.nodos_funcionales.runtime import resolve_pipeline_mode


class RuntimeTests(unittest.TestCase):
    def test_cli_mode_overrides_config(self) -> None:
        config = {"runtime": {"pipeline_mode": "compare"}}
        self.assertEqual(resolve_pipeline_mode(config, "legacy"), "legacy")

    def test_default_mode_aliases_compare(self) -> None:
        config = {"runtime": {"pipeline_mode": "legacy"}}
        self.assertEqual(resolve_pipeline_mode(config, "default"), "compare")

    def test_invalid_mode_raises(self) -> None:
        config = {"runtime": {"pipeline_mode": "unsupported"}}
        with self.assertRaises(ValueError):
            resolve_pipeline_mode(config)


if __name__ == "__main__":
    unittest.main()
