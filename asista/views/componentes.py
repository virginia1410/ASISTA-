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
    ACENTO, BORDE, BG, CARD, F_TEXTO, F_TITULO, OK, PRIMARIO, PRIMARIO_H,
    SUAVE, TEXTO, banner_imagen, logo_check, logo_institucion
)
from .ui_utils import boton, campo, tarjeta, etiqueta, segmentado, combo


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
        bg_col = BG[1 if ctk.get_appearance_mode() == "Dark" else 0] if isinstance(BG, tuple) else BG
        self.configure(bg=bg_col)

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
        self.foto = ImageTk.PhotoImage(banner_imagen(w, self.alto))
        self.create_image(0, 0, image=self.foto, anchor="nw")
        k, t, s = self.textos
        acento_col = ACENTO[0] if isinstance(ACENTO, tuple) else ACENTO
        self.create_text(38, 32, text=k, anchor="w", fill="#A5F3FC", font=(F_TEXTO, 10, "bold"))
        self.create_rectangle(38, 46, 86, 49, fill=acento_col, width=0)
        self.create_text(38, 82, text=t, anchor="w", fill="white", font=(F_TITULO, 27, "bold"))
        self.create_text(38, 116, text=s, anchor="w", fill="#E0F2FE", font=(F_TEXTO, 12))
        if self.escudo_tk:
            x = max(0, w - 112)
            self.create_rectangle(x, 14, w - 16, 126, fill="white", outline="#D9E2EC", width=1)
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
                    color_txt = "white" if es else (SUAVE[0] if isinstance(SUAVE, tuple) else SUAVE if c >= 5 else (TEXTO[0] if isinstance(TEXTO, tuple) else TEXTO))
                    color_bg = PRIMARIO if es else "transparent"
                    ctk.CTkLabel(self.rejilla, text=str(d), width=34, height=30, corner_radius=15,
                                 font=(F_TEXTO, 12, "bold" if es else "normal"),
                                 fg_color=color_bg,
                                 text_color=color_txt).grid(
                        row=r, column=c, pady=1)


class DialogoSelectorFecha(ctk.CTkToplevel):
    """Diálogo modal interactivo para selección visual de fecha (Día, Mes, Año)."""
    def __init__(self, master, fecha_inicial=None, al_seleccionar=None):
        super().__init__(master, fg_color=BG[0] if isinstance(BG, tuple) else BG)
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

                color_btn = PRIMARIO if es_sel else ("#E2E8F0" if es_hoy else "transparent")
                color_txt = "white" if es_sel else TEXTO

                b = ctk.CTkButton(
                    self.f_dias, text=str(dia), width=34, height=34, corner_radius=17,
                    fg_color=color_btn, text_color=color_txt,
                    hover_color=PRIMARIO_H, font=(F_TEXTO, 11, "bold" if (es_hoy or es_sel) else "normal"),
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
    """Ventana modal del portal móvil con soporte de código QR dinámico y Escáner en tiempo real."""

    def __init__(self, master, puerto=8080):
        super().__init__(master, fg_color=BG[0] if isinstance(BG, tuple) else BG)
        self.title("Asista · Portal Móvil para Celular")
        self.geometry("490x750")
        self.resizable(False, False)
        self.transient(master.winfo_toplevel())
        self.after(150, self.grab_set)

        try:
            from servicio_asista import obtener_ip_local, listar_ips_locales
            self.ips = listar_ips_locales()
            self.ip = self.ips[0]
        except Exception:
            self.ips = ["127.0.0.1"]
            self.ip = "127.0.0.1"
        self.puerto = puerto

        color_prim = PRIMARIO[0] if isinstance(PRIMARIO, tuple) else PRIMARIO
        color_prim_h = PRIMARIO_H[0] if isinstance(PRIMARIO_H, tuple) else PRIMARIO_H
        color_card = CARD[0] if isinstance(CARD, tuple) else CARD
        color_borde = BORDE[0] if isinstance(BORDE, tuple) else BORDE
        color_texto = TEXTO[0] if isinstance(TEXTO, tuple) else TEXTO

        ctk.CTkLabel(
            self, text="📱 Portal Móvil para Celular", font=(F_TITULO, 22, "bold"), text_color=color_texto
        ).pack(pady=(14, 2))

        ctk.CTkLabel(
            self,
            text="Escanea el código QR con tu celular para abrir el portal\ny activar el escaneo de carnets en tiempo real.",
            font=(F_TEXTO, 11), text_color=SUAVE, justify="center"
        ).pack(pady=(0, 6), padx=20)

        # Selector de Red / IP si hay varias
        if len(self.ips) > 1:
            f_ip = ctk.CTkFrame(self, fg_color="transparent")
            f_ip.pack(fill="x", padx=30, pady=(0, 6))
            ctk.CTkLabel(f_ip, text="Red / IP:", font=(F_TEXTO, 11, "bold"), text_color=color_texto).pack(side="left", padx=(0, 6))
            self.cb_ip = combo(f_ip, values=self.ips, command=self._cambiar_ip, width=170, height=28)
            self.cb_ip.set(self.ip)
            self.cb_ip.pack(side="left")

        # Selector de Modo: Docentes vs Portería
        self.seg_modo = segmentado(
            self,
            values=["👨‍🏫 Portal Docente (Cursos)", "🏛️ Portería General"],
            command=self._cambiar_modo,
            height=32,
            font=(F_TEXTO, 11, "bold")
        )
        self.seg_modo.pack(fill="x", padx=30, pady=(0, 6))
        self.seg_modo.set("👨‍🏫 Portal Docente (Cursos)")

        # Selector de Protocolo: HTTPS (Cámara en Vivo) vs HTTP (Directo)
        self.seg_proto = segmentado(
            self,
            values=["📷 Cámara en Vivo (HTTPS :8443)", "🌐 Acceso Directo (HTTP :8080)"],
            command=self._cambiar_modo,
            height=32,
            font=(F_TEXTO, 11, "bold")
        )
        self.seg_proto.pack(fill="x", padx=30, pady=(0, 8))
        self.seg_proto.set("📷 Cámara en Vivo (HTTPS :8443)")

        # Contenedor del QR
        self.f_qr = ctk.CTkFrame(self, fg_color="transparent")
        self.f_qr.pack(pady=(0, 6))

        self.lbl_qr = ctk.CTkLabel(self.f_qr, text="")
        self.lbl_qr.pack()

        # Enlace directo
        f_url = ctk.CTkFrame(self, fg_color=color_card, border_width=1, border_color=color_borde, corner_radius=10)
        f_url.pack(fill="x", padx=30, pady=(0, 8))
        self.lbl_url = ctk.CTkLabel(f_url, text="", font=(F_TEXTO, 12, "bold"), text_color=color_prim)
        self.lbl_url.pack(pady=6)

        # Botón para abrir en PC, copiar enlace o escanear en laptop
        btn_box = ctk.CTkFrame(self, fg_color="transparent")
        btn_box.pack(fill="x", padx=30, pady=(0, 6))

        def _abrir_nav():
            import webbrowser
            webbrowser.open(self.url_actual)

        def _copiar():
            self.clipboard_clear()
            self.clipboard_append(self.url_actual)
            self.btn_copiar.configure(text="✓ ¡Copiado!")
            self.after(2000, lambda: self.btn_copiar.configure(text="Copiar Enlace"))

        ctk.CTkButton(
            btn_box, text="🌐 Abrir en PC", command=_abrir_nav,
            fg_color=color_prim, hover_color=color_prim_h, height=32, corner_radius=10, font=(F_TEXTO, 11, "bold")
        ).pack(side="left", expand=True, fill="x", padx=(0, 4))

        self.btn_copiar = ctk.CTkButton(
            btn_box, text="Copiar Enlace", command=_copiar,
            fg_color="#F3F4F6", hover_color="#E5E7EB", text_color=color_texto, height=32, corner_radius=10, font=(F_TEXTO, 11, "bold")
        )
        self.btn_copiar.pack(side="left", expand=True, fill="x", padx=(4, 4))

        ctk.CTkButton(
            btn_box, text="💻 Cámara Laptop", command=self._iniciar_escaner_pc,
            fg_color="#0F766E", hover_color="#0D9488", text_color="white", height=32, corner_radius=10, font=(F_TEXTO, 11, "bold")
        ).pack(side="right", expand=True, fill="x", padx=(4, 0))

        # Aviso de uso para cámara en vivo
        self.f_aviso = ctk.CTkFrame(self, fg_color="#F0F9FF", border_width=1, border_color="#BAE6FD", corner_radius=8)
        self.f_aviso.pack(fill="x", padx=25, pady=(0, 8))
        self.lbl_aviso = ctk.CTkLabel(
            self.f_aviso,
            text="⚡ Escaneo en Tiempo Real en Celular:\nAl abrir en el celular, si dice 'La conexión no es privada',\npulsa en 'Configuración avanzada' y luego 'Acceder a... (no seguro)'.\n¡Esto activa la cámara nativa en vivo y el escaneo automático!",
            font=(F_TEXTO, 10), text_color="#0369A1", justify="center"
        )
        self.lbl_aviso.pack(padx=10, pady=6)

        self._cambiar_modo()

    def _cambiar_ip(self, nueva_ip):
        self.ip = nueva_ip
        self._cambiar_modo()

    def _cambiar_modo(self, _v=None):
        modo = self.seg_modo.get()
        proto = self.seg_proto.get()
        ruta = "/profesor" if "Docente" in modo else "/"

        if "HTTPS" in proto:
            self.url_actual = f"https://{self.ip}:8443{ruta}"
            self.lbl_aviso.configure(
                text="⚡ Escaneo en Tiempo Real en Celular:\nAl abrir en el celular, si dice 'La conexión no es privada',\npulsa en 'Configuración avanzada' y luego 'Acceder a... (no seguro)'.\n¡Esto activa la cámara nativa en vivo y el escaneo automático!"
            )
        else:
            self.url_actual = f"http://{self.ip}:{self.puerto}{ruta}"
            self.lbl_aviso.configure(
                text="🌐 Modo Directo HTTP:\nCarga inmediata sin certificados.\nPara activar la cámara de video en vivo se recomienda el modo HTTPS arriba."
            )

        self.lbl_url.configure(text=self.url_actual)

        # Regenerar QR
        try:
            import qrcode
            qr_img = qrcode.make(self.url_actual).convert("RGBA")
            qr_img = qr_img.resize((190, 190), Image.Resampling.LANCZOS)
            self._img_tk = ctk.CTkImage(light_image=qr_img, size=(190, 190))
            self.lbl_qr.configure(image=self._img_tk)
        except Exception as e:
            self.lbl_qr.configure(text=f"Código QR no disponible: {e}")

    def _iniciar_escaner_pc(self):
        """Lanza el escáner de webcam de la laptop."""
        try:
            from .mobile_scanner import lanzar_escanner
            def _on_success(codigo):
                import json, urllib.request
                try:
                    payload = json.dumps({"cedula": codigo}).encode("utf-8")
                    req = urllib.request.Request(
                        f"http://127.0.0.1:{self.puerto}/api/marcar",
                        data=payload,
                        headers={"Content-Type": "application/json"},
                        method="POST"
                    )
                    with urllib.request.urlopen(req, timeout=5) as resp:
                        data = json.load(resp)
                        msg = data.get("mensaje", "")
                        nom = data.get("persona") or data.get("nombre", "")
                        messagebox.showinfo("Marcaje Exitoso", f"Cédula: {codigo}\n{nom}\n{msg}")
                except Exception as ex:
                    messagebox.showerror("Error", f"No se pudo registrar: {ex}")
            lanzar_escanner(self, _on_success)
        except Exception as err:
            messagebox.showwarning("Aviso", f"No se pudo iniciar la cámara de la laptop: {err}")
