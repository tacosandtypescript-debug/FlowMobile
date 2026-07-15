from __future__ import annotations

from flow.domain.sites import platform_name


def friendly_error(url: str, error: Exception) -> tuple[str, str]:
    platform = platform_name(url)
    detail = str(error).strip()
    value = detail.lower()

    if any(term in value for term in ("sign in", "login", "cookie", "cookies")):
        return (
            f"{platform} solicita iniciar sesión.",
            "El contenido puede ser privado, tener restricción de edad o requerir cookies.",
        )
    if any(term in value for term in ("private", "not available", "unavailable", "deleted")):
        return (
            f"El contenido no está disponible en {platform}.",
            "Comprueba que el enlace sea público y que el contenido no haya sido eliminado.",
        )
    if "unsupported url" in value or "no suitable extractor" in value:
        return (
            f"El enlace de {platform} todavía no es compatible.",
            "Actualiza yt-dlp desde el menú principal y vuelve a intentarlo.",
        )
    if "429" in value or "too many requests" in value:
        return (
            f"{platform} limitó temporalmente las descargas.",
            "Espera unos minutos antes de volver a intentarlo.",
        )
    if "403" in value or "forbidden" in value:
        return (
            f"{platform} rechazó el acceso al archivo.",
            "El enlace puede haber caducado; genera o copia uno nuevo.",
        )
    if any(term in value for term in ("timed out", "timeout", "network", "connection")):
        return (
            "La conexión se interrumpió.",
            "Comprueba Internet y vuelve a intentar la descarga.",
        )
    if any(term in value for term in ("no space", "disk full", "errno 28")):
        return (
            "No queda espacio suficiente en el dispositivo.",
            "Libera almacenamiento antes de repetir la descarga.",
        )
    if "ffmpeg" in value:
        return (
            "FFmpeg no pudo procesar el archivo descargado.",
            "El original se conserva. Revisa Sistema para ver los codificadores disponibles.",
        )
    return (
        f"No se pudo completar la operación con {platform}.",
        detail[:220] or "Vuelve a intentarlo o actualiza yt-dlp.",
    )
