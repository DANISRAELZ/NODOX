from __future__ import annotations

import unittest

from tests.helpers import PROJECT_ROOT


SCRIPT_NAMES = [
    "run_tests.ps1",
    "run_demo.ps1",
    "run_cpseudo_dryrun.ps1",
    "run_corynebacterium_online_demo.ps1",
    "clean_project.ps1",
]


class WindowsScriptsExistTests(unittest.TestCase):
    def test_windows_scripts_exist(self) -> None:
        for script_name in SCRIPT_NAMES:
            with self.subTest(script=script_name):
                self.assertTrue((PROJECT_ROOT / "scripts" / script_name).exists())

    def test_python_scripts_have_python_exe_resolution(self) -> None:
        for script_name in [
            "run_tests.ps1",
            "run_demo.ps1",
            "run_cpseudo_dryrun.ps1",
            "run_corynebacterium_online_demo.ps1",
        ]:
            with self.subTest(script=script_name):
                text = (PROJECT_ROOT / "scripts" / script_name).read_text(encoding="utf-8")
                self.assertIn("PYTHON_EXE", text)
                self.assertIn("Resolve-Python", text)
                self.assertIn("python.exe", text)

    def test_windows_scripts_do_not_hardcode_user_python_path(self) -> None:
        for script_name in [
            "run_tests.ps1",
            "run_demo.ps1",
            "run_corynebacterium_online_demo.ps1",
        ]:
            with self.subTest(script=script_name):
                text = (PROJECT_ROOT / "scripts" / script_name).read_text(encoding="utf-8")
                self.assertNotIn("C:\\Users\\danis", text)
                self.assertIn("$env:USERPROFILE", text)

    def test_run_tests_script_uses_stable_offline_suite(self) -> None:
        text = (PROJECT_ROOT / "scripts" / "run_tests.ps1").read_text(encoding="utf-8")
        self.assertIn("-p no:cacheprovider", text)
        self.assertIn('-m "not online"', text)
        self.assertIn("Stable offline", text)

    def test_demo_script_labels_pao1_as_demo_only(self) -> None:
        text = (PROJECT_ROOT / "scripts" / "run_demo.ps1").read_text(encoding="utf-8")
        self.assertIn("PAO1 demo pipeline", text)
        self.assertIn("not as a project default", text)
        self.assertIn("replace --organism and --strain", text)

    def test_cpseudo_script_is_real_dry_run_without_demo_data(self) -> None:
        text = (PROJECT_ROOT / "scripts" / "run_cpseudo_dryrun.ps1").read_text(encoding="utf-8")
        self.assertIn("--dry-run", text)
        self.assertIn("-Organism", text)
        self.assertIn("-Strain", text)
        self.assertNotIn("--allow-demo-data", text)

    def test_clean_script_preserves_user_data_by_default(self) -> None:
        text = (PROJECT_ROOT / "scripts" / "clean_project.ps1").read_text(encoding="utf-8")
        self.assertIn("GeneratedOutputs", text)
        self.assertIn("data_user", text)
        self.assertNotIn('Remove-PathSafe -PathValue "data_user"', text)
        self.assertNotIn("Remove-Item -LiteralPath data_user", text)

    def test_windows_execution_guide_exists(self) -> None:
        path = PROJECT_ROOT / "docs" / "windows_execution_guide.md"
        self.assertTrue(path.exists())
        text = path.read_text(encoding="utf-8")
        self.assertIn("PowerShell", text)
        self.assertIn("PYTHON_EXE", text)
        self.assertIn("Corynebacterium pseudotuberculosis", text)
        self.assertIn("<RUTA_DEL_REPOSITORIO>", text)
        self.assertNotIn("C:\\Users\\danis", text)


if __name__ == "__main__":
    unittest.main()
