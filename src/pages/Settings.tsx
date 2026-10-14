import { useEffect, useState } from "react";
import { Plug, RotateCcw, ServerCog } from "lucide-react";
import { useStore } from "../lib/store";
import type { AppSettings, Country } from "../types";
import { AUTHORITY } from "../data/sampleData";
import {
  api,
  getApiToken,
  setApiToken,
  type CorebizConfig,
  type ErpConfig,
  type McpTool,
  type ProbeResult,
  type ToolsStatus
} from "../lib/api";

function Toggle({
  label,
  hint,
  checked,
  onChange
}: {
  label: string;
  hint: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <label className="flex cursor-pointer items-start justify-between gap-4 py-3">
      <span>
        <span className="block text-sm font-medium text-slate-800">{label}</span>
        <span className="mt-0.5 block text-xs text-slate-500">{hint}</span>
      </span>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={`relative mt-0.5 h-6 w-11 shrink-0 rounded-full transition-colors ${
          checked ? "bg-emerald-500" : "bg-slate-300"
        }`}
      >
        <span
          className={`absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-all ${
            checked ? "left-[22px]" : "left-0.5"
          }`}
        />
      </button>
    </label>
  );
}

const COUNTRIES: Country[] = ["MX", "BR", "CO", "CL", "PE", "AR", "EC"];

export default function Settings() {
  const { settings, updateSettings, reset, reconnect } = useStore();
  const set = (patch: Partial<AppSettings>) => updateSettings(patch);
  const [tools, setTools] = useState<ToolsStatus | null>(null);
  const [mcpTools, setMcpTools] = useState<McpTool[]>([]);
  const [erpCfg, setErpCfg] = useState<ErpConfig | null>(null);
  const [probe, setProbe] = useState<ProbeResult | null>(null);
  const [erpBusy, setErpBusy] = useState(false);
  const [erpMsg, setErpMsg] = useState("");
  const [token, setToken] = useState(() => getApiToken());
  const [tokenMsg, setTokenMsg] = useState("");

  useEffect(() => {
    api.toolsStatus().then(setTools).catch(() => setTools(null));
    api
      .mcpTools()
      .then((r) => setMcpTools(r.tools))
      .catch(() => setMcpTools([]));
    api.erpConfig().then(setErpCfg).catch(() => setErpCfg(null));
  }, []);

  const setCorebiz = (patch: Partial<CorebizConfig>) =>
    setErpCfg((c) => (c ? { ...c, corebiz: { ...c.corebiz, ...patch } } : c));

  async function saveErp() {
    if (!erpCfg) return;
    setErpBusy(true);
    setErpMsg("");
    try {
      setErpCfg(await api.saveErpConfig(erpCfg));
      setErpMsg("Configuración guardada.");
    } catch (e) {
      setErpMsg(e instanceof Error ? e.message : "Error al guardar");
    } finally {
      setErpBusy(false);
    }
  }

  async function testErp() {
    setErpBusy(true);
    setProbe(null);
    setErpMsg("");
    try {
      setProbe(await api.testErp());
    } catch (e) {
      setErpMsg(e instanceof Error ? e.message : "Error al probar");
    } finally {
      setErpBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start gap-3 rounded-xl border border-slate-200 bg-white p-4">
        <ServerCog className="mt-0.5 h-5 w-5 text-slate-500" />
        <div>
          <h1 className="text-sm font-semibold text-slate-900">Configuración</h1>
          <p className="text-xs text-slate-500">
            El país es configuración, no código: cambia formato fiscal y autoridad sin tocar el
            núcleo.
          </p>
        </div>
      </div>

      <section className="rounded-xl border border-slate-200 bg-white p-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="block">
            <span className="mb-1 block text-sm font-medium text-slate-800">País</span>
            <select
              value={settings.country}
              onChange={(e) => set({ country: e.target.value as Country })}
              className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none focus:border-sky-400 focus:bg-white"
            >
              {COUNTRIES.map((c) => (
                <option key={c} value={c}>
                  {c} · autoridad {AUTHORITY[c]}
                </option>
              ))}
            </select>
            <span className="mt-1 block text-xs text-slate-500">
              Formato fiscal y verificación adaptados a {AUTHORITY[settings.country]}.
            </span>
          </label>

          <label className="block">
            <span className="mb-1 block text-sm font-medium text-slate-800">Modo de registro</span>
            <select
              value={settings.mode}
              onChange={(e) => set({ mode: e.target.value as AppSettings["mode"] })}
              className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none focus:border-sky-400 focus:bg-white"
            >
              <option value="seguro">Seguro (prepara, tú importas)</option>
              <option value="conectado">Conectado (registra en tu ERP)</option>
            </select>
            <span className="mt-1 block text-xs text-slate-500">
              En modo seguro el agente nunca escribe solo en tu ERP.
            </span>
          </label>

          <label className="block sm:col-span-2">
            <span className="mb-1 block text-sm font-medium text-slate-800">ERP conectado (demo)</span>
            <input
              value={settings.erp}
              onChange={(e) => set({ erp: e.target.value })}
              className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none focus:border-sky-400 focus:bg-white"
            />
          </label>
        </div>
      </section>

      <section className="divide-y divide-slate-100 rounded-xl border border-slate-200 bg-white px-4 py-1">
        <Toggle
          label="Conexión al ERP autorizada por el usuario"
          hint="Sin esta autorización no se lee ni escribe nada en el ERP. Es del usuario, no del proveedor."
          checked={settings.connectionAuthorized}
          onChange={(v) => set({ connectionAuthorized: v })}
        />
        <Toggle
          label="Exigir verificación fiscal"
          hint="Valida sello/UUID/CUFE contra la autoridad antes de proponer el registro."
          checked={settings.requireFiscalVerification}
          onChange={(v) => set({ requireFiscalVerification: v })}
        />
        <Toggle
          label="Redactar PII y secretos antes del modelo"
          hint="Los datos sensibles se enmascaran antes de llegar a cualquier modelo."
          checked={settings.piiRedaction}
          onChange={(v) => set({ piiRedaction: v })}
        />
        <Toggle
          label="Guardia contra inyección de prompt"
          hint="Cada documento se trata como entrada no confiable."
          checked={settings.promptInjectionGuard}
          onChange={(v) => set({ promptInjectionGuard: v })}
        />
        <Toggle
          label="Ruteo dinámico de modelos"
          hint="Fáciles al modelo chico; difíciles al de razonamiento. Con presupuesto de tokens y tiempo."
          checked={settings.modelRouting}
          onChange={(v) => set({ modelRouting: v })}
        />
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-4">
        <div className="flex items-center gap-2">
          <Plug className="h-4 w-4 text-slate-500" />
          <h2 className="text-sm font-semibold text-slate-900">Conexión al ERP (Corebiz)</h2>
        </div>
        {erpCfg ? (
          <div className="mt-3 space-y-3">
            <label className="block">
              <span className="mb-1 block text-xs text-slate-500">Proveedor</span>
              <select
                value={erpCfg.provider}
                onChange={(e) => setErpCfg({ ...erpCfg, provider: e.target.value })}
                className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none focus:border-sky-400 focus:bg-white sm:w-64"
              >
                <option value="demo">Demo (datos sintéticos)</option>
                <option value="corebiz">CoreBiz (API REST)</option>
              </select>
            </label>

            {erpCfg.provider === "corebiz" ? (
              <div className="grid gap-3 sm:grid-cols-2">
                <label className="block sm:col-span-2">
                  <span className="mb-1 block text-xs text-slate-500">URL base de la API</span>
                  <input
                    value={erpCfg.corebiz.baseUrl}
                    onChange={(e) => setCorebiz({ baseUrl: e.target.value })}
                    placeholder="https://api.corebiz.tu-dominio.com"
                    className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none focus:border-sky-400 focus:bg-white"
                  />
                </label>
                <label className="block">
                  <span className="mb-1 block text-xs text-slate-500">API key / token</span>
                  <input
                    type="password"
                    value={erpCfg.corebiz.apiKey}
                    onChange={(e) => setCorebiz({ apiKey: e.target.value })}
                    placeholder="se guarda solo en este equipo"
                    className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none focus:border-sky-400 focus:bg-white"
                  />
                </label>
                <label className="block">
                  <span className="mb-1 block text-xs text-slate-500">Empresa (x-corebiz-tenant)</span>
                  <input
                    value={erpCfg.corebiz.tenantId}
                    onChange={(e) => setCorebiz({ tenantId: e.target.value })}
                    placeholder="se detecta del token si se deja vacío"
                    className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none focus:border-sky-400 focus:bg-white"
                  />
                </label>
                <label className="block">
                  <span className="mb-1 block text-xs text-slate-500">Ruta del recurso</span>
                  <input
                    value={erpCfg.corebiz.recordsPath}
                    onChange={(e) => setCorebiz({ recordsPath: e.target.value })}
                    placeholder="/v1/integrations/delivery-notes"
                    className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none focus:border-sky-400 focus:bg-white"
                  />
                </label>
                <label className="block">
                  <span className="mb-1 block text-xs text-slate-500">Cabecera del token</span>
                  <input
                    value={erpCfg.corebiz.tokenHeader}
                    onChange={(e) => setCorebiz({ tokenHeader: e.target.value })}
                    className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none focus:border-sky-400 focus:bg-white"
                  />
                </label>
                <label className="block">
                  <span className="mb-1 block text-xs text-slate-500">Prefijo del token</span>
                  <input
                    value={erpCfg.corebiz.tokenPrefix}
                    onChange={(e) => setCorebiz({ tokenPrefix: e.target.value })}
                    className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none focus:border-sky-400 focus:bg-white"
                  />
                </label>
              </div>
            ) : null}

            <div className="flex flex-wrap items-center gap-3">
              <button
                onClick={saveErp}
                disabled={erpBusy}
                className="inline-flex items-center gap-2 rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-700 disabled:opacity-40"
              >
                Guardar conexión
              </button>
              <button
                onClick={testErp}
                disabled={erpBusy}
                className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100 disabled:opacity-40"
              >
                Probar conexión
              </button>
              {erpMsg ? <span className="text-xs text-slate-500">{erpMsg}</span> : null}
            </div>

            {probe ? (
              <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                <p className="text-xs font-medium text-slate-700">
                  {probe.ok ? "Conexión correcta" : "Revisa la configuración"}
                  {probe.mode ? ` · modo ${probe.mode}` : ""}
                </p>
                <ul className="mt-2 space-y-1">
                  {probe.steps.map((s) => (
                    <li key={s.key} className="text-xs">
                      <span
                        className={
                          s.status === "ok"
                            ? "text-emerald-600"
                            : s.status === "error"
                              ? "text-rose-600"
                              : "text-amber-600"
                        }
                      >
                        ●
                      </span>{" "}
                      <span className="font-medium text-slate-700">{s.key}</span>{" "}
                      <span className="text-slate-500">{s.detail}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </div>
        ) : (
          <p className="mt-2 text-xs text-slate-400">
            Conecta el backend para configurar el ERP.
          </p>
        )}
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-4">
        <div className="flex items-center gap-2">
          <Plug className="h-4 w-4 text-slate-500" />
          <h2 className="text-sm font-semibold text-slate-900">Herramientas e integraciones</h2>
        </div>
        {tools ? (
          <>
            <div className="mt-3 grid gap-3 sm:grid-cols-2">
              <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                <p className="text-xs text-slate-500">Transporte del ERP</p>
                <p className="mt-0.5 text-sm font-medium text-slate-800">
                  {tools.erp.backend === "mcp" ? "Servidor MCP (real)" : "Sandbox en proceso"}
                </p>
                <p className="mt-0.5 text-xs text-slate-500">
                  {tools.erp.mcpEnabled ? "MCP habilitado" : "MCP deshabilitado (fallback)"}
                </p>
              </div>
              <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                <p className="text-xs text-slate-500">Respaldo de navegador</p>
                <p className="mt-0.5 text-sm font-medium text-slate-800">
                  {tools.browser.available ? "Playwright disponible" : "No disponible"}
                </p>
                <p className="mt-0.5 text-xs text-slate-500">
                  {tools.browser.enabled ? "Habilitado" : "Deshabilitado"}
                </p>
              </div>
            </div>
            <div className="mt-3">
              <p className="text-xs text-slate-500">Herramientas MCP expuestas (solo lectura)</p>
              {mcpTools.length ? (
                <ul className="mt-2 space-y-1.5">
                  {mcpTools.map((t) => (
                    <li key={t.name} className="text-xs text-slate-600">
                      <code className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[11px] text-slate-800">
                        {t.name}
                      </code>{" "}
                      {t.description}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="mt-2 text-xs text-slate-400">
                  Sin servidor MCP conectado (usando el sandbox en proceso).
                </p>
              )}
            </div>
          </>
        ) : (
          <p className="mt-2 text-xs text-slate-400">
            Conecta el backend para ver el estado de las herramientas.
          </p>
        )}
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-4">
        <div className="flex items-center gap-2">
          <ServerCog className="h-4 w-4 text-slate-500" />
          <h2 className="text-sm font-semibold text-slate-900">Seguridad local</h2>
        </div>
        <p className="mt-1 text-xs text-slate-500">
          La API exige token a todo cliente que no sea la propia máquina. Al entrar por la web
          (a través del proxy) también lo pide: copia el token de
          <code className="mx-1 rounded bg-slate-100 px-1 py-0.5 font-mono text-[11px]">
            backend/data/api_token
          </code>
          y guárdalo aquí.
        </p>
        <div className="mt-3 flex flex-wrap items-end gap-2">
          <label className="block flex-1">
            <span className="mb-1 block text-xs text-slate-500">Token de la API local</span>
            <input
              type="password"
              value={token}
              onChange={(e) => {
                setToken(e.target.value);
                setTokenMsg("");
              }}
              placeholder="pega el token de backend/data/api_token"
              className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none focus:border-sky-400 focus:bg-white"
            />
          </label>
          <button
            type="button"
            onClick={() => {
              setApiToken(token.trim());
              setTokenMsg(token.trim() ? "Token guardado. Reconectando…" : "Token eliminado.");
              reconnect();
            }}
            className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
          >
            Guardar token
          </button>
          {tokenMsg ? <span className="text-xs text-slate-500">{tokenMsg}</span> : null}
        </div>
      </section>

      <section className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-dashed border-slate-300 bg-slate-50 p-4">
        <div>
          <p className="text-sm font-medium text-slate-800">Reiniciar datos de la demo</p>
          <p className="text-xs text-slate-500">Vuelve a las facturas sintéticas originales.</p>
        </div>
        <button
          onClick={reset}
          className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
        >
          <RotateCcw className="h-4 w-4" /> Reiniciar demo
        </button>
      </section>
    </div>
  );
}
