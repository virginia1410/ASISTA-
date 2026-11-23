"""Módulo de utilidades gráficas para ASISTA.
Genera gráficas estadísticas vectoriales/rasterizadas en alta resolución con Pillow:
- Gráfica de Dona (Distribución de Asistencia)
- Gráfica de Barras (Comparativa por Curso/Cohorte)
- Gráfica de Líneas (Tendencia y Evolución Semanal)
- Imagen consolidada para reportes ejecutivos en PDF.
"""
import math
import os
import io
from PIL import Image, ImageDraw, ImageFont

def _obtener_fuente(size=14, bold=False):
    """Carga fuentes estándar del sistema Windows con fallback seguro."""
    rutas = [
        r"C:\Windows\Fonts\segoeuib.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\calibrib.ttf" if bold else r"C:\Windows\Fonts\calibri.ttf"
    ]
    for r in rutas:
        if os.path.exists(r):
            try:
                return ImageFont.truetype(r, size)
            except Exception:
                pass
    return ImageFont.load_default()


def dibujar_grafica_dona(datos, size=(400, 250), is_dark=False):
    """Genera gráfica de dona de asistencia con leyenda y porcentaje central."""
    scale = 2
    w, h = size[0] * scale, size[1] * scale
    bg = (17, 34, 64, 255) if is_dark else (255, 255, 255, 255)
    img = Image.new("RGBA", (w, h), bg)
    draw = ImageDraw.Draw(img)

    f_titulo = _obtener_fuente(12 * scale, bold=True)
    f_num = _obtener_fuente(22 * scale, bold=True)
    f_sub = _obtener_fuente(10 * scale, bold=False)
    f_leg = _obtener_fuente(11 * scale, bold=False)
    f_leg_bold = _obtener_fuente(11 * scale, bold=True)

    colores = {
        "Presente": (16, 185, 129, 255),    # Verde Esmeralda #10B981
        "Retraso": (245, 158, 11, 255),     # Ámbar #F59E0B
        "Ausente": (239, 68, 68, 255),      # Rojo Coral #EF4444
        "Justificado": (0, 180, 216, 255),  # Turquesa #00B4D8
        "Salida Temprana": (139, 92, 246, 255)
    }

    # Título
    txt_color = (255, 255, 255, 255) if is_dark else (15, 32, 66, 255)
    sub_color = (148, 163, 184, 255) if is_dark else (100, 116, 139, 255)
    draw.text((18 * scale, 12 * scale), "Distribución de Asistencia en Cursos", font=f_titulo, fill=txt_color)

    # Cálculo de sectores
    total = sum(datos.values())
    hay_datos = total > 0
    if total <= 0:
        total = 1

    cx, cy = int(w * 0.32), int(h * 0.58)
    r_ext = int(min(w, h) * 0.34)
    r_int = int(r_ext * 0.64)

    start_deg = -90.0
    for estado, cant in datos.items():
        if cant <= 0:
            continue
        span = (cant / total) * 360.0
        c = colores.get(estado, (100, 116, 139, 255))
        draw.pieslice([cx - r_ext, cy - r_ext, cx + r_ext, cy + r_ext], start=start_deg, end=start_deg + span, fill=c)
        start_deg += span

    # Agujero central de la dona
    draw.ellipse([cx - r_int, cy - r_int, cx + r_int, cy + r_int], fill=bg)

    # Porcentaje de asistencia efectiva central
    presentes = datos.get("Presente", 0) + datos.get("Retraso", 0)
    pct = int((presentes / total) * 100) if total > 0 else 0
    str_pct = f"{pct}%" if hay_datos else "—"
    bbox_pct = draw.textbbox((0, 0), str_pct, font=f_num)
    pw = bbox_pct[2] - bbox_pct[0]
    draw.text((cx - pw // 2, cy - int(14 * scale)), str_pct, font=f_num, fill=txt_color)
    str_asist = "Efectiva" if hay_datos else "Sin datos"
    bbox_asist = draw.textbbox((0, 0), str_asist, font=f_sub)
    aw = bbox_asist[2] - bbox_asist[0]
    draw.text((cx - aw // 2, cy + int(10 * scale)), str_asist, font=f_sub, fill=sub_color)

    # Leyenda a la derecha
    lx = int(w * 0.60)
    ly = int(h * 0.28)
    step_y = int(24 * scale)

    for estado in ["Presente", "Retraso", "Ausente", "Justificado"]:
        cant = datos.get(estado, 0)
        c = colores.get(estado, (100, 116, 139, 255))
        p = int((cant / total) * 100) if total > 0 else 0
        # Círculo indicador
        draw.ellipse([lx, ly + 2 * scale, lx + 10 * scale, ly + 12 * scale], fill=c)
        # Etiqueta
        draw.text((lx + 16 * scale, ly), estado, font=f_leg, fill=txt_color)
        # Cantidad y %
        num_str = f"{cant} ({p}%)"
        draw.text((lx + 95 * scale, ly), num_str, font=f_leg_bold, fill=txt_color)
        ly += step_y

    return img.resize(size, Image.Resampling.LANCZOS)


def dibujar_grafica_barras(barras_data, size=(460, 250), is_dark=False):
    """Genera gráfica de barras comparativa de cursos y cohortes técnicas."""
    scale = 2
    w, h = size[0] * scale, size[1] * scale
    bg = (17, 34, 64, 255) if is_dark else (255, 255, 255, 255)
    img = Image.new("RGBA", (w, h), bg)
    draw = ImageDraw.Draw(img)

    f_titulo = _obtener_fuente(12 * scale, bold=True)
    f_curso = _obtener_fuente(10 * scale, bold=True)
    f_meta = _obtener_fuente(9 * scale, bold=False)
    f_pct = _obtener_fuente(10 * scale, bold=True)

    txt_color = (255, 255, 255, 255) if is_dark else (15, 32, 66, 255)
    sub_color = (148, 163, 184, 255) if is_dark else (100, 116, 139, 255)
    track_color = (30, 41, 59, 255) if is_dark else (226, 232, 240, 255)
    bar_color = (0, 180, 216, 255)     # Turquesa #00B4D8
    good_color = (16, 185, 129, 255)   # Verde #10B981

    # Título
    draw.text((18 * scale, 12 * scale), "Rendimiento y Asistencia por Curso Técnico", font=f_titulo, fill=txt_color)

    items = barras_data if barras_data else []
    n_items = len(items)
    if not items:
        draw.text(
            (18 * scale, int(h * 0.52)),
            "Sin registros de asistencia por curso",
            font=f_meta,
            fill=sub_color,
        )
        return img.resize(size, Image.Resampling.LANCZOS)
    
    # Ajustar dinámicamente el alto por item para que entren todos los cursos
    if n_items > 0:
        disponible_y = int(h * 0.72)
        item_height = max(int(22 * scale), disponible_y // n_items)
        y_pos = int(h * 0.22)
    else:
        item_height = int(h * 0.23)
        y_pos = int(h * 0.24)
    x_bar = int(w * 0.53)
    bar_w_max = int(w * 0.28)

    for item in items:
        nombre = item.get("curso", "Curso")
        if len(nombre) > 26:
            nombre = nombre[:24] + "…"
        tot = int(item.get("total_registros", 0) or 0)
        pres = float(item.get("presentes", 0) or 0)
        pct = min(100, max(0, int((pres / tot) * 100))) if tot else 0

        # Nombre del curso
        draw.text((18 * scale, y_pos), nombre, font=f_curso, fill=txt_color)
        meta_str = f"{int(pres)}/{tot} asistencias"
        draw.text((18 * scale, y_pos + 12 * scale), meta_str, font=f_meta, fill=sub_color)

        # Barra de progreso
        y_bar = y_pos + 3 * scale
        h_bar = int(12 * scale)
        r_bar = int(6 * scale)
        # Fondo
        draw.rounded_rectangle([x_bar, y_bar, x_bar + bar_w_max, y_bar + h_bar], radius=r_bar, fill=track_color)
        # Relleno
        fill_w = int(bar_w_max * (pct / 100.0))
        if fill_w > r_bar * 2:
            c_fill = good_color if pct >= 75 else bar_color
            draw.rounded_rectangle([x_bar, y_bar, x_bar + fill_w, y_bar + h_bar], radius=r_bar, fill=c_fill)

        # % a la derecha
        pct_str = f"{pct}%"
        draw.text((x_bar + bar_w_max + 10 * scale, y_pos), pct_str, font=f_pct, fill=txt_color)

        y_pos += item_height

    return img.resize(size, Image.Resampling.LANCZOS)


def dibujar_grafica_lineas(lineas_data, size=(880, 200), is_dark=False):
    """Genera gráfica de tendencia temporal / evolución semanal."""
    scale = 2
    w, h = size[0] * scale, size[1] * scale
    bg = (17, 34, 64, 255) if is_dark else (255, 255, 255, 255)
    img = Image.new("RGBA", (w, h), bg)
    draw = ImageDraw.Draw(img)

    f_titulo = _obtener_fuente(12 * scale, bold=True)
    f_axis = _obtener_fuente(9 * scale, bold=False)
    f_pt = _obtener_fuente(8 * scale, bold=True)

    txt_color = (255, 255, 255, 255) if is_dark else (15, 32, 66, 255)
    sub_color = (148, 163, 184, 255) if is_dark else (100, 116, 139, 255)
    grid_color = (30, 41, 59, 180) if is_dark else (241, 245, 249, 255)
    line_color = (0, 180, 216, 255)     # Turquesa #00B4D8
    dot_color = (16, 185, 129, 255)     # Verde #10B981

    # Título
    draw.text((18 * scale, 10 * scale), "Tendencia y Constancia Semanal de Asistencia (Últimas Clases)", font=f_titulo, fill=txt_color)

    if not lineas_data:
        draw.text(
            (int(w * 0.34), int(h * 0.55)),
            "Sin registros de asistencia de cursos",
            font=f_axis,
            fill=sub_color,
        )
        return img.resize(size, Image.Resampling.LANCZOS)

    # Área de trazado
    x_min, x_max = int(45 * scale), int(w - 25 * scale)
    y_min, y_max = int(40 * scale), int(h - 30 * scale)

    # Cuadrícula horizontal
    for pct in [50, 75, 100]:
        y_g = int(y_max - (pct / 100.0) * (y_max - y_min))
        draw.line([(x_min, y_g), (x_max, y_g)], fill=grid_color, width=scale)
        draw.text((14 * scale, y_g - 6 * scale), f"{pct}%", font=f_axis, fill=sub_color)

    # Línea umbral del 75% (mínimo de aprobación) en rojo
    y_75 = int(y_max - 0.75 * (y_max - y_min))
    draw.line([(x_min, y_75), (x_max, y_75)], fill=(239, 68, 68, 120), width=scale)
    draw.text((x_max - 65 * scale, y_75 - 12 * scale), "Mínimo 75%", font=f_axis, fill=(239, 68, 68, 220))

    # Puntos de la curva
    n = len(lineas_data)
    step_x = (x_max - x_min) / max(1, n - 1)
    pts = []

    for i, item in enumerate(lineas_data):
        pct = item.get("porcentaje")
        if pct is None:
            tot = item.get("total", 1) or 1
            asist = float(item.get("asistieron", 0) or 0)
            pct = int((asist / tot) * 100) if tot > 0 else 0
        pct = max(0, min(100, pct))
        px = int(x_min + i * step_x)
        py = int(y_max - (pct / 100.0) * (y_max - y_min))
        pts.append((px, py, pct, str(item.get("fecha", f"Día {i+1}"))))

    # Línea conectora
    for i in range(len(pts) - 1):
        x1, y1, _, _ = pts[i]
        x2, y2, _, _ = pts[i+1]
        draw.line([(x1, y1), (x2, y2)], fill=line_color, width=int(2.5 * scale))

    # Puntos y valores
    for px, py, pct, lbl in pts:
        r = int(4 * scale)
        draw.ellipse([px - r, py - r, px + r, py + r], fill=dot_color, outline=bg, width=scale)
        draw.text((px - 8 * scale, py - 14 * scale), f"{pct}%", font=f_pt, fill=txt_color)
        if len(lbl) > 6 and '-' in lbl:
            partes = lbl.split('-')
            lbl = f"{partes[-1]}/{partes[-2]}"
        draw.text((px - 10 * scale, y_max + 6 * scale), lbl[:6], font=f_axis, fill=sub_color)

    return img.resize(size, Image.Resampling.LANCZOS)


def generar_bytes_grafica_dona(datos, size=(400, 250)):
    """Retorna un BytesIO listo para ReportLab Image."""
    img = dibujar_grafica_dona(datos, size=size, is_dark=False)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def generar_bytes_grafica_barras(barras_data, size=(460, 250)):
    """Retorna un BytesIO listo para ReportLab Image."""
    img = dibujar_grafica_barras(barras_data, size=size, is_dark=False)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def generar_bytes_grafica_lineas(lineas_data, size=(880, 200)):
    """Retorna un BytesIO listo para ReportLab Image."""
    img = dibujar_grafica_lineas(lineas_data, size=size, is_dark=False)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf
