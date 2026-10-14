import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { Scale } from "lucide-react";

export function LegalSection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="space-y-2">
      <h2 className="text-sm font-semibold text-slate-900">{title}</h2>
      <div className="space-y-2 text-sm leading-relaxed text-slate-600">{children}</div>
    </section>
  );
}

export default function LegalPage({
  title,
  updated,
  children
}: {
  title: string;
  updated: string;
  children: ReactNode;
}) {
  return (
    <article className="space-y-6">
      <div className="flex items-start gap-3 rounded-xl border border-slate-200 bg-white p-4">
        <Scale className="mt-0.5 h-5 w-5 text-slate-500" />
        <div>
          <h1 className="text-base font-semibold text-slate-900">{title}</h1>
          <p className="text-xs text-slate-500">Última actualización: {updated}</p>
        </div>
      </div>

      <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-xs text-amber-900">
        Este documento es una <strong>plantilla de demostración</strong> para ConciliaBot (app
        demo). No constituye asesoría legal y debe ser revisado por un abogado y adaptado a cada
        país antes de usarse en producción.
      </div>

      <div className="space-y-6 rounded-xl border border-slate-200 bg-white p-5">{children}</div>

      <div className="text-xs text-slate-500">
        <Link to="/legal" className="underline">
          Volver a documentos legales
        </Link>
      </div>
    </article>
  );
}
