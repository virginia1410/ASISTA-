"""Captura y almacenamiento de fotografías de perfil para fichas y carnets."""
import os
import re
from tkinter import messagebox

import customtkinter as ctk
from PIL import Image, ImageOps

from config import BASE_DIR


DIR_FOTOS = BASE_DIR / "fotos_perfil"
TAMANO_FOTO = (480, 640)


def procesar_y_guardar_foto(imagen, cedula):
    """Normaliza una imagen a retrato y la guarda asociada a la cédula."""
    if not isinstance(imagen, Image.Image):
        raise TypeError("La foto debe ser una imagen válida.")

    identificador = re.sub(r"[^A-Za-z0-9_-]", "", str(cedula))
    if not identificador:
        raise ValueError("No se pudo determinar el identificador de la persona.")

    DIR_FOTOS.mkdir(parents=True, exist_ok=True)
    nombre = f"{identificador}.jpg"
    destino = DIR_FOTOS / nombre
    temporal = destino.with_name(f"{destino.stem}.tmp")
    foto = ImageOps.exif_transpose(imagen).convert("RGB")
    foto = ImageOps.fit(foto, TAMANO_FOTO, method=Image.Resampling.LANCZOS)
    foto.save(temporal, format="JPEG", quality=88, optimize=True)
    temporal.replace(destino)
    return nombre


class DialogoCapturaCamara(ctk.CTkToplevel):
    """Permite tomar una foto de perfil con la cámara local del equipo."""

    def __init__(self, master, al_capturar):
        super().__init__(master)
        self.title("Capturar foto de perfil")
        self.geometry("560x500")
        self.resizable(False, False)
        self.transient(master.winfo_toplevel())
        self.al_capturar = al_capturar
        self._cv2 = None
        self._camara = None
        self._imagen_actual = None
        self._imagen_preview = None
        self._trabajo = None

        try:
            import cv2
        except ImportError:
            messagebox.showerror(
                "Cámara no disponible",
                "Falta OpenCV. Instale las dependencias de Asista para habilitar "
                "la captura de fotos.",
                parent=master,
            )
            self.destroy()
            return

        self._cv2 = cv2
        backend = cv2.CAP_DSHOW if os.name == "nt" else cv2.CAP_ANY
        self._camara = cv2.VideoCapture(0, backend)
        if not self._camara.isOpened():
            self._camara.release()
            self._camara = None
            messagebox.showerror(
                "Cámara no disponible",
                "No se pudo abrir la cámara. Verifique que esté conectada y que "
                "Asista tenga permiso para usarla.",
                parent=master,
            )
            self.destroy()
            return

        self.configure(fg_color="#F0F4F8")
        ctk.CTkLabel(
            self,
            text="Foto para el carnet",
            font=("Segoe UI", 19, "bold"),
            text_color="#0F2042",
        ).pack(pady=(18, 4))
        ctk.CTkLabel(
            self,
            text="Centre el rostro y tome la foto cuando la vista previa esté lista.",
            font=("Segoe UI", 12),
            text_color="#627D98",
        ).pack(pady=(0, 12))

        self.vista = ctk.CTkLabel(
            self,
            text="Iniciando cámara…",
            width=400,
            height=300,
            fg_color="#0A1428",
            corner_radius=12,
        )
        self.vista.pack(padx=24, fill="both", expand=True)
        ctk.CTkButton(
            self,
            text="Tomar foto",
            command=self.capturar,
            height=42,
            fg_color="#0F2042",
            hover_color="#1A3668",
        ).pack(fill="x", padx=24, pady=18)

        self.protocol("WM_DELETE_WINDOW", self.cerrar)
        self.after(120, self.grab_set)
        self._actualizar_vista()

    def _actualizar_vista(self):
        if not self._camara or not self.winfo_exists():
            return
        leida, frame = self._camara.read()
        if not leida:
            messagebox.showerror(
                "Error de cámara",
                "La cámara dejó de entregar imagen. Cierre esta ventana y vuelva a intentarlo.",
                parent=self,
            )
            self.cerrar()
            return

        rgb = self._cv2.cvtColor(frame, self._cv2.COLOR_BGR2RGB)
        self._imagen_actual = Image.fromarray(rgb)
        vista = ImageOps.fit(
            self._imagen_actual,
            (400, 300),
            method=Image.Resampling.LANCZOS,
        )
        self._imagen_preview = ctk.CTkImage(light_image=vista, size=(400, 300))
        self.vista.configure(image=self._imagen_preview, text="")
        self._trabajo = self.after(40, self._actualizar_vista)

    def capturar(self):
        if self._imagen_actual is None:
            messagebox.showwarning("Foto no disponible", "Espere a que aparezca la vista previa.", parent=self)
            return
        self.al_capturar(self._imagen_actual.copy())
        self.cerrar()

    def cerrar(self):
        if self._trabajo:
            self.after_cancel(self._trabajo)
            self._trabajo = None
        if self._camara:
            self._camara.release()
            self._camara = None
        self.destroy()
