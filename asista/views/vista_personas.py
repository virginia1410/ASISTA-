"""Módulo Personas: Gestión de estudiantes y personal de la institución (Altas, Bajas, Edición, Carnets)."""
import os
import subprocess
import sys
from tkinter import filedialog, messagebox
import customtkinter as ctk

import carnets
from fotos_manager import DialogoCapturaCamara, procesar_y_guardar_foto, DIR_FOTOS
from PIL import Image
import config
from config import CARGOS
from tema import BG, F_TITULO, F_TEXTO, TEXTO, SUAVE
from .ui_utils import (
    Vista, seguro, tarjeta, campo, combo, segmentado, boton, etiqueta, crear_tabla, insertar, limpiar
)


class FormPersona(ctk.CTkToplevel):
    def __init__(self, master, db, persona=None, al_guardar=None):
        super().__init__(master, fg_color=BG)
        self.db, self.persona, self.al_guardar = db, persona, al_guardar
        titulo_texto = "Editar persona" if persona else "Nueva persona"
        self.title(titulo_texto)
        self.geometry("520x680")
        self.minsize(460, 480)
        self.resizable(True, True)
        self.transient(master.winfo_toplevel())
        self.after(150, self.grab_set)
        self.mapa = {s["etiqueta"]: s["id_seccion"] for s in db.secciones()}

        self.foto_pil_actual = None
        self.foto_nombre_existente = (persona.get("foto") if persona else None)

        # 1. Barra superior fija con Título
        f_top = ctk.CTkFrame(self, fg_color="transparent")
        f_top.pack(fill="x", padx=24, pady=(18, 6))
        ctk.CTkLabel(f_top, text=titulo_texto, font=(F_TITULO, 20, "bold"), text_color=TEXTO).pack(anchor="w")

        # 2. Barra inferior fija (Toolbar de acciones: Cancelar y Guardar Cambios)
        f_toolbar = ctk.CTkFrame(self, fg_color=SUAVE, height=64, corner_radius=0)
        f_toolbar.pack(side="bottom", fill="x")
        f_toolbar.pack_propagate(False)

        boton(f_toolbar, "Cancelar", "blanco", self.destroy, height=40, width=120).pack(side="left", padx=(20, 10), pady=12)
        txt_btn_guardar = "💾 Guardar Cambios" if persona else "💾 Registrar Persona"
        boton(f_toolbar, txt_btn_guardar, "primario", self.guardar, height=40).pack(side="right", fill="x", expand=True, padx=(10, 20), pady=12)

        # 3. Contenedor desplazable con barra de scroll para ver cómodamente hacia abajo
        self.scroll_body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_body.pack(fill="both", expand=True, padx=12, pady=(0, 6))

        # Sección de Foto de Perfil / Carnet
        f_foto_box = ctk.CTkFrame(self.scroll_body, fg_color="transparent")
        f_foto_box.pack(fill="x", padx=16, pady=(10, 4))

        self.f_preview = ctk.CTkFrame(f_foto_box, width=80, height=96, fg_color="#E2E8F0", corner_radius=10)
        self.f_preview.pack(side="left", padx=(0, 14))
        self.f_preview.pack_propagate(False)
        self.lbl_foto_preview = ctk.CTkLabel(self.f_preview, text="Sin Foto\n👤", font=(F_TEXTO, 11), text_color="#64748B")
        self.lbl_foto_preview.pack(fill="both", expand=True)

        f_foto_actions = ctk.CTkFrame(f_foto_box, fg_color="transparent")
        f_foto_actions.pack(side="left", fill="both", expand=True)

        ctk.CTkLabel(f_foto_actions, text="Foto de Perfil para Carnet", font=(F_TEXTO, 12, "bold"), text_color=TEXTO, anchor="w").pack(fill="x")
        
        f_btns_f = ctk.CTkFrame(f_foto_actions, fg_color="transparent")
        f_btns_f.pack(fill="x", pady=(6, 0))

        boton(f_btns_f, "📷 Tomar Foto", "primario", self._tomar_foto_camara, height=32).pack(side="left", padx=(0, 6))
        boton(f_btns_f, "📁 Subir", "blanco", self._subir_foto_archivo, height=32).pack(side="left")

        self.tipo = segmentado(self.scroll_body, values=["Estudiante", "Personal"], command=self._tipo)
        self.tipo.pack(fill="x", padx=16, pady=(12, 0))
        self.e_ced = self._campo("Cédula")
        self.e_nom = self._campo("Nombre")
        self.e_ape = self._campo("Apellido")
        self.e_tel = self._campo("Teléfono (opcional)")
        self.extra = ctk.CTkFrame(self.scroll_body, fg_color="transparent")
        self.extra.pack(fill="x")
        self.f_sec = ctk.CTkFrame(self.extra, fg_color="transparent")
        etiqueta(self.f_sec, "Sección").pack(fill="x", padx=16, pady=(10, 2))
        self.cb_sec = combo(self.f_sec, values=list(self.mapa) or [""])
        self.cb_sec.pack(fill="x", padx=16)

        etiqueta(self.f_sec, "Nombre del Representante (opcional)").pack(fill="x", padx=16, pady=(10, 2))
        self.e_rep = campo(self.f_sec, placeholder_text="ej: Ana Gómez")
        self.e_rep.pack(fill="x", padx=16)

        etiqueta(self.f_sec, "Teléfono del Representante (opcional)").pack(fill="x", padx=16, pady=(10, 2))
        self.e_tel_rep = campo(self.f_sec, placeholder_text="ej: 0414-1234567")
        self.e_tel_rep.pack(fill="x", padx=16)
        self.f_car = ctk.CTkFrame(self.extra, fg_color="transparent")
        etiqueta(self.f_car, "Cargo").pack(fill="x", padx=16, pady=(12, 2))
        self.cb_car = combo(self.f_car, values=CARGOS)
        self.cb_car.pack(fill="x", padx=16)
        if self.mapa:
            self.cb_sec.set(next(iter(self.mapa)))

        ctk.CTkFrame(self.scroll_body, height=12, fg_color="transparent").pack()

        if persona:
            self.tipo.set(persona["tipo_persona"])
            self.tipo.configure(state="disabled")
            for e, k in ((self.e_ced, "cedula"), (self.e_nom, "nombre"), (self.e_ape, "apellido"),
                         (self.e_tel, "telefono")):
                e.insert(0, persona[k] or "")
            et = next((k for k, v in self.mapa.items() if v == persona["id_seccion"]), None)
            if et:
                self.cb_sec.set(et)
            if persona["cargo"]:
                self.cb_car.set(persona["cargo"])
            if persona.get("representante"):
                self.e_rep.insert(0, persona["representante"])
            if persona.get("telefono_representante"):
                self.e_tel_rep.insert(0, persona["telefono_representante"])
            if persona.get("foto"):
                p_foto = DIR_FOTOS / persona["foto"]
                if p_foto.exists():
                    try:
                        img_ex = Image.open(str(p_foto))
                        self._actualizar_thumbnail(img_ex)
                    except Exception:
                        pass
        else:
            self.tipo.set("Estudiante")
        self._tipo(self.tipo.get())

    def _actualizar_thumbnail(self, img_pil):
        try:
            th = img_pil.resize((74, 90), Image.Resampling.LANCZOS)
            ctk_img = ctk.CTkImage(light_image=th, size=(74, 90))
            self.lbl_foto_preview.configure(image=ctk_img, text="")
            self.lbl_foto_preview.image = ctk_img
        except Exception:
            pass

    def _tomar_foto_camara(self):
        def _cb(img_capturada):
            self.foto_pil_actual = img_capturada
            self._actualizar_thumbnail(img_capturada)
        DialogoCapturaCamara(self, _cb)

    def _subir_foto_archivo(self):
        ruta = filedialog.askopenfilename(
            parent=self,
            title="Seleccionar foto de perfil",
            filetypes=[("Imágenes", "*.jpg *.jpeg *.png *.webp")]
        )
        if ruta:
            try:
                img = Image.open(ruta).convert("RGB")
                self.foto_pil_actual = img
                self._actualizar_thumbnail(img)
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo cargar la imagen:\n{e}")

    def _campo(self, texto):
        etiqueta(self.scroll_body, texto).pack(fill="x", padx=16, pady=(12, 2))
        e = campo(self.scroll_body, height=38)
        e.pack(fill="x", padx=16)
        return e

    def _tipo(self, valor):
        self.f_sec.pack_forget()
        self.f_car.pack_forget()
        (self.f_sec if valor == "Estudiante" else self.f_car).pack(fill="x")

    @seguro
    def guardar(self):
        d = {"tipo": self.tipo.get(), "cedula": self.e_ced.get().strip(), "nombre": self.e_nom.get().strip(),
             "apellido": self.e_ape.get().strip(), "telefono": self.e_tel.get().strip() or None}
        if len(d["cedula"]) < 5 or not d["cedula"].replace("-", "").isalnum():
            raise UserWarning("Ingrese una cédula válida (solo letras, números o guion).")
        if not d["nombre"] or not d["apellido"]:
            raise UserWarning("Nombre y apellido son obligatorios.")
        if d["tipo"] == "Estudiante":
            if self.cb_sec.get() not in self.mapa:
                raise UserWarning("Seleccione una sección válida (puede registrar nuevas secciones desde el módulo de Administración).")
            d["id_seccion"] = self.mapa[self.cb_sec.get()]
            d["representante"] = self.e_rep.get().strip() or None
            d["telefono_representante"] = self.e_tel_rep.get().strip() or None
        else:
            d["cargo"] = self.cb_car.get()
        # Procesar foto
        nombre_foto = self.foto_nombre_existente
        if self.foto_pil_actual:
            res_foto = procesar_y_guardar_foto(self.foto_pil_actual, d["cedula"])
            if res_foto:
                nombre_foto = res_foto
        d["foto"] = nombre_foto

        if self.persona:
            self.db.actualizar_persona(self.persona["id_persona"], d)
        else:
            self.db.crear_persona(d)
        if self.al_guardar:
            self.al_guardar()
        self.destroy()



class DialogoConfirmarClave(ctk.CTkToplevel):
    def __init__(self, master, db, id_usuario, on_exito):
        super().__init__(master, fg_color=BG)
        self.db = db
        self.id_usuario = id_usuario
        self.on_exito = on_exito
        self.title("Seguridad · Verificación")
        self.geometry("400x260")
        self.resizable(False, False)
        self.transient(master.winfo_toplevel())
        self.after(150, self.grab_set)

        ctk.CTkLabel(self, text="🔒 Verificación de Seguridad", font=(F_TITULO, 18, "bold"), text_color=TEXTO).pack(pady=(22, 6))
        ctk.CTkLabel(
            self,
            text="Ingrese su contraseña de usuario para consultar\nel Archivo Histórico de Estudiantes Inactivos y Egresados:",
            font=(F_TEXTO, 11),
            text_color=TEXTO,
            justify="center"
        ).pack(pady=(0, 14))

        self.e_pass = campo(self, show="*", placeholder_text="Contraseña de usuario")
        self.e_pass.pack(fill="x", padx=32, pady=(0, 16))
        self.e_pass.bind("<Return>", lambda e: self.verificar())

        boton(self, "Desbloquear Archivo", "primario", self.verificar, height=42).pack(fill="x", padx=32)

    @seguro
    def verificar(self):
        pwd = self.e_pass.get().strip()
        if not pwd:
            raise UserWarning("Por favor ingrese su contraseña.")
        es_valido = self.db.verificar_password_usuario(self.id_usuario, pwd)
        if not es_valido:
            raise UserWarning("Contraseña incorrecta. Acceso al Archivo Histórico denegado.")
        self.destroy()
        if self.on_exito:
            self.on_exito()


class VentanaArchivoHistoricoEstudiantes(ctk.CTkToplevel):
    def __init__(self, master, db, on_reactivar=None):
        super().__init__(master, fg_color=BG)
        self.db = db
        self.on_reactivar = on_reactivar
        self.filas = {}
        self.title("Archivo Histórico Escolar · Estudiantes Egresados e Inactivos")
        self.geometry("1040x620")
        self.minsize(920, 520)
        self.transient(master.winfo_toplevel())
        self.after(150, self.grab_set)

        # Encabezado
        head = ctk.CTkFrame(self, fg_color="transparent")
        head.pack(fill="x", padx=24, pady=(18, 10))
        ctk.CTkLabel(head, text="📁 Archivo Histórico de Estudiantes (Bajas y Egresados)", font=(F_TITULO, 20, "bold"), text_color=TEXTO).pack(anchor="w")
        ctk.CTkLabel(head, text="Expedientes resguardados de estudiantes egresados de 5° Año, traslados y retiros escolares.", font=(F_TEXTO, 11), text_color=TEXTO).pack(anchor="w")

        # Barra de búsqueda y acciones
        barra = ctk.CTkFrame(self, fg_color="transparent")
        barra.pack(fill="x", padx=24, pady=(0, 12))
        self.e_buscar = campo(barra, height=40, placeholder_text="Buscar en histórico por cédula, nombre o motivo…")
        self.e_buscar.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.e_buscar.bind("<KeyRelease>", lambda e: self.cargar())

        boton(barra, "↺ Reincorporar Estudiante", "acento", self.reincorporar, width=190, height=40).pack(side="left", padx=(0, 8))
        boton(barra, "📂 Abrir Carpeta de Respaldo", "suave", self.abrir_carpeta, width=210, height=40).pack(side="left", padx=(0, 8))
        boton(barra, "Cerrar", "suave", self.destroy, width=80, height=40).pack(side="left")

        t = tarjeta(self)
        t.pack(fill="both", expand=True, padx=24, pady=(0, 20))
        cont, self.tabla = crear_tabla(
            t,
            [
                ("ced", "Cédula", 100),
                ("nombre", "Nombre", 140),
                ("apellido", "Apellido", 140),
                ("seccion", "Última Sección", 160),
                ("fecha", "Fecha Salida", 140),
                ("motivo", "Motivo de Baja / Egreso", 240),
                ("rep", "Representante", 170)
            ],
            14
        )
        cont.pack(fill="both", expand=True, padx=14, pady=14)
        self.cargar()

    @seguro
    def cargar(self):
        limpiar(self.tabla)
        self.filas = {}
        for r in self.db.listar_estudiantes_inactivos(self.e_buscar.get().strip()):
            iid = str(r["id_persona"])
            self.filas[iid] = r
            f_str = r["fecha_inactivo"].strftime("%d/%m/%Y %H:%M") if r.get("fecha_inactivo") else "—"
            rep_txt = r.get("representante") or "—"
            if r.get("telefono_representante"):
                rep_txt += f" ({r['telefono_representante']})"
            insertar(
                self.tabla,
                (r["cedula"], r["nombre"], r["apellido"], r["seccion_origen"], f_str, r["motivo_inactivo"], rep_txt),
                iid=iid
            )

    @seguro
    def reincorporar(self):
        sel = self.tabla.selection()
        if not sel:
            raise UserWarning("Seleccione un estudiante de la tabla para reincorporarlo.")
        p = self.filas[sel[0]]

        if not messagebox.askyesno(
            "Confirmar Reincorporación",
            f"¿Desea restaurar a {p['nombre']} {p['apellido']} a la lista de estudiantes activos?"
        ):
            return

        self.db.reactivar_estudiante(p["id_persona"])
        messagebox.showinfo("Estudiante Reactivado", f"{p['nombre']} {p['apellido']} ha sido reincorporado a la matrícula activa.")
        self.cargar()
        if self.on_reactivar:
            self.on_reactivar()

    def abrir_carpeta(self):
        import config
        import subprocess
        p = config.BASE_DIR / "respaldos" / "estudiantes_archivados"
        p.mkdir(parents=True, exist_ok=True)
        try:
            if os.name == 'nt':
                os.startfile(p)
            else:
                subprocess.Popen(["xdg-open", str(p)])
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir la carpeta: {e}")



# ==============================================================================
# MODALES: EXPEDIENTE ACADÉMICO E INSCRIPCIÓN RÁPIDA EN CURSOS
# ==============================================================================
class DialogoInscribirCurso(ctk.CTkToplevel):
    """Permite inscribir a un alumno existente en un nuevo curso sin duplicar datos."""
    def __init__(self, master, db, persona, on_exito=None):
        super().__init__(master, fg_color=BG)
        self.db = db
        self.persona = persona
        self.on_exito = on_exito

        self.title("Inscribir Estudiante en Curso")
        self.geometry("480x420")
        self.resizable(False, False)
        self.transient(master.winfo_toplevel())
        self.after(150, self.grab_set)

        ctk.CTkLabel(
            self,
            text="➕ Inscribir en Curso",
            font=(F_TITULO, 20, "bold"),
            text_color=TEXTO
        ).pack(pady=(20, 4))

        nombre_completo = f"{persona['nombre']} {persona['apellido']}"
        ctk.CTkLabel(
            self,
            text=f"Estudiante: {nombre_completo} (C.I. {persona['cedula']})",
            font=(F_TEXTO, 12, "bold"),
            text_color=SUAVE
        ).pack(pady=(0, 16))

        form = ctk.CTkFrame(self, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=28)

        # Cargar cohortes activas
        self.cohortes = self.db.listar_cohortes(incluir_archivados=False)
        if not self.cohortes:
            opciones_c = ["(No hay cursos activos abiertos actualmente)"]
        else:
            opciones_c = [
                f"{c['curso_codigo']} · {c['curso_nombre']} - {c['nombre_grupo']} ({c['dias_semana']})"
                for c in self.cohortes
            ]

        etiqueta(form, "Seleccione el Curso / Horario").pack(anchor="w")
        self.cb_cohorte = combo(form, values=opciones_c)
        self.cb_cohorte.pack(fill="x", pady=(2, 14))
        if opciones_c:
            self.cb_cohorte.set(opciones_c[0])

        etiqueta(form, "Observaciones de Matrícula (Opcional)").pack(anchor="w")
        self.e_obs = campo(form, placeholder_text="ej: Reingreso, Beca institucional...")
        self.e_obs.pack(fill="x", pady=(2, 20))

        boton(self, "Confirmar Inscripción", "primario", self.guardar, height=44).pack(fill="x", padx=28, pady=(0, 24))

    @seguro
    def guardar(self):
        if not self.cohortes:
            raise UserWarning("No hay cursos abiertos disponibles para inscribir.")

        sel = self.cb_cohorte.get()
        id_cohorte = None
        for i, c in enumerate(self.cohortes):
            label = f"{c['curso_codigo']} · {c['curso_nombre']} - {c['nombre_grupo']} ({c['dias_semana']})"
            if label == sel:
                id_cohorte = c["id_cohorte"]
                break

        if not id_cohorte:
            raise UserWarning("Debe seleccionar un curso válido de la lista.")

        obs = self.e_obs.get().strip()
        self.db.inscribir_estudiante_cohorte(self.persona["id_persona"], id_cohorte, obs)
        messagebox.showinfo(
            "Inscripción Exitosa",
            f"El estudiante {self.persona['nombre']} {self.persona['apellido']} "
            f"ha sido inscrito exitosamente en el curso seleccionado."
        )
        if self.on_exito:
            self.on_exito()
        self.destroy()


class VentanaHistorialEstudiante(ctk.CTkToplevel):
    """Muestra el expediente académico acumulativo del estudiante a lo largo del tiempo."""
    def __init__(self, master, db, persona, on_actualizar=None):
        super().__init__(master, fg_color=BG)
        self.db = db
        self.persona = persona
        self.on_actualizar = on_actualizar

        nombre_completo = f"{persona['nombre']} {persona['apellido']}"
        self.title(f"Expediente Académico · {nombre_completo}")
        self.geometry("1060x600")
        self.minsize(920, 500)
        self.transient(master.winfo_toplevel())
        self.after(150, self.grab_set)

        # Encabezado con datos del alumno
        head = ctk.CTkFrame(self, fg_color="transparent")
        head.pack(fill="x", padx=24, pady=(18, 12))

        f_izq = ctk.CTkFrame(head, fg_color="transparent")
        f_izq.pack(side="left", fill="both", expand=True)

        ctk.CTkLabel(
            f_izq,
            text=f"🎓 Expediente del Estudiante: {nombre_completo}",
            font=(F_TITULO, 22, "bold"),
            text_color=TEXTO
        ).pack(anchor="w")

        tel = persona.get("telefono") or "Sin teléfono"
        rep = persona.get("representante") or "No registrado"
        ctk.CTkLabel(
            f_izq,
            text=f"C.I.: {persona['cedula']}  |  Teléfono: {tel}  |  Representante: {rep}  |  QR Permanente: Asignado ✓",
            font=(F_TEXTO, 12),
            text_color=SUAVE
        ).pack(anchor="w", pady=(2, 0))

        # Botones superiores
        f_der = ctk.CTkFrame(head, fg_color="transparent")
        f_der.pack(side="right")

        boton(f_der, "➕ Inscribir en Otro Curso", "acento", self.inscribir_nuevo, width=180, height=40).pack(side="left", padx=(0, 8))
        boton(f_der, "🖹 Carnet Serial", "primario", self.imprimir_carnet, width=120, height=40).pack(side="left", padx=(0, 8))
        boton(f_der, "Cerrar", "suave", self.destroy, width=80, height=40).pack(side="left")

        # Tarjeta y tabla de cursos realizados
        t = tarjeta(self)
        t.pack(fill="both", expand=True, padx=24, pady=(0, 20))

        cont, self.tabla = crear_tabla(
            t,
            [
                ("codigo", "Código", 95),
                ("curso", "Especialidad / Curso", 240),
                ("grupo", "Grupo / Denominación", 180),
                ("horario", "Días y Horario", 180),
                ("periodo", "Período / Trimestre", 160),
                ("docente", "Profesor", 150),
                ("asist", "Asistencia %", 110),
                ("estado", "Estatus del Curso", 130)
            ],
            14
        )
        cont.pack(fill="both", expand=True, padx=16, pady=16)

        self.cargar()

    @seguro
    def cargar(self):
        limpiar(self.tabla)
        historial = self.db.obtener_historial_academico_estudiante(self.persona["id_persona"])
        for r in historial:
            iid = str(r["id_matricula"])
            h_ini = str(r.get("hora_inicio", ""))[:5]
            h_fin = str(r.get("hora_fin", ""))[:5]
            horario_txt = f"{r.get('dias_semana', '')} ({h_ini} - {h_fin})"
            doc = r.get("docente_nombre", "").strip() or "Sin asignar"
            pct_val = float(r.get('porcentaje_asistencia', 0))
            st = r.get("estado_matricula", "En Curso")
            pct = f"⚠️ {pct_val:.1f}% (Riesgo)" if pct_val < 75.0 and st == "En Curso" else f"{pct_val:.1f}%"

            # Iconos de estatus
            if st in ("Egresado", "Aprobado"):
                st_txt = f"✓ {st}"
            elif st == "En Curso":
                st_txt = f"🟢 {st}"
            elif st == "Reprobado":
                st_txt = f"❌ {st}"
            else:
                st_txt = st

            insertar(
                self.tabla,
                (r["curso_codigo"], r["curso_nombre"], r["nombre_grupo"],
                 horario_txt, r["periodo_nombre"], doc, pct, st_txt),
                iid=iid
            )

    @seguro
    def inscribir_nuevo(self):
        DialogoInscribirCurso(self, self.db, self.persona, self._al_inscribir)

    def _al_inscribir(self):
        self.cargar()
        if self.on_actualizar:
            self.on_actualizar()

    @seguro
    def imprimir_carnet(self):
        ruta = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("Documento PDF", "*.pdf")],
            initialfile=f"carnet_{self.persona['cedula']}.pdf"
        )
        if not ruta:
            return
        carnets.generar_carnet_individual(self.db, self.persona["id_persona"], ruta)
        messagebox.showinfo("Carnet Generado", f"Carnet institucional con código serial generado con éxito:\n{ruta}")
        try:
            if sys.platform.startswith("win"):
                os.startfile(ruta)
            else:
                subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", ruta])
        except Exception:
            pass


class Personas(Vista):
    def __init__(self, master, app):
        super().__init__(master, app)
        self.filas, self._job = {}, None
        self.titulo("Gestión de personas", "Estudiantes y personal de la institución")
        # Fila 1: Búsqueda, Filtro de Roles y Botón de Añadir Persona
        f_top = ctk.CTkFrame(self, fg_color="transparent")
        f_top.pack(fill="x", padx=30, pady=(0, 8))
        self.e_buscar = campo(f_top, height=40, placeholder_text="Buscar por nombre, cédula o curso…")
        self.e_buscar.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.e_buscar.bind("<KeyRelease>", lambda e: self._programar())
        self.seg = segmentado(f_top, values=["Todos", "Estudiante", "Personal"], command=lambda v: self.cargar(),
                              height=38)
        self.seg.set("Todos")
        self.seg.pack(side="left", padx=(0, 10))
        boton(f_top, "+ Añadir Persona", "acento", self.nueva, width=160, height=40).pack(side="right")

        # Fila 2: Barra de herramientas para la persona seleccionada
        f_herramientas = ctk.CTkFrame(self, fg_color="transparent")
        f_herramientas.pack(fill="x", padx=30, pady=(0, 12))
        boton(f_herramientas, "🎓 Expediente", "acento", self.abrir_historial, width=140, height=38).pack(side="left", padx=(0, 8))
        boton(f_herramientas, "➕ Inscribir en Curso", "primario", self.inscribir_en_curso, width=175, height=38).pack(side="left", padx=(0, 8))
        boton(f_herramientas, "🖹 Carnet Serial", "suave", self.imprimir_carnet, width=130, height=38).pack(side="left", padx=(0, 8))
        boton(f_herramientas, "✏️ Editar", "suave", self.editar, width=105, height=38).pack(side="left", padx=(0, 8))
        boton(f_herramientas, "🗑️ Dar de Baja", "suave", self.dar_baja, width=135, height=38).pack(side="left", padx=(0, 8))
        boton(f_herramientas, "📁 Archivo Histórico", "suave", self.abrir_archivo_historico, width=165, height=38).pack(side="left")

        t = tarjeta(self)
        t.pack(fill="both", expand=True, padx=30, pady=(0, 24))
        cont, self.tabla = crear_tabla(t, [("cedula", "Cédula", 100), ("nombre", "Nombre", 150),
                                           ("apellido", "Apellido", 150), ("tipo", "Tipo", 95),
                                           ("detalle", "Sección / Cargo", 200),
                                           ("rep", "Edad", 120),
                                           ("tel", "Teléfono", 120)], 15)
        cont.pack(fill="both", expand=True, padx=16, pady=16)
        self.tabla.bind("<Double-1>", lambda e: self.abrir_historial())

    @seguro
    def abrir_historial(self):
        sel = self.tabla.selection()
        if not sel:
            raise UserWarning("Seleccione un estudiante de la tabla para ver su expediente e historial.")
        p = self.filas[sel[0]]
        VentanaHistorialEstudiante(self, self.db, p, self.cargar)

    @seguro
    def inscribir_en_curso(self):
        sel = self.tabla.selection()
        if not sel:
            raise UserWarning("Seleccione un estudiante de la tabla para inscribirlo en un curso.")
        p = self.filas[sel[0]]
        DialogoInscribirCurso(self, self.db, p, self.cargar)

    def refrescar(self):
        self.cargar()

    def _programar(self):
        if self._job:
            self.after_cancel(self._job)
        self._job = self.after(250, self.cargar)

    @seguro
    def cargar(self):
        limpiar(self.tabla)
        self.filas = {}
        for r in self.db.listar_personas(self.e_buscar.get().strip(), self.seg.get()):
            iid = str(r["id_persona"])
            self.filas[iid] = r
            if r["tipo_persona"] == "Estudiante":
                rep_txt = r.get("representante") or "—"
                if "(" in rep_txt:
                    rep_txt = rep_txt.split("(")[0].strip()
            else:
                rep_txt = "Personal Institucional"

            insertar(self.tabla, (r["cedula"], r["nombre"], r["apellido"], r["tipo_persona"], r["detalle"] or "",
                                  rep_txt, r["telefono"] or ""), iid=iid)

    @seguro
    def nueva(self):
        FormPersona(self, self.db, None, self.cargar)

    @seguro
    def editar(self):
        sel = self.tabla.selection()
        if not sel:
            raise UserWarning("Seleccione una persona de la tabla.")
        FormPersona(self, self.db, self.filas[sel[0]], self.cargar)

    @seguro
    def imprimir_carnet(self):
        sel = self.tabla.selection()
        if not sel:
            raise UserWarning("Seleccione una persona de la tabla para generar su carnet.")
        p = self.filas[sel[0]]
        ruta = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("Documento PDF", "*.pdf")],
            initialfile=f"carnet_{p['cedula']}.pdf"
        )
        if not ruta:
            return
        carnets.generar_carnet_individual(self.db, p["id_persona"], ruta)
        messagebox.showinfo("Carnet Generado", f"Carnet con código de barras generado con éxito:\n{ruta}")
        try:
            if sys.platform.startswith("win"):
                os.startfile(ruta)  # noqa: S606
            else:
                subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", ruta])
        except Exception:
            pass


    @seguro
    def dar_baja(self):
        sel = self.tabla.selection()
        if not sel:
            raise UserWarning("Seleccione un estudiante de la tabla para dar de baja.")
        p = self.filas[sel[0]]
        if p.get("tipo_persona") != "Estudiante":
            raise UserWarning("La baja de personal docente o administrativo debe realizarse desde el módulo de Administración.")

        operador = getattr(self.app, "usuario_actual", {}).get("username", "Admin")
        detalle = p.get("detalle") or ""

        # Si el estudiante es de 5° Año, ofrecer graduación directa
        if "5°" in detalle or "5to" in detalle.lower():
            opc = messagebox.askyesno(
                "Egreso de 5° Año / Graduación",
                f"El estudiante {p['nombre']} {p['apellido']} pertenece a 5° Año ({detalle}).\n\n"
                f"¿Desea tramitar directamente su GRADUACIÓN como Bachiller (Egreso de 5° Año)?\n\n"
                f"• Presione 'Sí' para marcarlo inactivo y archivarlo en el Respaldo Histórico de Directiva.\n"
                f"• Presione 'No' para especificar otro motivo de baja (traslado/retiro)."
            )
            if opc:
                motivo = "Promoción de Bachilleres (Egreso de 5° Año)"
                ruta = self.db.dar_baja_estudiante(p["id_persona"], motivo, operador)
                messagebox.showinfo(
                    "Graduación Completada",
                    f"✓ El estudiante {p['nombre']} {p['apellido']} ha egresado con éxito de 5° Año.\n\n"
                    f"El sistema ha actualizado su estatus a inactivo y resguardado su expediente en el Respaldo de Directiva:\n{ruta}"
                )
                self.cargar()
                return

        dlg = ctk.CTkInputDialog(
            text=f"¿Está seguro de pasar a inactivo al estudiante {p['nombre']} {p['apellido']}?\n\n"
                 f"Esta acción lo trasladará al Archivo Histórico Escolar.\n"
                 f"Ingrese el motivo (ej: Retiro Voluntario, Traslado a otra institución):",
            title="Dar de Baja a Estudiante"
        )
        motivo = dlg.get_input()
        if not motivo or not motivo.strip():
            return

        ruta = self.db.dar_baja_estudiante(p["id_persona"], motivo.strip(), operador)
        messagebox.showinfo(
            "Estudiante Archivado",
            f"El estudiante {p['nombre']} {p['apellido']} ha sido dado de baja de la lista activa.\n\n"
            f"Expediente archivado en el Respaldo de Directiva:\n{ruta}"
        )
        self.cargar()

    @seguro
    def egresar_5to(self):
        est = self.db.detectar_estudiantes_5to_ano()
        if not est:
            messagebox.showinfo("Cierre de 5° Año", "No se encontraron estudiantes activos matriculados en 5° Año actualmente.")
            return

        resumen = "\n".join([f"• {e['cedula']} - {e['nombre']} {e['apellido']} ({e['seccion_nombre']})" for e in est[:6]])
        if len(est) > 6:
            resumen += f"\n...y {len(est) - 6} estudiante(s) más."

        if not messagebox.askyesno(
            "Confirmar Egreso de 5° Año (Bachilleres)",
            f"Se detectaron {len(est)} estudiante(s) de 5° Año listos para egresar de bachillerato:\n\n{resumen}\n\n"
            f"¿Desea procesar su promoción de egresados y trasladarlos al Archivo Histórico?"
        ):
            return

        operador = getattr(self.app, "usuario_actual", {}).get("username", "Admin")
        n, ruta = self.db.procesar_egreso_5to_ano(operador)
        messagebox.showinfo(
            "Graduación Procesada",
            f"Se procesó con éxito el egreso de {n} bachiller(es).\n\n"
            f"Respaldo de promoción resguardado en:\n{ruta}"
        )
        self.cargar()

    @seguro
    def abrir_archivo_historico(self):
        id_u = getattr(self.app, "usuario_actual", {}).get("id_usuario")
        if not id_u:
            raise UserWarning("Sesión no válida para acceder al Archivo Histórico.")
        DialogoConfirmarClave(self, self.db, id_u, lambda: VentanaArchivoHistoricoEstudiantes(self, self.db, self.cargar))
