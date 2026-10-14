import { useRef, useState } from "react";
import type { ChangeEvent, DragEvent } from "react";
import { Download, FileCheck, FileText, Loader2, Upload, X } from "lucide-react";
import { api } from "../lib/api";
import { useStore } from "../lib/store";

interface Sample {
  label: string;
  text: string;
  filename: string;
  source: string;
  deliveryNote?: string;
}

const SAMPLES: Sample[] = [
  {
    label: "Nota de entrega (NE-5001)",
    filename: "NE-5001.pdf",
    source: "carpeta",
    deliveryNote: "NE-5001",
    text: `NOTA DE ENTREGA / REMISIÓN
Folio: NE-5001
Distribuidora del Norte S.A. de C.V.
RFC: DNO920415H19
Cliente: Comercio de Ejemplo S.A.
Fecha de Emisión: 2026-10-01
Fecha de Entrega: 2026-10-02
Moneda: MXN
Subtotal: $ 14,500.00
IVA: $ 0.00
TOTAL: $ 14,500.00
Orden de Compra (OC): P-1042
Estado: Entregada (Recibido 100%)`
  },
  {
    label: "CFDI que cuadra",
    filename: "C-90001.xml",
    source: "email",
    text: `<?xml version="1.0" encoding="UTF-8"?>
<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/4" xmlns:tfd="http://www.sat.gob.mx/TimbreFiscalDigital"
  Folio="C-90001" Fecha="2026-10-05T10:00:00" SubTotal="12500.00" Moneda="MXN" Total="14500.00">
  <cfdi:Emisor Rfc="DNO920415H19" Nombre="Distribuidora del Norte S.A. de C.V."/>
  <cfdi:Impuestos TotalImpuestosTrasladados="2000.00"/>
  <cfdi:Complemento><tfd:TimbreFiscalDigital UUID="C9000001-1111-2222-3333-444455556666"/></cfdi:Complemento>
</cfdi:Comprobante>`
  },
  {
    label: "Con diferencia vs OC",
    filename: "C-90002.xml",
    source: "email",
    text: `<?xml version="1.0" encoding="UTF-8"?>
<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/4" xmlns:tfd="http://www.sat.gob.mx/TimbreFiscalDigital"
  Folio="C-90002" Fecha="2026-10-05T11:00:00" SubTotal="13000.00" Moneda="MXN" Total="16000.00">
  <cfdi:Emisor Rfc="APM010203K55" Nombre="Aceros y Perfiles Monterrey S.A."/>
  <cfdi:Impuestos TotalImpuestosTrasladados="3000.00"/>
  <cfdi:Complemento><tfd:TimbreFiscalDigital UUID="C9000002-1111-2222-3333-444455556666"/></cfdi:Complemento>
</cfdi:Comprobante>`
  },
  {
    label: "Escaneado (baja confianza)",
    filename: "FE-90001.pdf",
    source: "carpeta",
    text: `FACTURA ELECTRONICA DE VENTA
NIT: 9001234567
RazonSocial: Servicios Logisticos Andinos S.A.S.
Folio: FE-90001
CUFE: 9F3A7C21-0000-0000-0000-000000000000
Total: 4998000
Moneda: COP`
  }
];

export default function Ingest() {
  const { mode } = useStore();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [text, setText] = useState("");
  const [filename, setFilename] = useState("factura.xml");
  const [source, setSource] = useState("api");
  const [useBrowser, setUseBrowser] = useState(false);
  const [deliveryNote, setDeliveryNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState("");

  function onFileChange(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) handlePickedFile(file);
  }

  function handlePickedFile(file: File) {
    setSelectedFile(file);
    setFilename(file.name);
    setError("");
  }

  function handleDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file) handlePickedFile(file);
  }

  async function downloadSamplePdf(number = "NE-000004") {
    try {
      await api.downloadPdfTemplate(number);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al descargar PDF");
    }
  }

  async function run() {
    setBusy(true);
    setError("");
    try {
      let inv;
      if (selectedFile) {
        inv = await api.ingestFile(selectedFile, source, useBrowser, deliveryNote);
      } else {
        inv = await api.ingest(text, filename, source, useBrowser, deliveryNote);
      }
      window.location.assign(`/facturas/${inv.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al procesar");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-5">
      <div className="rounded-xl border border-slate-200 bg-white p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-sm font-semibold text-slate-900">Ingesta y validación de documentos</h1>
            <p className="mt-1 text-xs text-slate-500">
              Sube un <strong>PDF</strong>, archivo de <strong>nota de entrega</strong> (XML, JSON, Excel) o pega el texto para validar todos sus campos y registrarlo en CoreBiz al confirmar.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={() => downloadSamplePdf("NE-000004")}
              className="inline-flex items-center gap-1.5 rounded-lg border border-sky-300 bg-sky-50 px-3 py-1.5 text-xs font-semibold text-sky-700 hover:bg-sky-100"
              title="Nota de entrega NE-000004 existente en CoreBiz lista para cotejar y registrar"
            >
              <Download className="h-3.5 w-3.5 text-sky-600" />
              Descargar PDF CoreBiz (NE-000004)
            </button>
            <button
              onClick={() => downloadSamplePdf("NE-5001")}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50"
            >
              <Download className="h-3.5 w-3.5 text-slate-500" />
              PDF NE-5001
            </button>
          </div>
        </div>

        {mode !== "api" ? (
          <p className="mt-2 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800">
            El backend no está conectado. Pega el token de la API en{" "}
            <strong>Ajustes → Seguridad local</strong> y guarda; en local también vale levantar
            (`uvicorn app.main:app --port 8000`) y recargar.
          </p>
        ) : null}
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-4">
        {/* Upload Dropzone */}
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`cursor-pointer rounded-xl border-2 border-dashed p-6 text-center transition-colors ${
            dragOver
              ? "border-sky-500 bg-sky-50"
              : selectedFile
                ? "border-emerald-400 bg-emerald-50/40"
                : "border-slate-200 bg-slate-50 hover:bg-slate-100/70"
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.xml,.json,.xlsx,.txt"
            onChange={onFileChange}
            className="hidden"
          />

          {selectedFile ? (
            <div className="flex flex-col items-center">
              <div className="flex items-center gap-2 rounded-lg bg-white px-3 py-2 shadow-sm border border-emerald-200">
                <FileCheck className="h-5 w-5 text-emerald-600" />
                <span className="text-sm font-medium text-slate-800">{selectedFile.name}</span>
                <span className="text-xs text-slate-400">({(selectedFile.size / 1024).toFixed(1)} KB)</span>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    setSelectedFile(null);
                  }}
                  className="ml-2 rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
              <p className="mt-2 text-xs text-emerald-700">Archivo listo para procesar y cotejar contra CoreBiz.</p>
            </div>
          ) : (
            <div className="flex flex-col items-center">
              <Upload className="h-8 w-8 text-sky-600" />
              <p className="mt-2 text-sm font-medium text-slate-700">
                Arrastra tu PDF o archivo de nota de entrega aquí, o haz clic para seleccionarlo
              </p>
              <p className="mt-1 text-xs text-slate-400">
                Formatos compatibles: .PDF (notas de entrega / facturas), .XML (CFDI/UBL), .JSON, .XLSX
              </p>
            </div>
          )}
        </div>

        <div className="my-4 flex items-center gap-3">
          <div className="h-px flex-1 bg-slate-200" />
          <span className="text-xs font-medium text-slate-400">o prueba con ejemplos predefinidos</span>
          <div className="h-px flex-1 bg-slate-200" />
        </div>

        <div className="mb-3 flex flex-wrap gap-2">
          {SAMPLES.map((s) => (
            <button
              key={s.label}
              onClick={() => {
                setSelectedFile(null);
                setText(s.text);
                setFilename(s.filename);
                setSource(s.source);
                if (s.deliveryNote) setDeliveryNote(s.deliveryNote);
              }}
              className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium text-slate-600 hover:bg-slate-100"
            >
              {s.label}
            </button>
          ))}
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          <label className="block">
            <span className="mb-1 block text-xs text-slate-500">Nombre de archivo</span>
            <input
              value={filename}
              onChange={(e) => setFilename(e.target.value)}
              className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none focus:border-sky-400 focus:bg-white"
            />
          </label>
          <label className="block">
            <span className="mb-1 block text-xs text-slate-500">Origen</span>
            <select
              value={source}
              onChange={(e) => setSource(e.target.value)}
              className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none focus:border-sky-400 focus:bg-white"
            >
              <option value="api">API</option>
              <option value="carpeta">Carpeta / Carga manual</option>
              <option value="email">Correo electrónico</option>
            </select>
          </label>
        </div>

        <label className="mt-3 block">
          <span className="mb-1 block text-xs text-slate-500">
            Nº de nota de entrega / orden (opcional)
          </span>
          <input
            value={deliveryNote}
            onChange={(e) => setDeliveryNote(e.target.value)}
            placeholder="p. ej. NE-5001 o P-1042"
            className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none focus:border-sky-400 focus:bg-white"
          />
          <span className="mt-1 block text-xs text-slate-400">
            Se coteja contra el ERP (Corebiz). Si el documento contiene el número de remisión, el sistema lo detecta automáticamente.
          </span>
        </label>

        <label className="mt-3 flex items-start gap-2 text-xs text-slate-600">
          <input
            type="checkbox"
            checked={useBrowser}
            onChange={(e) => setUseBrowser(e.target.checked)}
            className="mt-0.5 h-4 w-4 rounded border-slate-300"
          />
          <span>
            Cotejar con la web del ERP (respaldo de navegador con Playwright)
            <span className="block text-slate-400">
              Para ERPs sin API. Solo lectura; la página se trata como entrada no confiable.
            </span>
          </span>
        </label>

        {!selectedFile ? (
          <label className="mt-3 block">
            <span className="mb-1 block text-xs text-slate-500">O contenido de texto / XML</span>
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              rows={8}
              spellCheck={false}
              placeholder="Pega aquí el contenido del documento o selecciona un archivo arriba…"
              className="w-full rounded-lg border border-slate-200 bg-slate-900 p-3 font-mono text-xs text-slate-100 outline-none focus:border-sky-400"
            />
          </label>
        ) : null}

        {error ? (
          <p className="mt-3 rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</p>
        ) : null}

        <div className="mt-4 flex items-center gap-3">
          <button
            onClick={run}
            disabled={busy || mode !== "api" || (!selectedFile && !text.trim())}
            className="inline-flex items-center gap-2 rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-700 disabled:cursor-not-allowed disabled:opacity-40 shadow-sm"
          >
            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileText className="h-4 w-4" />}
            {busy ? "Validando y procesando…" : selectedFile ? "Procesar y validar archivo" : "Procesar documento"}
          </button>
          <span className="text-xs text-slate-400">
            Valida todos los campos contra Corebiz. Al confirmar, se registra en el ERP.
          </span>
        </div>
      </div>
    </div>
  );
}
