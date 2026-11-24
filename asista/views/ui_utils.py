"""Utilidades de interfaz de usuario, widgets personalizados y decoradores."""
import functools
import traceback
import tkinter as tk
from tkinter import messagebox, ttk
import customtkinter as ctk
import sqlite3

from tema import (
    ACENTO, ACENTO_H, AVISO, BG, BORDE, CARD, ESTADO_COLOR,
    F_TEXTO, F_TITULO, LEMA, MORADO, MORADO_OSC, NOMBRE_SISTEMA,
    OK, OK_H, PRIMARIO, PRIMARIO_H, SUAVE, SUAVE_BG, TEXTO
)


def seguro(fn):
    """Evita cierres inesperados: muestra el error en un cuadro de diálogo."""
    @functools.wraps(fn)
    def envoltura(self, *a, **k):
        try:
            return fn(self, *a, **k)
        except UserWarning as w:
            messagebox.showwarning("Atención", str(w))
        except sqlite3.IntegrityError as e:
            msg = "Esa cédula o dato único ya está registrado en el sistema." if "UNIQUE" in str(e).upper() else str(e)
            messagebox.showwarning("Dato no válido", msg)
        except sqlite3.Error as e:
            messagebox.showerror("Error de base de datos", str(e))
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            messagebox.showerror("Error inesperado", str(e))
    return envoltura


TABLAS = []


def estilo_tablas():
    """Configura el tema y estilo de las tablas ttk según el modo de apariencia."""
    oscuro = ctk.get_appearance_mode() == "Dark"
    bg, fg, zebra = ("#0F2042", "#F0F4F8", "#162C55") if oscuro else ("#FFFFFF", "#0A192F", "#F1F5F9")
    s = ttk.Style()
    s.theme_use("clam")
    s.configure(
        "Treeview",
        background=bg,
        fieldbackground=bg,
        foreground=fg,
        rowheight=36,
        borderwidth=0,
        font=(F_TEXTO, 11)
    )
    s.configure(
        "Treeview.Heading",
        background=MORADO,
        foreground="white",
        font=(F_TEXTO, 11, "bold"),
        relief="flat",
        padding=(8, 10)
    )
    # Fila seleccionada en Turquesa con texto Marino para contraste supremo
    s.map(
        "Treeview",
        background=[("selected", "#00B4D8")],
        foreground=[("selected", "#0A192F")]
    )
    s.map("Treeview.Heading", background=[("active", MORADO_OSC)])
    vivas = []
    for t in TABLAS:
        try:
            if t.winfo_exists():
                t.tag_configure("impar", background=zebra)
                vivas.append(t)
        except Exception:
            pass
    TABLAS[:] = vivas


# ==============================================================================
# PALETA DE BOTONES DE ALTO CONTRASTE (Modo Claro & Modo Oscuro)
# ==============================================================================
# Turquesa institucional vibrante (Acción principal / Acento)
COLOR_TURQUESA = ("#00B4D8", "#00B4D8")
COLOR_TURQUESA_H = ("#0096B7", "#06B6D4")
COLOR_TURQUESA_TXT = ("#0A192F", "#0A192F")

# Blanco luminoso con borde nítido (Acciones secundarias y herramientas)
COLOR_BLANCO = ("#FFFFFF", "#FFFFFF")
COLOR_BLANCO_H = ("#F1F5F9", "#E2E8F0")
COLOR_BLANCO_TXT = ("#0A192F", "#0A192F")
COLOR_BLANCO_BORDE = ("#CBD5E1", "#00B4D8")

# Primario Institucional
# Modo Claro: Navy Blue con texto blanco
# Modo Oscuro: Turquesa vibrante con texto Navy para máxima visibilidad en fondos oscuros
COLOR_PRIMARIO_BTN = ("#0F2042", "#00B4D8")
COLOR_PRIMARIO_BTN_H = ("#1A3668", "#06B6D4")
COLOR_PRIMARIO_BTN_TXT = ("#FFFFFF", "#0A192F")

# Peligro / Baja / Archivo
COLOR_PELIGRO_BTN = ("#FFFFFF", "#FFFFFF")
COLOR_PELIGRO_BTN_H = ("#FEE2E2", "#FEE2E2")
COLOR_PELIGRO_BTN_TXT = ("#DC2626", "#DC2626")
COLOR_PELIGRO_BORDE = ("#FCA5A5", "#EF4444")

# Éxito / Confirmación
COLOR_OK_BTN = ("#10B981", "#10B981")
COLOR_OK_BTN_H = ("#059669", "#34D399")
COLOR_OK_BTN_TXT = ("#FFFFFF", "#0A192F")

ESTILOS_BOTON = {
    "acento": (COLOR_TURQUESA, COLOR_TURQUESA_H, COLOR_TURQUESA_TXT, None, 0),
    "turquesa": (COLOR_TURQUESA, COLOR_TURQUESA_H, COLOR_TURQUESA_TXT, None, 0),
    "primario": (COLOR_PRIMARIO_BTN, COLOR_PRIMARIO_BTN_H, COLOR_PRIMARIO_BTN_TXT, None, 0),
    "suave": (COLOR_BLANCO, COLOR_BLANCO_H, COLOR_BLANCO_TXT, COLOR_BLANCO_BORDE, 1.5),
    "blanco": (COLOR_BLANCO, COLOR_BLANCO_H, COLOR_BLANCO_TXT, COLOR_BLANCO_BORDE, 1.5),
    "peligro": (COLOR_PELIGRO_BTN, COLOR_PELIGRO_BTN_H, COLOR_PELIGRO_BTN_TXT, COLOR_PELIGRO_BORDE, 1.5),
    "ok": (COLOR_OK_BTN, COLOR_OK_BTN_H, COLOR_OK_BTN_TXT, None, 0)
}


def boton(parent, texto, tipo, comando, **kw):
    estilo = ESTILOS_BOTON.get(tipo, ESTILOS_BOTON["suave"])
    fg, hv, tx, b_col, b_w = estilo
    alto = kw.pop("height", 42)
    borde_ancho = kw.pop("border_width", b_w)
    borde_color = kw.pop("border_color", b_col)
    texto_color = kw.pop("text_color", tx)

    params = {
        "text": texto,
        "command": comando,
        "fg_color": fg,
        "hover_color": hv,
        "text_color": texto_color,
        "height": alto,
        "corner_radius": alto // 2,
        "font": kw.pop("font", (F_TEXTO, 12, "bold")),
    }
    if borde_ancho > 0 and borde_color is not None:
        params["border_width"] = borde_ancho
        params["border_color"] = borde_color

    params.update(kw)
    return ctk.CTkButton(parent, **params)


def feedback_boton(widget, texto="✓ Registrado", duracion=1600, tipo="ok"):
    """Cambia temporalmente un botón para confirmar una acción sin alterar su comando."""
    if not widget or not widget.winfo_exists():
        return
    texto_original = widget.cget("text")
    fg_original = widget.cget("fg_color")
    hover_original = widget.cget("hover_color")
    texto_color_original = widget.cget("text_color")

    estilo = ESTILOS_BOTON.get(tipo, ESTILOS_BOTON["ok"])
    fg, hover, texto_color, _, _ = estilo
    widget.configure(text=texto, fg_color=fg, hover_color=hover, text_color=texto_color, state="disabled")

    def restaurar():
        if widget.winfo_exists():
            widget.configure(
                text=texto_original,
                fg_color=fg_original,
                hover_color=hover_original,
                text_color=texto_color_original,
                state="normal"
            )

    widget.after(duracion, restaurar)


def tarjeta(parent, **kw):
    return ctk.CTkFrame(parent, fg_color=CARD, corner_radius=20, border_width=1, border_color=BORDE, **kw)


def campo(parent, **kw):
    return ctk.CTkEntry(parent, fg_color=SUAVE_BG, border_color=BORDE, border_width=1, text_color=TEXTO,
                        placeholder_text_color=SUAVE, corner_radius=14, height=kw.pop("height", 42),
                        font=kw.pop("font", (F_TEXTO, 13)), **kw)


def combo(parent, **kw):
    return ctk.CTkComboBox(parent, fg_color=SUAVE_BG, border_color=BORDE, button_color=PRIMARIO,
                           button_hover_color=PRIMARIO_H, dropdown_fg_color=CARD, dropdown_hover_color=SUAVE_BG,
                           dropdown_text_color=TEXTO, text_color=TEXTO, corner_radius=14,
                           height=kw.pop("height", 40), state=kw.pop("state", "readonly"),
                           font=(F_TEXTO, 13), **kw)


def area(parent, **kw):
    return ctk.CTkTextbox(parent, fg_color=SUAVE_BG, border_color=BORDE, border_width=1, text_color=TEXTO,
                          corner_radius=14, font=(F_TEXTO, 13), **kw)


def segmentado(parent, **kw):
    fnt = kw.pop("font", (F_TEXTO, 11, "bold"))
    return ctk.CTkSegmentedButton(
        parent,
        fg_color=("#E2E8F0", "#162C55"),
        unselected_color=("#E2E8F0", "#162C55"),
        unselected_hover_color=("#CBD5E1", "#1E3A6D"),
        selected_color=("#00B4D8", "#00B4D8"),
        selected_hover_color=("#0096B7", "#06B6D4"),
        text_color=("#0F2042", "#0F2042"),
        font=fnt,
        corner_radius=14,
        **kw
    )


def chip(parent, texto, color):
    return ctk.CTkLabel(parent, text=f"  {texto}  ", fg_color=color, text_color="white", corner_radius=10,
                        height=24, font=(F_TEXTO, 11, "bold"))


def etiqueta(parent, texto, **kw):
    return ctk.CTkLabel(parent, text=texto, text_color=kw.pop("color", SUAVE), anchor="w",
                        font=kw.pop("font", (F_TEXTO, 12)), **kw)


def crear_tabla(parent, columnas, altura=10):
    cont = ctk.CTkFrame(parent, fg_color="transparent")
    cont.grid_rowconfigure(0, weight=1)
    cont.grid_columnconfigure(0, weight=1)

    tree = ttk.Treeview(cont, columns=[c[0] for c in columnas], show="headings", height=altura, selectmode="browse")
    for cid, titulo, ancho in columnas:
        tree.heading(cid, text=titulo)
        tree.column(cid, width=ancho, anchor="w")

    sb_y = ttk.Scrollbar(cont, orient="vertical", command=tree.yview)
    sb_x = ttk.Scrollbar(cont, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=sb_y.set, xscrollcommand=sb_x.set)

    tree.grid(row=0, column=0, sticky="nsew")
    sb_y.grid(row=0, column=1, sticky="ns")
    sb_x.grid(row=1, column=0, sticky="ew")

    for tag, color in {"Presente": "#12A97A", "Retraso": "#E8890C", "Salida Temprana": "#E8890C",
                       "Ausente": "#FF3B00", "pendiente": "#E8890C"}.items():
        tree.tag_configure(tag, foreground=color)
    TABLAS.append(tree)
    estilo_tablas()
    return cont, tree


def insertar(tree, valores, tags=(), iid=None):
    z = ("impar",) if len(tree.get_children()) % 2 else ()
    tree.insert("", "end", iid=iid, values=valores, tags=tuple(tags) + z)


def limpiar(tree):
    tree.delete(*tree.get_children())


class Vista(ctk.CTkScrollableFrame):
    """Clase base para todos los módulos de vista con barra de desplazamiento vertical integrada."""
    def __init__(self, master, app):
        super().__init__(master, fg_color=BG, corner_radius=0)
        self.app, self.db = app, app.db

    def titulo(self, texto, sub=""):
        ctk.CTkLabel(self, text=texto, font=(F_TITULO, 26, "bold"), text_color=TEXTO, anchor="w").pack(
            fill="x", padx=30, pady=(20, 0))
        ctk.CTkFrame(self, width=48, height=4, fg_color=ACENTO, corner_radius=2).pack(anchor="w", padx=30, pady=(6, 0))
        ctk.CTkLabel(self, text=sub, font=(F_TEXTO, 13), text_color=SUAVE, anchor="w").pack(
            fill="x", padx=30, pady=(6, 14))

    def refrescar(self):
        pass

    def actualizar_tema(self):
        self.configure(fg_color=BG)
