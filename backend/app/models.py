from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class Base(BaseModel):
    """Base model that speaks camelCase over the wire (matches the PWA)."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="ignore",
    )


class InvoiceStatus(str, Enum):
    ingested = "ingested"
    processing = "processing"
    needs_review = "needs_review"
    matched = "matched"
    discrepancy = "discrepancy"
    duplicate = "duplicate"
    approved = "approved"
    rejected = "rejected"
    registered = "registered"


class Country(str, Enum):
    MX = "MX"
    BR = "BR"
    CO = "CO"
    CL = "CL"
    PE = "PE"
    AR = "AR"
    EC = "EC"


class DocFormat(str, Enum):
    CFDI = "CFDI"
    NFe = "NF-e"
    DIAN = "DIAN"
    DTE = "DTE"
    SUNAT = "SUNAT"
    PDF = "PDF"
    DELIVERY_NOTE = "NOTA_ENTREGA"


class Severity(str, Enum):
    info = "info"
    warning = "warning"
    critical = "critical"


class StepStatus(str, Enum):
    pending = "pending"
    running = "running"
    done = "done"
    warning = "warning"
    error = "error"


class ModelTier(str, Enum):
    small = "small"
    reasoning = "reasoning"
    none = "none"


class Provider(Base):
    name: str
    tax_id: str
    country: Country


class PurchaseOrder(Base):
    number: str
    amount: float
    received_amount: float
    currency: str


class DeliveryNote(Base):
    number: str
    amount: float
    received_amount: float
    currency: str


class Discrepancy(Base):
    field: str
    invoice_value: str
    expected_value: str
    severity: Severity
    message: str


class PipelineStep(Base):
    key: str
    label: str
    status: StepStatus
    detail: str
    model: ModelTier = ModelTier.none
    tokens: Optional[int] = None
    duration_ms: Optional[int] = None


class FiscalCheck(Base):
    verified: bool
    authority: str
    reference: str
    message: str


class Invoice(Base):
    id: str
    folio: str
    uuid: str
    format: DocFormat
    country: Country
    provider: Provider
    issue_date: str
    due_date: str
    currency: str
    subtotal: float
    tax: float
    total: float
    status: InvoiceStatus
    source: str
    purchase_order: Optional[PurchaseOrder] = None
    delivery_note: Optional[DeliveryNote] = None
    discrepancies: List[Discrepancy] = []
    duplicate_of: Optional[str] = None
    fiscal: FiscalCheck
    pipeline: List[PipelineStep] = []
    created_at: str
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    note: Optional[str] = None
    connection_id: str = ""


class AuditEntry(Base):
    id: str
    invoice_id: str
    action: str
    actor: str
    detail: str
    at: str
    connection_id: str = ""
    actor_kind: str = ""
    prev_hash: str = ""
    hash: str = ""


class AppSettings(Base):
    country: Country = Country.MX
    mode: str = "seguro"
    connection_authorized: bool = True
    auto_approve_threshold: float = 0
    require_fiscal_verification: bool = True
    erp: str = "ERP del cliente (demo)"
    pii_redaction: bool = True
    prompt_injection_guard: bool = True
    model_routing: bool = True


class ApprovalInput(Base):
    actor: str


class CorrectionInput(Base):
    actor: str
    note: str


class IngestInput(Base):
    text: str
    filename: str = "factura.xml"
    source: str = "api"
    use_browser: bool = False
    delivery_note: Optional[str] = None


class CorebizConfig(Base):
    base_url: str = ""
    api_key: str = ""
    tenant_id: str = ""
    token_header: str = "Authorization"
    token_prefix: str = "Bearer "
    records_path: str = "/v1/integrations/delivery-notes"


class ErpConfig(Base):
    provider: str = "demo"
    corebiz: CorebizConfig = CorebizConfig()
