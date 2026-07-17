from __future__ import annotations

import gzip
import io
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd

from .online_http import get_ssl_context


SOURCE_MODES = {"offline_only", "cache_first", "online_optional"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_dump(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _cache_path(workspace: Path, config: dict[str, Any]) -> Path:
    return workspace / "config" / str(config["online_sources"]["human_essentiality"]["cache_filename"])


def load_human_essentiality_cache(workspace: Path, config: dict[str, Any]) -> dict[str, Any]:
    path = _cache_path(workspace, config)
    if not path.exists():
        return {"schema_version": 1, "updated_at_utc": None, "entries": {}}
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload.setdefault("schema_version", 1)
    payload.setdefault("updated_at_utc", None)
    payload.setdefault("entries", {})
    return payload


def save_human_essentiality_cache(workspace: Path, config: dict[str, Any], payload: dict[str, Any]) -> None:
    payload["updated_at_utc"] = _utc_now()
    _json_dump(_cache_path(workspace, config), payload)


def _request_bytes(url: str, timeout: float, user_agent: str) -> bytes:
    if (
        getattr(urlopen, "__module__", "") == "urllib.request"
        and sys.platform == "win32"
        and os.environ.get("NODOS_ALLOW_WINDOWS_REAL_HTTPS") != "1"
    ):
        raise URLError("windows_real_https_requires_diagnostic_opt_in")
    request = Request(url, headers={"User-Agent": user_agent, "Accept": "text/tab-separated-values,text/plain,*/*"})
    context = get_ssl_context() if getattr(urlopen, "__module__", "") == "urllib.request" and sys.platform != "win32" else None
    with urlopen(request, timeout=timeout, context=context) as response:
        return response.read()


def _api_get_bytes(url: str, cfg: dict[str, Any]) -> tuple[bytes | None, list[str]]:
    timeout = float(cfg["provider_timeout_seconds"])
    user_agent = str(cfg["provider_user_agent"])
    retries = int(cfg["provider_max_retries"])
    backoff = float(cfg["provider_backoff_seconds"])
    errors: list[str] = []
    for attempt in range(retries + 1):
        try:
            return _request_bytes(url, timeout=timeout, user_agent=user_agent), errors
        except HTTPError as exc:
            errors.append(f"HTTP {exc.code} en human_essentiality")
            if exc.code == 429 and attempt < retries:
                time.sleep(backoff)
                continue
            break
        except URLError as exc:
            errors.append(f"Error de red en human_essentiality: {exc.reason}")
            break
        except TimeoutError:
            errors.append("Timeout en human_essentiality")
            break
    return None, errors


def _request_json(url: str, timeout: float, user_agent: str) -> Any:
    if (
        getattr(urlopen, "__module__", "") == "urllib.request"
        and sys.platform == "win32"
        and os.environ.get("NODOS_ALLOW_WINDOWS_REAL_HTTPS") != "1"
    ):
        raise URLError("windows_real_https_requires_diagnostic_opt_in")
    request = Request(url, headers={"User-Agent": user_agent, "Accept": "application/json"})
    context = get_ssl_context() if getattr(urlopen, "__module__", "") == "urllib.request" and sys.platform != "win32" else None
    with urlopen(request, timeout=timeout, context=context) as response:
        return json.loads(response.read().decode("utf-8"))


def _query_ncbi_gene_id(symbol: str, cfg: dict[str, Any]) -> tuple[str, list[str]]:
    clean = str(symbol or "").strip()
    if not clean:
        return "", []
    params = {
        "terms": clean,
        "maxList": 1,
        "sf": "Symbol",
        "df": "GeneID,Symbol",
    }
    url = f"{str(cfg['ncbi_gene_api_url']).rstrip('/')}?{urlencode(params)}"
    timeout = float(cfg["provider_timeout_seconds"])
    user_agent = str(cfg["provider_user_agent"])
    try:
        payload = _request_json(url, timeout=timeout, user_agent=user_agent)
    except (HTTPError, URLError, TimeoutError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return "", [f"NCBI gene lookup failed for {clean}: {exc}"]
    rows = payload[3] if isinstance(payload, list) and len(payload) > 3 and isinstance(payload[3], list) else []
    if not rows:
        return "", []
    first = rows[0]
    if isinstance(first, list) and first:
        return str(first[0]).strip(), []
    return "", []


def _decode_table(raw: bytes) -> pd.DataFrame:
    if raw[:2] == b"\x1f\x8b":
        text = gzip.decompress(raw).decode("utf-8")
    else:
        text = raw.decode("utf-8")
    if not text.strip():
        return pd.DataFrame()
    return pd.read_csv(io.StringIO(text), sep="\t")


def _normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    normalised = df.copy()
    normalised.columns = [str(column).strip() for column in normalised.columns]
    column_lookup = {column.lower(): column for column in normalised.columns}
    rename = {}
    for target, aliases in {
        "human_gene": ["human_gene", "gene", "gene_symbol", "symbol", "genesymbol"],
        "entrez_gene_id": ["entrez_gene_id", "entrez", "geneid", "gene_id", "ncbi_gene_id"],
        "essentiality_status": ["essentiality_status", "human_essential", "essential", "status", "label"],
        "essentiality_score": ["essentiality_score", "score"],
    }.items():
        for alias in aliases:
            if alias in column_lookup:
                rename[column_lookup[alias]] = target
                break
    return normalised.rename(columns=rename)


def _is_essential_value(value: object) -> bool:
    text = str(value or "").strip().lower()
    return text in {"1", "true", "yes", "essential", "e", "essential_gene"}


def _table_to_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    if df.empty:
        return []
    normalised = _normalise_columns(df)
    records = []
    for _, row in normalised.iterrows():
        gene = str(row.get("human_gene") or "").strip().upper()
        entrez = str(row.get("entrez_gene_id") or "").strip()
        score_value = pd.to_numeric(pd.Series([row.get("essentiality_score")]), errors="coerce").iloc[0]
        if pd.notna(score_value):
            essentiality_score = max(0.0, min(1.0, float(score_value)))
        else:
            essentiality_score = 1.0 if _is_essential_value(row.get("essentiality_status")) else 0.0
        if not gene and not entrez:
            continue
        records.append(
            {
                "human_gene": gene,
                "entrez_gene_id": entrez,
                "human_essential": 1 if essentiality_score >= 0.5 else 0,
                "human_essentiality_score": round(essentiality_score, 4),
            }
        )
    return records


def _read_local_tables(workspace: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for dirname in ["data_user", "data_cache", "data_external", "data_raw"]:
        path = workspace / dirname / "human_essentiality.csv"
        if not path.exists():
            continue
        records.extend(_table_to_records(pd.read_csv(path)))
    return records


def _human_genes_from_workspace(workspace: Path) -> list[str]:
    path = workspace / "data_raw" / "human_homologs.csv"
    if not path.exists():
        return []
    df = pd.read_csv(path)
    if "human_gene" not in df.columns:
        return []
    genes = []
    for value in df["human_gene"].fillna("").tolist():
        gene = str(value).strip().upper()
        if gene and gene not in {"NONE", "NAN", "UNKNOWN"} and gene not in genes:
            genes.append(gene)
    return genes


def _lookup_records_for_genes(records: list[dict[str, Any]], genes: list[str], cfg: dict[str, Any]) -> tuple[pd.DataFrame, list[str]]:
    by_gene = {str(record.get("human_gene") or "").upper(): record for record in records if record.get("human_gene")}
    by_entrez = {str(record.get("entrez_gene_id") or ""): record for record in records if record.get("entrez_gene_id")}
    rows = []
    notes: list[str] = []
    for gene in genes:
        record = by_gene.get(gene)
        entrez = ""
        if record is None:
            entrez, lookup_notes = _query_ncbi_gene_id(gene, cfg)
            notes.extend(lookup_notes)
            record = by_entrez.get(entrez)
        if record is None:
            rows.append(
                {
                    "human_gene": gene,
                    "entrez_gene_id": entrez,
                    "human_essential": 0,
                    "human_essentiality_score": 0.0,
                    "human_essentiality_lookup_status": "not_found",
                }
            )
            continue
        rows.append(
            {
                "human_gene": gene,
                "entrez_gene_id": str(record.get("entrez_gene_id") or entrez),
                "human_essential": int(record.get("human_essential", 0)),
                "human_essentiality_score": float(record.get("human_essentiality_score", 0.0)),
                "human_essentiality_lookup_status": "matched",
            }
        )
    return pd.DataFrame(rows), notes


def fetch_human_essentiality_annotations(
    workspace: Path,
    config: dict[str, Any],
    mode: str,
    refresh_cache: bool = False,
    no_write_cache: bool = False,
) -> dict[str, Any]:
    if mode not in SOURCE_MODES:
        raise ValueError(f"online source mode no soportado: {mode}")
    workspace = Path(workspace)
    cfg = config["online_sources"]["human_essentiality"]
    genes = _human_genes_from_workspace(workspace)
    cache_key = "human_essentiality::" + "|".join(sorted(genes))
    cache = load_human_essentiality_cache(workspace, config)

    if not refresh_cache and cache["entries"].get(cache_key):
        entry = cache["entries"][cache_key]
        df = pd.DataFrame(entry.get("rows", []))
        manifest = {**entry.get("manifest", {}), "mode": mode, "source_used": "cache", "cache_hit": True, "api_attempted": False}
        return {"human_essentiality": df, "manifest": manifest}

    local_records = _read_local_tables(workspace)
    if local_records:
        df, notes = _lookup_records_for_genes(local_records, genes, cfg)
        manifest = {
            "source": "human_essentiality",
            "provider": "local_human_essentiality",
            "mode": mode,
            "source_used": "local_file",
            "cache_hit": False,
            "api_attempted": False,
            "api_success": False,
            "genes_queried": len(genes),
            "genes_matched": int(df["human_essentiality_lookup_status"].eq("matched").sum()) if not df.empty else 0,
            "notes": notes,
            "generated_at_utc": _utc_now(),
        }
        return {"human_essentiality": df, "manifest": manifest}

    if mode == "offline_only":
        raise FileNotFoundError("Modo offline_only sin cache o archivo local de human_essentiality.")
    raw, errors = _api_get_bytes(str(cfg["provider_download_url"]), cfg)
    if raw is None:
        manifest = {
            "source": "human_essentiality",
            "provider": str(cfg["provider_name"]),
            "mode": mode,
            "source_used": "api_failed",
            "cache_hit": False,
            "api_attempted": True,
            "api_success": False,
            "genes_queried": len(genes),
            "genes_matched": 0,
            "notes": errors,
            "generated_at_utc": _utc_now(),
        }
        return {"human_essentiality": pd.DataFrame(), "manifest": manifest}

    records = _table_to_records(_decode_table(raw))
    df, notes = _lookup_records_for_genes(records, genes, cfg)
    manifest = {
        "source": "human_essentiality",
        "provider": str(cfg["provider_name"]),
        "provider_docs_url": str(cfg.get("provider_docs_url", "")),
        "mode": mode,
        "source_used": "api_real",
        "cache_hit": False,
        "api_attempted": True,
        "api_success": True,
        "genes_queried": len(genes),
        "genes_matched": int(df["human_essentiality_lookup_status"].eq("matched").sum()) if not df.empty else 0,
        "notes": errors + notes,
        "generated_at_utc": _utc_now(),
    }
    if not no_write_cache:
        cache["entries"][cache_key] = {"saved_at_utc": _utc_now(), "rows": df.to_dict(orient="records"), "manifest": manifest}
        save_human_essentiality_cache(workspace, config, cache)
    return {"human_essentiality": df, "manifest": manifest}
