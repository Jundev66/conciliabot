import { useRef, useState } from "react";
import type { ChangeEvent } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Download,
  FileSpreadsheet,
  Loader2,
  Upload
} from "lucide-react";
import { api, importSpreadsheet, type SpreadsheetImportResult } from "../lib/api";
import { useStore } from "../lib/store";

const PREVIEW_COLUMNS: { key: string; label: string }[] = [
  { key: "number", label: "Nº nota" },
  { key: "customerName", label: "Cliente" },
  { key: "currency", label: "Moneda" },
  { key: "total", label: "Total" },
  { key: "receivedAmount", label: "Recibido" },
  { key: "status", label: "Estado" }
];

export default function Data() {
  const { mode } = useStore();
  const inputRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<SpreadsheetImportResult | null>(null);
  const [error, setError] = useState("");
  const offline = mode !== "api";

  async function runDownload(task: () => Promise<void>) {
    setError("");
    try {
      await task();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function onFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setBusy(true);
    setError("");
    setResult(null);
    try {
      setResult(await importSpreadsheet(file));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-slate-200 bg-white p-4">
        <h1 className="flex items-center gap-2 text-sm font-semibold text-slate-900">
          <FileSpreadsheet className="h-4 w-4 text-sky-600" />
          Datos · Excel de notas de entrega
        </h1>
        <p className="mt-1 text-xs text-slate-500">
          El ejemplo sigue el esquema de CoreBiz
          (<span className="font-mono">/v1/integrations/delivery-notes</span>): nº de nota, cliente,
          moneda, total, estado y fechas. Descárgalo, edítalo e impórtalo para validar el cotejo sin
          tocar el ERP real.
        </p>
        {offline ? (
          <p className="mt-2 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800">
            El backend no está conectado. Pega el token de la API en{" "}
            <strong>Ajustes → Seguridad local</strong> y guarda para descargar o importar.
          </p>
        ) : null}
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-semibold text-slate-900">Descargar ejemplos y registros</h2>
          <p className="mt-1 text-xs text-slate-500">
            Descarga la nota de entrega de ejemplo en <strong>PDF</strong> (ideal para probar validación e ingesta) o en Excel (.xlsx).
          </p>
          <div className="mt-3 flex flex-col gap-2">
            <button
              onClick={() => runDownload(() => api.downloadPdfTemplate("NE-000004"))}
              disabled={offline}
              className="inline-flex items-center justify-center gap-2 rounded-lg bg-sky-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-sky-700 disabled:cursor-not-allowed disabled:opacity-40"
            >
              <Download className="h-4 w-4" />
              Descargar PDF CoreBiz (Nota NE-000004 · Panadería Santa Rosa)
            </button>
            <button
              onClick={() => runDownload(() => api.downloadPdfTemplate("NE-5001"))}
              disabled={offline}
              className="inline-flex items-center justify-center gap-2 rounded-lg border border-indigo-200 bg-indigo-50 px-4 py-2 text-sm font-medium text-indigo-700 hover:bg-indigo-100 disabled:cursor-not-allowed disabled:opacity-40"
            >
              <Download className="h-4 w-4" />
              Descargar PDF Estándar (Nota NE-5001)
            </button>
            <button
              onClick={() => runDownload(() => api.downloadTemplate())}
              disabled={offline}
              className="inline-flex items-center justify-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
            >
              <Download className="h-4 w-4" />
              Descargar ejemplo en Excel (.xlsx)
            </button>
            <button
              onClick={() => runDownload(() => api.downloadRecords())}
              disabled={offline}
              className="inline-flex items-center justify-center gap-2 rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
            >
              <Download className="h-4 w-4" />
              Exportar registros conciliados (.xlsx)
            </button>
          </div>
          <p className="mt-2 text-xs text-slate-400">
            El PDF de NE-000004 se coteja contra CoreBiz real y permite confirmar su entrega directamente en el ERP.
          </p>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-semibold text-slate-900">Importar y validar</h2>
          <p className="mt-1 text-xs text-slate-500">
            Sube un <span className="font-mono">.xlsx</span> con las mismas columnas. Se valida en
            seco (solo lectura): nada se registra.
          </p>
          <button
            onClick={() => inputRef.current?.click()}
            disabled={busy || offline}
            className="mt-3 inline-flex items-center gap-2 rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
            {busy ? "Leyendo…" : "Elegir archivo .xlsx"}
          </button>
          <input
            ref={inputRef}
            type="file"
            accept=".xlsx"
            onChange={onFile}
            className="hidden"
          />
          <p className="mt-3 text-xs text-slate-400">
            Tip: usa el “Nº nota” en <span className="font-medium text-slate-500">Ingesta → Nº de
            nota de entrega</span> para cotejar contra CoreBiz.
          </p>
        </div>
      </div>

      {error ? (
        <p className="flex items-center gap-2 rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700">
          <AlertTriangle className="h-4 w-4" />
          {error}
        </p>
      ) : null}

      {result ? (
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <div className="flex flex-wrap items-center gap-3">
            <span className="flex items-center gap-2 text-sm font-medium text-slate-900">
              <CheckCircle2 className="h-4 w-4 text-emerald-600" />
              {result.filename}
            </span>
            <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs text-slate-600">
              {result.count} fila(s)
            </span>
            <span
              className={[
                "rounded-full border px-3 py-1 text-xs font-medium",
                result.errors.length
                  ? "border-amber-200 bg-amber-50 text-amber-800"
                  : "border-emerald-200 bg-emerald-50 text-emerald-700"
              ].join(" ")}
            >
              {result.errors.length} observación(es)
            </span>
          </div>

          {result.errors.length ? (
            <ul className="mt-3 space-y-1 text-xs text-amber-800">
              {result.errors.slice(0, 10).map((err, i) => (
                <li key={i}>
                  Fila {err.row} · {err.field || "—"}: {err.message}
                </li>
              ))}
            </ul>
          ) : null}

          <div className="mt-3 overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-200 text-slate-500">
                  {PREVIEW_COLUMNS.map((col) => (
                    <th key={col.key} className="py-2 pr-4 font-medium">
                      {col.label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {result.rows.slice(0, 50).map((row, i) => (
                  <tr key={i} className="border-b border-slate-100 text-slate-700">
                    {PREVIEW_COLUMNS.map((col) => (
                      <td key={col.key} className="py-1.5 pr-4">
                        {String(row[col.key] ?? "")}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}
    </div>
  );
}
