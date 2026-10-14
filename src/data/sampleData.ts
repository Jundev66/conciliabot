import type {
  AppSettings,
  AuditEntry,
  Country,
  Discrepancy,
  DocFormat,
  Invoice,
  PipelineStep,
  Provider
} from "../types";

export const AUTHORITY: Record<Country, string> = {
  MX: "SAT",
  BR: "SEFAZ",
  CO: "DIAN",
  CL: "SII",
  PE: "SUNAT",
  AR: "ARCA",
  EC: "SRI"
};

export const FORMAT_BY_COUNTRY: Record<Country, DocFormat> = {
  MX: "CFDI",
  BR: "NF-e",
  CO: "DIAN",
  CL: "DTE",
  PE: "SUNAT",
  AR: "PDF",
  EC: "PDF"
};

function provider(name: string, taxId: string, country: Country): Provider {
  return { name, taxId, country };
}

function basePipeline(): PipelineStep[] {
  return [
    {
      key: "ingest",
      label: "Ingesta",
      status: "done",
      detail: "Documento recibido y job creado (estado durable).",
      model: "none",
      durationMs: 120
    },
    {
      key: "preprocess",
      label: "Pre-proceso",
      status: "done",
      detail: "PII redactada, documento marcado como entrada no confiable, hash calculado.",
      model: "none",
      durationMs: 40
    },
    {
      key: "classify",
      label: "Clasificacion y ruteo",
      status: "done",
      detail: "Formato detectado. Ruteo de modelo aplicado.",
      model: "small",
      tokens: 180,
      durationMs: 260
    },
    {
      key: "extract",
      label: "Extraccion",
      status: "done",
      detail: "Campos extraidos y validados contra esquema estricto.",
      model: "small",
      tokens: 640,
      durationMs: 720
    },
    {
      key: "fiscal",
      label: "Verificacion fiscal",
      status: "done",
      detail: "Sello verificado contra la autoridad.",
      model: "none",
      durationMs: 310
    },
    {
      key: "match",
      label: "Cotejo con ERP",
      status: "done",
      detail: "Consulta de solo lectura via MCP: OC, proveedor y recepcion.",
      model: "none",
      durationMs: 450
    },
    {
      key: "reconcile",
      label: "Conciliacion",
      status: "done",
      detail: "Comparacion factura vs OC.",
      model: "reasoning",
      tokens: 1120,
      durationMs: 1450
    }
  ];
}

function step(
  pipeline: PipelineStep[],
  key: string,
  patch: Partial<PipelineStep>
): PipelineStep[] {
  return pipeline.map((s) => (s.key === key ? { ...s, ...patch } : s));
}

let auditSeq = 0;
function audit(
  invoiceId: string,
  action: AuditEntry["action"],
  actor: AuditEntry["actor"],
  detail: string,
  at: string
): AuditEntry {
  auditSeq += 1;
  return { id: `A-${String(auditSeq).padStart(4, "0")}`, invoiceId, action, actor, detail, at };
}

export const invoices: Invoice[] = [
  (() => {
    let p = basePipeline();
    p = step(p, "reconcile", {
      status: "done",
      detail: "Todo coincide con la orden de compra P-1042."
    });
    return {
      id: "F-1001",
      folio: "A-45231",
      uuid: "6F8E2A1C-77B4-4E9D-9C21-2A0F1D3E5B90",
      format: "CFDI",
      country: "MX",
      provider: provider("Distribuidora del Norte S.A. de C.V.", "DNO-920415-H19", "MX"),
      issueDate: "2026-09-28",
      dueDate: "2026-10-28",
      currency: "MXN",
      subtotal: 12500,
      tax: 2000,
      total: 14500,
      status: "matched",
      source: "email",
      purchaseOrder: { number: "P-1042", amount: 14500, receivedAmount: 14500, currency: "MXN" },
      discrepancies: [],
      fiscal: {
        verified: true,
        authority: "SAT",
        reference: "UUID verificado (SAT)",
        message: "Sello válido. Documento íntegro."
      },
      pipeline: p,
      createdAt: "2026-09-28T09:12:00"
    } satisfies Invoice;
  })(),
  (() => {
    let p = basePipeline();
    p = step(p, "reconcile", {
      status: "warning",
      detail: "Diferencia de importe detectada vs OC P-1043."
    });
    const discrepancies: Discrepancy[] = [
      {
        field: "Importe total",
        invoiceValue: "$16,820.00",
        expectedValue: "$15,950.00",
        severity: "critical",
        message: "La factura cobra $870 más que la orden de compra."
      },
      {
        field: "Impuesto",
        invoiceValue: "$2,320.00",
        expectedValue: "$2,200.00",
        severity: "warning",
        message: "El impuesto excede el calculado sobre el subtotal de la OC."
      }
    ];
    return {
      id: "F-1002",
      folio: "B-77810",
      uuid: "1C4B9D22-5A0E-4F1B-8D77-9E6C2B4A1F03",
      format: "CFDI",
      country: "MX",
      provider: provider("Aceros y Perfiles Monterrey S.A.", "APM-010203-K55", "MX"),
      issueDate: "2026-09-30",
      dueDate: "2026-10-30",
      currency: "MXN",
      subtotal: 14500,
      tax: 2320,
      total: 16820,
      status: "discrepancy",
      source: "email",
      purchaseOrder: { number: "P-1043", amount: 15950, receivedAmount: 15950, currency: "MXN" },
      discrepancies,
      fiscal: {
        verified: true,
        authority: "SAT",
        reference: "UUID verificado (SAT)",
        message: "Sello válido. Documento íntegro."
      },
      pipeline: p,
      createdAt: "2026-09-30T14:03:00"
    } satisfies Invoice;
  })(),
  (() => {
    let p = basePipeline();
    p = step(p, "reconcile", {
      status: "warning",
      detail: "Posible duplicado por folio/UUID."
    });
    return {
      id: "F-1003",
      folio: "NF-0099231",
      uuid: "BR-35200914200166000187550010000092311000092318",
      format: "NF-e",
      country: "BR",
      provider: provider("Metalurgica Paulista Ltda.", "14.200.166/0001-87", "BR"),
      issueDate: "2026-09-29",
      dueDate: "2026-10-29",
      currency: "BRL",
      subtotal: 8400,
      tax: 1512,
      total: 9912,
      status: "duplicate",
      source: "api",
      purchaseOrder: { number: "P-1044", amount: 9912, receivedAmount: 9912, currency: "BRL" },
      discrepancies: [
        {
          field: "Registro",
          invoiceValue: "NF-0099231",
          expectedValue: "Ya registrada el 29/09",
          severity: "critical",
          message: "La misma factura ya fue registrada. Riesgo de pago duplicado."
        }
      ],
      duplicateOf: "F-0980",
      fiscal: {
        verified: true,
        authority: "SEFAZ",
        reference: "chave verificada (SEFAZ)",
        message: "Documento válido, pero ya registrado."
      },
      pipeline: p,
      createdAt: "2026-09-29T18:45:00"
    } satisfies Invoice;
  })(),
  (() => {
    let p = basePipeline();
    p = step(p, "extract", {
      status: "warning",
      detail: "Confianza media: el PDF no es texto nativo (escaneado)."
    });
    p = step(p, "reconcile", {
      status: "pending",
      detail: "En espera de revision humana.",
      model: "none"
    });
    return {
      id: "F-1004",
      folio: "FE-2026-88431",
      uuid: "CO-9F3A7C21-2E88-4D4A-B1F0-7C5D9E2A4B66",
      format: "DIAN",
      country: "CO",
      provider: provider("Servicios Logisticos Andinos S.A.S.", "NIT 900.123.456-7", "CO"),
      issueDate: "2026-10-01",
      dueDate: "2026-10-31",
      currency: "COP",
      subtotal: 4200000,
      tax: 798000,
      total: 4998000,
      status: "needs_review",
      source: "carpeta",
      purchaseOrder: { number: "P-1045", amount: 4998000, receivedAmount: 4800000, currency: "COP" },
      discrepancies: [
        {
          field: "Cantidad recibida",
          invoiceValue: "Factura por 100%",
          expectedValue: "Recepción parcial (96%)",
          severity: "warning",
          message: "La orden indica recepción parcial. Requiere confirmacion humana."
        }
      ],
      fiscal: {
        verified: true,
        authority: "DIAN",
        reference: "CUFE verificado (DIAN)",
        message: "Documento válido."
      },
      pipeline: p,
      createdAt: "2026-10-01T08:20:00"
    } satisfies Invoice;
  })(),
  (() => {
    let p = basePipeline();
    p = step(p, "reconcile", { status: "done", detail: "Conciliada y aprobada." });
    return {
      id: "F-1005",
      folio: "A-45180",
      uuid: "7A2D1E90-3C6B-4F2A-9E11-0B8C4D6A2E71",
      format: "CFDI",
      country: "MX",
      provider: provider("Papeleria Corporativa del Bajio S.A.", "PCB-050607-L22", "MX"),
      issueDate: "2026-09-25",
      dueDate: "2026-10-25",
      currency: "MXN",
      subtotal: 3200,
      tax: 512,
      total: 3712,
      status: "approved",
      source: "email",
      purchaseOrder: { number: "P-1041", amount: 3712, receivedAmount: 3712, currency: "MXN" },
      discrepancies: [],
      fiscal: {
        verified: true,
        authority: "SAT",
        reference: "UUID verificado (SAT)",
        message: "Sello válido. Documento íntegro."
      },
      pipeline: p,
      createdAt: "2026-09-25T11:00:00",
      approvedBy: "María López",
      approvedAt: "2026-09-25T16:40:00"
    } satisfies Invoice;
  })(),
  (() => {
    let p = basePipeline();
    p = step(p, "fiscal", {
      status: "running",
      detail: "Consultando SUNAT...",
      model: "none"
    });
    p = step(p, "match", { status: "pending", detail: "Pendiente.", model: "none" });
    p = step(p, "reconcile", { status: "pending", detail: "Pendiente.", model: "none" });
    return {
      id: "F-1006",
      folio: "F001-00231",
      uuid: "PE-20123456789-01-F001-00231",
      format: "SUNAT",
      country: "PE",
      provider: provider("Insumos Industriales del Pacifico S.A.C.", "RUC 20123456789", "PE"),
      issueDate: "2026-10-02",
      dueDate: "2026-11-01",
      currency: "PEN",
      subtotal: 6800,
      tax: 1224,
      total: 8024,
      status: "processing",
      source: "email",
      purchaseOrder: { number: "P-1046", amount: 8024, receivedAmount: 8024, currency: "PEN" },
      discrepancies: [],
      fiscal: {
        verified: false,
        authority: "SUNAT",
        reference: "En proceso",
        message: "Verificando comprobante."
      },
      pipeline: p,
      createdAt: "2026-10-02T07:35:00"
    } satisfies Invoice;
  })()
];

export const auditLog: AuditEntry[] = [
  audit("F-1001", "ingested", "agente", "Factura recibida desde correo (A-45231).", "2026-09-28T09:12:00"),
  audit("F-1001", "fiscal_verified", "agente", "UUID validado contra SAT.", "2026-09-28T09:12:04"),
  audit("F-1001", "matched", "agente", "Coincide con OC P-1042 por $14,500.00.", "2026-09-28T09:12:06"),
  audit("F-1002", "ingested", "agente", "Factura recibida desde correo (B-77810).", "2026-09-30T14:03:00"),
  audit("F-1002", "discrepancy_found", "agente", "Diferencia de $870.00 vs OC P-1043.", "2026-09-30T14:03:08"),
  audit("F-1003", "duplicate_found", "agente", "Mismo UUID ya registrado (F-0980).", "2026-09-29T18:45:05"),
  audit("F-1005", "approved", "usuario", "Aprobada por María López.", "2026-09-25T16:40:00"),
  audit("F-1005", "registered", "sistema", "Registro preparado para importacion (modo seguro).", "2026-09-25T16:40:02")
];

export const defaultSettings: AppSettings = {
  country: "MX",
  mode: "seguro",
  connectionAuthorized: true,
  autoApproveThreshold: 0,
  requireFiscalVerification: true,
  erp: "ERP del cliente (demo)",
  piiRedaction: true,
  promptInjectionGuard: true,
  modelRouting: true
};
