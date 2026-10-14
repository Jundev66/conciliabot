import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import type { AppSettings, AuditEntry, Invoice } from "../types";
import { auditLog as seedAudit, defaultSettings, invoices as seedInvoices } from "../data/sampleData";
import { api } from "./api";

const STORAGE_KEY = "conciliabot.state.v1";

export type ConnectionMode = "api" | "local" | "loading";

interface PersistedState {
  invoices: Invoice[];
  audit: AuditEntry[];
  settings: AppSettings;
}

interface StoreValue extends PersistedState {
  mode: ConnectionMode;
  approve: (id: string, actor: string) => void;
  reject: (id: string, actor: string) => void;
  correct: (id: string, actor: string, note: string) => void;
  reset: () => void;
  updateSettings: (patch: Partial<AppSettings>) => void;
  reconnect: () => void;
}

const StoreContext = createContext<StoreValue | null>(null);

function loadCache(): PersistedState {
  if (typeof localStorage !== "undefined") {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw) as PersistedState;
        if (parsed.invoices && parsed.audit && parsed.settings) return parsed;
      }
    } catch {
      // ignore corrupted state
    }
  }
  return { invoices: seedInvoices, audit: seedAudit, settings: defaultSettings };
}

function nextAuditId(audit: AuditEntry[]): string {
  return `A-${String(audit.length + 1).padStart(4, "0")}`;
}

function now(): string {
  return new Date().toISOString();
}

export function StoreProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<PersistedState>(() => loadCache());
  const [mode, setMode] = useState<ConnectionMode>("loading");

  const connect = useCallback(async () => {
    try {
      const [invoices, audit, settings] = await Promise.all([
        api.invoices(),
        api.audit(),
        api.settings()
      ]);
      setState({ invoices, audit, settings });
      setMode("api");
    } catch {
      setMode("local");
    }
  }, []);

  useEffect(() => {
    void connect();
  }, [connect]);

  const reconnect = useCallback(() => {
    setMode("loading");
    void connect();
  }, [connect]);

  useEffect(() => {
    if (mode !== "api") {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
      } catch {
        // storage unavailable
      }
    }
  }, [state, mode]);

  const appendAudit = useCallback(
    (audit: AuditEntry[], entry: Omit<AuditEntry, "id">): AuditEntry[] => [
      ...audit,
      { ...entry, id: nextAuditId(audit) }
    ],
    []
  );

  const refreshAudit = useCallback(async () => {
    try {
      const audit = await api.audit();
      setState((s) => ({ ...s, audit }));
    } catch {
      // keep local audit
    }
  }, []);

  const approve = useCallback(
    (id: string, actor: string) => {
      if (mode === "api") {
        api
          .approve(id, actor)
          .then((inv) => {
            setState((s) => ({
              ...s,
              invoices: s.invoices.map((i) => (i.id === id ? inv : i))
            }));
            void refreshAudit();
          })
          .catch(() => {});
        return;
      }
      setState((s) => {
        const at = now();
        const registered = s.settings.mode === "conectado";
        let audit = appendAudit(s.audit, {
          invoiceId: id,
          action: "approved",
          actor: "usuario",
          detail: `Aprobada por ${actor}.`,
          at
        });
        audit = appendAudit(audit, {
          invoiceId: id,
          action: "registered",
          actor: "sistema",
          detail: registered
            ? `Registrada en ${s.settings.erp} (modo conectado).`
            : "Registro preparado para importacion (modo seguro).",
          at
        });
        return {
          ...s,
          invoices: s.invoices.map((i) =>
            i.id === id
              ? {
                  ...i,
                  status: registered ? "registered" : "approved",
                  approvedBy: actor,
                  approvedAt: at
                }
              : i
          ),
          audit
        };
      });
    },
    [mode, appendAudit, refreshAudit]
  );

  const reject = useCallback(
    (id: string, actor: string) => {
      if (mode === "api") {
        api
          .reject(id, actor)
          .then((inv) => {
            setState((s) => ({
              ...s,
              invoices: s.invoices.map((i) => (i.id === id ? inv : i))
            }));
            void refreshAudit();
          })
          .catch(() => {});
        return;
      }
      setState((s) => ({
        ...s,
        invoices: s.invoices.map((i) => (i.id === id ? { ...i, status: "rejected" } : i)),
        audit: appendAudit(s.audit, {
          invoiceId: id,
          action: "rejected",
          actor: "usuario",
          detail: `Rechazada por ${actor}. No se registra nada.`,
          at: now()
        })
      }));
    },
    [mode, appendAudit, refreshAudit]
  );

  const correct = useCallback(
    (id: string, actor: string, note: string) => {
      if (mode === "api") {
        api
          .correct(id, actor, note)
          .then((inv) => {
            setState((s) => ({
              ...s,
              invoices: s.invoices.map((i) => (i.id === id ? inv : i))
            }));
            void refreshAudit();
          })
          .catch(() => {});
        return;
      }
      setState((s) => {
        const at = now();
        let audit = appendAudit(s.audit, {
          invoiceId: id,
          action: "corrected",
          actor: "usuario",
          detail: `Correccion de ${actor}: ${note}`,
          at
        });
        audit = appendAudit(audit, {
          invoiceId: id,
          action: "approved",
          actor: "usuario",
          detail: `Aprobada con correccion por ${actor}.`,
          at
        });
        return {
          ...s,
          invoices: s.invoices.map((i) =>
            i.id === id ? { ...i, status: "approved", approvedBy: actor, approvedAt: at, note } : i
          ),
          audit
        };
      });
    },
    [mode, appendAudit, refreshAudit]
  );

  const reset = useCallback(() => {
    if (mode === "api") {
      api
        .reset()
        .then(async () => {
          const [invoices, audit, settings] = await Promise.all([
            api.invoices(),
            api.audit(),
            api.settings()
          ]);
          setState({ invoices, audit, settings });
        })
        .catch(() => {});
      return;
    }
    setState({ invoices: seedInvoices, audit: seedAudit, settings: defaultSettings });
  }, [mode]);

  const updateSettings = useCallback(
    (patch: Partial<AppSettings>) => {
      setState((s) => {
        const settings = { ...s.settings, ...patch };
        if (mode === "api") {
          api.saveSettings(settings).catch(() => {});
        }
        return { ...s, settings };
      });
    },
    [mode]
  );

  const value = useMemo<StoreValue>(
    () => ({ ...state, mode, approve, reject, correct, reset, updateSettings, reconnect }),
    [state, mode, approve, reject, correct, reset, updateSettings, reconnect]
  );

  return <StoreContext.Provider value={value}>{children}</StoreContext.Provider>;
}

export function useStore(): StoreValue {
  const ctx = useContext(StoreContext);
  if (!ctx) throw new Error("useStore debe usarse dentro de StoreProvider");
  return ctx;
}
