from __future__ import annotations

from scripts.run_online_only_validation import build_parser


def test_cli_exposes_explicit_diamond_options() -> None:
    help_text = build_parser().format_help()

    for flag in (
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
