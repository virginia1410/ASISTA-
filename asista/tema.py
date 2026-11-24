"""Tema visual de Asista: paleta institucional tecnológico (Navy Blue / Turquesa / Blanco).
Tipografías, logo y banner. Para cambiar colores o el nombre del sistema, edite solo este archivo."""
import os

from PIL import Image, ImageDraw

# --- Identidad ----------------------------------------------------------------
NOMBRE_SISTEMA = "Asista"
LEMA = "CONTROL DE ASISTENCIAS"

# --- Paletas centralizadas de marca (modo claro / oscuro) ----------------------
PALETA_CLARO = {
    "bg": "#F7F9FC",
    "card": "#FFFFFF",
    "surface": "#EFF3F8",
    "border": "#DFE6EF",
    "text": "#040444",
    "muted": "#667085",
    "primary": "#040444",
    "primary_hover": "#08082D",
    "accent": "#56E1E8",
    "accent_hover": "#35C8D1",
    "accent_soft": "#E5F8FA",
    "accent_text": "#07585D",
    "danger": "#70283D",
    "danger_bg": "#F5EAEE",
    "danger_text": "#70283D",
    "brown": "#72543F",
    "brown_bg": "#F2ECE7",
    "white": "#FFFFFF",
    "sidebar": "#040444",
    "sidebar_surface": "#10104C",
    "sidebar_hover": "#171750",
    "sidebar_text": "#F3EFE8",
    "banner_start": "#FFFFFF",
    "banner_end": "#EEF3F8",
    "table_zebra": "#F5F7FA",
}

PALETA_OSCURO = {
    "bg": "#040444",
    "card": "#0D1538",
    "surface": "#111D49",
    "border": "#26385E",
    "text": "#FFFFFF",
    "muted": "#B9C4D8",
    "primary": "#040444",
    "primary_hover": "#08082D",
    "accent": "#56E1E8",
    "accent_hover": "#35C8D1",
    "accent_soft": "#17384A",
    "accent_text": "#56E1E8",
    "danger": "#70283D",
    "danger_bg": "#39202D",
    "danger_text": "#E6C7D0",
    "brown": "#80664F",
    "brown_bg": "#30291F",
    "white": "#FFFFFF",
    "sidebar": "#03032F",
    "sidebar_surface": "#101A43",
    "sidebar_hover": "#1A2850",
    "sidebar_text": "#F3EFE8",
    "banner_start": "#040444",
    "banner_end": "#08082D",
    "table_zebra": "#111D49",
}


def colores_modo(token, oscuro=False):
    """Obtiene un token visual concreto para Canvas y estilos ttk."""
    paleta = PALETA_OSCURO if oscuro else PALETA_CLARO
    return paleta[token]


def _par(token):
    return PALETA_CLARO[token], PALETA_OSCURO[token]


NAVY = PALETA_CLARO["primary"]
NAVY_OSC = PALETA_OSCURO["primary_hover"]
TURQUESA = PALETA_CLARO["accent"]
TURQUESA_OSC = PALETA_OSCURO["accent_hover"]
BURDEOS = PALETA_CLARO["danger"]
BURDEOS_OSC = PALETA_OSCURO["danger"]
BLANCO = PALETA_CLARO["white"]
MARRON = _par("brown")
MARRON_BG = _par("brown_bg")
AVISO_BG = _par("danger_bg")
AVISO_TEXTO = _par("danger_text")
ACENTO_TEXTO = _par("accent_text")
SIDEBAR = _par("sidebar")
SIDEBAR_SUPERFICIE = _par("sidebar_surface")
SIDEBAR_HOVER = _par("sidebar_hover")
SIDEBAR_TEXTO = _par("sidebar_text")

# Compatibilidad con módulos que aún usan los nombres históricos.
MORADO = _par("primary")
MORADO_OSC = _par("primary_hover")
NARANJA = _par("accent")
NARANJA_H = _par("accent_hover")

PRIMARIO = _par("primary")
PRIMARIO_H = _par("primary_hover")
ACENTO = _par("accent")
ACENTO_H = _par("accent_hover")
ACENTO_SUAVE = _par("accent_soft")
OK = ACENTO
OK_H = ACENTO_H
AVISO = _par("danger")
BG = _par("bg")
CARD = _par("card")
BORDE = _par("border")
TEXTO = _par("text")
SUAVE = _par("muted")
SUAVE_BG = _par("surface")
ESTADO_COLOR = {
    "Presente": OK,
    "Retraso": AVISO,
    "Salida Temprana": AVISO,
    "Ausente": AVISO,
}

# --- Tipografías (Georgia da el toque editorial/lujo a los títulos) -----------
F_TITULO = "Georgia"
F_TEXTO = "Segoe UI"

# --- Logo (check de Asista vectorizado: se dibuja en cualquier color/tamaño) --
ASPECTO = 1.368
POLIGONOS = [
    [(0.224, 0.489), (0.303, 0.675), (0.379, 0.499), (0.375, 0.488)],
    [(0.996, 0.004), (0.848, 0.004), (0.514, 0.801), (0.509, 0.8), (0.493, 0.769), (0.418, 0.948),
     (0.437, 0.996), (0.584, 0.995)],
    [(0.773, 0.002), (0.623, 0.005), (0.288, 0.803), (0.151, 0.488), (0.0, 0.488), (0.215, 0.997),
     (0.362, 0.994), (0.774, 0.008)],
]


def logo_check(color="#FFFFFF", alto=64, opacidad=255):
    ancho, s = round(alto * ASPECTO), 4
    mascara = Image.new("L", (ancho * s, alto * s), 0)
    d = ImageDraw.Draw(mascara)
    for pts in POLIGONOS:
        d.polygon([(x * ancho * s, y * alto * s) for x, y in pts], fill=opacidad)
    img = Image.new("RGBA", (ancho, alto), color)
    img.putalpha(mascara.resize((ancho, alto), Image.LANCZOS))
    return img


# --- Identidad institucional ---------------------------------------------------
import sys
if getattr(sys, "frozen", False):
    _base_assets = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    RUTA_ASSETS = os.path.join(_base_assets, "assets")
    if not os.path.exists(RUTA_ASSETS):
        RUTA_ASSETS = os.path.join(os.path.dirname(sys.executable), "assets")
else:
    RUTA_ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

RUTA_ICONO = os.path.join(RUTA_ASSETS, "asista_icon.ico")


def logo_institucion(alto=56, ancho_max=200, modo=None):
    """Carga el escudo institucional con transparencia limpia o, como respaldo, el logo de Asista."""
    for nombre in (
        "escudo_institucion_tight.png",
        "escudo_institucion_tight.jpg",
        "escudo_institucion_clean.png",
        "escudo institucion.png",
        "logo_institucion.png",
    ):
        ruta = os.path.join(RUTA_ASSETS, nombre)
        if os.path.exists(ruta):
            try:
                img = Image.open(ruta).convert("RGBA")
                esc = min(alto / img.height, ancho_max / img.width)
                img = img.resize((max(1, round(img.width * esc)), max(1, round(img.height * esc))),
                                 Image.LANCZOS)
                if modo == "blanco":
                    r, g, b, a = img.split()
                    blanco = Image.new("RGBA", img.size, (255, 255, 255, 0))
                    blanco.paste(Image.new("RGB", img.size, (255, 255, 255)), mask=a)
                    blanco.putalpha(a)
                    img = blanco
                return img
            except Exception:  # noqa: BLE001
                return None
    return None


def logo_asista(alto=38, ancho_max=180, modo="blanco"):
    """Carga el logo oficial tipográfico de Asista (por defecto en blanco sobre fondo oscuro)."""
    archivos = [
        "logo_asista_blanco_transp.png" if modo == "blanco" else "logo_asista_color_transp.png",
        "logo_asista_blanco.png",
        "logo_blanco.png" if modo == "blanco" else "logo.png",
        "logo.png"
    ]
    for nombre in archivos:
        ruta = os.path.join(RUTA_ASSETS, nombre)
        if os.path.exists(ruta):
            try:
                img = Image.open(ruta).convert("RGBA")
                esc = min(alto / img.height, ancho_max / img.width)
                img = img.resize((max(1, round(img.width * esc)), max(1, round(img.height * esc))),
                                 Image.LANCZOS)
                if modo == "blanco" and "blanco" not in nombre.lower():
                    r, g, b, a = img.split()
                    blanco = Image.new("RGBA", img.size, (255, 255, 255, 0))
                    blanco.paste(Image.new("RGB", img.size, (255, 255, 255)), mask=a)
                    blanco.putalpha(a)
                    img = blanco
                return img
            except Exception:
                return None
    return logo_check("#FFFFFF" if modo == "blanco" else TURQUESA, alto)


# --- Banner del panel: degradado Navy Blue institucional, destellos y marca de agua
def banner_imagen(ancho, alto, radio=24, oscuro=False):
    s = 2
    W, H = ancho * s, alto * s
    paleta = PALETA_OSCURO if oscuro else PALETA_CLARO
    c1 = tuple(int(paleta["banner_start"][i:i + 2], 16) for i in (1, 3, 5))
    c2 = tuple(int(paleta["banner_end"][i:i + 2], 16) for i in (1, 3, 5))
    base = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(base)
    for x in range(W):
        t = x / max(W - 1, 1)
        d.line([(x, 0), (x, H)], fill=tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3)))
    capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    cd = ImageDraw.Draw(capa)
    cd.ellipse([W * 0.55, -H * 0.9, W * 1.05, H * 0.9],
               fill=(255, 255, 255, 20 if not oscuro else 12))
    cd.ellipse([W * 0.86, H * 0.45, W * 1.2, H * 1.6], fill=(86, 225, 232, 30))
    base = Image.alpha_composite(base.convert("RGBA"), capa)
    color_marca = "#040444" if not oscuro else "#FFFFFF"
    marca = logo_check(color_marca, int(H * 0.60), 18 if not oscuro else 38)
    base.alpha_composite(marca, (max(0, W - marca.width - int(W * 0.07)), (H - marca.height) // 2))
    mascara = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mascara).rounded_rectangle([0, 0, W - 1, H - 1], radius=radio * s, fill=255)
    base.putalpha(mascara)
    return base.resize((ancho, alto), Image.LANCZOS)
