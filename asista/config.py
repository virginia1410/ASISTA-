"""Configuración central de REGISTRA: base de datos, horarios y paleta de colores.
Las credenciales sensibles se cargan automáticamente desde el archivo .env.
"""
import os
from datetime import time
from pathlib import Path
from dotenv import load_dotenv

# Directorio base del proyecto
import sys
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent

# Cargar variables de entorno desde el archivo .env si existe
_env_path = BASE_DIR / ".env"
if _env_path.exists():
    load_dotenv(_env_path)
else:
    load_dotenv()

# --- Conexión SQLite (Ruta relativa portable sin dependencias externas) ------
DB_FILE = os.getenv("DB_FILE", "database/asista.sqlite")
DB_PATH = (BASE_DIR / DB_FILE).resolve()
DB_CONFIG = {
    "database": str(DB_PATH),
    "host": "localhost"
}

# --- Ruta a ejecutable mysqldump (para respaldos .sql) -------------------------
MYSQLDUMP_PATH = os.getenv("MYSQLDUMP_PATH", "")

# --- Reglas de asistencia e institución (Turnos Mañana y Tarde) ---------------
INSTITUCION = os.getenv("INSTITUCION", "Unidad Educativa Prof. Aristóbulo Istúriz")

# Horarios base por turno institucional
HORARIOS_TURNO = {
    "Mañana": {
        "entrada_limite": time(7, 15),
        "salida_minima": time(12, 0)
    },
    "Tarde": {
        "entrada_limite": time(12, 45),
        "salida_minima": time(17, 30)
    }
}
HORA_LIMITE_ENTRADA = HORARIOS_TURNO["Mañana"]["entrada_limite"]
HORA_SALIDA_MINIMA = HORARIOS_TURNO["Mañana"]["salida_minima"]

# --- Control de sesión activa y RBAC ------------------------------------------
USUARIO_ID = None                   # id_usuario que firma registros y cierres
USUARIO_ROL = None                  # 'Administrador', 'Docente', 'Control', etc.
USUARIO_CARGO = None                # Cargo institucional (Docente, Vigilante, etc.)
USUARIO_NOMBRE = None               # Nombre para mostrar
USUARIO_ACTUAL = None               # Diccionario completo de sesión

CARGOS = ["Directivo", "Docente", "Administrativo", "Obrero", "Vigilante"]
MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto",
         "Septiembre", "Octubre", "Noviembre", "Diciembre"]
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]

# ==========================================
# PALETA DE COLORES ASISTA (Claro / Oscuro)
# ==========================================

# Barra lateral y encabezados principales (Navy Blue Tecnológico)
AZUL = ("#0F2042", "#0A1428")         # Azul marino oficial / Azul noche muy oscuro
AZUL_H = ("#0A1428", "#1E3A6D")       # Navy hover claro / Navy hover oscuro

# Botones de acción y resaltados (Turquesa / Cyan Tech)
NARANJA = ("#00B4D8", "#06B6D4")      # Turquesa oficial / Cyan brillante
NARANJA_H = ("#0096B7", "#00A8CC")    # Turquesa hover claro / Turquesa hover oscuro

# Fondos principales y tarjetas
BG = ("#F0F4F8", "#0A1428")           # Fondo Slate claro / Fondo Navy noche profundo
CARD = ("#FFFFFF", "#0F2042")         # Tarjetas blancas / Tarjetas Navy contenedor
BORDE = ("#D9E2EC", "#1E3A6D")        # Borde gris frío suave / Borde Navy sutil

# Textos
TEXTO = ("#0A192F", "#FFFFFF")        # Texto Navy oscuro en claro / Texto blanco en oscuro
SUAVE = ("#627D98", "#9FB3C8")        # Texto secundario gris frío / Texto secundario azul tenue

# Estados de asistencia (Puntualidad)
VERDE = ("#059669", "#10B981")        # Presente
VERDE_H = ("#047857", "#059669")
ROJO = ("#DC2626", "#EF4444")         # Ausente
ROJO_H = ("#B91C1C", "#DC2626")

# --- Validador riguroso de contraseñas ---------------------------------------
def validar_password_rigurosa(password: str) -> tuple[bool, str]:
    """Valida los requisitos rigurosos de seguridad para contraseñas de Asista:
    - Mínimo 8 caracteres
    - Al menos una letra mayúscula
    - Al menos una letra minúscula
    - Al menos un número
    - Al menos un carácter especial (@$!%*?&#._-)
    """
    import re
    if not password or len(password) < 8:
        return False, "La contraseña debe tener al menos 8 caracteres de longitud."
    if not re.search(r"[A-Z]", password):
        return False, "La contraseña debe incluir al menos una letra MAYÚSCULA."
    if not re.search(r"[a-z]", password):
        return False, "La contraseña debe incluir al menos una letra minúscula."
    if not re.search(r"[0-9]", password):
        return False, "La contraseña debe incluir al menos un número (0-9)."
    if not re.search(r"[@$!%*?&#._\-+=~^/\\|<>{}\[\]():;]", password):
        return False, "La contraseña debe incluir al menos un símbolo especial (ej: @$!%*?&#._-)."
    return True, ""
