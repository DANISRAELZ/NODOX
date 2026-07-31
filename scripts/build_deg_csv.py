from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import re
import zipfile
from pathlib import Path


BUILDER_VERSION = "deg-local-adapter-v1"
OFFICIAL_COLUMNS = [
    "deg_id",
    "deg_gene_id",
    "gene",
    "gi",
    "cog",
    "functional_class",
    "product",
    "organism",
    "reference_accession",
    "experimental_condition",
    "essentiality",
    "go_terms",
    "uniprot_accessions",
]
OUTPUT_COLUMNS = [
    *OFFICIAL_COLUMNS,
    "evidence",
    "source_file",
    "provider",
    "affects_score",
]
CANDIDATE_EXTENSIONS = {".csv", ".tsv", ".txt", ".dat"}


def read_text_file(path: Path) -> str:
    if path.suffix.lower() == ".gz":
        with gzip.open(path, "rt", encoding="utf-8", errors="replace") as handle:
            return handle.read()
    return path.read_text(encoding="utf-8", errors="replace")


def find_deg_files(raw_dir: Path) -> list[Path]:
    files = []
    for path in raw_dir.rglob("*"):
        if not path.is_file():
            continue
        name = path.name.lower()
        if "deg" in name or "essential" in name:
            files.append(path)
    return sorted(files)


def extract_zip(path: Path, raw_dir: Path) -> list[Path]:
    extracted = []
    target_dir = raw_dir / f"{path.stem}_extracted"
    target_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path) as archive:
        for member in archive.infolist():
            if member.is_dir():
                continue
            filename = Path(member.filename).name
            if not filename or filename.startswith("._"):
                continue
            output_path = target_dir / filename
            with archive.open(member) as source, output_path.open("wb") as target:
                target.write(source.read())
            extracted.append(output_path)
    return extracted


def sniff_delimiter(sample: str) -> str | None:
    try:
        return csv.Sniffer().sniff(sample[:4096], delimiters=",\t;|").delimiter
    except csv.Error:
        for delimiter in ("\t", ";", ",", "|"):
            if delimiter in sample:
                return delimiter
    return None


def normalize_header(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")


def pick(row: dict[str, object], candidates: list[str]) -> str:
    normalized = {normalize_header(key): value for key, value in row.items() if key is not None}
    for candidate in candidates:
        value = normalized.get(normalize_header(candidate))
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def _normalized_output(values: dict[str, str], source_file: Path) -> dict[str, str]:
    return {
        **{column: str(values.get(column, "")).strip() for column in OFFICIAL_COLUMNS},
        "evidence": str(values.get("evidence") or values.get("experimental_condition") or "DEG curated record").strip(),
        "source_file": str(source_file),
        "provider": "DEG",
        "affects_score": "false",
    }


def _parse_official_headerless(rows: list[list[str]], source_file: Path) -> list[dict[str, str]]:
    output = []
    for row in rows:
        if len(row) < len(OFFICIAL_COLUMNS):
            continue
        values = {column: row[index].strip() for index, column in enumerate(OFFICIAL_COLUMNS)}
        if not re.fullmatch(r"DEG\d+", values["deg_id"], flags=re.IGNORECASE):
            continue
        output.append(_normalized_output(values, source_file))
    return output


def _parse_headered(rows: list[list[str]], source_file: Path) -> list[dict[str, str]]:
    if not rows:
        return []
    header = rows[0]
    output = []
    for values in rows[1:]:
        row = {header[index]: values[index] for index in range(min(len(header), len(values)))}
        normalized = {
            "deg_id": pick(row, ["DEG ID", "DEG_ID", "degid", "id"]),
            "deg_gene_id": pick(row, ["DEG gene ID", "deg_gene_id", "gene_id"]),
            "gene": pick(row, ["Gene", "gene", "Gene name", "gene_name", "symbol"]),
            "gi": pick(row, ["GI", "gi"]),
            "cog": pick(row, ["COG", "cog"]),
            "functional_class": pick(row, ["Functional class", "functional_class", "function"]),
            "product": pick(row, ["Product", "product", "description"]),
            "organism": pick(row, ["Organism", "organism", "Species", "species", "Strain", "strain"]),
            "reference_accession": pick(row, ["Reference accession", "reference_accession", "reference"]),
            "experimental_condition": pick(
                row,
                ["Experimental condition", "experimental_condition", "condition", "method"],
            ),
            "essentiality": pick(row, ["Essentiality", "essentiality", "Essential", "essential"]),
            "go_terms": pick(row, ["GO terms", "go_terms"]),
            "uniprot_accessions": pick(
                row,
                ["UniProt accessions", "uniprot_accessions", "uniprot_accession", "protein_id"],
            ),
            "evidence": pick(row, ["Evidence", "evidence", "experiment", "method"]),
        }
        if any(normalized.get(key) for key in ("deg_id", "deg_gene_id", "gene", "uniprot_accessions")):
            output.append(_normalized_output(normalized, source_file))
    return output


def parse_table(path: Path) -> list[dict[str, str]]:
    text = read_text_file(path)
    if "<html" in text.lower() or "<!doctype html" in text.lower():
        print(f"[skip] {path}: parece HTML, no tabla estructurada")
        return []
    delimiter = sniff_delimiter(text)
    if delimiter is None:
        print(f"[skip] {path}: no se pudo detectar delimitador")
        return []
    rows = list(csv.reader((line for line in text.splitlines() if line.strip()), delimiter=delimiter))
    if not rows:
        return []
    first_value = rows[0][0].strip().strip('"') if rows[0] else ""
    if re.fullmatch(r"DEG\d+", first_value, flags=re.IGNORECASE):
        return _parse_official_headerless(rows, path)
    return _parse_headered(rows, path)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_deg_csv(raw_dir: Path, output_path: Path, version_path: Path) -> int:
    if not raw_dir.exists():
        raise FileNotFoundError(f"No existe {raw_dir}")
    files = find_deg_files(raw_dir)
    expanded = []
    source_archives = []
    for path in files:
        if path.suffix.lower() == ".zip":
            source_archives.append(path)
            expanded.extend(extract_zip(path, raw_dir))
        else:
            expanded.append(path)
    usable = sorted(
        {
            path.resolve()
            for path in expanded
            if path.suffix.lower() in CANDIDATE_EXTENSIONS
            or ".gz" in [suffix.lower() for suffix in path.suffixes]
        }
    )
    all_rows = []
    for path in usable:
        rows = parse_table(path)
        print(f"[info] {path}: {len(rows)} filas")
        all_rows.extend(rows)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(all_rows)
    sources = source_archives or usable
    version_lines = [BUILDER_VERSION]
    version_lines.extend(f"{path.name} sha256={_sha256(path)}" for path in sources if path.exists())
    version_path.parent.mkdir(parents=True, exist_ok=True)
    version_path.write_text("\n".join(version_lines) + "\n", encoding="utf-8")
    return len(all_rows)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Normalize a manually downloaded DEG export into data_external/deg.csv.")
    parser.add_argument("--raw-dir", type=Path, default=Path("data_external/raw"))
    parser.add_argument("--output", type=Path, default=Path("data_external/deg.csv"))
    parser.add_argument("--version-output", type=Path, default=Path("data_external/deg.version.txt"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        row_count = build_deg_csv(args.raw_dir, args.output, args.version_output)
    except FileNotFoundError as exc:
        print(f"[error] {exc}")
        return 1
    print(f"[done] Escrito: {args.output}")
    print(f"[done] Filas DEG normalizadas: {row_count}")
    if row_count == 0:
        print("[warning] No se encontraron filas DEG estructuradas; no se infiere evidencia.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
