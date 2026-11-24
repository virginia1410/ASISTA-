"""Servicio de Fondo Autónomo para Asista:
- Servidor Web de Marcaje Móvil (HTTP desde 8080, con alternativas limitadas)
- HTTPS en 8443 para habilitar la cámara móvil
- Registro móvil de asistencias con autenticación y permisos por rol/cohorte
- Ejecución automática del cierre diario institucional a las 11:59 PM
- Permanece activo 24/7 incluso si la ventana principal de Asista está cerrada.
"""
import errno
import http.server
import ipaddress
import ssl
import json
import logging
import os
from pathlib import Path
import socket
import socketserver
import subprocess
import secrets
import sys
import threading
import time
import urllib.error
import urllib.request
from datetime import date, datetime
from urllib.parse import parse_qs, urlparse


def resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    base_path = Path(__file__).resolve().parent
    return str(base_path / relative_path)


# Asegurar importación de módulos locales
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import config
from db import Database, resolver_turno_persona
from tema import PALETA_CLARO, PALETA_OSCURO

# Configuración de logs
LOG_FILE = BASE_DIR / "servicio_asista.log"
logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

HOST_SERVICIO = "0.0.0.0"
PUERTO_SERVICIO = int(os.getenv("ASISTA_PORT", 8080))
PUERTOS_HTTP_ALTERNATIVOS = 10
PUERTO_HTTPS = 8443
PUERTO_HTTP_ACTIVO = None
PUERTO_HTTPS_ACTIVO = None
IPS_CERTIFICADO_SSL = set()
_HILO_HTTPS = None
_LOCK_INICIO_SERVICIO = threading.Lock()
_EVENTO_SERVICIO_LISTO = threading.Event()
_HILO_SERVICIO = None
_ERROR_INICIO_SERVICIO = None
db_instancia = Database()
API_SESSION_TTL = 8 * 60 * 60
API_LOGIN_WINDOW = 15 * 60
API_LOGIN_MAX_ATTEMPTS = 5
API_ADMIN_ROLES = frozenset(("Administrador", "Directivo"))
API_SESSIONS = {}
API_LOGIN_ATTEMPTS = {}
API_AUTH_LOCK = threading.Lock()

# Directorio de Assets
RUTA_ASSETS = Path(resource_path("assets"))


def render_mobile_html(template):
    static_logo_url = "/static/img/escudo_institucion.png"
    html = template.replace(
        "{{ url_for('static', filename='img/logo.png') }}", static_logo_url
    )
    for mode_name, palette in (("CLARO", PALETA_CLARO), ("OSCURO", PALETA_OSCURO)):
        for token, color in palette.items():
            html = html.replace(f"__ASISTA_{mode_name}_{token.upper()}__", color)
    return html.replace("</head>", f"<script>{MOBILE_AUTH_SCRIPT}</script></head>", 1)


MOBILE_AUTH_SCRIPT = r"""
(() => {
    const nativeFetch = window.fetch.bind(window);
    const tokenKey = 'asista_api_token';

    window.verificarEstadoAuth = function() {
        const token = sessionStorage.getItem(tokenKey);
        const userJson = sessionStorage.getItem('asista_api_user');
        const vLogin = document.getElementById('vistaLoginMovil');
        const vCambio = document.getElementById('vistaCambioClaveMovil');
        const vDash = document.getElementById('vistaDashboardMovil');

        if (!vLogin || !vDash) return;

        if (!token || !userJson) {
            vLogin.style.display = 'block';
            vDash.style.display = 'none';
            if (vCambio) vCambio.style.display = 'none';
            return;
        }

        try {
            const user = JSON.parse(userJson);
            if (user.primer_ingreso) {
                vLogin.style.display = 'none';
                vDash.style.display = 'none';
                if (vCambio) {
                    vCambio.style.display = 'block';
                    const lblUser = document.getElementById('txtUsuarioCambio');
                    if (lblUser) lblUser.textContent = user.username;
                }
                return;
            }

            vLogin.style.display = 'none';
            if (vCambio) vCambio.style.display = 'none';
            vDash.style.display = 'block';

            if (user.rol_sistema === 'Docente' && user.id_persona) {
                localStorage.setItem('asista_docente_id', user.id_persona);
                localStorage.setItem('asista_docente_nombre', user.nombre);
                const nombreDocente = document.getElementById('txtDocenteActivo');
                const cargoDocente = document.getElementById('txtDocenteCargo');
                if (nombreDocente) nombreDocente.textContent = user.nombre;
                if (cargoDocente) cargoDocente.textContent = 'Facilitador Titular';
                const verTodos = document.getElementById('chkVerTodos');
                if (verTodos) {
                    verTodos.checked = false;
                    verTodos.disabled = true;
                    if (verTodos.closest('label')) verTodos.closest('label').style.display = 'none';
                }
            }
            if (typeof cargarCohortes === 'function') {
                cargarCohortes();
            }
        } catch (_) {
            sessionStorage.clear();
            vLogin.style.display = 'block';
            vDash.style.display = 'none';
        }
    };

    window.iniciarSesionMovil = async function(event) {
        event.preventDefault();
        const userField = document.getElementById('movil_user');
        const passField = document.getElementById('movil_pass');
        const errBox = document.getElementById('movil_error');
        const btnSubmit = document.getElementById('btnSubmitLogin');

        if (!userField || !passField) return;
        errBox.textContent = '';
        btnSubmit.disabled = true;
        btnSubmit.textContent = 'Verificando...';

        try {
            const resp = await nativeFetch('/api/auth/login', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({username: userField.value.trim(), password: passField.value})
            });
            const data = await resp.json();
            if (!resp.ok) {
                errBox.textContent = data.mensaje || 'Credenciales inválidas.';
                passField.value = '';
                passField.focus();
                btnSubmit.disabled = false;
                btnSubmit.textContent = 'Ingresar al Aula Sabatina';
                return;
            }

            sessionStorage.setItem(tokenKey, data.token);
            sessionStorage.setItem('asista_api_user', JSON.stringify(data.usuario));
            btnSubmit.disabled = false;
            btnSubmit.textContent = 'Ingresar al Aula Sabatina';
            window.verificarEstadoAuth();
        } catch (e) {
            errBox.textContent = 'No se pudo conectar con el servidor local.';
            btnSubmit.disabled = false;
            btnSubmit.textContent = 'Ingresar al Aula Sabatina';
        }
    };

    window.guardarClavePrimerIngreso = async function(event) {
        event.preventDefault();
        const p1 = document.getElementById('movil_nueva_clave').value.trim();
        const p2 = document.getElementById('movil_conf_clave').value.trim();
        const errBox = document.getElementById('movil_cambio_error');
        const btn = document.getElementById('btnSubmitCambio');

        if (!p1 || !p2) {
            errBox.textContent = 'Complete ambos campos.';
            return;
        }
        if (p1 !== p2) {
            errBox.textContent = 'Las contraseñas no coinciden.';
            return;
        }
        if (p1.length < 8) {
            errBox.textContent = 'Mínimo 8 caracteres.';
            return;
        }

        btn.disabled = true;
        btn.textContent = 'Actualizando...';
        errBox.textContent = '';

        try {
            const token = sessionStorage.getItem(tokenKey);
            const resp = await nativeFetch('/api/auth/cambiar_password_primer_ingreso', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': 'Bearer ' + token
                },
                body: JSON.stringify({nueva_password: p1})
            });
            const data = await resp.json();
            if (!resp.ok) {
                errBox.textContent = data.mensaje || 'Error actualizando contraseña.';
                btn.disabled = false;
                btn.textContent = 'Establecer Contraseña e Ingresar';
                return;
            }

            const userJson = sessionStorage.getItem('asista_api_user');
            if (userJson) {
                const user = JSON.parse(userJson);
                user.primer_ingreso = false;
                sessionStorage.setItem('asista_api_user', JSON.stringify(user));
            }
            alert('Contraseña actualizada con éxito. ¡Bienvenido a su aula sabatina!');
            window.verificarEstadoAuth();
        } catch (e) {
            errBox.textContent = 'Error de conexión con el servidor.';
            btn.disabled = false;
            btn.textContent = 'Establecer Contraseña e Ingresar';
        }
    };

    window.cerrarSesionMovil = async function() {
        if (!confirm('¿Desea cerrar la sesión de asistencia?')) return;
        try {
            const token = sessionStorage.getItem(tokenKey);
            if (token) {
                await nativeFetch('/api/auth/logout', {
                    method: 'POST',
                    headers: {'Authorization': 'Bearer ' + token}
                });
            }
        } catch (_) {}
        sessionStorage.clear();
        localStorage.removeItem('asista_docente_id');
        localStorage.removeItem('asista_docente_nombre');
        window.location.reload();
    };

    window.fetch = async (input, init) => {
        const request = new Request(input, init);
        const url = new URL(request.url, window.location.href);
        if (url.origin !== window.location.origin || !url.pathname.startsWith('/api/') ||
            url.pathname === '/api/auth/login' || url.pathname === '/api/status') {
            return nativeFetch(request);
        }

        const token = sessionStorage.getItem(tokenKey);
        const headers = new Headers(request.headers);
        if (token) headers.set('Authorization', 'Bearer ' + token);
        const response = await nativeFetch(new Request(request.clone(), {headers}));
        if (response.status === 401) {
            sessionStorage.clear();
            window.verificarEstadoAuth();
        }
        return response;
    };

    document.addEventListener('DOMContentLoaded', () => {
        window.verificarEstadoAuth();
    });
})();
"""


def fmt_hora_simple(valor):
    """Convierte timedelta, time o str a formato legible HH:MM."""
    if not valor:
        return ""
    if hasattr(valor, "strftime"):
        return valor.strftime("%H:%M")
    s = str(valor)
    partes = s.split(":")
    if len(partes) >= 2:
        try:
            return f"{int(partes[0]):02d}:{int(partes[1]):02d}"
        except Exception:
            return s[:5]
    return s[:5]


_CACHE_IP = None

def obtener_ip_local():
    """Detecta la IP local real y activa de la laptop en la red Wi-Fi/LAN al instante."""
    global _CACHE_IP
    # Probar resolución por ruta de socket (el método más preciso del SO)
    for target in (("8.8.8.8", 80), ("1.1.1.1", 80), ("192.168.0.254", 80), ("192.168.1.1", 80)):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.settimeout(0.3)
                s.connect(target)
                ip = s.getsockname()[0]
            if ip and not ip.startswith("127.") and not ip.startswith("169.254."):
                _CACHE_IP = ip
                return _CACHE_IP
        except OSError:
            pass

    # Consulta a interfaces de red en Windows
    try:
        out = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command",
             "(Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -like '*Wi-Fi*' -or $_.InterfaceAlias -like '*Ethernet*' }).IPAddress"],
            text=True, timeout=2
        ).strip().splitlines()
        for line in out:
            candidate = line.strip()
            if candidate and not candidate.startswith("127.") and not candidate.startswith("169.254."):
                _CACHE_IP = candidate
                return _CACHE_IP
    except (OSError, subprocess.SubprocessError):
        pass

    _CACHE_IP = "127.0.0.1"
    return _CACHE_IP


def listar_ips_locales():
    """Retorna lista de IPs IPv4 candidatas de la red local, con la IP activa de primero."""
    activa = obtener_ip_local()
    candidatos = [activa] if activa and not activa.startswith("127.") else []
    try:
        hostname = socket.gethostname()
        for ip in socket.gethostbyname_ex(hostname)[2]:
            if ip and not ip.startswith("127.") and not ip.startswith("169.254."):
                if ip not in candidatos:
                    candidatos.append(ip)
    except Exception:
        pass
    return candidatos or ["127.0.0.1"]


def _consultar_estado_local(puerto, esquema="http"):
    """Consulta el endpoint liviano del servicio sin abrir conexiones a la base de datos."""
    url = f"{esquema}://127.0.0.1:{puerto}/api/status"
    contexto = ssl._create_unverified_context() if esquema == "https" else None
    try:
        with urllib.request.urlopen(url, timeout=1.0, context=contexto) as respuesta:
            estado = json.loads(respuesta.read(2048).decode("utf-8"))
    except (OSError, ssl.SSLError, urllib.error.URLError, ValueError):
        return None

    if not isinstance(estado, dict) or estado.get("status") != "online":
        return None
    if estado.get("service") != "asista" and not {"hora", "fecha"}.issubset(estado):
        return None

    return estado


def obtener_estado_servidor():
    """Devuelve los puertos que están atendiendo el servicio local, si alguno."""
    puertos_http = []
    if PUERTO_HTTP_ACTIVO:
        puertos_http.append(PUERTO_HTTP_ACTIVO)
    puertos_http.extend(
        range(PUERTO_SERVICIO, min(PUERTO_SERVICIO + PUERTOS_HTTP_ALTERNATIVOS, 65536))
    )

    for puerto in dict.fromkeys(puertos_http):
        estado = _consultar_estado_local(puerto)
        if estado:
            estado["http_port"] = estado.get("http_port") or puerto
            if not estado.get("https_port"):
                estado_https = _consultar_estado_local(PUERTO_HTTPS_ACTIVO or PUERTO_HTTPS, "https")
                if estado_https:
                    estado["https_port"] = estado_https.get("https_port") or PUERTO_HTTPS
            return estado

    puerto_https = PUERTO_HTTPS_ACTIVO or PUERTO_HTTPS
    estado = _consultar_estado_local(puerto_https, "https")
    if estado:
        estado["http_port"] = estado.get("http_port") or PUERTO_HTTP_ACTIVO
        estado["https_port"] = estado.get("https_port") or puerto_https
        return estado
    return None


def obtener_url_movil(ip=None, ruta="/"):
    """Genera una URL móvil con protocolo y puerto realmente activos."""
    direccion = ip or obtener_ip_local()
    try:
        ipv4 = ipaddress.ip_address(direccion)
        if not isinstance(ipv4, ipaddress.IPv4Address) or ipv4.is_loopback or ipv4.is_link_local:
            return None
    except ValueError:
        return None

    estado = obtener_estado_servidor()
    if not estado:
        return None

    ruta = ruta if ruta.startswith("/") else f"/{ruta}"
    puerto_https = estado.get("https_port")
    if puerto_https and (not IPS_CERTIFICADO_SSL or str(ipv4) in IPS_CERTIFICADO_SSL):
        return f"https://{ipv4}:{puerto_https}{ruta}"

    puerto_http = estado.get("http_port")
    return f"http://{ipv4}:{puerto_http}{ruta}" if puerto_http else None


def generar_icono_pwa(size=192):
    """Genera el icono PWA de Asista. Usa el logo real si existe, sino genera uno de respaldo."""
    from PIL import Image, ImageDraw
    import io

    # 1. Intentar cargar el icono real redimensionado (icon-192.png o icon-512.png)
    p_ico_cached = RUTA_ASSETS / f"icon-{size}.png"
    if p_ico_cached.exists():
        with open(p_ico_cached, "rb") as f:
            return f.read()

    # 2. Intentar cargar icon.png original y redimensionar
    p_ico_real = RUTA_ASSETS / "icon.png"
    if p_ico_real.exists():
        try:
            img = Image.open(str(p_ico_real)).convert("RGBA").resize((size, size), Image.LANCZOS)
            b = io.BytesIO()
            img.save(b, format="PNG")
            # Guardar para cache futura
            with open(str(p_ico_cached), "wb") as fc:
                fc.write(b.getvalue())
            b.seek(0)
            return b.read()
        except Exception:
            pass

    # 3. Icono de respaldo generado con Pillow (paleta Asista)
    img = Image.new('RGBA', (size, size), '#0F2042')
    draw = ImageDraw.Draw(img)
    draw.ellipse([size*0.08, size*0.08, size*0.92, size*0.92], fill='#162C55', outline='#00B4D8', width=max(2, int(size*0.03)))
    pts = [
        (size*0.28, size*0.52),
        (size*0.44, size*0.68),
        (size*0.72, size*0.34)
    ]
    draw.line(pts, fill='#00B4D8', width=max(3, int(size*0.08)), joint='curve')
    b = io.BytesIO()
    img.save(b, format='PNG')
    return b.getvalue()


_ICON_192 = None
_ICON_512 = None

HTML_PROFESOR = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Asista - Portal Móvil del Docente</title>
    <!-- PWA y Soporte Móvil Nativo -->
    <link rel="manifest" href="/manifest.json">
    <meta name="theme-color" content="#040444">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="Asista Docente">
    <link rel="apple-touch-icon" href="/static/icon-192.png">
    <link rel="icon" type="image/x-icon" href="/favicon.ico">
    <!-- Librerías de Escaneo: ZXing servido localmente (sin CDN) -->
    <script src="/static/zxing.js"></script>
    <style>
        :root {
            --primario: #040444;
            --primario-dark: #08082D;
            --acento: #56E1E8;
            --acento-dark: #35C8D1;
            --ok: #56E1E8;
            --ok-bg: rgba(86, 225, 232, 0.1);
            --aviso: #70283D;
            --aviso-bg: #24151C;
            --rojo: #70283D;
            --rojo-bg: #24151C;
            --bg: #040444;
            --card: #12131B;
            --texto: #F3EFE8;
            --suave: #AAA6A1;
            --borde: rgba(86, 225, 232, 0.2);
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        body { background: var(--bg); color: var(--texto); padding-bottom: 24px; -webkit-tap-highlight-color: transparent; }
        #pwaBanner, #modalInstalarApp { display: none !important; }

        .brand-header { max-width: 520px; margin: 12px auto 8px; padding: 0 12px; }
        .brand-frame {
            min-height: 72px; display: grid; place-items: center; padding: 8px;
            background: linear-gradient(180deg, var(--card), var(--bg));
            border: 1px solid var(--borde); border-radius: 16px;
        }
        .brand-frame img { display: block; max-height: 52px; width: auto; }
        .mobile-page-heading { margin-bottom: 12px; }
        .header-actions { display: flex; align-items: center; gap: 6px; }
        .btn-switch {
            background: var(--primario);
            color: white;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 700;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 4px;
        }
        .btn-pwa-header {
            background: var(--primario);
            border: 1px solid var(--acento);
            color: white;
            font-size: 11px;
            padding: 4px 10px;
            border-radius: 20px;
            font-weight: 700;
            cursor: pointer;
        }
        .header-title-row { display: flex; align-items: center; justify-content: space-between; margin-top: 10px; }
        .header-title { font-size: 18px; font-weight: 800; letter-spacing: -0.3px; color: var(--texto); }
        .portal-badge {
            background: rgba(0, 180, 216, 0.2);
            color: #A5F3FC;
            font-size: 10px;
            font-weight: 800;
            padding: 3px 8px;
            border-radius: 6px;
            letter-spacing: 0.5px;
        }

        /* Barra de identificación del docente */
        .docente-bar {
            background: var(--card);
            border: 1px solid var(--borde);
            border-radius: 12px;
            padding: 8px 12px;
            margin-top: 8px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .docente-info { display: flex; align-items: center; gap: 8px; }
        .docente-name { font-size: 13px; font-weight: 800; color: var(--primario); }
        .docente-cargo { font-size: 10px; color: var(--suave); }
        .btn-docente-change {
            background: var(--acento);
            color: var(--primario);
            border: none;
            padding: 4px 10px;
            border-radius: 8px;
            font-size: 11px;
            font-weight: 800;
            cursor: pointer;
        }

        .container { max-width: 520px; margin: 12px auto; padding: 0 12px; }

        /* Banner PWA */
        .pwa-banner {
            background: linear-gradient(135deg, #0A192F, #1E3A6D);
            color: white;
            padding: 10px 14px;
            border-radius: 14px;
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }
        .btn-pwa-install {
            background: var(--acento);
            color: var(--primario);
            border: none;
            padding: 6px 12px;
            border-radius: 8px;
            font-size: 11px;
            font-weight: 800;
            cursor: pointer;
        }

        /* Barra de contingencia offline */
        .offline-bar {
            background: #21151B;
            border: 1px solid var(--aviso);
            color: #E8D9DD;
            padding: 10px 14px;
            border-radius: 12px;
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 12px;
            font-weight: 700;
        }
        .btn-sync {
            background: var(--aviso);
            color: white;
            border: none;
            padding: 4px 10px;
            border-radius: 8px;
            font-size: 11px;
            font-weight: 800;
            cursor: pointer;
        }

        /* Banner de Sesión Cerrada */
        .session-status {
            background: rgba(86, 225, 232, 0.06);
            border: 1px solid var(--borde);
            border-radius: 12px;
            padding: 10px 14px;
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 12px;
            font-weight: 800;
            color: var(--texto);
        }
        .btn-reabrir {
            background: var(--card);
            border: 1px solid var(--borde);
            color: var(--acento);
            padding: 4px 10px;
            border-radius: 8px;
            font-size: 11px;
            font-weight: 800;
            cursor: pointer;
        }

        .card {
            background: var(--card);
            border-radius: 14px;
            padding: 14px 16px;
            margin-bottom: 12px;
            box-shadow: none;
            border: 1px solid var(--borde);
        }

        /* Selector de Curso */
        .select-label { font-size: 11px; font-weight: 800; color: var(--suave); text-transform: uppercase; }
        select {
            width: 100%;
            padding: 12px;
            font-size: 14px;
            font-weight: 700;
            color: var(--texto);
            background: #1B1A21;
            border: 1px solid var(--borde);
            border-radius: 12px;
            outline: none;
            margin-top: 6px;
        }
        select:focus { border-color: var(--acento); }

        .curso-info {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 8px;
            padding-top: 8px;
            border-top: 1px solid var(--borde);
            font-size: 12px;
            color: var(--suave);
        }
        .curso-badge {
            background: rgba(0, 180, 216, 0.12);
            color: var(--primario);
            font-weight: 800;
            padding: 3px 8px;
            border-radius: 8px;
        }

        /* TARJETA ESCÁNER DE FOTO Y CÉDULA RÁPIDA */
        .scanner-card {
            background: #11131B;
            color: white;
            border: 1px solid var(--borde);
            border-radius: 14px;
            padding: 18px;
            margin-bottom: 12px;
            box-shadow: none;
        }
        .scanner-title { font-size: 14px; font-weight: 800; margin-bottom: 10px; display: flex; align-items: center; justify-content: space-between; }
        .scanner-badge { background: rgba(0, 180, 216, 0.2); color: #A5F3FC; font-size: 10px; padding: 2px 8px; border-radius: 6px; font-weight: 800; }
        .connection-status {
            display: inline-flex; align-items: center; padding: 4px 8px; border-radius: 999px;
            font-size: 10px; font-weight: 800; white-space: nowrap;
        }
        .connection-status[data-state="checking"], .connection-status[data-state="sending"] {
            color: var(--acento); background: rgba(86, 225, 232, 0.1);
        }
        .connection-status[data-state="online"] { color: var(--acento); background: rgba(86, 225, 232, 0.1); }
        .connection-status[data-state="offline"] { color: #E6C7D0; background: rgba(112, 40, 61, 0.36); }

        .btn-tomar-foto {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            width: 100%;
            background: var(--acento);
            color: var(--primario);
            padding: 14px;
            border-radius: 12px;
            font-size: 15px;
            font-weight: 800;
            border: none;
            cursor: pointer;
            box-shadow: none;
            margin-bottom: 10px;
            transition: transform 0.1s ease;
        }
        .btn-tomar-foto:active { transform: scale(0.98); }

        .quick-form { display: flex; gap: 8px; margin-top: 8px; }
        .input-cedula {
            flex: 1;
            padding: 12px 14px;
            border-radius: 12px;
            border: 1px solid var(--borde);
            background: #1B1A21;
            color: var(--texto);
            font-size: 14px;
            font-weight: 700;
            outline: none;
        }
        .input-cedula::placeholder { color: var(--suave); }
        .input-cedula:focus { border-color: var(--acento); background: #1B1A21; }
        .btn-marcar-submit {
            background: var(--acento);
            color: var(--primario);
            border: none;
            padding: 0 16px;
            border-radius: 12px;
            font-size: 13px;
            font-weight: 800;
            cursor: pointer;
            white-space: nowrap;
        }
        .capture-fallback {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-width: 44px;
            padding: 0 10px;
            border: 1px solid var(--acento);
            border-radius: 12px;
            background: var(--primario);
            color: white;
            font-size: 19px;
            cursor: pointer;
        }

        /* Notificación Toast de Confirmación */
        .toast-confirm {
            background: var(--card);
            border: 1px solid var(--borde);
            border-left: 3px solid var(--ok);
            border-radius: 12px;
            padding: 12px 14px;
            margin-bottom: 12px;
            box-shadow: none;
            display: none;
            animation: slideDown 0.3s ease;
        }
        .toast-confirm.toast-error {
            border-left-color: var(--rojo);
        }
        .toast-confirm.toast-duplicate {
            border-left-color: var(--aviso);
        }
        @keyframes slideDown { from { opacity: 0; transform: translateY(-8px); } to { opacity: 1; transform: translateY(0); } }
        .toast-title { font-size: 13px; font-weight: 800; color: var(--acento); margin-bottom: 2px; }
        .toast-confirm.toast-error .toast-title, .toast-confirm.toast-duplicate .toast-title { color: #E6C7D0; }
        .toast-desc { font-size: 13px; font-weight: 700; color: var(--texto); }
        .toast-meta { font-size: 11px; color: var(--suave); margin-top: 2px; }
        .attendance-tools { margin: 8px 0 16px; }
        .attendance-tools > summary {
            padding: 11px 14px; border: 1px solid var(--borde); border-radius: 12px;
            background: var(--card); color: var(--primario); font-size: 12px;
            font-weight: 800; cursor: pointer; list-style-position: inside;
        }
        .attendance-tools[open] > summary { margin-bottom: 10px; }

        /* Lista de Estudiantes */
        .list-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        .btn-masivo {
            background: rgba(16, 185, 129, 0.12);
            color: #065F46;
            border: 1px solid rgba(16, 185, 129, 0.4);
            padding: 6px 12px;
            border-radius: 10px;
            font-size: 11px;
            font-weight: 800;
            cursor: pointer;
        }

        .student-item {
            background: var(--card);
            border: 1.5px solid var(--borde);
            border-radius: 14px;
            padding: 12px;
            margin-bottom: 8px;
            transition: all 0.2s ease;
        }
        .student-item.item-presente {
            border-color: rgba(16, 185, 129, 0.5);
            background: #F0FDF4;
        }
        .student-item.item-retraso {
            border-color: rgba(245, 158, 11, 0.5);
            background: #FFFBEB;
        }
        .student-item.item-ausente {
            border-color: rgba(239, 68, 68, 0.4);
            background: #FEF2F2;
        }
        .student-top {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }
        .student-name { font-size: 14px; font-weight: 800; color: var(--texto); }
        .student-cedula { font-size: 11px; color: var(--suave); font-weight: 600; }
        .status-pill {
            font-size: 10px;
            font-weight: 800;
            padding: 3px 8px;
            border-radius: 8px;
            text-transform: uppercase;
        }
        .status-pill.presente { background: var(--ok); color: white; }
        .status-pill.retraso { background: var(--aviso); color: white; }
        .status-pill.ausente { background: var(--rojo); color: white; }
        .status-pill.pendiente { background: var(--bg); color: var(--suave); }

        .btn-group {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 6px;
        }
        .btn-touch {
            padding: 10px 4px;
            font-size: 12px;
            font-weight: 800;
            border-radius: 10px;
            border: 1px solid var(--borde);
            background: var(--bg);
            color: var(--suave);
            cursor: pointer;
            text-align: center;
            transition: all 0.15s ease;
        }
        .btn-touch:active { transform: scale(0.97); }
        .btn-touch.active-presente { background: var(--ok); color: white; border-color: var(--ok); box-shadow: 0 2px 6px rgba(16, 185, 129, 0.3); }
        .btn-touch.active-retraso { background: var(--aviso); color: white; border-color: var(--aviso); box-shadow: 0 2px 6px rgba(245, 158, 11, 0.3); }
        .btn-touch.active-ausente { background: var(--rojo); color: white; border-color: var(--rojo); box-shadow: 0 2px 6px rgba(239, 68, 68, 0.3); }

        /* Botón de Cierre de Clase */
        .btn-cerrar-clase {
            width: 100%;
            background: #FFFFFF;
            border: 2px solid var(--primario);
            color: var(--primario);
            padding: 14px;
            border-radius: 14px;
            font-size: 14px;
            font-weight: 800;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            margin-top: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }

        /* Modales */
        .modal-overlay {
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(10, 20, 40, 0.7);
            display: none;
            align-items: center;
            justify-content: center;
            padding: 16px;
            z-index: 9999;
        }
        .modal-content {
            background: white;
            border-radius: 20px;
            padding: 22px;
            width: 100%;
            max-width: 440px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.3);
        }
        .modal-title { font-size: 17px; font-weight: 800; color: var(--primario); margin-bottom: 6px; }
        .modal-desc { font-size: 12px; color: var(--suave); margin-bottom: 14px; }
    </style>
</head>
<body>

    <header style="background-color: transparent; text-align: center; padding: 10px 0;"><img src="{{ url_for('static', filename='img/logo.png') }}" alt="Escudo de la U.E.P. Prof. Aristóbulo Istúriz, código PD31212303" style="max-height: 100px; width: auto; display: block; margin: 0 auto;"></header>

    <!-- 1. VISTA DE INICIO DE SESIÓN MÓVIL (PANTALLA OBLIGATORIA) -->
    <div id="vistaLoginMovil" class="container" style="display:block; max-width:420px; margin:16px auto;">
        <div class="card" style="padding:26px 20px; text-align:center; box-shadow:0 10px 25px rgba(15,32,66,0.12); border-radius:20px;">
            <div style="font-size:38px; margin-bottom:8px;">📱</div>
            <h2 style="color:var(--primario); font-size:20px; font-weight:800; margin-bottom:4px;">Portal Docente Sabatino</h2>
            <p style="color:var(--suave); font-size:12px; margin-bottom:20px;">U.E.P. Prof. Aristóbulo Iztúriz</p>
            
            <form onsubmit="iniciarSesionMovil(event)" style="text-align:left;">
                <label style="display:block; font-size:12px; font-weight:700; color:var(--texto); margin-bottom:4px;">Usuario Institucional</label>
                <input id="movil_user" type="text" autocomplete="username" required placeholder="ej: prof.navarro"
                       style="width:100%; height:44px; padding:10px 12px; border:1.5px solid var(--borde); border-radius:10px; font-size:14px; margin-bottom:14px; box-sizing:border-box;">

                <label style="display:block; font-size:12px; font-weight:700; color:var(--texto); margin-bottom:4px;">Contraseña</label>
                <input id="movil_pass" type="password" autocomplete="current-password" required placeholder="Contraseña"
                       style="width:100%; height:44px; padding:10px 12px; border:1.5px solid var(--borde); border-radius:10px; font-size:14px; margin-bottom:14px; box-sizing:border-box;">

                <div id="movil_error" style="color:var(--rojo); font-size:12px; font-weight:700; min-height:18px; margin-bottom:12px; text-align:center;"></div>

                <button id="btnSubmitLogin" type="submit"
                        style="width:100%; height:46px; background:var(--primario); color:white; border:none; border-radius:12px; font-size:14px; font-weight:800; cursor:pointer;">
                    Ingresar al Aula Sabatina
                </button>
            </form>

            <div style="margin-top:20px; padding-top:14px; border-top:1px solid var(--borde); font-size:11px; color:var(--suave); line-height:1.4;">
                🔒 <strong>Acceso protegido:</strong> Solo la Directora y el personal de Administración asignan usuarios a los facilitadores.
            </div>
        </div>
    </div>

    <!-- 2. VISTA DE CAMBIO OBLIGATORIO DE CONTRASEÑA (PRIMER INGRESO) -->
    <div id="vistaCambioClaveMovil" class="container" style="display:none; max-width:420px; margin:16px auto;">
        <div class="card" style="padding:26px 20px; text-align:center; box-shadow:0 10px 25px rgba(15,32,66,0.12); border-radius:20px;">
            <div style="font-size:38px; margin-bottom:8px;">🔐</div>
            <h2 style="color:var(--primario); font-size:19px; font-weight:800; margin-bottom:4px;">Cambio de Contraseña Requerido</h2>
            <p style="color:var(--suave); font-size:12px; margin-bottom:18px;">
                Primer ingreso detectado para <strong id="txtUsuarioCambio" style="color:var(--primario);">usuario</strong>.<br>Defina su nueva contraseña personal para continuar.
            </p>

            <form onsubmit="guardarClavePrimerIngreso(event)" style="text-align:left;">
                <label style="display:block; font-size:12px; font-weight:700; color:var(--texto); margin-bottom:4px;">Nueva Contraseña</label>
                <input id="movil_nueva_clave" type="password" required placeholder="Mínimo 8 caracteres"
                       style="width:100%; height:44px; padding:10px 12px; border:1.5px solid var(--borde); border-radius:10px; font-size:14px; margin-bottom:12px; box-sizing:border-box;">

                <label style="display:block; font-size:12px; font-weight:700; color:var(--texto); margin-bottom:4px;">Confirmar Nueva Contraseña</label>
                <input id="movil_conf_clave" type="password" required placeholder="Repita la nueva contraseña"
                       style="width:100%; height:44px; padding:10px 12px; border:1.5px solid var(--borde); border-radius:10px; font-size:14px; margin-bottom:12px; box-sizing:border-box;">

                <div style="background:#F1F5F9; border-radius:8px; padding:10px; font-size:11px; color:#334155; margin-bottom:14px; line-height:1.4;">
                    • Mínimo 8 caracteres<br>
                    • Mayúsculas y minúsculas<br>
                    • Números y símbolos (@$!%*?&#.-)
                </div>

                <div id="movil_cambio_error" style="color:var(--rojo); font-size:12px; font-weight:700; min-height:18px; margin-bottom:12px; text-align:center;"></div>

                <button id="btnSubmitCambio" type="submit"
                        style="width:100%; height:46px; background:var(--primario); color:white; border:none; border-radius:12px; font-size:14px; font-weight:800; cursor:pointer;">
                    Establecer Contraseña e Ingresar
                </button>
            </form>
        </div>
    </div>

    <!-- 3. DASHBOARD PRINCIPAL DE ASISTENCIA (SOLO TRAS INICIAR SESIÓN) -->
    <div id="vistaDashboardMovil" class="container" style="display:none;">
        <div class="mobile-page-heading">
            <div class="header-actions">
                <button onclick="cerrarSesionMovil()" class="btn-switch" style="background:#DC2626; border:none; cursor:pointer;">🚪 Salir</button>
            </div>
            <div class="header-title-row">
                <div class="header-title">Asistencia de Curso</div>
                <span class="portal-badge" id="txtFecha">Hoy</span>
            </div>

            <!-- Identificación del Profesor -->
            <div class="docente-bar">
                <div class="docente-info">
                    <span style="font-size: 20px;">👨‍🏫</span>
                    <div>
                        <div class="docente-name" id="txtDocenteActivo">Docente / Profesor</div>
                        <div class="docente-cargo" id="txtDocenteCargo">Facilitador Titular</div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Banner PWA -->
        <div class="pwa-banner" id="pwaBanner" style="display: none;">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 24px;">📲</span>
                <div>
                    <strong style="font-size: 13px;">Instalar Asista como App</strong>
                    <div style="font-size: 11px; opacity: 0.85;">Acceso directo en pantalla de inicio</div>
                </div>
            </div>
            <div style="display: flex; align-items: center; gap: 8px;">
                <button class="btn-pwa-install" onclick="instalarPwa()">Instalar</button>
                <button onclick="cerrarBannerPwa()" title="Ocultar" style="background:none; border:none; color:white; font-size:16px; cursor:pointer; padding:4px 6px; opacity:0.75; line-height:1;">&times;</button>
            </div>
        </div>

        <!-- Barra Offline -->
        <div class="offline-bar" id="offlineBar" style="display: none;">
            <span>💾 <strong id="txtOfflineCount">0</strong> marcajes guardados en celular</span>
            <button class="btn-sync" onclick="sincronizarOffline()">🔄 Sincronizar</button>
        </div>

        <!-- Banner Sesión Cerrada -->
        <div class="session-status" id="sessionStatus" style="display: none;">
            <span id="sessionStatusTxt">🔒 Sesión Cerrada</span>
            <button class="btn-reabrir" onclick="reabrirSesion()">🔄 Reabrir</button>
        </div>

        <!-- Selector de Curso Activo -->
        <div class="card">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <label class="select-label" for="selectCohorte">Curso y Grupo Activo</label>
                <label style="font-size: 11px; color: var(--suave); display: flex; align-items: center; gap: 4px; cursor: pointer;">
                    <input type="checkbox" id="chkVerTodos" checked onchange="toggleVerTodos()"> Ver todos
                </label>
            </div>
            <select id="selectCohorte" onchange="cambiarCurso()">
                <option value="">Cargando cursos activos...</option>
            </select>
            <div class="curso-info" id="cursoDetalle" style="display: none;">
                <span id="txtAulaDocente">Aula: --</span>
                <span class="curso-badge" id="txtInscritos">0 Alumnos</span>
            </div>
        </div>

        <!-- ESCÁNER EN TIEMPO REAL — PORTAL PROFESOR -->
        <div class="scanner-card">
            <div class="scanner-title">
                <span>📷 Escaneo de carnet</span>
                <span class="connection-status" id="estadoConexionProfesor" data-state="checking" aria-live="polite">Comprobando conexión…</span>
            </div>


            <!-- Panel aviso HTTPS / alternativas -->
            <div id="panelHttpsAviso" style="display:none; background:#1E3A5F; border-radius:12px; padding:14px; margin-bottom:10px;">
                <div style="color:#FCD34D; font-weight:800; font-size:13px; margin-bottom:8px;">⚠️ No se pudo abrir la cámara</div>
                <div style="color:#BAE6FD; font-size:12px; line-height:1.5;">
                    Permite el acceso a la cámara en la configuración del navegador y vuelve a iniciar el escáner.
                </div>
            </div>

            <!-- Visor de cámara en tiempo real -->
            <div id="visorCamaraProf" style="display:none; position:relative; border-radius:14px; overflow:hidden; background:#000; margin-bottom:10px;">
                <video id="videoEscanerProf" autoplay playsinline muted
                    style="width:100%; display:block; border-radius:14px; max-height:230px; object-fit:cover;"></video>
                <!-- Marco guía -->
                <div style="position:absolute; top:50%; left:50%; transform:translate(-50%,-54%);
                    width:72%; height:40%; border:3px solid #00B4D8; border-radius:10px;
                    box-shadow:0 0 0 9999px rgba(0,0,0,0.42); pointer-events:none;">
                    <div style="position:absolute;top:-2px;left:-2px;width:20px;height:20px;border-top:4px solid #00B4D8;border-left:4px solid #00B4D8;border-radius:3px 0 0 0;"></div>
                    <div style="position:absolute;top:-2px;right:-2px;width:20px;height:20px;border-top:4px solid #00B4D8;border-right:4px solid #00B4D8;border-radius:0 3px 0 0;"></div>
                    <div style="position:absolute;bottom:-2px;left:-2px;width:20px;height:20px;border-bottom:4px solid #00B4D8;border-left:4px solid #00B4D8;border-radius:0 0 0 3px;"></div>
                    <div style="position:absolute;bottom:-2px;right:-2px;width:20px;height:20px;border-bottom:4px solid #00B4D8;border-right:4px solid #00B4D8;border-radius:0 0 3px 0;"></div>
                    <div style="position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,transparent,#00B4D8,transparent);animation:scanLine 1.6s ease-in-out infinite;"></div>
                </div>
                <div id="estadoCamaraProf" style="position:absolute;bottom:7px;left:0;right:0;text-align:center;color:white;font-size:12px;font-weight:700;text-shadow:0 1px 3px rgba(0,0,0,0.9);">
                    Apunte al código del carnet
                </div>
                <div style="position:absolute;top:7px;right:7px;display:flex;gap:6px;z-index:10;">
                    <button onclick="detenerCamaraProf()" title="Cerrar Cámara" style="background:rgba(0,0,0,0.55);border:none;color:white;border-radius:50%;width:32px;height:32px;font-size:16px;cursor:pointer;display:flex;align-items:center;justify-content:center;">✕</button>
                </div>
            </div>

            <style>@keyframes scanLine{0%{top:0}50%{top:calc(100% - 2px)}100%{top:0}}</style>

            <button type="button" class="btn-tomar-foto" id="btnActivarCamaraProf" style="margin: 0; background: linear-gradient(135deg, #0284C7, #0369A1); font-size:16px;" onclick="activarCamaraProf()">
                <span>🎥 Iniciar escáner en vivo</span>
            </button>
        </div>

        <!-- Tarjeta de Confirmación de Marcaje -->
        <div class="toast-confirm" id="toastConfirm" aria-live="polite">
            <div class="toast-title" id="toastTitle">✓ Asistencia Guardada</div>
            <div class="toast-desc" id="toastNombre">Estudiante</div>
            <div class="toast-meta" id="toastMeta">Hora: --:-- | Asistencia: --%</div>
        </div>

        <details class="attendance-tools">
            <summary>Opciones adicionales de asistencia</summary>
        <!-- LISTA DE ESTUDIANTES CON BOTONES DE TOQUE -->
        <div class="card">
            <div class="list-header" style="flex-wrap: wrap; gap: 8px;">
                <div>
                    <span class="select-label">Lista de Asistencia</span>
                    <div style="font-size: 11px; color: var(--suave);" id="resumenAsistencia">Cargando...</div>
                </div>
                <button class="btn-masivo" id="btnMarcarTodos" onclick="marcarTodosPresentes()">
                    ✓ Marcar Todos
                </button>
            </div>

            <!-- Búsqueda rápida por nombre o cédula -->
            <div style="margin: 8px 0 12px 0;">
                <input type="text" id="busquedaManualParticipante" class="input-cedula"
                       placeholder="🔍 Buscar participante por nombre o C.I..."
                       oninput="filtrarEstudiantesManual()"
                       style="width: 100%; box-sizing: border-box; padding: 9px 12px; font-size: 13px; border-radius: 8px;">
            </div>

            <!-- Contenedor dinámico de estudiantes -->
            <div id="contenedorEstudiantes">
                <div style="text-align: center; color: var(--suave); padding: 20px; font-size: 13px;">
                    Cargando estudiantes del curso...
                </div>
            </div>
        </div>

        <!-- Botón de Cierre de Sesión -->
        <button class="btn-cerrar-clase" id="btnAbrirCierre" onclick="abrirModalCierre()">
            🔒 Cerrar Asistencia del Día (Firma Digital)
        </button>
        </details>

    </div>

    <!-- MODAL: INSTRUCCIONES INSTALACIÓN PWA -->
    <div class="modal-overlay" id="modalInstalarApp">
        <div class="modal-content">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                <div class="modal-title" style="margin-bottom:0;">📲 Instalar Asista en tu Celular</div>
                <button onclick="cerrarModalInstalarApp()" style="background:none; border:none; font-size:22px; cursor:pointer; color:var(--suave); line-height:1;">&times;</button>
            </div>
            <div class="modal-desc">Ingresa directamente desde el icono en tu pantalla de inicio como una aplicación nativa:</div>

            <div style="display: flex; gap: 8px; margin-bottom: 14px;">
                <button id="tabGuiaAndroid" onclick="cambiarGuiaPwa('android')" style="flex:1; padding:8px 6px; border-radius:10px; font-weight:800; font-size:12px; border:2px solid var(--acento); background:var(--acento); color:var(--primario); cursor:pointer;">🤖 Android (Chrome/Edge)</button>
                <button id="tabGuiaiOS" onclick="cambiarGuiaPwa('ios')" style="flex:1; padding:8px 6px; border-radius:10px; font-weight:800; font-size:12px; border:2px solid var(--borde); background:#F8FAFC; color:var(--suave); cursor:pointer;">🍏 iPhone (Safari)</button>
            </div>

            <div id="cuerpoGuiaAndroid" style="background:#F0FDFA; border:1px solid #99F6E4; padding:14px; border-radius:12px; font-size:13px; line-height:1.6; color:#0F766E;">
                <p style="margin-bottom:6px;"><strong>1.</strong> Toca los <strong>tres puntos verticales (⋮)</strong> en la esquina superior del navegador.</p>
                <p style="margin-bottom:6px;"><strong>2.</strong> Toca <strong>«Añadir a la pantalla principal»</strong> o <strong>«Instalar aplicación»</strong>.</p>
                <p style="margin-bottom:6px;"><strong>3.</strong> Confirma tocando <strong>«Instalar»</strong>.</p>
                <p style="margin-top:8px; font-size:12px; color:#115E59; border-top:1px dashed #99F6E4; padding-top:6px;">✓ ¡Listo! El icono de Asista aparecerá en tu teléfono y abrirá a pantalla completa.</p>
            </div>

            <div id="cuerpoGuiaiOS" style="display:none; background:#F8FAFC; border:1px solid #E2E8F0; padding:14px; border-radius:12px; font-size:13px; line-height:1.6; color:#1E293B;">
                <p style="margin-bottom:6px;"><strong>1.</strong> Toca el botón <strong>Compartir</strong> (icono del recuadro con flecha 📤 en Safari).</p>
                <p style="margin-bottom:6px;"><strong>2.</strong> Desliza hacia abajo y presiona <strong>«Añadir a pantalla de inicio»</strong>.</p>
                <p style="margin-bottom:6px;"><strong>3.</strong> Toca <strong>«Añadir»</strong> arriba a la derecha.</p>
                <p style="margin-top:8px; font-size:12px; color:#475569; border-top:1px dashed #CBD5E1; padding-top:6px;">✓ ¡Listo! Asista quedará guardado junto a tus apps.</p>
            </div>

            <button onclick="cerrarModalInstalarApp()" style="margin-top:16px; width:100%; background:var(--primario); color:white; border:none; padding:12px; border-radius:12px; font-weight:800; font-size:14px; cursor:pointer;">Entendido</button>
        </div>
    </div>

    <!-- MODAL: SELECCIONAR DOCENTE -->
    <div class="modal-overlay" id="modalDocente">
        <div class="modal-content">
            <div class="modal-title">👨‍🏫 Identificación del Docente</div>
            <div class="modal-desc">Seleccione su nombre para cargar sus cursos:</div>
            <select id="selectDocenteList" style="margin-bottom: 16px;">
                <option value="">Cargando docentes...</option>
            </select>
            <div style="display: flex; gap: 8px;">
                <button class="btn-touch" style="flex:1; padding:12px;" onclick="document.getElementById('modalDocente').style.display='none'">Cancelar</button>
                <button class="btn-tomar-foto" style="flex:2; margin:0; padding:12px;" onclick="guardarDocenteSeleccionado()">Confirmar y Entrar</button>
            </div>
        </div>
    </div>

    <!-- MODAL: CIERRE Y FIRMA DIGITAL -->
    <div class="modal-overlay" id="modalCierre">
        <div class="modal-content">
            <div class="modal-title">🔒 Cierre de Asistencia</div>
            <div class="modal-desc" id="cierreResumenTxt">Resumen de la sesión de hoy:</div>
            <div style="background: var(--bg); padding: 12px; border-radius: 12px; margin-bottom: 14px; font-size: 13px;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                    <span>Presentes:</span> <strong id="lblCierrePres" style="color: var(--ok);">0</strong>
                </div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                    <span>Retrasos:</span> <strong id="lblCierreRet" style="color: var(--aviso);">0</strong>
                </div>
                <div style="display: flex; justify-content: space-between;">
                    <span>Ausentes:</span> <strong id="lblCierreAus" style="color: var(--rojo);">0</strong>
                </div>
            </div>
            <label style="font-size: 11px; font-weight: 800; color: var(--suave);">FIRMA DIGITAL DEL DOCENTE</label>
            <input type="text" id="txtFirmaDocente" placeholder="Escriba su nombre o cédula para firmar..."
                   style="width: 100%; padding: 10px; border: 1.5px solid var(--borde); border-radius: 10px; margin: 6px 0 16px; font-size: 13px;">
            <div style="display: flex; gap: 8px;">
                <button class="btn-touch" style="flex: 1; padding: 12px;" onclick="cerrarModalCierre()">Cancelar</button>
                <button class="btn-tomar-foto" style="flex: 2; margin: 0; padding: 12px;" onclick="confirmarCierreClase()">Firmar y Cerrar</button>
            </div>
        </div>
    </div>

    <script>
        let cohortes = [];
        let cohorteActual = null;
        let estudiantes = [];
        let sesionCerrada = false;
        let deferredPrompt = null;

        // Gestión de Docente
        let docenteId = localStorage.getItem('asista_docente_id') || null;
        let docenteNombre = localStorage.getItem('asista_docente_nombre') || null;

        // Fecha actual
        const opcionesFecha = { weekday: 'short', day: 'numeric', month: 'short' };
        document.getElementById('txtFecha').textContent = new Date().toLocaleDateString('es-ES', opcionesFecha);

        async function cargarDocentes() {
            try {
                const res = await fetch('/api/docentes');
                const docentes = await res.json();
                const sel = document.getElementById('selectDocenteList');
                sel.innerHTML = '<option value="">-- Seleccione su nombre --</option>';
                docentes.forEach(d => {
                    const opt = document.createElement('option');
                    opt.value = d.id_persona;
                    opt.textContent = `${d.nombre_completo} (${d.total_cohortes} cursos)`;
                    sel.appendChild(opt);
                });
                if (docenteId) sel.value = docenteId;
            } catch(e) {
                console.error(e);
            }
        }

        function abrirModalDocente() {
            cargarDocentes();
            document.getElementById('modalDocente').style.display = 'flex';
        }

        function guardarDocenteSeleccionado() {
            const sel = document.getElementById('selectDocenteList');
            const val = sel.value;
            if (!val) return alert('Por favor seleccione un docente.');
            docenteId = val;
            docenteNombre = sel.options[sel.selectedIndex].text.split('(')[0].trim();
            localStorage.setItem('asista_docente_id', docenteId);
            localStorage.setItem('asista_docente_nombre', docenteNombre);
            actualizarBarraDocente();
            document.getElementById('modalDocente').style.display = 'none';
            cargarCohortes();
        }

        function actualizarBarraDocente() {
            if (docenteNombre) {
                document.getElementById('txtDocenteActivo').textContent = docenteNombre;
                document.getElementById('txtDocenteCargo').textContent = 'Docente Verificado';
            } else {
                document.getElementById('txtDocenteActivo').textContent = 'Docente / Profesor';
                document.getElementById('txtDocenteCargo').textContent = 'Portal Académico Móvil';
            }
        }

        // Gestión de Cohortes
        async function cargarCohortes() {
            const verTodos = document.getElementById('chkVerTodos').checked;
            const url = (docenteId && !verTodos)
                ? `/api/cohortes_activas?id_docente=${docenteId}`
                : '/api/cohortes_activas';

            try {
                const res = await fetch(url);
                cohortes = await res.json();
                const sel = document.getElementById('selectCohorte');
                sel.innerHTML = '';

                if (cohortes.length === 0) {
                    sel.innerHTML = '<option value="">No hay cursos asignados hoy</option>';
                    document.getElementById('cursoDetalle').style.display = 'none';
                    document.getElementById('contenedorEstudiantes').innerHTML = '<div style="text-align:center; padding:20px; color:var(--suave);">No hay cursos activos disponibles.</div>';
                    return;
                }

                cohortes.forEach((c) => {
                    const opt = document.createElement('option');
                    opt.value = c.id_cohorte;
                    opt.textContent = `${c.curso_codigo} - ${c.curso_nombre} (${c.nombre_grupo})`;
                    sel.appendChild(opt);
                });

                cohorteActual = cohortes[0];
                sel.value = cohorteActual.id_cohorte;
                actualizarDetalleCurso();
                cargarEstudiantes();
            } catch(e) {
                console.error('Error cargando cohortes:', e);
            }
        }

        function toggleVerTodos() {
            cargarCohortes();
        }

        function cambiarCurso() {
            const id = parseInt(document.getElementById('selectCohorte').value);
            cohorteActual = cohortes.find(c => c.id_cohorte === id);
            actualizarDetalleCurso();
            cargarEstudiantes();
        }

        function actualizarDetalleCurso() {
            if (!cohorteActual) return;
            const det = document.getElementById('cursoDetalle');
            det.style.display = 'flex';
            document.getElementById('txtAulaDocente').textContent = `Aula: ${cohorteActual.aula || 'Taller Principal'}`;
            document.getElementById('txtInscritos').textContent = `${cohorteActual.total_inscritos || 0} Alumnos`;
        }

        // Estudiantes y Marcaje
        async function cargarEstudiantes() {
            if (!cohorteActual) return;
            try {
                const res = await fetch(`/api/alumnos_cohorte?id_cohorte=${cohorteActual.id_cohorte}`);
                const data = await res.json();
                estudiantes = data.alumnos || data || [];
                const sesion = data.sesion || {};

                sesionCerrada = (sesion.estado === 'Cerrada');
                actualizarEstadoSesionUI(sesion);
                renderizarListaEstudiantes();
            } catch(e) {
                console.error(e);
            }
        }

        function actualizarEstadoSesionUI(sesion) {
            const bar = document.getElementById('sessionStatus');
            const txt = document.getElementById('sessionStatusTxt');
            const btnCierre = document.getElementById('btnAbrirCierre');
            const btnMasivo = document.getElementById('btnMarcarTodos');

            if (sesionCerrada) {
                bar.style.display = 'flex';
                txt.textContent = `🔒 Asistencia Cerrada (${sesion.hora_cierre || 'Hoy'}) - ${sesion.total_presentes || 0} Presentes`;
                btnCierre.style.display = 'none';
                btnMasivo.disabled = true;
                btnMasivo.style.opacity = '0.5';

                const btnReabrir = bar.querySelector('.btn-reabrir');
                if (btnReabrir) {
                    if (usuarioSesion && usuarioSesion.rol_sistema === 'Docente') {
                        btnReabrir.style.display = 'none';
                    } else {
                        btnReabrir.style.display = 'inline-block';
                    }
                }
            } else {
                bar.style.display = 'none';
                btnCierre.style.display = 'flex';
                btnMasivo.disabled = false;
                btnMasivo.style.opacity = '1';
            }
        }

        function filtrarEstudiantesManual() {
            const input = document.getElementById('busquedaManualParticipante');
            filtroBusquedaEstudiantes = input ? input.value.trim().toLowerCase() : '';
            renderizarListaEstudiantes();
        }

        function renderizarListaEstudiantes() {
            const cont = document.getElementById('contenedorEstudiantes');
            cont.innerHTML = '';

            let pres = 0, ret = 0, aus = 0;
            if (estudiantes.length === 0) {
                cont.innerHTML = '<div style="text-align: center; color: var(--suave); padding: 20px; font-size: 13px;">No hay alumnos inscritos en este curso aún.</div>';
                document.getElementById('resumenAsistencia').textContent = '0 alumnos inscritos';
                return;
            }

            estudiantes.forEach(est => {
                if (est.estado === 'Presente') pres++;
                else if (est.estado === 'Retraso') ret++;
                else if (est.estado === 'Ausente') aus++;
            });

            // Filtrar participantes si el usuario escribió en el buscador
            const listaAMostrar = filtroBusquedaEstudiantes ? estudiantes.filter(e => {
                const nom = (e.nombre_completo || (e.nombre + ' ' + e.apellido)).toLowerCase();
                const ced = String(e.cedula || '').toLowerCase();
                return nom.includes(filtroBusquedaEstudiantes) || ced.includes(filtroBusquedaEstudiantes);
            }) : estudiantes;

            if (listaAMostrar.length === 0) {
                cont.innerHTML = `<div style="text-align: center; color: var(--suave); padding: 20px; font-size: 13px;">No se encontró ningún participante que coincida con "${filtroBusquedaEstudiantes}".</div>`;
            } else {
                listaAMostrar.forEach(est => {
                    const card = document.createElement('div');
                    card.id = `card-est-${est.id_persona}`;
                    const estLower = est.estado ? est.estado.toLowerCase() : 'pendiente';
                    card.className = `student-item item-${estLower}`;

                    const estadoTxt = est.estado ? (est.hora ? `${est.estado} (${est.hora})` : est.estado) : 'Pendiente';
                    const disabledAttr = sesionCerrada ? 'disabled' : '';

                    const pctNum = (est.pct_asistencia !== undefined && est.pct_asistencia !== null) ? Number(est.pct_asistencia) : 100.0;
                    const enRiesgo = pctNum < 75.0;
                    const badgeRiesgo = enRiesgo
                        ? `<span style="background:#EF4444; color:#ffffff; font-size:10px; font-weight:800; padding:2px 7px; border-radius:5px; margin-left:6px; display:inline-block; vertical-align:middle; letter-spacing:0.3px; box-shadow:0 1px 3px rgba(239,68,68,0.4);">⚠️ RIESGO (&lt;75%)</span>`
                        : '';
                    const cedulaStyle = enRiesgo ? 'style="color:#F87171; font-weight:700;"' : '';

                    card.innerHTML = `
                        <div class="student-top">
                            <div>
                                <div class="student-name">${est.nombre_completo} ${badgeRiesgo}</div>
                                <div class="student-cedula" ${cedulaStyle}>C.I. ${est.cedula} &bull; Asistencia: ${pctNum.toFixed(1)}%</div>
                            </div>
                            <span class="status-pill ${estLower}">${estadoTxt}</span>
                        </div>
                        <div class="btn-group">
                            <button class="btn-touch ${est.estado === 'Presente' ? 'active-presente' : ''}" ${disabledAttr}
                                    onclick="marcarManual(${est.id_persona}, '${est.cedula}', 'Presente')">✓ Presente</button>
                            <button class="btn-touch ${est.estado === 'Retraso' ? 'active-retraso' : ''}" ${disabledAttr}
                                    onclick="marcarManual(${est.id_persona}, '${est.cedula}', 'Retraso')">⏱ Tarde</button>
                            <button class="btn-touch ${est.estado === 'Ausente' ? 'active-ausente' : ''}" ${disabledAttr}
                                    onclick="marcarManual(${est.id_persona}, '${est.cedula}', 'Ausente')">✕ Falta</button>
                        </div>
                    `;
                    cont.appendChild(card);
                });
            }

            document.getElementById('resumenAsistencia').textContent =
                `${pres} Presentes | ${ret} Retrasos | ${aus} Ausentes de ${estudiantes.length} inscritos`;
        }

        // --- MARCAJE MANUAL Y ESCANEO ---
        async function marcarManual(idPersona, cedula, estado) {
            if (sesionCerrada) {
                if (usuarioSesion && usuarioSesion.rol_sistema === 'Docente') {
                    alert('La sesión de asistencia de hoy está CERRADA. Solo Directora o Administración pueden autorizar modificaciones.');
                    return;
                }
                if (!confirm('La sesión de hoy está cerrada. ¿Desea reabrirla como personal administrativo?')) {
                    return;
                }
                await reabrirSesion();
            }

            const payload = {
                id_cohorte: cohorteActual.id_cohorte,
                id_persona: idPersona,
                cedula: cedula,
                estado: estado
            };

            try {
                const res = await fetch('/api/marcar_asistencia_curso', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(payload)
                });
                const r = await res.json();
                if (r.ok) {
                    reproducirAudioConfirmacion(true);
                    if (navigator.vibrate) navigator.vibrate(80);
                    mostrarToast(r.estudiante, r.estado, r.hora, r.pct_asistencia);
                    actualizarEstudianteLocal(idPersona, estado, r.hora);
                } else {
                    reproducirAudioConfirmacion(false);
                    alert(r.mensaje || 'Error al guardar');
                }
            } catch(err) {
                // Fallback offline
                guardarOffline(payload);
                reproducirAudioConfirmacion(false);
                mostrarToast('Guardado en Celular (Offline)', estado, 'Pendiente Sync', '--');
                actualizarEstudianteLocal(idPersona, estado, 'Offline');
            }
        }

        function actualizarEstudianteLocal(idPersona, estado, hora) {
            const e = estudiantes.find(x => x.id_persona === idPersona);
            if (e) {
                e.estado = estado;
                e.hora = hora;
                renderizarListaEstudiantes();
                const card = document.getElementById(`card-est-${idPersona}`);
                if (card) {
                    card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                }
            }
        }

        // ---- SCANNER EN TIEMPO REAL — PROFESOR ----
        let streamActivoProf = null;
        let animFrameIdProf = null;
        let ultimoCodigoProf = null;
        let tsUltimoCodigoProf = 0;
        let linternaEncendida = false;
        let facingModeActual = 'environment';
        let filtroBusquedaEstudiantes = '';
        let marcajeEnCursoProf = false;
        const COOLDOWN_PROF = 2500;

        function establecerEstadoConexionProfesor(estado, texto) {
            const indicador = document.getElementById('estadoConexionProfesor');
            indicador.dataset.state = estado;
            indicador.textContent = texto;
        }

        async function comprobarConexionProfesor() {
            if (marcajeEnCursoProf) return;
            try {
                const respuesta = await fetch('/api/status', {cache: 'no-store'});
                if (!respuesta.ok) throw new Error('Servidor no disponible');
                establecerEstadoConexionProfesor('online', 'Conectado');
            } catch (_) {
                establecerEstadoConexionProfesor('offline', 'Sin conexión');
            }
        }

        // Motores de detección (reutiliza detectorBD y zxingReader del scope global si están)
        let detBDProf = null;
        if ('BarcodeDetector' in window) {
            try { detBDProf = new BarcodeDetector({ formats: ['code_128','code_39','qr_code','ean_13','upc_a','codabar','data_matrix','pdf417','itf','code_93'] }); } catch(e) {}
        }
        function tomarFotoProfesorDirecta() {
            const input = document.getElementById('inputFotoProfesor');
            if (input) input.click();
        }

        // Cámara única con detección local y foto directa en celular
        async function activarCamaraProf() {
            const btn = document.getElementById('btnActivarCamaraProf');
            const visor = document.getElementById('visorCamaraProf');

            const esSeguro = location.protocol === 'https:' || location.hostname === 'localhost' || location.hostname === '127.0.0.1';

            if (!esSeguro || !navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                const httpsUrl = 'https://' + location.hostname + ':8443' + location.pathname;
                const pnl = document.getElementById('panelHttpsAviso');
                if (pnl) {
                    pnl.style.display = 'block';
                    pnl.innerHTML = `
                        <div style="color:#FCD34D; font-weight:800; font-size:14px; margin-bottom:6px;">🎥 Escáner en Tiempo Real</div>
                        <div style="color:#BAE6FD; font-size:12px; line-height:1.5;">
                            Para escanear en tiempo real con video en vivo, abre el portal seguro:<br><br>
                            <a href="${httpsUrl}" style="display:inline-block; background:#0284C7; color:white; padding:10px 14px; border-radius:8px; font-weight:800; text-decoration:none; overflow-wrap:anywhere;">${httpsUrl}</a><br><br>
                            <small style="opacity:0.85;">(Si tu teléfono muestra <i>"La conexión no es privada"</i>, pulsa en <b>Configuración avanzada</b> → <b>Acceder a... (no seguro)</b>).</small>
                        </div>
                    `;
                    pnl.scrollIntoView({behavior:'smooth'});
                } else {
                    location.href = httpsUrl;
                }
                return;
            }

            btn.disabled = true;
            btn.textContent = 'Abriendo...';
            document.getElementById('panelHttpsAviso').style.display = 'none';
            try {
                const stream = await navigator.mediaDevices.getUserMedia({
                    video: { facingMode: { ideal: facingModeActual } },
                    audio: false
                });
                streamActivoProf = stream;
                const video = document.getElementById('videoEscanerProf');
                video.srcObject = stream;
                await video.play();
                visor.style.display = 'block';
                btn.style.display = 'none';
                document.getElementById('estadoCamaraProf').textContent = 'Apunta al código del carnet';
                iniciarBucleLecturaProf(video);
            } catch (err) {
                if (streamActivoProf) {
                    streamActivoProf.getTracks().forEach(track => track.stop());
                    streamActivoProf = null;
                }
                btn.disabled = false;
                btn.innerHTML = '<span>🎥 Iniciar escáner en vivo</span>';
                const panel = document.getElementById('panelHttpsAviso');
                panel.style.display = 'block';
                panel.innerHTML = `
                    <div style="color:#FCD34D; font-weight:800; font-size:14px; margin-bottom:6px;">No se pudo abrir la cámara</div>
                    <div style="color:#BAE6FD; font-size:12px; line-height:1.5;">
                        Verifica los permisos de cámara del navegador y vuelve a intentarlo.
                    </div>
                `;
            }
        }

        async function iniciarBucleLecturaProf(video) {
            const canvas = document.createElement('canvas');
            const context = canvas.getContext('2d', {willReadFrequently: true});
            let ocupado = false;
            let ultimoIntento = 0;
            let lectorZXing = null;
            if (typeof ZXing !== 'undefined' && ZXing && ZXing.BrowserMultiFormatReader) {
                lectorZXing = new ZXing.BrowserMultiFormatReader();
            }

            const leerFotograma = async () => {
                if (!streamActivoProf) return;
                animFrameIdProf = requestAnimationFrame(leerFotograma);
                const ahora = Date.now();
                if (ocupado || video.readyState < 2 || ahora - ultimoIntento < 220) return;
                ocupado = true;
                ultimoIntento = ahora;
                try {
                    let codigo = null;
                    if (detBDProf) {
                        try {
                            const codigos = await detBDProf.detect(video);
                            if (codigos.length) codigo = codigos[0].rawValue;
                        } catch (_) {}
                    }
                    if (!codigo && lectorZXing) {
                        canvas.width = video.videoWidth;
                        canvas.height = video.videoHeight;
                        context.drawImage(video, 0, 0, canvas.width, canvas.height);
                        try {
                            const resultado = await lectorZXing.decodeFromCanvas(canvas);
                            if (resultado) codigo = resultado.getText();
                        } catch (_) {}
                    }
                    const cedula = codigo && (codigo.replace(/[^0-9]/g, '') || codigo.trim());
                    if (cedula && cedula.length >= 5 &&
                        (cedula !== ultimoCodigoProf || ahora - tsUltimoCodigoProf > COOLDOWN_PROF)) {
                        ultimoCodigoProf = cedula;
                        tsUltimoCodigoProf = ahora;
                        document.getElementById('estadoCamaraProf').textContent = 'Código detectado. Registrando...';
                        if (navigator.vibrate) navigator.vibrate([60, 30, 60]);
                        await marcarPorCedulaDetectada(cedula);
                        if (streamActivoProf) {
                            document.getElementById('estadoCamaraProf').textContent = 'Listo. Apunta al siguiente carnet.';
                        }
                    }
                } catch (err) {
                    console.warn('No se pudo leer el fotograma de la cámara:', err);
                } finally {
                    ocupado = false;
                }
            };
            leerFotograma();
        }

        async function detenerCamaraProf() {
            if (animFrameIdProf) { cancelAnimationFrame(animFrameIdProf); animFrameIdProf = null; }
            if (streamActivoProf) {
                streamActivoProf.getTracks().forEach(t => t.stop());
                streamActivoProf = null;
            }
            linternaEncendida = false;
            const btnTorch = document.getElementById('btnTorchProf');
            if (btnTorch) {
                btnTorch.style.background = 'rgba(0,0,0,0.55)';
                btnTorch.title = 'Linterna / Flash';
            }
            document.getElementById('visorCamaraProf').style.display = 'none';
            document.getElementById('videoEscanerProf').srcObject = null;
            const btn = document.getElementById('btnActivarCamaraProf');
            btn.disabled = false;
            btn.style.display = '';
            btn.innerHTML = '<span>📷 Iniciar Escáner en Vivo</span>';
        }

        async function toggleLinternaProf() {
            if (!streamActivoProf) return;
            const track = streamActivoProf.getVideoTracks()[0];
            if (!track) return;
            try {
                const capabilities = track.getCapabilities ? track.getCapabilities() : {};
                if (!capabilities.torch) {
                    mostrarToast("Linterna no disponible", "Este dispositivo no soporta flash web", "--:--", "", true);
                    return;
                }
                linternaEncendida = !linternaEncendida;
                await track.applyConstraints({
                    advanced: [{ torch: linternaEncendida }]
                });
                const btnTorch = document.getElementById('btnTorchProf');
                if (btnTorch) {
                    btnTorch.style.background = linternaEncendida ? '#F59E0B' : 'rgba(0,0,0,0.55)';
                    btnTorch.title = linternaEncendida ? 'Apagar linterna' : 'Encender linterna';
                }
            } catch(e) {
                console.warn("Error al alternar linterna:", e);
                mostrarToast("Aviso linterna", "No se pudo activar el flash", "--:--", "", true);
            }
        }

        async function alternarCamaraProf() {
            facingModeActual = (facingModeActual === 'environment') ? 'user' : 'environment';
            detenerCamaraProf();
            await activarCamaraProf();
        }

        // --- ESCÁNER POR FOTO NATIVA (fallback) ---
        async function procesarFotoCarnetProfesor(event) {
            const file = event.target.files[0];
            if (!file) return;

            mostrarToast("📸 Leyendo carnet...", "Analizando código de barras de la foto...", "--:--", "");

            const reader = new FileReader();
            reader.onload = function(e) {
                const img = new Image();
                img.onload = async function() {
                    // Pre-escalado en canvas para máxima velocidad y nitidez (máx 1200px)
                    let w = img.width, h = img.height;
                    const MAX = 1200;
                    if (w > MAX || h > MAX) {
                        if (w > h) { h = Math.round(h * MAX / w); w = MAX; }
                        else { w = Math.round(w * MAX / h); h = MAX; }
                    }
                    const canvas = document.createElement('canvas');
                    canvas.width = w; canvas.height = h;
                    const ctx = canvas.getContext('2d');
                    ctx.drawImage(img, 0, 0, w, h);

                    let codigo = null;

                    // Funcion auxiliar: intentar BarcodeDetector con un canvas dado
                    async function intentarDetectarProf(srcCanvas) {
                        if (!('BarcodeDetector' in window)) return null;
                        try {
                            const det = new BarcodeDetector({ formats: ['code_128', 'code_39', 'qr_code', 'ean_13', 'upc_a', 'codabar', 'data_matrix', 'pdf417'] });
                            const bs = await det.detect(srcCanvas);
                            if (bs.length > 0) return bs[0].rawValue.trim();
                        } catch(e) {}
                        return null;
                    }

                    // Intento 1: Canvas original
                    codigo = await intentarDetectarProf(canvas);

                    // Intento 2: Alto contraste
                    if (!codigo) {
                        const c2 = document.createElement('canvas');
                        c2.width = canvas.width; c2.height = canvas.height;
                        const cx2 = c2.getContext('2d');
                        cx2.filter = 'contrast(2) brightness(1.1) grayscale(1)';
                        cx2.drawImage(canvas, 0, 0);
                        codigo = await intentarDetectarProf(c2);
                    }

                    // Intento 3: Escala 2x si imagen pequeña
                    if (!codigo && canvas.width < 800) {
                        const c3 = document.createElement('canvas');
                        c3.width = canvas.width * 2; c3.height = canvas.height * 2;
                        const cx3 = c3.getContext('2d');
                        cx3.imageSmoothingEnabled = false;
                        cx3.drawImage(canvas, 0, 0, c3.width, c3.height);
                        codigo = await intentarDetectarProf(c3);
                    }

                    // Intento 4: ZXing si disponible
                    if (!codigo && typeof ZXing !== 'undefined' && ZXing) {
                        try {
                            const codeReader = new ZXing.BrowserMultiFormatReader();
                            const res = await codeReader.decodeFromCanvas(canvas);
                            if (res) codigo = res.getText().trim();
                        } catch(err) {}
                    }

                    if (codigo) {
                        const cedulaDetectada = codigo.replace(/[^0-9]/g, '') || codigo.trim();
                        await marcarPorCedulaDetectada(cedulaDetectada);
                    } else {
                        reproducirAudioConfirmacion(false);
                        mostrarToast("No se detectó el código", "Tome la foto más de cerca o escriba la cédula manualmente.", "--:--", "", true);
                    }
                };
                img.src = e.target.result;
            };
            reader.readAsDataURL(file);
            event.target.value = "";
        }

        // --- ENTRADA RÁPIDA POR TECLADO O VOZ ---
        async function enviarCedulaManualProfesor() {
            const input = document.getElementById('inputCedulaManualProfesor');
            const cedula = input.value.trim().replace(/[^0-9]/g, '');
            if (!cedula) return alert('Por favor escriba o dicte el número de cédula.');
            input.value = "";
            input.blur();
            await marcarPorCedulaDetectada(cedula);
        }

        async function marcarPorCedulaDetectada(cedula) {
            if (!cohorteActual) return alert('Seleccione un curso activo primero.');

            // Buscar alumno en la cohorte actual
            const est = estudiantes.find(e => String(e.cedula).trim() === String(cedula).trim());
            const idPersona = est ? est.id_persona : null;

            // Validación anti-duplicados previa: no registrar dos veces al mismo participante en la misma sesión
            if (est && est.estado === 'Presente') {
                reproducirAudioAviso();
                if (navigator.vibrate) navigator.vibrate([60, 40, 60]);
                mostrarToast(est.nombre_completo, `Ya registrado (${est.hora || 'Hoy'})`, est.hora || '--:--', est.pct_asistencia || 100, false, true);
                return;
            }

            const payload = {
                id_cohorte: cohorteActual.id_cohorte,
                id_persona: idPersona,
                cedula: cedula,
                estado: 'Presente'
            };

            marcajeEnCursoProf = true;
            establecerEstadoConexionProfesor('sending', 'Enviando…');
            try {
                const res = await fetch('/api/marcar_asistencia_curso', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(payload)
                });
                const r = await res.json();
                establecerEstadoConexionProfesor('online', 'Conectado');
                if (r.ok) {
                    reproducirAudioConfirmacion(true);
                    if (navigator.vibrate) navigator.vibrate([80, 40, 80]);
                    mostrarToast(r.estudiante, r.estado, r.hora, r.pct_asistencia);
                    if (idPersona) {
                        actualizarEstudianteLocal(idPersona, 'Presente', r.hora);
                    } else {
                        cargarEstudiantes();
                    }
                } else {
                    reproducirAudioConfirmacion(false);
                    mostrarToast(r.mensaje || `C.I. ${cedula} no inscrita`, "No se pudo registrar", "--:--", "", true);
                }
            } catch(e) {
                establecerEstadoConexionProfesor('offline', 'Sin conexión');
                guardarOffline(payload);
                reproducirAudioConfirmacion(false);
                mostrarToast('Guardado Offline en Celular', 'Presente', 'Pendiente Sync', '--');
                if (idPersona) actualizarEstudianteLocal(idPersona, 'Presente', 'Offline');
            } finally {
                marcajeEnCursoProf = false;
            }
        }

        // Marcaje Masivo
        async function marcarTodosPresentes() {
            if (sesionCerrada) return alert('La sesión está cerrada.');
            if (!confirm(`¿Marcar a todos los ${estudiantes.length} alumnos como PRESENTES hoy?`)) return;

            try {
                const res = await fetch('/api/marcar_masivo_curso', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ id_cohorte: cohorteActual.id_cohorte, estado: 'Presente' })
                });
                const r = await res.json();
                if (r.ok) {
                    reproducirAudioConfirmacion(true);
                    cargarEstudiantes();
                } else {
                    alert('Error en marcaje masivo: ' + r.mensaje);
                }
            } catch(e) {
                alert('Sin conexión para marcaje masivo.');
            }
        }

        // --- FEEDBACK AUDITIVO Y TOAST ---
        function reproducirAudioAviso() {
            try {
                const ctx = new (window.AudioContext || window.webkitAudioContext)();
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();
                osc.connect(gain);
                gain.connect(ctx.destination);
                osc.frequency.setValueAtTime(440, ctx.currentTime);
                osc.frequency.setValueAtTime(554, ctx.currentTime + 0.08);
                gain.gain.setValueAtTime(0.25, ctx.currentTime);
                gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.18);
                osc.start();
                osc.stop(ctx.currentTime + 0.18);
            } catch(e) {}
        }

        function reproducirAudioConfirmacion(exito = true) {
            try {
                const ctx = new (window.AudioContext || window.webkitAudioContext)();
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();
                osc.connect(gain);
                gain.connect(ctx.destination);

                if (exito) {
                    osc.frequency.setValueAtTime(659, ctx.currentTime);
                    osc.frequency.exponentialRampToValueAtTime(880, ctx.currentTime + 0.12);
                    gain.gain.setValueAtTime(0.3, ctx.currentTime);
                    gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.15);
                    osc.start();
                    osc.stop(ctx.currentTime + 0.15);
                } else {
                    osc.frequency.setValueAtTime(320, ctx.currentTime);
                    gain.gain.setValueAtTime(0.3, ctx.currentTime);
                    gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.25);
                    osc.start();
                    osc.stop(ctx.currentTime + 0.25);
                }
            } catch(e) {}
        }

        function mostrarToast(nombre, estado, hora, pct, esError = false, esDuplicado = false) {
            const t = document.getElementById('toastConfirm');
            t.className = `toast-confirm ${esDuplicado ? 'toast-duplicate' : (esError ? 'toast-error' : '')}`;
            document.getElementById('toastTitle').textContent = esDuplicado ? '⚠ Marcaje duplicado' : (esError ? '✕ Aviso' : `✓ ${estado}`);
            document.getElementById('toastNombre').textContent = nombre;
            document.getElementById('toastMeta').textContent = pct ? `Hora: ${hora} &bull; Asistencia: ${pct}%` : `Hora: ${hora}`;
            t.style.display = 'block';
        }

        // --- SISTEMA OFFLINE CON DEDUPLICACIÓN ---
        function guardarOffline(item) {
            let cola = JSON.parse(localStorage.getItem('asista_offline_queue') || '[]');
            const idx = cola.findIndex(x =>
                String(x.id_cohorte) === String(item.id_cohorte) &&
                ( (item.id_persona && String(x.id_persona) === String(item.id_persona)) ||
                  (item.cedula && String(x.cedula) === String(item.cedula)) )
            );
            if (idx >= 0) {
                cola[idx] = item;
            } else {
                cola.push(item);
            }
            localStorage.setItem('asista_offline_queue', JSON.stringify(cola));
            actualizarOfflineUI();
        }

        function actualizarOfflineUI() {
            let cola = JSON.parse(localStorage.getItem('asista_offline_queue') || '[]');
            const bar = document.getElementById('offlineBar');
            if (cola.length > 0) {
                bar.style.display = 'flex';
                document.getElementById('txtOfflineCount').textContent = cola.length;
            } else {
                bar.style.display = 'none';
            }
        }

        async function sincronizarOffline() {
            let cola = JSON.parse(localStorage.getItem('asista_offline_queue') || '[]');
            if (cola.length === 0) return;

            try {
                const res = await fetch('/api/sincronizar_offline_curso', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({registros: cola})
                });
                const r = await res.json();
                if (r.ok) {
                    localStorage.removeItem('asista_offline_queue');
                    actualizarOfflineUI();
                    alert(`✓ ¡Éxito! Se sincronizaron ${r.procesados} asistencias con el servidor principal.`);
                    cargarEstudiantes();
                } else {
                    alert('Error en servidor al sincronizar: ' + r.mensaje);
                }
            } catch(e) {
                alert('Aún no hay conexión con la laptop. Asegúrese de estar en la misma red Wi-Fi.');
            }
        }

        window.addEventListener('online', () => { sincronizarOffline(); });

        // --- CIERRE Y FIRMA DIGITAL ---
        function abrirModalCierre() {
            if (!cohorteActual) return;
            let pres = 0, ret = 0, aus = 0;
            estudiantes.forEach(e => {
                if (e.estado === 'Presente') pres++;
                else if (e.estado === 'Retraso') ret++;
                else aus++;
            });

            document.getElementById('lblCierrePres').textContent = pres;
            document.getElementById('lblCierreRet').textContent = ret;
            document.getElementById('lblCierreAus').textContent = aus;
            document.getElementById('txtFirmaDocente').value = docenteNombre || '';
            document.getElementById('modalCierre').style.display = 'flex';
        }

        function cerrarModalCierre() {
            document.getElementById('modalCierre').style.display = 'none';
        }

        async function confirmarCierreClase() {
            const firma = document.getElementById('txtFirmaDocente').value.trim();
            if (!firma) return alert('Por favor ingrese su firma/nombre para validar el cierre.');

            try {
                const res = await fetch('/api/cerrar_sesion_clase', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        id_cohorte: cohorteActual.id_cohorte,
                        id_docente: docenteId,
                        firma_docente: firma
                    })
                });
                const r = await res.json();
                if (r.ok) {
                    cerrarModalCierre();
                    alert(`✓ Sesión cerrada con éxito a las ${r.resumen.hora_cierre}.\nFirma: ${firma}`);
                    cargarEstudiantes();
                } else {
                    alert('Error al cerrar sesión: ' + r.mensaje);
                }
            } catch(e) {
                alert('Error al comunicarse con el servidor: ' + e);
            }
        }

        async function reabrirSesion() {
            if (usuarioSesion && usuarioSesion.rol_sistema === 'Docente') {
                alert('Permiso denegado: solo personal Directivo o de Administración puede autorizar la reapertura de una sesión cerrada.');
                return;
            }
            if (!confirm('¿Desea reabrir la sesión de asistencia para realizar correcciones?')) return;
            try {
                const res = await fetch('/api/reabrir_sesion_clase', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${tokenSesion || ''}`
                    },
                    body: JSON.stringify({ id_cohorte: cohorteActual.id_cohorte })
                });
                const r = await res.json();
                if (r.ok) {
                    alert('✓ Sesión reabierta exitosamente.');
                    cargarEstudiantes();
                } else {
                    alert(r.mensaje || 'Error al reabrir sesión');
                }
            } catch(e) {
                alert('Error al reabrir sesión: ' + e);
            }
        }

        // --- PWA INSTALACIÓN ---
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/sw.js').catch(function() {});
        }

        window.addEventListener('beforeinstallprompt', (e) => {
            e.preventDefault();
            deferredPrompt = e;
            const banner = document.getElementById('pwaBanner');
            if (banner && sessionStorage.getItem('pwa_profesor_dismissed') !== '1') {
                banner.style.display = 'flex';
            }
        });

        const esStandalone = window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone === true;
        if (esStandalone || sessionStorage.getItem('pwa_profesor_dismissed') === '1') {
            const banner = document.getElementById('pwaBanner');
            if (banner) banner.style.display = 'none';
        } else {
            const banner = document.getElementById('pwaBanner');
            if (banner) banner.style.display = 'flex';
        }

        function cerrarBannerPwa() {
            sessionStorage.setItem('pwa_profesor_dismissed', '1');
            const banner = document.getElementById('pwaBanner');
            if (banner) banner.style.display = 'none';
        }

        function instalarPwa() {
            if (deferredPrompt) {
                deferredPrompt.prompt();
                deferredPrompt.userChoice.then((choiceResult) => {
                    if (choiceResult.outcome === 'accepted') {
                        cerrarBannerPwa();
                    }
                    deferredPrompt = null;
                });
            } else {
                abrirModalInstalarApp();
            }
        }

        function abrirModalInstalarApp() {
            document.getElementById('modalInstalarApp').style.display = 'flex';
        }

        function cerrarModalInstalarApp() {
            document.getElementById('modalInstalarApp').style.display = 'none';
        }

        function cambiarGuiaPwa(plataforma) {
            const btnAnd = document.getElementById('tabGuiaAndroid');
            const btnIos = document.getElementById('tabGuiaiOS');
            const gAnd = document.getElementById('cuerpoGuiaAndroid');
            const gIos = document.getElementById('cuerpoGuiaiOS');
            if (plataforma === 'android') {
                btnAnd.style.background = 'var(--acento)';
                btnAnd.style.color = 'var(--primario)';
                btnAnd.style.borderColor = 'var(--acento)';
                btnIos.style.background = '#F8FAFC';
                btnIos.style.color = 'var(--suave)';
                btnIos.style.borderColor = 'var(--borde)';
                gAnd.style.display = 'block';
                gIos.style.display = 'none';
            } else {
                btnIos.style.background = 'var(--acento)';
                btnIos.style.color = 'var(--primario)';
                btnIos.style.borderColor = 'var(--acento)';
                btnAnd.style.background = '#F8FAFC';
                btnAnd.style.color = 'var(--suave)';
                btnAnd.style.borderColor = 'var(--borde)';
                gIos.style.display = 'block';
                gAnd.style.display = 'none';
            }
        }

        // Inicialización
        window.addEventListener('DOMContentLoaded', () => {
            actualizarBarraDocente();
            actualizarOfflineUI();
            cargarCohortes();
            comprobarConexionProfesor();
            setInterval(comprobarConexionProfesor, 15000);
        });
    </script>
</body>
</html>"""


HTML_SCANNER = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Asista - Escáner Móvil de Portería</title>
    <!-- PWA y Soporte Móvil Nativo -->
    <link rel="manifest" href="/manifest.json">
    <meta name="theme-color" content="#040444">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="Asista Portería">
    <link rel="apple-touch-icon" href="/static/icon-192.png">
    <link rel="icon" type="image/x-icon" href="/favicon.ico">
    <!-- ZXing servido localmente - sin depender de internet -->
    <script src="/static/zxing.js"></script>
    <style>
        :root {
            --primario: __ASISTA_OSCURO_PRIMARY__;
            --primario-dark: __ASISTA_OSCURO_PRIMARY_HOVER__;
            --acento: __ASISTA_OSCURO_ACCENT__;
            --ok: __ASISTA_OSCURO_ACCENT__;
            --aviso: __ASISTA_OSCURO_DANGER__;
            --aviso-bg: __ASISTA_OSCURO_DANGER_BG__;
            --aviso-texto: __ASISTA_OSCURO_DANGER_TEXT__;
            --rojo: __ASISTA_OSCURO_DANGER__;
            --bg: __ASISTA_OSCURO_BG__;
            --card: __ASISTA_OSCURO_CARD__;
            --texto: __ASISTA_OSCURO_TEXT__;
            --suave: __ASISTA_OSCURO_MUTED__;
            --borde: __ASISTA_OSCURO_BORDER__;
        }
        @media (prefers-color-scheme: light) {
            :root {
                --primario: __ASISTA_CLARO_PRIMARY__;
                --primario-dark: __ASISTA_CLARO_PRIMARY_HOVER__;
                --acento: __ASISTA_CLARO_ACCENT__;
                --ok: __ASISTA_CLARO_ACCENT__;
                --aviso: __ASISTA_CLARO_DANGER__;
                --aviso-bg: __ASISTA_CLARO_DANGER_BG__;
                --aviso-texto: __ASISTA_CLARO_DANGER_TEXT__;
                --rojo: __ASISTA_CLARO_DANGER__;
                --bg: __ASISTA_CLARO_BG__;
                --card: __ASISTA_CLARO_CARD__;
                --texto: __ASISTA_CLARO_TEXT__;
                --suave: __ASISTA_CLARO_MUTED__;
                --borde: __ASISTA_CLARO_BORDER__;
            }
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        body { background: var(--bg); color: var(--texto); padding-bottom: 24px; }
        #pwaBanner, #modalInstalarApp { display: none !important; }
        .brand-header { max-width: 500px; margin: 12px auto 8px; padding: 0 12px; }
        .brand-frame {
            min-height: 72px; display: grid; place-items: center; padding: 8px;
            background: linear-gradient(180deg, #12131B, #0C0D18);
            border: 1px solid var(--borde); border-radius: 16px;
        }
        .brand-frame img { display: block; max-height: 52px; width: auto; }
        .mobile-page-heading { margin-bottom: 12px; }
        .header-actions { display: flex; align-items: center; gap: 6px; }
        .btn-switch {
            background: var(--primario);
            color: white;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 700;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 4px;
        }
        .btn-pwa-header {
            background: var(--primario);
            border: 1px solid var(--acento);
            color: white;
            font-size: 11px;
            padding: 4px 10px;
            border-radius: 20px;
            font-weight: 700;
            cursor: pointer;
        }
        .header-title-row { display: flex; align-items: center; justify-content: space-between; margin-top: 10px; }
        .header-title { font-size: 18px; font-weight: 800; letter-spacing: -0.3px; color: var(--texto); }
        .clock-badge {
            display: inline-block;
            background: rgba(86, 225, 232, 0.1);
            padding: 3px 10px;
            border-radius: 14px;
            font-size: 12px;
            font-weight: 700;
            color: var(--acento);
        }

        .container { max-width: 500px; margin: 12px auto; padding: 0 12px; }

        /* Banner PWA */
        .pwa-banner {
            background: linear-gradient(135deg, #0A192F, #1E3A6D);
            color: white;
            padding: 10px 14px;
            border-radius: 12px;
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }
        .btn-pwa-install {
            background: var(--acento);
            color: var(--primario);
            border: none;
            padding: 6px 12px;
            border-radius: 8px;
            font-size: 11px;
            font-weight: 800;
            cursor: pointer;
        }

        .card {
            background: var(--card);
            border-radius: 14px;
            padding: 18px;
            margin-bottom: 14px;
            box-shadow: none;
            border: 1px solid var(--borde);
        }

        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }
        .card-title { font-size: 15px; font-weight: 800; color: var(--texto); }
        .badge-status {
            background: rgba(86, 225, 232, 0.1);
            color: var(--acento);
            font-size: 10px;
            font-weight: 700;
            padding: 2px 6px;
            border-radius: 10px;
        }
        .badge-status[data-state="checking"], .badge-status[data-state="sending"] {
            background: rgba(86, 225, 232, 0.1); color: var(--acento);
        }
        .badge-status[data-state="online"] { background: rgba(86, 225, 232, 0.1); color: var(--acento); }
        .badge-status[data-state="offline"] { background: var(--aviso-bg); color: var(--aviso-texto); }
        .secondary-feed { display: none; }

        .btn-tomar-foto {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            width: 100%;
            background: var(--acento);
            color: var(--primario);
            padding: 16px 20px;
            border-radius: 14px;
            font-size: 16px;
            font-weight: 800;
            border: none;
            cursor: pointer;
            box-shadow: none;
            margin-bottom: 12px;
            transition: transform 0.1s ease;
        }
        .btn-tomar-foto:active { transform: scale(0.98); }

        .notice-box {
            background: var(--card);
            border: 1px solid var(--borde);
            color: var(--suave);
            padding: 10px 12px;
            border-radius: 10px;
            font-size: 12px;
            margin-bottom: 12px;
            line-height: 1.4;
        }

        /* Formulario Manual */
        .manual-form { display: flex; gap: 8px; margin-top: 6px; }
        .input-cedula {
            flex: 1;
            padding: 12px 14px;
            border: 1px solid var(--borde);
            border-radius: 12px;
            font-size: 15px;
            font-weight: 700;
            background: var(--card);
            color: var(--texto);
            outline: none;
        }
        .input-cedula:focus { border-color: var(--acento); }
        .btn-marcar {
            background: var(--acento);
            color: var(--primario);
            border: none;
            padding: 0 18px;
            border-radius: 12px;
            font-size: 14px;
            font-weight: 800;
            cursor: pointer;
        }
        .capture-fallback {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-width: 44px;
            padding: 0 10px;
            border: 1px solid var(--borde);
            border-radius: 12px;
            background: var(--card);
            color: var(--acento);
            font-size: 19px;
            cursor: pointer;
        }

        /* Notificación de resultado */
        .result-box {
            padding: 14px 16px;
            border-radius: 12px;
            border: 1px solid var(--borde);
            margin-bottom: 14px;
            display: none;
            animation: slideDown 0.3s ease;
        }
        @keyframes slideDown { from { opacity: 0; transform: translateY(-8px); } to { opacity: 1; transform: translateY(0); } }
        .result-success { background: rgba(86, 225, 232, 0.08); border: 1px solid var(--borde); color: var(--texto); }
        .result-warning, .result-error { background: var(--aviso-bg); border: 1px solid var(--aviso); color: var(--aviso-texto); }
        .res-nombre { font-size: 16px; font-weight: 800; margin-bottom: 4px; }
        .res-det { font-size: 13px; font-weight: 600; }

        /* Historial */
        .feed-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 0;
            border-bottom: 1px solid var(--borde);
        }
        .feed-item:last-child { border-bottom: none; }
        .feed-nombre { font-weight: 700; font-size: 14px; color: var(--texto); }
        .feed-meta { font-size: 11px; color: var(--suave); margin-top: 2px; }
        .feed-badge {
            font-size: 11px;
            font-weight: 800;
            padding: 4px 10px;
            border-radius: 10px;
        }
        .badge-presente { background: rgba(86, 225, 232, 0.1); color: var(--acento); }
        .badge-retraso { background: var(--aviso-bg); color: var(--aviso-texto); }
        .badge-salida { background: rgba(86, 225, 232, 0.1); color: var(--acento); }

        /* Modales */
        .modal-overlay {
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(4, 4, 68, 0.9);
            display: none;
            align-items: center;
            justify-content: center;
            padding: 16px;
            z-index: 9999;
        }
        .modal-content {
            background: var(--card);
            border: 1px solid var(--borde);
            border-radius: 14px;
            padding: 22px;
            width: 100%;
            max-width: 440px;
            box-shadow: none;
        }
        .modal-title { font-size: 17px; font-weight: 800; color: var(--primario); margin-bottom: 6px; }
        .modal-desc { font-size: 12px; color: var(--suave); margin-bottom: 14px; }
    </style>
</head>
<body>

    <header class="brand-header"><div class="brand-frame"><img src="{{ url_for('static', filename='img/logo.png') }}" alt="Escudo de la U.E.P. Prof. Aristóbulo Istúriz, código PD31212303"></div></header>

    <div class="container">
        <div class="mobile-page-heading">
            <div class="header-title-row">
                <div class="header-title">Portería General</div>
                <span class="clock-badge" id="reloj">--:--:--</span>
            </div>
        </div>
        <!-- Banner PWA -->
        <div class="pwa-banner" id="pwaBanner" style="display: none;">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 24px;">📲</span>
                <div>
                    <strong style="font-size: 13px;">Instalar Portería como App</strong>
                    <div style="font-size: 11px; opacity: 0.85;">Acceso directo en pantalla de inicio</div>
                </div>
            </div>
            <div style="display: flex; align-items: center; gap: 8px;">
                <button class="btn-pwa-install" onclick="instalarPwa()">Instalar</button>
                <button onclick="cerrarBannerPwa()" title="Ocultar" style="background:none; border:none; color:white; font-size:16px; cursor:pointer; padding:4px 6px; opacity:0.75; line-height:1;">&times;</button>
            </div>
        </div>

        <!-- Banner para cambiar a HTTPS si está en HTTP -->
        <div id="bannerHttps" style="display:none; background:var(--card); color:var(--texto); padding:12px 14px; border:1px solid var(--borde); border-radius:12px; margin-bottom:12px; align-items:center; justify-content:space-between;">
            <div style="display:flex; align-items:center; gap:8px;">
                <span style="font-size:22px;">🎥</span>
                <div style="font-size:12px; line-height:1.3;">
                    <strong>¿Escanear en Tiempo Real?</strong><br>
                    <span style="font-size:11px; opacity:0.9;">Activa el video en vivo en tu teléfono</span>
                </div>
            </div>
            <a id="btnIrHttps" href="#" style="background:var(--acento); color:var(--primario); padding:8px 12px; border-radius:8px; font-size:11px; font-weight:800; text-decoration:none; white-space:nowrap;">Activar En Vivo</a>
        </div>

        <!-- Escáner en Tiempo Real -->
        <div class="card">
            <div class="card-header">
                <span class="card-title">📷 Escáner de carnet</span>
                <span class="badge-status" id="estadoServidor" data-state="checking" aria-live="polite">Comprobando conexión…</span>
            </div>

            <!-- Visor de cámara en tiempo real -->
            <div id="visorCamara" style="display:none; position:relative; border-radius:14px; overflow:hidden; background:#08082D; margin-bottom:12px;">
                <video id="videoEscaner" autoplay playsinline muted
                    style="width:100%; display:block; border-radius:14px; max-height:260px; object-fit:cover;"></video>
                <!-- Marco guía de escaneo -->
                <div style="position:absolute; top:50%; left:50%; transform:translate(-50%,-54%);
                    width:72%; height:38%; border:2px solid var(--acento);
                    border-radius:10px; box-shadow:0 0 0 9999px rgba(0,0,0,0.45);
                    pointer-events:none;">
                    <div style="position:absolute; top:-2px; left:-2px; width:22px; height:22px; border-top:3px solid var(--acento); border-left:3px solid var(--acento); border-radius:4px 0 0 0;"></div>
                    <div style="position:absolute; top:-2px; right:-2px; width:22px; height:22px; border-top:3px solid var(--acento); border-right:3px solid var(--acento); border-radius:0 4px 0 0;"></div>
                    <div style="position:absolute; bottom:-2px; left:-2px; width:22px; height:22px; border-bottom:3px solid var(--acento); border-left:3px solid var(--acento); border-radius:0 0 0 4px;"></div>
                    <div style="position:absolute; bottom:-2px; right:-2px; width:22px; height:22px; border-bottom:3px solid var(--acento); border-right:3px solid var(--acento); border-radius:0 0 4px 0;"></div>
                    <div id="lineaEscaneo" style="position:absolute; top:0; left:0; right:0; height:2px; background:linear-gradient(90deg,transparent,var(--acento),transparent); animation:scanLine 1.8s ease-in-out infinite;"></div>
                </div>
                <div id="estadoCamara" style="position:absolute; bottom:8px; left:0; right:0; text-align:center; color:white; font-size:12px; font-weight:700; text-shadow:0 1px 3px rgba(0,0,0,0.8);">
                    Apunte al código de barras del carnet
                </div>
                <button onclick="detenerCamara()" style="position:absolute; top:8px; right:8px; background:rgba(0,0,0,0.55); border:none; color:white; border-radius:50%; width:32px; height:32px; font-size:16px; cursor:pointer; display:flex; align-items:center; justify-content:center;">✕</button>
            </div>

            <style>
                @keyframes scanLine { 0%{top:0} 50%{top:calc(100% - 2px)} 100%{top:0} }
            </style>

            <!-- Botones de Escaneo por Cámara -->
            <div style="display: flex;">
                <button type="button" class="btn-tomar-foto" id="btnActivarCamara"
                    style="flex: 1; margin: 0; font-size:16px;"
                    onclick="activarCamara()">
                    <span>📷 Iniciar Escáner en Vivo</span>
                </button>
            </div>

            <!-- Confirmación persistente del último marcaje, bajo el visor -->
            <div id="resultado" class="result-box" aria-live="polite"></div>
        </div>

        <!-- Historial de Hoy -->
        <div class="card secondary-feed">
            <div class="card-header">
                <span class="card-title">📋 Últimos Marcajes de Hoy</span>
                <span style="font-size: 12px; color: var(--suave);" id="contadorHoy">0 asistencias</span>
            </div>
            <div id="listaFeed">
                <div style="text-align: center; color: var(--suave); padding: 16px; font-size: 13px;">
                    Esperando marcajes...
                </div>
            </div>
        </div>
    </div>

    <!-- MODAL PWA -->
    <div class="modal-overlay" id="modalInstalarApp">
        <div class="modal-content">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                <div class="modal-title" style="margin-bottom:0;">📲 Instalar Asista en tu Celular</div>
                <button onclick="cerrarModalInstalarApp()" style="background:none; border:none; font-size:22px; cursor:pointer; color:var(--suave); line-height:1;">&times;</button>
            </div>
            <div class="modal-desc">Ingresa directamente desde el icono en tu pantalla de inicio como una aplicación nativa:</div>

            <div style="display: flex; gap: 8px; margin-bottom: 14px;">
                <button id="tabGuiaAndroid" onclick="cambiarGuiaPwa('android')" style="flex:1; padding:8px 6px; border-radius:10px; font-weight:800; font-size:12px; border:2px solid var(--acento); background:var(--acento); color:var(--primario); cursor:pointer;">🤖 Android (Chrome/Edge)</button>
                <button id="tabGuiaiOS" onclick="cambiarGuiaPwa('ios')" style="flex:1; padding:8px 6px; border-radius:10px; font-weight:800; font-size:12px; border:2px solid var(--borde); background:#F8FAFC; color:var(--suave); cursor:pointer;">🍏 iPhone (Safari)</button>
            </div>

            <div id="cuerpoGuiaAndroid" style="background:#F0FDFA; border:1px solid #99F6E4; padding:14px; border-radius:12px; font-size:13px; line-height:1.6; color:#0F766E;">
                <p style="margin-bottom:6px;"><strong>1.</strong> Toca los <strong>tres puntos verticales (⋮)</strong> en la esquina del navegador.</p>
                <p style="margin-bottom:6px;"><strong>2.</strong> Toca <strong>«Añadir a la pantalla principal»</strong> o <strong>«Instalar aplicación»</strong>.</p>
                <p style="margin-bottom:6px;"><strong>3.</strong> Confirma tocando <strong>«Instalar»</strong>.</p>
                <p style="margin-top:8px; font-size:12px; color:#115E59; border-top:1px dashed #99F6E4; padding-top:6px;">✓ ¡Listo! Se creará el acceso directo con el icono institucional en tu menú.</p>
            </div>

            <div id="cuerpoGuiaiOS" style="display:none; background:#F8FAFC; border:1px solid #E2E8F0; padding:14px; border-radius:12px; font-size:13px; line-height:1.6; color:#1E293B;">
                <p style="margin-bottom:6px;"><strong>1.</strong> Toca el botón <strong>Compartir</strong> (icono 📤 en Safari).</p>
                <p style="margin-bottom:6px;"><strong>2.</strong> Presiona <strong>«Añadir a pantalla de inicio»</strong>.</p>
                <p style="margin-bottom:6px;"><strong>3.</strong> Toca <strong>«Añadir»</strong>.</p>
            </div>

            <button onclick="cerrarModalInstalarApp()" style="margin-top:16px; width:100%; background:var(--primario); color:white; border:none; padding:12px; border-radius:12px; font-weight:800; font-size:14px; cursor:pointer;">Entendido</button>
        </div>
    </div>

    <script>
        let deferredPrompt = null;

        function reproducirBeep(exito = true) {
            try {
                const ctx = new (window.AudioContext || window.webkitAudioContext)();
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();
                osc.connect(gain);
                gain.connect(ctx.destination);
                
                if (exito) {
                    osc.frequency.setValueAtTime(659, ctx.currentTime);
                    osc.frequency.exponentialRampToValueAtTime(880, ctx.currentTime + 0.12);
                    gain.gain.setValueAtTime(0.3, ctx.currentTime);
                    gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.15);
                    osc.start();
                    osc.stop(ctx.currentTime + 0.15);
                } else {
                    osc.frequency.setValueAtTime(320, ctx.currentTime);
                    gain.gain.setValueAtTime(0.3, ctx.currentTime);
                    gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.25);
                    osc.start();
                    osc.stop(ctx.currentTime + 0.25);
                }
            } catch (e) {}

            if (navigator.vibrate) {
                navigator.vibrate(exito ? [80, 40, 80] : [200]);
            }
        }

        function actualizarReloj() {
            const ahora = new Date();
            document.getElementById('reloj').innerText = ahora.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true });
        }
        setInterval(actualizarReloj, 1000);
        actualizarReloj();

        // Auto-iniciar cámara en vivo al abrir la página
        window.addEventListener('load', async function() {
            await comprobarEstadoServidor();
            setInterval(comprobarEstadoServidor, 15000);
            if (location.protocol !== 'https:' && !window.isSecureContext &&
                location.hostname !== 'localhost' && location.hostname !== '127.0.0.1') {
                const urlSegura = crearUrlHttpsActiva();
                if (urlSegura) {
                    location.replace(urlSegura);
                    return;
                }
                const banner = document.getElementById('bannerHttps');
                const botonHttps = document.getElementById('btnIrHttps');
                banner.style.display = 'flex';
                banner.querySelector('strong').textContent = 'HTTPS no está disponible';
                banner.querySelector('div div span').textContent = 'Cámara en vivo requiere una conexión segura';
                botonHttps.style.display = 'none';
            } else {
                setTimeout(function() {
                    activarCamara();
                }, 800);
            }
        });

        // Cámara nativa del navegador; ZXing local cubre los equipos sin BarcodeDetector.
        let streamCamara = null;
        let frameEscaner = null;
        let ultimoCodigo = null;
        let tsUltimoCodigo = 0;
        let marcajeEnCurso = false;
        let puertoHttpsActivo = null;

        function crearUrlHttpsActiva() {
            if (!puertoHttpsActivo) return null;
            return `https://${location.hostname}:${puertoHttpsActivo}${location.pathname}`;
        }

        function establecerEstadoServidor(estado, texto) {
            const indicador = document.getElementById('estadoServidor');
            indicador.dataset.state = estado;
            indicador.textContent = texto;
        }

        async function comprobarEstadoServidor() {
            if (marcajeEnCurso) return;
            try {
                const respuesta = await fetch('/api/status', {cache: 'no-store'});
                if (!respuesta.ok) throw new Error('Servidor no disponible');
                const servicio = await respuesta.json();
                puertoHttpsActivo = Number(servicio.https_port) || null;
                establecerEstadoServidor('online', 'En línea');
            } catch (_) {
                puertoHttpsActivo = null;
                establecerEstadoServidor('offline', 'Sin conexión');
            }
        }

        const COOLDOWN_MS = 2500;

        // Motor BarcodeDetector nativo (Chrome Android 9+)
        let detectorBD = null;
        if ('BarcodeDetector' in window) {
            try {
                detectorBD = new BarcodeDetector({
                    formats: ['code_128', 'code_39', 'qr_code', 'ean_13', 'upc_a', 'codabar', 'data_matrix', 'pdf417', 'itf', 'code_93']
                });
            } catch(e) { detectorBD = null; }
        }

        async function activarCamara() {
            const btn = document.getElementById('btnActivarCamara');
            const visor = document.getElementById('visorCamara');

            // Si el navegador no permite streaming por ser HTTP en celular, guiar a HTTPS para cámara en tiempo real
            if (!window.isSecureContext || !navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                const httpsUrl = crearUrlHttpsActiva();
                const resBox = document.getElementById('resultado');
                resBox.className = 'result-box result-warning';
                const detalle = httpsUrl
                    ? `Abre esta dirección segura para habilitar la cámara: <a href="${httpsUrl}" style="color:var(--acento);overflow-wrap:anywhere;">${httpsUrl}</a>.`
                    : 'El listener HTTPS no está activo. Reinicia ASISTA y verifica que el puerto HTTPS 8443 esté libre y permitido en el Firewall.';
                resBox.innerHTML = `<div class="res-nombre">La cámara requiere HTTPS</div><div class="res-det" style="margin-top:6px;line-height:1.5;">${detalle}</div>`;
                resBox.style.display = 'block';
                resBox.scrollIntoView({behavior:'smooth'});
                return;
            }

            btn.disabled = true;
            btn.innerHTML = '<span>⏳ Abriendo cámara...</span>';
            try {
                // Intentar primero cámara trasera, luego cualquier cámara
                try {
                    streamCamara = await navigator.mediaDevices.getUserMedia({
                        video: { facingMode: { ideal: 'environment' }, width: { ideal: 1280 }, height: { ideal: 720 } },
                        audio: false
                    });
                } catch (e1) {
                    streamCamara = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
                }
                const video = document.getElementById('videoEscaner');
                video.srcObject = streamCamara;
                await video.play();
                visor.style.display = 'block';
                btn.style.display = 'none';
                document.getElementById('estadoCamara').textContent = 'Apunta el código de barras del carnet al marco cian';
                iniciarLecturaCamara(video);
            } catch (err) {
                if (streamCamara) {
                    streamCamara.getTracks().forEach(track => track.stop());
                    streamCamara = null;
                }
                visor.style.display = 'none';
                btn.disabled = false;
                btn.innerHTML = '<span>📷 Iniciar Escáner en Vivo</span>';
                // Mostrar error amigable
                const resBox = document.getElementById('resultado');
                resBox.className = 'result-box result-warning';
                resBox.innerHTML = '<div class="res-nombre">Cámara bloqueada</div><div class="res-det">Permite el acceso a la cámara en la configuración del navegador y vuelve a iniciar el escáner.</div>';
                resBox.style.display = 'block';
            }
        }

        async function iniciarLecturaCamara(video) {
            const canvas = document.createElement('canvas');
            const context = canvas.getContext('2d', {willReadFrequently: true});
            let ocupado = false;
            let ultimoIntento = 0;
            let lectorZXing = null;
            if (typeof ZXing !== 'undefined' && ZXing && ZXing.BrowserMultiFormatReader) {
                lectorZXing = new ZXing.BrowserMultiFormatReader();
            }

            const leerFotograma = async () => {
                if (!streamCamara) return;
                frameEscaner = requestAnimationFrame(leerFotograma);
                const ahora = Date.now();
                if (ocupado || video.readyState < 2 || ahora - ultimoIntento < 220) return;
                ocupado = true;
                ultimoIntento = ahora;
                try {
                    let codigo = null;
                    if (detectorBD) {
                        try {
                            const codigos = await detectorBD.detect(video);
                            if (codigos.length) codigo = codigos[0].rawValue;
                        } catch (_) {}
                    }
                    if (!codigo && lectorZXing) {
                        canvas.width = video.videoWidth;
                        canvas.height = video.videoHeight;
                        context.drawImage(video, 0, 0, canvas.width, canvas.height);
                        try {
                            const resultado = await lectorZXing.decodeFromCanvas(canvas);
                            if (resultado) codigo = resultado.getText();
                        } catch (_) {}
                    }
                    const cedula = codigo && (codigo.replace(/[^0-9]/g, '') || codigo.trim());
                    if (cedula && cedula.length >= 5 &&
                        (cedula !== ultimoCodigo || ahora - tsUltimoCodigo > COOLDOWN_MS)) {
                        ultimoCodigo = cedula;
                        tsUltimoCodigo = ahora;
                        document.getElementById('estadoCamara').textContent = 'Código detectado. Registrando...';
                        if (navigator.vibrate) navigator.vibrate([60, 30, 60]);
                        await procesarCedula(cedula);
                        if (streamCamara) {
                            document.getElementById('estadoCamara').textContent = 'Listo. Apunta al siguiente carnet.';
                        }
                    }
                } catch (err) {
                    console.warn('No se pudo leer el fotograma de la cámara:', err);
                } finally {
                    ocupado = false;
                }
            };
            leerFotograma();
        }

        async function detenerCamara() {
            if (frameEscaner) {
                cancelAnimationFrame(frameEscaner);
                frameEscaner = null;
            }
            if (streamCamara) {
                streamCamara.getTracks().forEach(track => track.stop());
                streamCamara = null;
            }
            document.getElementById('visorCamara').style.display = 'none';
            document.getElementById('videoEscaner').srcObject = null;
            const btn = document.getElementById('btnActivarCamara');
            btn.disabled = false;
            btn.style.display = '';
            btn.innerHTML = '<span>📷 Iniciar Escáner en Vivo</span>';
        }

        function mostrarErrorConexion(msg) {
            const resBox = document.getElementById('resultado');
            resBox.className = 'result-box result-warning';
            resBox.innerHTML = '<div class="res-nombre">⚠️ Aviso</div><div class="res-det">' + msg + '</div>';
            resBox.style.display = 'block';
        }

        async function procesarCedula(cedula) {
            const resBox = document.getElementById('resultado');
            marcajeEnCurso = true;
            establecerEstadoServidor('sending', 'Enviando…');
            try {
                const response = await fetch('/api/marcar', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ cedula: cedula })
                });

                const data = await response.json();

                establecerEstadoServidor('online', 'En línea');
                if (data.duplicado) {
                    reproducirBeep(false);
                    resBox.className = 'result-box result-warning';
                    const titulo = document.createElement('div');
                    titulo.className = 'res-nombre';
                    titulo.textContent = '⚠ Marcaje duplicado';
                    const detalle = document.createElement('div');
                    detalle.className = 'res-det';
                    detalle.textContent = data.mensaje || `${data.persona || 'La persona'} ya tiene un marcaje reciente.`;
                    resBox.replaceChildren(titulo, detalle);
                    resBox.style.display = 'block';
                    resBox.scrollIntoView({behavior:'smooth', block:'center'});
                    if (navigator.vibrate) navigator.vibrate([80, 40, 80]);
                } else if (data.ok) {
                    reproducirBeep(true);
                    let cls = "result-success";
                    if (data.estado === "Retraso") cls = "result-warning";
                    if (data.tipo === "SALIDA") cls = "result-success";

                    // Nombre: usar nombre+apellido si vienen separados, o el campo "persona" completo
                    const nombreCompleto = (data.nombre && data.apellido)
                        ? (data.nombre + ' ' + data.apellido)
                        : (data.persona || data.nombre_completo || 'Sin nombre');

                    resBox.className = `result-box ${cls}`;
                    resBox.innerHTML = `
                        <div class="res-nombre">${nombreCompleto}</div>
                        <div class="res-det">
                            <b>${data.tipo}</b>: ${data.estado || 'OK'} (${data.hora}) &bull; ${data.tipo_persona || ''} &bull; C.I. ${data.cedula}
                        </div>
                    `;
                    resBox.style.display = "block";
                    resBox.scrollIntoView({behavior:'smooth', block:'center'});
                    if (navigator.vibrate) navigator.vibrate([100, 50, 100, 50, 200]);
                } else {
                    reproducirBeep(false);
                    resBox.className = "result-box result-error";
                    resBox.innerHTML = `
                        <div class="res-nombre">⚠️ No Registrado</div>
                        <div class="res-det">C.I. ${cedula} — ${data.mensaje || 'Cédula no encontrada en el sistema'}</div>
                    `;
                    resBox.style.display = "block";
                    resBox.scrollIntoView({behavior:'smooth', block:'center'});
                    if (navigator.vibrate) navigator.vibrate([300]);
                }
            } catch (err) {
                establecerEstadoServidor('offline', 'Sin conexión');
                reproducirBeep(false);
                resBox.className = "result-box result-error";
                resBox.innerHTML = `
                    <div class="res-nombre">Error de Conexión</div>
                    <div class="res-det">No se pudo conectar con el servidor principal.</div>
                `;
                resBox.style.display = "block";
            } finally {
                marcajeEnCurso = false;
            }
        }

        async function actualizarFeed() {
            try {
                const res = await fetch('/api/registros');
                if (!res.ok) return;
                const rows = await res.json();
                if (!Array.isArray(rows)) return;
                const feed = document.getElementById('listaFeed');
                document.getElementById('contadorHoy').innerText = `${rows.length} marcajes hoy`;

                if (rows.length === 0) {
                    feed.innerHTML = `<div style="text-align: center; color: var(--suave); padding: 16px; font-size: 13px;">No hay marcajes registrados hoy aún.</div>`;
                    return;
                }

                feed.innerHTML = rows.map(r => `
                    <div class="feed-item">
                        <div>
                            <div class="feed-nombre">${r.nombre_completo || ((r.nombre || '') + ' ' + (r.apellido || '')).trim() || r.persona || 'Sin nombre'}</div>
                            <div class="feed-meta">${r.tipo_persona || ''} &bull; C.I. ${r.cedula} &bull; ⏰ ${r.hora_entrada ? r.hora_entrada.slice(0,5) : '--'}</div>
                        </div>
                        <span class="feed-badge ${r.estado === 'Presente' ? 'badge-presente' : (r.estado === 'Retraso' ? 'badge-retraso' : 'badge-salida')}">
                            ${r.estado || 'Presente'}
                        </span>
                    </div>
                `).join('');
            } catch (e) {}
        }

        // PWA
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/sw.js').catch(function() {});
        }

        window.addEventListener('beforeinstallprompt', (e) => {
            e.preventDefault();
            deferredPrompt = e;
            const banner = document.getElementById('pwaBanner');
            if (banner && sessionStorage.getItem('pwa_scanner_dismissed') !== '1') {
                banner.style.display = 'flex';
            }
        });

        const esStandalonePorteria = window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone === true;
        if (esStandalonePorteria || sessionStorage.getItem('pwa_scanner_dismissed') === '1') {
            const banner = document.getElementById('pwaBanner');
            if (banner) banner.style.display = 'none';
        } else {
            const banner = document.getElementById('pwaBanner');
            if (banner) banner.style.display = 'flex';
        }

        function cerrarBannerPwa() {
            sessionStorage.setItem('pwa_scanner_dismissed', '1');
            const banner = document.getElementById('pwaBanner');
            if (banner) banner.style.display = 'none';
        }

        function instalarPwa() {
            if (deferredPrompt) {
                deferredPrompt.prompt();
                deferredPrompt.userChoice.then((choiceResult) => {
                    if (choiceResult.outcome === 'accepted') {
                        cerrarBannerPwa();
                    }
                    deferredPrompt = null;
                });
            } else {
                abrirModalInstalarApp();
            }
        }

        function abrirModalInstalarApp() {
            document.getElementById('modalInstalarApp').style.display = 'flex';
        }

        function cerrarModalInstalarApp() {
            document.getElementById('modalInstalarApp').style.display = 'none';
        }

        function cambiarGuiaPwa(plataforma) {
            const btnAnd = document.getElementById('tabGuiaAndroid');
            const btnIos = document.getElementById('tabGuiaiOS');
            const gAnd = document.getElementById('cuerpoGuiaAndroid');
            const gIos = document.getElementById('cuerpoGuiaiOS');
            if (plataforma === 'android') {
                btnAnd.style.background = 'var(--acento)';
                btnAnd.style.color = 'var(--primario)';
                btnAnd.style.borderColor = 'var(--acento)';
                btnIos.style.background = '#F8FAFC';
                btnIos.style.color = 'var(--suave)';
                btnIos.style.borderColor = 'var(--borde)';
                gAnd.style.display = 'block';
                gIos.style.display = 'none';
            } else {
                btnIos.style.background = 'var(--acento)';
                btnIos.style.color = 'var(--primario)';
                btnIos.style.borderColor = 'var(--acento)';
                btnAnd.style.background = '#F8FAFC';
                btnAnd.style.color = 'var(--suave)';
                btnAnd.style.borderColor = 'var(--borde)';
                gIos.style.display = 'block';
                gAnd.style.display = 'none';
            }
        }

    </script>
</body>
</html>"""


class AsistaHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Silenciar logs ruidosos en consola, escribir solo en archivo
        logging.info("%s - - [%s] %s" % (self.address_string(), self.log_date_time_string(), format % args))

    def _sesion_api_actual(self):
        esquema, _, token = self.headers.get("Authorization", "").partition(" ")
        if esquema.lower() != "bearer" or not token:
            return None

        ahora = time.monotonic()
        with API_AUTH_LOCK:
            for token_vencido, sesion_vencida in list(API_SESSIONS.items()):
                if sesion_vencida["expira"] <= ahora:
                    API_SESSIONS.pop(token_vencido, None)
            sesion = API_SESSIONS.get(token)
            if not sesion or sesion["expira"] <= ahora:
                API_SESSIONS.pop(token, None)
                return None
            return sesion

    def _roles_permitidos(self, metodo, ruta):
        rutas_comunes = {
            "POST": {"/api/auth/logout", "/api/auth/cambiar_password_primer_ingreso"}
        }
        if ruta in rutas_comunes.get(metodo, set()):
            return API_ADMIN_ROLES | frozenset(("Docente", "Control"))

        rutas_docente = {
            "GET": {"/api/docentes", "/api/cohortes_activas", "/api/alumnos_cohorte"},
            "POST": {
                "/api/marcar_asistencia_curso", "/api/marcar_masivo_curso",
                "/api/cerrar_sesion_clase", "/api/reabrir_sesion_clase",
                "/api/sincronizar_offline_curso"
            }
        }
        rutas_control = {
            "GET": {"/api/registros", "/api/ip"},
            "POST": {"/api/marcar", "/api/escanear"}
        }
        if ruta in rutas_docente.get(metodo, set()):
            return API_ADMIN_ROLES | frozenset(("Docente",))
        if ruta in rutas_control.get(metodo, set()):
            return API_ADMIN_ROLES | frozenset(("Control",))
        return None

    def _autorizar_api(self, metodo, ruta):
        # Endpoints públicos de escaneo y portería no requieren sesión previa de usuario
        if not ruta.startswith("/api/") or ruta in ("/api/status", "/api/ip", "/api/registros", "/api/marcar", "/api/escanear"):
            return True

        self.usuario_api = self._sesion_api_actual()
        if not self.usuario_api:
            self._responder_json({"ok": False, "mensaje": "Inicie sesión para continuar."}, 401)
            return False

        roles = self._roles_permitidos(metodo, ruta)
        if roles and self.usuario_api["rol_sistema"] not in roles:
            self._responder_json({"ok": False, "mensaje": "No tiene permiso para esta operación."}, 403)
            return False
        return True

    def _cohorte_permitida(self, id_cohorte):
        if self.usuario_api["rol_sistema"] in API_ADMIN_ROLES:
            return True
        try:
            cohorte = db_instancia.fetch_one(
                "SELECT id_docente FROM cohorte WHERE id_cohorte = %s",
                (id_cohorte,)
            )
        except Exception:
            logging.exception("No se pudo validar el acceso a la cohorte %s", id_cohorte)
            raise
        return bool(
            cohorte
            and self.usuario_api["rol_sistema"] == "Docente"
            and cohorte.get("id_docente") == self.usuario_api.get("id_persona")
        )

    def _matricula_activa(self, id_persona, id_cohorte):
        return bool(db_instancia.fetch_one(
            """SELECT id_matricula FROM matricula
                 WHERE id_persona = %s AND id_cohorte = %s
                   AND estado <> 'Retirado'""",
            (id_persona, id_cohorte)
        ))

    def _autenticar_api(self):
        try:
            longitud = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._responder_json({"ok": False, "mensaje": "Solicitud inválida."}, 400)
            return
        if longitud <= 0 or longitud > 8192:
            self._responder_json({"ok": False, "mensaje": "Solicitud inválida."}, 400)
            return

        try:
            datos = json.loads(self.rfile.read(longitud).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._responder_json({"ok": False, "mensaje": "Solicitud inválida."}, 400)
            return
        if not isinstance(datos, dict):
            self._responder_json({"ok": False, "mensaje": "Solicitud inválida."}, 400)
            return

        username = str(datos.get("username", "") or datos.get("usuario", "")).strip()
        password = datos.get("password", "")
        if not username or not isinstance(password, str) or not password:
            self._responder_json({"ok": False, "mensaje": "Usuario o contraseña incorrectos."}, 401)
            return

        ip_cliente = self.client_address[0]
        try:
            loopback = ipaddress.ip_address(ip_cliente).is_loopback
        except ValueError:
            loopback = False

        ahora = time.monotonic()
        with API_AUTH_LOCK:
            intentos, inicio = API_LOGIN_ATTEMPTS.get(ip_cliente, (0, ahora))
            if ahora - inicio >= API_LOGIN_WINDOW:
                intentos, inicio = 0, ahora
            bloqueado = intentos >= API_LOGIN_MAX_ATTEMPTS
        if bloqueado:
            self._responder_json(
                {"ok": False, "mensaje": "Demasiados intentos. Espere 15 minutos."},
                429
            )
            return

        try:
            usuario = db_instancia.fetch_one("""
                SELECT u.id_usuario, u.username, u.password_encriptada, u.rol_sistema, u.primer_ingreso,
                       p.id_persona, CONCAT(p.nombre, ' ', p.apellido) AS nombre
                  FROM usuario u
                  JOIN personal pe ON pe.id_personal = u.id_personal
                  JOIN persona p ON p.id_persona = pe.id_persona
                 WHERE u.username = %s AND u.activo = 1
            """, (username,))
            valido = False
            if usuario:
                hash_password = usuario.get("password_encriptada") or ""
                if isinstance(hash_password, bytes):
                    hash_password = hash_password.decode("utf-8", errors="ignore")
                if hash_password.startswith("$2"):
                    try:
                        import bcrypt
                        valido = bcrypt.checkpw(password.encode("utf-8"), hash_password.encode("utf-8"))
                    except (ValueError, TypeError):
                        valido = False
                else:
                    valido = bool(db_instancia.fetch_one(
                        """SELECT id_usuario FROM usuario
                             WHERE id_usuario = %s
                               AND password_encriptada = SHA2(%s, 256)""",
                        (usuario["id_usuario"], password)
                    ))
        except Exception:
            logging.exception("Error validando el inicio de sesión móvil.")
            self._responder_json({"ok": False, "mensaje": "No se pudo validar el acceso."}, 500)
            return

        if not valido or usuario["rol_sistema"] not in (API_ADMIN_ROLES | {"Docente", "Control"}):
            with API_AUTH_LOCK:
                intentos, inicio = API_LOGIN_ATTEMPTS.get(ip_cliente, (0, ahora))
                if ahora - inicio >= API_LOGIN_WINDOW:
                    intentos, inicio = 0, ahora
                API_LOGIN_ATTEMPTS[ip_cliente] = (intentos + 1, inicio)
            self._responder_json({"ok": False, "mensaje": "Usuario o contraseña incorrectos."}, 401)
            return

        token = secrets.token_urlsafe(32)
        sesion = {
            "id_usuario": usuario["id_usuario"],
            "username": usuario["username"],
            "id_persona": usuario["id_persona"],
            "nombre": usuario["nombre"] or usuario["username"],
            "rol_sistema": usuario["rol_sistema"],
            "primer_ingreso": bool(usuario.get("primer_ingreso", 0)),
            "expira": ahora + API_SESSION_TTL
        }
        with API_AUTH_LOCK:
            API_LOGIN_ATTEMPTS.pop(ip_cliente, None)
            API_SESSIONS[token] = sesion
            for token_vencido, sesion_vencida in list(API_SESSIONS.items()):
                if sesion_vencida["expira"] <= ahora:
                    API_SESSIONS.pop(token_vencido, None)

        self._responder_json({
            "ok": True,
            "token": token,
            "expira_en": API_SESSION_TTL,
            "usuario": {
                "id_usuario": sesion["id_usuario"],
                "username": sesion["username"],
                "id_persona": sesion["id_persona"],
                "nombre": sesion["nombre"],
                "rol_sistema": sesion["rol_sistema"],
                "primer_ingreso": sesion["primer_ingreso"]
            }
        })

    def _responder_json(self, data, status_code=200):
        cuerpo = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(cuerpo)

    def do_OPTIONS(self):
        self.send_response(405)
        self.send_header("Allow", "GET, POST")
        self.end_headers()

    def do_GET(self):
        ruta = urlparse(self.path).path

        if not self._autorizar_api("GET", ruta):
            return

        if ruta in ("/", "/escaner", "/index.html", "/porteria", "/kiosco"):
            cuerpo = render_mobile_html(HTML_SCANNER).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(cuerpo)))
            self.end_headers()
            self.wfile.write(cuerpo)

        elif ruta in ("/profesor", "/profesor.html", "/p", "/profe", "/docente", "/cursos", "/aula"):
            cuerpo = render_mobile_html(HTML_PROFESOR).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(cuerpo)))
            self.end_headers()
            self.wfile.write(cuerpo)

        elif ruta == "/sw.js":
            sw_code = """
const CACHE_NAME = 'asista-sw-v2';
self.addEventListener('install', (e) => { self.skipWaiting(); });
self.addEventListener('activate', (e) => { e.waitUntil(clients.claim()); });
self.addEventListener('fetch', (e) => {
    e.respondWith(fetch(e.request).catch(() => caches.match(e.request)));
});
"""
            cuerpo = sw_code.strip().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/javascript; charset=utf-8")
            self.send_header("Content-Length", str(len(cuerpo)))
            self.end_headers()
            self.wfile.write(cuerpo)

        elif ruta == "/manifest.json":
            manifest = {
                "name": "Asista - Control de Asistencia",
                "short_name": "Asista",
                "description": "Portal móvil de asistencia y control de acceso institucional",
                "start_url": "/profesor",
                "display": "standalone",
                "background_color": "#0A1428",
                "theme_color": "#040444",
                "orientation": "portrait-primary",
                "icons": [
                    {"src": "/static/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
                    {"src": "/static/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"}
                ]
            }
            cuerpo = json.dumps(manifest, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/manifest+json; charset=utf-8")
            self.send_header("Content-Length", str(len(cuerpo)))
            self.end_headers()
            self.wfile.write(cuerpo)

        elif ruta == "/static/zxing.js":
            p_zxing = RUTA_ASSETS / "zxing.min.js"
            if p_zxing.exists():
                with open(str(p_zxing), "rb") as f:
                    cuerpo = f.read()
            else:
                cuerpo = b"// ZXing no disponible"
            self.send_response(200)
            self.send_header("Content-Type", "application/javascript; charset=utf-8")
            self.send_header("Content-Length", str(len(cuerpo)))
            self.send_header("Cache-Control", "public, max-age=86400")
            self.end_headers()
            self.wfile.write(cuerpo)

        elif ruta == "/static/icon.png":
            p_icon = RUTA_ASSETS / "icon.png"
            if p_icon.exists():
                with open(str(p_icon), "rb") as f:
                    cuerpo = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Content-Length", str(len(cuerpo)))
                self.send_header("Cache-Control", "public, max-age=86400")
                self.end_headers()
                self.wfile.write(cuerpo)
            else:
                self.send_error(404)

        elif ruta == "/static/img/escudo_institucion.png":
            p_escudo = RUTA_ASSETS / "escudo institucion.png"
            if p_escudo.exists():
                with open(p_escudo, "rb") as f:
                    cuerpo = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Content-Length", str(len(cuerpo)))
                self.send_header("Cache-Control", "public, max-age=86400")
                self.end_headers()
                self.wfile.write(cuerpo)
            else:
                self.send_error(404)

        elif ruta == "/static/img/logo.png":
            p_logo = RUTA_ASSETS / "logo_completo.png"
            if p_logo.exists():
                with open(p_logo, "rb") as f:
                    cuerpo = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Content-Length", str(len(cuerpo)))
                self.send_header("Cache-Control", "public, max-age=86400")
                self.end_headers()
                self.wfile.write(cuerpo)
            else:
                self.send_error(404)

        elif ruta in ("/static/logo.png", "/static/logo_blanco.png"):
            p_logo = RUTA_ASSETS / "logo_blanco.png"
            if not p_logo.exists():
                p_logo = RUTA_ASSETS / "logo_institucion.png"
            if p_logo.exists():
                with open(p_logo, "rb") as f:
                    cuerpo = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Content-Length", str(len(cuerpo)))
                self.send_header("Cache-Control", "public, max-age=86400")
                self.end_headers()
                self.wfile.write(cuerpo)
            else:
                self.send_error(404)

        elif ruta in ("/static/logo_institucion.png", "/static/logo_transparente.png"):
            p_logo = RUTA_ASSETS / ("logo_transparente.png" if "transparente" in ruta else "logo_institucion.png")
            if p_logo.exists():
                with open(p_logo, "rb") as f:
                    cuerpo = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Content-Length", str(len(cuerpo)))
                self.send_header("Cache-Control", "public, max-age=86400")
                self.end_headers()
                self.wfile.write(cuerpo)
            else:
                self.send_error(404)

        elif ruta == "/favicon.ico":
            p_ico = RUTA_ASSETS / "asista_icon.ico"
            if p_ico.exists():
                with open(p_ico, "rb") as f:
                    cuerpo = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "image/x-icon")
                self.send_header("Content-Length", str(len(cuerpo)))
                self.end_headers()
                self.wfile.write(cuerpo)
            else:
                self.send_error(404)

        elif ruta == "/static/icon-192.png":
            global _ICON_192
            if not _ICON_192:
                _ICON_192 = generar_icono_pwa(192)
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(_ICON_192)))
            self.end_headers()
            self.wfile.write(_ICON_192)

        elif ruta == "/static/icon-512.png":
            global _ICON_512
            if not _ICON_512:
                _ICON_512 = generar_icono_pwa(512)
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(_ICON_512)))
            self.end_headers()
            self.wfile.write(_ICON_512)

        elif ruta == "/api/docentes":
            try:
                docentes = db_instancia.listar_docentes()
                if self.usuario_api["rol_sistema"] == "Docente":
                    id_persona = self.usuario_api.get("id_persona")
                    docentes = [d for d in docentes if d["id_persona"] == id_persona]
                self._responder_json(docentes)
            except Exception as e:
                logging.exception("Error listando docentes en la API móvil.")
                self._responder_json([], status_code=500)

        elif ruta == "/api/cohortes_activas":
            try:
                params = parse_qs(urlparse(self.path).query)
                id_doc = params.get("id_docente", [None])[0]
                if self.usuario_api["rol_sistema"] == "Docente":
                    id_doc = self.usuario_api.get("id_persona")
                elif id_doc:
                    try:
                        id_d_int = int(id_doc)
                    except ValueError:
                        self._responder_json({"ok": False, "mensaje": "Docente inválido."}, 400)
                        return
                    id_doc = id_d_int
                cohortes = db_instancia.listar_cohortes(
                    id_docente=id_doc,
                    incluir_archivados=False
                )
                for c in cohortes:
                    c["hora_inicio"] = fmt_hora_simple(c.get("hora_inicio"))
                    c["hora_fin"] = fmt_hora_simple(c.get("hora_fin"))
                self._responder_json(cohortes)
            except Exception as e:
                logging.exception("Error listando cohortes en la API móvil.")
                self._responder_json([], status_code=500)

        elif ruta == "/api/alumnos_cohorte":
            try:
                params = parse_qs(urlparse(self.path).query)
                id_c = int(params.get("id_cohorte", [0])[0])
                if not self._cohorte_permitida(id_c):
                    self._responder_json({"ok": False, "mensaje": "No tiene acceso a esta cohorte."}, 403)
                    return
                hoy = date.today()
                alumnos = db_instancia.obtener_asistencia_cohorte_fecha(id_c, hoy)
                matriculas = db_instancia.listar_estudiantes_cohorte(id_c)
                pct_map = {m["id_persona"]: float(m.get("porcentaje_asistencia", 0)) for m in matriculas}
                for a in alumnos:
                    a["pct_asistencia"] = pct_map.get(a["id_persona"], 100.0)
                    if a.get("hora"):
                        a["hora"] = fmt_hora_simple(a.get("hora"))
                
                sesion_row = db_instancia.obtener_o_crear_sesion_clase(id_c, hoy)
                sesion_info = {
                    "estado": sesion_row.get("estado", "Abierta") if sesion_row else "Abierta",
                    "hora_cierre": fmt_hora_simple(sesion_row.get("hora_cierre")) if sesion_row and sesion_row.get("hora_cierre") else None,
                    "firma_docente": sesion_row.get("firma_docente") if sesion_row else None,
                    "total_presentes": int(sesion_row.get("total_presentes", 0)) if sesion_row else 0,
                    "total_ausentes": int(sesion_row.get("total_ausentes", 0)) if sesion_row else 0
                }
                self._responder_json({
                    "alumnos": alumnos,
                    "sesion": sesion_info
                })
            except Exception as e:
                logging.exception("Error consultando asistencia de cohorte en la API móvil.")
                self._responder_json({"alumnos": [], "sesion": {"estado": "Abierta"}}, status_code=500)

        elif ruta == "/api/status":
            host = self.headers.get("Host", "").split(":", 1)[0].strip("[]")
            puerto_https = (
                PUERTO_HTTPS_ACTIVO
                if _HILO_HTTPS and _HILO_HTTPS.is_alive() else None
            )
            if puerto_https and host not in ("localhost", "127.0.0.1") and host not in IPS_CERTIFICADO_SSL:
                puerto_https = None
            self._responder_json({
                "service": "asista",
                "status": "online",
                "hora": datetime.now().strftime("%H:%M:%S"),
                "fecha": date.today().isoformat(),
                "http_port": PUERTO_HTTP_ACTIVO,
                "https_port": puerto_https
            })

        elif ruta == "/api/registros":
            try:
                registros = db_instancia.registros_hoy(limite=20)
                self._responder_json(registros)
            except Exception as e:
                self._responder_json([], status_code=500)

        elif ruta == "/api/ip":
            self._responder_json({"ip": obtener_ip_local()})

        else:
            if ruta.startswith("/api/"):
                self.send_response(404)
                self.end_headers()
            else:
                # Redirección amigable a la página principal para evitar pantallas negras en móviles
                self.send_response(302)
                self.send_header("Location", "/")
                self.end_headers()

    def do_POST(self):
        ruta = urlparse(self.path).path

        if ruta == "/api/auth/login":
            self._autenticar_api()
            return
        if not self._autorizar_api("POST", ruta):
            return

        if ruta == "/api/auth/logout":
            auth_header = self.headers.get("Authorization", "")
            token = auth_header.replace("Bearer ", "").strip()
            with API_AUTH_LOCK:
                API_SESSIONS.pop(token, None)
            self._responder_json({"ok": True, "mensaje": "Sesión cerrada correctamente."})
            return

        elif ruta == "/api/auth/cambiar_password_primer_ingreso":
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            try:
                datos = json.loads(post_data.decode('utf-8'))
                nueva_pass = str(datos.get("nueva_password", "")).strip()
                from config import validar_password_rigurosa
                valida, msg_pwd = validar_password_rigurosa(nueva_pass)
                if not valida:
                    self._responder_json({"ok": False, "mensaje": msg_pwd}, 400)
                    return

                import bcrypt
                nuevo_hash = bcrypt.hashpw(nueva_pass.encode("utf-8"), bcrypt.gensalt(12)).decode("utf-8")
                id_usu = self.usuario_api["id_usuario"]
                db_instancia.cambiar_password_primer_ingreso(id_usu, nuevo_hash)
                self.usuario_api["primer_ingreso"] = False
                self._responder_json({"ok": True, "mensaje": "Contraseña actualizada exitosamente."})
            except Exception as err:
                logging.exception("Error cambiando password de primer ingreso móvil: %s", err)
                self._responder_json({"ok": False, "mensaje": "Error actualizando la contraseña."}, 500)
            return

        if ruta == "/api/marcar_asistencia_curso":
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            try:
                datos = json.loads(post_data.decode('utf-8'))
                id_cohorte = int(datos.get("id_cohorte", 0))
                if not self._cohorte_permitida(id_cohorte):
                    self._responder_json({"ok": False, "mensaje": "No tiene acceso a esta cohorte."}, 403)
                    return
                cedula = str(datos.get("cedula", "")).strip()
                id_persona = datos.get("id_persona")
                estado = str(datos.get("estado", "Presente")).strip()
                obs = str(datos.get("observaciones", "")).strip()

                if not id_persona and cedula:
                    p = db_instancia.persona_por_cedula(cedula)
                    if p:
                        id_persona = p["id_persona"]
                    else:
                        self._responder_json({"ok": False, "mensaje": f"Cédula {cedula} no encontrada en el sistema"}, status_code=404)
                        return

                if not id_persona or not id_cohorte:
                    self._responder_json({"ok": False, "mensaje": "Datos incompletos para marcaje de curso"}, status_code=400)
                    return
                if (
                    self.usuario_api["rol_sistema"] == "Docente"
                    and not self._matricula_activa(id_persona, id_cohorte)
                ):
                    self._responder_json(
                        {"ok": False, "mensaje": "El estudiante no está inscrito en esta cohorte."},
                        403
                    )
                    return

                hoy = date.today()
                # Verificar si la sesión de asistencia de hoy está cerrada
                sesion_actual = db_instancia.fetch_one(
                    "SELECT estado FROM sesion_clase WHERE id_cohorte = %s AND fecha = %s",
                    (id_cohorte, hoy)
                )
                if sesion_actual and sesion_actual.get("estado") == "Cerrada" and self.usuario_api["rol_sistema"] == "Docente":
                    self._responder_json(
                        {"ok": False, "mensaje": "La sesión de hoy está CERRADA. Solo Directora o Administración pueden autorizar modificaciones."},
                        status_code=403
                    )
                    return

                # Validación anti-duplicados previa en servidor
                asist_ant = db_instancia.fetch_one(
                    "SELECT id_asistencia_curso, estado, hora FROM asistencia_curso "
                    "WHERE id_persona = %s AND id_cohorte = %s AND fecha = %s",
                    (id_persona, id_cohorte, hoy)
                )
                if asist_ant and asist_ant.get("estado") == estado:
                    persona = db_instancia.persona_por_id(id_persona)
                    nom = f"{persona['nombre']} {persona['apellido']}" if persona else "Estudiante"
                    mat = db_instancia.fetch_one("SELECT porcentaje_asistencia FROM matricula WHERE id_persona=%s AND id_cohorte=%s", (id_persona, id_cohorte))
                    pct = float(mat["porcentaje_asistencia"]) if mat else 100.0
                    hora_existente = asist_ant.get("hora") or ""
                    self._responder_json({
                        "ok": True,
                        "duplicado": True,
                        "estudiante": nom,
                        "estado": estado,
                        "hora": hora_existente,
                        "pct_asistencia": pct,
                        "mensaje": f"ℹ {nom} ya tenía registrada su asistencia como '{estado}' hoy."
                    })
                    return

                ahora = datetime.now().time()
                db_instancia.registrar_asistencia_estudiante_curso(
                    id_persona, id_cohorte, hoy, ahora, estado, obs,
                    self.usuario_api["id_usuario"]
                )

                persona = db_instancia.persona_por_id(id_persona)
                nom = f"{persona['nombre']} {persona['apellido']}" if persona else "Estudiante"
                mat = db_instancia.fetch_one("SELECT porcentaje_asistencia FROM matricula WHERE id_persona=%s AND id_cohorte=%s", (id_persona, id_cohorte))
                pct = float(mat["porcentaje_asistencia"]) if mat else 100.0

                self._responder_json({
                    "ok": True,
                    "estudiante": nom,
                    "estado": estado,
                    "hora": ahora.strftime("%H:%M:%S"),
                    "pct_asistencia": pct
                })
            except Exception as e:
                logging.error(f"Error en marcaje de curso: {e}")
                self._responder_json({"ok": False, "mensaje": f"Error: {e}"}, status_code=500)

        elif ruta == "/api/marcar_masivo_curso":
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            try:
                datos = json.loads(post_data.decode('utf-8'))
                id_cohorte = int(datos.get("id_cohorte", 0))
                if not self._cohorte_permitida(id_cohorte):
                    self._responder_json({"ok": False, "mensaje": "No tiene acceso a esta cohorte."}, 403)
                    return
                estado = str(datos.get("estado", "Presente")).strip()

                alumnos = db_instancia.listar_estudiantes_cohorte(id_cohorte)
                hoy = date.today()
                ahora = datetime.now().time()
                for a in alumnos:
                    db_instancia.registrar_asistencia_estudiante_curso(
                        a["id_persona"], id_cohorte, hoy, ahora, estado,
                        "Marcaje Masivo", self.usuario_api["id_usuario"]
                    )

                self._responder_json({"ok": True, "afectados": len(alumnos)})
            except Exception as e:
                self._responder_json({"ok": False, "mensaje": str(e)}, status_code=500)

        elif ruta == "/api/cerrar_sesion_clase":
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            try:
                datos = json.loads(post_data.decode('utf-8'))
                id_cohorte = int(datos.get("id_cohorte", 0))
                if not self._cohorte_permitida(id_cohorte):
                    self._responder_json({"ok": False, "mensaje": "No tiene acceso a esta cohorte."}, 403)
                    return
                id_docente = datos.get("id_docente")
                if self.usuario_api["rol_sistema"] == "Docente":
                    id_docente = self.usuario_api["id_persona"]
                    firma = self.usuario_api["nombre"]
                else:
                    firma = str(datos.get("firma_docente", "")).strip()

                res = db_instancia.cerrar_sesion_clase(id_cohorte, date.today(), id_docente, firma)
                self._responder_json({"ok": True, "resumen": res})
            except Exception as e:
                self._responder_json({"ok": False, "mensaje": str(e)}, status_code=500)

        elif ruta == "/api/reabrir_sesion_clase":
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            try:
                datos = json.loads(post_data.decode('utf-8'))
                id_cohorte = int(datos.get("id_cohorte", 0))
                if not self._cohorte_permitida(id_cohorte):
                    self._responder_json({"ok": False, "mensaje": "No tiene acceso a esta cohorte."}, 403)
                    return
                # Validación de rol: solo Directora o Administración pueden reabrir sesiones cerradas
                if self.usuario_api["rol_sistema"] == "Docente":
                    self._responder_json(
                        {"ok": False, "mensaje": "Permiso denegado: solo personal Directivo o de Administración puede reabrir una sesión cerrada."},
                        status_code=403
                    )
                    return
                res = db_instancia.reabrir_sesion_clase(id_cohorte, date.today())
                self._responder_json({"ok": True, "resumen": res})
            except Exception as e:
                self._responder_json({"ok": False, "mensaje": str(e)}, status_code=500)

        elif ruta == "/api/sincronizar_offline_curso":
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            try:
                datos = json.loads(post_data.decode('utf-8'))
                registros = datos.get("registros", [])
                if not isinstance(registros, list):
                    self._responder_json({"ok": False, "mensaje": "Lista de registros inválida."}, 400)
                    return
                for registro in registros:
                    if not isinstance(registro, dict):
                        self._responder_json({"ok": False, "mensaje": "Registro inválido."}, 400)
                        return
                    try:
                        id_c = int(registro.get("id_cohorte", 0))
                    except (TypeError, ValueError):
                        self._responder_json({"ok": False, "mensaje": "Cohorte inválida."}, 400)
                        return
                    if not self._cohorte_permitida(id_c):
                        self._responder_json({"ok": False, "mensaje": "No tiene acceso a una de las cohortes."}, 403)
                        return
                    if self.usuario_api["rol_sistema"] == "Docente":
                        id_p = registro.get("id_persona")
                        cedula = registro.get("cedula")
                        if not id_p and cedula:
                            persona = db_instancia.persona_por_cedula(str(cedula).strip())
                            id_p = persona["id_persona"] if persona else None
                        if not id_p or not self._matricula_activa(id_p, id_c):
                            self._responder_json(
                                {"ok": False, "mensaje": "Un estudiante no está inscrito en su cohorte."},
                                403
                            )
                            return
                        registro["_id_persona_autorizado"] = id_p
                procesados = 0
                hoy = date.today()
                ahora = datetime.now().time()

                # Desduplicar registros en el lote recibido: conservar el último registro por alumno, cohorte y fecha
                registros_unicos = {}
                for reg in registros:
                    if isinstance(reg, dict):
                        k = (
                            reg.get("id_persona") or reg.get("_id_persona_autorizado") or reg.get("cedula"),
                            int(reg.get("id_cohorte", 0)),
                            reg.get("fecha") or str(hoy)
                        )
                        registros_unicos[k] = reg

                for r in registros_unicos.values():
                    try:
                        id_p = r.get("id_persona") or r.get("_id_persona_autorizado")
                        id_c = int(r.get("id_cohorte", 0))
                        est = r.get("estado", "Presente")
                        ced = r.get("cedula")
                        f_reg = r.get("fecha") or hoy
                        if isinstance(f_reg, str) and len(f_reg) >= 10:
                            try:
                                f_reg = datetime.strptime(f_reg[:10], "%Y-%m-%d").date()
                            except Exception:
                                f_reg = hoy

                        if not id_p and ced:
                            p = db_instancia.persona_por_cedula(ced)
                            if p:
                                id_p = p["id_persona"]
                        if id_p and id_c:
                            db_instancia.registrar_asistencia_estudiante_curso(
                                id_p, id_c, f_reg, ahora, est, "Sync Offline Celular",
                                self.usuario_api["id_usuario"]
                            )
                            procesados += 1
                    except Exception as item_err:
                        logging.warning(f"Error procesando registro offline individual: {item_err}")
                self._responder_json({"ok": True, "procesados": procesados})
            except Exception as e:
                self._responder_json({"ok": False, "mensaje": str(e)}, status_code=500)

        elif ruta in ("/api/escanear", "/api/marcar"):
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)

            cedula = ""
            try:
                datos = json.loads(post_data.decode('utf-8'))
                cedula = str(datos.get("cedula") or datos.get("barcode") or datos.get("text") or "").strip()
            except Exception:
                try:
                    params = parse_qs(post_data.decode('utf-8'))
                    cedula = params.get("cedula", [""])[0].strip()
                except Exception:
                    pass

            if not cedula:
                self._responder_json({"ok": False, "mensaje": "Cédula no proporcionada"}, status_code=400)
                return

            try:
                resultado = db_instancia.procesar_marcaje(cedula)
                logging.info(f"Marcaje procesado para C.I. {cedula}: {resultado.get('tipo')} - {resultado.get('estado')}")
                self._responder_json(resultado)
            except Exception as e:
                logging.error(f"Error procesando marcaje de {cedula}: {e}")
                self._responder_json({"ok": False, "mensaje": f"Error interno: {e}"}, status_code=500)

        else:
            self.send_response(404)
            self.end_headers()


def loop_cierre_diario_automatico():
    """Monitorea la hora y ejecuta automáticamente el cierre a las 11:59 PM."""
    ultimo_cierre = None
    while True:
        try:
            ahora = datetime.now()
            hoy = ahora.date()
            if ahora.hour == 23 and ahora.minute == 59 and ultimo_cierre != hoy:
                logging.info(f"Iniciando cierre diario automático de las 11:59 PM para fecha: {hoy}")
                try:
                    res = db_instancia.ejecutar_cierre_diario(hoy)
                    logging.info(f"Cierre diario automático completado exitosamente: {res}")
                    ultimo_cierre = hoy
                except Exception as ex:
                    logging.error(f"Error en cierre diario automático: {ex}")
            time.sleep(30)
        except Exception as e:
            time.sleep(60)


def generar_certificado_ssl():
    """Genera un certificado SSL autofirmado para HTTPS local."""
    import datetime
    global IPS_CERTIFICADO_SSL

    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.x509 import DNSName, IPAddress
    except ImportError:
        logging.warning("cryptography no disponible - servidor correra en HTTP")
        return None, None

    cert_path = BASE_DIR / "asista_cert.pem"
    key_path  = BASE_DIR / "asista_key.pem"

    if cert_path.exists() and key_path.exists():
        try:
            cert_existente = x509.load_pem_x509_certificate(cert_path.read_bytes())
            ips_existentes = {
                str(ip) for ip in cert_existente.extensions
                .get_extension_for_class(x509.SubjectAlternativeName)
                .value.get_values_for_type(IPAddress)
            }
            vencimiento = getattr(cert_existente, "not_valid_after_utc", None)
            if vencimiento is None:
                vencimiento = cert_existente.not_valid_after.replace(tzinfo=datetime.timezone.utc)
            ips_requeridas = {
                ip for ip in listar_ips_locales()
                if ip and not ip.startswith(("127.", "169.254."))
            }
            if ips_requeridas.issubset(ips_existentes) and vencimiento > datetime.datetime.now(datetime.timezone.utc):
                ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER).load_cert_chain(
                    certfile=str(cert_path), keyfile=str(key_path)
                )
                IPS_CERTIFICADO_SSL = ips_existentes
                return str(cert_path), str(key_path)
            logging.info("Renovando certificado SSL: vencido o sin la IP IPv4 activa.")
        except (OSError, ValueError, ssl.SSLError, x509.ExtensionNotFound):
            logging.warning("Certificado SSL previo inválido; se regenerará.")

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "CO"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Asista"),
        x509.NameAttribute(NameOID.COMMON_NAME, "asista.local"),
    ])
    san_entries = [
        DNSName("localhost"),
        DNSName("asista.local"),
        IPAddress(ipaddress.IPv4Address("127.0.0.1")),
    ]
    IPS_CERTIFICADO_SSL = {"127.0.0.1"}
    for _cand_ip in listar_ips_locales():
        try:
            direccion = ipaddress.IPv4Address(_cand_ip)
            san_entries.append(IPAddress(direccion))
            IPS_CERTIFICADO_SSL.add(str(direccion))
        except ValueError:
            pass
    san = x509.SubjectAlternativeName(san_entries)
    ahora_utc = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(ahora_utc)
        .not_valid_after(ahora_utc + datetime.timedelta(days=3650))
        .add_extension(san, critical=False)
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption()
    ))
    logging.info("Certificado SSL generado correctamente.")
    return str(cert_path), str(key_path)


class AsistaHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    allow_reuse_address = False
    daemon_threads = True


def _crear_servidor_http(puerto_inicial):
    fin = min(puerto_inicial + PUERTOS_HTTP_ALTERNATIVOS, 65536)
    for puerto in range(puerto_inicial, fin):
        try:
            return AsistaHTTPServer((HOST_SERVICIO, puerto), AsistaHTTPRequestHandler)
        except OSError as exc:
            if exc.errno != errno.EADDRINUSE and getattr(exc, "winerror", None) != 10048:
                raise
            logging.warning("Puerto HTTP %s ocupado; se probará el siguiente sin cerrar otros procesos.", puerto)
    raise OSError(errno.EADDRINUSE, f"No hay puertos libres entre {puerto_inicial} y {fin - 1}.")


def iniciar_servidor(puerto=PUERTO_SERVICIO):
    """Inicia el listener HTTP en el primer puerto disponible y HTTPS en 8443."""
    global PUERTO_HTTP_ACTIVO, PUERTO_HTTPS_ACTIVO, _HILO_HTTPS, _ERROR_INICIO_SERVICIO

    if not 1 <= int(puerto) <= 65535:
        raise ValueError(f"Puerto HTTP fuera de rango: {puerto}")

    PUERTO_HTTPS_ACTIVO = None
    _HILO_HTTPS = None
    servidor = _crear_servidor_http(int(puerto))
    PUERTO_HTTP_ACTIVO = servidor.server_port
    ip_actual = obtener_ip_local()

    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

    try:
        cert_path, key_path = generar_certificado_ssl()
        if cert_path and key_path and os.path.exists(cert_path) and os.path.exists(key_path):
            srv_https = AsistaHTTPServer((HOST_SERVICIO, PUERTO_HTTPS), AsistaHTTPRequestHandler)
            try:
                contexto = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                contexto.load_cert_chain(certfile=cert_path, keyfile=key_path)
                srv_https.socket = contexto.wrap_socket(srv_https.socket, server_side=True)
                hilo_https = threading.Thread(target=srv_https.serve_forever, daemon=True)
                hilo_https.start()
                _HILO_HTTPS = hilo_https
                PUERTO_HTTPS_ACTIVO = PUERTO_HTTPS
            except Exception:
                srv_https.server_close()
                raise
    except Exception:
        PUERTO_HTTPS_ACTIVO = None
        logging.exception("No se pudo iniciar HTTPS en el puerto %s; HTTP permanece disponible.", PUERTO_HTTPS)

    t_cierre = threading.Thread(target=loop_cierre_diario_automatico, daemon=True)
    t_cierre.start()
    _EVENTO_SERVICIO_LISTO.set()

    mensajes = [
        "=" * 60,
        "[ASISTA] Servicio de Asistencia Autónomo en línea",
        f"Acceso HTTP:  http://{ip_actual}:{PUERTO_HTTP_ACTIVO}/",
    ]
    if PUERTO_HTTPS_ACTIVO:
        mensajes.append(f"Acceso HTTPS: https://{ip_actual}:{PUERTO_HTTPS_ACTIVO}/ (cámara en vivo)")
    else:
        mensajes.append("HTTPS no disponible; la cámara móvil requiere habilitar el certificado y el puerto 8443.")
    mensajes.extend((
        "Escáner en vivo: HTTPS requiere confiar el certificado local en el teléfono.",
        "=" * 60,
    ))
    if sys.stdout is not None:
        for mensaje in mensajes:
            print(mensaje)
    logging.info(
        "Servicio Asista iniciado. %s",
        " | ".join(mensajes[1:-1])
    )

    try:
        servidor.serve_forever()
    finally:
        servidor.server_close()
        PUERTO_HTTP_ACTIVO = None


def _ejecutar_servidor():
    global _ERROR_INICIO_SERVICIO
    try:
        iniciar_servidor(PUERTO_SERVICIO)
    except Exception as exc:
        _ERROR_INICIO_SERVICIO = exc
        _EVENTO_SERVICIO_LISTO.set()
        logging.exception("No se pudo iniciar el servicio ASISTA.")


def asegurar_servidor(timeout=5.0):
    """Inicia una sola instancia local y espera una respuesta HTTP verificable."""
    global _HILO_SERVICIO, _ERROR_INICIO_SERVICIO

    if obtener_estado_servidor():
        return True

    with _LOCK_INICIO_SERVICIO:
        if _HILO_SERVICIO is None or not _HILO_SERVICIO.is_alive():
            _EVENTO_SERVICIO_LISTO.clear()
            _ERROR_INICIO_SERVICIO = None
            _HILO_SERVICIO = threading.Thread(target=_ejecutar_servidor, daemon=True)
            _HILO_SERVICIO.start()
        hilo = _HILO_SERVICIO

    inicio = time.monotonic()
    if not _EVENTO_SERVICIO_LISTO.wait(timeout):
        logging.error("Tiempo agotado esperando que ASISTA abra un puerto HTTP.")
        return False
    if _ERROR_INICIO_SERVICIO:
        return False
    while True:
        if obtener_estado_servidor():
            return True
        if not hilo.is_alive() or time.monotonic() - inicio >= timeout:
            logging.error("El listener HTTP no respondió después de enlazar el puerto.")
            return False
        time.sleep(0.1)


if __name__ == "__main__":
    puerto = PUERTO_SERVICIO
    if len(sys.argv) > 1:
        try:
            puerto = int(sys.argv[1])
        except ValueError:
            pass
    iniciar_servidor(puerto)
