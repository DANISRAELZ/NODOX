from __future__ import annotations

import unittest

import pandas as pd

from src.nodos_funcionales.config import load_config
from src.nodos_funcionales.virulence_layers import compute_virulence_layer_features
from tests.helpers import PROJECT_ROOT


class VirulenceLayerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = load_config(PROJECT_ROOT / "config" / "params.yaml")

    def test_toxin_raises_direct_host_damage_score(self) -> None:
        df = pd.DataFrame(
            {
                "protein_id": ["PA0001"],
                "gene": ["toxA"],
                "product": ["exotoxin tissue damage factor"],
            }
        )

        result = compute_virulence_layer_features(df, self.config)

        self.assertGreaterEqual(float(result.loc[0, "toxin_activity_score"]), 0.90)
        self.assertGreaterEqual(float(result.loc[0, "direct_host_damage_score"]), 0.80)

    def test_adhesin_raises_colonization_score(self) -> None:
        df = pd.DataFrame(
            {
                "protein_id": ["PA0002"],
                "gene": ["fimA"],
                "product": ["fimbrial adhesin surface colonization protein"],
            }
        )

        result = compute_virulence_layer_features(df, self.config)

        self.assertGreaterEqual(float(result.loc[0, "colonization_score"]), 0.90)

    def test_iron_system_raises_nutritional_immunity_escape_score(self) -> None:
        df = pd.DataFrame(
            {
                "protein_id": ["PA0003"],
                "gene": ["pvdA"],
                "product": ["pyoverdine siderophore iron acquisition enzyme"],
            }
        )

        result = compute_virulence_layer_features(df, self.config)

        self.assertGreaterEqual(float(result.loc[0, "nutritional_immunity_escape_score"]), 0.90)

    def test_quorum_regulator_raises_quorum_sensing_score(self) -> None:
        df = pd.DataFrame(
            {
                "protein_id": ["PA0004"],
                "gene": ["lasR"],
                "product": ["quorum sensing transcriptional regulator"],
            }
        )

        result = compute_virulence_layer_features(df, self.config)

        self.assertGreaterEqual(float(result.loc[0, "quorum_sensing_score"]), 0.90)

    def test_sublayers_integrate_into_virulence_severity_score(self) -> None:
        df = pd.DataFrame(
            {
                "protein_id": ["PA0005"],
                "direct_host_damage_score": [0.90],
                "colonization_score": [0.80],
                "immune_evasion_score": [0.70],
                "biofilm_persistence_score": [0.60],
                "toxin_activity_score": [0.90],
                "nutritional_immunity_escape_score": [0.50],
                "quorum_sensing_score": [0.40],
                "antivirulence_target_score": [0.42],
            }
        )

        result = compute_virulence_layer_features(df, self.config)

        self.assertGreater(float(result.loc[0, "virulence_severity_score"]), 0.60)
        self.assertEqual(float(result.loc[0, "antivirulence_target_score"]), 0.42)
        self.assertIn("antivirulence_target_score_preserved", result.loc[0, "audit_flags"])


if __name__ == "__main__":
    unittest.main()
