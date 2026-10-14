import { useState } from "react";
import { FlaskConical, Loader2, CheckCircle2, XCircle } from "lucide-react";
import { api, type EvalResult } from "../lib/api";
import { useStore } from "../lib/store";

const METRIC_LABEL: Record<string, string> = {
  status_accuracy: "Precisión de estado",
  format_accuracy: "Precisión de formato",
  fiscal_accuracy: "Precisión fiscal",
  discrepancy_accuracy: "Detección de diferencias",
  duplicate_recall: "Recall de duplicados",
  trajectory_pass_rate: "Trayectoria correcta"
};

export default function Evals() {
  const { mode } = useStore();
  const [result, setResult] = useState<EvalResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function run() {
    setBusy(true);
    setError("");
    try {
      setResult(await api.runEvals());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al ejecutar evals");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-3 rounded-xl border border-slate-200 bg-white p-4">
        <div className="flex items-start gap-3">
          <FlaskConical className="mt-0.5 h-5 w-5 text-slate-500" />
          <div>
            <h1 className="text-sm font-semibold text-slate-900">Evaluaciones (evals)</h1>
            <p className="text-xs text-slate-500">
              Conjunto dorado ejecutado contra el pipeline real, en una base de datos aislada. Es el
              mismo chequeo que bloquearía un despliegue en CI.
            </p>
          </div>
        </div>
        <button
          onClick={run}
          disabled={busy || mode !== "api"}
          className="inline-flex items-center gap-2 rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <FlaskConical className="h-4 w-4" />}
          {busy ? "Ejecutando…" : "Ejecutar evals"}
        </button>
      </div>

      {mode !== "api" ? (
        <p className="rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800">
          Conecta el backend para ejecutar las evals.
        </p>
      ) : null}
      {error ? (
        <p className="rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</p>
      ) : null}

      {result ? (
        <>
          <div
            className={`flex items-center gap-3 rounded-xl border p-4 ${
              result.passed
                ? "border-emerald-200 bg-emerald-50 text-emerald-800"
                : "border-rose-200 bg-rose-50 text-rose-800"
            }`}
          >
            {result.passed ? (
              <CheckCircle2 className="h-5 w-5" />
            ) : (
              <XCircle className="h-5 w-5" />
            )}
            <div>
              <p className="text-sm font-semibold">
                {result.passed ? "Gate superado" : "Gate fallido"}
              </p>
              <p className="text-xs">
                {result.case_count} casos · umbral y resultados detallados abajo.
              </p>
            </div>
          </div>

          <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-left text-xs text-slate-500">
                <tr>
                  <th className="px-4 py-3 font-medium">Métrica</th>
                  <th className="px-4 py-3 text-right font-medium">Resultado</th>
                  <th className="px-4 py-3 text-right font-medium">Umbral</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {Object.entries(result.metrics).map(([k, v]) => {
                  const threshold = result.thresholds[k];
                  const ok = v >= threshold;
                  return (
                    <tr key={k}>
                      <td className="px-4 py-3 text-slate-700">{METRIC_LABEL[k] ?? k}</td>
                      <td className={`px-4 py-3 text-right font-medium ${ok ? "text-emerald-600" : "text-rose-600"}`}>
                        {v}
                      </td>
                      <td className="px-4 py-3 text-right text-slate-500">{threshold}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-left text-xs text-slate-500">
                <tr>
                  <th className="px-4 py-3 font-medium">Caso</th>
                  <th className="px-4 py-3 font-medium">Esperado</th>
                  <th className="px-4 py-3 font-medium">Obtenido</th>
                  <th className="px-4 py-3 font-medium">OK</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {result.cases.map((c) => (
                  <tr key={c.id}>
                    <td className="px-4 py-3 font-mono text-xs text-slate-700">{c.id}</td>
                    <td className="px-4 py-3 text-slate-600">{c.expected_status}</td>
                    <td className="px-4 py-3 text-slate-600">{c.actual_status}</td>
                    <td className="px-4 py-3">
                      {c.ok ? (
                        <span className="text-emerald-600">sí</span>
                      ) : (
                        <span className="text-rose-600">no</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : null}
    </div>
  );
}
