from __future__ import annotations

from pathlib import Path
from typing import NoReturn

import pandas as pd


def explain_io_error(exc: BaseException, path: str | Path, operation: str) -> str:
    """Return a user-facing Windows/OneDrive hint without hiding the original error."""
    target = Path(path)
    base = f"No se pudo {operation} `{target}`."
    detail = f"Detalle tecnico: {type(exc).__name__}: {exc}"
    lower_path = str(target).lower()
    one_drive_hint = (
        " Si la ruta esta en OneDrive, verifica que la carpeta este descargada localmente "
        "con 'Mantener siempre en este dispositivo' y espera a que termine la sincronizacion."
        if "onedrive" in lower_path
        else ""
    )
    if isinstance(exc, PermissionError):
        return (
            f"{base} Parece que el archivo esta abierto en Excel, bloqueado por OneDrive o sin permisos de escritura."
            f" Cierra el archivo, revisa permisos o usa un workspace fuera de OneDrive.{one_drive_hint} {detail}"
        )
    if isinstance(exc, FileNotFoundError):
        return (
            f"{base} La ruta no existe o OneDrive aun no la descargo localmente."
            f" Revisa el nombre de la carpeta, espacios en la ruta y el estado de sincronizacion.{one_drive_hint} {detail}"
        )
    if isinstance(exc, OSError):
        return (
            f"{base} El sistema operativo reporto un problema de archivo. Puede ser bloqueo por Excel, ruta solo-nube, "
            f"conflicto de sincronizacion o permisos insuficientes.{one_drive_hint} {detail}"
        )
    return f"{base} {detail}"


def raise_user_friendly_io_error(exc: BaseException, path: str | Path, operation: str) -> NoReturn:
    raise type(exc)(explain_io_error(exc, path, operation)) from exc


def read_csv(path: str | Path, **kwargs) -> pd.DataFrame:
    try:
        return pd.read_csv(path, **kwargs)
    except (PermissionError, FileNotFoundError, OSError) as exc:
        raise_user_friendly_io_error(exc, path, "leer el CSV")


def write_csv(df: pd.DataFrame, path: str | Path, **kwargs) -> None:
    try:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(path, **kwargs)
    except (PermissionError, FileNotFoundError, OSError) as exc:
        raise_user_friendly_io_error(exc, path, "escribir el CSV")


def write_text(path: str | Path, text: str, **kwargs) -> None:
    try:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(text, **kwargs)
    except (PermissionError, FileNotFoundError, OSError) as exc:
        raise_user_friendly_io_error(exc, path, "escribir el reporte")


def ensure_dir(path: str | Path) -> Path:
    target = Path(path)
    try:
        target.mkdir(parents=True, exist_ok=True)
    except (PermissionError, FileNotFoundError, OSError) as exc:
        raise_user_friendly_io_error(exc, target, "crear la carpeta")
    return target
