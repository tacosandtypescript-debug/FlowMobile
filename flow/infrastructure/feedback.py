from __future__ import annotations

from urllib.parse import urlencode

from flow import APP_VERSION
from flow.infrastructure.platform import PLATFORM


ISSUES_URL = "https://github.com/tacosandtypescript-debug/FlowMobile/issues"
SECURITY_REPORT_URL = (
    "https://github.com/tacosandtypescript-debug/FlowMobile/security/advisories/new"
)


def feedback_url(kind: str) -> str:
    if kind == "suggestion":
        label = "enhancement"
        title = "[Sugerencia] "
        heading = "Sugerencia"
        prompt = "Describe qué te gustaría añadir o mejorar."
    elif kind == "bug":
        label = "bug"
        title = "[Error] "
        heading = "Reporte de error"
        prompt = "Explica qué estabas haciendo, qué ocurrió y qué esperabas que ocurriera."
    else:
        raise ValueError("Tipo de comentario no válido.")

    body = (
        f"## {heading}\n\n"
        f"{prompt}\n\n"
        "## Contexto automático\n\n"
        f"- FlowMobile: {APP_VERSION}\n"
        f"- Dispositivo: {PLATFORM.mobile_os} / {PLATFORM.name}\n\n"
        "## Privacidad\n\n"
        "No incluyas cookies, contraseñas, tokens, enlaces privados ni rutas personales.\n"
    )
    query = urlencode({"labels": label, "title": title, "body": body})
    return f"{ISSUES_URL}/new?{query}"
