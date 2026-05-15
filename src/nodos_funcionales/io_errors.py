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
            f" Cierra Excel, revisa permisos, usa una ruta absoluta o mueve el workspace fuera de OneDrive.{one_drive_hint} {detail}"
        )
    if isinstance(exc, FileNotFoundError):
        return (
            f"{base} La ruta no existe o OneDrive aun no la descargo localmente."
            f" Revisa el nombre de la carpeta, usa una ruta absoluta, confirma espacios/caracteres especiales "
            f"y espera a que termine la sincronizacion.{one_drive_hint} {detail}"
        )
    if isinstance(exc, OSError):
        return (
            f"{base} El sistema operativo reporto un problema de archivo. Puede ser bloqueo por Excel, ruta solo-nube, "
            f"conflicto de sincronizacion o permisos insuficientes. Cierra Excel, espera la sincronizacion, "
            f"usa una ruta absoluta o copia el workspace a una carpeta local.{one_drive_hint} {detail}"
        )
    return f"{base} {detail}"


def explain_cli_error(exc: BaseException, command_name: str = "comando") -> str:
    """Return a concise CLI error with a concrete next action for common failures."""
    detail = f"{type(exc).__name__}: {exc}"
    message = str(exc)
    lowered = message.lower()

    if isinstance(exc, PermissionError):
        return (
            f"[ERROR] {command_name} no pudo escribir o leer un archivo. "
            "Cierra Excel, visores de vista previa u otros procesos que puedan tener abierto el CSV/reporte; "
            "si el workspace esta en OneDrive, espera la sincronizacion o mueve el workspace a una carpeta local. "
            f"Detalle tecnico: {detail}"
        )
    if isinstance(exc, FileNotFoundError):
        return (
            f"[ERROR] {command_name} no encontro un archivo o directorio requerido. "
            "Revisa la ruta, usa una ruta absoluta si hay espacios, confirma que el archivo existe localmente "
            "y, si esta en OneDrive, marca la carpeta como disponible sin conexion. "
            f"Detalle tecnico: {detail}"
        )
    if isinstance(exc, OSError):
        return (
            f"[ERROR] {command_name} encontro un problema del sistema de archivos. "
            "Puede deberse a permisos, OneDrive, un archivo abierto o una ruta no disponible localmente. "
            "Cierra archivos abiertos y prueba un workspace local estable. "
            f"Detalle tecnico: {detail}"
        )
    if isinstance(exc, ValueError):
        hint = "Revisa los parametros y los archivos de entrada."
        if "faltan columnas requeridas" in lowered or "required columns" in lowered:
            hint = "Compara tu CSV con la plantilla correspondiente en data_templates/ y conserva los nombres de columnas requeridos."
        elif "online source mode" in lowered or "modo" in lowered and "online" in lowered:
            hint = "Usa un modo valido: offline_only, cache_first, online_optional, auto, local o api_stub, segun el comando."
        elif "organism_name" in lowered or "organismo" in lowered:
            hint = "Proporciona --organism con el nombre bacteriano; --strain es opcional si no aplica."
        return f"[ERROR] {command_name} recibio una configuracion o entrada invalida. {hint} Detalle tecnico: {detail}"
    return f"[ERROR] {command_name} fallo. Detalle tecnico: {detail}"


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
