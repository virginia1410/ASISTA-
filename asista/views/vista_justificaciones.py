"""Módulo Justificaciones y Cierres: Gestión de motivos de faltas, cierres diarios y consolidación mensual."""
import os
import shutil
import subprocess
import sys
from datetime import date, datetime
from tkinter import filedialog, messagebox
import customtkinter as ctk

import config
from config import MESES
from tema import BG, BORDE, F_TEXTO, F_TITULO, OK, PRIMARIO, PRIMARIO_H, ACENTO, ACENTO_H, TEXTO, SUAVE, CARD
from .ui_utils import (
    Vista, seguro, tarjeta, campo, combo, segmentado, boton, etiqueta, area, crear_tabla, insertar, limpiar
)
from .componentes import asociar_boton_calendario, DialogoSelectorFecha


class DialogoClaveCierre(ctk.CTkToplevel):
    def __init__(self, master, db, id_usuario, periodo_txt, on_autorizado):
        super().__init__(master, fg_color=BG)
        self.db = db
        self.id_usuario = id_usuario
        self.on_autorizado = on_autorizado
        self.title("Confirmación de Seguridad")
        self.geometry("400x260")
        self.resizable(False, False)
        self.transient(master.winfo_toplevel())
        self.after(150, self.grab_set)

        ctk.CTkLabel(self, text="🔒 Autorización de Cierre", font=(F_TITULO, 18, "bold"), text_color=TEXTO).pack(pady=(22, 6))
        ctk.CTkLabel(
            self,
            text=f"Ingrese su contraseña institucional para autorizar\ny consolidar el cierre mensual de {periodo_txt}:",
            font=(F_TEXTO, 11),
            text_color=TEXTO,
            justify="center"
        ).pack(pady=(0, 14))

        self.e_pass = campo(self, show="*", placeholder_text="Contraseña de usuario")
        self.e_pass.pack(fill="x", padx=32, pady=(0, 16))
        self.e_pass.bind("<Return>", lambda e: self.verificar())

        boton(self, "Confirmar y Ejecutar Cierre", "acento", self.verificar, height=42).pack(fill="x", padx=32)

    @seguro
    def verificar(self):
        pwd = self.e_pass.get().strip()
        if not pwd:
            raise UserWarning("Por favor ingrese su contraseña.")
        es_valido = self.db.verificar_password_usuario(self.id_usuario, pwd)
        if not es_valido:
            raise UserWarning("Contraseña incorrecta. El cierre mensual no ha sido autorizado.")
        self.destroy()
        if self.on_autorizado:
            self.on_autorizado()


class Justificaciones(Vista):
    def __init__(self, master, app):
        super().__init__(master, app)
        self.filas = {}
        self.sel_id = None
        self.filas_cierres_diarios = {}

        self.titulo(
            "Justificaciones y Cierres de Asistencia",
            "Gestión de justificaciones, cierres diarios automáticos a las 11:59 PM y consolidación mensual"
        )

        # Selector de Pestañas / Paneles
        barra_pestanas = ctk.CTkFrame(self, fg_color="transparent")
        barra_pestanas.pack(fill="x", padx=30, pady=(0, 12))

        self.seg_pestanas = segmentado(
            barra_pestanas,
            values=["📋 Justificaciones de Asistencia", "📁 Cierres Diarios y Respaldo", "📅 Cierre Mensual"],
            command=self._cambiar_pestana,
            height=38
        )
        self.seg_pestanas.pack(fill="x")
        self.seg_pestanas.set("📋 Justificaciones de Asistencia")

        # Contenedor central
        self.contenedor = ctk.CTkFrame(self, fg_color="transparent")
        self.contenedor.pack(fill="both", expand=True, padx=30, pady=(0, 20))

        # -------------------------------------------------------------
        # PANEL 1: JUSTIFICACIONES DEL DÍA
        # -------------------------------------------------------------
        self.panel_justif = ctk.CTkFrame(self.contenedor, fg_color="transparent")
        self.panel_justif.grid_columnconfigure(0, weight=3)
        self.panel_justif.grid_columnconfigure(1, weight=2)
        self.panel_justif.grid_rowconfigure(0, weight=1)

        izq = tarjeta(self.panel_justif)
        izq.grid(row=0, column=0, sticky="nsew", padx=(0, 14))

        f = ctk.CTkFrame(izq, fg_color="transparent")
        f.pack(fill="x", padx=16, pady=(16, 8))
        etiqueta(f, "Fecha:").pack(side="left")
        self.e_fecha = campo(f, width=120, height=36)
        self.e_fecha.insert(0, date.today().isoformat())
        self.e_fecha.pack(side="left", padx=(8, 4))
        self.btn_cal_justif = asociar_boton_calendario(f, self.e_fecha, lambda _: self.cargar())
        self.btn_cal_justif.pack(side="left", padx=(0, 8))
        boton(f, "Cargar", "primario", self.cargar, width=80, height=36).pack(side="left")

        cont, self.tabla = crear_tabla(
            izq,
            [
                ("ced", "Cédula", 90),
                ("nombre", "Nombre", 140),
                ("origen", "Origen / Curso", 130),
                ("estado", "Estado", 100),
                ("just", "Justif.", 85),
                ("obs", "Observación y Soporte", 180)
            ],
            8
        )
        cont.pack(fill="both", expand=True, padx=16)
        self.tabla.bind("<<TreeviewSelect>>", lambda e: self._seleccion())

        der_justif = tarjeta(self.panel_justif)
        der_justif.grid(row=0, column=1, sticky="nsew")

        ctk.CTkLabel(der_justif, text="Motivo o Justificación", font=(F_TITULO, 16, "bold"), text_color=TEXTO, anchor="w").pack(
            fill="x", padx=16, pady=(16, 4))
        etiqueta(
            der_justif,
            "Seleccione un registro no-presente e ingrese el motivo y documento de soporte (reposo médico, constancia laboral, etc.). Exclusivo Directora/Administración.",
            wraplength=280
        ).pack(fill="x", padx=16, pady=(0, 6))

        etiqueta(der_justif, "Motivo detallado:").pack(fill="x", padx=16, pady=(4, 2))
        self.txt = area(der_justif, height=85)
        self.txt.pack(fill="x", padx=16, pady=(0, 8))

        etiqueta(der_justif, "Documento / Soporte:").pack(fill="x", padx=16, pady=(4, 2))
        self.e_soporte = campo(der_justif, placeholder_text="Ej: Reposo Médico IVSS #045, Permiso Laboral...")
        self.e_soporte.pack(fill="x", padx=16, pady=(0, 14))

        boton(der_justif, "💾 Guardar Justificación", "primario", self.guardar, height=44).pack(fill="x", padx=16, pady=(0, 16))

        # -------------------------------------------------------------
        # PANEL 2: CIERRES DIARIOS Y RESPALDO
        # -------------------------------------------------------------
        self.panel_cierres_diarios = ctk.CTkFrame(self.contenedor, fg_color="transparent")

        # Barra superior de filtros y acciones para Cierres Diarios
        barra_cd = ctk.CTkFrame(self.panel_cierres_diarios, fg_color="transparent")
        barra_cd.pack(fill="x", pady=(0, 10))

        etiqueta(barra_cd, "Filtrar por fecha:").pack(side="left", padx=(0, 6))
        self.e_filtro_cierre = campo(barra_cd, width=120, height=36, placeholder_text="AAAA-MM-DD")
        self.e_filtro_cierre.pack(side="left", padx=(0, 4))
        self.btn_cal_cierre = asociar_boton_calendario(barra_cd, self.e_filtro_cierre, lambda _: self.cargar_cierres_diarios())
        self.btn_cal_cierre.pack(side="left", padx=(0, 8))

        boton(barra_cd, "Buscar", "primario", self.cargar_cierres_diarios, width=80, height=36).pack(side="left", padx=(0, 6))
        boton(barra_cd, "Ver Todos", "suave", self._limpiar_filtro_cierres, width=90, height=36).pack(side="left", padx=(0, 14))

        boton(barra_cd, "⚡ Ejecutar Cierre Diario de Hoy", "acento", self.ejecutar_cierre_hoy, width=220, height=36).pack(side="left", padx=(0, 8))
        boton(barra_cd, "📄 Descargar PDF", "primario", self.descargar_pdf_cierre, width=130, height=36).pack(side="left", padx=(0, 6))
        boton(barra_cd, "📊 Descargar Excel", "ok", self.descargar_excel_cierre, width=140, height=36).pack(side="left", padx=(0, 6))
        boton(barra_cd, "📂 Abrir Carpeta", "suave", self.abrir_carpeta_cierres, width=120, height=36).pack(side="left")

        # Tabla de Cierres Diarios
        t_cd = tarjeta(self.panel_cierres_diarios)
        t_cd.pack(fill="both", expand=True)

        cont_cd, self.t_cierres_diarios = crear_tabla(
            t_cd,
            [
                ("fecha", "Fecha Oficial", 100),
                ("mat", "Matrícula", 75),
                ("pres", "Presentes", 75),
                ("retr", "Retrasos", 75),
                ("salt", "Sal. Temp.", 75),
                ("aus", "Ausencias", 75),
                ("just", "Justific.", 70),
                ("pct", "% Asistencia", 95),
                ("usr", "Autorizado Por", 110),
                ("creado", "Generado En", 130)
            ],
            12
        )
        cont_cd.pack(fill="both", expand=True, padx=14, pady=12)
        self.t_cierres_diarios.bind("<<TreeviewSelect>>", lambda e: self._seleccion_cierre_diario())

        # Barra informativa inferior
        self.card_info_cd = ctk.CTkFrame(self.panel_cierres_diarios, fg_color=CARD, corner_radius=10, border_width=1, border_color=BORDE)
        self.card_info_cd.pack(fill="x", pady=(10, 0))
        self.l_info_cierre = ctk.CTkLabel(
            self.card_info_cd,
            text="ℹ Seleccione un cierre diario de la tabla para ver su resumen y descargar el reporte en PDF o Excel.",
            font=(F_TEXTO, 11, "bold"),
            text_color=TEXTO
        )
        self.l_info_cierre.pack(padx=14, pady=8, anchor="w")

        # -------------------------------------------------------------
        # PANEL 3: CIERRE MENSUAL
        # -------------------------------------------------------------
        self.panel_mensual = ctk.CTkFrame(self.contenedor, fg_color="transparent")
        self.panel_mensual.grid_columnconfigure(0, weight=1)
        self.panel_mensual.grid_columnconfigure(1, weight=1)
        self.panel_mensual.grid_rowconfigure(0, weight=1)

        t_mensual = tarjeta(self.panel_mensual)
        t_mensual.grid(row=0, column=0, sticky="nsew", padx=(0, 14))

        ctk.CTkLabel(t_mensual, text="Cierre y Consolidación Mensual", font=(F_TITULO, 18, "bold"), text_color=TEXTO, anchor="w").pack(
            fill="x", padx=18, pady=(18, 2))
        etiqueta(
            t_mensual,
            "Consolida los indicadores de todo el mes escolar en el histórico permanente institucional. Un mes cerrado queda certificado.",
            wraplength=340, justify="left"
        ).pack(fill="x", padx=18)

        fila = ctk.CTkFrame(t_mensual, fg_color="transparent")
        fila.pack(fill="x", padx=18, pady=16)
        anio = date.today().year
        self.cb_anio = combo(fila, values=[str(a) for a in range(anio, anio - 4, -1)], width=95)
        self.cb_anio.pack(side="left")
        self.cb_mes = combo(fila, values=MESES)
        self.cb_mes.pack(side="left", padx=8, fill="x", expand=True)
        self.cb_mes.set(MESES[date.today().month - 1])

        self.chk = ctk.CTkCheckBox(
            t_mensual, text="Archivar y respaldar los registros diarios del mes",
            text_color=TEXTO, fg_color=PRIMARIO, hover_color=PRIMARIO_H, border_color=BORDE,
            font=(F_TEXTO, 12)
        )
        self.chk.pack(anchor="w", padx=18, pady=(0, 14))

        boton(t_mensual, "Ejecutar Cierre Mensual Certificado", "acento", self.cerrar_mensual, height=46).pack(fill="x", padx=18, pady=(0, 18))

        t_hist_m = tarjeta(self.panel_mensual)
        t_hist_m.grid(row=0, column=1, sticky="nsew")

        ctk.CTkLabel(t_hist_m, text="Histórico de Cierres Mensuales", font=(F_TITULO, 16, "bold"), text_color=TEXTO,
                     anchor="w").pack(fill="x", padx=18, pady=(18, 8))
        c2, self.t_cierres = crear_tabla(t_hist_m, [("per", "Período", 110), ("pers", "Personas", 80),
                                                    ("arch", "Archivado", 90)], 10)
        c2.pack(fill="both", expand=True, padx=18, pady=(0, 18))

        # Vista inicial
        self._cambiar_pestana("📋 Justificaciones de Asistencia")

    def _cambiar_pestana(self, valor):
        self.panel_justif.pack_forget()
        self.panel_cierres_diarios.pack_forget()
        self.panel_mensual.pack_forget()

        if "Justificaciones" in valor:
            self.panel_justif.pack(fill="both", expand=True)
            self.cargar()
        elif "Cierres Diarios" in valor:
            self.panel_cierres_diarios.pack(fill="both", expand=True)
            self.cargar_cierres_diarios()
        elif "Cierre Mensual" in valor:
            self.panel_mensual.pack(fill="both", expand=True)
            self.cargar_cierres_mensuales()

    def refrescar(self):
        if not self.e_fecha.get().strip():
            self.e_fecha.delete(0, "end")
            self.e_fecha.insert(0, date.today().isoformat())
        self._cambiar_pestana(self.seg_pestanas.get())

    # -------------------------------------------------------------
    # MÉTODOS DE JUSTIFICACIONES
    # -------------------------------------------------------------
    def _fecha(self):
        val = self.e_fecha.get().strip() if hasattr(self, "e_fecha") else ""
        if not val:
            hoy = date.today()
            if hasattr(self, "e_fecha"):
                self.e_fecha.delete(0, "end")
                self.e_fecha.insert(0, hoy.isoformat())
            return hoy
        try:
            return datetime.strptime(val, "%Y-%m-%d").date()
        except ValueError:
            hoy = date.today()
            if hasattr(self, "e_fecha"):
                self.e_fecha.delete(0, "end")
                self.e_fecha.insert(0, hoy.isoformat())
            return hoy

    @seguro
    def cargar(self):
        fecha = self._fecha()
        limpiar(self.tabla)
        self.filas, self.sel_id = {}, None
        self.txt.delete("1.0", "end")
        if hasattr(self, "e_soporte"):
            self.e_soporte.delete(0, "end")

        for r in self.db.no_presentes(fecha):
            iid = str(r.get("id_clave") or r.get("id_asistencia") or r.get("id_asistencia_curso"))
            self.filas[iid] = r
            obs = (r["observaciones"] or "").strip()
            insertar(
                self.tabla,
                (r["cedula"], r["nombre"], r.get("origen", "General"), r["estado"],
                 "Registrada" if obs else "Pendiente", obs[:60]),
                () if obs else ("pendiente",),
                iid
            )

    def _seleccion(self):
        sel = self.tabla.selection()
        if sel:
            self.sel_id = sel[0]
            r = self.filas[self.sel_id]
            self.txt.delete("1.0", "end")
            obs_raw = r.get("observaciones") or ""
            # Si contiene "[Soporte: ...]", separar para mejor edición
            soporte_val = ""
            if "[Soporte:" in obs_raw and obs_raw.endswith("]"):
                partes = obs_raw.rsplit("[Soporte:", 1)
                obs_txt = partes[0].strip()
                soporte_val = partes[1].rstrip("]").strip()
            else:
                obs_txt = obs_raw

            self.txt.insert("1.0", obs_txt)
            if hasattr(self, "e_soporte"):
                self.e_soporte.delete(0, "end")
                self.e_soporte.insert(0, soporte_val)

    @seguro
    def guardar(self):
        if not self.sel_id:
            raise UserWarning("Seleccione un registro de la tabla para justificar.")
        r = self.filas[self.sel_id]
        obs = self.txt.get("1.0", "end").strip()
        soporte = self.e_soporte.get().strip() if hasattr(self, "e_soporte") else ""

        if r["estado"] in ("Retraso", "Salida Temprana", "Ausente") and len(obs) < 4:
            raise UserWarning("Debe indicar el motivo detallado de la justificación (mínimo 4 caracteres).")

        id_asist = r.get("id_asistencia")
        id_asist_curso = r.get("id_asistencia_curso")

        self.db.guardar_justificacion(
            id_asistencia=id_asist,
            id_asistencia_curso=id_asist_curso,
            obs=obs,
            soporte=soporte
        )
        self.cargar()
        messagebox.showinfo(
            "Justificación Registrada",
            f"La justificación de {r['nombre']} fue guardada exitosamente y su porcentaje de asistencia fue recalculado."
        )

    # -------------------------------------------------------------
    # MÉTODOS DE CIERRES DIARIOS
    # -------------------------------------------------------------
    def _limpiar_filtro_cierres(self):
        self.e_filtro_cierre.delete(0, "end")
        self.cargar_cierres_diarios()

    @seguro
    def cargar_cierres_diarios(self):
        limpiar(self.t_cierres_diarios)
        self.filas_cierres_diarios = {}
        filtro = self.e_filtro_cierre.get().strip() or None

        cierres = self.db.listar_cierres_diarios(filtro)
        for c in cierres:
            iid = str(c["id_cierre_diario"])
            self.filas_cierres_diarios[iid] = c
            f_fmt = c["fecha_str"]
            pct_fmt = f"{c['pct_asistencia']:.1f}%"
            insertar(
                self.t_cierres_diarios,
                (
                    f_fmt,
                    c["total_matricula"],
                    c["presentes"],
                    c["retrasos"],
                    c["salidas_tempranas"],
                    c["ausencias"],
                    c["justificados"],
                    pct_fmt,
                    c.get("usuario_nombre") or "Automático",
                    c.get("fecha_cierre_fmt") or "—"
                ),
                iid=iid
            )

    def _seleccion_cierre_diario(self):
        sel = self.t_cierres_diarios.selection()
        if sel:
            c = self.filas_cierres_diarios[sel[0]]
            self.l_info_cierre.configure(
                text=f"📅 Cierre del {c['fecha_str']}: Matrícula: {c['total_matricula']} | "
                     f"Presentes: {c['presentes']} | Retrasos: {c['retrasos']} | Ausencias: {c['ausencias']} | "
                     f"Asistencia: {c['pct_asistencia']:.1f}%. Reportes PDF y Excel disponibles para descarga."
            )

    @seguro
    def ejecutar_cierre_hoy(self):
        hoy = date.today()
        id_u = getattr(self.app, "usuario_actual", {}).get("id_usuario") or config.USUARIO_ID
        if not messagebox.askyesno(
            "Ejecutar Cierre Diario",
            f"¿Desea generar y consolidar el Cierre Diario para el día de hoy ({hoy.strftime('%d/%m/%Y')})?\n\n"
            "El sistema calculará las estadísticas de asistencia, generará los archivos oficiales en PDF y Excel, "
            "y los archivará de manera segura en el respaldo del sistema."
        ):
            return

        res = self.db.ejecutar_cierre_diario(hoy, id_u)
        messagebox.showinfo(
            "Cierre Diario Completado",
            f"✓ Cierre diario de hoy ({hoy.strftime('%d/%m/%Y')}) completado con éxito.\n\n"
            f"Matrícula: {res['total_matricula']}\n"
            f"Asistencia Global: {res['pct_asistencia']:.1f}%\n"
            f"PDF generado: {res['archivo_pdf']}\n"
            f"Excel generado: {res['archivo_excel']}"
        )
        self.cargar_cierres_diarios()

    @seguro
    def descargar_pdf_cierre(self):
        sel = self.t_cierres_diarios.selection()
        if not sel:
            raise UserWarning("Seleccione un registro de cierre diario de la tabla para descargar el PDF.")
        c = self.filas_cierres_diarios[sel[0]]

        fecha_obj = c.get("fecha")
        if isinstance(fecha_obj, str):
            try:
                fecha_obj = datetime.strptime(fecha_obj[:10], "%Y-%m-%d").date()
            except Exception:
                fecha_obj = date.today()
        elif isinstance(fecha_obj, datetime):
            fecha_obj = fecha_obj.date()
        elif not isinstance(fecha_obj, date):
            fecha_obj = date.today()

        fecha_str = fecha_obj.strftime("%Y-%m-%d")
        fecha_slug = fecha_obj.strftime("%Y_%m_%d")

        ruta_origen = c.get("archivo_pdf")
        if not ruta_origen or not os.path.exists(ruta_origen):
            nombre_base = f"cierre_diario_{fecha_slug}.pdf"
            candidato = config.BASE_DIR / "respaldos" / "cierres_diarios" / "pdf" / nombre_base
            if candidato.exists():
                ruta_origen = str(candidato)
            else:
                dir_pdf = config.BASE_DIR / "respaldos" / "cierres_diarios" / "pdf"
                dir_pdf.mkdir(parents=True, exist_ok=True)
                ruta_origen = str(dir_pdf / nombre_base)
                import reports
                reports.generar_reporte_diario_pdf(self.db, fecha_obj, ruta_origen)

        destino = filedialog.asksaveasfilename(
            title="Guardar Reporte Diario en PDF",
            defaultextension=".pdf",
            filetypes=[("Documento PDF (*.pdf)", "*.pdf")],
            initialfile=f"Cierre_Diario_{fecha_str}.pdf"
        )
        if not destino:
            return

        shutil.copy2(ruta_origen, destino)
        messagebox.showinfo("Descarga Exitosa", f"Archivo PDF guardado exitosamente en:\n{destino}")
        try:
            if sys.platform.startswith("win"):
                os.startfile(destino)
        except Exception:
            pass

    @seguro
    def descargar_excel_cierre(self):
        sel = self.t_cierres_diarios.selection()
        if not sel:
            raise UserWarning("Seleccione un registro de cierre diario de la tabla para descargar el Excel.")
        c = self.filas_cierres_diarios[sel[0]]

        fecha_obj = c.get("fecha")
        if isinstance(fecha_obj, str):
            try:
                fecha_obj = datetime.strptime(fecha_obj[:10], "%Y-%m-%d").date()
            except Exception:
                fecha_obj = date.today()
        elif isinstance(fecha_obj, datetime):
            fecha_obj = fecha_obj.date()
        elif not isinstance(fecha_obj, date):
            fecha_obj = date.today()

        fecha_str = fecha_obj.strftime("%Y-%m-%d")
        fecha_slug = fecha_obj.strftime("%Y_%m_%d")

        ruta_origen = c.get("archivo_excel")
        if not ruta_origen or not os.path.exists(ruta_origen):
            nombre_base = f"cierre_diario_{fecha_slug}.xlsx"
            candidato = config.BASE_DIR / "respaldos" / "cierres_diarios" / "excel" / nombre_base
            if candidato.exists():
                ruta_origen = str(candidato)
            else:
                dir_xl = config.BASE_DIR / "respaldos" / "cierres_diarios" / "excel"
                dir_xl.mkdir(parents=True, exist_ok=True)
                ruta_origen = str(dir_xl / nombre_base)
                import excel_reports
                excel_reports.exportar_reporte_diario_excel(self.db, fecha_obj, ruta_origen)

        destino = filedialog.asksaveasfilename(
            title="Guardar Reporte Diario en Excel",
            defaultextension=".xlsx",
            filetypes=[("Libro de Excel (*.xlsx)", "*.xlsx")],
            initialfile=f"Cierre_Diario_{fecha_str}.xlsx"
        )
        if not destino:
            return

        shutil.copy2(ruta_origen, destino)
        messagebox.showinfo("Descarga Exitosa", f"Archivo Excel guardado exitosamente en:\n{destino}")
        try:
            if sys.platform.startswith("win"):
                os.startfile(destino)
        except Exception:
            pass

    def abrir_carpeta_cierres(self):
        p = config.BASE_DIR / "respaldos" / "cierres_diarios"
        p.mkdir(parents=True, exist_ok=True)
        try:
            if os.name == 'nt':
                os.startfile(p)
            else:
                subprocess.Popen(["xdg-open", str(p)])
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir la carpeta: {e}")

    # -------------------------------------------------------------
    # MÉTODOS DE CIERRE MENSUAL
    # -------------------------------------------------------------
    def cargar_cierres_mensuales(self):
        limpiar(self.t_cierres)
        for c in self.db.cierres():
            insertar(
                self.t_cierres,
                (f"{MESES[c['mes'] - 1][:3]} {c['anio']}", c["total_personas"], "Sí" if c["archivado"] else "No")
            )

    @seguro
    def cerrar_mensual(self):
        anio, mes = int(self.cb_anio.get()), MESES.index(self.cb_mes.get()) + 1
        archivar = bool(self.chk.get())
        periodo_txt = f"{MESES[mes - 1]} {anio}"

        if not messagebox.askyesno(
            "Confirmar Cierre Mensual",
            f"¿Desea iniciar el proceso de cierre mensual de {periodo_txt}?\n\n"
            "Esta acción consolidará las estadísticas del mes en el histórico."
            + ("\nLos registros diarios serán resguardados y archivados." if archivar else "")
        ):
            return

        id_u = getattr(self.app, "usuario_actual", {}).get("id_usuario") or config.USUARIO_ID
        if not id_u:
            raise UserWarning("Sesión no válida para autorizar el cierre mensual.")

        def ejecutar_cierre_confirmado():
            res = self.db.call("sp_cierre_mensual", (anio, mes, id_u, 1 if archivar else 0))
            n = res[0][0]["personas_consolidadas"] if res and res[0] else 0
            u_nom = getattr(self.app, "usuario_actual", {}).get("nombre_persona") or "Usuario en sesión"
            messagebox.showinfo(
                "Cierre Completado",
                f"El cierre mensual de {periodo_txt} se ha consolidado con éxito.\n\n"
                f"Personas consolidadas: {n}\n"
                f"Mes firmado y autorizado por: {u_nom}."
            )
            self.cargar_cierres_mensuales()

        DialogoClaveCierre(self, self.db, id_u, periodo_txt, ejecutar_cierre_confirmado)
