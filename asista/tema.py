"""Tema visual de Asista: paleta institucional tecnológico (Navy Blue / Turquesa / Blanco).
Tipografías, logo y banner. Para cambiar colores o el nombre del sistema, edite solo este archivo."""
import os

from PIL import Image, ImageDraw

# --- Identidad ----------------------------------------------------------------
NOMBRE_SISTEMA = "Asista"
LEMA = "CONTROL DE ASISTENCIAS"

# --- Colores de marca Institucional (Tecnología y Academia) -------------------
NAVY = "#0F2042"          # Azul marino institucional profundo
NAVY_OSC = "#0A1428"      # Azul noche oscuro (para contrastes, degradados)
TURQUESA = "#00B4D8"      # Turquesa / Cyan vibrante de tecnología
TURQUESA_OSC = "#0096B7"  # Turquesa hover
BLANCO = "#FFFFFF"

# Compatibilidad con módulos existentes que importan MORADO o NARANJA
MORADO = NAVY
MORADO_OSC = NAVY_OSC
NARANJA = TURQUESA

# Pares (modo claro, modo oscuro) para CustomTkinter
PRIMARIO = (NAVY, "#1A3668")
PRIMARIO_H = (NAVY_OSC, "#244A8F")
ACENTO = (TURQUESA, "#06B6D4")
ACENTO_H = (TURQUESA_OSC, "#00A8CC")
OK = ("#0F9F6E", "#34D399")
OK_H = ("#0B7D56", "#10B981")
AVISO = ("#E8890C", "#FBBF24")
BG = ("#F0F4F8", "#0A1428")            # Fondo de la aplicación (Slate claro / Navy oscuro)
CARD = ("#FFFFFF", "#0F2042")          # Tarjetas (Blanco puro / Navy Blue contenedor)
BORDE = ("#D9E2EC", "#1E3A6D")         # Bordes sutiles
TEXTO = ("#0A192F", "#F0F4F8")         # Texto de alto contraste
SUAVE = ("#627D98", "#9FB3C8")         # Texto secundario
SUAVE_BG = ("#E2E8F0", "#162C55")      # Campos, chips, fondos tenues
ESTADO_COLOR = {"Presente": OK, "Retraso": AVISO, "Salida Temprana": AVISO, "Ausente": ("#DC2626", "#EF4444")}

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
def banner_imagen(ancho, alto, radio=24):
    s = 2
    W, H = ancho * s, alto * s
    base = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(base)
    c1, c2 = (15, 32, 66), (10, 20, 40)  # #0F2042 (Navy) a #0A1428 (Navy Profundo)
    for x in range(W):
        t = x / max(W - 1, 1)
        d.line([(x, 0), (x, H)], fill=tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3)))
    capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    cd = ImageDraw.Draw(capa)
    cd.ellipse([W * 0.55, -H * 0.9, W * 1.05, H * 0.9], fill=(255, 255, 255, 25))
    cd.ellipse([W * 0.86, H * 0.45, W * 1.2, H * 1.6], fill=(0, 180, 216, 140))  # Destello turquesa tecnológico
    base = Image.alpha_composite(base.convert("RGBA"), capa)
    marca = logo_check("#FFFFFF", int(H * 0.60), 38)
    base.alpha_composite(marca, (max(0, W - marca.width - int(W * 0.07)), (H - marca.height) // 2))
    mascara = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mascara).rounded_rectangle([0, 0, W - 1, H - 1], radius=radio * s, fill=255)
    base.putalpha(mascara)
    return base.resize((ancho, alto), Image.LANCZOS)
