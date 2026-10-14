from __future__ import annotations

import io
from typing import Any, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def build_sample_delivery_note_pdf(number: Optional[str] = None) -> bytes:
    """Generate a clean, professional sample Delivery Note (Nota de Entrega / Remisión).
    Supports CoreBiz real demo note (NE-000004 / Panadería Santa Rosa / USD 119.71)
    and the standard test note (NE-5001 / MXN 14,500.00).
    """
    is_ne3 = bool(number and "000003" in number)
    is_ne4 = bool(number and "000004" in number)

    if is_ne3:
        folio_str = "NE-000003"
        currency_str = "USD"
        total_str = "$ 169.07 USD"
        subtotal_str = "$ 145.75 USD"
        tax_str = "$ 23.32 USD"
    elif is_ne4:
        folio_str = "NE-000004"
        currency_str = "USD"
        total_str = "$ 119.71 USD"
        subtotal_str = "$ 103.20 USD"
        tax_str = "$ 16.51 USD"
    else:
        folio_str = "NE-5001"
        currency_str = "MXN"
        total_str = "$ 14,500.00 MXN"
        subtotal_str = "$ 14,500.00 MXN"
        tax_str = "$ 0.00 MXN"

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=40,
        rightMargin=40,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0f172a"),
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#64748b"),
    )
    badge_style = ParagraphStyle(
        "BadgeText",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#0369a1"),
        alignment=2,  # Right align
    )
    table_header_style = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.white,
    )
    table_cell_style = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#1e293b"),
    )
    table_cell_bold = ParagraphStyle(
        "TableCellBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#0f172a"),
    )
    right_cell_style = ParagraphStyle(
        "RightCell",
        parent=table_cell_style,
        alignment=2,
    )
    right_cell_bold = ParagraphStyle(
        "RightCellBold",
        parent=table_cell_bold,
        alignment=2,
    )

    story = []

    # 1. Header: Vendor / Issuer & Document Badge
    if is_ne3:
        issuer_html = (
            "<b>SUPERMERCADO MI BARRIO / PROVEEDOR COREBIZ</b><br/>"
            "<font size=8 color='#475569'>"
            "Tax ID: J-30456789-3 · Sucursal Principal<br/>"
            "Calle 10, Edificio Centro Comercial Mi Barrio<br/>"
            "Tel: +1 (555) 789-0123 · entregas@mibarrio.local"
            "</font>"
        )
    elif is_ne4:
        issuer_html = (
            "<b>PANADERÍA SANTA ROSA / PROVEEDOR COREBIZ</b><br/>"
            "<font size=8 color='#475569'>"
            "Tax ID: J-30456789-4 · Almacén Principal<br/>"
            "Av. Los Próceres 102, Edificio Industrial CoreBiz<br/>"
            "Tel: +1 (555) 492-8810 · entregas@santarosa.local"
            "</font>"
        )
    else:
        issuer_html = (
            "<b>DISTRIBUIDORA DEL NORTE S.A. DE C.V.</b><br/>"
            "<font size=8 color='#475569'>"
            "RFC: DNO920415H19 · Régimen General de Ley Personas Morales<br/>"
            "Av. Parque Industrial 4500, Edificio C-2, Monterrey, N.L., CP 64000<br/>"
            "Tel: +52 (81) 8000-1234 · contacto@distribuidoradelnorte.mx"
            "</font>"
        )

    header_data = [
        [
            Paragraph(issuer_html, subtitle_style),
            Paragraph(
                "<font size=14 color='#0284c7'><b>NOTA DE ENTREGA</b></font><br/>"
                f"<font size=12 color='#0f172a'><b>Folio: {folio_str}</b></font><br/>"
                "<font size=8 color='#059669'><b>ESTADO: EMITIDA / POR CONFIRMAR</b></font><br/>"
                "<font size=8 color='#64748b'>Cotejo CoreBiz: /v1/integrations/delivery-notes</font>",
                badge_style,
            ),
        ]
    ]
    header_table = Table(header_data, colWidths=[330, 200])
    header_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(header_table)
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2e8f0")))
    story.append(Spacer(1, 10))

    # 2. Metadata: Customer / Receiver & Shipment Details
    if is_ne3:
        cust_html = (
            "<b>Razón Social:</b> Supermercado Mi Barrio<br/>"
            "<b>Tax ID:</b> J-30456789-3<br/>"
            "<b>Dirección:</b> Calle 10, Edificio Centro Comercial Mi Barrio<br/>"
            "<b>Almacén Destino:</b> Almacén Central CoreBiz"
        )
        ship_html = (
            "<b>Fecha de Emisión:</b> 2026-10-06<br/>"
            "<b>Fecha de Entrega:</b> 2026-10-14 10:30:00<br/>"
            "<b>Orden de Compra (OC):</b> P-1043<br/>"
            "<b>Moneda:</b> USD (Dólares Americanos)<br/>"
            "<b>Método de Traslado:</b> Transporte Terrestre"
        )
    elif is_ne4:
        cust_html = (
            "<b>Razón Social:</b> Panadería Santa Rosa<br/>"
            "<b>Tax ID:</b> J-30456789-4<br/>"
            "<b>Dirección:</b> Av. Bolívar, Calle 4, Local 12<br/>"
            "<b>Almacén Destino:</b> Almacén Central CoreBiz"
        )
        ship_html = (
            "<b>Fecha de Emisión:</b> 2026-10-07<br/>"
            "<b>Fecha de Entrega:</b> 2026-10-14 09:00:00<br/>"
            "<b>Orden de Compra (OC):</b> P-1042<br/>"
            "<b>Moneda:</b> USD (Dólares Americanos)<br/>"
            "<b>Método de Traslado:</b> Transporte Terrestre"
        )
    else:
        cust_html = (
            "<b>Razón Social:</b> Comercio de Ejemplo S.A.<br/>"
            "<b>RFC / Tax ID:</b> CEX200101ABC<br/>"
            "<b>Dirección:</b> Calzada del Valle 120, San Pedro Garza García, N.L.<br/>"
            "<b>Almacén Destino:</b> Almacén Central - Rampa 3"
        )
        ship_html = (
            "<b>Fecha de Emisión:</b> 2026-10-01<br/>"
            "<b>Fecha de Entrega:</b> 2026-10-02 15:30:00<br/>"
            "<b>Orden de Compra (OC):</b> P-1042<br/>"
            "<b>Moneda:</b> MXN (Pesos Mexicanos)<br/>"
            "<b>Método de Traslado:</b> Transporte Terrestre Privado"
        )

    meta_data = [
        [
            Paragraph("<b>CLIENTE / DESTINATARIO</b>", table_cell_bold),
            Paragraph("<b>DETALLES DE ENTREGA</b>", table_cell_bold),
        ],
        [
            Paragraph(cust_html, table_cell_style),
            Paragraph(ship_html, table_cell_style),
        ],
    ]
    meta_table = Table(meta_data, colWidths=[265, 265])
    meta_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f8fafc")),
                ("PADDING", (0, 0), (-1, -1), 6),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#f1f5f9")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(meta_table)
    story.append(Spacer(1, 14))

    # 3. Items Table
    items_header = [
        Paragraph("Línea", table_header_style),
        Paragraph("Código", table_header_style),
        Paragraph("Descripción de la Mercancía", table_header_style),
        Paragraph("Cant.", table_header_style),
        Paragraph("Unidad", table_header_style),
        Paragraph("P. Unitario", table_header_style),
        Paragraph("Total", table_header_style),
    ]

    if is_ne3:
        items_rows = [
            [
                Paragraph("1", table_cell_style),
                Paragraph("PRD-003", table_cell_style),
                Paragraph("Arroz Blanco Especial 1 kg", table_cell_style),
                Paragraph("75", right_cell_style),
                Paragraph("und", table_cell_style),
                Paragraph("$ 1.15", right_cell_style),
                Paragraph("$ 86.25", right_cell_style),
            ],
            [
                Paragraph("2", table_cell_style),
                Paragraph("PRD-004", table_cell_style),
                Paragraph("Aceite Vegetal 1 L", table_cell_style),
                Paragraph("25", right_cell_style),
                Paragraph("und", table_cell_style),
                Paragraph("$ 2.38", right_cell_style),
                Paragraph("$ 59.50", right_cell_style),
            ],
        ]
    elif is_ne4:
        items_rows = [
            [
                Paragraph("1", table_cell_style),
                Paragraph("PRD-001", table_cell_style),
                Paragraph("Harina de trigo 1 kg", table_cell_style),
                Paragraph("40", right_cell_style),
                Paragraph("und", table_cell_style),
                Paragraph("$ 1.20", right_cell_style),
                Paragraph("$ 48.00", right_cell_style),
            ],
            [
                Paragraph("2", table_cell_style),
                Paragraph("PRD-002", table_cell_style),
                Paragraph("Leche en polvo 900 g", table_cell_style),
                Paragraph("8", right_cell_style),
                Paragraph("und", table_cell_style),
                Paragraph("$ 6.90", right_cell_style),
                Paragraph("$ 55.20", right_cell_style),
            ],
        ]
    else:
        items_rows = [
            [
                Paragraph("1", table_cell_style),
                Paragraph("MAT-001", table_cell_style),
                Paragraph("Cajas de cartón corrugado reforzado 40x40", table_cell_style),
                Paragraph("100", right_cell_style),
                Paragraph("pza", table_cell_style),
                Paragraph("$ 70.00", right_cell_style),
                Paragraph("$ 7,000.00", right_cell_style),
            ],
            [
                Paragraph("2", table_cell_style),
                Paragraph("MAT-002", table_cell_style),
                Paragraph("Cinta de embalaje industrial 48mm x 100m", table_cell_style),
                Paragraph("150", right_cell_style),
                Paragraph("pza", table_cell_style),
                Paragraph("$ 50.00", right_cell_style),
                Paragraph("$ 7,500.00", right_cell_style),
            ],
        ]

    items_table_data = [items_header] + items_rows
    items_table = Table(items_table_data, colWidths=[32, 60, 208, 45, 45, 65, 75])
    items_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0284c7")),
                ("ALIGN", (3, 1), (3, -1), "RIGHT"),
                ("ALIGN", (5, 1), (6, -1), "RIGHT"),
                ("PADDING", (0, 0), (-1, -1), 6),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    story.append(items_table)
    story.append(Spacer(1, 10))

    # 4. Summary / Totals block
    totals_data = [
        [
            Paragraph(
                "<b>Observaciones:</b><br/>"
                "<font size=7 color='#64748b'>"
                "Documento mercantil no fiscal de traslado y entrega de mercancía.<br/>"
                "Mercancía recibida a total satisfacción por el área de recepción.<br/>"
                "Para conciliar en ConciliaBot: ingresar o cargar este documento PDF.<br/>"
                "Al aprobar, el sistema registra la confirmación directamente en CoreBiz."
                "</font>",
                table_cell_style,
            ),
            Paragraph(
                f"<b>Subtotal:</b> {subtotal_str}<br/>"
                f"<b>IVA (Impuesto):</b> {tax_str}<br/>"
                f"<font size=10 color='#0284c7'><b>TOTAL: {total_str}</b></font><br/>"
                f"<font size=8 color='#059669'><b>Monto Documento: {total_str}</b></font>",
                right_cell_style,
            ),
        ]
    ]
    totals_table = Table(totals_data, colWidths=[330, 200])
    totals_table.setStyle(
        TableStyle(
            [
                ("PADDING", (0, 0), (-1, -1), 6),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(totals_table)
    story.append(Spacer(1, 16))

    # 5. Delivery Confirmation & Signatures
    sig_data = [
        [
            Paragraph("<b>ENTREGADO POR:</b>", table_cell_bold),
            Paragraph("<b>RECIBIDO A CONFORMIDAD:</b>", table_cell_bold),
        ],
        [
            Paragraph(
                "Transportista: Logística Express del Norte S.A.<br/>"
                "Operador: Carlos Ruiz Méndez<br/>"
                "Placas: NL-9842-B<br/>"
                "<br/>"
                "Firma: ___________________________",
                table_cell_style,
            ),
            Paragraph(
                "Recepción: Almacén Central CoreBiz<br/>"
                "Recibido por: <b>Juan Pérez</b> (Jefe de Almacén)<br/>"
                "Fecha y Hora: 2026-10-02 15:30:00<br/>"
                "<br/>"
                "Firma / Sello: ___________________________",
                table_cell_style,
            ),
        ],
    ]
    sig_table = Table(sig_data, colWidths=[265, 265])
    sig_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                ("PADDING", (0, 0), (-1, -1), 6),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(sig_table)
    story.append(Spacer(1, 12))

    # 6. Footer disclaimer
    footer_text = Paragraph(
        "<font size=7 color='#94a3b8'>"
        "ConciliaBot CoreBiz Bridge · Documento generado para prueba de validación y conciliación automatizada. "
        "Al confirmar esta nota de entrega se emitirá el registro durable en la API de CoreBiz (/v1/integrations/delivery-notes)."
        "</font>",
        subtitle_style,
    )
    story.append(footer_text)

    doc.build(story)
    return buf.getvalue()


def build_invoice_voucher_pdf(invoice: Any) -> bytes:
    """Generate a printable PDF voucher of an ingested/reconciled invoice or delivery note."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=40,
        rightMargin=40,
        topMargin=36,
        bottomMargin=36,
    )
    styles = getSampleStyleSheet()

    table_cell = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#1e293b"),
    )
    table_cell_bold = ParagraphStyle(
        "TableCellBold",
        parent=table_cell,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor("#0f172a"),
    )

    story = []

    # Title
    doc_type = "NOTA DE ENTREGA" if getattr(invoice, "delivery_note", None) or invoice.folio.startswith(("NE-", "DN-")) else "COMPROBANTE DE FACTURA"
    story.append(
        Paragraph(
            f"<b>{doc_type} · CONCILIACIÓN CON COREBIZ</b>",
            ParagraphStyle("H1", parent=styles["Heading1"], fontSize=16, leading=20, textColor=colors.HexColor("#0284c7")),
        )
    )
    story.append(Spacer(1, 6))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0284c7")))
    story.append(Spacer(1, 10))

    # Summary table
    status_str = str(invoice.status.value if hasattr(invoice.status, "value") else invoice.status).upper()
    info_data = [
        [
            Paragraph("<b>Identificador ConciliaBot:</b>", table_cell_bold),
            Paragraph(str(invoice.id), table_cell),
            Paragraph("<b>Estado:</b>", table_cell_bold),
            Paragraph(f"<b>{status_str}</b>", table_cell_bold),
        ],
        [
            Paragraph("<b>Folio / Número:</b>", table_cell_bold),
            Paragraph(str(invoice.folio), table_cell),
            Paragraph("<b>Formato:</b>", table_cell_bold),
            Paragraph(str(getattr(invoice.format, "value", invoice.format)), table_cell),
        ],
        [
            Paragraph("<b>Proveedor / Emisor:</b>", table_cell_bold),
            Paragraph(str(invoice.provider.name), table_cell),
            Paragraph("<b>RFC / Tax ID:</b>", table_cell_bold),
            Paragraph(str(invoice.provider.tax_id), table_cell),
        ],
        [
            Paragraph("<b>Fecha Emisión:</b>", table_cell_bold),
            Paragraph(str(invoice.issue_date or "—"), table_cell),
            Paragraph("<b>Fecha Vencimiento:</b>", table_cell_bold),
            Paragraph(str(invoice.due_date or "—"), table_cell),
        ],
        [
            Paragraph("<b>Total Documento:</b>", table_cell_bold),
            Paragraph(f"<b>{invoice.currency} {invoice.total:,.2f}</b>", table_cell_bold),
            Paragraph("<b>Subtotal / IVA:</b>", table_cell_bold),
            Paragraph(f"{invoice.currency} {invoice.subtotal:,.2f} / {invoice.tax:,.2f}", table_cell),
        ],
    ]

    dn = getattr(invoice, "delivery_note", None)
    if dn:
        info_data.append(
            [
                Paragraph("<b>Nota de Entrega (CoreBiz):</b>", table_cell_bold),
                Paragraph(f"<b>{dn.number}</b> ({dn.currency} {dn.amount:,.2f})", table_cell_bold),
                Paragraph("<b>Recepción Almacén:</b>", table_cell_bold),
                Paragraph(f"{dn.currency} {dn.received_amount:,.2f}", table_cell),
            ]
        )

    po = getattr(invoice, "purchase_order", None)
    if po:
        info_data.append(
            [
                Paragraph("<b>Orden de Compra:</b>", table_cell_bold),
                Paragraph(f"<b>{po.number}</b> ({po.currency} {po.amount:,.2f})", table_cell),
                Paragraph("<b>Recepción OC:</b>", table_cell_bold),
                Paragraph(f"{po.currency} {po.received_amount:,.2f}", table_cell),
            ]
        )

    if getattr(invoice, "approved_by", None):
        info_data.append(
            [
                Paragraph("<b>Confirmado por:</b>", table_cell_bold),
                Paragraph(str(invoice.approved_by), table_cell),
                Paragraph("<b>Fecha Confirmación:</b>", table_cell_bold),
                Paragraph(str(invoice.approved_at or "—"), table_cell),
            ]
        )

    info_table = Table(info_data, colWidths=[130, 140, 120, 140])
    info_table.setStyle(
        TableStyle(
            [
                ("PADDING", (0, 0), (-1, -1), 5),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#f1f5f9")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    story.append(info_table)
    story.append(Spacer(1, 14))

    # Discrepancies if any
    discrepancies = getattr(invoice, "discrepancies", [])
    if discrepancies:
        story.append(Paragraph("<b>Discrepancias Detectadas:</b>", table_cell_bold))
        story.append(Spacer(1, 4))
        disc_rows = [
            [
                Paragraph("Campo", table_cell_bold),
                Paragraph("Valor Doc.", table_cell_bold),
                Paragraph("Esperado", table_cell_bold),
                Paragraph("Severidad", table_cell_bold),
                Paragraph("Mensaje", table_cell_bold),
            ]
        ]
        for d in discrepancies:
            disc_rows.append(
                [
                    Paragraph(d.field, table_cell),
                    Paragraph(d.invoice_value, table_cell),
                    Paragraph(d.expected_value, table_cell),
                    Paragraph(str(d.severity.value if hasattr(d.severity, "value") else d.severity).upper(), table_cell),
                    Paragraph(d.message, table_cell),
                ]
            )
        disc_table = Table(disc_rows, colWidths=[80, 80, 80, 60, 230])
        disc_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#fee2e2")),
                    ("PADDING", (0, 0), (-1, -1), 4),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#fca5a5")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#fecaca")),
                ]
            )
        )
        story.append(disc_table)
        story.append(Spacer(1, 10))

    doc.build(story)
    return buf.getvalue()
