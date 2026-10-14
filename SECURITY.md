# Seguridad

## Datos de demostración

Este repositorio es una **demostración con datos sintéticos**. No contiene datos reales de
clientes, credenciales ni secretos:

- La carpeta `backend/data/` (base SQLite, `erp.json` y `api_token`) está **ignorada por Git**
  (`.gitignore`).
- Los ejemplos de facturas/notas son inventados.
- La clave de cifrado y el token se configuran por instalación mediante variables de entorno
  o se generan localmente; **nunca** se versionan.

Si vas a desplegarlo con datos reales, revisa `docs/DECISIONS.md` (ADR-0003 y ADR-0004) y usa
copias de seguridad y HTTPS.

## Controles incluidos

| Área | Control |
|---|---|
| Acceso remoto | Token local para clientes no-loopback; loopback confiable (`main.py`) |
| Salidas de red (SSRF) | `security.validate_outbound_url` (solo http/https; bloqueo link-local/metadata) |
| Secretos en reposo | AES-256-GCM para la API key del ERP y el documento fuente |
| Trazabilidad | Bitácora `audit` append-only encadenada por hash (`db.py::verify_audit_chain`) |
| Entrada no confiable | Redacción de PII y sospecha de inyección de prompt (`agent/pii.py`) |
| Límite de volumen | Rate limiting por credencial en `/api/*` y `/v1/integrations/*` |

## Cómo reportar

¿Encontraste una vulnerabilidad? Usa el **reporte privado de vulnerabilidades de GitHub**
(pestaña **Security → Report a vulnerability** de este repositorio). Evita abrir un issue
público para problemas de seguridad: coordino la corrección antes de publicarla.

## Alcance

Es un proyecto de demostración/portafolio; no incluye garantías (ver `LICENSE`). Los controles
descritos son los aplicados en el código, no una certificación de seguridad.
