import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { AlertTriangle, CheckCircle2, Copy, FileClock, Inbox, Search } from "lucide-react";
import { useStore } from "../lib/store";
import StatusBadge from "../components/StatusBadge";
import { money, shortDate } from "../lib/format";
import { isOpen, STATUS_LABEL } from "../lib/labels";
import type { InvoiceStatus } from "../types";

const FILTERS: { key: "todas" | InvoiceStatus; label: string }[] = [
  { key: "todas", label: "Todas" },
  { key: "matched", label: STATUS_LABEL.matched },
  { key: "discrepancy", label: STATUS_LABEL.discrepancy },
  { key: "duplicate", label: STATUS_LABEL.duplicate },
  { key: "needs_review", label: STATUS_LABEL.needs_review },
  { key: "processing", label: STATUS_LABEL.processing },
  { key: "approved", label: STATUS_LABEL.approved }
];

export default function Dashboard() {
  const { invoices } = useStore();
  const [filter, setFilter] = useState<"todas" | InvoiceStatus>("todas");
  const [query, setQuery] = useState("");

  const stats = useMemo(
    () => ({
      total: invoices.length,
      open: invoices.filter((i) => isOpen(i.status)).length,
      matched: invoices.filter((i) => i.status === "matched").length,
      issues: invoices.filter((i) => i.status === "discrepancy" || i.status === "duplicate").length,
      approved: invoices.filter((i) => i.status === "approved" || i.status === "registered").length
    }),
    [invoices]
  );

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    return invoices.filter((i) => {
      if (filter !== "todas" && i.status !== filter) return false;
      if (!q) return true;
      return (
        i.provider.name.toLowerCase().includes(q) ||
        i.folio.toLowerCase().includes(q) ||
        i.id.toLowerCase().includes(q) ||
        (i.purchaseOrder?.number.toLowerCase().includes(q) ?? false)
      );
    });
  }, [invoices, filter, query]);

  const cards = [
    { label: "En bandeja", value: stats.open, icon: Inbox, tone: "text-sky-600 bg-sky-50" },
    { label: "Conciliadas", value: stats.matched, icon: CheckCircle2, tone: "text-emerald-600 bg-emerald-50" },
    { label: "Con problemas", value: stats.issues, icon: AlertTriangle, tone: "text-orange-600 bg-orange-50" },
    { label: "Aprobadas", value: stats.approved, icon: FileClock, tone: "text-indigo-600 bg-indigo-50" }
  ];

  return (
    <div className="space-y-6">
      <section className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {cards.map((c) => {
          const Icon = c.icon;
          return (
            <div key={c.label} className="rounded-xl border border-slate-200 bg-white p-4">
              <div className={`mb-3 inline-grid h-9 w-9 place-items-center rounded-lg ${c.tone}`}>
                <Icon className="h-5 w-5" />
              </div>
              <p className="text-2xl font-semibold text-slate-900">{c.value}</p>
              <p className="text-xs text-slate-500">{c.label}</p>
            </div>
          );
        })}
      </section>

      <section className="rounded-xl border border-slate-200 bg-white">
        <div className="flex flex-col gap-3 border-b border-slate-200 p-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex flex-wrap gap-1.5">
            {FILTERS.map((f) => (
              <button
                key={f.key}
                onClick={() => setFilter(f.key)}
                className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                  filter === f.key
                    ? "bg-slate-900 text-white"
                    : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Buscar proveedor, folio u OC…"
              className="w-full rounded-lg border border-slate-200 bg-slate-50 py-2 pl-9 pr-3 text-sm outline-none focus:border-sky-400 focus:bg-white lg:w-72"
            />
          </div>
        </div>

        <div className="divide-y divide-slate-100">
          {visible.map((inv) => {
            const problem = inv.status === "discrepancy" || inv.status === "duplicate";
            return (
              <Link
                key={inv.id}
                to={`/facturas/${inv.id}`}
                className="flex flex-wrap items-center gap-3 p-4 transition-colors hover:bg-slate-50"
              >
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <p className="truncate font-medium text-slate-900">{inv.provider.name}</p>
                    {problem ? (
                      <AlertTriangle className="h-4 w-4 shrink-0 text-orange-500" />
                    ) : inv.status === "duplicate" ? (
                      <Copy className="h-4 w-4 shrink-0 text-rose-500" />
                    ) : null}
                  </div>
                  <p className="mt-0.5 text-xs text-slate-500">
                    {inv.id} · {inv.format} {inv.folio} · vence {shortDate(inv.dueDate)}
                  </p>
                </div>
                <div className="text-right">
                  <p className="font-medium text-slate-900">{money(inv.total, inv.currency)}</p>
                  {inv.purchaseOrder ? (
                    <p className="text-xs text-slate-500">OC {inv.purchaseOrder.number}</p>
                  ) : (
                    <p className="text-xs text-slate-400">sin OC</p>
                  )}
                </div>
                <StatusBadge status={inv.status} />
              </Link>
            );
          })}
          {visible.length === 0 ? (
            <div className="p-10 text-center text-sm text-slate-500">Sin facturas que coincidan.</div>
          ) : null}
        </div>
      </section>
    </div>
  );
}
