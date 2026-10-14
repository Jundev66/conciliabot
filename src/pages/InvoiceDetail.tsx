import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  ArrowLeft,
  BadgeCheck,
  CheckCircle2,
  Copy,
  Cpu,
  Download,
  FileText,
  Link2,
  ScanLine,
  ShieldAlert,
  Truck,
  XCircle
} from "lucide-react";
import { api } from "../lib/api";
import { useStore } from "../lib/store";
import StatusBadge from "../components/StatusBadge";
import { dateTime, money, shortDate } from "../lib/format";
import { MODEL_LABEL, STEP_STYLE } from "../lib/labels";
import type { PipelineStep } from "../types";

const STEP_ICON: Record<string, typeof Cpu> = {
  ingest: FileText,
  preprocess: ShieldAlert,
  classify: Cpu,
  extract: ScanLine,
  fiscal: BadgeCheck,
  match: Link2,
  reconcile: CheckCircle2
};

function StepRow({ step }: { step: PipelineStep }) {
  const Icon = STEP_ICON[step.key] ?? Cpu;
  return (
    <div className="flex gap-3 py-3">
      <div className={`mt-0.5 ${STEP_STYLE[step.status]}`}>
        <Icon className="h-5 w-5" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <p className="text-sm font-medium text-slate-900">{step.label}</p>
          <span className={`text-xs font-medium ${STEP_STYLE[step.status]}`}>
            {step.status === "done"
              ? "listo"
              : step.status === "warning"
                ? "atención"
                : step.status === "running"
                  ? "en curso"
                  : step.status === "error"
                    ? "error"
                    : "pendiente"}
          </span>
        </div>
        <p className="mt-0.5 text-sm text-slate-600">{step.detail}</p>
        <p className="mt-1 text-xs text-slate-400">
          {MODEL_LABEL[step.model ?? "none"]}
          {step.tokens ? ` · ${step.tokens} tokens` : ""}
          {step.durationMs ? ` · ${step.durationMs} ms` : ""}
        </p>
      </div>
    </div>
  );
}

export default function InvoiceDetail() {
  const { id } = useParams();
  const { invoices, audit, settings, approve, reject, correct } = useStore();
  const inv = invoices.find((i) => i.id === id);
  const [actor, setActor] = useState("María López");
  const [correcting, setCorrecting] = useState(false);
  const [note, setNote] = useState("");
  const [downloading, setDownloading] = useState(false);

  if (!inv) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-8 text-center">
        <p className="text-slate-600">Factura no encontrada.</p>
        <Link to="/" className="mt-3 inline-block text-sm text-sky-600 underline">
          Volver a la bandeja
        </Link>
      </div>
    );
  }

  async function handleDownloadPdf() {
    if (!inv) return;
    setDownloading(true);
    try {
      await api.downloadInvoicePdf(inv.id);
    } finally {
      setDownloading(false);
    }
  }

  const invAudit = audit.filter((a) => a.invoiceId === inv.id);
  const canAct = ["matched", "discrepancy", "duplicate", "needs_review", "ingested", "approved"].includes(
    inv.status
  ) && inv.status !== "processing";

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <Link to="/" className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-800">
          <ArrowLeft className="h-4 w-4" /> Bandeja
        </Link>
        <button
          onClick={handleDownloadPdf}
          disabled={downloading}
          className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 shadow-sm hover:bg-slate-50 disabled:opacity-50"
        >
          <Download className="h-3.5 w-3.5 text-slate-500" />
          {downloading ? "Descargando…" : "Descargar PDF"}
        </button>
      </div>

      <section className="rounded-xl border border-slate-200 bg-white p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-semibold text-slate-900">{inv.provider.name}</h1>
              <StatusBadge status={inv.status} />
            </div>
            <p className="mt-1 text-sm text-slate-500">
              {inv.id} · {inv.format} {inv.folio} · {inv.provider.taxId} · {inv.country}
            </p>
            <p className="mt-0.5 text-xs text-slate-400">UUID/chave: {inv.uuid}</p>
          </div>
          <div className="text-right">
            <p className="text-2xl font-semibold text-slate-900">{money(inv.total, inv.currency)}</p>
            <p className="text-xs text-slate-500">
              emitida {shortDate(inv.issueDate)} · vence {shortDate(inv.dueDate)}
            </p>
          </div>
        </div>
      </section>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <section className="rounded-xl border border-slate-200 bg-white">
            <h2 className="border-b border-slate-200 px-4 py-3 text-sm font-semibold text-slate-800">
              Cotejo con la orden de compra
            </h2>
            <div className="p-4">
              {inv.purchaseOrder ? (
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-xs text-slate-500">
                      <th className="pb-2 font-medium">Concepto</th>
                      <th className="pb-2 text-right font-medium">Factura</th>
                      <th className="pb-2 text-right font-medium">Orden de compra</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    <tr>
                      <td className="py-2 text-slate-600">Subtotal</td>
                      <td className="py-2 text-right text-slate-900">{money(inv.subtotal, inv.currency)}</td>
                      <td className="py-2 text-right text-slate-500">—</td>
                    </tr>
                    <tr>
                      <td className="py-2 text-slate-600">Impuesto</td>
                      <td className="py-2 text-right text-slate-900">{money(inv.tax, inv.currency)}</td>
                      <td className="py-2 text-right text-slate-500">—</td>
                    </tr>
                    <tr>
                      <td className="py-2 font-medium text-slate-700">Total</td>
                      <td
                        className={`py-2 text-right font-semibold ${
                          inv.discrepancies.some((d) => d.field === "Importe total")
                            ? "text-orange-600"
                            : "text-slate-900"
                        }`}
                      >
                        {money(inv.total, inv.currency)}
                      </td>
                      <td className="py-2 text-right text-slate-900">
                        {money(inv.purchaseOrder.amount, inv.purchaseOrder.currency)}
                      </td>
                    </tr>
                  </tbody>
                </table>
              ) : (
                <p className="text-sm text-slate-500">No hay orden de compra asociada.</p>
              )}

              {inv.discrepancies.length > 0 ? (
                <div className="mt-4 space-y-2">
                  {inv.discrepancies.map((d) => (
                    <div
                      key={d.field}
                      className={`rounded-lg border p-3 text-sm ${
                        d.severity === "critical"
                          ? "border-rose-200 bg-rose-50"
                          : d.severity === "warning"
                            ? "border-amber-200 bg-amber-50"
                            : "border-slate-200 bg-slate-50"
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        {d.severity === "critical" ? (
                          <ShieldAlert className="h-4 w-4 text-rose-600" />
                        ) : (
                          <Copy className="h-4 w-4 text-amber-600" />
                        )}
                        <span className="font-medium text-slate-800">{d.field}</span>
                      </div>
                      <p className="mt-1 text-slate-700">{d.message}</p>
                      <p className="mt-1 text-xs text-slate-500">
                        Factura: {d.invoiceValue} · Esperado: {d.expectedValue}
                      </p>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="mt-4 flex items-center gap-2 text-sm text-emerald-700">
                  <CheckCircle2 className="h-4 w-4" /> Todo coincide con los registros del ERP.
                </p>
              )}
            </div>
          </section>

          {inv.deliveryNote ? (
            <section className="rounded-xl border border-slate-200 bg-white">
              <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
                <div className="flex items-center gap-2">
                  <Truck className="h-4 w-4 text-sky-600" />
                  <h2 className="text-sm font-semibold text-slate-800">
                    Cotejo con la Nota de Entrega (CoreBiz)
                  </h2>
                </div>
                <span className="rounded-full border border-sky-200 bg-sky-50 px-2.5 py-0.5 text-xs font-semibold text-sky-700">
                  Remisión: {inv.deliveryNote.number}
                </span>
              </div>
              <div className="p-4">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-xs text-slate-500">
                      <th className="pb-2 font-medium">Concepto</th>
                      <th className="pb-2 text-right font-medium">Documento</th>
                      <th className="pb-2 text-right font-medium">Nota de Entrega (CoreBiz)</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    <tr>
                      <td className="py-2 text-slate-600">Importe Total</td>
                      <td className="py-2 text-right text-slate-900">{money(inv.total, inv.currency)}</td>
                      <td className="py-2 text-right font-semibold text-slate-900">
                        {money(inv.deliveryNote.amount, inv.deliveryNote.currency)}
                      </td>
                    </tr>
                    <tr>
                      <td className="py-2 text-slate-600">Monto Recibido en Almacén</td>
                      <td className="py-2 text-right text-slate-500">—</td>
                      <td className="py-2 text-right font-medium text-emerald-600">
                        {money(inv.deliveryNote.receivedAmount, inv.deliveryNote.currency)}
                        {inv.deliveryNote.receivedAmount >= inv.deliveryNote.amount
                          ? " (100% Recibido)"
                          : " (Recepción Parcial)"}
                      </td>
                    </tr>
                    <tr>
                      <td className="py-2 text-slate-600">Estado de Recepción</td>
                      <td className="py-2 text-slate-500">—</td>
                      <td className="py-2 text-right font-medium text-slate-700">
                        {inv.deliveryNote.receivedAmount >= inv.deliveryNote.amount
                          ? "Entregada y Verificada"
                          : "Pendiente de Completar"}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </section>
          ) : null}

          <section className="rounded-xl border border-slate-200 bg-white">
            <h2 className="border-b border-slate-200 px-4 py-3 text-sm font-semibold text-slate-800">
              Trayectoria del agente
            </h2>
            <div className="divide-y divide-slate-100 px-4">
              {inv.pipeline.map((s) => (
                <StepRow key={s.key} step={s} />
              ))}
            </div>
          </section>

          <section className="rounded-xl border border-slate-200 bg-white">
            <h2 className="border-b border-slate-200 px-4 py-3 text-sm font-semibold text-slate-800">
              Trazas de esta factura
            </h2>
            <ul className="divide-y divide-slate-100">
              {invAudit.length === 0 ? (
                <li className="px-4 py-4 text-sm text-slate-500">Sin eventos registrados.</li>
              ) : (
                invAudit.map((a) => (
                  <li key={a.id} className="flex items-start gap-3 px-4 py-3 text-sm">
                    <span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-slate-300" />
                    <div>
                      <p className="text-slate-700">{a.detail}</p>
                      <p className="text-xs text-slate-400">
                        {a.actor} · {dateTime(a.at)}
                      </p>
                    </div>
                  </li>
                ))
              )}
            </ul>
          </section>
        </div>

        <div className="space-y-6">
          <section className="rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="mb-3 text-sm font-semibold text-slate-800">Verificación fiscal</h2>
            <div className="flex items-center gap-2 text-sm">
              <BadgeCheck
                className={`h-5 w-5 ${inv.fiscal.verified ? "text-emerald-600" : "text-amber-500"}`}
              />
              <span className="text-slate-700">
                {inv.fiscal.verified ? `Verificado (${inv.fiscal.authority})` : "En verificación"}
              </span>
            </div>
            <p className="mt-2 text-xs text-slate-500">{inv.fiscal.message}</p>
            <p className="mt-1 text-xs text-slate-400">{inv.fiscal.reference}</p>
          </section>

          <section className="rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="mb-3 text-sm font-semibold text-slate-800">Decisión humana (HITL)</h2>
            <label className="mb-1 block text-xs text-slate-500">Aprueba como</label>
            <input
              value={actor}
              onChange={(e) => setActor(e.target.value)}
              className="mb-3 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none focus:border-sky-400 focus:bg-white"
            />

            {inv.status === "approved" && (
              <div className="mb-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800">
                <p className="flex items-center gap-1.5 font-semibold text-amber-900">
                  <ShieldAlert className="h-4 w-4 text-amber-600" />
                  Aprobada localmente — Pendiente de registrar en CoreBiz
                </p>
                <p className="mt-1">
                  Aprobada por {inv.approvedBy} {inv.approvedAt ? `el ${dateTime(inv.approvedAt)}` : ""}.
                </p>
                {inv.note ? <p className="mt-1 font-mono text-[11px] text-amber-700">{inv.note}</p> : null}
              </div>
            )}

            {canAct ? (
              <div className="space-y-2">
                <button
                  onClick={() => approve(inv.id, actor)}
                  className="flex w-full items-center justify-center gap-2 rounded-lg bg-emerald-600 px-3 py-2 text-sm font-medium text-white shadow-sm hover:bg-emerald-700"
                >
                  <CheckCircle2 className="h-4 w-4" />
                  {inv.status === "approved"
                    ? "Reintentar registro en CoreBiz"
                    : "Confirmar y registrar en CoreBiz"}
                </button>
                <button
                  onClick={() => setCorrecting((v) => !v)}
                  className="flex w-full items-center justify-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
                >
                  Corregir y aprobar
                </button>
                {correcting ? (
                  <div className="rounded-lg border border-slate-200 p-3">
                    <textarea
                      value={note}
                      onChange={(e) => setNote(e.target.value)}
                      rows={2}
                      placeholder="Describe la corrección (queda en auditoría)…"
                      className="w-full rounded-md border border-slate-200 bg-slate-50 p-2 text-sm outline-none focus:border-sky-400 focus:bg-white"
                    />
                    <button
                      disabled={!note.trim()}
                      onClick={() => {
                        correct(inv.id, actor, note.trim());
                        setCorrecting(false);
                        setNote("");
                      }}
                      className="mt-2 w-full rounded-lg bg-sky-600 px-3 py-2 text-sm font-medium text-white hover:bg-sky-700 disabled:cursor-not-allowed disabled:opacity-40"
                    >
                      Guardar corrección y confirmar
                    </button>
                  </div>
                ) : null}
                <button
                  onClick={() => reject(inv.id, actor)}
                  className="flex w-full items-center justify-center gap-2 rounded-lg border border-rose-200 px-3 py-2 text-sm font-medium text-rose-600 hover:bg-rose-50"
                >
                  <XCircle className="h-4 w-4" /> Rechazar
                </button>
              </div>
            ) : (
              <div className="rounded-lg bg-slate-50 p-3 text-sm text-slate-600">
                {inv.status === "processing" ? (
                  "El agente aún está procesando esta factura."
                ) : inv.status === "registered" ? (
                  <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-xs text-emerald-800">
                    <p className="flex items-center gap-1.5 font-semibold text-emerald-900">
                      <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                      Registrada y confirmada en CoreBiz
                    </p>
                    <p className="mt-1">
                      Aprobada por {inv.approvedBy} {inv.approvedAt ? `el ${dateTime(inv.approvedAt)}` : ""}.
                    </p>
                    {inv.note ? <p className="mt-1 font-mono text-[11px] text-emerald-700">{inv.note}</p> : null}
                  </div>
                ) : (
                  `Estado actual: ${inv.status}. No requiere acción.`
                )}
                {inv.status !== "registered" && inv.approvedBy ? (
                  <p className="mt-1 text-xs text-slate-400">
                    Aprobada por {inv.approvedBy} · {inv.approvedAt ? dateTime(inv.approvedAt) : ""}
                  </p>
                ) : null}
              </div>
            )}

            <p className="mt-3 text-xs text-slate-500">
              Al aprobar, el sistema prepara el registro; en modo{" "}
              <span className="font-medium">{settings.mode}</span>{" "}
              {settings.mode === "conectado"
                ? "lo registra en el ERP (autorizado por el usuario)."
                : "te entrega el registro listo para importar. El agente nunca escribe solo en tu ERP."}
            </p>
          </section>
        </div>
      </div>
    </div>
  );
}
