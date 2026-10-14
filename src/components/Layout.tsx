import { NavLink, Outlet } from "react-router-dom";
import {
  LayoutDashboard,
  ScrollText,
  Settings as SettingsIcon,
  ShieldCheck,
  FileText,
  Smartphone,
  Upload,
  FileSpreadsheet,
  FlaskConical
} from "lucide-react";
import { useStore } from "../lib/store";
import { isOpen, STATUS_LABEL } from "../lib/labels";

const nav = [
  { to: "/", label: "Bandeja", icon: LayoutDashboard, end: true },
  { to: "/ingesta", label: "Ingesta", icon: Upload, end: false },
  { to: "/datos", label: "Datos", icon: FileSpreadsheet, end: false },
  { to: "/auditoria", label: "Auditoría", icon: ScrollText, end: false },
  { to: "/evals", label: "Evals", icon: FlaskConical, end: false },
  { to: "/configuracion", label: "Configuración", icon: SettingsIcon, end: false },
  { to: "/legal", label: "Legal", icon: FileText, end: false }
];

const CONNECTION: Record<string, { label: string; cls: string }> = {
  api: { label: "Backend activo", cls: "border-emerald-200 bg-emerald-50 text-emerald-700" },
  local: { label: "Modo local (sin backend)", cls: "border-slate-200 bg-slate-100 text-slate-600" },
  loading: { label: "Conectando…", cls: "border-sky-200 bg-sky-50 text-sky-700" }
};

export default function Layout() {
  const { invoices, settings, mode } = useStore();
  const pending = invoices.filter((i) => isOpen(i.status)).length;
  const conn = CONNECTION[mode] ?? CONNECTION.loading;

  return (
    <div className="flex min-h-full flex-col md:flex-row">
      <aside className="md:w-64 md:shrink-0 bg-slate-900 text-slate-100 md:min-h-screen">
        <div className="flex items-center gap-3 px-5 py-4 md:py-6">
          <div className="grid h-10 w-10 place-items-center rounded-xl bg-sky-500/15 ring-1 ring-sky-400/40">
            <ShieldCheck className="h-5 w-5 text-sky-400" />
          </div>
          <div>
            <p className="text-base font-semibold leading-tight">ConciliaBot</p>
            <p className="text-xs text-slate-400">Facturas · LATAM</p>
          </div>
        </div>
        <nav className="flex gap-1 overflow-x-auto px-3 pb-3 md:flex-col md:overflow-visible md:pb-0">
          {nav.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  [
                    "flex items-center gap-2 rounded-lg px-3 py-2 text-sm whitespace-nowrap transition-colors",
                    isActive
                      ? "bg-sky-500/15 text-sky-300 ring-1 ring-sky-400/30"
                      : "text-slate-300 hover:bg-white/5"
                  ].join(" ")
                }
              >
                <Icon className="h-4 w-4" />
                <span>{item.label}</span>
                {item.to === "/" && pending > 0 ? (
                  <span className="ml-auto hidden rounded-full bg-amber-400/20 px-2 text-xs text-amber-300 md:inline">
                    {pending}
                  </span>
                ) : null}
              </NavLink>
            );
          })}
        </nav>
        <div className="mt-auto hidden px-5 py-6 md:block">
          <div className="rounded-lg bg-white/5 p-3 text-xs text-slate-300 ring-1 ring-white/10">
            <p className="mb-1 flex items-center gap-1 font-medium text-slate-100">
              <Smartphone className="h-3.5 w-3.5" /> Demo instalable
            </p>
            <p>
              Modo <span className="text-sky-300">{settings.mode}</span> · Datos sintéticos, nada
              sale de tu equipo.
            </p>
          </div>
        </div>
      </aside>

      <main className="flex-1">
        <header className="sticky top-0 z-10 border-b border-slate-200 bg-white/85 backdrop-blur">
          <div className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-4 py-3">
            <div>
              <p className="text-sm font-medium text-slate-900">Panel de conciliación</p>
              <p className="text-xs text-slate-500">
                {pending} factura(s) en espera · {STATUS_LABEL.matched} y demás estados visibles abajo
              </p>
            </div>
            <div className="flex items-center gap-2">
              <span className={`rounded-full border px-3 py-1 text-xs font-medium ${conn.cls}`}>
                {conn.label}
              </span>
              <span className="hidden rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-xs font-medium text-amber-800 sm:inline">
                Demo · datos sintéticos
              </span>
            </div>
          </div>
        </header>
        <div className="mx-auto max-w-6xl px-4 py-6">
          <Outlet />
        </div>
        <footer className="mx-auto max-w-6xl px-4 pb-10 pt-4 text-xs text-slate-500">
          ConciliaBot demo · Software de conciliación (BYOC). No es asesoría fiscal ni contable. Ver{" "}
          <NavLink className="underline" to="/legal">
            Términos y Privacidad
          </NavLink>
          .
        </footer>
      </main>
    </div>
  );
}
