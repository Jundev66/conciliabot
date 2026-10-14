from __future__ import annotations

from . import db, services
from .agent import pipeline
from .models import (
    Country,
    DocFormat,
    FiscalCheck,
    Invoice,
    InvoiceStatus,
    ModelTier,
    PipelineStep,
    Provider,
    StepStatus,
)

# Synthetic documents. Everything is fake: no real invoices, no real people.
DOC_CFDI_MATCH = """<?xml version="1.0" encoding="UTF-8"?>
<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/4" xmlns:tfd="http://www.sat.gob.mx/TimbreFiscalDigital"
    Folio="A-45231" Fecha="2026-09-28T09:12:00" SubTotal="12500.00" Moneda="MXN" Total="14500.00">
  <cfdi:Emisor Rfc="DNO920415H19" Nombre="Distribuidora del Norte S.A. de C.V."/>
  <cfdi:Impuestos TotalImpuestosTrasladados="2000.00"/>
  <cfdi:Complemento>
    <tfd:TimbreFiscalDigital UUID="6F8E2A1C-77B4-4E9D-9C21-2A0F1D3E5B90"/>
  </cfdi:Complemento>
</cfdi:Comprobante>
"""

DOC_CFDI_DISCREPANCY = """<?xml version="1.0" encoding="UTF-8"?>
<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/4" xmlns:tfd="http://www.sat.gob.mx/TimbreFiscalDigital"
    Folio="B-77810" Fecha="2026-09-30T14:03:00" SubTotal="14500.00" Moneda="MXN" Total="16820.00">
  <cfdi:Emisor Rfc="APM010203K55" Nombre="Aceros y Perfiles Monterrey S.A."/>
  <cfdi:Impuestos TotalImpuestosTrasladados="2320.00"/>
  <cfdi:Complemento>
    <tfd:TimbreFiscalDigital UUID="1C4B9D22-5A0E-4F1B-8D77-9E6C2B4A1F03"/>
  </cfdi:Complemento>
</cfdi:Comprobante>
"""

DOC_NFE_DUPLICATE = """<?xml version="1.0" encoding="UTF-8"?>
<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe">
  <NFe>
    <infNFe Id="NFe35200914200166000187550010000092311000092318">
      <ide><nNF>99231</nNF></ide>
      <emit><CNPJ>14200166000187</CNPJ><xNome>Metalurgica Paulista Ltda.</xNome></emit>
      <total><ICMSTot><vProd>8400.00</vProd><vICMS>1512.00</vICMS><vNF>9912.00</vNF></ICMSTot></total>
    </infNFe>
  </NFe>
  <protNFe><infProt><chNFe>35200914200166000187550010000092311000092318</chNFe></infProt></protNFe>
</nfeProc>
"""

DOC_DIAN_SCAN = """FACTURA ELECTRONICA DE VENTA
NIT: 9001234567
RazonSocial: Servicios Logisticos Andinos S.A.S.
Folio: FE-2026-88431
CUFE: 9F3A7C21-2E88-4D4A-B1F0-7C5D9E2A4B66
Fecha: 2026-10-01
Moneda: COP
Total: 4998000
"""

DOC_CFDI_APPROVED = """<?xml version="1.0" encoding="UTF-8"?>
<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/4" xmlns:tfd="http://www.sat.gob.mx/TimbreFiscalDigital"
    Folio="A-45180" Fecha="2026-09-25T11:00:00" SubTotal="3200.00" Moneda="MXN" Total="3712.00">
  <cfdi:Emisor Rfc="PCB050607L22" Nombre="Papeleria Corporativa del Bajio S.A."/>
  <cfdi:Impuestos TotalImpuestosTrasladados="512.00"/>
  <cfdi:Complemento>
    <tfd:TimbreFiscalDigital UUID="7A2D1E90-3C6B-4F2A-9E11-0B8C4D6A2E71"/>
  </cfdi:Complemento>
</cfdi:Comprobante>
"""


def _seed_duplicate_reference() -> None:
    """A previously registered document whose UUID will collide with a new one."""
    inv = Invoice(
        id="F-0980",
        folio="NF-0099231",
        uuid="35200914200166000187550010000092311000092318",
        format=DocFormat.NFe,
        country=Country.BR,
        provider=Provider(name="Metalurgica Paulista Ltda.", tax_id="14200166000187", country=Country.BR),
        issue_date="2026-09-29",
        due_date="2026-10-29",
        currency="BRL",
        subtotal=8400,
        tax=1512,
        total=9912,
        status=InvoiceStatus.registered,
        source="api",
        fiscal=FiscalCheck(
            verified=True,
            authority="SEFAZ",
            reference="chave verificada (SEFAZ)",
            message="Documento valido.",
        ),
        pipeline=[],
        created_at="2026-09-29T18:40:00",
        approved_by="Sistema",
        approved_at="2026-09-29T18:40:05",
    )
    db.store_invoice(inv)


def _seed_processing() -> None:
    inv = Invoice(
        id="F-1006",
        folio="F001-00231",
        uuid="PE-20123456789-01-F001-00231",
        format=DocFormat.SUNAT,
        country=Country.PE,
        provider=Provider(
            name="Insumos Industriales del Pacifico S.A.C.", tax_id="20123456789", country=Country.PE
        ),
        issue_date="2026-10-02",
        due_date="2026-11-01",
        currency="PEN",
        subtotal=6800,
        tax=1224,
        total=8024,
        status=InvoiceStatus.processing,
        source="email",
        fiscal=FiscalCheck(
            verified=False,
            authority="SUNAT",
            reference="En proceso",
            message="Verificando comprobante.",
        ),
        pipeline=[
            PipelineStep(key="ingest", label="Ingesta", status=StepStatus.done, detail="Documento recibido.", duration_ms=110),
            PipelineStep(key="preprocess", label="Pre-proceso", status=StepStatus.done, detail="PII redactada.", duration_ms=35),
            PipelineStep(key="classify", label="Clasificacion y ruteo", status=StepStatus.done, detail="Formato SUNAT.", model=ModelTier.small, tokens=160, duration_ms=240),
            PipelineStep(key="extract", label="Extraccion", status=StepStatus.done, detail="Campos extraidos.", model=ModelTier.small, tokens=610, duration_ms=690),
            PipelineStep(key="fiscal", label="Verificacion fiscal", status=StepStatus.running, detail="Consultando SUNAT..."),
            PipelineStep(key="match", label="Cotejo con ERP", status=StepStatus.pending, detail="Pendiente."),
            PipelineStep(key="reconcile", label="Conciliacion", status=StepStatus.pending, detail="Pendiente."),
        ],
        created_at="2026-10-02T07:35:00",
    )
    db.store_invoice(inv)


def seed_if_empty() -> None:
    db.init_db()
    if not db.is_empty():
        return

    _seed_duplicate_reference()

    pipeline.run_pipeline(DOC_CFDI_MATCH, "A-45231.xml", "email")
    pipeline.run_pipeline(DOC_CFDI_DISCREPANCY, "B-77810.xml", "email")
    pipeline.run_pipeline(DOC_NFE_DUPLICATE, "NF-0099231.xml", "api")
    pipeline.run_pipeline(DOC_DIAN_SCAN, "FE-2026-88431.pdf", "carpeta")
    approved, _ = pipeline.run_pipeline(DOC_CFDI_APPROVED, "A-45180.xml", "email")
    services.approve(approved.id, "María López")

    _seed_processing()
