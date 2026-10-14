import { Link } from "react-router-dom";
import { Lock } from "lucide-react";
import { useStore } from "../lib/store";
import { dateTime } from "../lib/format";

const ACTION_LABEL: Record<string, string> = {
  ingested: "Ingesta",
  classified: "Clasificación",
  extracted: "Extracción",
  fiscal_verified: "Verificación fiscal",
  matched: "Cotejo",
  discrepancy_found: "Diferencia",
  duplicate_found: "Duplicado",
  approved: "Aprobación",
  rejected: "Rechazo",
  corrected: "Corrección",
  registered: "Registro"
};

export default function AuditLogPage() {
  const { audit, invoices } = useStore();
  const sorted = [...audit].sort((a, b) => (a.at < b.at ? 1 : -1));

  return (
    <div className="space-y-4">
      <div className="flex items-start gap-3 rounded-xl border border-slate-200 bg-white p-4">
        <Lock className="mt-0.5 h-5 w-5 text-slate-500" />
        <div>
          <h1 className="text-sm font-semibold text-slate-900">Registro de auditoría</h1>
          <p className="text-xs text-slate-500">
            Bitácora inmutable de cada llamada, decisión y acción. Base de tu trazabilidad y
            cumplimiento.
          </p>
        </div>
      </div>

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left text-xs text-slate-500">
            <tr>
              <th className="px-4 py-3 font-medium">Evento</th>
              <th className="px-4 py-3 font-medium">Factura</th>
              <th className="hidden px-4 py-3 font-medium sm:table-cell">Actor</th>
              <th className="px-4 py-3 font-medium">Fecha</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {sorted.map((a) => {
              const inv = invoices.find((i) => i.id === a.invoiceId);
              return (
                <tr key={a.id} className="align-top">
                  <td className="px-4 py-3">
                    <span className="inline-flex rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
                      {ACTION_LABEL[a.action] ?? a.action}
                    </span>
                    <p className="mt-1 text-slate-700">{a.detail}</p>
                  </td>
                  <td className="px-4 py-3">
                    <Link
                      to={`/facturas/${a.invoiceId}`}
                      className="text-sky-600 hover:underline"
                    >
                      {a.invoiceId}
                    </Link>
                    {inv ? <p className="text-xs text-slate-400">{inv.provider.name}</p> : null}
                  </td>
                  <td className="hidden px-4 py-3 text-slate-600 sm:table-cell">{a.actor}</td>
                  <td className="whitespace-nowrap px-4 py-3 text-xs text-slate-500">
                    {dateTime(a.at)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
