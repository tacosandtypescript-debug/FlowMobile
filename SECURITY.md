# Seguridad

## Versiones compatibles

Solo la versión estable más reciente recibe correcciones de seguridad.

## Protecciones incluidas

- Los instaladores estables verifican `SHA256SUMS` antes de usar el paquete.
- El código ejecutable se compara con `SECURITY_MANIFEST.sha256`.
- Las dependencias Python se instalan desde `requirements.lock` con hashes.
- Las cookies se guardan localmente con permisos privados y nunca se incluyen
  en el diagnóstico.
- Los paquetes publicados incluyen una atestación de procedencia de GitHub.
- Dependabot revisa semanalmente Python y GitHub Actions; CodeQL analiza el
  código y la rama principal exige verificaciones antes de integrar cambios.

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
