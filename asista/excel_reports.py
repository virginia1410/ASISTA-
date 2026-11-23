"""Módulo de Exportación a Microsoft Excel (.xlsx) con OpenPyXL para REGISTRA / Asista."""
from datetime import datetime, date
from pathlib import Path
import openpyxl
from openpyxl.drawing.image import Image as ExcelImage
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

from config import INSTITUCION, MESES
from db import fmt_hora
from tema import RUTA_ASSETS

# Paleta de colores Excel
COLOR_MORADO = "0F2042"
COLOR_BLANCO = "FFFFFF"
COLOR_GRIS_FONDO = "F8FAFC"
COLOR_BORDE = "CBD5E1"

# Fills para estados de asistencia
FILL_PRESENTE = PatternFill(start_color="D1F2D9", end_color="D1F2D9", fill_type="solid")
FONT_PRESENTE = Font(name="Calibri", size=10, bold=True, color="0F5132")

FILL_AUSENTE = PatternFill(start_color="F8D7DA", end_color="F8D7DA", fill_type="solid")
FONT_AUSENTE = Font(name="Calibri", size=10, bold=True, color="842029")

FILL_RETRASO = PatternFill(start_color="FFF3CD", end_color="FFF3CD", fill_type="solid")
FONT_RETRASO = Font(name="Calibri", size=10, bold=True, color="664D03")

FILL_TEMPRANA = PatternFill(start_color="E2D9F3", end_color="E2D9F3", fill_type="solid")
FONT_TEMPRANA = Font(name="Calibri", size=10, bold=True, color="381E72")

FILL_JUSTIFICADO = PatternFill(start_color="D1ECF1", end_color="D1ECF1", fill_type="solid")
FONT_JUSTIFICADO = Font(name="Calibri", size=10, bold=True, color="055160")

FILL_FIN_SEMANA = PatternFill(start_color="E2E8F0", end_color="E2E8F0", fill_type="solid")

BORDE_FINO = Border(
    left=Side(style="thin", color=COLOR_BORDE),
    right=Side(style="thin", color=COLOR_BORDE),
    top=Side(style="thin", color=COLOR_BORDE),
    bottom=Side(style="thin", color=COLOR_BORDE)
)


def _aplicar_cabecera_institucional(ws, titulo, subtitulo, total_cols=10):
    if total_cols < 3:
        raise ValueError("El encabezado institucional requiere al menos tres columnas.")

    for col in range(1, total_cols + 1):
        ws.cell(row=1, column=col).fill = PatternFill(
            start_color=COLOR_MORADO, end_color=COLOR_MORADO, fill_type="solid"
        )
    ws.merge_cells(start_row=1, start_column=3, end_row=1, end_column=total_cols)
    cell_inst = ws.cell(row=1, column=3)
    cell_inst.value = INSTITUCION.upper()
    cell_inst.font = Font(name="Calibri", size=14, bold=True, color=COLOR_BLANCO)
    cell_inst.fill = PatternFill(start_color=COLOR_MORADO, end_color=COLOR_MORADO, fill_type="solid")
    cell_inst.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws.row_dimensions[1].height = 42

    ruta_escudo = Path(RUTA_ASSETS) / "escudo institucion.png"
    if ruta_escudo.exists():
        escudo = ExcelImage(str(ruta_escudo))
        escudo.width = 38
        escudo.height = 40
        ws.add_image(escudo, "A1")

    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=total_cols)
    cell_tit = ws.cell(row=2, column=1)
    cell_tit.value = titulo
    cell_tit.font = Font(name="Calibri", size=12, bold=True, color="1E0B3A")
    cell_tit.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[2].height = 22

    ws.merge_cells(start_row=3, start_column=1, end_row=3, end_column=total_cols)
    cell_sub = ws.cell(row=3, column=1)
    cell_sub.value = subtitulo
    cell_sub.font = Font(name="Calibri", size=10, italic=True, color="475569")
    cell_sub.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[3].height = 18


def exportar_matriz_excel(db, id_seccion, anio, mes, ruta_guardar):
    """Genera la matriz mensual 1 al 31 por sección en Excel con formato condicional."""
    datos = db.matriz_asistencia_seccion(id_seccion, anio, mes)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Matriz {MESES[mes - 1][:3]} {anio}"

    sec_txt = datos["seccion"]["etiqueta"]
    dias_mes = datos["dias_mes"]
    total_cols = 3 + dias_mes + 4  # N°, Cédula, Estudiante + 1..dias + P, A, R, %

    _aplicar_cabecera_institucional(
        ws,
        f"CONTROL MENSUAL DE ASISTENCIA · SECCIÓN {sec_txt.upper()}",
        f"Período: {MESES[mes - 1]} de {anio} · Generado el {datetime.now():%d/%m/%Y %H:%M}",
        total_cols
    )

    # Encabezados de tabla
    headers = ["N°", "Cédula", "Apellidos y Nombres"]
    headers.extend([str(d) for d in range(1, dias_mes + 1)])
    headers.extend(["Presentes", "Ausentes", "Retrasos", "% Asistencia"])

    fila_header = 5
    ws.row_dimensions[fila_header].height = 24
    for col_idx, h in enumerate(headers, start=1):
        c = ws.cell(row=fila_header, column=col_idx)
        c.value = h
        c.font = Font(name="Calibri", size=10, bold=True, color=COLOR_BLANCO)
        c.fill = PatternFill(start_color=COLOR_MORADO, end_color=COLOR_MORADO, fill_type="solid")
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.border = BORDE_FINO

    # Rellenar estudiantes
    fila_actual = 6
    alumnos = datos["alumnos"]
    mapa = datos["registros"]

    for idx, alu in enumerate(alumnos, start=1):
        ws.row_dimensions[fila_actual].height = 20
        pid = alu["id_persona"]
        nombre_completo = f"{alu['apellido']} {alu['nombre']}"

        ws.cell(row=fila_actual, column=1, value=idx).alignment = Alignment(horizontal="center")
        ws.cell(row=fila_actual, column=2, value=alu["cedula"]).alignment = Alignment(horizontal="center")
        ws.cell(row=fila_actual, column=3, value=nombre_completo).alignment = Alignment(horizontal="left")

        for c_base in (1, 2, 3):
            cell = ws.cell(row=fila_actual, column=c_base)
            cell.font = Font(name="Calibri", size=10)
            cell.border = BORDE_FINO

        cant_p, cant_a, cant_r, cant_t = 0, 0, 0, 0
        asistencias_alumno = mapa.get(pid, {})

        for dia in range(1, dias_mes + 1):
            col_pos = 3 + dia
            c_dia = ws.cell(row=fila_actual, column=col_pos)
            c_dia.border = BORDE_FINO
            c_dia.alignment = Alignment(horizontal="center", vertical="center")

            # Comprobar si es fin de semana
            dia_semana = date(anio, mes, dia).weekday()
            es_fin_semana = dia_semana >= 5

            if dia in asistencias_alumno:
                st = asistencias_alumno[dia]["estado"]
                if st == "Presente":
                    c_dia.value = "P"
                    c_dia.fill = FILL_PRESENTE
                    c_dia.font = FONT_PRESENTE
                    cant_p += 1
                elif st == "Ausente":
                    c_dia.value = "A"
                    c_dia.fill = FILL_AUSENTE
                    c_dia.font = FONT_AUSENTE
                    cant_a += 1
                elif st == "Retraso":
                    c_dia.value = "R"
                    c_dia.fill = FILL_RETRASO
                    c_dia.font = FONT_RETRASO
                    cant_r += 1
                elif st == "Salida Temprana":
                    c_dia.value = "T"
                    c_dia.fill = FILL_TEMPRANA
                    c_dia.font = FONT_TEMPRANA
                    cant_t += 1
            else:
                if es_fin_semana:
                    c_dia.value = "·"
                    c_dia.fill = FILL_FIN_SEMANA
                    c_dia.font = Font(color="94A3B8")
                else:
                    c_dia.value = "—"
                    c_dia.font = Font(color="CBD5E1")

        # Columnas de resumen
        total_eval = cant_p + cant_a + cant_r + cant_t
        pct = round(100.0 * (cant_p + cant_r + cant_t) / total_eval, 1) if total_eval > 0 else 0.0

        for offset, (val, fmt_bold) in enumerate([
            (cant_p, True), (cant_a, True), (cant_r, False), (f"{pct}%", True)
        ]):
            c_res = ws.cell(row=fila_actual, column=3 + dias_mes + 1 + offset, value=val)
            c_res.border = BORDE_FINO
            c_res.alignment = Alignment(horizontal="center", vertical="center")
            c_res.font = Font(name="Calibri", size=10, bold=fmt_bold)

        fila_actual += 1

    # Ajustar anchos de columnas
    ws.column_dimensions["A"].width = 5
    ws.column_dimensions["B"].width = 13
    ws.column_dimensions["C"].width = 30
    for d in range(1, dias_mes + 1):
        col_letter = get_column_letter(3 + d)
        ws.column_dimensions[col_letter].width = 4.2

    for off in range(1, 5):
        col_letter = get_column_letter(3 + dias_mes + off)
        ws.column_dimensions[col_letter].width = 13

    wb.save(ruta_guardar)
    return ruta_guardar


def exportar_alerta_inasistencias_excel(db, anio, periodo, tipo_periodo, ruta_guardar, umbral=25.0):
    """Genera listado en Excel de estudiantes en riesgo por inasistencias críticas (> 25%)."""
    mes = periodo if tipo_periodo == "Mensual" else None
    semestre = periodo if tipo_periodo == "Semestral" else None

    datos = db.alerta_inasistencias(anio, mes=mes, semestre=semestre, umbral=umbral)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Alerta Inasistencias"

    sub = f"Período: {MESES[periodo - 1]} {anio}" if tipo_periodo == "Mensual" else f"Semestre {periodo} ({anio})"
    _aplicar_cabecera_institucional(
        ws,
        f"ALERTA TEMPRANA · ESTUDIANTES EN RIESGO POR INASISTENCIAS (> {umbral}%)",
        f"{sub} · Criterio Legal: Art. 109 LOE · Generado: {datetime.now():%d/%m/%Y %H:%M}",
        total_cols=9
    )

    headers = [
        "N°", "Cédula", "Estudiante", "Sección", "Turno",
        "Días Evaluados", "Inasistencias", "% Inasistencia", "Estado de Riesgo"
    ]
    fila_h = 5
    ws.row_dimensions[fila_h].height = 24
    for col_idx, h in enumerate(headers, start=1):
        c = ws.cell(row=fila_h, column=col_idx, value=h)
        c.font = Font(name="Calibri", size=10, bold=True, color=COLOR_BLANCO)
        c.fill = PatternFill(start_color="DC2626", end_color="DC2626", fill_type="solid")
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.border = BORDE_FINO

    fila_actual = 6
    for idx, r in enumerate(datos, start=1):
        ws.row_dimensions[fila_actual].height = 20
        pct = float(r["pct_ausencia"])
        estado_riesgo = "CRÍTICO (>25%)" if pct >= 25.0 else "PREVENTIVO"

        valores = [
            idx,
            r["cedula"],
            r["nombre_completo"],
            r["seccion"],
            r["turno"],
            r["dias_registrados"],
            r["ausencias"],
            f"{pct}%",
            estado_riesgo
        ]

        for col_idx, val in enumerate(valores, start=1):
            c = ws.cell(row=fila_actual, column=col_idx, value=val)
            c.border = BORDE_FINO
            c.font = Font(name="Calibri", size=10)
            if col_idx in (1, 2, 5, 6, 7, 8, 9):
                c.alignment = Alignment(horizontal="center", vertical="center")
            else:
                c.alignment = Alignment(horizontal="left", vertical="center")

            if col_idx == 8:
                c.font = Font(name="Calibri", size=10, bold=True, color="DC2626")
            elif col_idx == 9:
                c.font = Font(name="Calibri", size=10, bold=True)
                c.fill = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")

        fila_actual += 1

    anchos = [5, 14, 28, 18, 12, 14, 14, 15, 18]
    for i, w in enumerate(anchos, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w

    wb.save(ruta_guardar)
    return ruta_guardar


def exportar_resumen_seccion_excel(db, tipo, id_seccion, anio, periodo, ruta_guardar):
    """Exporta el consolidado mensual o semestral de una sección a Excel."""
    sec = db.fetch_one(
        "SELECT CONCAT(grado_ano, '° \"', seccion_letra, '\" - ', turno) AS e "
        "FROM seccion WHERE id_seccion = %s", (id_seccion,)
    )["e"]
    alumnos = db.fetch_all(
        "SELECT p.cedula, CONCAT(p.apellido, ' ', p.nombre) AS nombre FROM estudiante e "
        "JOIN persona p ON p.id_persona = e.id_persona WHERE e.id_seccion = %s AND p.activo = 1 "
        "ORDER BY p.apellido, p.nombre", (id_seccion,)
    )

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Resumen Sección"

    sub = f"Sección {sec} · Período: {MESES[periodo - 1] if tipo == 'Mensual' else f'Semestre {periodo}'} {anio}"
    _aplicar_cabecera_institucional(ws, f"RESUMEN DE ASISTENCIA POR SECCIÓN ({tipo.upper()})", sub, total_cols=8)

    headers = ["N°", "Cédula", "Estudiante", "Asistencias", "Ausencias", "Retrasos", "Sal. Tempranas", "% Asistencia"]
    fila_h = 5
    ws.row_dimensions[fila_h].height = 24
    for col_idx, h in enumerate(headers, start=1):
        c = ws.cell(row=fila_h, column=col_idx, value=h)
        c.font = Font(name="Calibri", size=10, bold=True, color=COLOR_BLANCO)
        c.fill = PatternFill(start_color=COLOR_MORADO, end_color=COLOR_MORADO, fill_type="solid")
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.border = BORDE_FINO

    sp = "sp_reporte_mensual_cedula" if tipo == "Mensual" else "sp_reporte_semestral"
    fila_actual = 6
    for idx, a in enumerate(alumnos, start=1):
        ws.row_dimensions[fila_actual].height = 20
        res = db.call(sp, (a["cedula"], anio, periodo))
        r = res[0][0]
        pct = r["porcentaje_asistencia"]

        valores = [
            idx,
            a["cedula"],
            a["nombre"],
            int(r["asistencias"]),
            int(r["ausencias"]),
            int(r["retrasos"]),
            int(r["salidas_tempranas"]),
            f"{float(pct):.1f}%" if pct is not None else "—"
        ]

        for col_idx, val in enumerate(valores, start=1):
            c = ws.cell(row=fila_actual, column=col_idx, value=val)
            c.border = BORDE_FINO
            c.font = Font(name="Calibri", size=10)
            c.alignment = Alignment(horizontal="center" if col_idx != 3 else "left", vertical="center")
            if col_idx == 8 and pct is not None:
                c.font = Font(name="Calibri", size=10, bold=True)
                if float(pct) >= 75.0:
                    c.font = Font(name="Calibri", size=10, bold=True, color="059669")
                else:
                    c.font = Font(name="Calibri", size=10, bold=True, color="DC2626")

        fila_actual += 1

    anchos = [5, 14, 30, 14, 14, 14, 15, 16]
    for i, w in enumerate(anchos, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w

    wb.save(ruta_guardar)
    return ruta_guardar


def exportar_reporte_diario_excel(db, fecha, ruta):
    """Genera el reporte Excel (.xlsx) institucional oficial de Cierre Diario de Asistencia."""
    if isinstance(fecha, str):
        fecha = datetime.strptime(fecha.strip(), "%Y-%m-%d").date()

    stats = db.obtener_estadisticas_dia(fecha)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Cierre {fecha.strftime('%Y-%m-%d')}"

    total_cols = 9
    _aplicar_cabecera_institucional(
        ws,
        "ACTA DE CIERRE DIARIO DE ASISTENCIA ESCOLAR",
        f"Fecha Oficial: {fecha.strftime('%d/%m/%Y')} · Generado el {datetime.now():%d/%m/%Y %H:%M}",
        total_cols
    )

    kpis = [
        ("Matrícula Total", stats["total_matricula"]),
        ("Presentes", stats["presentes"]),
        ("Retrasos", stats["retrasos"]),
        ("Salidas Tempranas", stats["salidas_tempranas"]),
        ("Ausencias", stats["ausencias"]),
        ("Justificados", stats["justificados"]),
        ("% Asistencia", f"{stats['pct_asistencia']:.1f}%")
    ]
    for i, (tit, val) in enumerate(kpis, start=1):
        c_tit = ws.cell(row=5, column=i, value=tit)
        c_tit.font = Font(name="Calibri", size=9, bold=True, color=COLOR_BLANCO)
        c_tit.fill = PatternFill(start_color=COLOR_MORADO, end_color=COLOR_MORADO, fill_type="solid")
        c_tit.alignment = Alignment(horizontal="center", vertical="center")
        c_tit.border = BORDE_FINO

        c_val = ws.cell(row=6, column=i, value=val)
        c_val.font = Font(name="Calibri", size=13, bold=True, color="1E0B3A")
        c_val.fill = PatternFill(start_color="F1E9FC", end_color="F1E9FC", fill_type="solid")
        c_val.alignment = Alignment(horizontal="center", vertical="center")
        c_val.border = BORDE_FINO

    ws.row_dimensions[5].height = 20
    ws.row_dimensions[6].height = 24

    headers = [
        "N°", "Cédula", "Apellidos y Nombres", "Tipo", "Sección / Cargo",
        "Hora Entrada", "Hora Salida", "Estado", "Observación / Justificación"
    ]
    fila_h = 8
    ws.row_dimensions[fila_h].height = 24
    for col_idx, h in enumerate(headers, start=1):
        c = ws.cell(row=fila_h, column=col_idx, value=h)
        c.font = Font(name="Calibri", size=10, bold=True, color=COLOR_BLANCO)
        c.fill = PatternFill(start_color=COLOR_MORADO, end_color=COLOR_MORADO, fill_type="solid")
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.border = BORDE_FINO

    fila_actual = 9
    registros = stats.get("registros", [])
    for idx, r in enumerate(registros, start=1):
        ws.row_dimensions[fila_actual].height = 20
        c_num = ws.cell(row=fila_actual, column=1, value=idx)
        c_ced = ws.cell(row=fila_actual, column=2, value=r["cedula"])
        c_nom = ws.cell(row=fila_actual, column=3, value=f"{r['apellido']}, {r['nombre']}")
        c_tip = ws.cell(row=fila_actual, column=4, value=r["tipo_persona"])
        c_det = ws.cell(row=fila_actual, column=5, value=r["detalle"] or "—")
        c_ent = ws.cell(row=fila_actual, column=6, value=fmt_hora(r["hora_entrada"]))
        c_sal = ws.cell(row=fila_actual, column=7, value=fmt_hora(r["hora_salida"]))
        c_est = ws.cell(row=fila_actual, column=8, value=r["estado"])
        c_obs = ws.cell(row=fila_actual, column=9, value=r["observaciones"] or "")

        est = r["estado"]
        if est == "Presente":
            c_est.fill, c_est.font = FILL_PRESENTE, FONT_PRESENTE
        elif est == "Ausente":
            c_est.fill, c_est.font = FILL_AUSENTE, FONT_AUSENTE
        elif est == "Retraso":
            c_est.fill, c_est.font = FILL_RETRASO, FONT_RETRASO
        elif est == "Salida Temprana":
            c_est.fill, c_est.font = FILL_TEMPRANA, FONT_TEMPRANA
        elif est == "Justificado":
            c_est.fill, c_est.font = FILL_JUSTIFICADO, FONT_JUSTIFICADO

        for col in range(1, total_cols + 1):
            ws.cell(row=fila_actual, column=col).border = BORDE_FINO

        c_num.alignment = Alignment(horizontal="center", vertical="center")
        c_ced.alignment = Alignment(horizontal="center", vertical="center")
        c_nom.alignment = Alignment(horizontal="left", vertical="center")
        c_tip.alignment = Alignment(horizontal="center", vertical="center")
        c_det.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
        c_ent.alignment = Alignment(horizontal="center", vertical="center")
        c_sal.alignment = Alignment(horizontal="center", vertical="center")
        c_est.alignment = Alignment(horizontal="center", vertical="center")
        c_obs.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)

        fila_actual += 1

    anchos = [5, 14, 30, 14, 20, 14, 14, 16, 32]
    for i, w in enumerate(anchos, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w

    wb.save(ruta)
    return ruta


def exportar_acta_cohorte_excel(db, id_cohorte, ruta_guardar):
    """Genera el acta oficial de asistencia y evaluación técnica por cohorte en Excel con estilos institucionales."""
    res = db.obtener_resumen_cohorte(id_cohorte)
    if not res:
        raise UserWarning("No se encontró información para la cohorte seleccionada.")

    cohorte = res["cohorte"]
    estudiantes = res["estudiantes"]
    total_ses = res["total_sesiones"]

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Acta {cohorte['nombre_grupo'][:15]}"

    _aplicar_cabecera_institucional(
        ws,
        f"ACTA OFICIAL DE ASISTENCIA Y EVALUACIÓN - {cohorte['curso_nombre'].upper()}",
        f"Grupo: {cohorte['nombre_grupo']} | Período: {cohorte.get('periodo_nombre', 'Actual')} | Docente: {cohorte['docente_nombre'] or 'No Asignado'}",
        total_cols=9
    )

    # Metadata de la cohorte
    ws.cell(row=5, column=1, value="Especialidad:").font = Font(name="Calibri", size=10, bold=True)
    ws.cell(row=5, column=2, value=f"{cohorte['curso_nombre']} ({cohorte['curso_codigo']})").font = Font(name="Calibri", size=10)
    ws.cell(row=5, column=5, value="Aula / Taller:").font = Font(name="Calibri", size=10, bold=True)
    ws.cell(row=5, column=6, value=cohorte.get("aula", "Sede Central")).font = Font(name="Calibri", size=10)

    ws.cell(row=6, column=1, value="Docente Titular:").font = Font(name="Calibri", size=10, bold=True)
    ws.cell(row=6, column=2, value=cohorte.get("docente_nombre", "No asignado")).font = Font(name="Calibri", size=10)
    ws.cell(row=6, column=5, value="Clases Registradas:").font = Font(name="Calibri", size=10, bold=True)
    ws.cell(row=6, column=6, value=f"{total_ses} sesiones").font = Font(name="Calibri", size=10)

    # Cabecera de la tabla
    headers = ["N°", "Cédula", "Estudiante (Apellidos y Nombres)", "Presentes", "Retrasos", "Ausencias", "Justificados", "% Asistencia", "Condición Final"]
    row_h = 8
    for col_idx, h in enumerate(headers, 1):
        c = ws.cell(row=row_h, column=col_idx, value=h)
        c.font = Font(name="Calibri", size=10, bold=True, color=COLOR_BLANCO)
        c.fill = PatternFill(start_color=COLOR_MORADO, end_color=COLOR_MORADO, fill_type="solid")
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.border = BORDE_FINO
    ws.row_dimensions[row_h].height = 24

    # Registros
    curr_row = 9
    for i, a in enumerate(estudiantes, 1):
        ws.cell(row=curr_row, column=1, value=i).alignment = Alignment(horizontal="center")
        ws.cell(row=curr_row, column=2, value=a["cedula"]).alignment = Alignment(horizontal="center")
        ws.cell(row=curr_row, column=3, value=a["nombre_completo"]).alignment = Alignment(horizontal="left")
        ws.cell(row=curr_row, column=4, value=a["presentes"]).alignment = Alignment(horizontal="center")
        ws.cell(row=curr_row, column=5, value=a["retrasos"]).alignment = Alignment(horizontal="center")
        ws.cell(row=curr_row, column=6, value=a["ausentes"]).alignment = Alignment(horizontal="center")
        ws.cell(row=curr_row, column=7, value=a["justificados"]).alignment = Alignment(horizontal="center")

        c_pct = ws.cell(row=curr_row, column=8, value=f"{a['porcentaje']}%")
        c_pct.alignment = Alignment(horizontal="center")
        c_pct.font = Font(name="Calibri", size=10, bold=True)

        c_cond = ws.cell(row=curr_row, column=9, value=a["estado_aprobacion"])
        c_cond.alignment = Alignment(horizontal="center")
        c_cond.font = Font(name="Calibri", size=10, bold=True, color="0F5132" if a["estado_aprobacion"] == "APROBADO" else "842029")
        c_cond.fill = FILL_PRESENTE if a["estado_aprobacion"] == "APROBADO" else FILL_AUSENTE

        for col in range(1, 10):
            ws.cell(row=curr_row, column=col).border = BORDE_FINO
            if col != 9 and col != 8:
                ws.cell(row=curr_row, column=col).font = Font(name="Calibri", size=10)

        ws.row_dimensions[curr_row].height = 20
        curr_row += 1

    # Ajustar anchos
    anchos = {1: 6, 2: 14, 3: 36, 4: 12, 5: 12, 6: 12, 7: 14, 8: 15, 9: 26}
    for col_idx, ancho in anchos.items():
        ws.column_dimensions[get_column_letter(col_idx)].width = ancho

    wb.save(ruta_guardar)
    return ruta_guardar


def exportar_historial_participante_excel(db, cedula, ruta_guardar):
    """Genera el reporte oficial de historial completo de asistencia por participante en Excel."""
    datos = db.obtener_historial_asistencias_participante(cedula)
    if not datos or not datos.get("persona"):
        raise UserWarning(f"No se encontró ninguna persona registrada con la cédula {cedula}.")

    persona = datos["persona"]
    registros = datos.get("registros", [])
    matriculas = datos.get("matriculas", [])
    nom_completo = f"{persona['nombre']} {persona['apellido']}"

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Historial {cedula}"

    _aplicar_cabecera_institucional(
        ws,
        "HISTORIAL INDIVIDUAL DE ASISTENCIA Y RENDIMIENTO",
        f"Participante: {nom_completo} | C.I.: {cedula} | Teléfono: {persona.get('telefono') or 'No registrado'}",
        total_cols=7
    )

    # Metadata
    cursos_inscritos = ", ".join(m["curso_nombre"] for m in matriculas) if matriculas else "Ninguno"
    ws.cell(row=5, column=1, value="Participante:").font = Font(name="Calibri", size=10, bold=True)
    ws.cell(row=5, column=2, value=nom_completo).font = Font(name="Calibri", size=10)
    ws.cell(row=5, column=4, value="C.I.:").font = Font(name="Calibri", size=10, bold=True)
    ws.cell(row=5, column=5, value=cedula).font = Font(name="Calibri", size=10)

    ws.cell(row=6, column=1, value="Cursos:").font = Font(name="Calibri", size=10, bold=True)
    ws.cell(row=6, column=2, value=cursos_inscritos).font = Font(name="Calibri", size=10)
    ws.cell(row=6, column=4, value="Total Clases:").font = Font(name="Calibri", size=10, bold=True)
    ws.cell(row=6, column=5, value=f"{len(registros)} sesiones").font = Font(name="Calibri", size=10)

    # Cabecera
    headers = ["N°", "Fecha", "Hora", "Curso / Especialidad", "Turno / Grupo", "Estado", "Observaciones y Soporte"]
    row_h = 8
    for col_idx, h in enumerate(headers, 1):
        c = ws.cell(row=row_h, column=col_idx, value=h)
        c.font = Font(name="Calibri", size=10, bold=True, color=COLOR_BLANCO)
        c.fill = PatternFill(start_color=COLOR_MORADO, end_color=COLOR_MORADO, fill_type="solid")
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.border = BORDE_FINO
    ws.row_dimensions[row_h].height = 24

    curr_row = 9
    pres = ret = aus = just = 0
    for i, r in enumerate(registros, 1):
        est = r["estado"]
        if est == "Presente": pres += 1
        elif est == "Retraso": ret += 1
        elif est == "Ausente": aus += 1
        elif est == "Justificado": just += 1

        f_str = r["fecha"].strftime("%d/%m/%Y") if hasattr(r["fecha"], "strftime") else str(r["fecha"])
        h_str = str(r["hora"])[:5] if r.get("hora") else "--:--"

        ws.cell(row=curr_row, column=1, value=i).alignment = Alignment(horizontal="center")
        ws.cell(row=curr_row, column=2, value=f_str).alignment = Alignment(horizontal="center")
        ws.cell(row=curr_row, column=3, value=h_str).alignment = Alignment(horizontal="center")
        ws.cell(row=curr_row, column=4, value=r.get("curso_nombre", "Curso")).alignment = Alignment(horizontal="left")
        ws.cell(row=curr_row, column=5, value=r.get("nombre_grupo", "Sábado")).alignment = Alignment(horizontal="center")

        c_est = ws.cell(row=curr_row, column=6, value=est)
        c_est.alignment = Alignment(horizontal="center")
        c_est.font = Font(name="Calibri", size=10, bold=True)
        if est == "Presente":
            c_est.fill = FILL_PRESENTE
            c_est.font = Font(name="Calibri", size=10, bold=True, color="0F5132")
        elif est == "Retraso":
            c_est.fill = FILL_RETRASO
            c_est.font = Font(name="Calibri", size=10, bold=True, color="664D03")
        elif est == "Justificado":
            c_est.fill = FILL_JUSTIFICADO
            c_est.font = Font(name="Calibri", size=10, bold=True, color="055160")
        else:
            c_est.fill = FILL_AUSENTE
            c_est.font = Font(name="Calibri", size=10, bold=True, color="842029")

        ws.cell(row=curr_row, column=7, value=r.get("observaciones") or "—").alignment = Alignment(horizontal="left")

        for col in range(1, 8):
            ws.cell(row=curr_row, column=col).border = BORDE_FINO
            if col != 6:
                ws.cell(row=curr_row, column=col).font = Font(name="Calibri", size=10)

        ws.row_dimensions[curr_row].height = 20
        curr_row += 1

    # Fila resumen
    tot = len(registros)
    pct = round(((pres + ret + just) / tot) * 100.0, 1) if tot > 0 else 100.0
    ws.cell(row=curr_row, column=1, value="RESUMEN:").font = Font(name="Calibri", size=10, bold=True)
    ws.cell(row=curr_row, column=4, value=f"{pres} Pres. | {ret} Ret. | {just} Just. | {aus} Aus.").font = Font(name="Calibri", size=10, bold=True)
    c_res_pct = ws.cell(row=curr_row, column=6, value=f"{pct}%")
    c_res_pct.font = Font(name="Calibri", size=11, bold=True, color="0F5132" if pct >= 75.0 else "842029")
    c_res_pct.alignment = Alignment(horizontal="center")

    for col in range(1, 8):
        ws.cell(row=curr_row, column=col).border = BORDE_FINO

    # Ajustar anchos
    anchos = {1: 6, 2: 14, 3: 10, 4: 32, 5: 18, 6: 16, 7: 38}
    for col_idx, ancho in anchos.items():
        ws.column_dimensions[get_column_letter(col_idx)].width = ancho

    wb.save(ruta_guardar)
    return ruta_guardar
