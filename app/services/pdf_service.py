"""Generación de PDFs de nómina con ReportLab.

Las importaciones de ReportLab se hacen de forma diferida (lazy) dentro de cada
función para que la aplicación pueda importarse aunque la dependencia aún no
esté instalada; solo se requiere al llamar realmente a estos endpoints.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from app.models.contrato import Contrato
from app.models.empleado import Empleado
from app.models.empresa import Empresa
from app.models.nomina import Nomina, NominaDetalle

# Colores de marca
COLOR_INDIGO = "#4F46E5"
COLOR_VERDE_CLARO = "#D1FAE5"
COLOR_GRIS_HEADER = "#E5E7EB"
COLOR_TEXTO = "#111827"


def _cop(valor) -> str:
    """Formatea un valor a pesos colombianos: '$ 1.234.567'."""
    entero = int(Decimal(valor).quantize(Decimal("1")))
    return "$ " + f"{entero:,}".replace(",", ".")


def _fecha(d) -> str:
    return d.strftime("%d/%m/%Y") if d else "—"


# --------------------------------------------------------------------------- #
# 2.1 PDF Nómina completa (resumen de empresa)
# --------------------------------------------------------------------------- #
def generar_pdf_nomina(
    nomina: Nomina,
    detalles: list[NominaDetalle],
    empresa: Empresa,
    empleados: dict[uuid.UUID, Empleado],
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
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title=f"Nómina {empresa.nombre}",
    )

    styles = getSampleStyleSheet()
    h_marca = ParagraphStyle(
        "marca", parent=styles["Title"], fontSize=20, textColor=colors.HexColor(COLOR_INDIGO)
    )
    h_empresa = ParagraphStyle(
        "empresa", parent=styles["Normal"], fontSize=10, alignment=2
    )
    titulo = ParagraphStyle(
        "titulo", parent=styles["Heading1"], fontSize=14, spaceBefore=6, spaceAfter=2
    )
    sub = ParagraphStyle("sub", parent=styles["Normal"], fontSize=9, textColor=colors.grey)
    celda = ParagraphStyle("celda", parent=styles["Normal"], fontSize=6, leading=7)
    celda_h = ParagraphStyle(
        "celdaH", parent=styles["Normal"], fontSize=6, leading=7, textColor=colors.white
    )

    elementos = []

    # Header
    header_tbl = Table(
        [[Paragraph("NomiApp", h_marca),
          Paragraph(f"<b>{empresa.nombre}</b><br/>NIT: {empresa.nit}", h_empresa)]],
        colWidths=[doc.width * 0.5, doc.width * 0.5],
    )
    header_tbl.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    elementos.append(header_tbl)
    elementos.append(Spacer(1, 8))

    elementos.append(Paragraph("LIQUIDACIÓN DE NÓMINA", titulo))
    elementos.append(
        Paragraph(
            f"Período: {_fecha(nomina.periodo_inicio)} – {_fecha(nomina.periodo_fin)}"
            f" &nbsp;|&nbsp; Estado: {nomina.estado.value}",
            sub,
        )
    )
    elementos.append(Spacer(1, 8))

    encabezados = [
        "Empleado", "Cédula", "Cargo", "Salario Base", "Aux. Transp.",
        "H. Extra", "Devengado", "Salud", "Pensión", "Deducc.", "NETO",
    ]
    data = [[Paragraph(f"<b>{h}</b>", celda_h) for h in encabezados]]

    for det in detalles:
        emp = empleados.get(det.empleado_id)
        nombre = f"{emp.nombre} {emp.apellido}" if emp else "—"
        cedula = emp.cedula if emp else "—"
        cargo = (emp.cargo if emp and emp.cargo else "—")
        data.append([
            Paragraph(nombre, celda),
            Paragraph(cedula, celda),
            Paragraph(cargo, celda),
            Paragraph(_cop(det.salario_base), celda),
            Paragraph(_cop(det.auxilio_transporte), celda),
            Paragraph(_cop(det.valor_horas_extra), celda),
            Paragraph(_cop(det.total_devengado), celda),
            Paragraph(_cop(det.salud_empleado), celda),
            Paragraph(_cop(det.pension_empleado), celda),
            Paragraph(_cop(det.total_deducciones), celda),
            Paragraph(f"<b>{_cop(det.neto_pagado)}</b>", celda),
        ])

    # Fila de totales
    data.append([
        Paragraph("<b>TOTALES</b>", celda), Paragraph("", celda), Paragraph("", celda),
        Paragraph("", celda), Paragraph("", celda), Paragraph("", celda),
        Paragraph(f"<b>{_cop(nomina.total_devengado)}</b>", celda),
        Paragraph("", celda), Paragraph("", celda),
        Paragraph(f"<b>{_cop(nomina.total_deducciones)}</b>", celda),
        Paragraph(f"<b>{_cop(nomina.total_neto)}</b>", celda),
    ])

    w = doc.width
    col_widths = [
        w * 0.14, w * 0.08, w * 0.10, w * 0.095, w * 0.09, w * 0.07,
        w * 0.095, w * 0.075, w * 0.075, w * 0.085, w * 0.10,
    ]
    tabla = Table(data, colWidths=col_widths, repeatRows=1)
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(COLOR_INDIGO)),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor(COLOR_GRIS_HEADER)),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#9CA3AF")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#F9FAFB")]),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    elementos.append(tabla)
    elementos.append(Spacer(1, 16))

    pie = ParagraphStyle(
        "pie", parent=styles["Normal"], fontSize=8, textColor=colors.grey, alignment=1
    )
    generado = datetime.now().strftime("%d/%m/%Y %H:%M")
    elementos.append(
        Paragraph(f"Generado por NomiApp &nbsp;|&nbsp; {generado}", pie)
    )

    doc.build(elementos)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf


# --------------------------------------------------------------------------- #
# 2.2 PDF Desprendible individual (colilla de pago)
# --------------------------------------------------------------------------- #
def generar_pdf_desprendible(
    detalle: NominaDetalle,
    nomina: Nomina,
    empresa: Empresa,
    empleado: Empleado,
    contrato: Contrato | None,
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
        title=f"Desprendible {empleado.nombre} {empleado.apellido}",
    )

    styles = getSampleStyleSheet()
    blanco_izq = ParagraphStyle(
        "bizq", parent=styles["Title"], fontSize=18, textColor=colors.white
    )
    blanco_der = ParagraphStyle(
        "bder", parent=styles["Heading2"], fontSize=12, textColor=colors.white, alignment=2
    )
    seccion = ParagraphStyle(
        "seccion", parent=styles["Heading3"], fontSize=10,
        textColor=colors.HexColor(COLOR_INDIGO), spaceBefore=8, spaceAfter=2,
    )
    normal = ParagraphStyle("n", parent=styles["Normal"], fontSize=9, leading=12)
    concepto = ParagraphStyle("c", parent=styles["Normal"], fontSize=9)
    valor = ParagraphStyle("v", parent=styles["Normal"], fontSize=9, alignment=2)
    neto = ParagraphStyle(
        "neto", parent=styles["Title"], fontSize=18, alignment=1,
        textColor=colors.HexColor("#065F46"),
    )

    elementos = []
    w = doc.width

    # Header indigo
    header = Table(
        [[Paragraph("NomiApp", blanco_izq), Paragraph("DESPRENDIBLE DE PAGO", blanco_der)]],
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
    elementos.append(header)

    # Empresa
    elementos.append(Paragraph("Empresa", seccion))
    elementos.append(Paragraph(
        f"<b>{empresa.nombre}</b><br/>NIT: {empresa.nit}<br/>Ciudad: {empresa.ciudad or '—'}",
        normal,
    ))

    # Empleado
    tipo_contrato = contrato.tipo.value if contrato else "—"
    fecha_ini_contrato = _fecha(contrato.fecha_inicio) if contrato else "—"
    elementos.append(Paragraph("Empleado", seccion))
    elementos.append(Paragraph(
        f"<b>{empleado.nombre} {empleado.apellido}</b><br/>"
        f"Cédula: {empleado.cedula}<br/>"
        f"Cargo: {empleado.cargo or '—'}<br/>"
        f"Tipo de contrato: {tipo_contrato}<br/>"
        f"Inicio de contrato: {fecha_ini_contrato}",
        normal,
    ))

    # Período
    elementos.append(Paragraph("Período", seccion))
    elementos.append(Paragraph(
        f"{_fecha(nomina.periodo_inicio)} – {_fecha(nomina.periodo_fin)}"
        f"<br/>Días trabajados: {detalle.dias_trabajados}",
        normal,
    ))
    elementos.append(Spacer(1, 8))

    def _tabla_conceptos(titulo_tabla, filas, total_label, total_valor):
        data = [[Paragraph(f"<b>{titulo_tabla}</b>", concepto), Paragraph("", valor)]]
        for label, val in filas:
            data.append([Paragraph(label, concepto), Paragraph(_cop(val), valor)])
        data.append([
            Paragraph(f"<b>{total_label}</b>", concepto),
            Paragraph(f"<b>{_cop(total_valor)}</b>", valor),
        ])
        t = Table(data, colWidths=[w * 0.7, w * 0.3])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(COLOR_GRIS_HEADER)),
            ("LINEBELOW", (0, -1), (-1, -1), 1, colors.HexColor(COLOR_INDIGO)),
            ("LINEABOVE", (0, -1), (-1, -1), 0.5, colors.grey),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#E5E7EB")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        return t

    # Devengados (auxilio y horas extra solo si aplican)
    filas_dev = [("Salario básico", detalle.salario_base)]
    if Decimal(detalle.auxilio_transporte) > 0:
        filas_dev.append(("Auxilio de transporte", detalle.auxilio_transporte))
    if Decimal(detalle.valor_horas_extra) > 0:
        filas_dev.append(("Horas extra", detalle.valor_horas_extra))
    elementos.append(_tabla_conceptos(
        "DEVENGADOS", filas_dev, "TOTAL DEVENGADO", detalle.total_devengado
    ))
    elementos.append(Spacer(1, 8))

    # Deducciones
    filas_ded = [
        ("Salud (4%)", detalle.salud_empleado),
        ("Pensión (4%)", detalle.pension_empleado),
    ]
    elementos.append(_tabla_conceptos(
        "DEDUCCIONES", filas_ded, "TOTAL DEDUCCIONES", detalle.total_deducciones
    ))
    elementos.append(Spacer(1, 14))

    # Caja NETO A PAGAR
    neto_box = Table(
        [[Paragraph("NETO A PAGAR", ParagraphStyle(
            "nl", parent=styles["Normal"], fontSize=11, alignment=1,
            textColor=colors.HexColor("#065F46")))],
         [Paragraph(_cop(detalle.neto_pagado), neto)]],
        colWidths=[w],
    )
    neto_box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(COLOR_VERDE_CLARO)),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#10B981")),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    elementos.append(neto_box)
    elementos.append(Spacer(1, 30))

    # Firmas
    firma = ParagraphStyle("f", parent=styles["Normal"], fontSize=8, alignment=1)
    firmas = Table(
        [[Paragraph("_____________________________<br/>Firma empleado", firma),
          Paragraph("_____________________________<br/>Firma empleador", firma)]],
        colWidths=[w * 0.5, w * 0.5],
    )
    firmas.setStyle(TableStyle([("TOPPADDING", (0, 0), (-1, -1), 6)]))
    elementos.append(firmas)
    elementos.append(Spacer(1, 14))

    pie = ParagraphStyle(
        "pie", parent=styles["Normal"], fontSize=8, textColor=colors.grey, alignment=1
    )
    elementos.append(Paragraph(
        "Este documento es generado automáticamente por NomiApp", pie
    ))

    doc.build(elementos)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf
