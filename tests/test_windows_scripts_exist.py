from __future__ import annotations

import unittest

from tests.helpers import PROJECT_ROOT


SCRIPT_NAMES = [
    "run_tests.ps1",
    "run_demo.ps1",
    "run_cpseudo_dryrun.ps1",
    "clean_project.ps1",
]


class WindowsScriptsExistTests(unittest.TestCase):
    def test_windows_scripts_exist(self) -> None:
        for script_name in SCRIPT_NAMES:
            with self.subTest(script=script_name):
                self.assertTrue((PROJECT_ROOT / "scripts" / script_name).exists())

    def test_python_scripts_have_python_exe_resolution(self) -> None:
        for script_name in ["run_tests.ps1", "run_demo.ps1", "run_cpseudo_dryrun.ps1"]:
            with self.subTest(script=script_name):
                text = (PROJECT_ROOT / "scripts" / script_name).read_text(encoding="utf-8")
                self.assertIn("PYTHON_EXE", text)
                self.assertIn("Resolve-Python", text)
                self.assertIn("python.exe", text)

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


if __name__ == "__main__":
    unittest.main()
