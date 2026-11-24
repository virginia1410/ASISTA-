"""Módulo Kiosco / Terminal de Marcaje Autónomo:
Permite registrar asistencias con captura fotográfica de carnets por cámara web,
escáner de código de barras láser o teclado manual SIN requerir inicio de sesión previo.
"""
from datetime import date, datetime
import os
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk
import cv2
import numpy as np
from PIL import Image, ImageTk
try:
    import zxingcpp
except ImportError:
    zxingcpp = None

import config
from db import resolver_turno_persona
from tema import (
    BG, BORDE, CARD, F_TEXTO, F_TITULO, PRIMARIO, PRIMARIO_H, ACENTO, ACENTO_H, AVISO, SUAVE, TEXTO, logo_check
)
from .componentes import DialogoQRMovil


def _beep_exito():
    try:
        import winsound
        winsound.Beep(1400, 120)
    except Exception:
        pass


def _beep_alerta():
    try:
        import winsound
        winsound.Beep(700, 250)
    except Exception:
        pass


def decodificar_imagen_carnet(frame):
    """Pipeline multinivel de reconocimiento óptico exclusivamente para códigos de barras (1D).

    Omite cualquier código QR y decodifica únicamente códigos de barras lineales (Code 128, Code 39, EAN, UPC, ITF).
    """
    if frame is None:
        return None, None, None

    if zxingcpp:
        FORMATOS_LINEALES = zxingcpp.BarcodeFormat.AllLinear
        # 1. Pase directo en BGR con zxingcpp
        try:
            res = zxingcpp.read_barcode(frame, formats=FORMATOS_LINEALES)
            if res and res.text and res.text.strip():
                return res.text.strip(), res.position, 'zxing_bgr'
        except Exception:
            pass

        # 2. Pase en Escala de grises
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        try:
            res = zxingcpp.read_barcode(gray, formats=FORMATOS_LINEALES)
            if res and res.text and res.text.strip():
                return res.text.strip(), res.position, 'zxing_gray'
        except Exception:
            pass

        # 3. Ecualización adaptativa de contraste (CLAHE)
        try:
            clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
            enh = clahe.apply(gray)
            res = zxingcpp.read_barcode(enh, formats=FORMATOS_LINEALES)
            if res and res.text and res.text.strip():
                return res.text.strip(), res.position, 'zxing_clahe'
        except Exception:
            pass

        # 4. Filtro de enfoque / nitidez (Sharpening)
        try:
            kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
            sharp = cv2.filter2D(gray, -1, kernel)
            res = zxingcpp.read_barcode(sharp, formats=FORMATOS_LINEALES)
            if res and res.text and res.text.strip():
                return res.text.strip(), res.position, 'zxing_sharp'
        except Exception:
            pass

        # 5. Umbralizado adaptativo (Gaussian)
        try:
            adapt = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, 5)
            res = zxingcpp.read_barcode(adapt, formats=FORMATOS_LINEALES)
            if res and res.text and res.text.strip():
                return res.text.strip(), res.position, 'zxing_adapt'
        except Exception:
            pass

    # 6. Fallback OpenCV BarcodeDetector y QRCodeDetector (100% nativo)
    try:
        b_det = cv2.barcode.BarcodeDetector()
        t, pts, _ = b_det.detectAndDecode(frame)
        if t and t.strip():
            return t.strip(), pts, 'cv2_bar'
    except Exception:
        pass

    try:
        q_det = cv2.QRCodeDetector()
        val, pts, _ = q_det.detectAndDecode(frame)
        if val and val.strip():
            return val.strip(), pts, 'cv2_qr'
    except Exception:
        pass

    return None, None, None


class VentanaTerminalMarcaje(ctk.CTkToplevel):
    def __init__(self, master, db):
        super().__init__(master, fg_color=BG[0])
        self.db = db
        self.title("Asista · Terminal Autónomo de Marcaje Escolar")
        self.geometry("1020x720")
        self.minsize(920, 640)
        self.transient(master.winfo_toplevel())
        self.after(150, self.grab_set)

        # Variables de control de cámara web y escaneo
        self.cap = None
        self.camara_activa = False
        self.foto_congelada = False
        self.ultimo_frame_nativo = None
        self.frame_lock = threading.Lock()
        self.ultimo_codigo_leido = ""
        self.tiempo_ultimo_escaneo = 0.0
        self._contador_frames_auto = 0

        self.protocol("WM_DELETE_WINDOW", self._cerrar_ventana)

        self._crear_interfaz()
        self._actualizar_reloj()
        self.cargar_feed_hoy()

        # Captura automática global de teclas (teclado, pistola láser y barra espaciadora para foto)
        self.bind("<Key>", self._on_global_key)
        self.e_ced.focus_set()

        # Iniciar cámara web automáticamente al abrir
        self.after(200, self._iniciar_camara)

    def _crear_interfaz(self):
        # 1. Cabecera Superior
        header = ctk.CTkFrame(
            self, fg_color=PRIMARIO[0], corner_radius=0, height=80,
            border_width=1, border_color=BORDE[0]
        )
        header.pack(fill="x")
        header.pack_propagate(False)

        h_left = ctk.CTkFrame(header, fg_color="transparent")
        h_left.pack(side="left", padx=24)

        logo_marco = ctk.CTkFrame(
            h_left, fg_color="transparent", border_width=1, border_color=ACENTO[0],
            corner_radius=10, width=48, height=48
        )
        logo_marco.pack(side="left", padx=(0, 10))
        logo_marco.pack_propagate(False)
        img_logo = logo_check("#FFFFFF", 30)
        self.img_tk = ctk.CTkImage(light_image=img_logo, size=img_logo.size)
        ctk.CTkLabel(logo_marco, text="", image=self.img_tk).pack(expand=True)

        lbl_tit = ctk.CTkLabel(
            h_left, text="Asista · Terminal de Marcaje Escolar",
            font=(F_TITULO, 20, "bold"), text_color=TEXTO[0]
        )
        lbl_tit.pack(side="left")

        h_right = ctk.CTkFrame(header, fg_color="transparent")
        h_right.pack(side="right", padx=24)

        # Botón Encender / Apagar Cámara
        self.btn_toggle_cam = ctk.CTkButton(
            h_right, text="📷 Apagar Cámara", command=self._toggle_camara,
            fg_color=CARD[0], hover_color=SUAVE[0], text_color=TEXTO[0],
            border_width=1, border_color=BORDE[0], height=36, corner_radius=10,
            font=(F_TEXTO, 12, "bold")
        )
        self.btn_toggle_cam.pack(side="left", padx=(0, 10))



        # Botón Login
        btn_login = ctk.CTkButton(
            h_right, text="🔒 Acceso con Login", command=self._cerrar_ventana,
            fg_color=ACENTO[0], hover_color=ACENTO_H[0], text_color=PRIMARIO[0],
            height=36, corner_radius=10, font=(F_TEXTO, 12, "bold")
        )
        btn_login.pack(side="left")

        # 2. Barra de Estado y Reloj en Tiempo Real
        barra_info = ctk.CTkFrame(self, fg_color=CARD[0], height=42, corner_radius=0, border_width=1, border_color=BORDE[0])
        barra_info.pack(fill="x")
        barra_info.pack_propagate(False)

        self.l_reloj = ctk.CTkLabel(barra_info, text="", font=(F_TEXTO, 12, "bold"), text_color=TEXTO[0])
        self.l_reloj.pack(side="left", padx=24)

        self.l_turno = ctk.CTkLabel(barra_info, text="Turno Activo: --", font=(F_TEXTO, 12, "bold"), text_color=ACENTO[0])
        self.l_turno.pack(side="right", padx=24)

        # 3. Contenedor Principal
        cuerpo = ctk.CTkFrame(self, fg_color="transparent")
        cuerpo.pack(fill="both", expand=True, padx=20, pady=12)

        # Sección Superior: Dividida en Izquierda (Entrada/Ficha) y Derecha (Cámara + Botón Foto)
        f_superior = ctk.CTkFrame(cuerpo, fg_color="transparent")
        f_superior.pack(fill="x", pady=(0, 10))
        f_superior.grid_columnconfigure(0, weight=3)
        f_superior.grid_columnconfigure(1, weight=2, minsize=350)

        # --- Columna Izquierda: Entrada + Tarjeta de Marcaje ---
        col_izq = ctk.CTkFrame(f_superior, fg_color="transparent")
        col_izq.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        # Panel de Entrada
        f_scan = ctk.CTkFrame(col_izq, fg_color=CARD[0], corner_radius=14, border_width=1, border_color=BORDE[0])
        f_scan.pack(fill="x", pady=(0, 10))

        f_scan_inner = ctk.CTkFrame(f_scan, fg_color="transparent")
        f_scan_inner.pack(fill="x", padx=16, pady=12)

        ctk.CTkLabel(
            f_scan_inner, text="💳 Lector de Carnets / Cédula Manual:",
            font=(F_TEXTO, 13, "bold"), text_color=TEXTO[0]
        ).pack(anchor="w", pady=(0, 6))

        fila_input = ctk.CTkFrame(f_scan_inner, fg_color="transparent")
        fila_input.pack(fill="x")

        self.e_ced = ctk.CTkEntry(
            fila_input,
            placeholder_text="Pase el carnet por el lector o escriba la cédula...",
            height=44,
            font=(F_TEXTO, 14),
            fg_color=SUAVE_BG[0],
            border_color=BORDE[0],
            text_color=TEXTO[0]
        )
        self.e_ced.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.e_ced.bind("<Return>", self._on_entry_enter)
        self.e_ced.bind("<KP_Enter>", self._on_entry_enter)

        btn_marcar = ctk.CTkButton(
            fila_input,
            text="Marcar",
            command=self.procesar_marcaje,
            fg_color=ACENTO[0],
            hover_color=ACENTO_H[0],
            text_color=PRIMARIO[0],
            height=44,
            width=100,
            font=(F_TEXTO, 13, "bold"),
            corner_radius=10
        )
        btn_marcar.pack(side="right")

        # Tarjeta de Resultado del Marcaje
        self.card_res = ctk.CTkFrame(col_izq, fg_color=CARD[0], corner_radius=14, border_width=1, border_color=BORDE[0])
        self.card_res.pack(fill="x")

        f_res_inner = ctk.CTkFrame(self.card_res, fg_color="transparent")
        f_res_inner.pack(fill="x", padx=16, pady=14)

        fila_persona = ctk.CTkFrame(f_res_inner, fg_color="transparent")
        fila_persona.pack(fill="x")

        self.avatar = ctk.CTkLabel(
            fila_persona, text="?", width=52, height=52, corner_radius=26,
            fg_color=SUAVE, font=(F_TITULO, 18, "bold"), text_color="white"
        )
        self.avatar.pack(side="left", padx=(0, 14))

        f_textos = ctk.CTkFrame(fila_persona, fg_color="transparent")
        f_textos.pack(side="left", fill="x", expand=True)

        self.l_nombre = ctk.CTkLabel(f_textos, text="Listo para escanear", font=(F_TITULO, 16, "bold"), text_color=TEXTO[0], anchor="w")
        self.l_nombre.pack(fill="x")

        self.l_detalle = ctk.CTkLabel(
            f_textos,
            text="Tome la foto del carnet con la cámara web o use la pistola lectora.",
            font=(F_TEXTO, 12), text_color=SUAVE, anchor="w"
        )
        self.l_detalle.pack(fill="x", pady=(2, 0))

        self.badge_estado = ctk.CTkLabel(
            fila_persona, text="EN ESPERA", font=(F_TEXTO, 11, "bold"),
            fg_color=SUAVE_BG[0], text_color=SUAVE[0], corner_radius=8, width=110, height=30,
            border_width=1, border_color=BORDE[0]
        )
        self.badge_estado.pack(side="right")

        # --- Columna Derecha: Cámara Web con Botón de Captura Fotográfica ---
        col_der = ctk.CTkFrame(f_superior, fg_color=CARD[0], corner_radius=14, border_width=1, border_color=BORDE[0])
        col_der.grid(row=0, column=1, sticky="nsew")

        f_cam_inner = ctk.CTkFrame(col_der, fg_color="transparent")
        f_cam_inner.pack(fill="both", expand=True, padx=14, pady=12)

        # Encabezado del visor
        f_cam_header = ctk.CTkFrame(f_cam_inner, fg_color="transparent")
        f_cam_header.pack(fill="x", pady=(0, 6))

        ctk.CTkLabel(
            f_cam_header, text="📹 Lector de Carnets por Cámara",
            font=(F_TEXTO, 13, "bold"), text_color=TEXTO[0]
        ).pack(side="left")

        self.lbl_cam_status = ctk.CTkLabel(
            f_cam_header, text="🟡 Iniciando...",
            font=(F_TEXTO, 11, "bold"), text_color=ACENTO[0]
        )
        self.lbl_cam_status.pack(side="right")

        # Contenedor del video/foto en vivo
        f_video_box = ctk.CTkFrame(
            f_cam_inner, fg_color="#08082D", corner_radius=10, height=160,
            border_width=1, border_color=ACENTO[0]
        )
        f_video_box.pack(fill="x", pady=(0, 8))
        f_video_box.pack_propagate(False)

        self.lbl_video = ctk.CTkLabel(
            f_video_box, text="Conectando cámara web...",
            font=(F_TEXTO, 12), text_color=SUAVE[0], cursor="hand2"
        )
        self.lbl_video.pack(fill="both", expand=True)
        # Hacer clic sobre el video también toma la foto
        self.lbl_video.bind("<Button-1>", lambda e: self.tomar_foto_y_leer())

        # Botón Principal: TOMAR FOTO Y LEER CÓDIGO
        self.btn_capturar = ctk.CTkButton(
            f_cam_inner,
            text="📸 Tomar Foto y Leer Carnet",
            command=self.tomar_foto_y_leer,
            fg_color=ACENTO[0],
            hover_color=ACENTO_H[0],
            text_color=PRIMARIO[0],
            height=42,
            corner_radius=10,
            font=(F_TEXTO, 13, "bold")
        )
        self.btn_capturar.pack(fill="x", pady=(0, 4))

        # Mensaje de ayuda / resultado del escáner
        self.lbl_cam_feedback = ctk.CTkLabel(
            f_cam_inner,
            text="Apunte el código del carnet hacia la cámara y presione 'Tomar Foto' (o Espacio).",
            font=(F_TEXTO, 10.5), text_color=SUAVE, justify="center", wraplength=330
        )
        self.lbl_cam_feedback.pack(fill="x")

        # 4. Sección Inferior: Tabla de Marcajes de Hoy
        f_tabla = ctk.CTkFrame(cuerpo, fg_color=CARD[0], corner_radius=14, border_width=1, border_color=BORDE[0])
        f_tabla.pack(fill="both", expand=True)

        ctk.CTkLabel(
            f_tabla, text="📋 Marcajes Registrados el Día de Hoy",
            font=(F_TEXTO, 13, "bold"), text_color=TEXTO[0]
        ).pack(anchor="w", padx=16, pady=(10, 6))

        columnas = ("hora", "cedula", "nombre", "tipo", "seccion", "estado")
        estilo = ttk.Style(self)
        estilo.configure(
            "Kiosco.Treeview", background=CARD[0], fieldbackground=CARD[0],
            foreground=TEXTO[0], rowheight=32, borderwidth=0, font=(F_TEXTO, 10)
        )
        estilo.configure(
            "Kiosco.Treeview.Heading", background=CARD[0], foreground=ACENTO[0],
            font=(F_TEXTO, 10, "bold"), relief="flat", padding=(8, 8)
        )
        estilo.map(
            "Kiosco.Treeview", background=[("selected", ACENTO[0])],
            foreground=[("selected", PRIMARIO[0])]
        )
        estilo.map("Kiosco.Treeview.Heading", background=[("active", PRIMARIO_H[0])])
        self.tabla = ttk.Treeview(
            f_tabla, columns=columnas, show="headings", height=7, selectmode="none",
            style="Kiosco.Treeview"
        )
        self.tabla.tag_configure("par", background=SUAVE_BG[0])
        self.tabla.heading("hora", text="Hora")
        self.tabla.heading("cedula", text="Cédula")
        self.tabla.heading("nombre", text="Nombre y Apellido")
        self.tabla.heading("tipo", text="Tipo")
        self.tabla.heading("seccion", text="Grado / Cargo")
        self.tabla.heading("estado", text="Estado")

        self.tabla.column("hora", width=90, anchor="center")
        self.tabla.column("cedula", width=110, anchor="center")
        self.tabla.column("nombre", width=220, anchor="w")
        self.tabla.column("tipo", width=100, anchor="center")
        self.tabla.column("seccion", width=160, anchor="w")
        self.tabla.column("estado", width=120, anchor="center")

        scroll = ttk.Scrollbar(f_tabla, orient="vertical", command=self.tabla.yview)
        self.tabla.configure(yscrollcommand=scroll.set)
        self.tabla.pack(side="left", fill="both", expand=True, padx=(16, 0), pady=(0, 10))
        scroll.pack(side="right", fill="y", padx=(0, 16), pady=(0, 10))

    # ========================== GESTIÓN DE CÁMARA WEB ==========================
    def _iniciar_camara(self):
        """Inicia la cámara web en un hilo secundario para fluidez total."""
        if self.camara_activa:
            return
        self.camara_activa = True
        self.lbl_cam_status.configure(text="Conectando cámara...", text_color=ACENTO[0])
        self.btn_toggle_cam.configure(
            text="📷 Apagar Cámara", fg_color=CARD[0], hover_color=SUAVE[0]
        )

        threading.Thread(target=self._hilo_captura_camara, daemon=True).start()
        self._actualizar_visor_camara()

    def _hilo_captura_camara(self):
        """Hilo continuo para capturar frames nativos de la webcam."""
        try:
            # CAP_DSHOW en Windows acelera el encendido de webcams integradas
            cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            if not cap.isOpened():
                cap = cv2.VideoCapture(0)

            if not cap.isOpened():
                self.after(0, lambda: self.lbl_cam_status.configure(
                    text="Cámara no disponible", text_color="#E6C7D0"
                ))
                self.camara_activa = False
                return

            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.cap = cap

            self.after(0, lambda: self.lbl_cam_status.configure(
                text="Lista para capturar", text_color=ACENTO[0]
            ))

            while self.camara_activa and self.cap and self.cap.isOpened():
                ret, frame = self.cap.read()
                if not ret:
                    time.sleep(0.04)
                    continue

                frame_mirror = cv2.flip(frame, 1)

                with self.frame_lock:
                    self.ultimo_frame_nativo = frame_mirror

                # Auto-escaneo pasivo en segundo plano cada 8 frames si no está congelada la foto
                if not self.foto_congelada:
                    self._contador_frames_auto += 1
                    if self._contador_frames_auto >= 8:
                        self._contador_frames_auto = 0
                        try:
                            cod = None
                            if zxingcpp:
                                res_auto = zxingcpp.read_barcode(frame_mirror, formats=zxingcpp.BarcodeFormat.AllLinear)
                                if res_auto and res_auto.text and res_auto.text.strip():
                                    cod = res_auto.text.strip()
                            if not cod:
                                b_det = cv2.barcode.BarcodeDetector()
                                t, _, _ = b_det.detectAndDecode(frame_mirror)
                                if t and t.strip():
                                    cod = t.strip()
                            if not cod:
                                q_det = cv2.QRCodeDetector()
                                val, _, _ = q_det.detectAndDecode(frame_mirror)
                                if val and val.strip():
                                    cod = val.strip()

                            if cod:
                                ahora = time.time()
                                if (cod != self.ultimo_codigo_leido) or (ahora - self.tiempo_ultimo_escaneo > 3.5):
                                    self.ultimo_codigo_leido = cod
                                    self.tiempo_ultimo_escaneo = ahora
                                    self.after(0, lambda c=cod: self._confirmar_auto_escaneo(c, frame_mirror))
                        except Exception:
                            pass

                time.sleep(0.03)

        except Exception as e:
            print("Aviso captura cámara:", e)
        finally:
            if self.cap:
                try:
                    self.cap.release()
                except Exception:
                    pass
                self.cap = None

    def _actualizar_visor_camara(self):
        """Actualiza el label del visor mientras la foto no esté congelada."""
        if not self.winfo_exists():
            return

        if self.camara_activa and not self.foto_congelada:
            frame = None
            with self.frame_lock:
                if self.ultimo_frame_nativo is not None:
                    frame = self.ultimo_frame_nativo.copy()

            if frame is not None:
                self._mostrar_frame_en_visor(frame)

        self.after(35, self._actualizar_visor_camara)

    def _mostrar_frame_en_visor(self, frame):
        """Dibuja un frame (BGR) redimensionado dentro del CTkLabel del visor."""
        try:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb)
            ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(330, 160))
            self.lbl_video.configure(image=ctk_img, text="")
            self.lbl_video.image = ctk_img
        except Exception:
            pass

    # ========================== CAPTURA Y ANÁLISIS DE FOTO =====================
    def tomar_foto_y_leer(self):
        """Toma la foto del código de carnet, congela la imagen y extrae el número."""
        if not self.camara_activa:
            self._iniciar_camara()
            self.lbl_cam_feedback.configure(
                text="Iniciando cámara... intente nuevamente en 1 segundo.",
                text_color=ACENTO[0]
            )
            return

        with self.frame_lock:
            if self.ultimo_frame_nativo is None:
                self.lbl_cam_feedback.configure(
                    text="Esperando imagen de la cámara web...", text_color=ACENTO[0]
                )
                return
            foto = self.ultimo_frame_nativo.copy()

        # Congelar el visor con la foto capturada
        self.foto_congelada = True
        self.btn_capturar.configure(state="disabled", text="⏳ Analizando foto...")
        self.lbl_cam_status.configure(text="📸 Foto Capturada", text_color=ACENTO[0])
        self.lbl_cam_feedback.configure(
            text="🔍 Analizando imagen del carnet...", text_color=ACENTO[0]
        )

        self._mostrar_frame_en_visor(foto)

        # Analizar en hilo secundario para mantener la interfaz receptiva
        threading.Thread(target=self._hilo_analizar_foto, args=(foto,), daemon=True).start()

    def _hilo_analizar_foto(self, foto):
        """Procesa la foto tomada con el pipeline multinivel de decodificación."""
        try:
            codigo, puntos, metodo = decodificar_imagen_carnet(foto)

            if codigo:
                # Dibujar recuadro verde sobre el código en la foto
                foto_res = foto.copy()
                if puntos is not None:
                    try:
                        if hasattr(puntos, "top_left"):
                            pts = np.array([
                                [puntos.top_left.x, puntos.top_left.y],
                                [puntos.top_right.x, puntos.top_right.y],
                                [puntos.bottom_right.x, puntos.bottom_right.y],
                                [puntos.bottom_left.x, puntos.bottom_left.y]
                            ], dtype=np.int32)
                            cv2.polylines(foto_res, [pts], True, (232, 225, 86), 4)
                        elif isinstance(puntos, (list, tuple, np.ndarray)):
                            pts = np.array(puntos, dtype=np.int32)
                            cv2.polylines(foto_res, [pts], True, (232, 225, 86), 4)
                    except Exception:
                        pass

                self.after(0, lambda: self._mostrar_frame_en_visor(foto_res))
                self.after(0, lambda: self.lbl_cam_status.configure(
                    text="Carnet leído", text_color=ACENTO[0]
                ))
                self.after(0, lambda c=codigo: self.lbl_cam_feedback.configure(
                    text=f"✓ Código extraído con éxito: {c}", text_color=ACENTO[0]
                ))

                # Registrar asistencia
                self.after(0, lambda c=codigo: self.procesar_marcaje(c))

                # Pausa para mostrar la foto confirmada y reanudar video en vivo
                time.sleep(2.2)

            else:
                _beep_alerta()
                self.after(0, lambda: self.lbl_cam_status.configure(
                    text="Código no detectado", text_color="#E6C7D0"
                ))
                self.after(0, lambda: self.lbl_cam_feedback.configure(
                    text="⚠️ No se apreció el código con nitidez. Mantenga firme el carnet y presione 'Tomar Foto' de nuevo.",
                    text_color="#E6C7D0"
                ))
                time.sleep(1.8)

        except Exception as e:
            print("Error analizando foto:", e)
        finally:
            self.foto_congelada = False
            self.after(0, self._restablecer_controles_camara)

    def _confirmar_auto_escaneo(self, codigo, frame):
        """Maneja lecturas cuando el usuario sostiene el carnet firme frente a la cámara."""
        self.lbl_cam_status.configure(text="Carnet detectado", text_color=ACENTO[0])
        self.lbl_cam_feedback.configure(
            text=f"✓ Código detectado: {codigo}", text_color=ACENTO[0]
        )
        self.procesar_marcaje(codigo)

    def _restablecer_controles_camara(self):
        """Restaura el botón y etiquetas para la siguiente captura."""
        self.btn_capturar.configure(state="normal", text="📸 Tomar Foto y Leer Carnet")
        if self.camara_activa:
            self.lbl_cam_status.configure(text="Lista para capturar", text_color=ACENTO[0])
            self.lbl_cam_feedback.configure(
                text="Apunte el código del carnet hacia la cámara y presione 'Tomar Foto' (o Espacio).",
                text_color=SUAVE
            )

    def _detener_camara(self):
        """Detiene la cámara web de forma segura."""
        self.camara_activa = False
        self.foto_congelada = False
        if self.cap:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None
        self.lbl_video.configure(image="", text="📹 Cámara apagada\nHaga clic en 'Encender Cámara'")
        self.lbl_cam_status.configure(text="⚪ Cámara inactiva", text_color=SUAVE)
        self.btn_toggle_cam.configure(
            text="📷 Encender Cámara", fg_color=ACENTO[0], hover_color=ACENTO_H[0],
            text_color=PRIMARIO[0]
        )

    def _toggle_camara(self):
        if self.camara_activa:
            self._detener_camara()
        else:
            self._iniciar_camara()

    def _cerrar_ventana(self):
        self._detener_camara()
        self.destroy()

    # ========================== GESTIÓN DE TECLADO Y ESCÁNER ===================
    def _on_entry_enter(self, event=None):
        self.procesar_marcaje()
        return "break"

    def _on_global_key(self, event):
        """Captura pulsaciones globales: pistola de barras, teclado y tecla Espacio para foto."""
        widget_activo = self.focus_get()
        inner_entry = getattr(self.e_ced, "_entry", None)

        # Si presiona la barra espaciadora y no está escribiendo dentro de la barra de cédula:
        if event.keysym == "space":
            if widget_activo != self.e_ced and widget_activo != inner_entry:
                self.tomar_foto_y_leer()
                return "break"

        # Si el foco ya está en el campo de texto de la cédula, Tkinter ya inserta el carácter nativamente:
        if widget_activo == self.e_ced or widget_activo == inner_entry:
            if event.keysym in ("Return", "KP_Enter"):
                self.procesar_marcaje()
                return "break"
            return

        # Si el foco estaba en otro lugar (la tabla, un botón, etc.) y la pistola lectora o el usuario tipea:
        if event.char and event.char.isprintable() and len(event.char) == 1 and event.char != " ":
            self.e_ced.focus_set()
            self.e_ced.insert("end", event.char)
            return "break"
        elif event.keysym in ("Return", "KP_Enter"):
            self.e_ced.focus_set()
            self.procesar_marcaje()
            return "break"

    def procesar_marcaje(self, cedula_manual=None):
        """Procesa el marcaje recibido de la foto de carnet, de pistola láser o teclado."""
        if cedula_manual is not None:
            cedula_raw = str(cedula_manual).strip()
        else:
            cedula_raw = self.e_ced.get().strip()
            self.e_ced.delete(0, "end")
            self.e_ced.focus_set()

        if not cedula_raw:
            return

        # 1. Sanitizar si vino como URL en código QR
        cedula = cedula_raw
        if "cedula=" in cedula.lower():
            cedula = cedula.split("cedula=")[-1].split("&")[0].strip()
        elif "/" in cedula:
            cedula = cedula.rstrip("/").split("/")[-1].strip()

        # 2. Desduplicación inteligente si vino carácter por carácter duplicado (ej: 3311122233778899 -> 31123789)
        solo_num = "".join(c for c in cedula if c.isdigit())
        if solo_num and len(solo_num) >= 12 and len(solo_num) % 2 == 0:
            if all(solo_num[i] == solo_num[i+1] for i in range(0, len(solo_num), 2)):
                posible_dedup = "".join(solo_num[i] for i in range(0, len(solo_num), 2))
                try:
                    if not self.db.persona_por_cedula(cedula) and self.db.persona_por_cedula(posible_dedup):
                        cedula = posible_dedup
                except Exception:
                    cedula = posible_dedup

        # Limpiar inmediatamente el campo para el siguiente marcaje
        self.e_ced.delete(0, "end")
        self.e_ced.focus_set()

        res = self.db.procesar_marcaje(cedula)

        if res.get("ok"):
            _beep_exito()
            p_nombre = res["persona"]
            ini = "".join(x[:1] for x in p_nombre.split()[:2]).upper()
            self.avatar.configure(text=ini, fg_color=PRIMARIO[0])
            self.l_nombre.configure(text=p_nombre)
            self.l_detalle.configure(text=f"{res['tipo_persona']} · {res['detalle']} · C.I. {res['cedula']}")

            color_badge = SUAVE_BG[0] if res["estado"] == "Presente" else "#24151C"
            color_txt = ACENTO[0] if res["estado"] == "Presente" else "#E6C7D0"

            self.badge_estado.configure(
                text=f"{res['tipo']} · {res['estado']}",
                fg_color=color_badge,
                text_color=color_txt
            )
            self.card_res.configure(border_color=ACENTO[0])
            self.lbl_cam_feedback.configure(
                text=f"✓ {res['tipo']} registrado · {p_nombre}",
                text_color=ACENTO[0]
            )
            self.after(1800, lambda: self.card_res.configure(border_color=BORDE[0]))
            self.cargar_feed_hoy()

        elif res.get("duplicado"):
            _beep_alerta()
            self.avatar.configure(text="ℹ", fg_color=AVISO[0])
            p_nom = res.get("persona") or "Persona"
            self.l_nombre.configure(text=p_nom)
            self.l_detalle.configure(text=res.get("mensaje", "Marcaje duplicado detectado para esta fecha y turno."))
            self.badge_estado.configure(text="YA REGISTRADO", fg_color="#24151C", text_color="#E6C7D0")
            self.card_res.configure(border_color=AVISO[0])
            self.lbl_cam_feedback.configure(text="ℹ " + res.get("mensaje", "Marcaje duplicado"), text_color="#E6C7D0")
            self.cargar_feed_hoy()

        elif res.get("ya_completado"):
            _beep_alerta()
            self.avatar.configure(text="✓", fg_color=AVISO[0])
            self.l_nombre.configure(text=res["persona"])
            self.l_detalle.configure(text="Esta persona ya completó tanto su entrada como su salida de hoy.")
            self.badge_estado.configure(text="JORNADA LISTA", fg_color="#24151C", text_color="#E6C7D0")
            self.card_res.configure(border_color=AVISO[0])
            self.lbl_cam_feedback.configure(text="⚠ La jornada de hoy ya está completa", text_color="#E6C7D0")
            self.cargar_feed_hoy()

        else:
            _beep_alerta()
            self.avatar.configure(text="?", fg_color=AVISO[0])
            self.l_nombre.configure(text=f"Cédula {cedula} no encontrada")
            self.l_detalle.configure(text="El carnet no se encuentra registrado en el sistema escolar.")
            self.badge_estado.configure(text="NO REGISTRADO", fg_color="#24151C", text_color="#E6C7D0")
            self.card_res.configure(border_color=AVISO[0])
            self.lbl_cam_feedback.configure(text="✕ Carnet no reconocido", text_color="#E6C7D0")

    def _actualizar_reloj(self):
        ahora = datetime.now()
        self.l_reloj.configure(text=ahora.strftime("%A, %d de %B de %Y - %I:%M:%S %p").capitalize())
        h = ahora.time()
        turno = "Tarde" if h >= config.HORARIOS_TURNO["Tarde"]["entrada_limite"] else "Mañana"
        self.l_turno.configure(text=f"Turno Activo: {turno}")
        self.after(1000, self._actualizar_reloj)

    def cargar_feed_hoy(self):
        def _fmt_12h(v):
            if v is None:
                return "--:--"
            from datetime import timedelta, time, datetime
            if isinstance(v, timedelta):
                total_sec = int(v.total_seconds())
                h = (total_sec // 3600) % 24
                m = (total_sec % 3600) // 60
                ampm = "AM" if h < 12 else "PM"
                h12 = h % 12 or 12
                return f"{h12:02d}:{m:02d} {ampm}"
            elif isinstance(v, (time, datetime)):
                return v.strftime("%I:%M %p")
            return str(v)[:8]

        for item in self.tabla.get_children():
            self.tabla.delete(item)
        try:
            filas = self.db.registros_hoy(limite=35)
            for r in filas:
                h_txt = _fmt_12h(r.get("hora_entrada"))
                nombre_comp = f"{r.get('nombre', '')} {r.get('apellido', '')}".strip()
                self.tabla.insert("", "end", values=(
                    h_txt,
                    r.get("cedula", "") or "—",
                    nombre_comp or "—",
                    r.get("tipo_persona", "") or "—",
                    r.get("detalle", "") or "—",
                    r.get("estado", "") or "Presente"
                ), tags=("par",) if len(self.tabla.get_children()) % 2 else ())
        except Exception as e:
            print("Error cargando feed de hoy:", e)

    def _abrir_qr(self):
        DialogoQRMovil(self)
