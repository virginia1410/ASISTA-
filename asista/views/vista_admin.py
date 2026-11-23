"""Módulo Administrativo: Gestión autónoma de Secciones Escolares y Cuentas de Usuarios del Sistema."""
from tkinter import messagebox, filedialog
import os
import sys
from datetime import datetime
from pathlib import Path
import customtkinter as ctk
import bcrypt
import config


def resource_path(relative_path):
    base_path = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base_path, relative_path)


from tema import (
    BG, BORDE, CARD, F_TEXTO, F_TITULO, OK, PRIMARIO, PRIMARIO_H, ACENTO, ACENTO_H, SUAVE, TEXTO
)
from .ui_utils import (
    Vista, seguro, tarjeta, campo, combo, segmentado, boton, etiqueta, crear_tabla, insertar, limpiar
)


ROLES_SISTEMA = ["Profesor", "Administración", "Directora"]
TURNOS = ["Mañana", "Tarde"]
GRADOS = ["1", "2", "3", "4", "5", "6"]


def mapear_rol_bd(rol_texto: str) -> str:
    """Convierte el nombre visual del rol a su valor ENUM en MySQL."""
    r = (rol_texto or "").strip().lower()
    if "profe" in r or "docente" in r:
        return "Docente"
    if "direct" in r:
        return "Directivo"
    if "control" in r or "porter" in r:
        return "Control"
    return "Administrador"


# ==============================================================================
# MODALES PARA SECCIONES
# ==============================================================================
class FormSeccion(ctk.CTkToplevel):
    def __init__(self, master, db, seccion=None, al_guardar=None):
        super().__init__(master, fg_color=BG)
        self.db = db
        self.seccion = seccion
        self.al_guardar = al_guardar

        self.title("Editar Sección" if seccion else "Nueva Sección Escolar")
        self.geometry("380x360")
        self.resizable(False, False)
        self.transient(master.winfo_toplevel())
        self.after(150, self.grab_set)

        ctk.CTkLabel(
            self,
            text="Nueva Sección" if not seccion else "Editar Sección",
            font=(F_TITULO, 20, "bold"), text_color=TEXTO
        ).pack(pady=(22, 14))

        form = ctk.CTkFrame(self, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=26)

        etiqueta(form, "Año / Grado Escolar (1° a 6°)").pack(anchor="w")
        self.cb_grado = combo(form, values=GRADOS)
        self.cb_grado.pack(fill="x", pady=(2, 10))

        etiqueta(form, "Letra de Sección (ej: A, B, C)").pack(anchor="w")
        self.e_letra = campo(form, placeholder_text="A")
        self.e_letra.pack(fill="x", pady=(2, 10))

        etiqueta(form, "Turno").pack(anchor="w")
        self.cb_turno = combo(form, values=TURNOS)
        self.cb_turno.pack(fill="x", pady=(2, 16))

        boton(self, "Guardar Sección", "primario", self.guardar, height=44).pack(fill="x", padx=26, pady=(0, 20))

        if seccion:
            self.cb_grado.set(str(seccion["grado_ano"]))
            self.e_letra.insert(0, seccion["seccion_letra"])
            self.cb_turno.set(seccion["turno"])
        else:
            self.cb_grado.set("1")
            self.e_letra.insert(0, "A")
            self.cb_turno.set("Mañana")

    @seguro
    def guardar(self):
        grado = int(self.cb_grado.get())
        letra = self.e_letra.get().strip().upper()
        turno = self.cb_turno.get()

        if not letra or len(letra) != 1 or not letra.isalpha():
            raise UserWarning("La letra de la sección debe ser una única letra del abecedario (A-Z).")

        if self.seccion:
            self.db.actualizar_seccion(self.seccion["id_seccion"], grado, letra, turno)
            msg = "Sección actualizada correctamente."
        else:
            self.db.crear_seccion(grado, letra, turno)
            msg = f"Sección {grado}° \"{letra}\" ({turno}) creada exitosamente."

        messagebox.showinfo("Éxito", msg)
        if self.al_guardar:
            self.al_guardar()
        self.destroy()


# ==============================================================================
# MODALES PARA USUARIOS
# ==============================================================================

# ==============================================================================
# MODALES PARA CURSOS Y COHORTES DEL INSTITUTO
# ==============================================================================
class FormCursoCatalogo(ctk.CTkToplevel):
    def __init__(self, master, db, curso=None, al_guardar=None):
        super().__init__(master, fg_color=BG)
        self.db = db
        self.curso = curso
        self.al_guardar = al_guardar

        self.title("Editar Especialidad" if curso else "Nueva Especialidad / Curso")
        self.geometry("450x500")
        self.resizable(False, False)
        self.transient(master.winfo_toplevel())
        self.after(150, self.grab_set)

        ctk.CTkLabel(
            self,
            text="Nueva Especialidad" if not curso else "Editar Especialidad",
            font=(F_TITULO, 20, "bold"), text_color=TEXTO
        ).pack(pady=(22, 14))

        form = ctk.CTkFrame(self, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=26)

        etiqueta(form, "Código de Curso (ej: CEL-201, ELEC-101)").pack(anchor="w")
        self.e_codigo = campo(form, placeholder_text="MEC-101")
        self.e_codigo.pack(fill="x", pady=(2, 10))

        etiqueta(form, "Nombre de la Especialidad / Curso").pack(anchor="w")
        self.e_nombre = campo(form, placeholder_text="Mecánica Automotriz")
        self.e_nombre.pack(fill="x", pady=(2, 10))

        etiqueta(form, "Duración en Semanas (3 meses = 12 semanas)").pack(anchor="w")
        self.e_duracion = campo(form, placeholder_text="12")
        self.e_duracion.pack(fill="x", pady=(2, 10))

        etiqueta(form, "Descripción o Temario General").pack(anchor="w")
        self.e_desc = campo(form, placeholder_text="Contenido general del curso...")
        self.e_desc.pack(fill="x", pady=(2, 16))

        boton(self, "Guardar Especialidad", "primario", self.guardar, height=44).pack(fill="x", padx=26, pady=(0, 20))

        if curso:
            self.e_codigo.insert(0, curso.get("codigo", ""))
            self.e_nombre.insert(0, curso.get("nombre", ""))
            self.e_duracion.insert(0, str(curso.get("duracion_semanas", 12)))
            self.e_desc.insert(0, curso.get("descripcion") or "")
        else:
            self.e_duracion.insert(0, "12")

    @seguro
    def guardar(self):
        codigo = self.e_codigo.get().strip().upper()
        nombre = self.e_nombre.get().strip()
        dur_str = self.e_duracion.get().strip() or "12"
        desc = self.e_desc.get().strip()

        if not codigo or not nombre:
            raise UserWarning("El código y el nombre del curso son obligatorios.")

        try:
            dur = int(dur_str)
        except ValueError:
            raise UserWarning("La duración en semanas debe ser un número entero.")

        if self.curso:
            self.db.actualizar_curso(self.curso["id_curso"], codigo, nombre, desc, dur, 1)
            msg = f"Especialidad '{nombre}' actualizada correctamente."
        else:
            self.db.crear_curso(codigo, nombre, desc, dur)
            msg = f"Especialidad '{nombre}' registrada con éxito."

        messagebox.showinfo("Éxito", msg)
        if self.al_guardar:
            self.al_guardar()
        self.destroy()


class FormCohorte(ctk.CTkToplevel):
    def __init__(self, master, db, cohorte=None, al_guardar=None):
        super().__init__(master, fg_color=BG)
        self.db = db
        self.cohorte = cohorte
        self.al_guardar = al_guardar

        self.title("Editar Horario de Curso" if cohorte else "Abrir Nuevo Curso / Cohorte")
        self.geometry("480x640")
        self.resizable(False, False)
        self.transient(master.winfo_toplevel())
        self.after(150, self.grab_set)

        ctk.CTkLabel(
            self,
            text="Abrir Nuevo Curso" if not cohorte else "Editar Horario de Curso",
            font=(F_TITULO, 20, "bold"), text_color=TEXTO
        ).pack(pady=(16, 8))

        form = ctk.CTkFrame(self, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=24)

        # Cursos disponibles
        self.cursos = self.db.listar_cursos(solo_activos=True)
        if not self.cursos:
            self.db.crear_curso("GEN-101", "Curso General de Capacitación", "", 12)
            self.cursos = self.db.listar_cursos(solo_activos=True)

        nombres_cursos = [f"{c['codigo']} - {c['nombre']}" for c in self.cursos]
        etiqueta(form, "Especialidad / Curso a Dictar").pack(anchor="w")
        self.cb_curso = combo(form, values=nombres_cursos)
        self.cb_curso.pack(fill="x", pady=(2, 6))

        # Periodos disponibles
        self.periodos = self.db.listar_periodos()
        if not self.periodos:
            self.db.crear_periodo("Trimestre 2026-I (Enero - Marzo)", "2026-T1", "2026-01-12", "2026-04-03", "Activo")
            self.periodos = self.db.listar_periodos()
        nombres_periodos = [f"{p['codigo']} · {p['nombre']}" for p in self.periodos]

        etiqueta(form, "Período / Trimestre Académico").pack(anchor="w")
        self.cb_periodo = combo(form, values=nombres_periodos)
        self.cb_periodo.pack(fill="x", pady=(2, 6))

        # Docente a cargo
        self.docentes = self.db.fetch_all("""
            SELECT p.id_persona, p.cedula, p.nombre, p.apellido
            FROM persona p
            LEFT JOIN personal pl ON pl.id_persona = p.id_persona
            WHERE p.tipo_persona = 'Personal' OR pl.cargo = 'Docente'
            ORDER BY p.apellido, p.nombre
        """)
        nombres_docentes = ["(Sin docente asignado)"] + [
            f"{d['cedula']} - {d['nombre']} {d['apellido']}" for d in self.docentes
        ]

        etiqueta(form, "Profesor a Cargo").pack(anchor="w")
        self.cb_docente = combo(form, values=nombres_docentes)
        self.cb_docente.pack(fill="x", pady=(2, 6))

        # Denominación de grupo
        etiqueta(form, "Denominación del Grupo (ej: Grupo Sábados Mañana)").pack(anchor="w")
        self.e_grupo = campo(form, placeholder_text="Grupo Sábados Mañana")
        self.e_grupo.pack(fill="x", pady=(2, 6))

        # Días
        etiqueta(form, "Días de Clase").pack(anchor="w")
        dias_opciones = ["Sábados", "Lunes y Miércoles", "Martes y Jueves", "Viernes", "Lunes a Viernes", "Domingos"]
        self.cb_dias = combo(form, values=dias_opciones)
        self.cb_dias.pack(fill="x", pady=(2, 6))

        # Fila Horarios
        f_horas = ctk.CTkFrame(form, fg_color="transparent")
        f_horas.pack(fill="x", pady=(2, 6))

        f_h_ini = ctk.CTkFrame(f_horas, fg_color="transparent")
        f_h_ini.pack(side="left", fill="x", expand=True, padx=(0, 6))
        etiqueta(f_h_ini, "Hora Inicio (HH:MM)").pack(anchor="w")
        self.e_h_ini = campo(f_h_ini, placeholder_text="08:00")
        self.e_h_ini.pack(fill="x", pady=(2, 0))

        f_h_fin = ctk.CTkFrame(f_horas, fg_color="transparent")
        f_h_fin.pack(side="left", fill="x", expand=True, padx=(6, 0))
        etiqueta(f_h_fin, "Hora Fin (HH:MM)").pack(anchor="w")
        self.e_h_fin = campo(f_h_fin, placeholder_text="12:00")
        self.e_h_fin.pack(fill="x", pady=(2, 0))

        # Fila Aula y Cupo
        f_aula = ctk.CTkFrame(form, fg_color="transparent")
        f_aula.pack(fill="x", pady=(2, 10))

        f_a_txt = ctk.CTkFrame(f_aula, fg_color="transparent")
        f_a_txt.pack(side="left", fill="x", expand=True, padx=(0, 6))
        etiqueta(f_a_txt, "Aula / Laboratorio").pack(anchor="w")
        self.e_aula = campo(f_a_txt, placeholder_text="Laboratorio 1")
        self.e_aula.pack(fill="x", pady=(2, 0))

        f_a_cupo = ctk.CTkFrame(f_aula, fg_color="transparent")
        f_a_cupo.pack(side="left", fill="x", expand=True, padx=(6, 0))
        etiqueta(f_a_cupo, "Cupo Máximo").pack(anchor="w")
        self.e_cupo = campo(f_a_cupo, placeholder_text="25")
        self.e_cupo.pack(fill="x", pady=(2, 0))

        boton(self, "Guardar Horario de Curso", "primario", self.guardar, height=44).pack(fill="x", padx=24, pady=(0, 16))

        if cohorte:
            for i, c in enumerate(self.cursos):
                if c["id_curso"] == cohorte["id_curso"]:
                    self.cb_curso.set(nombres_cursos[i])
                    break
            for i, p in enumerate(self.periodos):
                if p["id_periodo"] == cohorte["id_periodo"]:
                    self.cb_periodo.set(nombres_periodos[i])
                    break
            if cohorte.get("id_docente"):
                for i, d in enumerate(self.docentes):
                    if d["id_persona"] == cohorte["id_docente"]:
                        self.cb_docente.set(nombres_docentes[i + 1])
                        break
            self.e_grupo.insert(0, cohorte.get("nombre_grupo", ""))
            self.cb_dias.set(cohorte.get("dias_semana", "Sábados"))
            h_ini = str(cohorte.get("hora_inicio", "08:00"))[:5]
            self.e_h_ini.insert(0, h_ini)
            h_fin = str(cohorte.get("hora_fin", "12:00"))[:5]
            self.e_h_fin.insert(0, h_fin)
            self.e_aula.insert(0, cohorte.get("aula") or "Aula Principal")
            self.e_cupo.insert(0, str(cohorte.get("cupo_maximo", 30)))
        else:
            self.e_grupo.insert(0, "Grupo Sábados Mañana")
            self.cb_dias.set("Sábados")
            self.e_h_ini.insert(0, "08:00")
            self.e_h_fin.insert(0, "12:00")
            self.e_aula.insert(0, "Laboratorio 1")
            self.e_cupo.insert(0, "25")

    @seguro
    def guardar(self):
        sel_c = self.cb_curso.get()
        id_curso = None
        for i, nom in enumerate([f"{c['codigo']} - {c['nombre']}" for c in self.cursos]):
            if nom == sel_c:
                id_curso = self.cursos[i]["id_curso"]
                break

        sel_p = self.cb_periodo.get()
        id_periodo = None
        for i, nom in enumerate([f"{p['codigo']} · {p['nombre']}" for p in self.periodos]):
            if nom == sel_p:
                id_periodo = self.periodos[i]["id_periodo"]
                break

        sel_d = self.cb_docente.get()
        id_docente = None
        if sel_d != "(Sin docente asignado)":
            for d in self.docentes:
                if f"{d['cedula']} - {d['nombre']} {d['apellido']}" == sel_d:
                    id_docente = d["id_persona"]
                    break

        grupo = self.e_grupo.get().strip()
        dias = self.cb_dias.get().strip()
        h_ini = self.e_h_ini.get().strip()
        h_fin = self.e_h_fin.get().strip()
        aula = self.e_aula.get().strip() or "Aula Principal"
        cupo_s = self.e_cupo.get().strip() or "30"

        if not id_curso or not id_periodo:
            raise UserWarning("Debe seleccionar una especialidad y un período válidos.")
        if not grupo:
            raise UserWarning("La denominación del grupo es obligatoria.")

        try:
            cupo = int(cupo_s)
        except ValueError:
            cupo = 30

        if len(h_ini) == 5: h_ini += ":00"
        if len(h_fin) == 5: h_fin += ":00"

        if self.cohorte:
            self.db.actualizar_cohorte(self.cohorte["id_cohorte"], grupo, dias, h_ini, h_fin, aula, cupo, id_docente)
            msg = f"Horario del curso '{grupo}' actualizado correctamente."
        else:
            self.db.crear_cohorte(id_curso, id_periodo, id_docente, grupo, dias, h_ini, h_fin, aula, cupo)
            msg = f"Curso '{grupo}' abierto exitosamente en el sistema."

        messagebox.showinfo("Éxito", msg)
        if self.al_guardar:
            self.al_guardar()
        self.destroy()


class FormNuevoUsuario(ctk.CTkToplevel):
    def __init__(self, master, db, al_guardar=None):
        super().__init__(master, fg_color=BG)
        self.db = db
        self.al_guardar = al_guardar

        self.title("Crear Cuenta de Usuario")
        self.geometry("450x640")
        self.minsize(440, 580)
        self.resizable(False, False)
        self.transient(master.winfo_toplevel())
        self.after(150, self.grab_set)

        ctk.CTkLabel(self, text="Nueva Cuenta de Usuario", font=(F_TITULO, 20, "bold"), text_color=TEXTO).pack(pady=(18, 4))

        try:
            self.personal_disp = self.db.personal_sin_usuario()
        except Exception:
            self.personal_disp = []

        f_modo = ctk.CTkFrame(self, fg_color="transparent")
        f_modo.pack(fill="x", padx=26, pady=(8, 12))

        opciones_modo = ["Registrar Nuevo Personal"]
        if self.personal_disp:
            opciones_modo.insert(0, "Personal Existente")

        self.seg_modo = segmentado(
            f_modo,
            values=opciones_modo,
            command=self._cambiar_modo,
            height=34,
            font=(F_TEXTO, 11, "bold")
        )
        self.seg_modo.pack(fill="x")
        self.seg_modo.set(opciones_modo[0])

        self.form_container = ctk.CTkFrame(self, fg_color="transparent")
        self.form_container.pack(fill="both", expand=True, padx=26, pady=(0, 16))

        self._construir_formulario()

    def _cambiar_modo(self, _val=None):
        for widget in self.form_container.winfo_children():
            widget.destroy()
        self._construir_formulario()

    def _construir_formulario(self):
        modo = self.seg_modo.get()

        try:
            self.cohortes_disp = self.db.listar_cohortes(incluir_archivados=False)
        except Exception:
            self.cohortes_disp = []
        opciones_c = ["(Ninguno / No Asignado)"] + [f"{c['id_cohorte']} - {c['curso_nombre']} ({c['nombre_grupo']})" for c in self.cohortes_disp]

        if modo == "Personal Existente" and self.personal_disp:
            etiqueta(self.form_container, "Seleccionar Personal").pack(anchor="w")
            etiquetas_personal = [p["etiqueta"] for p in self.personal_disp]
            self.cb_personal = combo(self.form_container, values=etiquetas_personal)
            self.cb_personal.pack(fill="x", pady=(2, 10))
            self.cb_personal.set(etiquetas_personal[0])

            etiqueta(self.form_container, "Nombre de Usuario (Login)").pack(anchor="w")
            self.e_user = campo(self.form_container, placeholder_text="ej: prof.navarro")
            self.e_user.pack(fill="x", pady=(2, 10))

            etiqueta(self.form_container, "Rol en el Sistema").pack(anchor="w")
            self.cb_rol = combo(self.form_container, values=ROLES_SISTEMA)
            self.cb_rol.pack(fill="x", pady=(2, 10))
            self.cb_rol.set("Profesor")

            etiqueta(self.form_container, "Curso Sabatino Asignado (Para Profesores)").pack(anchor="w")
            self.cb_cohorte = combo(self.form_container, values=opciones_c)
            self.cb_cohorte.pack(fill="x", pady=(2, 10))
            self.cb_cohorte.set(opciones_c[0])

            etiqueta(self.form_container, "Contraseña Temporal Inicial (Fuerza cambio en 1er login)").pack(anchor="w")
            self.e_pass = campo(self.form_container, show="*", placeholder_text="Mínimo 8 car., Mayús, Núm, Símbolo")
            self.e_pass.pack(fill="x", pady=(2, 16))

        else:
            etiqueta(self.form_container, "Cédula de Identidad").pack(anchor="w")
            self.e_cedula = campo(self.form_container, placeholder_text="ej: 25111222", height=36)
            self.e_cedula.pack(fill="x", pady=(2, 8))

            f_nombres = ctk.CTkFrame(self.form_container, fg_color="transparent")
            f_nombres.pack(fill="x", pady=(0, 8))
            f_nombres.grid_columnconfigure(0, weight=1)
            f_nombres.grid_columnconfigure(1, weight=1)

            etiqueta(f_nombres, "Nombre").grid(row=0, column=0, sticky="w", padx=(0, 4))
            etiqueta(f_nombres, "Apellido").grid(row=0, column=1, sticky="w", padx=(4, 0))

            self.e_nombre = campo(f_nombres, placeholder_text="ej: Laura", height=36)
            self.e_nombre.grid(row=1, column=0, sticky="ew", padx=(0, 4))

            self.e_apellido = campo(f_nombres, placeholder_text="ej: Gómez", height=36)
            self.e_apellido.grid(row=1, column=1, sticky="ew", padx=(4, 0))

            f_cargos = ctk.CTkFrame(self.form_container, fg_color="transparent")
            f_cargos.pack(fill="x", pady=(0, 8))
            f_cargos.grid_columnconfigure(0, weight=1)
            f_cargos.grid_columnconfigure(1, weight=1)

            etiqueta(f_cargos, "Cargo Institucional").grid(row=0, column=0, sticky="w", padx=(0, 4))
            etiqueta(f_cargos, "Rol del Sistema").grid(row=0, column=1, sticky="w", padx=(4, 0))

            self.cb_cargo_nuevo = combo(f_cargos, values=["Docente", "Administrativo", "Directivo", "Vigilante", "Obrero"], height=36)
            self.cb_cargo_nuevo.grid(row=1, column=0, sticky="ew", padx=(0, 4))
            self.cb_cargo_nuevo.set("Docente")

            self.cb_rol = combo(f_cargos, values=ROLES_SISTEMA, height=36)
            self.cb_rol.grid(row=1, column=1, sticky="ew", padx=(4, 0))
            self.cb_rol.set("Profesor")

            etiqueta(self.form_container, "Curso Sabatino Asignado (Para Profesores)").pack(anchor="w")
            self.cb_cohorte = combo(self.form_container, values=opciones_c, height=36)
            self.cb_cohorte.pack(fill="x", pady=(2, 8))
            self.cb_cohorte.set(opciones_c[0])

            etiqueta(self.form_container, "Nombre de Usuario (Login)").pack(anchor="w")
            self.e_user = campo(self.form_container, placeholder_text="ej: laura.secretaria", height=36)
            self.e_user.pack(fill="x", pady=(2, 8))

            etiqueta(self.form_container, "Contraseña Temporal Inicial (Fuerza cambio en 1er login)").pack(anchor="w")
            self.e_pass = campo(self.form_container, show="*", placeholder_text="Mínimo 8 car., Mayús, Núm, Símbolo", height=36)
            self.e_pass.pack(fill="x", pady=(2, 16))

        boton(self.form_container, "Registrar Usuario", "primario", self.guardar, height=42).pack(fill="x")

    @seguro
    def guardar(self):
        user = self.e_user.get().strip()
        pwd = self.e_pass.get().strip()
        rol = self.cb_rol.get()
        modo = self.seg_modo.get()

        if not user:
            raise UserWarning("El nombre de usuario es obligatorio.")
        from config import validar_password_rigurosa
        valida, msg_pwd = validar_password_rigurosa(pwd)
        if not valida:
            raise UserWarning(f"Contraseña no cumple requisitos de seguridad:\n{msg_pwd}")

        hashed = bcrypt.hashpw(pwd.encode('utf-8'), bcrypt.gensalt(12)).decode('utf-8')
        rol_bd = mapear_rol_bd(rol)

        if modo == "Personal Existente" and self.personal_disp:
            sel_idx = self.cb_personal.cget("values").index(self.cb_personal.get())
            id_personal = self.personal_disp[sel_idx]["id_personal"]
            self.db.crear_usuario(id_personal, user, hashed, rol_bd)
            msg = f"Cuenta creada con éxito para {user} con rol {rol}."
        else:
            cedula = self.e_cedula.get().strip()
            nombre = self.e_nombre.get().strip()
            apellido = self.e_apellido.get().strip()
            cargo = self.cb_cargo_nuevo.get()

            if not cedula or not nombre or not apellido:
                raise UserWarning("Debe ingresar cédula, nombre y apellido del nuevo personal.")

            self.db.crear_personal_y_usuario(cedula, nombre, apellido, cargo, user, hashed, rol_bd)
            msg = f"Personal '{nombre} {apellido}' ({cargo}) y cuenta de usuario '{user}' creados con éxito."

        # Asignar cohorte sabatina si se seleccionó una
        sel_c = getattr(self, "cb_cohorte", None) and self.cb_cohorte.get()
        if sel_c and not sel_c.startswith("("):
            try:
                id_coh = int(sel_c.split("-")[0].strip())
                u_creado = self.db.fetch_one("""
                    SELECT pe.id_persona FROM usuario u
                    JOIN personal pe ON pe.id_personal = u.id_personal
                    WHERE u.username = %s
                """, (user,))
                if u_creado and u_creado.get("id_persona"):
                    self.db.execute("UPDATE cohorte SET id_docente = %s WHERE id_cohorte = %s", (u_creado["id_persona"], id_coh))
            except Exception as e_coh:
                print(f"Aviso asociando cohorte: {e_coh}")

        messagebox.showinfo("Usuario Creado", f"{msg}\n\nSe ha configurado la cuenta con 'Cambio obligatorio de contraseña' en su primer inicio de sesión.")
        if self.al_guardar:
            self.al_guardar()
        self.destroy()


class FormEditarUsuario(ctk.CTkToplevel):
    """Permite editar nombre de usuario, rol institucional, estado y curso sabatino asignado."""
    def __init__(self, master, db, usuario, al_guardar=None):
        super().__init__(master, fg_color=BG)
        self.db = db
        self.usuario = usuario
        self.al_guardar = al_guardar

        self.title("Editar Usuario")
        self.geometry("450x520")
        self.resizable(False, False)
        self.transient(master.winfo_toplevel())
        self.after(150, self.grab_set)

        ctk.CTkLabel(
            self,
            text=f"Editar Usuario: {usuario['username']}",
            font=(F_TITULO, 18, "bold"), text_color=TEXTO
        ).pack(pady=(20, 10))

        form = ctk.CTkFrame(self, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=26)

        etiqueta(form, "Personal Vinculado").pack(anchor="w")
        nom_p = usuario.get("nombre_persona") or "No asignado"
        ced_p = usuario.get("cedula") or ""
        lbl_p = f"{nom_p} (C.I. {ced_p})"
        e_p = campo(form)
        e_p.insert(0, lbl_p)
        e_p.configure(state="disabled")
        e_p.pack(fill="x", pady=(2, 10))

        etiqueta(form, "Nombre de Usuario (Login)").pack(anchor="w")
        self.e_user = campo(form)
        self.e_user.insert(0, usuario.get("username", ""))
        self.e_user.pack(fill="x", pady=(2, 10))

        etiqueta(form, "Rol en el Sistema").pack(anchor="w")
        self.cb_rol = combo(form, values=ROLES_SISTEMA)
        self.cb_rol.pack(fill="x", pady=(2, 10))

        rol_bd = usuario.get("rol_sistema", "Docente")
        if rol_bd == "Directivo":
            self.cb_rol.set("Directora")
        elif rol_bd == "Docente":
            self.cb_rol.set("Profesor")
        else:
            self.cb_rol.set("Administración")

        etiqueta(form, "Curso Sabatino Asignado (Para Profesores)").pack(anchor="w")
        try:
            self.cohortes = self.db.listar_cohortes(incluir_archivados=False)
        except Exception:
            self.cohortes = []
        opciones_c = ["(Ninguno / No Asignado)"] + [f"{c['id_cohorte']} - {c['curso_nombre']} ({c['nombre_grupo']})" for c in self.cohortes]
        self.cb_cohorte = combo(form, values=opciones_c)
        self.cb_cohorte.pack(fill="x", pady=(2, 10))
        self.cb_cohorte.set(opciones_c[0])

        id_pers = usuario.get("id_persona")
        if id_pers:
            for idx, c in enumerate(self.cohortes):
                if c.get("id_docente") == id_pers:
                    self.cb_cohorte.set(opciones_c[idx + 1])
                    break

        etiqueta(form, "Estado de la Cuenta").pack(anchor="w")
        self.cb_activo = combo(form, values=["Activo (Acceso Permitido)", "Inactivo (Bloqueado)"])
        self.cb_activo.pack(fill="x", pady=(2, 16))
        self.cb_activo.set("Activo (Acceso Permitido)" if usuario.get("activo") else "Inactivo (Bloqueado)")

        boton(self, "Guardar Cambios", "primario", self.guardar, height=42).pack(fill="x", padx=26, pady=(0, 20))

    @seguro
    def guardar(self):
        nuevo_user = self.e_user.get().strip()
        if not nuevo_user:
            raise UserWarning("El nombre de usuario no puede estar vacío.")

        nuevo_rol = mapear_rol_bd(self.cb_rol.get())
        activo = 1 if "Activo" in self.cb_activo.get() else 0

        sel_c = self.cb_cohorte.get()
        id_cohorte = None
        if sel_c and not sel_c.startswith("("):
            try:
                id_cohorte = int(sel_c.split("-")[0].strip())
            except Exception:
                id_cohorte = None

        self.db.actualizar_usuario_admin(
            self.usuario["id_usuario"], nuevo_user, nuevo_rol, activo=activo, id_cohorte=id_cohorte
        )
        messagebox.showinfo("Usuario Actualizado", f"Los datos de la cuenta '{nuevo_user}' se actualizaron correctamente.")
        if self.al_guardar:
            self.al_guardar()
        self.destroy()


class FormResetClave(ctk.CTkToplevel):
    def __init__(self, master, db, usuario, al_guardar=None):
        super().__init__(master, fg_color=BG)
        self.db = db
        self.usuario = usuario
        self.al_guardar = al_guardar

        self.title("Restablecer Contraseña")
        self.geometry("380x320")
        self.resizable(False, False)
        self.transient(master.winfo_toplevel())
        self.after(150, self.grab_set)

        ctk.CTkLabel(
            self,
            text=f"Restablecer clave:\n{usuario['username']}",
            font=(F_TITULO, 18, "bold"), text_color=TEXTO
        ).pack(pady=(18, 10))

        form = ctk.CTkFrame(self, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=26)

        etiqueta(form, "Nueva Contraseña Temporal").pack(anchor="w")
        self.e_p1 = campo(form, show="*")
        self.e_p1.pack(fill="x", pady=(2, 8))

        etiqueta(form, "Confirmar Nueva Contraseña").pack(anchor="w")
        self.e_p2 = campo(form, show="*")
        self.e_p2.pack(fill="x", pady=(2, 14))

        ctk.CTkLabel(
            form, text="* El usuario deberá cambiarla obligatoriamente al iniciar sesión.",
            font=(F_TEXTO, 10), text_color="#64748B"
        ).pack(anchor="w", pady=(0, 10))

        boton(self, "Actualizar Contraseña", "acento", self.guardar, height=42).pack(fill="x", padx=26, pady=(0, 20))

    @seguro
    def guardar(self):
        p1 = self.e_p1.get().strip()
        p2 = self.e_p2.get().strip()

        if p1 != p2:
            raise UserWarning("Las contraseñas ingresadas no coinciden.")
        from config import validar_password_rigurosa
        valida, msg_pwd = validar_password_rigurosa(p1)
        if not valida:
            raise UserWarning(f"Contraseña no cumple requisitos de seguridad:\n{msg_pwd}")

        hashed = bcrypt.hashpw(p1.encode('utf-8'), bcrypt.gensalt(12)).decode('utf-8')
        self.db.resetear_password_usuario(self.usuario["id_usuario"], hashed, forzar_cambio=True)

        messagebox.showinfo(
            "Éxito",
            f"Contraseña restablecida para '{self.usuario['username']}'.\n\nSe ha forzado el cambio obligatorio en su próximo inicio de sesión."
        )
        if self.al_guardar:
            self.al_guardar()
        self.destroy()
        self.db.cambiar_password_usuario(self.usuario["id_usuario"], hashed)

        messagebox.showinfo("Éxito", f"Contraseña actualizada para el usuario {self.usuario['username']}.")
        if self.al_guardar:
            self.al_guardar()
        self.destroy()


# ==============================================================================
# VISTA PRINCIPAL ADMINISTRATIVA
# ==============================================================================
class Administracion(Vista):
    def __init__(self, master, app):
        super().__init__(master, app)
        self.filas_sec = {}
        self.filas_usu = {}

        self.filas_respaldo = {}
        self.titulo(
            "Módulo de Administración del Sistema",
            "Gestión de aulas, cuentas de usuarios con permisos RBAC y respaldos de la base de datos"
        )

        # Selector de pestaña superior y botón de acción rápida
        barra_pestanas = ctk.CTkFrame(self, fg_color="transparent")
        barra_pestanas.pack(fill="x", padx=30, pady=(0, 14))

        pestanas_disp = [
            "Cursos y Horarios (Instituto)"
        ]
        if getattr(self.app, "es_duena", False):
            pestanas_disp.append("Cuentas de Usuario")
            pestanas_disp.append("📂 Respaldo Oculto (Dirección)")
        pestanas_disp.extend([
            "Respaldos BD (.sql)",
            "Horarios y Turnos",
            "Secciones (Escolares)"
        ])

        self.seg_pestana = segmentado(
            barra_pestanas,
            values=pestanas_disp,
            command=lambda v: self._cambiar_pestana(),
            height=40,
            font=(F_TEXTO, 11, "bold")
        )
        self.seg_pestana.set(pestanas_disp[0])
        self.seg_pestana.pack(fill="x", expand=True)

        # Contenedor dinámico de pestañas
        self.f_cursos = ctk.CTkFrame(self, fg_color="transparent")
        self.filas_cursos = {}
        self.f_secciones = ctk.CTkFrame(self, fg_color="transparent")
        self.f_usuarios = ctk.CTkFrame(self, fg_color="transparent")
        self.f_respaldo_usuarios = ctk.CTkFrame(self, fg_color="transparent")
        self.f_respaldo = ctk.CTkFrame(self, fg_color="transparent")
        self.f_horarios = ctk.CTkFrame(self, fg_color="transparent")

        self._armar_panel_cursos()
        self._armar_panel_secciones()
        if getattr(self.app, "es_duena", False):
            self._armar_panel_usuarios()
            self._armar_panel_respaldo_usuarios()
        self._armar_panel_respaldo()
        self._armar_panel_horarios()

        self._cambiar_pestana()

    def _cambiar_pestana(self):
        modo = self.seg_pestana.get()
        if hasattr(self, "f_cursos"):
            self.f_cursos.pack_forget()
        self.f_secciones.pack_forget()
        self.f_usuarios.pack_forget()
        if hasattr(self, "f_respaldo_usuarios"):
            self.f_respaldo_usuarios.pack_forget()
        self.f_respaldo.pack_forget()
        self.f_horarios.pack_forget()

        if "Cursos" in modo:
            self.f_cursos.pack(fill="both", expand=True, padx=30, pady=(0, 24))
            self.cargar_cursos_vista()
        elif "Secciones" in modo:
            self.f_secciones.pack(fill="both", expand=True, padx=30, pady=(0, 24))
            self.cargar_secciones()
        elif "Usuario" in modo and "Respaldo" not in modo:
            self.f_usuarios.pack(fill="both", expand=True, padx=30, pady=(0, 24))
            self.cargar_usuarios()
        elif "Respaldo Oculto" in modo or "Dueña" in modo:
            if hasattr(self, "f_respaldo_usuarios"):
                self.f_respaldo_usuarios.pack(fill="both", expand=True, padx=30, pady=(0, 24))
                self.cargar_usuarios_archivados()
        elif "BD" in modo or "Base de Datos" in modo or "sql" in modo:
            self.f_respaldo.pack(fill="both", expand=True, padx=30, pady=(0, 24))
            self.cargar_respaldos()
        else:
            self.f_horarios.pack(fill="both", expand=True, padx=30, pady=(0, 24))
            self.cargar_horarios()

    # --------------------------------------------------------------------------
    # PESTAÑA: CURSOS Y HORARIOS DEL INSTITUTO (GESTIÓN ACADÉMICA Y RESGUARDOS)
    # --------------------------------------------------------------------------
    def _armar_panel_cursos(self):
        barra = ctk.CTkFrame(self.f_cursos, fg_color="transparent")
        barra.pack(fill="x", pady=(0, 10))

        boton(barra, "+ Abrir Nuevo Curso", "acento", self.nuevo_curso_cohorte, width=170, height=42).pack(side="left", padx=(0, 8))
        boton(barra, "+ Especialidad", "suave", self.nueva_especialidad, width=145, height=42).pack(side="left", padx=(0, 8))
        boton(barra, "✏️ Editar Horario", "suave", self.editar_curso_cohorte, width=140, height=42).pack(side="left", padx=(0, 8))
        boton(barra, "🖹 Carnets del Curso", "suave", self.exportar_carnets_cohorte_seleccionada, width=175, height=42).pack(side="left", padx=(0, 8))
        boton(barra, "📁 Archivar / Egresar", "suave", self.archivar_curso_cohorte, width=165, height=42).pack(side="left", padx=(0, 8))
        boton(barra, "🔄 Reactivar", "suave", self.reactivar_curso_cohorte, width=120, height=42).pack(side="left")

        # Filtro segmentado para ver Activos vs Archivados (Respaldo) vs Catálogo
        f_filtro = ctk.CTkFrame(self.f_cursos, fg_color="transparent")
        f_filtro.pack(fill="x", pady=(0, 10))

        self.filtro_vista_cursos = segmentado(
            f_filtro,
            values=["🟢 Cursos Activos", "📁 Cursos Egresados / Histórico", "📚 Catálogo de Especialidades"],
            command=lambda v: self.cargar_cursos_vista(),
            height=38,
            font=(F_TEXTO, 11, "bold")
        )
        self.filtro_vista_cursos.set("🟢 Cursos Activos")
        self.filtro_vista_cursos.pack(side="left", fill="x", expand=True)

        t = tarjeta(self.f_cursos)
        t.pack(fill="both", expand=True)

        cont, self.t_cursos = crear_tabla(
            t,
            [
                ("codigo", "Código", 100),
                ("nombre", "Especialidad / Curso", 240),
                ("grupo", "Grupo / Turno", 160),
                ("dias", "Días de Clase", 140),
                ("horario", "Horario", 120),
                ("aula", "Aula / Taller", 130),
                ("docente", "Profesor a Cargo", 180),
                ("inscritos", "Inscritos / Cupo", 130),
                ("estado", "Estado", 120)
            ],
            14
        )
        cont.pack(fill="both", expand=True, padx=16, pady=16)
        self.t_cursos.bind("<Double-1>", lambda e: self.editar_curso_cohorte())

    @seguro
    def cargar_cursos_vista(self):
        modo_filtro = getattr(self, "filtro_vista_cursos", None)
        filtro = modo_filtro.get() if modo_filtro else "🟢 Cursos Activos"

        limpiar(self.t_cursos)
        self.filas_cursos = {}

        if "Catálogo" in filtro:
            cursos = self.db.listar_cursos()
            for c in cursos:
                iid = f"cur_{c['id_curso']}"
                self.filas_cursos[iid] = ("curso", c)
                estado_txt = "Disponible" if c.get("activo", 1) else "Oculto"
                insertar(
                    self.t_cursos,
                    (c["codigo"], c["nombre"], "-", f"{c.get('duracion_semanas', 12)} Semanas",
                     "-", "-", "-", "-", estado_txt),
                    iid=iid
                )
        elif "Egresados" in filtro or "Histórico" in filtro:
            cohortes = self.db.listar_cohortes(incluir_archivados=True)
            for co in cohortes:
                if co["estado"] in ("Finalizado", "Archivado"):
                    iid = f"coh_{co['id_cohorte']}"
                    self.filas_cursos[iid] = ("cohorte", co)
                    h_ini = str(co["hora_inicio"])[:5]
                    h_fin = str(co["hora_fin"])[:5]
                    horario_txt = f"{h_ini} - {h_fin}"
                    docente = co["docente_nombre"].strip() if co.get("docente_nombre") else "Sin asignar"
                    cupos_txt = f"{co['total_inscritos']} / {co['cupo_maximo']}"
                    insertar(
                        self.t_cursos,
                        (co["curso_codigo"], co["curso_nombre"], co["nombre_grupo"],
                         co["dias_semana"], horario_txt, co.get("aula", "Aula"), docente,
                         cupos_txt, f"📁 {co['estado']}"),
                        iid=iid
                    )
        else:
            cohortes = self.db.listar_cohortes(incluir_archivados=False)
            for co in cohortes:
                iid = f"coh_{co['id_cohorte']}"
                self.filas_cursos[iid] = ("cohorte", co)
                h_ini = str(co["hora_inicio"])[:5]
                h_fin = str(co["hora_fin"])[:5]
                horario_txt = f"{h_ini} - {h_fin}"
                docente = co["docente_nombre"].strip() if co.get("docente_nombre") else "Sin asignar"
                cupos_txt = f"{co['total_inscritos']} / {co['cupo_maximo']}"
                st_icon = "🟢" if co["estado"] == "En Curso" else "🔵"
                insertar(
                    self.t_cursos,
                    (co["curso_codigo"], co["curso_nombre"], co["nombre_grupo"],
                     co["dias_semana"], horario_txt, co.get("aula", "Aula"), docente,
                     cupos_txt, f"{st_icon} {co['estado']}"),
                    iid=iid
                )

    @seguro
    def nuevo_curso_cohorte(self):
        FormCohorte(self, self.db, None, self.cargar_cursos_vista)

    @seguro
    def nueva_especialidad(self):
        FormCursoCatalogo(self, self.db, None, self.cargar_cursos_vista)

    @seguro
    def editar_curso_cohorte(self):
        sel = self.t_cursos.selection()
        if not sel:
            raise UserWarning("Seleccione un registro de la tabla para editar.")
        tipo, obj = self.filas_cursos[sel[0]]
        if tipo == "cohorte":
            FormCohorte(self, self.db, obj, self.cargar_cursos_vista)
        else:
            FormCursoCatalogo(self, self.db, obj, self.cargar_cursos_vista)

    @seguro
    def archivar_curso_cohorte(self):
        sel = self.t_cursos.selection()
        if not sel:
            raise UserWarning("Seleccione un curso de la tabla para archivar.")
        tipo, obj = self.filas_cursos[sel[0]]
        if tipo != "cohorte":
            raise UserWarning("Seleccione un grupo o curso para archivar.")

        if not messagebox.askyesno(
            "Archivar Curso",
            f"¿Desea archivar y egresar el curso '{obj['curso_nombre']} - {obj['nombre_grupo']}'?\n\n"
            "- Se ocultará de la lista de asistencia activa del día a día.\n"
            "- Los alumnos matriculados pasarán al estado 'Egresado'.\n"
            "- Todo el historial de asistencias y notas se conservará intacto en los respaldos."
        ):
            return

        self.db.cambiar_estado_cohorte(obj["id_cohorte"], "Archivado")
        messagebox.showinfo("Curso Archivado", "El curso ha sido archivado exitosamente y resguardado en el histórico.")
        self.cargar_cursos_vista()

    @seguro
    def reactivar_curso_cohorte(self):
        sel = self.t_cursos.selection()
        if not sel:
            raise UserWarning("Seleccione un curso archivado para reactivar.")
        tipo, obj = self.filas_cursos[sel[0]]
        if tipo != "cohorte":
            raise UserWarning("Seleccione una cohorte de curso para reactivar.")

        self.db.cambiar_estado_cohorte(obj["id_cohorte"], "En Curso")
        messagebox.showinfo("Reactivado", "El curso está nuevamente activo para tomar asistencia.")
        self.cargar_cursos_vista()

    @seguro
    def exportar_carnets_cohorte_seleccionada(self):
        sel = self.t_cursos.selection()
        if not sel:
            raise UserWarning("Seleccione un curso o cohorte de la tabla para generar los carnets de sus participantes.")
        tipo, obj = self.filas_cursos[sel[0]]
        if tipo != "cohorte":
            raise UserWarning("Debe seleccionar una cohorte o grupo de curso para emitir carnets.")

        id_cohorte = obj["id_cohorte"]
        nom_curso = f"{obj.get('curso_nombre', 'Curso')}_{obj.get('nombre_grupo', '')}".replace(" ", "_").replace("/", "-")
        nom_archivo_sugerido = f"carnets_{nom_curso}.pdf"

        ruta_guardar = filedialog.asksaveasfilename(
            title=f"Guardar Carnets de {obj.get('curso_nombre', 'Curso')}",
            defaultextension=".pdf",
            filetypes=[("Documento PDF", "*.pdf")],
            initialfile=nom_archivo_sugerido
        )
        if not ruta_guardar:
            return

        try:
            from carnets import generar_carnets_cohorte
            ruta_pdf = generar_carnets_cohorte(self.db, id_cohorte, ruta_guardar)
            if messagebox.askyesno(
                "Carnets Generados",
                f"Se generaron los carnets de los participantes exitosamente en:\n{ruta_pdf}\n\n¿Desea abrir el archivo PDF ahora?"
            ):
                import webbrowser
                webbrowser.open(str(ruta_pdf))
        except Exception as e:
            raise UserWarning(f"No se pudieron generar los carnets: {e}")


    # --------------------------------------------------------------------------
    # PESTAÑA: SECCIONES ESCOLARES
    # --------------------------------------------------------------------------
    def _armar_panel_secciones(self):
        barra = ctk.CTkFrame(self.f_secciones, fg_color="transparent")
        barra.pack(fill="x", pady=(0, 10))

        boton(barra, "+ Nueva Sección", "acento", self.nueva_seccion, width=150, height=42).pack(side="left", padx=(0, 10))
        boton(barra, "Editar Sección", "suave", self.editar_seccion, width=130, height=42).pack(side="left", padx=(0, 10))
        boton(barra, "Eliminar Sección", "suave", self.eliminar_seccion, width=140, height=42).pack(side="left")

        t = tarjeta(self.f_secciones)
        t.pack(fill="both", expand=True)

        cont, self.t_sec = crear_tabla(
            t,
            [
                ("grado", "Año / Grado", 110),
                ("letra", "Letra", 90),
                ("turno", "Turno", 140),
                ("alumnos", "Estudiantes Matriculados", 190),
                ("etiqueta", "Denominación Oficial", 220)
            ],
            14
        )
        cont.pack(fill="both", expand=True, padx=16, pady=16)
        self.t_sec.bind("<Double-1>", lambda e: self.editar_seccion())

    @seguro
    def cargar_secciones(self):
        limpiar(self.t_sec)
        self.filas_sec = {}
        for r in self.db.listar_secciones_detalle():
            iid = str(r["id_seccion"])
            self.filas_sec[iid] = r
            insertar(
                self.t_sec,
                (f"{r['grado_ano']}° Año", f"Sección \"{r['seccion_letra']}\"", r["turno"], r["n_estudiantes"], r["etiqueta"]),
                iid=iid
            )

    @seguro
    def nueva_seccion(self):
        FormSeccion(self, self.db, None, self.cargar_secciones)

    @seguro
    def editar_seccion(self):
        sel = self.t_sec.selection()
        if not sel:
            raise UserWarning("Seleccione una sección de la tabla para editar.")
        sec = self.filas_sec[sel[0]]
        FormSeccion(self, self.db, sec, self.cargar_secciones)

    @seguro
    def eliminar_seccion(self):
        sel = self.t_sec.selection()
        if not sel:
            raise UserWarning("Seleccione una sección de la tabla para eliminar.")
        sec = self.filas_sec[sel[0]]

        if not messagebox.askyesno(
            "Confirmar Eliminación",
            f"¿Está seguro de eliminar la sección {sec['etiqueta']}?\nEsta acción no se puede deshacer."
        ):
            return

        self.db.eliminar_seccion(sec["id_seccion"])
        messagebox.showinfo("Sección Eliminada", f"La sección {sec['etiqueta']} ha sido eliminada.")
        self.cargar_secciones()

    # --------------------------------------------------------------------------
    # PESTAÑA: CUENTAS DE USUARIO
    # --------------------------------------------------------------------------
    def _armar_panel_usuarios(self):
        barra = ctk.CTkFrame(self.f_usuarios, fg_color="transparent")
        barra.pack(fill="x", pady=(0, 10))

        boton(barra, "+ Nuevo Usuario", "acento", self.nuevo_usuario, width=140, height=42).pack(side="left", padx=(0, 8))
        boton(barra, "✏ Editar", "suave", self.editar_usuario, width=100, height=42).pack(side="left", padx=(0, 8))
        boton(barra, "🔑 Reset Clave", "suave", self.reset_clave, width=120, height=42).pack(side="left", padx=(0, 8))
        boton(barra, "⚡ Activar / Desactivar", "suave", self.toggle_estado_usuario, width=160, height=42).pack(side="left", padx=(0, 8))
        boton(barra, "🗑  Dar de Baja", "primario", self.dar_baja_usuario, width=130, height=42).pack(side="left")

        t = tarjeta(self.f_usuarios)
        t.pack(fill="both", expand=True)

        cont, self.t_usu = crear_tabla(
            t,
            [
                ("user", "Username", 120),
                ("persona", "Nombre del Personal", 200),
                ("ced", "C.I.", 100),
                ("cargo", "Cargo", 130),
                ("rol", "Rol de Sistema", 130),
                ("activo", "Estado", 100),
                ("ultimo", "Último Acceso", 150)
            ],
            14
        )
        cont.pack(fill="both", expand=True, padx=16, pady=16)

    @seguro
    def cargar_usuarios(self):
        limpiar(self.t_usu)
        self.filas_usu = {}
        for r in self.db.listar_usuarios():
            iid = str(r["id_usuario"])
            self.filas_usu[iid] = r
            estado_txt = "Activo" if r["activo"] else "Inactivo"
            ult_str = r["ultimo_ingreso"].strftime("%d/%m/%Y %H:%M") if r["ultimo_ingreso"] else "Sin ingresos"
            
            rol_bd = r.get("rol_sistema", "")
            if r.get("es_duena") or rol_bd in ("Directivo", "Directiva"):
                rol_vis = "Directora"
            elif rol_bd in ("Docente", "Profesor"):
                rol_vis = "Profesor"
            elif rol_bd in ("Administrador", "Administración"):
                rol_vis = "Administración"
            else:
                rol_vis = rol_bd or "Control"

            insertar(
                self.t_usu,
                (r["username"], r["nombre_persona"], r["cedula"], r["cargo"], rol_vis, estado_txt, ult_str),
                tags=(rol_vis,),
                iid=iid
            )

    @seguro
    def nuevo_usuario(self):
        FormNuevoUsuario(self, self.db, self.cargar_usuarios)

    @seguro
    def editar_usuario(self):
        sel = self.t_usu.selection()
        if not sel:
            raise UserWarning("Seleccione un usuario de la tabla para editar.")
        usu = self.filas_usu[sel[0]]
        FormEditarUsuario(self, self.db, usu, self.cargar_usuarios)

    @seguro
    def toggle_estado_usuario(self):
        sel = self.t_usu.selection()
        if not sel:
            raise UserWarning("Seleccione un usuario de la tabla.")
        usu = self.filas_usu[sel[0]]
        if usu.get("es_duena"):
            raise UserWarning("No se puede desactivar la cuenta principal de la Directora.")

        nuevo_estado = 0 if usu["activo"] else 1
        estado_txt = "activar" if nuevo_estado == 1 else "desactivar y bloquear"
        if not messagebox.askyesno(
            "Confirmar Estado de Usuario",
            f"¿Desea {estado_txt} la cuenta de '{usu['username']}'?"
        ):
            return

        self.db.cambiar_estado_usuario(usu["id_usuario"], nuevo_estado)
        acc_txt = "activada" if nuevo_estado == 1 else "desactivada/bloqueada"
        messagebox.showinfo("Estado Actualizado", f"La cuenta de '{usu['username']}' ha sido {acc_txt}.")
        self.cargar_usuarios()

    @seguro
    def reset_clave(self):
        sel = self.t_usu.selection()
        if not sel:
            raise UserWarning("Seleccione un usuario de la tabla.")
        usu = self.filas_usu[sel[0]]
        FormResetClave(self, self.db, usu, self.cargar_usuarios)

    @seguro
    def cambiar_rol(self):
        sel = self.t_usu.selection()
        if not sel:
            raise UserWarning("Seleccione un usuario de la tabla.")
        usu = self.filas_usu[sel[0]]

        # Preguntar nuevo rol mediante un diálogo rápido
        dlg = ctk.CTkInputDialog(
            text=f"Usuario: {usu['username']}\nRol actual: {usu['rol_sistema']}\n\nEscriba el nuevo rol:\n(Administrador, Directivo, Docente, Control)",
            title="Cambiar Rol de Acceso"
        )
        nuevo_rol = dlg.get_input()
        if not nuevo_rol:
            return

        nuevo_rol = nuevo_rol.strip().capitalize()
        if nuevo_rol not in ROLES_SISTEMA:
            raise UserWarning(f"Rol no válido. Opciones permitidas: {', '.join(ROLES_SISTEMA)}")

        self.db.cambiar_rol_usuario(usu["id_usuario"], nuevo_rol)
        messagebox.showinfo("Rol Actualizado", f"El usuario {usu['username']} ahora tiene el rol: {nuevo_rol}.")
        self.cargar_usuarios()

    @seguro
    def dar_baja_usuario(self):
        sel = self.t_usu.selection()
        if not sel:
            raise UserWarning("Seleccione un usuario de la tabla.")
        usu = self.filas_usu[sel[0]]

        if not getattr(self.app, "es_duena", False):
            messagebox.showwarning(
                "Acceso Restringido (Seguridad Jerárquica)",
                "Solo la Directiva del plantel posee la autorización para dar de baja o desvincular cuentas de usuario.\nLos administradores estándar no tienen este privilegio."
            )
            return

        if usu.get("es_duena"):
            raise UserWarning("La cuenta principal de la Directiva / Propietaria no puede ser dada de baja.")

        dlg = ctk.CTkInputDialog(
            text=f"¿Está segura de dar de baja la cuenta de '{usu['username']}'?\n\n"
                 f"Esta cuenta NO se destruirá físicamente, sino que se trasladará\n"
                 f"al Respaldo Oculto de Dirección.\n\n"
                 f"Ingrese el motivo de la baja (ej: Fin de contrato, Renuncia):",
            title="Dar de Baja a Usuario"
        )
        motivo = dlg.get_input()
        if not motivo or not motivo.strip():
            return

        operador = getattr(self.app, "usuario_actual", {}).get("username", "Dueña")
        ruta_resp = self.db.dar_baja_usuario(usu["id_usuario"], motivo.strip(), operador)
        messagebox.showinfo(
            "Usuario Archivado con Éxito",
            f"El usuario '{usu['username']}' ha sido desvinculado del acceso activo.\n\n"
            f"Expediente protegido resguardado en:\n{ruta_resp}"
        )
        self.cargar_usuarios()
        if hasattr(self, "cargar_usuarios_archivados"):
            self.cargar_usuarios_archivados()

    # --------------------------------------------------------------------------
    # PESTAÑA OCULTA: RESGUARDO DE USUARIOS (EXCLUSIVO DE LA DUEÑA)
    # --------------------------------------------------------------------------
    def _armar_panel_respaldo_usuarios(self):
        barra = ctk.CTkFrame(self.f_respaldo_usuarios, fg_color="transparent")
        barra.pack(fill="x", pady=(0, 10))

        boton(barra, "↺  Reactivar Cuenta", "acento", self.reactivar_usuario, width=170, height=42).pack(side="left", padx=(0, 10))
        boton(barra, "📂  Abrir Carpeta Oculta", "suave", self.abrir_carpeta_respaldo_usuarios, width=220, height=42).pack(side="left", padx=(0, 10))
        boton(barra, "🔄  Refrescar", "suave", self.cargar_usuarios_archivados, width=120, height=42).pack(side="left")

        t_aviso = tarjeta(self.f_respaldo_usuarios)
        t_aviso.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(
            t_aviso,
            text="🔒 MÓDULO PRIVADO Y RESERVADO: DIRECCIÓN GENERAL DEL PLANTEL\n"
                 "Los usuarios en esta sección han sido dados de baja (secretarias o docentes desvinculados).\n"
                 "Sus expedientes están resguardados en respaldo seguro y ningún otro administrador tiene acceso a esta sección.",
            font=(F_TEXTO, 11, "bold"),
            text_color="#6D28D9",
            justify="left"
        ).pack(padx=18, pady=10, anchor="w")

        t = tarjeta(self.f_respaldo_usuarios)
        t.pack(fill="both", expand=True)

        cont, self.t_usu_arch = crear_tabla(
            t,
            [
                ("user", "Username", 120),
                ("persona", "Nombre del Personal", 180),
                ("ced", "C.I.", 100),
                ("cargo", "Cargo", 120),
                ("rol", "Rol Asignado", 120),
                ("fecha", "Fecha de Baja", 150),
                ("motivo", "Motivo de Desvinculación", 250)
            ],
            14
        )
        cont.pack(fill="both", expand=True, padx=16, pady=16)

    @seguro
    def cargar_usuarios_archivados(self):
        if not hasattr(self, "t_usu_arch"):
            return
        limpiar(self.t_usu_arch)
        self.filas_usu_arch = {}
        for r in self.db.listar_usuarios_archivados():
            iid = str(r["id_usuario"])
            self.filas_usu_arch[iid] = r
            f_str = r["fecha_baja"].strftime("%d/%m/%Y %H:%M") if r.get("fecha_baja") else "—"
            insertar(
                self.t_usu_arch,
                (r["username"], r["nombre_persona"], r["cedula"], r["cargo"], r["rol_sistema"], f_str, r.get("motivo_baja") or "—"),
                iid=iid
            )

    @seguro
    def reactivar_usuario(self):
        sel = self.t_usu_arch.selection()
        if not sel:
            raise UserWarning("Seleccione un usuario de la lista de archivados para restaurar su acceso.")
        usu = self.filas_usu_arch[sel[0]]

        if not messagebox.askyesno("Confirmar Restauración", f"¿Desea restaurar y reactivar el acceso para el usuario '{usu['username']}'?"):
            return

        self.db.reactivar_usuario(usu["id_usuario"])
        messagebox.showinfo("Usuario Reactivado", f"La cuenta de '{usu['username']}' ha sido reactivada exitosamente.")
        self.cargar_usuarios_archivados()
        self.cargar_usuarios()

    def abrir_carpeta_respaldo_usuarios(self):
        import config
        import subprocess
        p = config.BASE_DIR / "respaldos" / "usuarios_archivados"
        p.mkdir(parents=True, exist_ok=True)
        try:
            if os.name == 'nt':
                os.startfile(p)
            else:
                subprocess.Popen(["xdg-open", str(p)])
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir la carpeta: {e}")


    # --------------------------------------------------------------------------
    # PESTAÑA: RESPALDO DE BASE DE DATOS (mysqldump)
    # --------------------------------------------------------------------------
    def _armar_panel_respaldo(self):
        barra = ctk.CTkFrame(self.f_respaldo, fg_color="transparent")
        barra.pack(fill="x", pady=(0, 12))

        boton(barra, "💾  Generar Respaldo Ahora (.sql)", "acento", self.generar_respaldo, width=250, height=42).pack(side="left", padx=(0, 10))
        boton(barra, "↺  Restaurar Respaldo (.sql)", "primario", self.restaurar_respaldo, width=210, height=42).pack(side="left", padx=(0, 10))
        boton(barra, "📂  Abrir Carpeta", "suave", self.abrir_carpeta_respaldos, width=160, height=42).pack(side="left", padx=(0, 10))
        boton(barra, "🔄  Refrescar", "suave", self.cargar_respaldos, width=120, height=42).pack(side="left")

        # Ficha técnica informativa
        t_info = tarjeta(self.f_respaldo)
        t_info.pack(fill="x", pady=(0, 14))

        f_grid = ctk.CTkFrame(t_info, fg_color="transparent")
        f_grid.pack(fill="x", padx=18, pady=12)

        datos_bd = [
            ("Motor de Base de Datos:", "SQLite 3 (Portable / Autónomo)"),
            ("Archivo de Datos:", str(getattr(self.db, "db_path", config.DB_PATH).name)),
            ("Ubicación:", str(getattr(self.db, "db_path", config.DB_PATH))),
            ("Estado:", "Conectado localmente (Sin requerir servidor MySQL ni XAMPP)")
        ]

        for i, (k, v) in enumerate(datos_bd):
            row = i // 2
            col = (i % 2) * 2
            ctk.CTkLabel(f_grid, text=k, font=(F_TEXTO, 11, "bold"), text_color=TEXTO).grid(row=row, column=col, sticky="w", padx=(0, 8), pady=3)
            ctk.CTkLabel(f_grid, text=v, font=(F_TEXTO, 11), text_color=SUAVE).grid(row=row, column=col + 1, sticky="w", padx=(0, 24), pady=3)

        # Tarjeta con la tabla de historial de respaldos
        t_tabla = tarjeta(self.f_respaldo)
        t_tabla.pack(fill="both", expand=True)

        ctk.CTkLabel(
            t_tabla,
            text="Copias de Seguridad Disponibles (.sql)",
            font=(F_TITULO, 15, "bold"),
            text_color=TEXTO,
            anchor="w"
        ).pack(fill="x", padx=18, pady=(14, 4))

        cont, self.t_respaldo = crear_tabla(
            t_tabla,
            [
                ("archivo", "Nombre del Archivo .sql", 280),
                ("fecha", "Fecha y Hora de Generación", 180),
                ("tamano", "Tamaño", 120),
                ("ruta", "Ruta en Disco", 360)
            ],
            12
        )
        cont.pack(fill="both", expand=True, padx=16, pady=14)

    @seguro
    def generar_respaldo(self):
        carpeta_defecto = config.BASE_DIR / "backups"
        carpeta_defecto.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_defecto = f"respaldo_registra_db_{timestamp}.sql"

        ruta_guardar = filedialog.asksaveasfilename(
            initialdir=str(carpeta_defecto),
            initialfile=nombre_defecto,
            defaultextension=".sql",
            filetypes=[("Archivo SQL (*.sql)", "*.sql"), ("Todos los archivos", "*.*")],
            title="Guardar Respaldo de Base de Datos (mysqldump)"
        )
        if not ruta_guardar:
            return

        res = self.db.generar_respaldo_sql(ruta_guardar)
        msg = (
            f'¡Copia de seguridad generada con éxito!\n\n'
            f'• Archivo: {res["nombre"]}\n'
            f'• Tamaño: {res["tamano_kb"]} KB ({res["tamano_mb"]} MB)\n'
            f'• Ubicación: {res["archivo"]}\n\n'
            f'Base de datos: {self.db.cfg.get("database")}\n'
            'Incluye tablas, vistas, procedimientos almacenados y triggers.'
        )
        messagebox.showinfo("Respaldo Exitoso", msg)
        self.cargar_respaldos()

    @seguro
    def abrir_carpeta_respaldos(self):
        try:
            carpeta = config.BASE_DIR / "backups"
            carpeta.mkdir(parents=True, exist_ok=True)
            if os.name == "nt":
                os.startfile(str(carpeta))
            else:
                import subprocess
                subprocess.Popen(["xdg-open", str(carpeta)])
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir la carpeta de respaldos: {e}")

    @seguro
    def restaurar_respaldo(self):
        sel = self.t_respaldo.selection()
        if sel:
            r = self.filas_respaldo[sel[0]]
            ruta = r["ruta"]
            nombre = r["nombre"]
        else:
            carpeta_defecto = config.BASE_DIR / "backups"
            ruta = filedialog.askopenfilename(
                initialdir=str(carpeta_defecto),
                filetypes=[("Archivo SQL (*.sql)", "*.sql"), ("Todos los archivos", "*.*")],
                title="Seleccionar archivo de respaldo .sql a restaurar"
            )
            if not ruta:
                return
            nombre = os.path.basename(ruta)

        if not messagebox.askyesno(
            "Confirmar Restauración de Base de Datos",
            f"¿Está seguro de que desea restaurar la base de datos desde el archivo:\n\n{nombre}?\n\n"
            "⚠️ ATENCIÓN: Esta acción reemplazará los datos actuales por los contenidos en la copia de seguridad."
        ):
            return

        self.db.restaurar_respaldo_sql(ruta)
        messagebox.showinfo(
            "Restauración Exitosa",
            f"¡La base de datos ha sido restaurada con éxito desde:\n\n{nombre}!"
        )
        self.cargar_respaldos()
        if hasattr(self, "cargar_secciones"):
            self.cargar_secciones()

    def cargar_respaldos(self):
        limpiar(self.t_respaldo)
        self.filas_respaldo = {}
        respaldos = self.db.listar_respaldos()
        for r in respaldos:
            iid = r["nombre"]
            self.filas_respaldo[iid] = r
            f_str = r["fecha"].strftime("%d/%m/%Y %H:%M:%S")
            insertar(
                self.t_respaldo,
                (r["nombre"], f_str, f"{r['tamano_kb']:.2f} KB", r["ruta"]),
                iid=iid
            )


    # --------------------------------------------------------------------------
    # PESTAÑA: HORARIOS INSTITUCIONALES Y PARÁMETROS
    # --------------------------------------------------------------------------
    def _armar_panel_horarios(self):
        # Contenedor de 2 columnas para Mañana y Tarde
        fila_turnos = ctk.CTkFrame(self.f_horarios, fg_color="transparent")
        fila_turnos.pack(fill="x", pady=(0, 14))
        fila_turnos.grid_columnconfigure(0, weight=1, uniform="turno")
        fila_turnos.grid_columnconfigure(1, weight=1, uniform="turno")

        # Tarjeta Mañana
        t_manana = tarjeta(fila_turnos)
        t_manana.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        ctk.CTkLabel(
            t_manana,
            text="🌅  Turno Mañana (Matutino)",
            font=(F_TITULO, 16, "bold"),
            text_color=TEXTO,
            anchor="w"
        ).pack(fill="x", padx=18, pady=(16, 4))
        etiqueta(t_manana, "Horarios para secciones y personal matutino").pack(anchor="w", padx=18, pady=(0, 12))

        etiqueta(t_manana, "Hora Límite de Entrada (HH:MM)").pack(anchor="w", padx=18)
        self.e_ent_m = campo(t_manana, placeholder_text="07:15")
        self.e_ent_m.pack(fill="x", padx=18, pady=(2, 6))
        etiqueta(t_manana, "💡 Pasada esta hora se computa como Retraso.", font=(F_TEXTO, 10)).pack(anchor="w", padx=18, pady=(0, 10))

        etiqueta(t_manana, "Hora Mínima de Salida (HH:MM)").pack(anchor="w", padx=18)
        self.e_sal_m = campo(t_manana, placeholder_text="12:00")
        self.e_sal_m.pack(fill="x", padx=18, pady=(2, 6))
        etiqueta(t_manana, "💡 Antes de esta hora se computa como Salida Temprana.", font=(F_TEXTO, 10)).pack(anchor="w", padx=18, pady=(0, 16))

        # Tarjeta Tarde
        t_tarde = tarjeta(fila_turnos)
        t_tarde.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        ctk.CTkLabel(
            t_tarde,
            text="🌇  Turno Tarde (Vespertino)",
            font=(F_TITULO, 16, "bold"),
            text_color=TEXTO,
            anchor="w"
        ).pack(fill="x", padx=18, pady=(16, 4))
        etiqueta(t_tarde, "Horarios para secciones y personal vespertino").pack(anchor="w", padx=18, pady=(0, 12))

        etiqueta(t_tarde, "Hora Límite de Entrada (HH:MM)").pack(anchor="w", padx=18)
        self.e_ent_t = campo(t_tarde, placeholder_text="12:45")
        self.e_ent_t.pack(fill="x", padx=18, pady=(2, 6))
        etiqueta(t_tarde, "💡 Pasada esta hora se computa como Retraso.", font=(F_TEXTO, 10)).pack(anchor="w", padx=18, pady=(0, 10))

        etiqueta(t_tarde, "Hora Mínima de Salida (HH:MM)").pack(anchor="w", padx=18)
        self.e_sal_t = campo(t_tarde, placeholder_text="17:30")
        self.e_sal_t.pack(fill="x", padx=18, pady=(2, 6))
        etiqueta(t_tarde, "💡 Antes de esta hora se computa como Salida Temprana.", font=(F_TEXTO, 10)).pack(anchor="w", padx=18, pady=(0, 16))

        # Tarjeta Institucional
        t_inst = tarjeta(self.f_horarios)
        t_inst.pack(fill="x", pady=(0, 16))

        ctk.CTkLabel(
            t_inst,
            text="🏫  Datos de Identidad Institucional y Tolerancia",
            font=(F_TITULO, 15, "bold"),
            text_color=TEXTO,
            anchor="w"
        ).pack(fill="x", padx=18, pady=(14, 10))

        f_inst_grid = ctk.CTkFrame(t_inst, fg_color="transparent")
        f_inst_grid.pack(fill="x", padx=18, pady=(0, 14))
        f_inst_grid.grid_columnconfigure(0, weight=3)
        f_inst_grid.grid_columnconfigure(1, weight=1)

        f_nombre = ctk.CTkFrame(f_inst_grid, fg_color="transparent")
        f_nombre.grid(row=0, column=0, sticky="ew", padx=(0, 12))
        etiqueta(f_nombre, "Nombre Oficial del Plantel Educativo").pack(anchor="w")
        self.e_nom_inst = campo(f_nombre, placeholder_text="Unidad Educativa...")
        self.e_nom_inst.pack(fill="x", pady=(2, 0))

        f_tol = ctk.CTkFrame(f_inst_grid, fg_color="transparent")
        f_tol.grid(row=0, column=1, sticky="ew")
        etiqueta(f_tol, "Tolerancia / Cortesía (Minutos)").pack(anchor="w")
        self.e_tol = campo(f_tol, placeholder_text="15")
        self.e_tol.pack(fill="x", pady=(2, 0))

        # Barra de botones de acción
        barra_btn = ctk.CTkFrame(self.f_horarios, fg_color="transparent")
        barra_btn.pack(fill="x")
        boton(barra_btn, "💾  Guardar Configuración de Horarios", "acento", self.guardar_horarios, width=280, height=44).pack(side="left", padx=(0, 12))
        boton(barra_btn, "🔄  Recargar Valores", "suave", self.cargar_horarios, width=170, height=44).pack(side="left")

    @seguro
    def cargar_horarios(self):
        cfg = self.db.cargar_configuracion_institucional()
        m = cfg.get("Mañana", {})
        t = cfg.get("Tarde", {})

        self.e_ent_m.delete(0, "end")
        self.e_ent_m.insert(0, m.get("str_entrada", "07:15"))

        self.e_sal_m.delete(0, "end")
        self.e_sal_m.insert(0, m.get("str_salida", "12:00"))

        self.e_ent_t.delete(0, "end")
        self.e_ent_t.insert(0, t.get("str_entrada", "12:45"))

        self.e_sal_t.delete(0, "end")
        self.e_sal_t.insert(0, t.get("str_salida", "17:30"))

        self.e_nom_inst.delete(0, "end")
        self.e_nom_inst.insert(0, cfg.get("institucion", "Unidad Educativa Prof. Aristóbulo Istúriz"))

        self.e_tol.delete(0, "end")
        self.e_tol.insert(0, str(cfg.get("tolerancia_minutos", 15)))

    @seguro
    def guardar_horarios(self):
        import re
        from datetime import time

        ent_m = self.e_ent_m.get().strip()
        sal_m = self.e_sal_m.get().strip()
        ent_t = self.e_ent_t.get().strip()
        sal_t = self.e_sal_t.get().strip()
        nom_inst = self.e_nom_inst.get().strip()
        tol_str = self.e_tol.get().strip()

        # Validaciones de formato HH:MM
        fmt_regex = r"^([01]?\d|2[0-3]):[0-5]\d$"
        for nombre_campo, valor in [
            ("Entrada Mañana", ent_m),
            ("Salida Mañana", sal_m),
            ("Entrada Tarde", ent_t),
            ("Salida Tarde", sal_t)
        ]:
            if not re.match(fmt_regex, valor):
                raise UserWarning(f"El campo '{nombre_campo}' debe tener formato de hora HH:MM válido (ej: 07:15).")

        def _to_time(s):
            h, m = map(int, s.split(":"))
            return time(h, m)

        if _to_time(ent_m) >= _to_time(sal_m):
            raise UserWarning("En el Turno Mañana, la hora de entrada debe ser anterior a la hora de salida.")

        if _to_time(ent_t) >= _to_time(sal_t):
            raise UserWarning("En el Turno Tarde, la hora de entrada debe ser anterior a la hora de salida.")

        try:
            tol_int = int(tol_str)
            if tol_int < 0 or tol_int > 60:
                raise ValueError()
        except Exception:
            raise UserWarning("El margen de tolerancia debe ser un número entero entre 0 y 60 minutos.")

        self.db.guardar_configuracion_institucional(ent_m, sal_m, ent_t, sal_t, nom_inst, tol_int)

        msg = (
            "¡Configuración de Horarios guardada con éxito!\n\n"
            f"• 🌅 Turno Mañana: Entrada hasta {ent_m} | Salida {sal_m}\n"
            f"• 🌇 Turno Tarde: Entrada hasta {ent_t} | Salida {sal_t}\n"
            f"• 🏫 Institución: {nom_inst}\n\n"
            "Los nuevos parámetros ya se encuentran activos en el módulo de Marcaje."
        )
        messagebox.showinfo("Configuración Actualizada", msg)
        self.cargar_horarios()

    def refrescar(self):
        self._cambiar_pestana()
