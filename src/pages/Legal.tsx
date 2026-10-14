import { Link } from "react-router-dom";
import { FileText, Lock, ShieldCheck, ChevronRight } from "lucide-react";

const docs = [
  {
    to: "/legal/terminos",
    title: "Términos y Condiciones",
    desc: "Uso del software, licencia, límites de responsabilidad y responsabilidades del usuario.",
    icon: FileText
  },
  {
    to: "/legal/privacidad",
    title: "Política de Privacidad",
    desc: "Qué datos se tratan, con qué fin, dónde viven y por cuánto tiempo se conservan.",
    icon: Lock
  },
  {
    to: "/legal/aviso",
    title: "Aviso legal y modelo BYOC",
    desc: "El software corre en tu entorno. Tú controlas los datos; el agente solo propone.",
    icon: ShieldCheck
  }
];

export default function Legal() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold text-slate-900">Documentos legales</h1>
        <p className="text-sm text-slate-500">
          Transparencia primero: así se protege tanto al negocio como a tus datos.
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {docs.map((d) => {
          const Icon = d.icon;
          return (
            <Link
              key={d.to}
              to={d.to}
              className="group rounded-xl border border-slate-200 bg-white p-4 transition-colors hover:border-sky-300 hover:bg-sky-50/40"
            >
              <div className="mb-3 inline-grid h-9 w-9 place-items-center rounded-lg bg-slate-100 text-slate-600 group-hover:bg-sky-100 group-hover:text-sky-600">
                <Icon className="h-5 w-5" />
              </div>
              <div className="flex items-center justify-between gap-2">
                <p className="text-sm font-semibold text-slate-900">{d.title}</p>
                <ChevronRight className="h-4 w-4 text-slate-400" />
              </div>
              <p className="mt-1 text-xs text-slate-500">{d.desc}</p>
            </Link>
          );
        })}
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-5 text-sm text-slate-600">
        <p className="font-medium text-slate-800">Principios que rigen esta demo</p>
        <ul className="mt-2 list-disc space-y-1 pl-5">
          <li>Los datos de la demo son <strong>sintéticos</strong>: ninguna factura real.</li>
          <li>El núcleo está pensado para correr <strong>dentro del entorno del cliente</strong> (BYOC).</li>
          <li>El agente <strong>propone</strong>; la persona <strong>aprueba</strong>. Nada con efecto fiscal o económico ocurre sin humano.</li>
          <li>No se presenta asesoría ni gestión fiscal o contable.</li>
        </ul>
      </div>
    </div>
  );
}
