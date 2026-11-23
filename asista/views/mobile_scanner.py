"""Módulo reutilizable para escaneo en tiempo real de códigos de barras/QR.

Utiliza la lógica ya presente en `vista_kiosco.py` (zxingcpp + OpenCV) y la
expone mediante la clase `MobileScannerDialog` que hereda de
`customtkinter.CTkToplevel`. La ventana muestra un `<video>` interno
implementado con OpenCV (`cv2.VideoCapture`) y decodifica cada frame
hasta encontrar un texto legible.

Cuando se detecta un código, se llama al *callback* proporcionado con el
texto (cédula) y se cierra la ventana.
"""

import threading
import time
import cv2
import numpy as np

try:
    import zxingcpp
except ImportError:
    zxingcpp = None

import customtkinter as ctk
from tkinter import messagebox
from PIL import Image, ImageTk

# ---------------------------------------------------------------------------
# Decodificador reutilizable (copia de `decodificar_imagen_carnet` del
# vista_kiosco). Devuelve (texto, posición, backend) o (None, None, None).
# ---------------------------------------------------------------------------
def decodificar_frame(frame):
    if frame is None:
        return None, None, None

    # 1. Intentar con zxingcpp en BGR
    if zxingcpp:
        formatos_lineales = zxingcpp.BarcodeFormat.AllLinear
        try:
            res = zxingcpp.read_barcode(frame, formats=formatos_lineales)
            if res and res.text and res.text.strip():
                return res.text.strip(), res.position, "zxing_bgr"
        except Exception:
            pass
        # 2. Gris
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        try:
            res = zxingcpp.read_barcode(gray, formats=formatos_lineales)
            if res and res.text and res.text.strip():
                return res.text.strip(), res.position, "zxing_gray"
        except Exception:
            pass
        # 3. CLAHE (contraste)
        try:
            clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
            enh = clahe.apply(gray)
            res = zxingcpp.read_barcode(enh, formats=formatos_lineales)
            if res and res.text and res.text.strip():
                return res.text.strip(), res.position, "zxing_clahe"
        except Exception:
            pass
        # 4. Sharpen
        try:
            kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
            sharp = cv2.filter2D(gray, -1, kernel)
            res = zxingcpp.read_barcode(sharp, formats=formatos_lineales)
            if res and res.text and res.text.strip():
                return res.text.strip(), res.position, "zxing_sharp"
        except Exception:
            pass
        # 5. Adaptive Gaussian threshold
        try:
            adapt = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, 5
            )
            res = zxingcpp.read_barcode(adapt, formats=formatos_lineales)
            if res and res.text and res.text.strip():
                return res.text.strip(), res.position, "zxing_adapt"
        except Exception:
            pass

    # Fallback con OpenCV nativo (BarcodeDetector y QRCodeDetector)
    try:
        b_det = cv2.barcode.BarcodeDetector()
        txt, pts, _ = b_det.detectAndDecode(frame)
        if txt and txt.strip():
            return txt.strip(), pts, "cv2_bar"
    except Exception:
        pass
    try:
        qr_det = cv2.QRCodeDetector()
        txt, pts, _ = qr_det.detectAndDecode(frame)
        if txt and txt.strip():
            return txt.strip(), pts, "cv2_qr"
    except Exception:
        pass

    return None, None, None

# ---------------------------------------------------------------------------
# Diálogo de escáner móvil
# ---------------------------------------------------------------------------
class MobileScannerDialog(ctk.CTkToplevel):
    """Ventana modal que abre la cámara del ordenador y escanea en tiempo real.

    Parámetros
    ----------
    master: widget padre.
    on_success: ``callable(str)`` que recibe el texto del código leído.
    """

    def __init__(self, master, on_success):
        super().__init__(master, fg_color="transparent")
        self.title("Escáner de código – Asista (móvil)")
        self.geometry("480x360")
        self.resizable(False, False)
        self.transient(master.winfo_toplevel())
        self.after(150, self.grab_set)

        self.on_success = on_success
        self._running = False
        self._thread = None

        # UI mínima: etiqueta + canvas para mostrar frame
        self.lbl = ctk.CTkLabel(self, text="Apunte el carnet a la cámara…", font=("Helvetica", 12))
        self.lbl.pack(pady=4)
        self.canvas = ctk.CTkCanvas(self, width=440, height=300, bg="black")
        self.canvas.pack()

        self._start_camera()
        self.protocol("WM_DELETE_WINDOW", self._cerrar)

    # ---------------------------------------------------------------------
    def _start_camera(self):
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            messagebox.showerror("Error", "No se pudo acceder a la cámara.")
            self.destroy()
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self):
        while self._running:
            ret, frame = self.cap.read()
            if not ret:
                continue
            # Mostrar frame en canvas (convertir a PhotoImage)
            img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img_pil = Image.fromarray(img_rgb)
            img_tk = ImageTk.PhotoImage(img_pil.resize((440, 300)))
            # tkinter requiere mantener referencia
            self.canvas.img = img_tk
            self.canvas.create_image(0, 0, anchor="nw", image=img_tk)

            # Intentar decodificar
            codigo, _, _ = decodificar_frame(frame)
            if codigo:
                self._running = False
                self.after(0, lambda: self._notify_success(codigo))
                break
            time.sleep(0.03)

    def _notify_success(self, codigo):
        if callable(self.on_success):
            self.on_success(codigo)
        self._cerrar()

    def _cerrar(self):
        self._running = False
        if hasattr(self, "cap") and self.cap is not None:
            self.cap.release()
        self.destroy()

# ---------------------------------------------------------------------------
# Helper para lanzar el escáner desde cualquier vista
# ---------------------------------------------------------------------------
def lanzar_escanner(master, on_success):
    """Conveniencia: crea y muestra ``MobileScannerDialog``.

    ``on_success`` recibe la cadena encontrada (cédula). Si el usuario cierra
    la ventana sin leer nada, simplemente no se llama.
    """
    MobileScannerDialog(master, on_success)

"""Fin del módulo mobile_scanner.py"""
