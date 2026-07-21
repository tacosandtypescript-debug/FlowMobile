# Seguridad

## Versiones compatibles

Solo la versión estable más reciente recibe correcciones de seguridad.

## Protecciones incluidas

- Los instaladores estables verifican `SHA256SUMS` antes de usar el paquete.
- Windows y Linux conservan la versión anterior hasta que
  `flow --health-check` valida la instalación nueva.
- El código ejecutable se compara con `SECURITY_MANIFEST.sha256`.
- Las dependencias Python se instalan desde `requirements.lock` con hashes.
- Las cookies se guardan localmente con permisos privados y nunca se incluyen
  en el diagnóstico.
- Windows aplica ACL del usuario actual a cookies, ajustes, historial, colas e
  informes; los sistemas POSIX usan permisos `600` y directorios `700`.
- El registro de instalación se reemplaza en cada intento, usa permisos
  privados y no contiene cookies ni historial de descargas.
- Los paquetes publicados incluyen una atestación de procedencia de GitHub.
- Dependabot revisa semanalmente Python y GitHub Actions; CodeQL analiza el
  código y la rama principal exige verificaciones antes de integrar cambios.
- Una prueba semanal instala el release estable desde cero en Windows y Linux.

El Centro de seguridad está en **Herramientas → Centro de seguridad**. Si la
integridad falla, no introduzcas cookies ni ejecutes actualizaciones: reinstala
desde el repositorio oficial.

## Informar una vulnerabilidad

No publiques cookies, enlaces privados, tokens, rutas personales ni informes
con datos sensibles en una incidencia pública. Utiliza **Security → Report a
vulnerability** en GitHub para enviar el informe de forma privada.

Incluye la versión de FlowMobile, la plataforma, los pasos mínimos para
reproducir el problema y el informe generado desde **Herramientas → Informe de
diagnóstico**. Ese informe no contiene enlaces, cookies ni rutas privadas.

No se deben probar vulnerabilidades contra cuentas, dispositivos o servicios
de terceros sin autorización.
