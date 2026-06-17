"""Payroll PDF generation with ReportLab.

ReportLab imports are deferred (lazy) inside each function so the application
can be imported even if the dependency is not yet installed; it is only
required when these endpoints are actually called. Visible labels in the
documents are kept in Spanish (end-user facing).
"""

import uuid
from datetime import datetime
from decimal import Decimal

from app.models.contract import Contract
from app.models.employee import Employee
from app.models.company import Company
from app.models.payroll import Payroll, PayrollDetail

# Brand colors
COLOR_INDIGO = "#4F46E5"
COLOR_LIGHT_GREEN = "#D1FAE5"
COLOR_HEADER_GRAY = "#E5E7EB"
COLOR_TEXT = "#111827"

CONTRACT_TYPE_LABELS = {
    "fixed_term": "Término Fijo",
    "indefinite": "Indefinido",
    "work_contract": "Obra Labor",
}

PAYROLL_STATUS_LABELS = {
    "draft": "Borrador",
    "closed": "Cerrada",
}


def _cop(value) -> str:
    """Formats a value as Colombian pesos: '$ 1.234.567'."""
    integer = int(Decimal(value).quantize(Decimal("1")))
    return "$ " + f"{integer:,}".replace(",", ".")


def _format_date(d) -> str:
    return d.strftime("%d/%m/%Y") if d else "—"


# --------------------------------------------------------------------------- #
# 2.1 Full payroll PDF (company summary)
# --------------------------------------------------------------------------- #
def generate_payroll_pdf(
    payroll: Payroll,
    details: list[PayrollDetail],
    company: Company,
    employees: dict[uuid.UUID, Employee],
    incidents_by_employee: dict | None = None,
) -> bytes:
    from io import BytesIO

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title=f"Nómina {company.name}",
    )

    styles = getSampleStyleSheet()
    h_brand = ParagraphStyle(
        "brand", parent=styles["Title"], fontSize=20, textColor=colors.HexColor(COLOR_INDIGO)
    )
    h_company = ParagraphStyle(
        "company", parent=styles["Normal"], fontSize=10, alignment=2
    )
    title_style = ParagraphStyle(
        "title", parent=styles["Heading1"], fontSize=14, spaceBefore=6, spaceAfter=2
    )
    sub = ParagraphStyle("sub", parent=styles["Normal"], fontSize=9, textColor=colors.grey)
    cell = ParagraphStyle("cell", parent=styles["Normal"], fontSize=8, leading=9)
    cell_h = ParagraphStyle(
        "cellH", parent=styles["Normal"], fontSize=8, leading=9, textColor=colors.white
    )

    elements = []

    # Header
    header_tbl = Table(
        [[Paragraph("NomiApp", h_brand),
          Paragraph(f"<b>{company.name}</b><br/>NIT: {company.nit}", h_company)]],
        colWidths=[doc.width * 0.5, doc.width * 0.5],
    )
    header_tbl.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    elements.append(header_tbl)
    elements.append(Spacer(1, 8))

    elements.append(Paragraph("LIQUIDACIÓN DE NÓMINA", title_style))
    elements.append(
        Paragraph(
            f"Período: {_format_date(payroll.period_start)} – {_format_date(payroll.period_end)}"
            f" &nbsp;|&nbsp; Estado: {PAYROLL_STATUS_LABELS.get(payroll.status.value, payroll.status.value)}",
            sub,
        )
    )
    elements.append(Spacer(1, 8))

    headers = [
        "Empleado", "Cédula", "Cargo", "Salario Base", "Aux. Transp.",
        "H. Extra", "Bonif./Incap.", "Devengado", "Salud", "Pensión",
        "Otros Desc.", "Total Deducc.", "NETO",
    ]
    data = [[Paragraph(f"<b>{h}</b>", cell_h) for h in headers]]

    for det in details:
        emp = employees.get(det.employee_id)
        name = f"{emp.first_name} {emp.last_name}" if emp else "—"
        id_number = emp.id_number if emp else "—"
        position = (emp.position if emp and emp.position else "—")
        data.append([
            Paragraph(name, cell),
            Paragraph(id_number, cell),
            Paragraph(position, cell),
            Paragraph(_cop(det.base_salary), cell),
            Paragraph(_cop(det.transport_allowance), cell),
            Paragraph(_cop(det.overtime_value) if Decimal(det.overtime_value) > 0 else "—", cell),
            Paragraph(_cop(det.total_bonuses) if Decimal(det.total_bonuses) > 0 else "—", cell),
            Paragraph(_cop(det.total_earned), cell),
            Paragraph(_cop(det.health_deduction), cell),
            Paragraph(_cop(det.pension_deduction), cell),
            Paragraph(_cop(det.total_additional_deductions) if Decimal(det.total_additional_deductions) > 0 else "—", cell),
            Paragraph(_cop(det.total_deductions), cell),
            Paragraph(f"<b>{_cop(det.net_pay)}</b>", cell),
        ])

    # Totals row
    data.append([
        Paragraph("<b>TOTALES</b>", cell), "", "", "", "", "", "",
        Paragraph(f"<b>{_cop(payroll.total_earned)}</b>", cell),
        "", "", "",
        Paragraph(f"<b>{_cop(payroll.total_deductions)}</b>", cell),
        Paragraph(f"<b>{_cop(payroll.total_net)}</b>", cell),
    ])

    w = doc.width
    col_widths = [
        w * 0.12,  # Empleado
        w * 0.08,  # Cédula
        w * 0.09,  # Cargo
        w * 0.08,  # Salario Base
        w * 0.07,  # Aux. Transp.
        w * 0.06,  # H. Extra
        w * 0.07,  # Bonif./Incap.
        w * 0.08,  # Devengado
        w * 0.06,  # Salud
        w * 0.06,  # Pensión
        w * 0.07,  # Otros Desc.
        w * 0.08,  # Total Deducc.
        w * 0.08,  # NETO
    ]
    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(COLOR_INDIGO)),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor(COLOR_HEADER_GRAY)),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#9CA3AF")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#F9FAFB")]),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 16))

    footer_style = ParagraphStyle(
        "footer", parent=styles["Normal"], fontSize=8, textColor=colors.grey, alignment=1
    )
    generated = datetime.now().strftime("%d/%m/%Y %H:%M")
    elements.append(
        Paragraph(f"Generado por NomiApp &nbsp;|&nbsp; {generated}", footer_style)
    )

    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf


# --------------------------------------------------------------------------- #
# 2.2 Individual pay stub PDF
# --------------------------------------------------------------------------- #
def generate_pay_stub_pdf(
    detail: PayrollDetail,
    payroll: Payroll,
    company: Company,
    employee: Employee,
    contract: Contract | None,
) -> bytes:
    from io import BytesIO

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=f"Desprendible {employee.first_name} {employee.last_name}",
    )

    styles = getSampleStyleSheet()
    white_left = ParagraphStyle(
        "wleft", parent=styles["Title"], fontSize=18, textColor=colors.white
    )
    white_right = ParagraphStyle(
        "wright", parent=styles["Heading2"], fontSize=12, textColor=colors.white, alignment=2
    )
    section = ParagraphStyle(
        "section", parent=styles["Heading3"], fontSize=10,
        textColor=colors.HexColor(COLOR_INDIGO), spaceBefore=8, spaceAfter=2,
    )
    normal = ParagraphStyle("n", parent=styles["Normal"], fontSize=9, leading=12)
    concept = ParagraphStyle("c", parent=styles["Normal"], fontSize=9)
    value_style = ParagraphStyle("v", parent=styles["Normal"], fontSize=9, alignment=2)
    net_style = ParagraphStyle(
        "net", parent=styles["Title"], fontSize=18, alignment=1,
        textColor=colors.HexColor("#065F46"),
    )

    elements = []
    w = doc.width

    # Indigo header
    header = Table(
        [[Paragraph("NomiApp", white_left), Paragraph("DESPRENDIBLE DE PAGO", white_right)]],
        colWidths=[w * 0.5, w * 0.5],
    )
    header.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(COLOR_INDIGO)),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
    ]))
    elements.append(header)

    # Company
    elements.append(Paragraph("Empresa", section))
    elements.append(Paragraph(
        f"<b>{company.name}</b><br/>NIT: {company.nit}<br/>Ciudad: {company.city or '—'}",
        normal,
    ))

    # Employee
    contract_type = (
        CONTRACT_TYPE_LABELS.get(contract.type.value, contract.type.value)
        if contract
        else "—"
    )
    contract_start = _format_date(contract.start_date) if contract else "—"
    period_days = (payroll.period_end - payroll.period_start).days + 1
    elements.append(Paragraph("Empleado", section))
    elements.append(Paragraph(
        f"<b>{employee.first_name} {employee.last_name}</b><br/>"
        f"Cédula: {employee.id_number}<br/>"
        f"Cargo: {employee.position or '—'}<br/>"
        f"Tipo de contrato: {contract_type}<br/>"
        f"Inicio de contrato: {contract_start}",
        normal,
    ))

    # Period
    elements.append(Paragraph("Período", section))
    elements.append(Paragraph(
        f"{_format_date(payroll.period_start)} – {_format_date(payroll.period_end)}"
        f"<br/>Días del período: {period_days}",
        normal,
    ))
    elements.append(Spacer(1, 8))

    def _concept_table(table_title, rows, total_label, total_value):
        data = [[Paragraph(f"<b>{table_title}</b>", concept), Paragraph("", value_style)]]
        for label, val in rows:
            data.append([Paragraph(label, concept), Paragraph(_cop(val), value_style)])
        data.append([
            Paragraph(f"<b>{total_label}</b>", concept),
            Paragraph(f"<b>{_cop(total_value)}</b>", value_style),
        ])
        t = Table(data, colWidths=[w * 0.7, w * 0.3])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(COLOR_HEADER_GRAY)),
            ("LINEBELOW", (0, -1), (-1, -1), 1, colors.HexColor(COLOR_INDIGO)),
            ("LINEABOVE", (0, -1), (-1, -1), 0.5, colors.grey),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#E5E7EB")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        return t

    # Earnings (allowance and overtime only if they apply)
    earning_rows = [("Salario básico", detail.base_salary)]
    if Decimal(detail.transport_allowance) > 0:
        earning_rows.append(("Auxilio de transporte", detail.transport_allowance))
    if Decimal(detail.overtime_value) > 0:
        earning_rows.append(("Horas extra", detail.overtime_value))
    if Decimal(detail.total_bonuses) > 0:
        earning_rows.append(("Bonificaciones / Incapacidades", detail.total_bonuses))
    elements.append(_concept_table(
        "DEVENGADOS", earning_rows, "TOTAL DEVENGADO", detail.total_earned
    ))
    elements.append(Spacer(1, 8))

    # Deductions
    deduction_rows = [
        ("Salud (4%)", detail.health_deduction),
        ("Pensión (4%)", detail.pension_deduction),
    ]
    if Decimal(detail.total_additional_deductions) > 0:
        deduction_rows.append(("Otros descuentos", detail.total_additional_deductions))
    elements.append(_concept_table(
        "DEDUCCIONES", deduction_rows, "TOTAL DEDUCCIONES", detail.total_deductions
    ))
    elements.append(Spacer(1, 14))

    # NET TO PAY box
    net_box = Table(
        [[Paragraph("NETO A PAGAR", ParagraphStyle(
            "nl", parent=styles["Normal"], fontSize=11, alignment=1,
            textColor=colors.HexColor("#065F46")))],
         [Paragraph(_cop(detail.net_pay), net_style)]],
        colWidths=[w],
    )
    net_box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(COLOR_LIGHT_GREEN)),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#10B981")),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(net_box)
    elements.append(Spacer(1, 30))

    # Signatures
    signature = ParagraphStyle("f", parent=styles["Normal"], fontSize=8, alignment=1)
    signatures = Table(
        [[Paragraph("_____________________________<br/>Firma empleado", signature),
          Paragraph("_____________________________<br/>Firma empleador", signature)]],
        colWidths=[w * 0.5, w * 0.5],
    )
    signatures.setStyle(TableStyle([("TOPPADDING", (0, 0), (-1, -1), 6)]))
    elements.append(signatures)
    elements.append(Spacer(1, 14))

    footer_style = ParagraphStyle(
        "footer", parent=styles["Normal"], fontSize=8, textColor=colors.grey, alignment=1
    )
    elements.append(Paragraph(
        "Este documento es generado automáticamente por NomiApp", footer_style
    ))

    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf
