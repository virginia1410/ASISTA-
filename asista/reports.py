"""Reportes PDF (ReportLab) avanzados y estadísticas para Asista."""
from datetime import datetime, date
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import Image as ReportImage, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from config import INSTITUCION, MESES
from db import fmt_hora
from tema import RUTA_ASSETS

AZUL, VERDE = colors.HexColor("#0F2042"), colors.HexColor("#059669")
NARANJA, ROJO = colors.HexColor("#E8890C"), colors.HexColor("#FF3B00")
GRIS, BORDE = colors.HexColor("#F0F4F8"), colors.HexColor("#D9E2EC")

COLOR_ESTADO = {
    "Presente": VERDE,
    "Retraso": NARANJA,
    "Salida Temprana": NARANJA,
    "Ausente": ROJO,
    "Justificado": colors.HexColor("#0284C7")
}

H1 = ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=15, leading=19, textColor=AZUL)
P = ParagraphStyle("p", fontName="Helvetica", fontSize=9.5, leading=13, textColor=colors.HexColor("#334155"))
SM = ParagraphStyle("sm", parent=P, fontSize=8, leading=10)
ANCHO = 17.5 * cm
ANCHO_L = 25.5 * cm


def _encabezado(titulo, subtitulo, ancho=ANCHO):
    texto_marca = Paragraph(
        f"<font color='white'><b>{INSTITUCION}</b></font><br/>"
        "<font color='white' size='9'>Asista · Control de Asistencias</font>",
        ParagraphStyle("b", fontName="Helvetica", fontSize=13, leading=17)
    )
    ruta_escudo = Path(RUTA_ASSETS) / "escudo_institucion_tight.png"
    if not ruta_escudo.exists():
        ruta_escudo = Path(RUTA_ASSETS) / "escudo institucion.png"
    if ruta_escudo.exists():
        logo = ReportImage(str(ruta_escudo), width=1.45 * cm, height=2 * cm)
        celdas = [[logo, texto_marca]]
        anchos = [2 * cm, ancho - 2 * cm]
    else:
        celdas = [[texto_marca]]
        anchos = [ancho]
    banda = Table(celdas, colWidths=anchos)
    banda.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), AZUL),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (0, 0), 6),
        ("RIGHTPADDING", (0, 0), (0, 0), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return [banda, Spacer(1, 14), Paragraph(escape(titulo), H1), Paragraph(escape(subtitulo), P), Spacer(1, 10)]


def _tabla(filas, anchos, col_estado=None):
    t = Table(filas, colWidths=anchos, repeatRows=1)
    estilo = [("BACKGROUND", (0, 0), (-1, 0), AZUL), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
              ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 9),
              ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRIS]),
              ("GRID", (0, 0), (-1, -1), 0.25, BORDE), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]
    if col_estado is not None:
        for i, f in enumerate(filas[1:], start=1):
            estilo += [("TEXTCOLOR", (col_estado, i), (col_estado, i), COLOR_ESTADO.get(f[col_estado], colors.black)),
                       ("FONTNAME", (col_estado, i), (col_estado, i), "Helvetica-Bold")]
    t.setStyle(TableStyle(estilo))
    return t


def _kpis(r):
    pct = r.get("porcentaje_asistencia")
    vals = [int(r["asistencias"]), int(r["ausencias"]), int(r["retrasos"]), int(r["salidas_tempranas"]),
            f"{float(pct):.1f}%" if pct is not None else "—"]
    t = Table([["Asistencias", "Ausencias", "Retrasos", "Salidas tempranas", "% asistencia"], vals],
              colWidths=[ANCHO / 5] * 5)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), VERDE), ("BACKGROUND", (1, 0), (1, 0), ROJO),
        ("BACKGROUND", (2, 0), (3, 0), NARANJA), ("BACKGROUND", (4, 0), (4, 0), AZUL),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("FONTNAME", (0, 0), (-1, 1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9), ("FONTSIZE", (0, 1), (-1, 1), 16),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDE), ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.white)]))
    return t


def _persona(r):
    # Mostrar solo primer nombre y primer apellido en lugar del nombre completo
    nombre = r.get('nombre_completo') or ''
    partes = nombre.split()
    nombre_corto = partes[0] if partes else ''
    apellido_corto = partes[1] if len(partes) > 1 else ''
    extra = f" · {escape(str(r['seccion_o_cargo']))}" if r.get('seccion_o_cargo') else ""
    return Paragraph(f"<b>{escape(nombre_corto)} {escape(apellido_corto)}</b> · C.I. {escape(r['cedula'])} · {r['tipo_persona']}{extra}", P)


def _periodo(tipo, anio, periodo):
    if tipo == "Mensual":
        return f"{MESES[periodo - 1]} {anio}"
    return f"Semestre {periodo} de {anio} ({'Enero–Junio' if periodo == 1 else 'Julio–Diciembre'})"


def _individual(db, tipo, cedula, anio, periodo):
    etiqueta = _periodo(tipo, anio, periodo)
    if tipo == "Mensual":
        res = db.call("sp_reporte_mensual_cedula", (cedula, anio, periodo))
        resumen, detalle = res[0][0], res[1]
        historia = _encabezado("Reporte mensual de asistencia", etiqueta)
        historia += [_persona(resumen), Spacer(1, 10), _kpis(resumen), Spacer(1, 14)]
        filas = [["Fecha", "Día", "Entrada", "Salida", "Estado", "Observaciones"]]
        for d in detalle:
            filas.append([d["fecha"].strftime("%d/%m/%Y"), d["dia_semana"], fmt_hora(d["hora_entrada"]),
                          fmt_hora(d["hora_salida"]), d["estado"], Paragraph(escape(d["observaciones"] or ""), SM)])
        if len(filas) == 1:
            historia.append(Paragraph("No hay registros diarios para este período.", P))
        else:
            historia.append(_tabla(filas, [2.2 * cm, 2.2 * cm, 1.8 * cm, 1.8 * cm, 2.6 * cm, 6.9 * cm], col_estado=4))
        return historia

    res = db.call("sp_reporte_semestral", (cedula, anio, periodo))
    resumen, meses = res[0][0], res[1]
    historia = _encabezado("Reporte semestral acumulado", etiqueta)
    historia += [_persona(resumen), Spacer(1, 10), _kpis(resumen), Spacer(1, 10),
                 Paragraph(f"Meses cerrados considerados: <b>{int(resumen['meses_cerrados'])} de 6</b>. "
                           "Los meses sin cierre no se incluyen en el acumulado.", P), Spacer(1, 10)]
    filas = [["Mes", "Asistencias", "Ausencias", "Retrasos", "Salidas tempr.", "Días registrados"]]
    for m in meses:
        filas.append([m["nombre_mes"], m["total_asistencias"], m["total_ausencias"], m["total_retrasos"],
                      m["total_salidas_tempranas"], m["total_dias_registrados"]])
    if len(filas) > 1:
        historia.append(_tabla(filas, [ANCHO / 6] * 6))
    return historia


def _seccion(db, tipo, id_seccion, anio, periodo):
    sec = db.fetch_one("SELECT CONCAT(grado_ano, '° \"', seccion_letra, '\" - ', turno) AS e "
                       "FROM seccion WHERE id_seccion = %s", (id_seccion,))["e"]
    alumnos = db.fetch_all(
        "SELECT p.cedula, CONCAT(p.apellido, ' ', p.nombre) AS nombre FROM estudiante e "
        "JOIN persona p ON p.id_persona = e.id_persona WHERE e.id_seccion = %s AND p.activo = 1 "
        "ORDER BY p.apellido, p.nombre", (id_seccion,))
    sp = "sp_reporte_mensual_cedula" if tipo == "Mensual" else "sp_reporte_semestral"
    historia = _encabezado(f"Reporte {tipo.lower()} por sección", f"Sección {sec} · {_periodo(tipo, anio, periodo)}")
    filas = [["Cédula", "Estudiante", "Asist.", "Aus.", "Retr.", "Sal. temp.", "% asist."]]
    for a in alumnos:
        r = db.call(sp, (a["cedula"], anio, periodo))[0][0]
        pct = r["porcentaje_asistencia"]
        filas.append([a["cedula"], a["nombre"], int(r["asistencias"]), int(r["ausencias"]), int(r["retrasos"]),
                      int(r["salidas_tempranas"]), f"{float(pct):.1f}%" if pct is not None else "—"])
    if len(filas) == 1:
        historia.append(Paragraph("La sección no tiene estudiantes registrados.", P))
    else:
        historia.append(_tabla(filas, [2.4 * cm, 6 * cm, 1.8 * cm, 1.8 * cm, 1.8 * cm, 2 * cm, 1.7 * cm]))
    return historia


def _matriz_seccion_historia(db, id_seccion, anio, mes):
    datos = db.matriz_asistencia_seccion(id_seccion, anio, mes)
    sec_txt = datos["seccion"]["etiqueta"]
    dias_mes = datos["dias_mes"]

    historia = _encabezado(
        f"Matriz mensual de asistencia diaria · Sección {sec_txt}",
        f"Mes de {MESES[mes - 1]} de {anio} · Convención: P = Presente, A = Ausente, R = Retraso, T = Salida Temprana",
        ancho=ANCHO_L
    )

    alumnos = datos["alumnos"]
    mapa = datos["registros"]

    # Definir anchos
    w_num = 0.8 * cm
    w_ced = 2.0 * cm
    w_nom = 4.2 * cm
    w_dia = (ANCHO_L - (w_num + w_ced + w_nom + 4.5 * cm)) / dias_mes
    w_asist = 1.1 * cm
    w_aus = 1.1 * cm
    w_ret = 1.1 * cm
    w_pct = 1.2 * cm

    anchos = [w_num, w_ced, w_nom] + [w_dia] * dias_mes + [w_asist, w_aus, w_ret, w_pct]

    headers = ["N°", "Cédula", "Estudiante"] + [str(d) for d in range(1, dias_mes + 1)] + ["Asist.", "Aus.", "Retr.", "%"]
    filas = [headers]

    for idx, alu in enumerate(alumnos, start=1):
        pid = alu["id_persona"]
        nom_corto = f"{alu['apellido']} {alu['nombre']}"
        if len(nom_corto) > 22:
            nom_corto = nom_corto[:20] + "…"

        asistencias_alu = mapa.get(pid, {})
        cant_p, cant_a, cant_r, cant_t = 0, 0, 0, 0
        dias_vals = []

        for dia in range(1, dias_mes + 1):
            if dia in asistencias_alu:
                st = asistencias_alu[dia]["estado"]
                if st == "Presente":
                    dias_vals.append("P")
                    cant_p += 1
                elif st == "Ausente":
                    dias_vals.append("A")
                    cant_a += 1
                elif st == "Retraso":
                    dias_vals.append("R")
                    cant_r += 1
                elif st == "Salida Temprana":
                    dias_vals.append("T")
                    cant_t += 1
            else:
                dia_sem = date(anio, mes, dia).weekday()
                dias_vals.append("·" if dia_sem >= 5 else "—")

        tot = cant_p + cant_a + cant_r + cant_t
        pct = round(100.0 * (cant_p + cant_r + cant_t) / tot, 1) if tot > 0 else 0.0

        filas.append([str(idx), alu["cedula"], nom_corto] + dias_vals + [str(cant_p), str(cant_a), str(cant_r), f"{pct}%"])

    t = Table(filas, colWidths=anchos, repeatRows=1)
    estilo = [
        ("BACKGROUND", (0, 0), (-1, 0), AZUL),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 6.5),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("ALIGN", (2, 1), (2, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.25, BORDE),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRIS]),
    ]
    t.setStyle(TableStyle(estilo))
    historia.append(t)
    return historia


def _alerta_inasistencias_historia(db, anio, periodo, tipo_periodo, umbral=25.0):
    mes = periodo if tipo_periodo == "Mensual" else None
    semestre = periodo if tipo_periodo == "Semestral" else None
    datos = db.alerta_inasistencias(anio, mes=mes, semestre=semestre, umbral=umbral)

    sub = f"Período: {MESES[periodo - 1]} {anio}" if tipo_periodo == "Mensual" else f"Semestre {periodo} ({anio})"
    historia = _encabezado(
        f"Alerta temprana · Inasistencias crónicas (> {umbral}%)",
        f"{sub} · Criterio legal: Reglamento LOE sobre inasistencias mínimas"
    )

    alerta_box = Table([[Paragraph(
        "<font color='#991B1B'><b>NOTA INSTITUCIONAL DE CONTROL ACADÉMICO:</b><br/>"
        "Los estudiantes señalados en este reporte registran un nivel de inasistencia que supera el "
        "límite reglamentario del 25%, comprometiendo la validez de la evaluación continua. "
        "Se exhorta a Coordinación y Control de Estudio a citar a los representantes legales.</font>",
        ParagraphStyle("al", fontName="Helvetica", fontSize=8.5, leading=12)
    )]], colWidths=[ANCHO])
    alerta_box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FEE2E2")),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#F87171"))
    ]))
    historia += [alerta_box, Spacer(1, 14)]

    filas = [["Cédula", "Estudiante", "Sección", "Turno", "Días", "Faltas", "% Faltas", "Teléfono"]]
    for r in datos:
        nom = r.get("nombre_completo") or ""
        partes = nom.split()
        nom_corto = f"{partes[0]} {partes[1]}" if len(partes) > 1 else (partes[0] if partes else "—")
        sec_txt = str(r.get("seccion") or "—")
        if len(sec_txt) > 26:
            sec_txt = sec_txt[:24] + "..."
        filas.append([
            Paragraph(escape(str(r["cedula"])), SM),
            Paragraph(escape(nom_corto), SM),
            Paragraph(escape(sec_txt), SM),
            Paragraph(escape(str(r.get("turno") or "—")), SM),
            Paragraph(str(r["dias_registrados"]), SM),
            Paragraph(str(r["ausencias"]), SM),
            Paragraph(f"{r['pct_ausencia']}%", SM),
            Paragraph(escape(str(r.get("telefono") or "—")), SM)
        ])

    if len(filas) == 1:
        historia.append(Paragraph("<b>Excelente:</b> Ningún estudiante supera el límite crítico de inasistencias en este período.", P))
    else:
        anchos = [2.0 * cm, 3.8 * cm, 4.0 * cm, 1.8 * cm, 1.2 * cm, 1.3 * cm, 1.6 * cm, 2.3 * cm]
        t = Table(filas, colWidths=anchos, repeatRows=1)
        estilo = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DC2626")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("ALIGN", (1, 1), (1, -1), "LEFT"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRIS]),
            ("GRID", (0, 0), (-1, -1), 0.25, BORDE),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE")
        ]
        t.setStyle(TableStyle(estilo))
        historia.append(t)

    return historia


def _pie(canvas, doc=None):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#64748B"))
    canvas.drawString(2 * cm, 1 * cm, f"Generado el {datetime.now():%d/%m/%Y %H:%M} · Asista")
    page_num = doc.page if (doc and hasattr(doc, 'page')) else getattr(canvas, '_pageNumber', 1)
    canvas.drawRightString(letter[0] - 2 * cm, 1 * cm, f"Página {page_num}")
    canvas.restoreState()


def _pie_apaisado(canvas, doc=None):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#64748B"))
    canvas.drawString(1.5 * cm, 0.8 * cm, f"Generado el {datetime.now():%d/%m/%Y %H:%M} · Asista · Control de Asistencias")
    page_num = doc.page if (doc and hasattr(doc, 'page')) else getattr(canvas, '_pageNumber', 1)
    canvas.drawRightString(landscape(letter)[0] - 1.5 * cm, 0.8 * cm, f"Página {page_num}")
    canvas.restoreState()


def generar(db, tipo, alcance, valor, anio, periodo, ruta):
    """Genera reportes PDF tradicionales (Individual o Resumen por sección)."""
    historia = (_individual(db, tipo, valor, anio, periodo) if alcance == "Individual"
                else _seccion(db, tipo, valor, anio, periodo))
    doc = SimpleDocTemplate(ruta, pagesize=letter, leftMargin=2 * cm, rightMargin=2 * cm,
                            topMargin=1.5 * cm, bottomMargin=1.8 * cm, title="Reporte Asista")
    doc.build(historia, onFirstPage=_pie, onLaterPages=_pie)
    return ruta


def generar_matriz_pdf(db, id_seccion, anio, mes, ruta):
    """Genera la matriz de asistencia 1 al 31 apaisada en PDF."""
    historia = _matriz_seccion_historia(db, id_seccion, anio, mes)
    doc = SimpleDocTemplate(ruta, pagesize=landscape(letter), leftMargin=1.2 * cm, rightMargin=1.2 * cm,
                            topMargin=1.2 * cm, bottomMargin=1.2 * cm, title="Matriz Mensual Asista")
    doc.build(historia, onFirstPage=_pie_apaisado, onLaterPages=_pie_apaisado)
    return ruta


def generar_alerta_pdf(db, anio, periodo, tipo_periodo, ruta, umbral=25.0):
    """Genera el reporte de alerta temprana en PDF."""
    historia = _alerta_inasistencias_historia(db, anio, periodo, tipo_periodo, umbral)
    doc = SimpleDocTemplate(ruta, pagesize=letter, leftMargin=2 * cm, rightMargin=2 * cm,
                            topMargin=1.5 * cm, bottomMargin=1.8 * cm, title="Alerta Temprana Asista")
    doc.build(historia, onFirstPage=_pie, onLaterPages=_pie)
    return ruta


def generar_reporte_diario_pdf(db, fecha, ruta):
    """Genera el acta oficial de Cierre Diario de Asistencia en PDF con diseño limpio y columnas proporcionales."""
    if isinstance(fecha, str):
        fecha = datetime.strptime(fecha.strip(), "%Y-%m-%d").date()

    stats = db.obtener_estadisticas_dia(fecha)
    etiqueta_fecha = f"{fecha.day} de {MESES[fecha.month - 1]} de {fecha.year}"

    ANCHO_PAGINA = 18.6 * cm

    doc = SimpleDocTemplate(
        ruta,
        pagesize=letter,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.8 * cm,
        title="Cierre Diario de Asistencia - Asista"
    )

    historia = _encabezado(
        "ACTA DE CIERRE DIARIO DE ASISTENCIA ESCOLAR",
        f"Fecha Oficial: {etiqueta_fecha} · Generado: {datetime.now():%d/%m/%Y %I:%M %p}",
        ancho=ANCHO_PAGINA
    )

    pct = stats["pct_asistencia"]
    vals = [
        str(stats["total_matricula"]),
        str(stats["presentes"]),
        str(stats["retrasos"]),
        str(stats["salidas_tempranas"]),
        str(stats["ausencias"]),
        str(stats["justificados"]),
        f"{float(pct):.1f}%"
    ]
    t_kpis = Table(
        [["Matrícula", "Presentes", "Retrasos", "Sal. Temp.", "Ausencias", "Justific.", "% Asist."], vals],
        colWidths=[ANCHO_PAGINA / 7] * 7
    )
    t_kpis.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), AZUL),
        ("BACKGROUND", (1, 0), (1, 0), VERDE),
        ("BACKGROUND", (2, 0), (2, 0), NARANJA),
        ("BACKGROUND", (3, 0), (3, 0), NARANJA),
        ("BACKGROUND", (4, 0), (4, 0), ROJO),
        ("BACKGROUND", (5, 0), (5, 0), colors.HexColor("#0284C7")),
        ("BACKGROUND", (6, 0), (6, 0), VERDE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("FONTSIZE", (0, 1), (-1, 1), 13),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDE),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.white)
    ]))
    historia += [t_kpis, Spacer(1, 14)]

    historia.append(Paragraph("<b>Detalle de Asistencias del Día</b>", H1))
    historia.append(Spacer(1, 6))

    # Anchos proporcionales limpios (suman exactamente 18.6 cm, ancho útil imprimible)
    anchos = [2.2 * cm, 4.4 * cm, 1.8 * cm, 5.4 * cm, 1.5 * cm, 1.5 * cm, 1.8 * cm]

    # Estilos de celdas con envoltura automática de texto (evita solapamientos)
    TH_C = ParagraphStyle("th_c", fontName="Helvetica-Bold", fontSize=8, leading=10, textColor=colors.white, alignment=TA_CENTER)
    TH_L = ParagraphStyle("th_l", fontName="Helvetica-Bold", fontSize=8, leading=10, textColor=colors.white, alignment=TA_LEFT)

    TD_CED = ParagraphStyle("td_ced", fontName="Helvetica", fontSize=8, leading=10, textColor=colors.HexColor("#1E293B"), alignment=TA_CENTER)
    TD_NOM = ParagraphStyle("td_nom", fontName="Helvetica", fontSize=8, leading=10.5, textColor=colors.HexColor("#0F2042"), alignment=TA_LEFT)
    TD_TIPO = ParagraphStyle("td_tipo", fontName="Helvetica", fontSize=7.5, leading=9.5, textColor=colors.HexColor("#475569"), alignment=TA_CENTER)
    TD_DET = ParagraphStyle("td_det", fontName="Helvetica", fontSize=7.5, leading=9.5, textColor=colors.HexColor("#334155"), alignment=TA_LEFT)
    TD_HORA = ParagraphStyle("td_hora", fontName="Helvetica", fontSize=7.5, leading=9.5, textColor=colors.HexColor("#1E293B"), alignment=TA_CENTER)
    TD_ESTADO = ParagraphStyle("td_est", fontName="Helvetica-Bold", fontSize=8, leading=10, alignment=TA_CENTER)

    filas = [[
        Paragraph("<b>Cédula</b>", TH_C),
        Paragraph("<b>Nombre y Apellido</b>", TH_L),
        Paragraph("<b>Tipo</b>", TH_C),
        Paragraph("<b>Sección / Cargo / Curso</b>", TH_L),
        Paragraph("<b>Entrada</b>", TH_C),
        Paragraph("<b>Salida</b>", TH_C),
        Paragraph("<b>Estado</b>", TH_C)
    ]]

    registros = stats.get("registros", [])
    if not registros:
        filas.append([
            Paragraph("—", TD_CED),
            Paragraph("Sin registros de asistencia para esta fecha", TD_NOM),
            Paragraph("—", TD_TIPO),
            Paragraph("—", TD_DET),
            Paragraph("—", TD_HORA),
            Paragraph("—", TD_HORA),
            Paragraph("—", TD_ESTADO)
        ])
    else:
        for r in registros:
            # Formatear detalle (Curso o Sección)
            det_raw = str(r.get("detalle") or "—").strip()
            if det_raw.startswith("Curso: ") and " (" in det_raw and det_raw.endswith(")"):
                partes = det_raw[7:].rsplit(" (", 1)
                curso_nom = escape(partes[0])
                horario = escape(partes[1][:-1])
                det_html = f"<b>{curso_nom}</b><br/><font color='#64748B' size='6.5'>{horario}</font>"
            else:
                det_html = escape(det_raw)

            # Observaciones / Justificación
            obs = (r.get("observaciones") or "").strip()
            if obs:
                det_html += f"<br/><font color='#0284C7' size='6.5'><i>Obs: {escape(obs)}</i></font>"

            # Color del estado
            est = str(r.get("estado") or "Presente").strip()
            col_hex = (
                "#059669" if est == "Presente"
                else "#0284C7" if est == "Justificado"
                else "#E8890C" if est in ("Retraso", "Salida Temprana")
                else "#DC2626"
            )
            est_html = f"<font color='{col_hex}'><b>{escape(est)}</b></font>"

            h_ent = fmt_hora(r.get("hora_entrada")) if r.get("hora_entrada") else "—"
            h_sal = fmt_hora(r.get("hora_salida")) if r.get("hora_salida") else "—"

            filas.append([
                Paragraph(escape(str(r["cedula"])), TD_CED),
                Paragraph(f"<b>{escape(str(r['nombre']))}</b> {escape(str(r['apellido']))}", TD_NOM),
                Paragraph(escape(str(r["tipo_persona"])), TD_TIPO),
                Paragraph(det_html, TD_DET),
                Paragraph(h_ent, TD_HORA),
                Paragraph(h_sal, TD_HORA),
                Paragraph(est_html, TD_ESTADO)
            ])

    t_detalle = Table(filas, colWidths=anchos, repeatRows=1)
    t_detalle.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), AZUL),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")])
    ]))
    historia.append(t_detalle)
    historia.append(Spacer(1, 28))

    t_firmas = Table([
        ["_____________________________", "_____________________________"],
        ["Dirección del Plantel", "Control de Asistencias / Operador"]
    ], colWidths=[ANCHO_PAGINA / 2, ANCHO_PAGINA / 2])
    t_firmas.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2)
    ]))
    historia.append(t_firmas)

    doc.build(historia, onFirstPage=_pie, onLaterPages=_pie)
    return ruta


def generar_acta_cohorte_pdf(db, id_cohorte, ruta_pdf):
    """Genera el Acta Oficial de Asistencia y Evaluación para una cohorte técnica con gráfica de dona."""
    import graficos_utils
    from reportlab.platypus import Image as RLImage

    res = db.obtener_resumen_cohorte(id_cohorte)
    if not res:
        raise UserWarning("No se encontró información para la cohorte seleccionada.")

    cohorte = res["cohorte"]
    estudiantes = res["estudiantes"]
    total_ses = res["total_sesiones"]

    doc = SimpleDocTemplate(
        ruta_pdf, pagesize=letter,
        leftMargin=1.2 * cm, rightMargin=1.2 * cm,
        topMargin=1.2 * cm, bottomMargin=1.2 * cm
    )
    story = []

    # Encabezado institucional
    story += _encabezado(
        "ACTA OFICIAL DE ASISTENCIA Y RENDIMIENTO ACADÉMICO",
        f"Especialidad: {cohorte['curso_nombre']} ({cohorte['curso_codigo']})  |  Grupo / Turno: {cohorte['nombre_grupo']}"
    )

    # Ficha técnica de la cohorte
    docente_str = cohorte["docente_nombre"] if cohorte["docente_nombre"].strip() else "No asignado"
    meta_info = [
        [f"Docente Titular: {docente_str}", f"Período: {cohorte.get('periodo_nombre', 'Actual')}"],
        [f"Horario: {cohorte.get('hora_inicio', '--')} - {cohorte.get('hora_fin', '--')}", f"Días: {cohorte.get('dias_semana', 'Lun-Vie')}"],
        [f"Aula / Taller: {cohorte.get('aula', 'Sede Central')}", f"Sesiones Registradas: {total_ses} clases"]
    ]
    t_meta = Table(meta_info, colWidths=[10 * cm, 9 * cm])
    t_meta.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#1E293B")),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDE),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, BORDE),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 10))

    # Gráfica de Dona de la cohorte
    dona_data = {"Presente": 0, "Retraso": 0, "Ausente": 0, "Justificado": 0}
    for e in estudiantes:
        dona_data["Presente"] += e["presentes"]
        dona_data["Retraso"] += e["retrasos"]
        dona_data["Ausente"] += e["ausentes"]
        dona_data["Justificado"] += e["justificados"]

    buf_dona = graficos_utils.generar_bytes_grafica_dona(dona_data, size=(380, 190))
    story.append(RLImage(buf_dona, width=15 * cm, height=7.5 * cm))
    story.append(Spacer(1, 10))

    # Tabla de estudiantes
    cabecera = ["N°", "Cédula", "Estudiante (Apellidos y Nombres)", "Pres.", "Ret.", "Aus.", "Just.", "% Asist.", "Condición Final"]
    filas = [cabecera]
    for i, a in enumerate(estudiantes, start=1):
        filas.append([
            str(i),
            a["cedula"],
            a["nombre_completo"],
            str(a["presentes"]),
            str(a["retrasos"]),
            str(a["ausentes"]),
            str(a["justificados"]),
            f"{a['porcentaje']}%",
            a["estado_aprobacion"]
        ])

    t_est = Table(filas, colWidths=[0.8 * cm, 2.2 * cm, 6.2 * cm, 1.2 * cm, 1.2 * cm, 1.2 * cm, 1.2 * cm, 1.8 * cm, 3.4 * cm], repeatRows=1)
    estilo_est = [
        ("BACKGROUND", (0, 0), (-1, 0), AZUL),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRIS]),
        ("GRID", (0, 0), (-1, -1), 0.25, BORDE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (3, 0), (-1, -1), "CENTER")
    ]
    for idx_row, a in enumerate(estudiantes, start=1):
        color_cond = VERDE if a["estado_aprobacion"] == "APROBADO" else ROJO
        estilo_est.append(("TEXTCOLOR", (8, idx_row), (8, idx_row), color_cond))
        estilo_est.append(("FONTNAME", (8, idx_row), (8, idx_row), "Helvetica-Bold"))

    t_est.setStyle(TableStyle(estilo_est))
    story.append(t_est)
    story.append(Spacer(1, 24))

    # Bloque de firmas
    firmas = [
        [
            Paragraph("____________________________<br/><b>Firma del Docente Titular</b><br/>C.I.: " + cohorte.get("docente_cedula", "_____________"), P),
            Paragraph("____________________________<br/><b>Dirección Académica</b><br/>Sello y Validación Oficial", P)
        ]
    ]
    t_firmas = Table(firmas, colWidths=[9.5 * cm, 9.5 * cm])
    t_firmas.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "TOP")
    ]))
    story.append(t_firmas)
    story.append(Spacer(1, 10))
    doc.build(story, onFirstPage=_pie, onLaterPages=_pie)
    return ruta_pdf


def generar_informe_estadistico_pdf(db, ruta_pdf):
    """Genera el Informe Ejecutivo Estadístico Institucional con las 3 gráficas y KPIs consolidados."""
    import graficos_utils
    from reportlab.platypus import Image as RLImage

    m = db.metricas_graficas_instituto()
    kpis = m["kpis"]
    dona = m["dona"]
    barras = m["barras"]
    lineas = m["lineas"]

    doc = SimpleDocTemplate(
        ruta_pdf, pagesize=letter,
        leftMargin=1.2 * cm, rightMargin=1.2 * cm,
        topMargin=1.2 * cm, bottomMargin=1.2 * cm
    )
    story = []

    story += _encabezado(
        "INFORME ESTADÍSTICO EJECUTIVO DE ASISTENCIA",
        "Métricas consolidadas, distribución de puntualidad y constancia académica institucional"
    )

    # Tarjetas KPI
    kpi_filas = [
        ["Total Asistencias Registradas", "% Efectividad / Puntualidad", "Cursos Técnicos Activos", "Alertas de Deserción"],
        [f"{kpis['total_asistencias']} marcajes", f"{kpis['pct_global']}%", f"{kpis['cursos_activos']} cursos", f"{kpis['alertas']} casos"]
    ]
    t_kpis = Table(kpi_filas, colWidths=[4.75 * cm, 4.75 * cm, 4.75 * cm, 4.75 * cm])
    t_kpis.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F2042")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8.5),
        ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#F0F4F8")),
        ("TEXTCOLOR", (0, 1), (-1, 1), colors.HexColor("#0F2042")),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 1), (-1, 1), 12),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDE),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t_kpis)
    story.append(Spacer(1, 14))

    # Gráficas 1 y 2 en fila (Dona y Barras)
    buf_dona = graficos_utils.generar_bytes_grafica_dona(dona, size=(380, 220))
    buf_barras = graficos_utils.generar_bytes_grafica_barras(barras, size=(420, 220))
    fila_graficas = [
        [RLImage(buf_dona, width=9.2 * cm, height=5.3 * cm),
         RLImage(buf_barras, width=9.6 * cm, height=5.3 * cm)]
    ]
    t_graf = Table(fila_graficas, colWidths=[9.5 * cm, 9.5 * cm])
    t_graf.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE")
    ]))
    story.append(t_graf)
    story.append(Spacer(1, 10))

    # Gráfica 3: Tendencia Temporal
    buf_lineas = graficos_utils.generar_bytes_grafica_lineas(lineas, size=(840, 190))
    story.append(RLImage(buf_lineas, width=19 * cm, height=4.3 * cm))
    story.append(Spacer(1, 16))

    # Resumen y Conclusiones
    conclusiones = [
        [Paragraph("<b>Observaciones de Dirección:</b> El presente informe consolida el control de acceso en portería general y las asistencias registradas en los talleres técnicos de especialidad. La constancia mínima requerida para la acreditación técnica es del 75%.", P)]
    ]
    t_conc = Table(conclusiones, colWidths=[19 * cm])
    t_conc.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDE),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t_conc)
    story.append(Spacer(1, 12))
    doc.build(story, onFirstPage=_pie, onLaterPages=_pie)
    return ruta_pdf


def generar_historial_participante_pdf(db, cedula, ruta_pdf):
    """Genera el reporte oficial de historial completo de asistencia por participante en PDF."""
    datos = db.obtener_historial_asistencias_participante(cedula)
    if not datos or not datos.get("persona"):
        raise UserWarning(f"No se encontró ninguna persona registrada con la cédula {cedula}.")

    persona = datos["persona"]
    registros = datos.get("registros", [])
    matriculas = datos.get("matriculas", [])

    doc = SimpleDocTemplate(
        ruta_pdf,
        pagesize=letter,
        leftMargin=1.2 * cm,
        rightMargin=1.2 * cm,
        topMargin=1.2 * cm,
        bottomMargin=1.2 * cm,
        title=f"Historial Asistencia - C.I. {cedula}"
    )
    story = []

    nom_completo = f"{persona['nombre']} {persona['apellido']}"
    story += _encabezado(
        "HISTORIAL INDIVIDUAL DE ASISTENCIA Y PARTICIPACIÓN",
        f"Participante: {nom_completo}  |  C.I.: {cedula}  |  Emisión: {datetime.now():%d/%m/%Y %I:%M %p}"
    )

    # Ficha personal
    tel_str = persona.get("telefono") or "No registrado"
    cursos_inscritos = ", ".join(m["curso_nombre"] for m in matriculas) if matriculas else "Ningún curso activo"
    meta_info = [
        [f"Nombres y Apellidos: {nom_completo}", f"Cédula de Identidad: {cedula}"],
        [f"Teléfono de Contacto: {tel_str}", f"Tipo de Registro: {persona.get('tipo_persona', 'Estudiante')}"],
        [f"Cursos Matriculados: {cursos_inscritos}", f"Total Asistencias Registradas: {len(registros)}"]
    ]
    t_meta = Table(meta_info, colWidths=[10 * cm, 9 * cm])
    t_meta.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#1E293B")),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDE),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, BORDE),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 10))

    # Métricas y KPIs del participante
    pres = sum(1 for r in registros if r["estado"] == "Presente")
    ret = sum(1 for r in registros if r["estado"] == "Retraso")
    aus = sum(1 for r in registros if r["estado"] == "Ausente")
    just = sum(1 for r in registros if r["estado"] == "Justificado")
    tot = len(registros)
    pct = round(((pres + ret + just) / tot) * 100.0, 1) if tot > 0 else 100.0

    condicion = "EN REGLA" if pct >= 75.0 else "EN RIESGO (<75%)"
    kpis = [
        ["Total Clases", "Presentes", "Retrasos", "Ausencias", "Justificadas", "% Asistencia", "Condición"],
        [str(tot), str(pres), str(ret), str(aus), str(just), f"{pct}%", condicion]
    ]
    t_kpis = Table(kpis, colWidths=[2.7 * cm] * 7)
    color_cond = VERDE if pct >= 75.0 else ROJO
    t_kpis.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), AZUL),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("FONTSIZE", (0, 1), (-1, 1), 11),
        ("TEXTCOLOR", (6, 1), (6, 1), color_cond),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDE),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, BORDE),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t_kpis)
    story.append(Spacer(1, 12))

    # Detalle de asistencias sesión por sesión
    story.append(Paragraph("<b>Registro Detallado de Sesiones Sabatinas</b>", H1))
    story.append(Spacer(1, 6))

    filas = [["Fecha", "Hora", "Curso / Especialidad", "Grupo", "Estado", "Observaciones y Soporte"]]
    if not registros:
        filas.append(["—", "—", "Sin registros de asistencia acumulados", "—", "—", "—"])
    else:
        for r in registros:
            f_str = r["fecha"].strftime("%d/%m/%Y") if hasattr(r["fecha"], "strftime") else str(r["fecha"])
            h_str = str(r["hora"])[:5] if r.get("hora") else "--:--"
            filas.append([
                f_str,
                h_str,
                r.get("curso_nombre", "Curso"),
                r.get("nombre_grupo", "Sábado"),
                r["estado"],
                Paragraph(escape(r.get("observaciones") or "—"), SM)
            ])

    t_reg = Table(filas, colWidths=[2.2 * cm, 1.6 * cm, 4.8 * cm, 2.4 * cm, 2.2 * cm, 5.8 * cm], repeatRows=1)
    estilo_reg = [
        ("BACKGROUND", (0, 0), (-1, 0), AZUL),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRIS]),
        ("GRID", (0, 0), (-1, -1), 0.25, BORDE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (1, -1), "CENTER"),
        ("ALIGN", (4, 0), (4, -1), "CENTER")
    ]
    t_reg.setStyle(TableStyle(estilo_reg))
    story.append(t_reg)
    story.append(Spacer(1, 20))

    # Bloque de firmas
    firmas = [
        [
            Paragraph("____________________________<br/><b>Firma del Participante</b><br/>C.I.: " + cedula, P),
            Paragraph("____________________________<br/><b>Dirección Académica</b><br/>U.E.P. Prof. Aristóbulo Iztúriz", P)
        ]
    ]
    t_firmas = Table(firmas, colWidths=[9.5 * cm, 9.5 * cm])
    t_firmas.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "TOP")
    ]))
    story.append(t_firmas)
    story.append(Spacer(1, 10))
    doc.build(story, onFirstPage=_pie, onLaterPages=_pie)
    return ruta_pdf
