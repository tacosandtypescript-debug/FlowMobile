# Contribuir a FlowMobile

Gracias por ayudar a mejorar FlowMobile.

1. Crea una rama desde `main`.
2. Mantén los cambios compatibles con Python 3.10 o posterior.
3. No añadas cookies, descargas, tokens, rutas del dispositivo ni datos reales.
4. Añade una prueba automatizada para cada corrección.
5. Ejecuta `python -m unittest discover -s tests -v`.
6. En Windows ejecuta `powershell -ExecutionPolicy Bypass -File .\scripts\check-release.ps1`.
7. Prueba los cambios móviles siguiendo [Pruebas en dispositivos](docs/DEVICE_TESTING.md).

Las descargas deben respetar las condiciones de cada servicio, los derechos de
autor y la legislación aplicable. FlowMobile no debe intentar eludir DRM ni
controles de acceso.
