from __future__ import annotations

from unittest.mock import patch

import pytest

from scripts.run_online_only_validation import build_parser, main


def test_cli_exposes_explicit_diamond_options() -> None:
    help_text = build_parser().format_help()

    for flag in (
        "--candidate-seed-snapshot",
        "--enable-diamond",
        "--diamond-execution-mode",
        "--diamond-reference-fasta",
        "--diamond-database-prefix",
        "--diamond-cached-tsv",
        "--diamond-candidate-fasta",
        "--diamond-executable",
    ):
        assert flag in help_text


def test_cli_parses_explicit_diamond_execute_profile() -> None:
    args = build_parser().parse_args(
        [
            "--organism-key",
            "helicobacter_pylori",
            "--enable-diamond",
            "--diamond-execution-mode",
            "execute",
            "--diamond-reference-fasta",
            "reference.faa.gz",
            "--diamond-database-prefix",
            "human_reference",
        ]
    )

    assert args.enable_diamond is True
    assert args.diamond_execution_mode == "execute"
    assert args.diamond_reference_fasta == "reference.faa.gz"
    assert args.diamond_database_prefix == "human_reference"


@pytest.mark.parametrize(
    ("requested", "canonical"),
    [("online_strict", "online_strict"), ("online_only", "online_strict"), ("hybrid_curated", "hybrid_curated")],
)
def test_cli_execution_path_passes_canonical_mode_to_validation(requested: str, canonical: str) -> None:
    completed = {"pipeline_status": "completed"}
    with patch("scripts.run_online_only_validation.run_standard_validation", return_value=completed) as runner:
        exit_code = main(["--organism", "Escherichia coli", "--taxon-id", "562", "--online-source-mode", requested])

    assert exit_code == 0
    assert runner.call_args.kwargs["online_source_mode"] == canonical


def test_cli_rejects_unknown_online_mode_with_clear_argparse_error(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--organism", "Escherichia coli", "--online-source-mode", "invented_mode"])

    assert exc.value.code == 2
    error = capsys.readouterr().err
    assert "invalid choice" in error
    assert "invented_mode" in error


def test_cli_passes_candidate_seed_snapshot_to_validation() -> None:
    completed = {"pipeline_status": "completed"}

    with patch(
        "scripts.run_online_only_validation.run_standard_validation",
        return_value=completed,
    ) as runner:
        exit_code = main(
            [
                "--organism",
                "Helicobacter pylori",
                "--taxon-id",
                "210",
                "--max-candidates",
                "25",
                "--candidate-seed-snapshot",
                "snapshot/path",
            ]
        )

    assert exit_code == 0
    assert (
        runner.call_args.kwargs["candidate_seed_snapshot"]
        == "snapshot/path"
    )
