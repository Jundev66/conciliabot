# ConciliaBot

<p align="center">
  <b>Enterprise-Grade Invoice & Delivery Note Reconciliation Assistant (BYOC)</b><br/>
  <i>Asistente de conciliación y validación de facturas y notas de entrega para ERPs de LATAM</i>
</p>

<p align="center">
  <a href="#-español"><b>🇪🇸 Leer en Español</b></a> •
  <a href="#-english"><b>🇺🇸 Read in English</b></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Architecture-BYOC%20(Bring%20Your%20Own%20Cloud)-0284c7?style=flat-square" alt="BYOC" />
  <img src="https://img.shields.io/badge/Security-AES--256--GCM%20%7C%20SSRF%20Guards-059669?style=flat-square" alt="Security" />
  <img src="https://img.shields.io/badge/Audit-Hash--Chained%20WORM-6366f1?style=flat-square" alt="Audit" />
  <img src="https://img.shields.io/badge/ERP-CoreBiz%20%7C%20MCP%20Protocol-d97706?style=flat-square" alt="ERP" />
  <img src="https://img.shields.io/badge/License-MIT-gray?style=flat-square" alt="License" />
</p>

---

## 🇪🇸 Español

Asistente local (backend en Python FastAPI + PWA en React/TypeScript) que **valida, concilia y confirma el registro de facturas y notas de entrega** contra sistemas ERP (como **CoreBiz** o vía protocolo MCP). Diseñado bajo el principio **BYOC (Bring Your Own Cloud)**: el software corre íntegramente dentro de la infraestructura del cliente, garantizando que los datos fiscales, comerciales y contables nunca salgan de su entorno.

> **Aviso**: Repositorio demostrativo con datos sintéticos. No constituye asesoría legal, fiscal ni contable.

---

### Arquitectura del Sistema

```
                 ┌──────────────────────────── Backend (FastAPI) ────────────────────────────┐
  Documento ───► │ Ingesta → PII → Ruteo → Extracción → Verificación fiscal → Cotejo ERP →    │
  (PDF / XML /   │ Conciliación → Política → Propuesta de registro → Auditoría WORM          │
   JSON / XLSX)  │                                                                           │
                 │  ERP CoreBiz (Bridge M2M)           ·  LLM Gateway (Ruteo / Presupuesto / │
                 │  ERP MCP (Sandbox solo lectura)     ·  Caché / Retry / Backoff / Fallback)│
                 │  SQLite local (Hash-chained audit)  ·  Playwright (Respaldo navegador)    │
                 └───────────────────────────────────────────────────────────────────────────┘
                                    ▲ /api                          PWA (React) ── vista
```

- **Backend (`backend/app`)**: Pipeline determinista y probabilístico, extractores de documentos (PDF con `pypdf`, CFDI, UBL, JSON, Excel), conector REST de CoreBiz, servidor MCP y framework de evaluaciones (evals).
- **Frontend (`src`)**: PWA moderna y responsiva con bandeja de facturas, cotejo interactivo en vivo, ingesta por arrastrar y soltar, bitácora de auditoría inmutable, centro de evaluaciones y panel de configuración BYOC.

---

### Características Principales

1. **Validación Multiformato:**
   - **PDF Nativo**: Extracción de texto y análisis heurístico de facturas y notas de entrega / remisiones generadas por sistemas de facturación.
   - **Formatos Fiscales Electrónicos**: Soporte para CFDI (México), NF-e (Brasil), UBL (Colombia, Perú, Chile).
   - **Archivos Comunes**: Importación y exportación de hojas de cálculo Excel (`.xlsx`) y cargas JSON.
2. **Cotejo Automático con ERP CoreBiz:**
   - Conexión M2M directa contra la API de CoreBiz (`/v1/integrations/delivery-notes`).
   - Cotejo instantáneo de folio, cliente/proveedor, importes (subtotal, impuestos, total) y estado de recepción física.
   - Detección precisa de discrepancias y discrepancias de recepción parcial.
3. **Registro y Confirmación Durable:**
   - Flujo *Human-in-the-Loop* (HITL): Al confirmar la nota de entrega desde la interfaz, el sistema invoca `POST /v1/integrations/delivery-notes/{id}/confirm` en CoreBiz para marcarla como `delivered` con trazabilidad del operador.
   - **Garantía antifallos**: Si el ERP responde con error (ej. `HTTP 404`), el sistema **nunca** marca la nota como registrada falsamente; la mantiene en estado `approved` (aprobada localmente) con alerta visible y botón de reintento.
4. **Respaldo mediante Protocolo MCP y Navegador:**
   - Servidor MCP integrado (`backend/app/mcp_server.py`) con herramientas de solo lectura.
   - Respaldo con navegador headless Playwright para ERPs legacy sin API abierta.

---

### Controles de Ciberseguridad y Privacidad

El proyecto está diseñado bajo estrictos estándares de ciberseguridad defensiva:

| Control | Implementación | Propósito |
|---|---|---|
| **Defensa Anti-SSRF** | `backend/app/security.py` | Bloquea llamadas a metadatos de nubes (AWS/GCP `169.254.169.254`), link-local, multicast y direcciones reservadas. |
| **Anonimización de PII** | `backend/app/agent/pii.py` | Redacta y censura correos, teléfonos, CURP, CPF y CNPJ antes de interactuar con modelos de lenguaje. |
| **Defensa Anti-Prompt Injection** | `backend/app/agent/pii.py` | Detecta heurísticamente instrucciones maliciosas en facturas (`ignore previous instructions`, etc.). |
| **Cifrado en Reposo (AES-256-GCM)** | `backend/app/security.py` | Cifrado autenticado para API keys y documentos fuente cuando se configura `CONCILIABOT_DB_KEY`. |
| **Bitácora Inmutable (WORM)** | `backend/app/db.py` | Cadena de auditoría encadenada por hashes SHA-256 (`prev_hash` $\rightarrow$ `hash`). Verificable vía `GET /api/audit/verify`. |
| **Presupuesto y Control DoS** | `backend/app/agent/llm.py` | Límites estrictos de tokens (`BUDGET_MAX_TOKENS`), timeouts (`BUDGET_MAX_MS`) y Rate Limiting por cliente. |

---

### Puesta en Marcha (Desarrollo Local)

#### 1. Backend (Python 3.12+)
```bash
cd backend
python -m venv .venv
# Windows
.\.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
python -m playwright install chromium  # para respaldo de navegador
uvicorn app.main:app --port 8000
```

#### 2. Frontend (Node.js 20+)
En otra terminal:
```bash
npm install
npm run dev        # Disponible en http://localhost:5173
```

---

### Despliegue con Docker Compose (Producción BYOC)

Despliegue con **un comando** que incluye **Caddy** con terminación TLS automática:

```bash
cp .env.example .env
docker compose up -d --build
```
- Aplicación disponible en `https://localhost` (o tu dominio en `SITE_ADDRESS`).
- Estado local persistente en el volumen montado `./backend/data`.

---

### Variables de Entorno

| Variable | Descripción | Valor por Defecto |
|---|---|---|
| `CONCILIABOT_AUTH` | Autenticación por token para clientes externos a localhost | `on` |
| `CONCILIABOT_DB_KEY` | Clave AES-256-GCM (base64) para cifrar datos en reposo | *(opcional)* |
| `CONCILIABOT_ALLOW_PRIVATE` | Permite conexiones a IPs privadas/LAN para ERP local | `on` |
| `CONCILIABOT_RATE_LIMIT` | Límite de peticiones por minuto por cliente | `60` |
| `CONCILIABOT_ERP_PROVIDER` | Proveedor del ERP: `corebiz` o `demo` | `corebiz` |
| `COREBIZ_BASE_URL` | URL base de la API de CoreBiz | `http://127.0.0.1:3021` |
| `COREBIZ_API_KEY` | Machine API Key para la integración CoreBiz | *(tu api key)* |
| `CONCILIABOT_LLM` | Activa gateway de LLM (`on` / `off` offline determinista) | `off` |

---

<br/>

## 🇺🇸 English

A local-first assistant (Python FastAPI backend + React/TypeScript PWA) that **validates, reconciles, and confirms invoice and delivery note records** against ERP systems (such as **CoreBiz** or via the MCP protocol). Built on the **BYOC (Bring Your Own Cloud)** paradigm: all processing occurs entirely within the client's infrastructure, guaranteeing that financial and accounting data never leave the perimeter.

> **Disclaimer**: Demonstration repository using synthetic data. Does not constitute legal, tax, or accounting advice.

---

### System Architecture

```
                 ┌──────────────────────────── Backend (FastAPI) ────────────────────────────┐
  Document  ───► │ Ingest → PII → Routing → Extraction → Fiscal Audit → ERP Reconciliation →  │
  (PDF / XML /   │ Discrepancy Analysis → Policy Engine → Settlement → WORM Audit Log        │
   JSON / XLSX)  │                                                                           │
                 │  CoreBiz ERP (M2M Bridge)           ·  LLM Gateway (Routing / Budgeting / │
                 │  MCP ERP (Read-only sandbox)        ·  Cache / Retry / Backoff / Fallback)│
                 │  Local SQLite (Hash-chained audit)  ·  Playwright (Headless Web Fallback) │
                 └───────────────────────────────────────────────────────────────────────────┘
                                    ▲ /api                          PWA (React) ── View
```

- **Backend (`backend/app`)**: Deterministic and probabilistic pipelines, document extractors (PDF via `pypdf`, CFDI, UBL, JSON, Excel), CoreBiz REST integration, MCP server, and evaluation suite.
- **Frontend (`src`)**: Responsive PWA featuring an invoice inbox, interactive reconciliation view, drag-and-drop ingest, tamper-evident audit trail, evals dashboard, and BYOC settings.

---

### Key Capabilities

1. **Multi-Format Document Processing:**
   - **Native PDF Extraction**: Intelligent parsing and heuristics for delivery notes and invoices without requiring external OCR services.
   - **Electronic Invoicing**: Support for CFDI (Mexico), NF-e (Brazil), and UBL (Colombia, Peru, Chile).
   - **Standard Business Files**: Import and export of Excel workbooks (`.xlsx`) and structured JSON payloads.
2. **Automated ERP Reconciliation (CoreBiz):**
   - Direct machine-to-machine connection to CoreBiz (`/v1/integrations/delivery-notes`).
   - Real-time comparison of document folio, counterparty, totals (subtotal, taxes, grand total), and physical warehouse receipts.
   - Precise discrepancy flagging (amount differences, partial receipts, missing POs).
3. **Durable CoreBiz Settlement:**
   - Human-in-the-Loop (HITL) approval: Confirming a delivery note triggers `POST /v1/integrations/delivery-notes/{id}/confirm` in CoreBiz, advancing status to `delivered` with operator attribution.
   - **Fail-safe state handling**: If CoreBiz returns an error (e.g., `HTTP 404`), the record is **never** marked as registered; it transitions to `approved` (locally approved) with an amber warning banner and retry controls.
4. **MCP Protocol & Browser Fallback:**
   - Standalone Model Context Protocol (MCP) server (`backend/app/mcp_server.py`) with read-only tools.
   - Sandboxed Playwright browser fallback for ERP systems lacking an open API.

---

### Security & Privacy by Design

Engineered following **OWASP** defense-in-depth principles:

| Control | Module | Purpose |
|---|---|---|
| **SSRF Mitigation** | `backend/app/security.py` | Restricts outbound traffic; blocks cloud metadata endpoints (`169.254.169.254`, Google/AWS internal), link-local, and multicast addresses. |
| **PII Redaction** | `backend/app/agent/pii.py` | Automatically scrubs emails, phone numbers, and national tax IDs (CURP, CPF, CNPJ) prior to LLM processing. |
| **Prompt Injection Defense** | `backend/app/agent/pii.py` | Heuristically detects adversarial jailbreak patterns in uploaded document text. |
| **Authenticated Encryption** | `backend/app/security.py` | AES-256-GCM encryption for stored ERP credentials and source files when `CONCILIABOT_DB_KEY` is configured. |
| **Tamper-Evident Audit Trail** | `backend/app/db.py` | Append-only SHA-256 hash-chained log (`prev_hash` $\rightarrow$ `hash`). Cryptographically verifiable via `GET /api/audit/verify`. |
| **Resource Budgets & Rate Limiting** | `backend/app/agent/llm.py` | Strict token ceilings (`BUDGET_MAX_TOKENS`), runtime caps (`BUDGET_MAX_MS`), and sliding-window rate limiters. |

---

### Quickstart (Local Development)

#### 1. Backend (Python 3.12+)
```bash
cd backend
python -m venv .venv
# Windows
.\.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
python -m playwright install chromium
uvicorn app.main:app --port 8000
```

#### 2. Frontend (Node.js 20+)
In a separate terminal:
```bash
npm install
npm run dev        # Served at http://localhost:5173
```

---

### Docker Deployment (BYOC Production)

Single-command setup with automated **Caddy TLS termination**:

```bash
cp .env.example .env
docker compose up -d --build
```
- Access the application at `https://localhost` (or configured `SITE_ADDRESS`).
- Persistent local SQLite state lives on the host volume `./backend/data`.

---

### Verification & Automated Tests

```bash
cd backend
python -m pytest -q          # Run unit test suite (38+ tests)
python -m app.evals.runner   # Run trajectory and extraction evals
```

---

### License

This project is licensed under the [MIT License](LICENSE).
