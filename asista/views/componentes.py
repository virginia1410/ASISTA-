"""Componentes visuales reutilizables de Asista (Banner, Calendario, Diálogos y Portal Móvil)."""
import calendar
from datetime import date, datetime
import os
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from PIL import Image, ImageTk

from config import MESES
from tema import (
    ACENTO, ACENTO_H, ACENTO_TEXTO, BORDE, BG, CARD, F_TEXTO, F_TITULO, PRIMARIO,
    SUAVE, SUAVE_BG, TEXTO, banner_imagen, colores_modo, logo_institucion
)
from .ui_utils import boton, campo, tarjeta, etiqueta, combo


class Banner(tk.Canvas):
    """Cabecera institucional con degradado Navy Blue, destellos y marca de agua del logo."""
    def __init__(self, master, alto=140):
        super().__init__(master, height=alto, highlightthickness=0, bd=0)
        self.alto = alto
        self._ancho = 0
        self.foto = None
        self.escudo_tk = None
        self.textos = ("", "", "")
        escudo = logo_institucion(alto=104, ancho_max=84)
        if escudo:
            self.escudo_tk = ImageTk.PhotoImage(escudo)
        self.bind("<Configure>", self._config)
        self.actualizar_tema()

    def actualizar_tema(self):
        oscuro = ctk.get_appearance_mode() == "Dark"
        self.configure(bg=colores_modo("bg", oscuro))
        self._dibujar()

    def poner(self, kicker, titulo, sub):
        self.textos = (kicker, titulo, sub)
        self._dibujar()

    def _config(self, e):
        if e.width != self._ancho:
            self._ancho = e.width
            self._dibujar()

    def _dibujar(self):
        w = self.winfo_width()
        if w < 50:
            return
        self.delete("all")
        oscuro = ctk.get_appearance_mode() == "Dark"
        self.foto = ImageTk.PhotoImage(banner_imagen(w, self.alto, oscuro=oscuro))
        self.create_image(0, 0, image=self.foto, anchor="nw")
        k, t, s = self.textos
        acento_col = colores_modo("accent", oscuro)
        self.create_text(38, 32, text=k, anchor="w", fill=colores_modo("accent_text", oscuro),
                         font=(F_TEXTO, 10, "bold"))
        self.create_rectangle(38, 46, 86, 49, fill=acento_col, width=0)
        self.create_text(38, 82, text=t, anchor="w", fill=colores_modo("text", oscuro),
                         font=(F_TITULO, 27, "bold"))
        self.create_text(38, 116, text=s, anchor="w", fill=colores_modo("muted", oscuro),
                         font=(F_TEXTO, 12))
        if self.escudo_tk:
            x = max(0, w - 112)
            self.create_rectangle(
                x, 14, w - 16, 126,
                fill=colores_modo("card", oscuro),
                outline=colores_modo("border", oscuro),
                width=1
            )
            self.create_image((x + w - 16) // 2, 70, image=self.escudo_tk)


# Alias de compatibilidad
Cabecera = Banner


class Calendario(ctk.CTkFrame):
    """Calendario mensual compacto para el panel de inicio / dashboard."""
    def __init__(self, master):
        super().__init__(master, fg_color=CARD, corner_radius=20, border_width=1, border_color=BORDE)
        self.cab = ctk.CTkLabel(self, font=(F_TITULO, 17, "bold"), text_color=TEXTO)
        self.cab.pack(pady=(16, 6))
        self.rejilla = ctk.CTkFrame(self, fg_color="transparent")
        self.rejilla.pack(padx=14, pady=(0, 16))
        self.dibujar()

    def dibujar(self):
        for w in self.rejilla.winfo_children():
            w.destroy()
        hoy = date.today()
        self.cab.configure(text=f"{MESES[hoy.month - 1]} {hoy.year}")
        for c, l in enumerate("LMXJVSD"):
            ctk.CTkLabel(self.rejilla, text=l, width=34, height=22, font=(F_TEXTO, 11, "bold"),
                         text_color=SUAVE).grid(row=0, column=c)
        for r, sem in enumerate(calendar.monthcalendar(hoy.year, hoy.month), start=1):
            for c, d in enumerate(sem):
                if d:
                    es = d == hoy.day
                    color_txt = PRIMARIO if es else SUAVE if c >= 5 else TEXTO
                    color_bg = ACENTO if es else SUAVE_BG if c == 6 or c == 5 else "transparent"
                    ctk.CTkLabel(self.rejilla, text=str(d), width=34, height=30, corner_radius=15,
                                 font=(F_TEXTO, 12, "bold" if es else "normal"),
                                 fg_color=color_bg,
                                 text_color=color_txt).grid(
                        row=r, column=c, pady=1)


class DialogoSelectorFecha(ctk.CTkToplevel):
    """Diálogo modal interactivo para selección visual de fecha (Día, Mes, Año)."""
    def __init__(self, master, fecha_inicial=None, al_seleccionar=None):
        super().__init__(master, fg_color=BG)
        self.al_seleccionar = al_seleccionar
        self.fecha_actual = fecha_inicial or date.today()

        self.title("Seleccionar Fecha")
        self.geometry("380x420")
        self.resizable(False, False)
        self.transient(master.winfo_toplevel())
        self.after(150, self.grab_set)

        self.meses_nombres = [
            "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
            "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
        ]

        self._crear_interfaz()

    def _crear_interfaz(self):
        head = ctk.CTkFrame(self, fg_color="transparent")
        head.pack(fill="x", padx=24, pady=(18, 10))

        ctk.CTkLabel(head, text="📅 Seleccionar Fecha", font=(F_TITULO, 18, "bold"), text_color=TEXTO).pack(side="left")

        # Selectores Mes y Año
        f_nav = ctk.CTkFrame(self, fg_color="transparent")
        f_nav.pack(fill="x", padx=24, pady=(0, 10))

        self.cb_mes = ctk.CTkComboBox(
            f_nav, values=self.meses_nombres, width=150, height=36,
            command=lambda v: self._actualizar_calendario()
        )
        self.cb_mes.pack(side="left", padx=(0, 8))
        self.cb_mes.set(self.meses_nombres[self.fecha_actual.month - 1])

        anios = [str(a) for a in range(2020, 2035)]
        self.cb_anio = ctk.CTkComboBox(
            f_nav, values=anios, width=100, height=36,
            command=lambda v: self._actualizar_calendario()
        )
        self.cb_anio.pack(side="left")
        self.cb_anio.set(str(self.fecha_actual.year))

        # Rejilla de días
        self.f_dias = tarjeta(self)
        self.f_dias.pack(fill="both", expand=True, padx=24, pady=(0, 14))

        # Botón Hoy y Cerrar
        f_pie = ctk.CTkFrame(self, fg_color="transparent")
        f_pie.pack(fill="x", padx=24, pady=(0, 18))

        boton(f_pie, "Hoy", "suave", self._seleccionar_hoy, width=90, height=38).pack(side="left")
        boton(f_pie, "Cancelar", "suave", self.destroy, width=90, height=38).pack(side="right")

        self._actualizar_calendario()

    def _actualizar_calendario(self):
        for w in self.f_dias.winfo_children():
            w.destroy()

        mes_idx = self.meses_nombres.index(self.cb_mes.get()) + 1
        anio = int(self.cb_anio.get())

        dias_semana = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
        for col, dia_nom in enumerate(dias_semana):
            ctk.CTkLabel(self.f_dias, text=dia_nom, font=(F_TEXTO, 11, "bold"), text_color=SUAVE).grid(
                row=0, column=col, padx=4, pady=4, sticky="nsew"
            )

        cal = calendar.monthcalendar(anio, mes_idx)
        for fila, semana in enumerate(cal):
            for col, dia in enumerate(semana):
                if dia == 0:
                    continue
                es_hoy = (dia == date.today().day and mes_idx == date.today().month and anio == date.today().year)
                es_sel = (dia == self.fecha_actual.day and mes_idx == self.fecha_actual.month and anio == self.fecha_actual.year)

                color_btn = ACENTO if es_sel else (SUAVE_BG if es_hoy else "transparent")
                color_txt = PRIMARIO if es_sel else TEXTO

                b = ctk.CTkButton(
                    self.f_dias, text=str(dia), width=34, height=34, corner_radius=17,
                    fg_color=color_btn, text_color=color_txt,
                    hover_color=ACENTO_H, font=(F_TEXTO, 11, "bold" if (es_hoy or es_sel) else "normal"),
                    command=lambda d=dia: self._elegir(d, mes_idx, anio)
                )
                b.grid(row=fila + 1, column=col, padx=3, pady=3)

    def _elegir(self, dia, mes, anio):
        self.fecha_actual = date(anio, mes, dia)
        if self.al_seleccionar:
            self.al_seleccionar(self.fecha_actual)
        self.destroy()

    def _seleccionar_hoy(self):
        self._elegir(date.today().day, date.today().month, date.today().year)


def asociar_boton_calendario(parent, entry, callback=None):
    """Crea un botón con icono 📅 que abre DialogoSelectorFecha y actualiza el campo de entrada."""
    def _abrir():
        val = entry.get().strip() if hasattr(entry, "get") else ""
        f_init = None
        if val:
            try:
                f_init = datetime.strptime(val, "%Y-%m-%d").date()
            except Exception:
                pass

        def _on_select(f_sel):
            if hasattr(entry, "delete") and hasattr(entry, "insert"):
                entry.delete(0, "end")
                entry.insert(0, f_sel.isoformat())
            if callback:
                callback(f_sel)

        DialogoSelectorFecha(entry.winfo_toplevel(), fecha_inicial=f_init, al_seleccionar=_on_select)

    b = ctk.CTkButton(
        parent, text="📅", width=36, height=36, corner_radius=10,
        fg_color="transparent", hover_color=BORDE, text_color=TEXTO,
        font=(F_TEXTO, 14), command=_abrir
    )
    return b


class DialogoQRMovil(ctk.CTkToplevel):
    """Ventana de acceso QR a la estación móvil de escaneo."""

    def __init__(self, master):
        super().__init__(master, fg_color=BG)
        self.title("Asista · Estación Móvil de Escaneo")
        self.geometry("470x690")
        self.resizable(False, False)
        self.transient(master.winfo_toplevel())
        self.after(150, self.grab_set)

        try:
            import servicio_asista
            self._servicio = servicio_asista
            self.ips = [
                ip for ip in servicio_asista.listar_ips_locales()
                if not ip.startswith(("127.", "169.254."))
            ]
        except ImportError as exc:
            self._servicio = None
            self.ips = []
            self._error_servicio = str(exc)
        else:
            self._error_servicio = ""
        self.ip = self.ips[0] if self.ips else None

        cabecera = ctk.CTkFrame(
            self, fg_color=CARD, border_width=1, border_color=BORDE, corner_radius=14
        )
        cabecera.pack(fill="x", padx=24, pady=(18, 12))

        escudo = logo_institucion(alto=54, ancho_max=54)
        if escudo:
            self._logo_tk = ctk.CTkImage(light_image=escudo, size=escudo.size)
            ctk.CTkLabel(cabecera, text="", image=self._logo_tk).pack(side="left", padx=(12, 10), pady=8)

        marca = ctk.CTkFrame(cabecera, fg_color="transparent")
        marca.pack(side="left", fill="x", expand=True, pady=10)
        ctk.CTkLabel(
            marca, text="ASISTA", font=(F_TITULO, 19, "bold"), text_color=TEXTO, anchor="w"
        ).pack(fill="x")
        ctk.CTkLabel(
            marca, text="ESTACIÓN MÓVIL DE ESCANEO", font=(F_TEXTO, 10, "bold"),
            text_color=ACENTO_TEXTO, anchor="w"
        ).pack(fill="x", pady=(2, 0))

        ctk.CTkLabel(
            self, text="Escanea el QR con el teléfono para abrir la cámara en vivo.",
            font=(F_TEXTO, 11), text_color=SUAVE, justify="center"
        ).pack(pady=(0, 8), padx=20)

        # Selector de Red / IP si hay varias
        if len(self.ips) > 1:
            f_ip = ctk.CTkFrame(self, fg_color="transparent")
            f_ip.pack(fill="x", padx=32, pady=(0, 8))
            ctk.CTkLabel(
                f_ip, text="IP de red", font=(F_TEXTO, 11, "bold"), text_color=TEXTO
            ).pack(side="left", padx=(0, 10))
            self.cb_ip = combo(f_ip, values=self.ips, command=self._cambiar_ip, width=230, height=32)
            self.cb_ip.set(self.ip)
            self.cb_ip.pack(side="left")

        self.f_qr = ctk.CTkFrame(
            self, fg_color=CARD, border_width=1, border_color=BORDE, corner_radius=18
        )
        self.f_qr.pack(pady=(0, 10), padx=24)

        self.lbl_qr = ctk.CTkLabel(self.f_qr, text="")
        self.lbl_qr.pack()

        f_url = ctk.CTkFrame(
            self, fg_color=CARD, border_width=1, border_color=BORDE, corner_radius=12
        )
        f_url.pack(fill="x", padx=24, pady=(0, 8))
        ctk.CTkLabel(
            f_url, text="Enlace del escáner · protocolo y puerto activos",
            font=(F_TEXTO, 10, "bold"), text_color=TEXTO
        ).pack(pady=(6, 0))
        self.lbl_url = ctk.CTkLabel(
            f_url, text="", font=(F_TEXTO, 12, "bold"), text_color=ACENTO_TEXTO,
            wraplength=400, justify="center"
        )
        self.lbl_url.pack(padx=8, pady=(2, 6))

        btn_box = ctk.CTkFrame(self, fg_color="transparent")
        btn_box.pack(fill="x", padx=24, pady=(0, 8))

        def _copiar():
            self.clipboard_clear()
            self.clipboard_append(self.url_actual)
            self.btn_copiar.configure(text="✓ ¡Copiado!")
            self.after(2000, lambda: self.btn_copiar.configure(text="Copiar Enlace"))

        self.btn_copiar = ctk.CTkButton(
            btn_box, text="Copiar URL", command=_copiar,
            fg_color=ACENTO, hover_color=ACENTO_H, text_color=PRIMARIO,
            height=36, corner_radius=10, font=(F_TEXTO, 11, "bold")
        )
        self.btn_copiar.pack(fill="x")

        self.f_aviso = ctk.CTkFrame(
            self, fg_color=CARD, border_width=1, border_color=BORDE, corner_radius=10
        )
        self.f_aviso.pack(fill="x", padx=24, pady=(0, 12))
        self.lbl_aviso = ctk.CTkLabel(
            self.f_aviso,
            text="Cámara en vivo por HTTPS · puerto 8443\nSi el navegador advierte sobre el certificado local, confirma el acceso seguro para continuar.",
            font=(F_TEXTO, 10), text_color=SUAVE, justify="center"
        )
        self.lbl_aviso.pack(padx=12, pady=8)

        self._actualizar_qr()

    def _cambiar_ip(self, nueva_ip):
        self.ip = nueva_ip
        self._actualizar_qr()

    def _actualizar_qr(self):
        self.url_actual = (
            self._servicio.obtener_url_movil(self.ip, "/")
            if self._servicio and self.ip else None
        )
        self.btn_copiar.configure(state="normal" if self.url_actual else "disabled")
        if not self.url_actual:
            self._img_tk = None
            if not self.ips:
                aviso = self._error_servicio or "No se detectó una dirección IPv4 activa de la red local."
                self.lbl_url.configure(text="No hay una IPv4 de red disponible.")
                self.lbl_qr.configure(
                    text="Conecta esta laptop a la red Wi-Fi y vuelve a abrir el acceso móvil.",
                    image=None
                )
                self.lbl_aviso.configure(text=aviso)
            else:
                self.lbl_url.configure(text="El servicio móvil todavía no está disponible.")
                self.lbl_qr.configure(text="Inicia ASISTA y vuelve a abrir esta ventana.", image=None)
                self.lbl_aviso.configure(
                    text="No se detectó un listener ASISTA activo en los puertos HTTP/HTTPS configurados."
                )
            return

        es_https = self.url_actual.startswith("https://")
        self.lbl_url.configure(text=self.url_actual)
        self.lbl_aviso.configure(
            text=(
                "La cámara requiere HTTPS. El certificado local es autofirmado; "
                "el teléfono puede pedir que se confíe en él antes de permitir la cámara."
                if es_https else
                "Este enlace HTTP abre el portal, pero no permite cámara en vivo. "
                "Libera el puerto HTTPS 8443 y reinicia ASISTA para activar el escaneo."
            )
        )

        # Regenerar QR
        self.lbl_qr.configure(text="", image=None)
        try:
            import qrcode
            qr_img = qrcode.make(self.url_actual).convert("RGBA")
            qr_img = qr_img.resize((190, 190), Image.Resampling.LANCZOS)
            self._img_tk = ctk.CTkImage(light_image=qr_img, size=(190, 190))
            self.lbl_qr.configure(text="", image=self._img_tk)
        except Exception as e:
            self.lbl_qr.configure(text=f"Código QR no disponible: {e}")
