# Decisiones de arquitectura (ADR)

Registro corto de **por qué** el sistema es como es. Cada decisión lista su contexto,
la alternativa que se descartó y las consecuencias. El objetivo no es documentar *qué*
hace el código (eso está en el código y en el README), sino **dejar por escrito el
criterio** detrás de las elecciones, incluidas las que se rechazaron a propósito.

Formato: Contexto · Decisión · Alternativas consideradas · Consecuencias.

---

## ADR-0001 — BYOC: una instalación por cliente, **no** multi-tenant

**Contexto.** El producto concilia facturas de proveedor contra notas de entrega de un
ERP. Quien lo usa es una PyME que ya tiene un ERP (p. ej. CoreBiz) y datos contables
sensibles. El valor principal es "tus datos no salen de tu entorno".

**Decisión.** El sistema es **BYOC / on-premise**: cada cliente recibe su propia
instalación (backend + base local + PWA), y el aislamiento entre clientes es la
**instalación misma**, no una columna `tenant_id` en una base compartida. No hay
multi-tenancy a nivel de aplicación ni Row Level Security (RLS).

**Alternativas consideradas.**
- *SaaS multi-tenant* (una base compartida, `tenant_id` + RLS). Se descartó porque obliga
  a custodiar los datos de todos los clientes, a construir y sostener el aislamiento por
  fila, y a operar una infraestructura que el cliente ya tiene. Además, un PWA servido
  desde un origen compartido introduce riesgo de caché cruzada entre inquilinos.
- *Multi-tenant "por si acaso"* (dejar el esquema listo sin necesidad). Se descartó por
  **over-engineering**: agrega complejidad y superficie de error sin un requisito que lo
  justifique. La señal de buen diseño es saber **cuándo no** aplicarlo.

**Consecuencias.**
- ✔ El cliente es dueño de sus datos; el proveedor no los custodia (menos riesgo legal).
- ✔ Aislamiento fuerte y simple: no hay consultas que puedan "olvidar" el `tenant_id`.
- ✔ Costo de infraestructura para el proveedor cercano a cero (el hosting lo pone el cliente).
- ✗ Actualizar N instalaciones y soportar entornos heterogéneos es **costo operativo real**.
- ✗ No existe un "actualizar a todos de golpe"; la distribución de versiones se resuelve
  aparte (paquete/contenedor por cliente).

**Cuándo se cambiaría.** Si el negocio pasa a vender una experiencia hospedada con un
único origen, ese cambio se diseña como una **variante explícita** (Postgres + `tenant_id`
+ RLS), no como un parche sobre el modo on-prem.

### Comparación de modelos (costo y riesgo)

| Modelo | Quién hospeda | Costo infra (proveedor) | Riesgo / carga | Encaje |
|---|---|---|---|---|
| **BYOC (este repo)** | El cliente | ~cero | Bajo: no se custodian datos | On-premise |
| Hospedado por cliente-proveedor, 1 por cliente | El proveedor | Alto (N despliegues) | Alto en operación | Evitar: lo peor de ambos |
| SaaS multi-tenant | El proveedor | Bajo por cliente (escala) | Aislamiento + custodia de datos | Otro producto |

---

## ADR-0002 — SQLite local, no Postgres/RLS

**Contexto.** La instalación corre en la máquina del cliente, sin administración.

**Decisión.** Persistencia en **SQLite local** (`backend/data/app.db`).

**Alternativas consideradas.** Postgres (necesario para RLS, pero requiere operar un motor
de base de datos en cada instalación). Se descartó por el costo de operación que contradice
la promesa "cero administración".

**Consecuencias.** ✔ Instalación trivial y sin dependencias externas. ✔ RLS no está
disponible — y no hace falta, porque el aislamiento lo da la instalación (ver ADR-0001).
✗ El día que se quiera el modo hospedado, la base cambia a Postgres (es un cambio acotado
porque el acceso a datos está encapsulado en `db.py`).

---

## ADR-0002b — `connection_id`: multi-ERP **dentro** de una instalación

**Contexto.** Un mismo cliente puede tener más de un ERP. Eso **no** es multi-tenant.

**Decisión.** Cada fila lleva `connection_id` derivado del ERP activo
(`erp_config.active_connection_id()`), de modo que los datos de distintos ERPs del **mismo
cliente** nunca se mezclan. La caché del LLM también se separa por conexión.

**Consecuencias.** ✔ Aislamiento de múltiples ERPs sin introducir multi-tenancy. ✔ No
confundir "varios ERPs" con "varios clientes": son ejes distintos.

---

## ADR-0003 — Autenticación local: loopback confiable + token

**Contexto.** El backend corre en la máquina del cliente. En uso local, exigir login
complica sin aportar seguridad real (quien abre `localhost` ya está en la máquina).

**Decisión.** Los clientes desde **loopback** (misma máquina) son confiables; los clientes
**remotos** deben presentar un token local (`Authorization: Bearer`, guardado en
`backend/data/api_token`, nunca en el repo). `/api/health` queda exento.

**Alternativas consideradas.** OAuth/usuario-contraseña para todos. Se descartó por
sobrecarga en un escenario de un solo operador local; el token cubre el caso remoto.

**Consecuencias.** ✔ No rompe el uso local ni la PWA. ✔ El acceso desde la red queda
protegido. ✗ Para multiusuario real o acceso por HTTPS remoto, se evoluciona a identidad
por usuario (fuera del alcance actual).

---

## ADR-0004 — Secretos cifrados y salidas validadas (SSRF)

**Contexto.** El sistema guarda credenciales de ERP y hace llamadas salientes a URLs que el
usuario configura (ERP, navegador de respaldo, LLM).

**Decisión.** La API key del ERP se cifra en reposo con **AES-256-GCM** cuando hay clave
(`CONCILIABOT_DB_KEY`); el documento fuente también. Toda URL saliente pasa por
`security.validate_outbound_url()` (solo `http/https`; bloqueo de link-local/metadata).

**Consecuencias.** ✔ El repo y los archivos locales no exponen secretos en claro. ✔ Se
corta la clase de ataque SSRF más común (metadata de nube). ✗ Requiere gestionar la clave
de cifrado por instalación.

---

## ADR-0005 — Auditoría **encadenada por hash**, no una tabla mutable

**Contexto.** Se necesita trazabilidad de cada decisión (quién, cuándo, sobre qué) que sea
**a prueba de manipulación**, tanto para el negocio como para una auditoría.

**Decisión.** La tabla `audit` es **append-only y encadenada por hash**: cada entrada
incluye el hash de la anterior. `verify_audit_chain()` (expuesto en
`GET /api/audit/verify`) detecta edición o borrado e indica **qué** entrada se rompió.

**Alternativas consideradas.** Log plano o tabla de auditoría normal. Se descartaron porque
no permiten detectar manipulación posterior.

**Consecuencias.** ✔ WORM lógico sin infraestructura extra. ✔ Es un punto de conversación
técnico fuerte. ✗ La verificación es lineal en el número de entradas (aceptable a esta
escala).

---

## ADR-0006 — La PWA se sirve desde el **mismo origen** que la API

**Contexto.** El cliente usa una interfaz web instalable (PWA) que habla con el backend.

**Decisión.** El backend sirve el bundle del PWA en `/` y la API en `/api`; el frontend usa
rutas **relativas** (`/api`). Sin CORS ni enrutamiento por inquilino.

**Consecuencias.** ✔ Simplicidad máxima: el PWA llama a *su* backend. ✔ El service worker
queda con scope por origen (sin caché cruzada entre clientes). ✗ "Instalar como app" exige
**contexto seguro** (HTTPS o `localhost`); el acceso por IP en LAN requiere TLS.

---

## Resumen

| Decisión | Elección | Descartado |
|---|---|---|
| Tenencia | Instalación por cliente (BYOC) | SaaS multi-tenant, RLS |
| Base de datos | SQLite local | Postgres |
| Multi-ERP | `connection_id` por instalación | Confundirlo con multi-tenant |
| Auth | Loopback + token | Login para todos |
| Secretos / salidas | AES-256-GCM + validación SSRF | Guardar en claro / URL libre |
| Auditoría | Cadena de hash (WORM lógico) | Tabla mutable |
| Frontend | PWA mismo origen | Origen compartido |
