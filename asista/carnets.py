"""Generación de carnets institucionales con diseño Aesthetic Luxury y código serial (Code 128 exclusivo).
Diseñado para la U.E.P. Prof. Aristóbulo Istúriz con soporte para fotografía de perfil y exportación en PDF.
Fondo blanco, paleta corporativa Navy & Turquesa, foto de perfil centrada y código de barras serial con cédula.
"""
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image, ImageDraw, ImageFont, ImageOps
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import Image as PDFImage, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from config import BASE_DIR, INSTITUCION

# Paleta Asista Aesthetic Luxury (Fondo Blanco / Navy / Turquesa)
BLANCO = (255, 255, 255, 255)
NAVY_OSCURO = (10, 20, 40, 255)       # #0A1428
NAVY_MEDIO = (15, 32, 66, 255)        # #0F2042
TURQUESA = (0, 180, 216, 255)         # #00B4D8
TURQUESA_OSCURO = (0, 130, 170, 255)  # #0082AA
TURQUESA_SUAVE = (240, 249, 255, 255) # #F0F9FF
GRIS_BORDE = (226, 232, 240, 255)     # #E2E8F0
GRIS_TEXTO = (100, 116, 139, 255)     # #64748B
GRIS_FONDO = (248, 250, 252, 255)     # #F8FAFC

from tema import RUTA_ASSETS as TEMA_RUTA_ASSETS

# Dimensiones carnet ReportLab
ANCHO_CARNET = 5.8 * cm
ALTO_CARNET = 8.92 * cm
RUTA_ASSETS = Path(TEMA_RUTA_ASSETS)
RUTA_FOTOS = BASE_DIR / "fotos_perfil"
RUTA_FOTOS.mkdir(parents=True, exist_ok=True)


def _obtener_fuente(size=14, bold=False):
    """Carga fuente tipográfica del sistema con respaldo seguro."""
    fuentes_sys = [
        "C:\\Windows\\Fonts\\segoeuib.ttf" if bold else "C:\\Windows\\Fonts\\segoeui.ttf",
        "C:\\Windows\\Fonts\\arialbd.ttf" if bold else "C:\\Windows\\Fonts\\arial.ttf",
    ]
    for ruta in fuentes_sys:
        if Path(ruta).exists():
            try:
                return ImageFont.truetype(ruta, size)
            except Exception:
                pass
    return ImageFont.load_default()


# Patrones oficiales Code 128 (Subset B) - 100% Python puro sin librerías externas
_PATRONES_CODE128 = [
    '212222', '222122', '222221', '121223', '121322', '131222', '122213', '122312', '132212', '221213',
    '221312', '231212', '112232', '122132', '122231', '113222', '123122', '123221', '223211', '221132',
    '221231', '213212', '223112', '312131', '311222', '321122', '321221', '312212', '322112', '322211',
    '212123', '212321', '232121', '111323', '131123', '131321', '112313', '132113', '132311', '211313',
    '231113', '231311', '112133', '112331', '132131', '113123', '113321', '133121', '313121', '211331',
    '231131', '213113', '213311', '213131', '311123', '311321', '331121', '312113', '312311', '332111',
    '314111', '221411', '431111', '111224', '111422', '121124', '121421', '141122', '141221', '112214',
    '112412', '122114', '122411', '142112', '142211', '241211', '221114', '413111', '241112', '134111',
    '111242', '121142', '121241', '114212', '124112', '124211', '411212', '421112', '421211', '212141',
    '214121', '412121', '111143', '111341', '131141', '114113', '114311', '411113', '411311', '113141',
    '114131', '311141', '411131', '211412', '211214', '211232', '2331112'
]


def generar_codigo_barras_128(texto, altura=68, modulo_ancho=2):
    """Genera imagen PIL del código de barras Code 128 (Subset B) nativamente."""
    texto_limpio = "".join(c for c in str(texto) if 32 <= ord(c) <= 126) or "000000"
    valores = [104]  # Start Code B
    for c in texto_limpio:
        valores.append(ord(c) - 32)
    chk = valores[0]
    for i, v in enumerate(valores[1:], 1):
        chk += i * v
    valores.append(chk % 103)
    valores.append(106)  # Stop Code

    modulos = []
    for val in valores:
        pat = _PATRONES_CODE128[val]
        barra = True
        for d in pat:
            w = int(d)
            modulos.extend([1 if barra else 0] * w)
            barra = not barra

    ancho_total = len(modulos) * modulo_ancho
    img_bc = Image.new("RGBA", (ancho_total, altura), (255, 255, 255, 255))
    draw_bc = ImageDraw.Draw(img_bc)
    for x_idx, es_barra in enumerate(modulos):
        if es_barra:
            x_ini = x_idx * modulo_ancho
            draw_bc.rectangle([x_ini, 0, x_ini + modulo_ancho - 1, altura], fill=(15, 32, 66, 255))
    return img_bc


def renderizar_imagen_carnet_aesthetic(persona_dict):
    """
    Construye la tarjeta de carnet VIP en alta resolución (650 x 1000 px):
    - Fondo blanco limpio y sofisticado.
    - Acabados y acentos en paleta corporativa Navy (#0F2042) y Turquesa (#00B4D8).
    - Escudo Institucional oficial y membrete de la U.E.P. Prof. Aristóbulo Istúriz.
    - Cinta esquinera de estatus ('ACTIVO').
    - Banner estilizado del Rol (ESTUDIANTE / DOCENTE / PERSONAL).
    - Marco central de fotografía de perfil en alta resolución.
    - Placa horizontal para el Nombre Completo.
    - Código de Barras Serial exclusivo Code 128 (sin QR) y debajo el número de cédula.
    - Sin datos de turno ni acceso.
    """
    W, H = 650, 1000
    img = Image.new("RGBA", (W, H), BLANCO)
    draw = ImageDraw.Draw(img)

    # 1. Borde exterior doble Luxury (Navy + Turquesa)
    draw.rounded_rectangle([14, 14, W - 14, H - 14], radius=24, outline=NAVY_MEDIO, width=3)
    draw.rounded_rectangle([20, 20, W - 20, H - 20], radius=18, outline=TURQUESA, width=2)

    # Ranura superior de lanyard
    draw.rounded_rectangle([(W // 2) - 45, 24, (W // 2) + 45, 34], radius=5, fill=(240, 244, 248, 255), outline=NAVY_MEDIO, width=1)

    # Cinta esquinera "ACTIVO" superior derecha
    f_ribbon = _obtener_fuente(10, bold=True)
    draw.polygon([(W - 130, 14), (W - 14, 130), (W - 14, 102), (W - 102, 14)], fill=TURQUESA)
    draw.text((W - 82, 35), "ACTIVO", font=f_ribbon, fill=NAVY_OSCURO)

    # 2. Encabezado con Escudo Institucional y Membrete Oficial
    ruta_escudo = RUTA_ASSETS / "escudo_institucion_tight.png"
    if not ruta_escudo.exists():
        ruta_escudo = RUTA_ASSETS / "escudo institucion.png"
    
    if ruta_escudo.exists():
        try:
            esc = Image.open(ruta_escudo).convert("RGBA")
            esc.thumbnail((68, 68), Image.Resampling.LANCZOS)
            img.paste(esc, (42, 46), mask=esc)
        except Exception:
            pass

    f_sub_inst = _obtener_fuente(10, bold=True)
    f_nom_inst = _obtener_fuente(15, bold=True)
    f_cod_inst = _obtener_fuente(11, bold=True)

    draw.text((120, 48), "REPÚBLICA BOLIVARIANA DE VENEZUELA", font=f_sub_inst, fill=GRIS_TEXTO)
    draw.text((120, 66), "U.E.P. PROF. ARISTÓBULO ISTÚRIZ", font=f_nom_inst, fill=NAVY_OSCURO)
    draw.text((120, 92), "CÓD. PD31212303 · CABIMAS, ESTADO ZULIA", font=f_cod_inst, fill=TURQUESA_OSCURO)

    # Línea divisoria de elegancia
    draw.line([40, 126, W - 40, 126], fill=TURQUESA, width=2)
    draw.line([40, 129, W - 40, 129], fill=NAVY_MEDIO, width=1)

    # 3. Banner del Título del Rol (ESTUDIANTE / DOCENTE / ADMINISTRATIVO)
    tipo = str(persona_dict.get("tipo_persona") or "ESTUDIANTE").upper()
    draw.rounded_rectangle([45, 142, W - 45, 192], radius=12, fill=NAVY_MEDIO, outline=TURQUESA, width=2)
    
    f_tipo = _obtener_fuente(24, bold=True)
    bbox_tipo = draw.textbbox((0, 0), tipo, font=f_tipo)
    w_t = bbox_tipo[2] - bbox_tipo[0]
    draw.text(((W - w_t) // 2, 148), tipo, font=f_tipo, fill=BLANCO)

    # 4. Marco Central de Fotografía de Perfil (Amplia y Centrada)
    fw, fh = 360, 390
    fx1 = (W - fw) // 2
    fy1 = 208
    fx2, fy2 = fx1 + fw, fy1 + fh

    # Bisel doble de fotografía
    draw.rounded_rectangle([fx1 - 5, fy1 - 5, fx2 + 5, fy2 + 5], radius=18, outline=TURQUESA, width=2)
    draw.rounded_rectangle([fx1, fy1, fx2, fy2], radius=14, fill=GRIS_FONDO, outline=NAVY_MEDIO, width=2)

    # Cargar y ajustar foto de la persona
    foto_nombre = persona_dict.get("foto")
    foto_cargada = False
    if foto_nombre:
        p_foto = RUTA_FOTOS / Path(foto_nombre).name
        if p_foto.exists():
            try:
                with Image.open(p_foto) as im_f:
                    f_rgb = ImageOps.exif_transpose(im_f).convert("RGBA")
                    f_fit = ImageOps.fit(f_rgb, (fw, fh), method=Image.Resampling.LANCZOS)
                    masc = Image.new("L", (fw, fh), 0)
                    ImageDraw.Draw(masc).rounded_rectangle([0, 0, fw, fh], radius=14, fill=255)
                    img.paste(f_fit, (fx1, fy1), mask=masc)
                    foto_cargada = True
            except Exception:
                pass

    if not foto_cargada:
        f_sin = _obtener_fuente(16, bold=True)
        draw.text((fx1 + 80, fy1 + 175), "FOTOGRAFÍA\nINSTITUCIONAL", font=f_sin, fill=GRIS_TEXTO, align="center")

    # Badge de Grado / Sección / Especialidad sobre la base de la foto (si existe)
    detalle = str(persona_dict.get("detalle") or "").upper().strip()
    # Si tiene turno en detalle, limpiarlo
    for palabra_turno in ["- MAÑANA", "- TARDE", "MAÑANA", "TARDE"]:
        detalle = detalle.replace(palabra_turno, "").strip()
    if detalle.endswith("-"):
        detalle = detalle[:-1].strip()

    if detalle:
        f_badge = _obtener_fuente(13, bold=True)
        bbox_d = draw.textbbox((0, 0), detalle, font=f_badge)
        wd = bbox_d[2] - bbox_d[0]
        bw = max(wd + 34, 160)
        bx1 = (W - bw) // 2
        draw.rounded_rectangle([bx1, fy2 - 18, bx1 + bw, fy2 + 16], radius=8, fill=NAVY_MEDIO, outline=TURQUESA, width=2)
        draw.text(((W - wd) // 2, fy2 - 13), detalle, font=f_badge, fill=BLANCO)

    # 5. Placa de Nombre Completo
    nom = f"{persona_dict.get('nombre', '')} {persona_dict.get('apellido', '')}".strip().upper()
    if len(nom) > 28:
        nom = nom[:26] + "…"
    
    py_nom = fy2 + 28
    draw.rounded_rectangle([45, py_nom, W - 45, py_nom + 52], radius=12, fill=TURQUESA_SUAVE, outline=NAVY_MEDIO, width=2)
    f_nom = _obtener_fuente(20, bold=True)
    bbox_nom = draw.textbbox((0, 0), nom, font=f_nom)
    w_n = bbox_nom[2] - bbox_nom[0]
    draw.text(((W - w_n) // 2, py_nom + 12), nom, font=f_nom, fill=NAVY_OSCURO)

    # 6. SECCIÓN DE CÓDIGO SERIAL EXCLUSIVO (CODE 128 NATIVO CENTRADO)
    serial = str(persona_dict.get("cedula") or "").strip()
    
    py_bar = py_nom + 66
    draw.rounded_rectangle([45, py_bar, W - 45, H - 38], radius=16, fill=BLANCO, outline=TURQUESA, width=2)

    # 6.1 Generación de la Barra Serial Code 128 (100% nativa)
    barcode_insertado = False
    try:
        raw_bc = generar_codigo_barras_128(serial, altura=70, modulo_ancho=2)
        ancho_bc = min(500, max(380, raw_bc.width * 2))
        scaled_bc = raw_bc.resize((ancho_bc, 68), Image.Resampling.NEAREST)
        bx = (W - ancho_bc) // 2
        by = py_bar + 18
        img.paste(scaled_bc, (bx, by))
        barcode_insertado = True
    except Exception:
        pass

    if not barcode_insertado:
        draw.rectangle([62, py_bar + 18, W - 62, py_bar + 86], fill=(240, 240, 240, 255))

    # Número serial / cédula directamente centrado debajo de la barra serial
    ced_mostrar = f"SERIAL: {serial}" if not serial.upper().startswith(("V-", "E-", "J-", "G-", "V", "E")) else f"SERIAL: {serial}"
    f_ced = _obtener_fuente(22, bold=True)
    bbox_c = draw.textbbox((0, 0), ced_mostrar, font=f_ced)
    w_c = bbox_c[2] - bbox_c[0]
    draw.text(((W - w_c) // 2, py_bar + 98), ced_mostrar, font=f_ced, fill=NAVY_OSCURO)

    # Leyenda legal e institucional inferior
    f_leg = _obtener_fuente(10, bold=False)
    leg_str = "Documento Oficial de Identificación · ASISTA"
    bbox_l = draw.textbbox((0, 0), leg_str, font=f_leg)
    w_l = bbox_l[2] - bbox_l[0]
    draw.text(((W - w_l) // 2, H - 56), leg_str, font=f_leg, fill=GRIS_TEXTO)

    return img


def _crear_carnet_flowable(persona_dict):
    """Genera la imagen del carnet y la convierte en un Flowable de ReportLab."""
    img_carnet = renderizar_imagen_carnet_aesthetic(persona_dict)
    buffer = BytesIO()
    img_carnet.save(buffer, format="PNG", optimize=True)
    buffer.seek(0)
    return PDFImage(buffer, width=ANCHO_CARNET, height=ALTO_CARNET)


def generar_carnets_seccion(db, id_seccion, ruta_guardar):
    """Genera hoja de carnets Aesthetic Luxury para todos los estudiantes activos de una sección."""
    alumnos = db.fetch_all(
        """
        SELECT p.id_persona, p.cedula, p.nombre, p.apellido, p.tipo_persona, p.foto,
               s.grado_ano, s.seccion_letra,
               CONCAT(s.grado_ano, '° \"', s.seccion_letra, '\"') AS detalle
          FROM estudiante e
          JOIN persona p ON p.id_persona = e.id_persona
          JOIN seccion s ON s.id_seccion = e.id_seccion
         WHERE e.id_seccion = %s AND p.activo = 1
         ORDER BY p.apellido, p.nombre
        """,
        (id_seccion,),
    )
    if not alumnos:
        raise UserWarning("No hay estudiantes registrados en esta sección.")

    ancho_espacio = 0.4 * cm
    filas = []
    widgets = [_crear_carnet_flowable(alumno) for alumno in alumnos]
    
    # 3 carnets por fila en hoja carta
    for inicio in range(0, len(widgets), 3):
        grupo = widgets[inicio:inicio + 3]
        fila = []
        for indice in range(3):
            fila.append(grupo[indice] if indice < len(grupo) else "")
            if indice < 2:
                fila.append(Spacer(ancho_espacio, 1))
        filas.append(fila)

    anchos = [ANCHO_CARNET, ancho_espacio, ANCHO_CARNET, ancho_espacio, ANCHO_CARNET]
    rejilla = Table(filas, colWidths=anchos)
    rejilla.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))
    
    documento = SimpleDocTemplate(
        str(ruta_guardar),
        pagesize=letter,
        leftMargin=1.1 * cm,
        rightMargin=1.1 * cm,
        topMargin=1.2 * cm,
        bottomMargin=1.2 * cm,
        title="Carnets Institucionales ASISTA",
    )
    documento.build([rejilla])
    return ruta_guardar


def generar_carnets_cohorte(db, id_cohorte, ruta_guardar):
    """Genera hoja de carnets Aesthetic Luxury para todos los participantes activos de un curso sabatino."""
    participantes = db.fetch_all(
        """
        SELECT p.id_persona, p.cedula, p.nombre, p.apellido, p.tipo_persona, p.foto,
               c.nombre AS detalle
          FROM matricula m
          JOIN persona p ON p.id_persona = m.id_persona
          JOIN cohorte ch ON ch.id_cohorte = m.id_cohorte
          JOIN curso c ON c.id_curso = ch.id_curso
         WHERE m.id_cohorte = %s AND m.estado <> 'Retirado' AND p.activo = 1
         ORDER BY p.apellido, p.nombre
        """,
        (id_cohorte,),
    )
    if not participantes:
        raise UserWarning("No hay participantes matriculados en este curso sabatino.")

    ancho_espacio = 0.4 * cm
    filas = []
    widgets = [_crear_carnet_flowable(part) for part in participantes]

    # 3 carnets por fila en hoja carta
    for inicio in range(0, len(widgets), 3):
        grupo = widgets[inicio:inicio + 3]
        fila = []
        for indice in range(3):
            fila.append(grupo[indice] if indice < len(grupo) else "")
            if indice < 2:
                fila.append(Spacer(ancho_espacio, 1))
        filas.append(fila)

    anchos = [ANCHO_CARNET, ancho_espacio, ANCHO_CARNET, ancho_espacio, ANCHO_CARNET]
    rejilla = Table(filas, colWidths=anchos)
    rejilla.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))

    documento = SimpleDocTemplate(
        str(ruta_guardar),
        pagesize=letter,
        leftMargin=1.1 * cm,
        rightMargin=1.1 * cm,
        topMargin=1.2 * cm,
        bottomMargin=1.2 * cm,
        title="Carnets Cursos Sabatinos ASISTA",
    )
    documento.build([rejilla])
    return ruta_guardar


def generar_carnet_individual(db, id_persona, ruta_guardar):
    """Genera el carnet individual con fondo blanco, barra serial, QR y número de cédula."""
    persona = db.fetch_one(
        """
        SELECT p.id_persona, p.cedula, p.nombre, p.apellido, p.tipo_persona, p.foto,
               COALESCE(
                   (SELECT c.nombre FROM matricula m JOIN cohorte ch ON ch.id_cohorte = m.id_cohorte JOIN curso c ON c.id_curso = ch.id_curso WHERE m.id_persona = p.id_persona AND m.estado <> 'Retirado' LIMIT 1),
                   (SELECT CONCAT(s.grado_ano, '° \"', s.seccion_letra, '\"') FROM estudiante e JOIN seccion s ON s.id_seccion = e.id_seccion WHERE e.id_persona = p.id_persona LIMIT 1),
                   pe.cargo,
                   'Participante Comunitario'
               ) AS detalle
          FROM persona p
          LEFT JOIN personal pe ON pe.id_persona = p.id_persona
         WHERE p.id_persona = %s
        """,
        (id_persona,),
    )
    if not persona:
        raise UserWarning("No se encontró la persona seleccionada.")

    widget = _crear_carnet_flowable(persona)
    
    tabla = Table([[widget]], colWidths=[ANCHO_CARNET])
    tabla.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    documento = SimpleDocTemplate(
        str(ruta_guardar),
        pagesize=letter,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        title=f"Carnet - {persona.get('cedula', '')}",
    )
    documento.build([tabla])
    return ruta_guardar
