from __future__ import annotations


def online_failure_message(provider: str, mode: str, error: BaseException | None = None) -> str:
    detail = f" Detalle tecnico: {type(error).__name__}: {error}" if error is not None else ""
    if mode == "offline_only":
        return f"Modo offline_only: no se consulta {provider}; se requiere cache local o datos de usuario.{detail}"
    if mode == "cache_first":
        return f"No se pudo usar {provider}; se intenta cache local antes de cualquier fallback.{detail}"
    return f"No se pudo consultar {provider}; el pipeline debe degradar a cache, stub o missing de forma trazable.{detail}"
