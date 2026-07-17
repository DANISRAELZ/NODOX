from pathlib import Path
import csv
import gzip
import zipfile
import re
import sys

RAW_DIR = Path("data_external/raw")
OUT = Path("data_external/deg.csv")

CANDIDATE_EXTENSIONS = {".csv", ".tsv", ".txt", ".dat"}

def read_text_file(path: Path) -> str:
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8", errors="replace") as f:
            return f.read()
    return path.read_text(encoding="utf-8", errors="replace")

def find_deg_files():
    files = []
    for p in RAW_DIR.rglob("*"):
        if not p.is_file():
            continue
        name = p.name.lower()
        if "deg" in name or "essential" in name:
            files.append(p)
    return files

def extract_zip(path: Path):
    extracted = []
    target_dir = RAW_DIR / f"{path.stem}_extracted"
    target_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(path) as z:
        for member in z.namelist():
            if member.endswith("/"):
                continue
            out_path = target_dir / Path(member).name
            with z.open(member) as src, open(out_path, "wb") as dst:
                dst.write(src.read())
            extracted.append(out_path)

    return extracted

def sniff_delimiter(sample: str):
    try:
        dialect = csv.Sniffer().sniff(sample[:4096], delimiters=",\t;|")
        return dialect.delimiter
    except Exception:
        if "\t" in sample:
            return "\t"
        if "," in sample:
            return ","
        return None

def normalize_header(h):
    return re.sub(r"[^a-z0-9]+", "_", str(h).strip().lower()).strip("_")

def pick(row, candidates):
    if not row:
        return ""

    normalized = {}
    for k, v in row.items():
        if k is None:
            continue
        normalized[normalize_header(k)] = v

    for candidate in candidates:
        key = normalize_header(candidate)
        value = normalized.get(key)
        if value is not None and str(value).strip() != "":
            return str(value).strip()

    return ""

def parse_table(path: Path):
    text = read_text_file(path)

    if "<html" in text.lower() or "<!doctype html" in text.lower():
        print(f"[skip] {path}: parece HTML, no tabla estructurada")
        return []

    delimiter = sniff_delimiter(text)
    if delimiter is None:
        print(f"[skip] {path}: no se pudo detectar delimitador")
        return []

    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return []

    reader = csv.DictReader(lines, delimiter=delimiter)
    rows = []

    for row in reader:
        deg_id = pick(row, ["DEG ID", "DEG_ID", "degid", "id", "Gene ID", "gene_id", "locus_tag"])
        gene = pick(row, ["Gene", "gene", "Gene name", "gene_name", "symbol"])
        organism = pick(row, ["Organism", "organism", "Species", "species", "Strain", "strain"])
        function = pick(row, ["Function", "function", "Description", "description", "Product", "product"])
        reference = pick(row, ["Reference", "reference", "PubMed", "pubmed", "PMID", "pmid"])
        essentiality = pick(row, ["Essentiality", "essentiality", "Essential", "essential"])

        if not any([deg_id, gene, organism, function]):
            continue

        rows.append({
            "deg_id": deg_id,
            "gene": gene,
            "organism": organism,
            "function": function,
            "reference": reference,
            "essentiality": essentiality,
            "source_file": str(path),
            "provider": "DEG",
            "affects_score": "false",
        })

    return rows

def main():
    if not RAW_DIR.exists():
        print(f"[error] No existe {RAW_DIR}")
        sys.exit(1)

    files = find_deg_files()

    expanded = []
    for p in files:
        if p.suffix.lower() == ".zip":
            try:
                expanded.extend(extract_zip(p))
            except Exception as e:
                print(f"[warn] No se pudo extraer {p}: {e}")
        else:
            expanded.append(p)

    usable = []
    for p in expanded:
        suffixes = [s.lower() for s in p.suffixes]
        if p.suffix.lower() in CANDIDATE_EXTENSIONS or ".gz" in suffixes:
            usable.append(p)

    print("[info] Archivos candidatos:")
    for p in usable:
        print(" -", p)

    all_rows = []
    for p in usable:
        try:
            rows = parse_table(p)
            print(f"[info] {p}: {len(rows)} filas")
            all_rows.extend(rows)
        except Exception as e:
            print(f"[warn] Error leyendo {p}: {e}")

    OUT.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "deg_id",
        "gene",
        "organism",
        "function",
        "reference",
        "essentiality",
        "source_file",
        "provider",
        "affects_score",
    ]

    with OUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"[done] Escrito: {OUT}")
    print(f"[done] Filas DEG normalizadas: {len(all_rows)}")

    if len(all_rows) == 0:
        print("[warning] Se creó deg.csv, pero sin filas. Probablemente DEG devolvió HTML o el archivo crudo no contiene tabla estructurada.")

if __name__ == "__main__":
    main()
