"""Módulo de Inicio de Sesión y Registro con control institucional para Asista."""
import os
from datetime import datetime
import socket
from tkinter import messagebox
import customtkinter as ctk
import bcrypt

from tema import logo_check, RUTA_ICONO

# Estilos y colores institucionales fijos para evitar errores de importación
BG = "#F8F9FA"
CARD = "#FFFFFF"
BORDE = "#E5E7EB"
TEXTO = "#1F2937"
SUAVE = "#6B7280"
MORADO = "#0F2042"
PRIMARIO = "#0F2042"
PRIMARIO_H = "#0A1428"
F_TITULO = "Segoe UI"
F_TEXTO = "Segoe UI"

# Control de intentos fallidos (Anti-fuerza bruta en escritorio)
INTENTOS_FALLIDOS = {}  # {username: (num_intentos, timestamp_bloqueo)}
VENTANA_BLOQUEO_SEGUNDOS = 15 * 60
MAX_INTENTOS_FALLIDOS = 5


class DialogoCambioClavePrimerIngreso(ctk.CTkToplevel):
    """Diálogo modal obligatorio para forzar el cambio de contraseña en el primer inicio de sesión."""
    def __init__(self, master, db, id_usuario, username, al_completar):
        super().__init__(master)
        self.db = db
        self.id_usuario = id_usuario
        self.username = username
        self.al_completar = al_completar

        self.title("Asista · Primer Inicio de Sesión")
        self.geometry("450x520")
        self.resizable(False, False)
        self.configure(fg_color=BG)
        self.transient(master)
        self.grab_set()

        if os.path.exists(RUTA_ICONO):
            try:
                self.iconbitmap(RUTA_ICONO)
            except Exception:
                pass

        # Centrar ventana
        self.update_idletasks()
        ancho = 450
        alto = 520
        x = (self.winfo_screenwidth() // 2) - (ancho // 2)
        y = (self.winfo_screenheight() // 2) - (alto // 2)
        self.geometry(f"{ancho}x{alto}+{x}+{y}")

        self._crear_interfaz()

    def _crear_interfaz(self):
        header = ctk.CTkFrame(self, fg_color="#0F2042", corner_radius=0, height=90)
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkLabel(
            header, text="🔒 Cambio Obligatorio de Contraseña",
            font=(F_TITULO, 16, "bold"), text_color="white"
        ).pack(pady=(18, 2))
        ctk.CTkLabel(
            header, text="Primer acceso detectado para: " + self.username,
            font=(F_TEXTO, 12), text_color="#A5F3FC"
        ).pack()

        cuerpo = ctk.CTkFrame(self, fg_color="transparent")
        cuerpo.pack(fill="both", expand=True, padx=30, pady=20)

        ctk.CTkLabel(
            cuerpo,
            text="Por estrictas políticas de seguridad institucional, debe definir una contraseña personal y segura antes de ingresar al sistema.",
            font=(F_TEXTO, 11), text_color=TEXTO, wraplength=380, justify="left"
        ).pack(anchor="w", pady=(0, 15))

        ctk.CTkLabel(cuerpo, text="Nueva Contraseña", font=(F_TEXTO, 12, "bold"), text_color=TEXTO).pack(anchor="w", pady=(0, 4))
        self.e_nueva = ctk.CTkEntry(cuerpo, placeholder_text="Mínimo 8 caracteres", show="*", height=40, fg_color=CARD, border_color=BORDE, text_color=TEXTO)
        self.e_nueva.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(cuerpo, text="Confirmar Nueva Contraseña", font=(F_TEXTO, 12, "bold"), text_color=TEXTO).pack(anchor="w", pady=(0, 4))
        self.e_confirma = ctk.CTkEntry(cuerpo, placeholder_text="Repita la nueva contraseña", show="*", height=40, fg_color=CARD, border_color=BORDE, text_color=TEXTO)
        self.e_confirma.pack(fill="x", pady=(0, 15))

        f_req = ctk.CTkFrame(cuerpo, fg_color="#F1F5F9", corner_radius=8)
        f_req.pack(fill="x", pady=(0, 18))
        txt_req = "• Mínimo 8 caracteres  • Una mayúscula  • Una minúscula\n• Al menos un número  • Un símbolo especial (@$!%*?&#.-)"
        ctk.CTkLabel(f_req, text=txt_req, font=(F_TEXTO, 10), text_color="#334155", justify="left").pack(padx=10, pady=8)

        btn_guardar = ctk.CTkButton(
            cuerpo, text="Establecer Contraseña e Ingresar", command=self._guardar_clave,
            fg_color="#0F2042", hover_color="#0A1428", height=44, font=(F_TEXTO, 13, "bold"), corner_radius=10
        )
        btn_guardar.pack(fill="x", pady=(0, 8))

        btn_cancelar = ctk.CTkButton(
            cuerpo, text="Cancelar", command=self.destroy,
            fg_color="transparent", text_color="#64748B", hover_color="#E2E8F0", height=32, font=(F_TEXTO, 11)
        )
        btn_cancelar.pack(fill="x")

    def _guardar_clave(self):
        from config import validar_password_rigurosa
        p1 = self.e_nueva.get().strip()
        p2 = self.e_confirma.get().strip()

        if not p1 or not p2:
            messagebox.showwarning("Atención", "Por favor complete ambos campos.", parent=self)
            return

        if p1 != p2:
            messagebox.showerror("Error", "Las contraseñas ingresadas no coinciden.", parent=self)
            return

        valida, msg = validar_password_rigurosa(p1)
        if not valida:
            messagebox.showwarning("Requisitos de Seguridad", msg, parent=self)
            return

        try:
            nuevo_hash = bcrypt.hashpw(p1.encode("utf-8"), bcrypt.gensalt(12)).decode("utf-8")
            self.db.cambiar_password_primer_ingreso(self.id_usuario, nuevo_hash)
            messagebox.showinfo("Éxito", "Su contraseña ha sido actualizada con éxito.\nBienvenido al sistema.", parent=self)
            self.destroy()
            if self.al_completar:
                self.al_completar()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo actualizar la contraseña: {e}", parent=self)


class VentanaLogin(ctk.CTk):
    def __init__(self, db, on_login_exitoso):
        super().__init__()
        self.db = db
        self.on_login_exitoso = on_login_exitoso

        self.title("Asista · Iniciar Sesión")
        self.geometry("460x740")
        self._asegurar_servicio()
        self.resizable(False, False)
        self.configure(fg_color=BG)
        if os.path.exists(RUTA_ICONO):
            try:
                self.iconbitmap(RUTA_ICONO)
            except Exception:
                pass

        # Centrar ventana
        self.update_idletasks()
        ancho = self.winfo_width()
        alto = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (ancho // 2)
        y = (self.winfo_screenheight() // 2) - (alto // 2)
        self.geometry(f"{ancho}x{alto}+{x}+{y}")

        self._crear_interfaz()
        self._actualizar_reloj()

    def _crear_interfaz(self):
        header = ctk.CTkFrame(self, fg_color=MORADO, corner_radius=0, height=160)
        header.pack(fill="x")
        header.pack_propagate(False)

        marca = ctk.CTkFrame(header, fg_color="transparent")
        marca.pack(expand=True)
        
        img_logo = logo_check("#FFFFFF", 44)
        self.img_tk = ctk.CTkImage(light_image=img_logo, size=img_logo.size)
        ctk.CTkLabel(marca, text="", image=self.img_tk).pack(side="left", padx=(0, 10))
        ctk.CTkLabel(marca, text="Asista", font=(F_TITULO, 32, "bold"), text_color="white").pack(side="left")

        self.l_reloj = ctk.CTkLabel(header, text="", font=(F_TEXTO, 11), text_color="#A5F3FC")
        self.l_reloj.pack(side="bottom", pady=10)

        cuerpo = ctk.CTkFrame(self, fg_color="transparent")
        cuerpo.pack(fill="both", expand=True, padx=35, pady=30)

        ctk.CTkLabel(cuerpo, text="Bienvenido", font=(F_TITULO, 22, "bold"), text_color=TEXTO).pack(anchor="w", pady=(0, 5))
        ctk.CTkLabel(cuerpo, text="Ingrese sus credenciales institucionales", font=(F_TEXTO, 12), text_color=SUAVE).pack(anchor="w", pady=(0, 20))

        ctk.CTkLabel(cuerpo, text="Usuario", font=(F_TEXTO, 12, "bold"), text_color=TEXTO).pack(anchor="w", pady=(0, 4))
        self.e_user = ctk.CTkEntry(cuerpo, placeholder_text="Nombre de usuario", height=42, fg_color=CARD, border_color=BORDE, text_color=TEXTO, font=(F_TEXTO, 13))
        self.e_user.pack(fill="x", pady=(0, 15))

        ctk.CTkLabel(cuerpo, text="Cargo Institucional", font=(F_TEXTO, 12, "bold"), text_color=TEXTO).pack(anchor="w", pady=(0, 4))
        self.cb_cargo = ctk.CTkComboBox(
            cuerpo,
            values=["Directivo", "Administrativo"],
            height=42, fg_color=CARD, border_color=BORDE, text_color=TEXTO, font=(F_TEXTO, 13)
        )
        self.cb_cargo.pack(fill="x", pady=(0, 15))
        self.cb_cargo.set("Directivo")

        ctk.CTkLabel(cuerpo, text="Contraseña", font=(F_TEXTO, 12, "bold"), text_color=TEXTO).pack(anchor="w", pady=(0, 4))
        self.e_pass = ctk.CTkEntry(cuerpo, placeholder_text="Contraseña", show="*", height=42, fg_color=CARD, border_color=BORDE, text_color=TEXTO, font=(F_TEXTO, 13))
        self.e_pass.pack(fill="x", pady=(0, 20))
        self.e_pass.bind("<Return>", lambda e: self.iniciar_sesion())

        btn_ingresar = ctk.CTkButton(cuerpo, text="Iniciar Sesión", command=self.iniciar_sesion, fg_color=PRIMARIO, hover_color=PRIMARIO_H, height=45, font=(F_TEXTO, 14, "bold"), corner_radius=12)
        btn_ingresar.pack(fill="x", pady=(0, 10))

        # Indicador de acceso restringido (Seguridad RBAC institucional - Sin registro público)
        f_info_seg = ctk.CTkFrame(cuerpo, fg_color="transparent")
        f_info_seg.pack(fill="x", pady=(0, 6))
        ctk.CTkLabel(
            f_info_seg,
            text="🔒 Acceso exclusivo para Directora y Administración",
            font=(F_TEXTO, 11), text_color=SUAVE
        ).pack()

        # Separador visual
        f_div = ctk.CTkFrame(cuerpo, fg_color="transparent")
        f_div.pack(fill="x", pady=(10, 10))
        ctk.CTkFrame(f_div, fg_color=BORDE, height=1).pack(fill="x")

        # Botón Terminal de Marcaje Autónomo (Sin Clave)
        btn_kiosco = ctk.CTkButton(
            cuerpo, text="📷 Terminal de Marcaje (Sin Clave)",
            command=self.abrir_terminal_marcaje,
            fg_color="#10B981", hover_color="#059669", text_color="white",
            height=44, font=(F_TEXTO, 13, "bold"), corner_radius=12
        )
        btn_kiosco.pack(fill="x", pady=(0, 8))

        # Botón Escáner Celular por Código QR
        btn_qr = ctk.CTkButton(
            cuerpo, text="📱 Escáner Celular (Código QR)",
            command=self.abrir_qr_movil,
            fg_color="#F3F4F6", hover_color="#E5E7EB", text_color=TEXTO,
            height=38, font=(F_TEXTO, 12, "bold"), corner_radius=10
        )
        btn_qr.pack(fill="x", pady=(0, 8))

        # Indicador de Servicio en Segundo Plano
        f_serv = ctk.CTkFrame(cuerpo, fg_color="#ECFDF5", corner_radius=8)
        f_serv.pack(fill="x")
        ctk.CTkLabel(
            f_serv, text="🟢 Servicio autónomo activo en segundo plano",
            font=(F_TEXTO, 10, "bold"), text_color="#047857"
        ).pack(pady=4)

    def _asegurar_servicio(self):
        try:
            import servicio_asista
        except ImportError as exc:
            messagebox.showerror("Servicio móvil no disponible", f"No se pudo cargar el servicio ASISTA:\n{exc}")
            return

        if not servicio_asista.asegurar_servidor():
            messagebox.showwarning(
                "Servicio móvil no disponible",
                "No se pudo iniciar el servidor en los puertos HTTP configurados. "
                "No se cerraron otros procesos; revise servicio_asista.log y los puertos 8080–8089/8443."
            )

    def abrir_terminal_marcaje(self):
        from views.vista_kiosco import VentanaTerminalMarcaje
        VentanaTerminalMarcaje(self, self.db)

    def abrir_qr_movil(self):
        from views.componentes import DialogoQRMovil
        DialogoQRMovil(self)

    def _actualizar_reloj(self):
        ahora = datetime.now()
        self.l_reloj.configure(text=ahora.strftime("%A, %d de %B de %Y - %H:%M:%S").capitalize())
        self.after(1000, self._actualizar_reloj)

    def iniciar_sesion(self):
        import time
        user = self.e_user.get().strip()
        pwd = self.e_pass.get().strip()

        if not user or not pwd:
            messagebox.showwarning("Atención", "Por favor, complete todos los campos.")
            return

        # 1. Protección contra ataques de fuerza bruta
        ahora_ts = time.time()
        intentos_prev, fin_bloqueo = INTENTOS_FALLIDOS.get(user, (0, 0))
        if fin_bloqueo > ahora_ts:
            minutos = int((fin_bloqueo - ahora_ts) // 60) + 1
            messagebox.showerror(
                "Acceso Bloqueado Temporalmente",
                f"Por seguridad institucional, esta cuenta está bloqueada tras múltiples intentos fallidos.\n\nIntente nuevamente en {minutos} minuto(s)."
            )
            return

        try:
            cargo_sel = self.cb_cargo.get().strip()

            # Consulta con RBAC: recupera rol, privilegios de dueña, primer_ingreso y cargo institucional
            res = self.db.fetch_one("""
                SELECT u.id_usuario, u.username, u.password_encriptada, u.rol_sistema, u.es_duena,
                       u.primer_ingreso, pe.cargo, CONCAT(p.nombre, ' ', p.apellido) AS nombre_persona
                FROM usuario u
                LEFT JOIN personal pe ON pe.id_personal = u.id_personal
                LEFT JOIN persona p ON p.id_persona = pe.id_persona
                WHERE u.username = %s AND u.activo = 1
            """, (user,))
            
            if not res:
                self._registrar_fallo_login(user, ahora_ts, intentos_prev)
                return

            id_usuario = res["id_usuario"]
            pwd_hash = res["password_encriptada"]

            valido = False
            if pwd_hash.startswith("$2b$") or pwd_hash.startswith("$2a$"):
                valido = bcrypt.checkpw(pwd.encode('utf-8'), pwd_hash.encode('utf-8'))
            else:
                res_sha = self.db.fetch_one("SELECT id_usuario FROM usuario WHERE username = %s AND password_encriptada = SHA2(%s, 256)", (user, pwd))
                valido = bool(res_sha)

            if not valido:
                self._registrar_fallo_login(user, ahora_ts, intentos_prev)
                return

            # Éxito en validación de credenciales: resetear contador de fallos
            INTENTOS_FALLIDOS.pop(user, None)

            # 2. Control de Acceso Estricto por Rol (RBAC de Escritorio)
            rol_actual = res.get("rol_sistema", "Control")
            if rol_actual not in ("Directivo", "Administrador"):
                from servicio_asista import obtener_ip_local, obtener_url_movil
                ip_actual = obtener_ip_local()
                url_movil = obtener_url_movil(ip_actual, "/profesor")
                messagebox.showwarning(
                    "Acceso Exclusivo al Portal Móvil",
                    f"Acceso restringido.\n\n"
                    f"El usuario '{user}' posee el rol de '{rol_actual}'.\n\n"
                    "Por normativa de seguridad institucional, la aplicación de escritorio está reservada exclusivamente para la Directora y la Administración.\n\n"
                    f"Los profesores deben acceder desde su teléfono celular al portal de escaneo y asistencia:\n"
                    f"{url_movil or 'Servicio móvil no disponible; reinicie ASISTA en la misma red Wi-Fi.'}"
                )
                return

            # 3. Validación de coincidencia de cargo institucional
            cargo_bd = res.get("cargo") or ""
            if cargo_sel.lower() != cargo_bd.lower():
                messagebox.showerror(
                    "Cargo Incorrecto",
                    f"El cargo seleccionado ('{cargo_sel}') no coincide con el cargo registrado en el sistema para este usuario ('{cargo_bd}').\nPor favor verifique su selección."
                )
                return

            # 4. Verificar si es primer inicio de sesión obligatorio
            primer_ingreso = bool(res.get("primer_ingreso", 0))
            if primer_ingreso:
                DialogoCambioClavePrimerIngreso(
                    self, self.db, id_usuario, user,
                    al_completar=lambda: self._completar_login_exitoso(res, cargo_bd, id_usuario, user, rol_actual)
                )
            else:
                self._completar_login_exitoso(res, cargo_bd, id_usuario, user, rol_actual)

        except Exception as e:
            messagebox.showerror("Error", f"Ocurrió un error al iniciar sesión: {e}")

    def _registrar_fallo_login(self, user, ahora_ts, intentos_prev):
        intentos = intentos_prev + 1
        if intentos >= MAX_INTENTOS_FALLIDOS:
            INTENTOS_FALLIDOS[user] = (intentos, ahora_ts + VENTANA_BLOQUEO_SEGUNDOS)
            messagebox.showerror(
                "Acceso Bloqueado",
                f"Ha superado el límite de {MAX_INTENTOS_FALLIDOS} intentos fallidos.\nLa cuenta ha sido bloqueada temporalmente por 15 minutos."
            )
        else:
            INTENTOS_FALLIDOS[user] = (intentos, 0)
            restantes = MAX_INTENTOS_FALLIDOS - intentos
            messagebox.showerror("Error de Acceso", f"Usuario o contraseña incorrectos.\nIntentos restantes: {restantes}")

    def _completar_login_exitoso(self, res, cargo_bd, id_usuario, user, rol_actual):
        try:
            equipo = socket.gethostname()
            self.db.execute("INSERT INTO auditoria_ingresos (id_usuario, equipo) VALUES (%s, %s)", (id_usuario, equipo))
        except Exception as err_aud:
            print(f"Aviso de auditoría: {err_aud}")
        
        nombre_vis = res.get("nombre_persona") or user
        es_duena_val = bool(res.get("es_duena", 0))
        perfil_txt = "Directiva" if es_duena_val else "Administración"
        messagebox.showinfo("Bienvenido", f"Acceso concedido.\n¡Hola, {nombre_vis}!\nCargo: {cargo_bd}\nPerfil de Acceso: {perfil_txt}")
        self.destroy()

        # Estructura completa de sesión para RBAC
        usuario_info = {
            "id_usuario": id_usuario,
            "username": user,
            "rol_sistema": rol_actual,
            "cargo": cargo_bd,
            "es_duena": es_duena_val,
            "nombre_persona": nombre_vis
        }
        self.on_login_exitoso(usuario_info)

    def abrir_registro(self):
        VentanaRegistro(self, self.db)


class VentanaRegistro(ctk.CTkToplevel):
    def __init__(self, master, db):
        super().__init__(master)
        self.db = db
        self.title("Asista · Registro de Usuario")
        self.geometry("450x640")
        self.minsize(440, 580)
        self.resizable(False, False)
        self.configure(fg_color=BG)
        if os.path.exists(RUTA_ICONO):
            try:
                self.iconbitmap(RUTA_ICONO)
            except Exception:
                pass
        self.transient(master)
        self.grab_set()

        ctk.CTkLabel(self, text="Crear Cuenta de Usuario", font=(F_TITULO, 20, "bold"), text_color=TEXTO).pack(pady=(18, 4))
        
        # Cargar personal disponible sin usuario
        try:
            self.personal_disp = self.db.personal_sin_usuario()
        except Exception:
            self.personal_disp = []

        # Selector de modo (Registrar Nuevo Personal vs Personal Existente)
        f_modo = ctk.CTkFrame(self, fg_color="transparent")
        f_modo.pack(fill="x", padx=30, pady=(8, 12))

        opciones_modo = ["Registrar Nuevo Personal"]
        if self.personal_disp:
            opciones_modo.insert(0, "Personal Existente")

        self.seg_modo = ctk.CTkSegmentedButton(
            f_modo,
            values=opciones_modo,
            command=self._cambiar_modo,
            fg_color=("#E2E8F0", "#162C55"),
            unselected_color=("#E2E8F0", "#162C55"),
            selected_color=("#00B4D8", "#00B4D8"),
            selected_hover_color=("#0096B7", "#06B6D4"),
            text_color=("#0F2042", "#0F2042"),
            font=(F_TEXTO, 11, "bold"),
            height=34,
            corner_radius=12
        )
        self.seg_modo.pack(fill="x")
        self.seg_modo.set(opciones_modo[0])

        self.form_container = ctk.CTkFrame(self, fg_color="transparent")
        self.form_container.pack(fill="both", expand=True, padx=30, pady=(0, 16))

        self._construir_formulario()

    def _cambiar_modo(self, _val=None):
        for widget in self.form_container.winfo_children():
            widget.destroy()
        self._construir_formulario()

    def _construir_formulario(self):
        modo = self.seg_modo.get()

        if modo == "Personal Existente" and self.personal_disp:
            ctk.CTkLabel(self.form_container, text="Seleccionar Personal Institucional", font=(F_TEXTO, 11, "bold"), text_color=TEXTO).pack(anchor="w")
            etiquetas_personal = [p["etiqueta"] for p in self.personal_disp]
            self.cb_personal = ctk.CTkComboBox(self.form_container, values=etiquetas_personal, height=38, fg_color=CARD, border_color=BORDE, text_color=TEXTO, command=self._sugerir_rol)
            self.cb_personal.pack(fill="x", pady=(2, 10))
            self.cb_personal.set(etiquetas_personal[0])

            ctk.CTkLabel(self.form_container, text="Rol del Sistema (Permisos)", font=(F_TEXTO, 11, "bold"), text_color=TEXTO).pack(anchor="w")
            self.cb_rol = ctk.CTkComboBox(self.form_container, values=["Administración", "Directiva"], height=38, fg_color=CARD, border_color=BORDE, text_color=TEXTO)
            self.cb_rol.pack(fill="x", pady=(2, 10))
            self._sugerir_rol(None)

            ctk.CTkLabel(self.form_container, text="Nombre de Usuario (Username)", font=(F_TEXTO, 11, "bold"), text_color=TEXTO).pack(anchor="w")
            self.e_user = ctk.CTkEntry(self.form_container, height=38, fg_color=CARD, border_color=BORDE, text_color=TEXTO)
            self.e_user.pack(fill="x", pady=(2, 10))

            ctk.CTkLabel(self.form_container, text="Contraseña Segura (Mínimo 8 car., Mayús, Núm, Símbolo)", font=(F_TEXTO, 11, "bold"), text_color=TEXTO).pack(anchor="w")
            self.e_pass = ctk.CTkEntry(self.form_container, show="*", height=38, fg_color=CARD, border_color=BORDE, text_color=TEXTO)
            self.e_pass.pack(fill="x", pady=(2, 16))

        else:
            # Modo: Registrar Nuevo Personal
            ctk.CTkLabel(self.form_container, text="Cédula de Identidad", font=(F_TEXTO, 11, "bold"), text_color=TEXTO).pack(anchor="w")
            self.e_cedula = ctk.CTkEntry(self.form_container, placeholder_text="ej: 25111222", height=36, fg_color=CARD, border_color=BORDE, text_color=TEXTO)
            self.e_cedula.pack(fill="x", pady=(2, 8))

            f_nombres = ctk.CTkFrame(self.form_container, fg_color="transparent")
            f_nombres.pack(fill="x", pady=(0, 8))
            f_nombres.grid_columnconfigure(0, weight=1)
            f_nombres.grid_columnconfigure(1, weight=1)

            ctk.CTkLabel(f_nombres, text="Nombre", font=(F_TEXTO, 11, "bold"), text_color=TEXTO).grid(row=0, column=0, sticky="w", padx=(0, 4))
            ctk.CTkLabel(f_nombres, text="Apellido", font=(F_TEXTO, 11, "bold"), text_color=TEXTO).grid(row=0, column=1, sticky="w", padx=(4, 0))

            self.e_nombre = ctk.CTkEntry(f_nombres, placeholder_text="ej: Laura", height=36, fg_color=CARD, border_color=BORDE, text_color=TEXTO)
            self.e_nombre.grid(row=1, column=0, sticky="ew", padx=(0, 4))

            self.e_apellido = ctk.CTkEntry(f_nombres, placeholder_text="ej: Gómez", height=36, fg_color=CARD, border_color=BORDE, text_color=TEXTO)
            self.e_apellido.grid(row=1, column=1, sticky="ew", padx=(4, 0))

            f_cargos = ctk.CTkFrame(self.form_container, fg_color="transparent")
            f_cargos.pack(fill="x", pady=(0, 8))
            f_cargos.grid_columnconfigure(0, weight=1)
            f_cargos.grid_columnconfigure(1, weight=1)

            ctk.CTkLabel(f_cargos, text="Cargo Institucional", font=(F_TEXTO, 11, "bold"), text_color=TEXTO).grid(row=0, column=0, sticky="w", padx=(0, 4))
            ctk.CTkLabel(f_cargos, text="Rol del Sistema", font=(F_TEXTO, 11, "bold"), text_color=TEXTO).grid(row=0, column=1, sticky="w", padx=(4, 0))

            self.cb_cargo_nuevo = ctk.CTkComboBox(f_cargos, values=["Administrativo", "Directivo"], height=36, fg_color=CARD, border_color=BORDE, text_color=TEXTO)
            self.cb_cargo_nuevo.grid(row=1, column=0, sticky="ew", padx=(0, 4))
            self.cb_cargo_nuevo.set("Administrativo")

            self.cb_rol = ctk.CTkComboBox(f_cargos, values=["Administración", "Directiva"], height=36, fg_color=CARD, border_color=BORDE, text_color=TEXTO)
            self.cb_rol.grid(row=1, column=1, sticky="ew", padx=(4, 0))
            self.cb_rol.set("Administrador")

            ctk.CTkLabel(self.form_container, text="Nombre de Usuario (Username)", font=(F_TEXTO, 11, "bold"), text_color=TEXTO).pack(anchor="w")
            self.e_user = ctk.CTkEntry(self.form_container, placeholder_text="ej: laura.secretaria", height=36, fg_color=CARD, border_color=BORDE, text_color=TEXTO)
            self.e_user.pack(fill="x", pady=(2, 8))

            ctk.CTkLabel(self.form_container, text="Contraseña Segura", font=(F_TEXTO, 11, "bold"), text_color=TEXTO).pack(anchor="w")
            self.e_pass = ctk.CTkEntry(self.form_container, show="*", placeholder_text="Mínimo 8 caracteres, mayúscula, número y símbolo", height=36, fg_color=CARD, border_color=BORDE, text_color=TEXTO)
            self.e_pass.pack(fill="x", pady=(2, 16))

        ctk.CTkButton(self.form_container, text="Guardar Usuario", command=self.guardar, fg_color=PRIMARIO, hover_color=PRIMARIO_H, height=42, font=(F_TEXTO, 13, "bold"), corner_radius=12).pack(fill="x")

    def _sugerir_rol(self, _choice):
        try:
            sel_idx = self.cb_personal.cget("values").index(self.cb_personal.get())
            cargo = self.personal_disp[sel_idx]["nombre_cargo"]
            if cargo == "Directivo":
                self.cb_rol.set("Directivo")
            elif cargo in ("Vigilante", "Obrero"):
                self.cb_rol.set("Control")
            elif cargo == "Docente":
                self.cb_rol.set("Docente")
            else:
                self.cb_rol.set("Administrador")
        except Exception:
            self.cb_rol.set("Docente")

    def guardar(self):
        username = self.e_user.get().strip()
        password = self.e_pass.get().strip()
        rol = self.cb_rol.get()
        modo = self.seg_modo.get()

        from config import validar_password_rigurosa
        valida, msg_pass = validar_password_rigurosa(password)
        if not valida:
            messagebox.showwarning("Contraseña no cumple requisitos", msg_pass)
            return

        if not username:
            messagebox.showwarning("Atención", "Ingrese un nombre de usuario.")
            return

        try:
            hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

            if modo == "Personal Existente" and self.personal_disp:
                sel_idx = self.cb_personal.cget("values").index(self.cb_personal.get())
                id_personal = self.personal_disp[sel_idx]["id_personal"]
                self.db.crear_usuario(id_personal, username, hashed, 'Directivo' if rol == 'Directiva' else 'Administrador')
                messagebox.showinfo("Éxito", f"Usuario '{username}' registrado correctamente con rol {rol}.")
            else:
                # Registrar nuevo personal y usuario juntos
                cedula = self.e_cedula.get().strip()
                nombre = self.e_nombre.get().strip()
                apellido = self.e_apellido.get().strip()
                cargo = self.cb_cargo_nuevo.get()

                if not cedula or not nombre or not apellido:
                    messagebox.showwarning("Atención", "Por favor complete cédula, nombre y apellido del nuevo personal.")
                    return

                self.db.crear_personal_y_usuario(cedula, nombre, apellido, cargo, username, hashed, 'Directivo' if rol == 'Directiva' else 'Administrador')
                messagebox.showinfo("Éxito", f"Personal institucional '{nombre} {apellido}' ({cargo}) y usuario '{username}' creados con éxito.")

            self.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo registrar el usuario: {e}")