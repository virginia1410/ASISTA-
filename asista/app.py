"""REGISTRA / Asista – Control de Asistencias · Unidad Educativa Prof. Aristóbulo Istúriz.
Ventana principal y orquestador de módulos con soporte de Control de Acceso Basado en Roles (RBAC).
Ejecutar: python app.py
"""
import json
import os
import ssl
import sys
import traceback
from datetime import datetime, date
from tkinter import messagebox
import customtkinter as ctk

from db import Database
from tema import (
    ACENTO, BG, F_TEXTO, F_TITULO, LEMA, MORADO, NOMBRE_SISTEMA,
    logo_check, logo_institucion, logo_asista, RUTA_ICONO
)
from views import (
    Inicio, Marcaje, Personas, Justificaciones, Reportes, Administracion, estilo_tablas
)
from login import VentanaLogin
import config


# ============================== GESTIÓN DE SESIÓN PERSISTENTE =================
RUTA_SESION = config.BASE_DIR / ".sesion_activa.json"


def guardar_sesion_activa(usuario_info):
    """Guarda la sesión activa en disco para persistencia al cerrar con la X."""
    try:
        if not usuario_info:
            return
        with open(RUTA_SESION, "w", encoding="utf-8") as f:
            json.dump(usuario_info, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Aviso guardando sesión: {e}")


def borrar_sesion_activa():
    """Elimina el archivo de sesión cuando el usuario hace clic en 'Cerrar Sesión'."""
    try:
        if RUTA_SESION.exists():
            RUTA_SESION.unlink()
    except Exception as e:
        print(f"Aviso borrando sesión: {e}")


def cargar_sesion_activa(db):
    """Carga y valida la sesión persistente para evitar login innecesario al reabrir la app."""
    try:
        if not RUTA_SESION.exists():
            return None
        with open(RUTA_SESION, "r", encoding="utf-8") as f:
            datos = json.load(f)
        id_u = datos.get("id_usuario")
        if not id_u:
            return None

        # Verificar que el usuario continúe activo en la base de datos
        sql = """
            SELECT u.id_usuario, u.username, u.activo, u.rol_sistema, u.es_duena,
                   pe.cargo, CONCAT(p.nombre, ' ', p.apellido) AS nombre_persona
              FROM usuario u
              JOIN personal pe ON pe.id_personal = u.id_personal
              JOIN persona p   ON p.id_persona = pe.id_persona
             WHERE u.id_usuario = %s AND u.activo = 1
        """
        row = db.fetch_one(sql, (id_u,))
        if not row:
            borrar_sesion_activa()
            return None

        return {
            "id_usuario": row["id_usuario"],
            "username": row["username"],
            "rol_sistema": row["rol_sistema"],
            "cargo": row.get("cargo") or "",
            "es_duena": bool(row.get("es_duena", 0)),
            "nombre_persona": row.get("nombre_persona") or row["username"]
        }
    except Exception as e:
        print(f"Aviso validando sesión persistente: {e}")
        return None


# ============================== VENTANA PRINCIPAL =============================
class App(ctk.CTk):
    def __init__(self):
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")
        super().__init__(fg_color=BG)
        self.title(f"{NOMBRE_SISTEMA} · Control de asistencias")
        import ctypes
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("asista.instituto.tecnico")
        except Exception:
            pass
        if os.path.exists(RUTA_ICONO):
            try:
                self.iconbitmap(RUTA_ICONO)
            except Exception:
                pass
        p_png = os.path.join(os.path.dirname(RUTA_ICONO), "asista_icon.png")
        if os.path.exists(p_png):
            try:
                from PIL import Image, ImageTk
                self.iconphoto(True, ImageTk.PhotoImage(Image.open(p_png)))
            except Exception:
                pass
        self.geometry("1360x820")
        self.minsize(1100, 660)
        self.state("zoomed")
        self.db = Database()
        self._imagenes = []
        self._ultimo_cierre_auto = None
        self._reloj_job = None

        try:
            self.db.connection()
            self.db.migrar_tablas_instituto()
        except Exception as e:
            messagebox.showerror(
                "No se pudo inicializar Asista",
                f"Verifique la conexión MySQL, los permisos de la base de datos "
                f"y las variables DB_* del archivo .env.\n\n{e}",
                parent=self,
            )
            self.destroy()
            return

        # Control de cierre con la X: no cierra sesión, solo destruye ventana (servicio sigue activo)
        self.protocol("WM_DELETE_WINDOW", self.on_cerrar_con_x)

        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Control de Acceso Basado en Roles (RBAC Estricto)
        self.usuario_actual = getattr(config, "USUARIO_ACTUAL", None) or {}
        self.rol_actual = getattr(config, "USUARIO_ROL", None) or self.usuario_actual.get("rol_sistema", "Administrador")
        self.es_admin = True
        self.es_duena = bool(self.usuario_actual.get("es_duena", False) or self.rol_actual in ("Directivo", "Directiva"))

        self.sidebar_visible = True
        self._barra_lateral()

        # Área Principal (Top Toolbar + Contenedor de Vistas)
        self.area_principal = ctk.CTkFrame(self, fg_color="transparent")
        self.area_principal.grid(row=0, column=1, sticky="nsew")
        self.area_principal.grid_rowconfigure(1, weight=1)
        self.area_principal.grid_columnconfigure(0, weight=1)

        self._barra_herramientas_superior()

        self.contenedor = ctk.CTkFrame(self.area_principal, fg_color="transparent")
        self.contenedor.grid(row=1, column=0, sticky="nsew")
        self.contenedor.grid_rowconfigure(0, weight=1)
        self.contenedor.grid_columnconfigure(0, weight=1)

        # Cargar vistas permitidas según el rol del usuario
        vistas_a_cargar = [
            ("inicio", Inicio),
            ("marcaje", Marcaje),
            ("personas", Personas),
            ("justif", Justificaciones),
            ("reportes", Reportes),
        ]
        if self.es_admin:
            vistas_a_cargar.append(("admin", Administracion))

        self.vistas = {}
        for clave, clase in vistas_a_cargar:
            self.vistas[clave] = clase(self.contenedor, self)

        estilo_tablas()
        self.after(200, self._arranque)

        # Monitoreo automático en segundo plano para cierre diario a las 11:59 PM
        self.after(20000, self._verificar_cierre_diario_automatico)
        # Actualización de reloj en la barra superior
        self._actualizar_reloj_superior()

    def _imagen(self, img):
        im = ctk.CTkImage(light_image=img, size=img.size)
        self._imagenes.append(im)
        return im

    def _barra_lateral(self):
        self.lado = ctk.CTkFrame(self, width=260, corner_radius=0, fg_color=MORADO)
        self.lado.grid(row=0, column=0, sticky="nsw")
        self.lado.pack_propagate(False)
        self.lado.grid_propagate(False)

        # Encabezado institucional con marca y botón rápido de colapsar
        marca = ctk.CTkFrame(self.lado, fg_color="transparent")
        marca.pack(fill="x", padx=16, pady=(18, 0))
        img_brand = logo_asista(alto=38, ancho_max=180, modo="blanco")
        if img_brand:
            ctk.CTkLabel(marca, text="", image=self._imagen(img_brand)).pack(side="left")
        else:
            ctk.CTkLabel(marca, text="", image=self._imagen(logo_check("#FFFFFF", 32))).pack(side="left")
            ctk.CTkLabel(marca, text=NOMBRE_SISTEMA, font=(F_TEXTO, 24, "bold"), text_color="white").pack(
                side="left", padx=(8, 0))

        btn_colapsar_marca = ctk.CTkButton(
            marca, text="◀", width=30, height=30, corner_radius=8,
            fg_color="#162C55", hover_color="#1E3A6D", font=(F_TEXTO, 12, "bold"),
            command=self.toggle_sidebar
        )
        btn_colapsar_marca.pack(side="right")

        ctk.CTkLabel(self.lado, text=LEMA, font=(F_TEXTO, 9, "bold"), text_color="#94A3B8", anchor="w").pack(
            fill="x", padx=24, pady=(2, 0))
        ctk.CTkFrame(self.lado, width=40, height=3, fg_color=ACENTO[0], corner_radius=2).pack(
            anchor="w", padx=24, pady=(4, 8)
        )

        # REPOSICIONAMIENTO SOLICITADO: Logo del colegio y nombre institucional ARRIBA debajo de Asista
        card_inst = ctk.CTkFrame(self.lado, fg_color="white", corner_radius=12)
        card_inst.pack(fill="x", padx=16, pady=(0, 10))
        f_top_inst = ctk.CTkFrame(card_inst, fg_color="transparent")
        f_top_inst.pack(fill="x", padx=10, pady=8)

        img_esc = logo_institucion(alto=48, ancho_max=44)
        if img_esc:
            ctk.CTkLabel(f_top_inst, text="", image=self._imagen(img_esc)).pack(side="left", padx=(0, 8))
        else:
            ctk.CTkLabel(f_top_inst, text="U.E.", width=34, height=34, corner_radius=17, fg_color=MORADO,
                         text_color="white", font=(F_TITULO, 11, "bold")).pack(side="left", padx=(0, 8))

        f_txt_inst = ctk.CTkFrame(f_top_inst, fg_color="transparent")
        f_txt_inst.pack(side="left", fill="both", expand=True)
        ctk.CTkLabel(
            f_txt_inst,
            text="U.E. Prof. Aristóbulo Istúriz",
            font=(F_TEXTO, 9.5, "bold"),
            text_color=MORADO,
            anchor="w",
            wraplength=145,
            justify="left"
        ).pack(fill="x")
        ctk.CTkLabel(
            f_txt_inst,
            text="Cabimas, Zulia",
            font=(F_TEXTO, 8.5),
            text_color="#6B7280",
            anchor="w"
        ).pack(fill="x")

        # Tarjeta visual de sesión activa (RBAC)
        card_user = ctk.CTkFrame(self.lado, fg_color="#162C55", corner_radius=12)
        card_user.pack(fill="x", padx=16, pady=(0, 12))

        nombre_u = getattr(config, "USUARIO_NOMBRE", "") or self.usuario_actual.get("username", "Usuario")
        ctk.CTkLabel(
            card_user,
            text=f"👤  {nombre_u}",
            font=(F_TEXTO, 11, "bold"),
            text_color="white",
            anchor="w"
        ).pack(fill="x", padx=12, pady=(8, 2))

        badge_color = ACENTO[0]
        f_badge = ctk.CTkFrame(card_user, fg_color=badge_color, corner_radius=6)
        f_badge.pack(anchor="w", padx=12, pady=(0, 8))
        texto_badge = " Rol: Directiva " if self.es_duena else " Rol: Administración "
        ctk.CTkLabel(
            f_badge,
            text=texto_badge,
            font=(F_TEXTO, 9, "bold"),
            text_color="white"
        ).pack(padx=4, pady=1)

        # Menú de Navegación con RBAC estricto
        self.nav = {}
        items_menu = [
            ("inicio", "⌂   Inicio"),
            ("marcaje", "✓   Marcaje"),
            ("personas", "◉   Personas"),
            ("justif", "✎   Justificaciones y cierres"),
            ("reportes", "▤   Reportes"),
        ]
        if self.es_admin:
            items_menu.append(("admin", "⚙   Administración"))

        for clave, texto in items_menu:
            self.nav[clave] = ctk.CTkButton(
                self.lado, text=texto, anchor="w", height=42, corner_radius=12,
                fg_color="transparent", hover_color="#162C55", text_color="#E2E8F0",
                font=(F_TEXTO, 13, "bold"), command=lambda k=clave: self.mostrar(k)
            )
            self.nav[clave].pack(fill="x", padx=16, pady=2)

        # Controles inferiores (Cerrar sesión y Modo oscuro únicamente, cuadro del colegio movido arriba)
        btn_cerrar_sesion = ctk.CTkButton(
            self.lado, text="🚪  Cerrar Sesión", anchor="center", height=34, corner_radius=10,
            fg_color="#162C55", hover_color="#1E3A6D", text_color="#FFFFFF",
            font=(F_TEXTO, 11, "bold"), command=self.cerrar_sesion
        )
        btn_cerrar_sesion.pack(side="bottom", fill="x", padx=16, pady=(0, 14))

        self.oscuro = ctk.CTkSwitch(
            self.lado, text="Modo oscuro", text_color="#E2E8F0", progress_color=ACENTO[0],
            font=(F_TEXTO, 11), command=self._tema
        )
        self.oscuro.pack(side="bottom", pady=(0, 10))

    def _barra_herramientas_superior(self):
        self.toolbar = ctk.CTkFrame(self.area_principal, height=48, fg_color="#FFFFFF", corner_radius=0, border_width=1, border_color="#E2E8F0")
        self.toolbar.grid(row=0, column=0, sticky="ew")
        self.toolbar.pack_propagate(False)
        self.toolbar.grid_propagate(False)

        # Botón para colapsar/expandir barra lateral
        self.btn_toggle_menu = ctk.CTkButton(
            self.toolbar,
            text="◀  Ocultar Menú",
            width=135,
            height=32,
            corner_radius=8,
            fg_color=("#00B4D8", "#00B4D8"),
            hover_color=("#0096B7", "#06B6D4"),
            text_color=("#0F2042", "#0F2042"),
            font=(F_TEXTO, 11, "bold"),
            command=self.toggle_sidebar
        )
        self.btn_toggle_menu.pack(side="left", padx=14, pady=8)

        # Indicador de módulo activo
        self.l_modulo_activo = ctk.CTkLabel(
            self.toolbar,
            text="Panel de Control · ⌂ Inicio",
            font=(F_TEXTO, 12, "bold"),
            text_color=("#0F2042", "#FFFFFF")
        )
        self.l_modulo_activo.pack(side="left", padx=10)

        # Información derecha de sesión, reloj y conexión
        f_der_tool = ctk.CTkFrame(self.toolbar, fg_color="transparent")
        f_der_tool.pack(side="right", padx=16)

        self.l_reloj_tool = ctk.CTkLabel(
            f_der_tool,
            text="",
            font=(F_TEXTO, 11, "bold"),
            text_color=("#00B4D8", "#00B4D8")
        )
        self.l_reloj_tool.pack(side="left", padx=(0, 14))

        nombre_u = getattr(config, "USUARIO_NOMBRE", "") or self.usuario_actual.get("username", "Usuario")
        rol_display = "Directiva" if self.es_duena else "Administración"
        ctk.CTkLabel(
            f_der_tool,
            text=f"👤 {nombre_u} [{rol_display}]",
            font=(F_TEXTO, 11, "bold"),
            text_color=MORADO
        ).pack(side="left", padx=(0, 14))

        self.l_status_bd = ctk.CTkLabel(
            f_der_tool,
            text="🟢 Conectado",
            font=(F_TEXTO, 11),
            text_color="#059669"
        )
        self.l_status_bd.pack(side="left")

    def _actualizar_reloj_superior(self):
        try:
            ahora = datetime.now()
            txt = ahora.strftime("%I:%M:%S %p")
            if hasattr(self, "l_reloj_tool"):
                self.l_reloj_tool.configure(text=f"🕒 {txt}")
        except Exception:
            pass
        try:
            self._reloj_job = self.after(1000, self._actualizar_reloj_superior)
        except Exception:
            pass

    def _verificar_cierre_diario_automatico(self):
        """Monitorea en segundo plano para ejecutar el cierre diario a las 11:59 PM (23:59)."""
        try:
            ahora = datetime.now()
            hoy = ahora.date()

            # Disparar si la hora es 23:59 y no se ha ejecutado hoy
            if ahora.hour == 23 and ahora.minute == 59 and self._ultimo_cierre_auto != hoy:
                id_u = getattr(self, "usuario_actual", {}).get("id_usuario") or config.USUARIO_ID
                self.db.ejecutar_cierre_diario(hoy, id_u)
                self._ultimo_cierre_auto = hoy
                print(f"[Asista] Cierre diario de {hoy} ejecutado automáticamente a las 23:59.")
                if hasattr(self, "vistas") and "justif" in self.vistas:
                    try:
                        self.vistas["justif"].cargar_cierres_diarios()
                    except Exception:
                        pass
        except Exception as e_cierre:
            print(f"[Asista] Error en verificación de cierre automático: {e_cierre}")

        try:
            self.after(30000, self._verificar_cierre_diario_automatico)
        except Exception:
            pass

    def toggle_sidebar(self):
        if self.sidebar_visible:
            self.lado.grid_remove()
            self.btn_toggle_menu.configure(
                text="☰  Mostrar Menú",
                fg_color=("#00B4D8", "#00B4D8"),
                hover_color=("#0096B7", "#06B6D4")
            )
            self.sidebar_visible = False
        else:
            self.lado.grid()
            self.btn_toggle_menu.configure(
                text="◀  Ocultar Menú",
                fg_color=("#00B4D8", "#00B4D8"),
                hover_color=("#0096B7", "#06B6D4")
            )
            self.sidebar_visible = True

    def _arranque(self):
        self._asegurar_servicio_autonomo()
        self.mostrar("inicio")

    def _tema(self):
        oscuro = bool(self.oscuro.get())
        ctk.set_appearance_mode("dark" if oscuro else "light")
        estilo_tablas()
        if hasattr(self, "toolbar"):
            self.toolbar.configure(
                fg_color="#0F2042" if oscuro else "#FFFFFF",
                border_color="#1E3A6D" if oscuro else "#E2E8F0"
            )
        if hasattr(self, "l_modulo_activo"):
            self.l_modulo_activo.configure(text_color="#FFFFFF" if oscuro else "#1E0B3A")
        for v in self.vistas.values():
            v.actualizar_tema()

    def mostrar(self, clave):
        if clave == "admin" and not self.es_admin:
            messagebox.showwarning(
                "Acceso Denegado",
                "Módulo restringido por política RBAC.\nSolo los usuarios con rol de Administrador pueden acceder a este apartado."
            )
            return

        if clave not in self.vistas:
            return

        for k, b in self.nav.items():
            activo = k == clave
            b.configure(
                fg_color="#00B4D8" if activo else "transparent",
                text_color="#0F2042" if activo else "#E2E8F0",
                hover_color="#06B6D4" if activo else "#162C55"
            )
        nombres_mod = {
            "inicio": "Panel de Control · ⌂ Inicio",
            "marcaje": "Asistencia Diaria · ✓ Marcaje Rápido",
            "personas": "Catálogo Escolar · ◉ Personas y Estudiantes",
            "justif": "Control Mensual · ✎ Justificaciones y Cierres",
            "reportes": "Centro de Informes · ▤ Reportes PDF y Excel",
            "admin": "Configuración del Sistema · ⚙ Administración"
        }
        if hasattr(self, "l_modulo_activo"):
            self.l_modulo_activo.configure(text=nombres_mod.get(clave, f"Módulo · {clave}"))

        for k, v in self.vistas.items():
            if k != clave:
                v.grid_remove()
        self.vistas[clave].grid(row=0, column=0, sticky="nsew")
        self.vistas[clave].refrescar()

    def _asegurar_servicio_autonomo(self):
        try:
            import urllib.request
            contexto_ssl = ssl._create_unverified_context()
            try:
                urllib.request.urlopen(
                    "https://127.0.0.1:8080/api/status",
                    timeout=0.5,
                    context=contexto_ssl
                )
                return
            except Exception:
                urllib.request.urlopen("http://127.0.0.1:8080/api/status", timeout=0.5)
                return
        except Exception:
            pass

        try:
            import threading
            import servicio_asista
            t = threading.Thread(target=servicio_asista.iniciar_servidor, args=(8080,), daemon=True)
            t.start()
        except Exception:
            pass

    def on_cerrar_con_x(self):
        """Al cerrar con la X no se borra la sesión; queda abierta para la próxima vez."""
        try:
            self.destroy()
        except Exception:
            pass
        sys.exit(0)

    def cerrar_sesion(self):
        """Cierre explícito de sesión: borra el archivo de persistencia y abre el login."""
        if messagebox.askyesno("Cerrar Sesión", "¿Está seguro de que desea cerrar la sesión actual?"):
            borrar_sesion_activa()
            try:
                self.destroy()
            except Exception:
                pass
            db_temp = Database()
            login = VentanaLogin(db_temp, iniciar_sistema)
            login.mainloop()

    def report_callback_exception(self, exc, val, tb):
        traceback.print_exception(exc, val, tb)
        messagebox.showerror("Error inesperado", str(val))


def iniciar_sistema(usuario):
    """Inicializa la sesión con control RBAC, guarda la sesión activa y arranca la ventana principal."""
    if isinstance(usuario, dict):
        config.USUARIO_ID = usuario.get("id_usuario")
        config.USUARIO_ACTUAL = usuario
        config.USUARIO_ROL = usuario.get("rol_sistema", "Control")
        config.USUARIO_CARGO = usuario.get("cargo", "")
        config.USUARIO_NOMBRE = usuario.get("nombre_persona") or usuario.get("username", "")
        config.USUARIO_ES_DUENA = usuario.get("es_duena", False)
    else:
        config.USUARIO_ID = usuario
        db_temp = Database()
        info = db_temp.obtener_usuario_por_id(usuario)
        if info:
            config.USUARIO_ACTUAL = info
            config.USUARIO_ROL = info.get("rol_sistema", "Control")
            config.USUARIO_CARGO = info.get("cargo", "")
            config.USUARIO_NOMBRE = info.get("nombre_persona") or info.get("username", "")
        else:
            config.USUARIO_ACTUAL = {"id_usuario": usuario, "rol_sistema": "Docente"}
            config.USUARIO_ROL = "Docente"

    # Persistir sesión activa en disco
    guardar_sesion_activa(config.USUARIO_ACTUAL)

    app = App()
    app.mainloop()


if __name__ == "__main__":
    db_temp = Database()
    # Verificar si existe una sesión activa persistente (cuando salieron con la X)
    sesion = cargar_sesion_activa(db_temp)
    if sesion:
        iniciar_sistema(sesion)
    else:
        login = VentanaLogin(db_temp, iniciar_sistema)
        login.mainloop()
