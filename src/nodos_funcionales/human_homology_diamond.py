from __future__ import annotations

import subprocess
import re
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen, urlretrieve

import pandas as pd


DIAMOND_COLUMNS = [
    "qseqid",
    "sseqid",
    "pident",
    "length",
    "qlen",
    "slen",
    "qstart",
    "qend",
    "sstart",
    "send",
    "evalue",
    "bitscore",
]

OUTPUT_COLUMNS = [
    "protein_id",
    "gene",
    "human_homolog",
    "evalue",
    "human_gene",
    "human_hit_id",
    "human_hit_name",
    "percent_identity",
    "query_coverage",
    "subject_coverage",
    "bit_score",
    "shared_domain_count",
    "source_database",
    "database",
    "evidence_source_type",
    "curator_notes",
    "human_uniprot_accession",
    "human_uniprot_id",
    "homology_lookup_status",
    "homology_query_strategy",
    "homology_evidence_tier",
    "homology_confidence_score",
    "homology_missing_flags",
    "homology_evidence_note",
    "orthology_method",
    "orthology_tool",
    "orthology_version",
    "orthology_reference",
    "orthology_query_coverage",
    "orthology_subject_coverage",
    "orthology_percent_identity",
    "orthology_bitscore",
    "orthology_confidence_score",
    "orthology_evidence_note",
]

NO_HIT_NOTE = (
    "Sin similitud humana detectable bajo los parametros utilizados; "
    "esto no demuestra ausencia absoluta de homologia."
)


@dataclass(frozen=True)
class DiamondHomologyConfig:
    enabled: bool = False
    execution_mode: str = "cache_only"
    diamond_executable: str = "diamond"
    reference_proteome_accession: str = "UP000005640"
    reference_fasta_path: str = ""
    reference_download_url: str = "https://rest.uniprot.org/uniprotkb/stream?compressed=false&format=fasta&query=proteome:UP000005640"
    database_prefix: str = ""
    sensitivity_mode: str = "ultra-sensitive"
    evalue_threshold: float = 1.0e-5
    max_target_seqs: int = 25
    threads: int = 1
    allow_download: bool = False
    allow_execution: bool = False
    reuse_cache: bool = True
    candidate_fasta_path: str = ""
    cached_tsv_path: str = ""
    output_filename: str = "human_homologs.csv"
    timeout_seconds: int = 600
    strong_evalue: float = 1.0e-10
    strong_percent_identity: float = 25.0
    strong_query_coverage: float = 0.50
    strong_subject_coverage: float = 0.50
    partial_evalue: float = 1.0e-5
    partial_percent_identity: float = 20.0
    partial_query_coverage: float = 0.20
    weak_human_homolog_value: str = "unresolved"
    database_label: str = "computed_diamond_human_homology_v1"
    sequence_batch_size: int = 50
    provider_base_url: str = "https://rest.uniprot.org/uniprotkb/stream"
    provider_timeout_seconds: float = 30.0
    provider_user_agent: str = "nodos-funcionales-human-homology-diamond/1.0"


def config_from_mapping(raw: dict[str, Any] | None) -> DiamondHomologyConfig:
    data = dict(raw or {})
    strong = dict(data.pop("strong_homology_thresholds", {}) or {})
    partial = dict(data.pop("partial_similarity_thresholds", {}) or {})
    aliases = {
        "diamond_executable": "diamond_executable",
        "reference_proteome_accession": "reference_proteome_accession",
        "reference_fasta_path": "reference_fasta_path",
        "database_prefix": "database_prefix",
        "sensitivity_mode": "sensitivity_mode",
        "evalue_threshold": "evalue_threshold",
        "maximum_target_sequences": "max_target_seqs",
        "threads": "threads",
        "allow_download": "allow_download",
        "timeout": "timeout_seconds",
        "timeout_seconds": "timeout_seconds",
    }
    normalized: dict[str, Any] = {}
    for key, value in data.items():
        normalized[aliases.get(key, key)] = value
    threshold_aliases = {
        "evalue": "strong_evalue",
        "percent_identity": "strong_percent_identity",
        "query_coverage": "strong_query_coverage",
        "subject_coverage": "strong_subject_coverage",
    }
    for key, value in strong.items():
        normalized[threshold_aliases.get(key, f"strong_{key}")] = value
    partial_aliases = {
        "evalue": "partial_evalue",
        "percent_identity": "partial_percent_identity",
        "query_coverage": "partial_query_coverage",
    }
    for key, value in partial.items():
        normalized[partial_aliases.get(key, f"partial_{key}")] = value
    return DiamondHomologyConfig(**{k: v for k, v in normalized.items() if k in DiamondHomologyConfig.__dataclass_fields__})


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def resolve_config_path(path_value: str, workspace: Path, base_dir: Path | None = None, *, default_workspace_relative: bool = False) -> Path:
    path_text = str(path_value or "").strip()
    if not path_text:
        raise ValueError("Ruta de configuracion vacia")
    path = Path(path_text)
    if path.is_absolute():
        return path
    base = workspace if default_workspace_relative else (base_dir or repository_root())
    return base / path


def default_candidate_fasta_path(workspace: Path) -> Path:
    return workspace / "data_external" / "candidate_proteins.faa"


def count_fasta_records(path: Path) -> int:
    validate_fasta_has_sequences(path)
    return sum(1 for line in path.read_text(encoding="utf-8", errors="ignore").splitlines() if line.strip().startswith(">"))


def _chunked(values: list[str], size: int) -> list[list[str]]:
    return [values[idx : idx + size] for idx in range(0, len(values), size)]


def _normalise_accession(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    protein_id, _ = _split_query_id(text)
    return protein_id.strip().upper()


def candidate_accessions_from_dataframe(candidates: pd.DataFrame) -> list[str]:
    if candidates.empty:
        return []
    accessions: list[str] = []
    for _, row in candidates.iterrows():
        raw = row.get("candidate_seed_accession")
        if pd.isna(raw) or not str(raw).strip():
            raw = row.get("uniprot_accession")
        if pd.isna(raw) or not str(raw).strip():
            raw = row.get("protein_id")
        accession = _normalise_accession(raw)
        if accession and accession not in accessions:
            accessions.append(accession)
    return accessions


def candidate_accessions_from_workspace(workspace: Path) -> list[str]:
    paths = [
        workspace / "data_external" / "essentiality.csv",
        workspace / "data_raw" / "essentiality.csv",
        workspace / "data_raw" / "uniprot_annotations.csv",
    ]
    for path in paths:
        if not path.exists():
            continue
        df = pd.read_csv(path)
        accessions = candidate_accessions_from_dataframe(df)
        if accessions:
            return accessions
    return []


def _fasta_accessions(fasta_text: str) -> set[str]:
    accessions: set[str] = set()
    for raw_line in fasta_text.splitlines():
        line = raw_line.strip()
        if not line.startswith(">"):
            continue
        protein_id, _ = _split_query_id(line[1:])
        accession = _normalise_accession(protein_id)
        if accession:
            accessions.add(accession)
    return accessions


def _fetch_uniprot_fasta_batch(accessions: list[str], cfg: DiamondHomologyConfig) -> str:
    query = " OR ".join(f"accession:{accession}" for accession in accessions)
    params = urlencode({"query": query, "format": "fasta"})
    url = f"{cfg.provider_base_url}?{params}"
    request_headers = {"User-Agent": cfg.provider_user_agent, "Accept": "text/x-fasta"}
    # urllib Request is imported lazily to keep tests free to monkeypatch urlopen only.
    from urllib.request import Request

    request = Request(url, headers=request_headers)
    with urlopen(request, timeout=float(cfg.provider_timeout_seconds)) as response:
        return response.read().decode("utf-8")


def _seed_fasta_blocks(seed_records: dict[str, Any] | None, wanted_accessions: set[str]) -> list[str]:
    """Build auditable FASTA records from UniProt seed JSON when sequences are already present."""
    blocks: list[str] = []
    for entry in (seed_records or {}).get("results", []) or []:
        if not isinstance(entry, dict):
            continue
        accession = _normalise_accession(entry.get("primaryAccession") or entry.get("uniProtkbId"))
        sequence_value = (entry.get("sequence") or {}).get("value") if isinstance(entry.get("sequence"), dict) else ""
        sequence = re.sub(r"\s+", "", str(sequence_value or "")).upper()
        if not accession or accession not in wanted_accessions or not sequence:
            continue
        entry_id = str(entry.get("uniProtkbId") or accession).strip()
        blocks.append(f">{accession}|{entry_id}\n{sequence}")
    return blocks


def materialize_candidate_fasta(
    workspace: Path,
    raw_cfg: dict[str, Any] | None,
    candidates: pd.DataFrame | None = None,
    mode: str = "online_optional",
    seed_records: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cfg = config_from_mapping(raw_cfg)
    output_path = default_candidate_fasta_path(workspace)
    manifest_path = workspace / "results" / "human_homology_candidate_fasta_manifest.json"
    accessions = candidate_accessions_from_dataframe(candidates) if candidates is not None else candidate_accessions_from_workspace(workspace)
    manifest: dict[str, Any] = {
        "provider_name": "human_homology_diamond",
        "source_provider": "uniprot_rest",
        "query_fasta_path": str(output_path),
        "candidate_accession_count": int(len(accessions)),
        "candidate_sequence_count": 0,
        "missing_sequence_count": int(len(accessions)),
        "missing_accessions": accessions,
        "retrieval_status": "not_started",
        "execution_status": "not_started",
        "online_source_mode": mode,
        "download_allowed": mode not in {"offline_only", "local", "api_stub"},
        "download_attempted": False,
        "download_successful": False,
        "retrieved_sequence_count": 0,
        "seed_sequence_count": 0,
        "fallback_reason": "",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    existing_text = ""
    recovered_accessions: set[str] = set()
    if output_path.exists():
        try:
            sequence_count = count_fasta_records(output_path)
        except (FileNotFoundError, ValueError) as exc:
            manifest.update({"retrieval_status": "existing_fasta_invalid", "fallback_reason": str(exc)})
        else:
            existing_text = output_path.read_text(encoding="utf-8", errors="ignore").strip()
            recovered_accessions = _fasta_accessions(existing_text)
            missing = [accession for accession in accessions if accession not in recovered_accessions]
            manifest.update(
                {
                    "candidate_sequence_count": sequence_count,
                    "missing_sequence_count": int(len(missing)),
                    "missing_accessions": missing,
                    "retrieval_status": "existing_fasta_reused",
                    "execution_status": "cache_reused",
                }
            )
            if not missing or not manifest["download_allowed"]:
                manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=True), encoding="utf-8")
                return manifest
    if not manifest["download_allowed"]:
        manifest.update(
            {
                "retrieval_status": "candidate_fasta_unavailable_offline_or_cache_only",
                "execution_status": "not_started",
                "fallback_reason": f"Candidate FASTA is incomplete or unavailable and online_source_mode={mode} does not allow sequence retrieval.",
            }
        )
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=True), encoding="utf-8")
        return manifest
    if not accessions:
        manifest.update(
            {
                "retrieval_status": "no_candidate_accessions",
                "execution_status": "not_started",
                "fallback_reason": "No candidate accessions were available for FASTA materialization.",
            }
        )
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=True), encoding="utf-8")
        return manifest

    fasta_blocks: list[str] = [existing_text] if existing_text else []
    seed_blocks = _seed_fasta_blocks(seed_records, set(accessions) - recovered_accessions)
    fasta_blocks.extend(seed_blocks)
    for block in seed_blocks:
        recovered_accessions.update(_fasta_accessions(block))
    manifest["seed_sequence_count"] = len(seed_blocks)
    errors: list[str] = []
    unresolved_accessions = [accession for accession in accessions if accession not in recovered_accessions]
    manifest["download_attempted"] = bool(unresolved_accessions)
    downloaded_accessions: set[str] = set()
    for batch in _chunked(unresolved_accessions, max(1, int(cfg.sequence_batch_size))):
        try:
            fasta_text = _fetch_uniprot_fasta_batch(batch, cfg)
        except Exception as exc:  # noqa: BLE001 - recorded as unresolved sequence retrieval.
            errors.append(f"{','.join(batch)}:{exc}")
            continue
        if fasta_text.strip():
            fasta_blocks.append(fasta_text.strip())
            batch_recovered = _fasta_accessions(fasta_text)
            recovered_accessions.update(batch_recovered)
            downloaded_accessions.update(batch_recovered)
    missing = [accession for accession in accessions if accession not in recovered_accessions]
    if fasta_blocks:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("\n".join(fasta_blocks) + "\n", encoding="utf-8")
        sequence_count = count_fasta_records(output_path)
        status = "candidate_fasta_materialized" if not missing else "candidate_fasta_partial"
    else:
        sequence_count = 0
        status = "candidate_fasta_unresolved"
    manifest.update(
        {
            "candidate_sequence_count": int(sequence_count),
            "retrieved_sequence_count": int(len(downloaded_accessions)),
            "download_successful": bool(downloaded_accessions),
            "missing_sequence_count": int(len(missing)),
            "missing_accessions": missing,
            "retrieval_status": status,
            "execution_status": "sequence_retrieval_completed" if sequence_count else "sequence_retrieval_failed",
            "fallback_reason": "; ".join(errors),
            "errors": errors,
        }
    )
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=True), encoding="utf-8")
    return manifest


def diamond_is_available(executable: str = "diamond") -> bool:
    try:
        subprocess.run([executable, "--version"], capture_output=True, text=True, timeout=10, check=False)
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return False
    return True


def get_diamond_version(executable: str = "diamond") -> str:
    try:
        result = subprocess.run([executable, "--version"], capture_output=True, text=True, timeout=10, check=False)
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return "not_available"
    text = (result.stdout or result.stderr or "").strip()
    return text or "unknown"


def validate_fasta_has_sequences(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"FASTA no encontrado: {path}")
    sequence_count = 0
    has_residues = False
    for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith(">"):
            sequence_count += 1
        else:
            has_residues = True
    if sequence_count == 0 or not has_residues:
        raise ValueError(f"FASTA sin secuencias utilizables: {path}")


def parse_fasta_records(path: Path) -> dict[str, dict[str, Any]]:
    validate_fasta_has_sequences(path)

    records: dict[str, dict[str, Any]] = {}
    current_id = ""
    current_gene = ""
    current_header = ""
    sequence_parts: list[str] = []

    def store_current() -> None:
        if not current_id:
            return

        sequence = "".join(sequence_parts).strip()

        records[current_id] = {
            "protein_id": current_id,
            "gene": current_gene or current_id,
            "header": current_header,
            "sequence": sequence,
            "sequence_length": len(sequence),
        }

    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()

            if not line:
                continue

            if line.startswith(">"):
                store_current()

                current_header = line[1:].strip()
                token = current_header.split()[0]
                parts = token.split("|")

                if len(parts) >= 3 and parts[0].lower() in {"sp", "tr"}:
                    current_id = parts[1].strip()
                    entry_name = parts[2].strip()
                elif len(parts) >= 2:
                    current_id = parts[0].strip()
                    entry_name = parts[1].strip()
                else:
                    current_id = token
                    entry_name = token

                gene = ""

                for field in current_header.split():
                    if field.startswith("GN="):
                        gene = field[3:].strip()
                        break

                if not gene:
                    gene = entry_name.split("_", 1)[0].strip()

                current_gene = gene or current_id
                sequence_parts = []
            else:
                sequence_parts.append(line)

    store_current()
    return records

def locate_or_download_reference_fasta(workspace: Path, cfg: DiamondHomologyConfig, base_dir: Path | None = None) -> Path:
    fasta_path = resolve_config_path(cfg.reference_fasta_path, workspace, base_dir)
    if fasta_path.exists():
        validate_fasta_has_sequences(fasta_path)
        return fasta_path
    if not cfg.allow_download:
        raise FileNotFoundError(f"Proteoma humano de referencia no disponible: {fasta_path}")
    fasta_path.parent.mkdir(parents=True, exist_ok=True)
    urlretrieve(cfg.reference_download_url, fasta_path)
    validate_fasta_has_sequences(fasta_path)
    return fasta_path


def locate_candidate_fasta(workspace: Path, cfg: DiamondHomologyConfig) -> Path:
    if cfg.candidate_fasta_path:
        path = resolve_config_path(cfg.candidate_fasta_path, workspace, default_workspace_relative=True)
        validate_fasta_has_sequences(path)
        return path
    default_path = default_candidate_fasta_path(workspace)
    validate_fasta_has_sequences(default_path)
    return default_path


def build_or_reuse_database(workspace: Path, cfg: DiamondHomologyConfig, reference_fasta: Path, base_dir: Path | None = None) -> Path:
    db_prefix = resolve_config_path(cfg.database_prefix, workspace, base_dir)
    db_path = db_prefix.with_suffix(".dmnd")
    if cfg.reuse_cache and db_path.exists():
        return db_path
    if not cfg.allow_execution:
        raise FileNotFoundError(f"Base DIAMOND no disponible en cache: {db_path}")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [cfg.diamond_executable, "makedb", "--in", str(reference_fasta), "--db", str(db_prefix)],
        capture_output=True,
        text=True,
        timeout=cfg.timeout_seconds,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"diamond makedb fallo: {(result.stderr or result.stdout).strip()}")
    return db_path


def run_diamond_blastp(workspace: Path, cfg: DiamondHomologyConfig, query_fasta: Path, db_path: Path) -> Path:
    output_path = workspace / "data_external" / "human_homology_diamond.tsv"
    if cfg.reuse_cache and output_path.exists():
        return output_path
    if not cfg.allow_execution:
        raise FileNotFoundError(f"TSV DIAMOND no disponible en cache: {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    db_prefix = str(db_path.with_suffix(""))
    command = [
        cfg.diamond_executable,
        "blastp",
        "--query",
        str(query_fasta),
        "--db",
        db_prefix,
        "--out",
        str(output_path),
        "--outfmt",
        "6",
        *DIAMOND_COLUMNS,
        "--evalue",
        str(cfg.evalue_threshold),
        "--max-target-seqs",
        str(cfg.max_target_seqs),
        "--threads",
        str(cfg.threads),
        f"--{cfg.sensitivity_mode}",
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=cfg.timeout_seconds, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"diamond blastp fallo: {(result.stderr or result.stdout).strip()}")
    return output_path


def _split_query_id(qseqid: object) -> tuple[str, str]:
    raw = str(qseqid or "").strip().lstrip(">")
    token = raw.split()[0] if raw else ""

    parts = token.split("|")

    if len(parts) >= 3 and parts[0].lower() in {"sp", "tr"}:
        protein_id = parts[1].strip()
        entry_name = parts[2].strip()
    elif len(parts) >= 2:
        protein_id = parts[0].strip()
        entry_name = parts[1].strip()
    else:
        protein_id = token
        entry_name = token

    gene = entry_name.split("_", 1)[0].strip()

    if not gene:
        gene = protein_id

    return protein_id, gene

def _split_human_hit(sseqid: object) -> tuple[str, str, str]:
    text = str(sseqid or "").strip()
    parts = text.split("|")
    if len(parts) >= 3:
        accession = parts[1].strip()
        uniprot_id = parts[2].strip()
    else:
        accession = text
        uniprot_id = text
    return accession, uniprot_id, uniprot_id


def classify_hit(row: pd.Series, cfg: DiamondHomologyConfig) -> str:
    if pd.isna(row.get("sseqid")) or str(row.get("sseqid", "")).strip() == "":
        return "no_detectable_human_similarity"
    evalue = float(row["evalue"])
    identity = float(row["pident"])
    query_coverage = float(row["query_coverage"])
    subject_coverage = float(row["subject_coverage"])
    if (
        evalue <= cfg.strong_evalue
        and identity >= cfg.strong_percent_identity
        and query_coverage >= cfg.strong_query_coverage
        and subject_coverage >= cfg.strong_subject_coverage
    ):
        return "strong_human_sequence_homology"
    if evalue <= cfg.partial_evalue and identity >= cfg.partial_percent_identity and query_coverage >= cfg.partial_query_coverage:
        return "partial_human_sequence_similarity"
    return "weak_low_coverage_similarity"


def human_homolog_value_for_tier(tier: str, cfg: DiamondHomologyConfig) -> object:
    if tier in {"strong_human_sequence_homology", "partial_human_sequence_similarity"}:
        return 1
    if tier == "no_detectable_human_similarity":
        return 0
    return 0 if str(cfg.weak_human_homolog_value).lower() == "zero" else pd.NA


def normalize_coverage_value(value: object) -> float | object:
    """Normalize coverage to [0, 1] without double-converting cached proportions."""
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(numeric):
        return pd.NA
    numeric = float(numeric)
    if numeric < 0.0 or numeric > 100.0:
        return pd.NA
    if numeric > 1.0:
        return numeric / 100.0
    return numeric


def normalize_diamond_coverage_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Keep canonical and orthology coverage columns on the same idempotent scale."""
    result = df.copy()
    coverage_columns = [
        "query_coverage",
        "subject_coverage",
        "orthology_query_coverage",
        "orthology_subject_coverage",
    ]
    invalid_by_row: dict[object, list[str]] = {}
    for column in coverage_columns:
        if column not in result.columns:
            continue
        original = pd.to_numeric(result[column], errors="coerce")
        invalid = original.notna() & ((original < 0.0) | (original > 100.0))
        for idx in result.index[invalid]:
            invalid_by_row.setdefault(idx, []).append(f"invalid_{column}")
        result[column] = result[column].map(normalize_coverage_value)
    for idx, flags in invalid_by_row.items():
        existing_value = result.at[idx, "homology_missing_flags"] if "homology_missing_flags" in result.columns else ""
        existing = "" if pd.isna(existing_value) else str(existing_value)
        tokens = [token for token in existing.split(";") if token and token.lower() != "nan"] + flags
        result.at[idx, "homology_missing_flags"] = "; ".join(dict.fromkeys(tokens))
        if "homology_evidence_note" in result.columns:
            note_value = result.at[idx, "homology_evidence_note"]
            note = "" if pd.isna(note_value) else str(note_value)
            result.at[idx, "homology_evidence_note"] = f"{note} Invalid coverage recorded: {', '.join(flags)}.".strip()
    return result


def _alignment_span_coverage(start: object, end: object, sequence_length: object) -> float | object:
    start_value = pd.to_numeric(pd.Series([start]), errors="coerce").iloc[0]
    end_value = pd.to_numeric(pd.Series([end]), errors="coerce").iloc[0]
    length_value = pd.to_numeric(pd.Series([sequence_length]), errors="coerce").iloc[0]
    if pd.isna(start_value) or pd.isna(end_value) or pd.isna(length_value) or float(length_value) <= 0.0:
        return pd.NA
    return normalize_coverage_value((abs(float(end_value) - float(start_value)) + 1.0) / float(length_value))


def parse_diamond_tsv(tsv_path: Path, query_fasta: Path, cfg: DiamondHomologyConfig) -> pd.DataFrame:
    queries = parse_fasta_records(query_fasta)
    if tsv_path.exists() and tsv_path.stat().st_size > 0:
        hits = pd.read_csv(tsv_path, sep="\t", names=DIAMOND_COLUMNS, header=None)
    else:
        hits = pd.DataFrame(columns=DIAMOND_COLUMNS)
    for column in ["pident", "length", "qlen", "slen", "qstart", "qend", "sstart", "send", "evalue", "bitscore"]:
        if column in hits.columns:
            hits[column] = pd.to_numeric(hits[column], errors="coerce")
    if not hits.empty:
        hits["qseqid_raw"] = hits["qseqid"].astype(str)
        hits["qseqid"] = hits["qseqid_raw"].map(
            lambda value: _split_query_id(value)[0]
        )
        hits["query_coverage"] = hits.apply(lambda row: _alignment_span_coverage(row["qstart"], row["qend"], row["qlen"]), axis=1)
        hits["subject_coverage"] = hits.apply(lambda row: _alignment_span_coverage(row["sstart"], row["send"], row["slen"]), axis=1)
        hits = hits.sort_values(["qseqid", "evalue", "bitscore"], ascending=[True, True, False])
        hits = hits.drop_duplicates(subset=["qseqid"], keep="first")

    rows: list[dict[str, Any]] = []
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    diamond_version = get_diamond_version(cfg.diamond_executable)
    hit_by_query = {str(row["qseqid"]): row for _, row in hits.iterrows()}
    for query_token, query in queries.items():
        qseqid = f"{query['protein_id']}|{query['gene']}"
        hit = hit_by_query.get(qseqid)
        if hit is None:
            hit = hit_by_query.get(str(query["protein_id"]))
        if hit is None:
            tier = "no_detectable_human_similarity"
            rows.append(_output_row_for_no_hit(query, cfg, run_id, diamond_version, tier))
            continue
        hit = hit.copy()
        tier = classify_hit(hit, cfg)
        rows.append(_output_row_for_hit(query, hit, cfg, run_id, diamond_version, tier))
    return normalize_diamond_coverage_columns(pd.DataFrame(rows, columns=OUTPUT_COLUMNS))


def _confidence_for_tier(tier: str) -> float:
    return {
        "strong_human_sequence_homology": 0.90,
        "partial_human_sequence_similarity": 0.72,
        "weak_low_coverage_similarity": 0.35,
        "no_detectable_human_similarity": 0.62,
    }.get(tier, 0.20)


def _output_row_for_hit(
    query: dict[str, Any],
    hit: pd.Series,
    cfg: DiamondHomologyConfig,
    run_id: str,
    diamond_version: str,
    tier: str,
) -> dict[str, Any]:
    accession, uniprot_id, hit_name = _split_human_hit(hit["sseqid"])
    note = (
        f"DIAMOND blastp {cfg.sensitivity_mode}; reference={cfg.reference_proteome_accession}; "
        f"evalue_threshold={cfg.evalue_threshold}; run_id={run_id}."
    )
    confidence = _confidence_for_tier(tier)
    return {
        "protein_id": query["protein_id"],
        "gene": query["gene"],
        "human_homolog": human_homolog_value_for_tier(tier, cfg),
        "evalue": hit["evalue"],
        "human_gene": hit_name,
        "human_hit_id": hit["sseqid"],
        "human_hit_name": hit_name,
        "percent_identity": hit["pident"],
        "query_coverage": hit["query_coverage"],
        "subject_coverage": hit["subject_coverage"],
        "bit_score": hit["bitscore"],
        "shared_domain_count": pd.NA,
        "source_database": cfg.database_label,
        "database": cfg.database_label,
        "evidence_source_type": "sequence_alignment",
        "curator_notes": note,
        "human_uniprot_accession": accession,
        "human_uniprot_id": uniprot_id,
        "homology_lookup_status": "diamond_hit",
        "homology_query_strategy": "diamond_blastp_sequence_alignment",
        "homology_evidence_tier": tier,
        "homology_confidence_score": confidence,
        "homology_missing_flags": "missing_shared_domain_count",
        "homology_evidence_note": note,
        "orthology_method": "diamond_blastp",
        "orthology_tool": "DIAMOND",
        "orthology_version": diamond_version,
        "orthology_reference": cfg.reference_proteome_accession,
        "orthology_query_coverage": hit["query_coverage"],
        "orthology_subject_coverage": hit["subject_coverage"],
        "orthology_percent_identity": hit["pident"],
        "orthology_bitscore": hit["bitscore"],
        "orthology_confidence_score": confidence,
        "orthology_evidence_note": note,
    }


def _output_row_for_no_hit(
    query: dict[str, Any],
    cfg: DiamondHomologyConfig,
    run_id: str,
    diamond_version: str,
    tier: str,
) -> dict[str, Any]:
    note = (
        f"{NO_HIT_NOTE} DIAMOND blastp {cfg.sensitivity_mode}; "
        f"reference={cfg.reference_proteome_accession}; evalue_threshold={cfg.evalue_threshold}; run_id={run_id}."
    )
    confidence = _confidence_for_tier(tier)
    return {
        "protein_id": query["protein_id"],
        "gene": query["gene"],
        "human_homolog": 0,
        "evalue": pd.NA,
        "human_gene": "none",
        "human_hit_id": "",
        "human_hit_name": "",
        "percent_identity": pd.NA,
        "query_coverage": pd.NA,
        "subject_coverage": pd.NA,
        "bit_score": pd.NA,
        "shared_domain_count": pd.NA,
        "source_database": cfg.database_label,
        "database": cfg.database_label,
        "evidence_source_type": "sequence_alignment",
        "curator_notes": note,
        "human_uniprot_accession": "",
        "human_uniprot_id": "",
        "homology_lookup_status": "diamond_no_hit",
        "homology_query_strategy": "diamond_blastp_sequence_alignment",
        "homology_evidence_tier": tier,
        "homology_confidence_score": confidence,
        "homology_missing_flags": "missing_alignment_hit; missing_human_uniprot_accession",
        "homology_evidence_note": note,
        "orthology_method": "diamond_blastp",
        "orthology_tool": "DIAMOND",
        "orthology_version": diamond_version,
        "orthology_reference": cfg.reference_proteome_accession,
        "orthology_query_coverage": pd.NA,
        "orthology_subject_coverage": pd.NA,
        "orthology_percent_identity": pd.NA,
        "orthology_bitscore": pd.NA,
        "orthology_confidence_score": confidence,
        "orthology_evidence_note": note,
    }


def build_human_homologs_with_diamond(
    workspace: Path,
    raw_cfg: dict[str, Any] | None,
    base_dir: Path | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    cfg = config_from_mapping(raw_cfg)
    diamond_version = get_diamond_version(cfg.diamond_executable) if cfg.enabled else "not_checked_provider_disabled"
    manifest: dict[str, Any] = {
        "provider_name": "human_homology_diamond",
        "diamond_version": diamond_version,
        "query_fasta_path": "",
        "candidate_sequence_count": 0,
        "missing_sequence_count": 0,
        "reference_fasta_path": "",
        "database_path": "",
        "tsv_path": "",
        "retrieval_status": "not_started",
        "execution_status": "not_started",
        "execution_started": False,
        "execution_completed": False,
        "execution_failed": False,
        "fallback_reason": "",
        "notes": [],
    }
    if not cfg.enabled:
        manifest.update({"status": "diamond_provider_disabled", "retrieval_status": "disabled", "execution_status": "disabled", "notes": ["diamond provider disabled"]})
        return pd.DataFrame(columns=OUTPUT_COLUMNS), manifest
    try:
        query_fasta = locate_candidate_fasta(workspace, cfg)
    except (FileNotFoundError, ValueError) as exc:
        manifest.update(
            {
                "status": "diamond_query_fasta_unavailable",
                "retrieval_status": "diamond_query_fasta_unavailable",
                "execution_status": "not_started",
                "fallback_reason": str(exc),
                "notes": [str(exc)],
            }
        )
        return pd.DataFrame(columns=OUTPUT_COLUMNS), manifest
    manifest["query_fasta_path"] = str(query_fasta)
    manifest["candidate_sequence_count"] = count_fasta_records(query_fasta)
    candidate_manifest_path = workspace / "results" / "human_homology_candidate_fasta_manifest.json"
    if candidate_manifest_path.exists():
        try:
            candidate_manifest = json.loads(candidate_manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            candidate_manifest = {}
        manifest["missing_sequence_count"] = int(candidate_manifest.get("missing_sequence_count", 0) or 0)
        manifest["missing_accessions"] = list(candidate_manifest.get("missing_accessions", []) or [])
    cached_tsv = resolve_config_path(cfg.cached_tsv_path, workspace, base_dir, default_workspace_relative=True) if cfg.cached_tsv_path else None
    if cached_tsv is not None and cached_tsv.exists() and cfg.reuse_cache:
        df = parse_diamond_tsv(cached_tsv, query_fasta, cfg)
        manifest.update(
            {
                "status": "diamond_cached_tsv_materialized",
                "retrieval_status": "diamond_cached_tsv_materialized",
                "execution_status": "cache_reused",
                "tsv_path": str(cached_tsv),
                "notes": [str(cached_tsv)],
            }
        )
        return df, manifest
    if not cfg.allow_execution or cfg.execution_mode in {"cache_only", "disabled"}:
        manifest.update(
            {
                "status": "diamond_cache_unavailable",
                "retrieval_status": "diamond_cache_unavailable",
                "execution_status": "execution_disabled",
                "fallback_reason": "No cached DIAMOND TSV was available and execution is disabled.",
                "notes": ["No cached DIAMOND TSV was available and execution is disabled."],
            }
        )
        return pd.DataFrame(columns=OUTPUT_COLUMNS), manifest
    if not diamond_is_available(cfg.diamond_executable):
        manifest.update(
            {
                "status": "diamond_executable_unavailable",
                "retrieval_status": "diamond_executable_unavailable",
                "execution_status": "executable_unavailable",
                "fallback_reason": f"Executable not available: {cfg.diamond_executable}",
                "notes": [f"Executable not available: {cfg.diamond_executable}"],
            }
        )
        return pd.DataFrame(columns=OUTPUT_COLUMNS), manifest
    manifest["execution_started"] = True
    manifest["execution_status"] = "started"
    try:
        configured_db_path = resolve_config_path(cfg.database_prefix, workspace, base_dir).with_suffix(".dmnd")
        if cfg.reuse_cache and configured_db_path.exists():
            db_path = configured_db_path
            reference_fasta = resolve_config_path(cfg.reference_fasta_path, workspace, base_dir)
        else:
            reference_fasta = locate_or_download_reference_fasta(workspace, cfg, base_dir)
            db_path = build_or_reuse_database(workspace, cfg, reference_fasta, base_dir)
        tsv_path = run_diamond_blastp(workspace, cfg, query_fasta, db_path)
        df = parse_diamond_tsv(tsv_path, query_fasta, cfg)
    except (FileNotFoundError, ValueError, RuntimeError, OSError, subprocess.TimeoutExpired) as exc:
        manifest.update(
            {
                "status": "diamond_execution_failed",
                "retrieval_status": "diamond_execution_failed",
                "execution_status": "failed",
                "execution_failed": True,
                "fallback_reason": str(exc),
                "notes": [str(exc)],
            }
        )
        return pd.DataFrame(columns=OUTPUT_COLUMNS), manifest
    manifest.update(
        {
            "status": "diamond_blastp_executed",
            "retrieval_status": "diamond_blastp_executed",
            "execution_status": "executed",
            "execution_completed": True,
            "reference_fasta_path": str(reference_fasta),
            "database_path": str(db_path),
            "tsv_path": str(tsv_path),
            "notes": [str(tsv_path)],
        }
    )
    return df, manifest
