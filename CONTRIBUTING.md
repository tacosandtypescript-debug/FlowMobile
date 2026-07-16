# Contribuir a FlowMobile

Gracias por ayudar a mejorar FlowMobile. Desde la versión 7.6.14, PolyForm
Strict no concede permiso general para crear modificaciones. Puedes proponer
ideas y reportar errores mediante GitHub Issues.

Antes de preparar código o abrir una solicitud de cambios, pide autorización
escrita en una incidencia. Las contribuciones aceptadas requerirán un acuerdo
separado que permita al titular incorporar y licenciar el cambio.

1. Obtén autorización escrita antes de crear una modificación.
2. Crea una rama desde `main`.
3. Mantén los cambios compatibles con Python 3.10 o posterior.
4. No añadas cookies, descargas, tokens, rutas del dispositivo ni datos reales.
5. Añade una prueba automatizada para cada corrección.
6. Ejecuta `python -m unittest discover -s tests -v`.
7. En Windows ejecuta `powershell -ExecutionPolicy Bypass -File .\scripts\check-release.ps1`.
8. Prueba los cambios móviles siguiendo [Pruebas en dispositivos](docs/DEVICE_TESTING.md).

Las descargas deben respetar las condiciones de cada servicio, los derechos de
autor y la legislación aplicable. FlowMobile no debe intentar eludir DRM ni
controles de acceso.
