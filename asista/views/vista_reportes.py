"""Módulo Reportes y Analíticas: Métricas visuales, gráficas del instituto y exportación en PDF y Excel."""
import os
import subprocess
import sys
from datetime import date
from tkinter import filedialog, messagebox
import customtkinter as ctk

import reports
import excel_reports
import carnets
import graficos_utils
from config import MESES
from tema import F_TEXTO, F_TITULO, OK, ACENTO, PRIMARIO, CARD, BORDE, SUAVE, TEXTO
from .ui_utils import Vista, seguro, tarjeta, campo, combo, segmentado, boton, etiqueta


class Reportes(Vista):
    def __init__(self, master, app):
        super().__init__(master, app)
        self.mapa_secciones = {}
        self.mapa_cohortes = {}
        self.mapa_cursos_filtro = {}

        self.titulo(
            "Métricas, Gráficas y Reportes Académicos",
            "Tablero de métricas estadísticas en tiempo real, actas de curso técnico y exportación en PDF y Excel"
        )

        # Selector de Pestañas Principal
        self.seg_pestana = segmentado(
            self,
            values=["📊 Métricas y Gráficas del Instituto", "📄 Generador de Reportes y Actas"],
            command=self._cambiar_pestana
        )
        self.seg_pestana.pack(fill="x", padx=30, pady=(0, 16))

        # --- CONTENEDOR 1: TABLERO DE MÉTRICAS Y GRÁFICAS ---
        self.f_metricas = ctk.CTkFrame(self, fg_color="transparent")

        # Barra de selección de visualización de cursos
        self.f_filtro_curso = ctk.CTkFrame(self.f_metricas, fg_color="transparent")
        self.f_filtro_curso.pack(fill="x", pady=(0, 10))
        
        etiqueta(self.f_filtro_curso, "Visualizar Métricas de:").pack(side="left", padx=(0, 10))
        self.cb_filtro_grafica = combo(
            self.f_filtro_curso,
            values=["Todos los Cursos (General)"],
            command=self._on_cambio_filtro_curso,
            width=320
        )
        self.cb_filtro_grafica.pack(side="left", padx=(0, 12))
        self.cb_filtro_grafica.set("Todos los Cursos (General)")
        
        boton(self.f_filtro_curso, "🔄 Actualizar", "blanco", self._cargar_metricas, height=32).pack(side="left")

        # Fila superior de KPIs
        self.f_kpis = ctk.CTkFrame(self.f_metricas, fg_color="transparent")
        self.f_kpis.pack(fill="x", pady=(0, 14))
        self.f_kpis.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.kpi_total = self._crear_tarjeta_kpi(self.f_kpis, 0, "TOTAL ASISTENCIAS", "0", "Marcajes Registrados")
        self.kpi_pct = self._crear_tarjeta_kpi(self.f_kpis, 1, "ASISTENCIA GLOBAL", "0%", "Puntualidad y Presencia")
        self.kpi_cursos = self._crear_tarjeta_kpi(self.f_kpis, 2, "CURSOS ACTIVOS", "0", "Especialidades Técnicas")
        self.kpi_alertas = self._crear_tarjeta_kpi(self.f_kpis, 3, "CASOS EN ALERTA", "0", "Asistencia < 75%")

        # Fila central de Gráficas: Dona y Barras
        self.f_graf_dual = ctk.CTkFrame(self.f_metricas, fg_color="transparent")
        self.f_graf_dual.pack(fill="x", pady=(0, 14))
        self.f_graf_dual.grid_columnconfigure(0, weight=4)
        self.f_graf_dual.grid_columnconfigure(1, weight=5)

        # Card Dona
        self.card_dona = tarjeta(self.f_graf_dual)
        self.card_dona.grid(row=0, column=0, padx=(0, 8), sticky="nsew")
        self.lbl_graf_dona = ctk.CTkLabel(self.card_dona, text="")
        self.lbl_graf_dona.pack(padx=8, pady=8, fill="both", expand=True)

        # Card Barras
        self.card_barras = tarjeta(self.f_graf_dual)
        self.card_barras.grid(row=0, column=1, padx=(8, 0), sticky="nsew")
        self.lbl_graf_barras = ctk.CTkLabel(self.card_barras, text="")
        self.lbl_graf_barras.pack(padx=8, pady=8, fill="both", expand=True)

        # Fila inferior: Gráfica de Tendencia Semanal
        self.card_lineas = tarjeta(self.f_metricas)
        self.card_lineas.pack(fill="x", pady=(0, 14))
        self.lbl_graf_lineas = ctk.CTkLabel(self.card_lineas, text="")
        self.lbl_graf_lineas.pack(padx=8, pady=8, fill="both", expand=True)

        # Barra de acciones de métricas
        self.f_acciones_m = ctk.CTkFrame(self.f_metricas, fg_color="transparent")
        self.f_acciones_m.pack(fill="x", pady=(0, 14))
        boton(self.f_acciones_m, "🔄 Actualizar Métricas en Vivo", "blanco", self._cargar_metricas, height=44).pack(side="left", padx=(0, 10))
        boton(self.f_acciones_m, "📥 Exportar Informe Estadístico Ejecutivo (PDF)", "acento", self._exportar_informe_estadistico, height=44).pack(side="left")

        # --- CONTENEDOR 2: GENERADOR DE REPORTES Y ACTAS ---
        self.f_generador = ctk.CTkFrame(self, fg_color="transparent")

        c = tarjeta(self.f_generador)
        c.pack(fill="x", pady=(0, 16))
        c.grid_columnconfigure(1, weight=1)

        # 1. Tipo de Reporte
        self.cb_categoria = self._fila(
            c, 0, "Tipo de reporte", combo,
            values=[
                "Acta de Asistencia por Curso Técnico / Cohorte",
                "Historial Individual por Cédula (Participante)",
                "Reporte General Sabatino (Resumen del Día)",
                "Alerta Temprana de Inasistencias (> 25%)",
                "Resumen General por Sección",
                "Matriz Diaria por Sección (1 al 31)",
                "Carnets con Código de Barras (Por Sección)"
            ],
            command=lambda v: self._actualizar()
        )
        self.cb_categoria.set("Acta de Asistencia por Curso Técnico / Cohorte")

        # 2. Formato de Salida
        self.seg_formato = self._fila(
            c, 1, "Formato de salida", segmentado,
            values=["PDF (.pdf)", "Excel (.xlsx)"]
        )
        self.seg_formato.set("PDF (.pdf)")

        # 3. Modalidad de Período
        self.seg_periodo = self._fila(
            c, 2, "Período temporal", segmentado,
            values=["Mensual", "Semestral"],
            command=lambda v: self._actualizar()
        )
        self.seg_periodo.set("Mensual")

        # 4. Parámetros condicionales
        self.cb_cohorte = self._fila(c, 3, "Curso / Cohorte", combo, values=["Cargando..."])
        self.e_ced = self._fila(c, 4, "Cédula", campo, height=38, placeholder_text="Ej: 28111222")
        self.cb_sec = self._fila(c, 5, "Sección", combo, values=[""])

        anio = date.today().year
        self.cb_anio = self._fila(c, 6, "Año", combo, values=[str(a) for a in range(anio, anio - 4, -1)])
        self.cb_mes = self._fila(c, 7, "Mes", combo, values=MESES)
        self.cb_sem = self._fila(c, 8, "Semestre", combo, values=["1 (Enero–Junio)", "2 (Julio–Diciembre)"])

        self.cb_anio.set(str(anio))
        self.cb_mes.set(MESES[date.today().month - 1])
        self.cb_sem.set("1 (Enero–Junio)" if date.today().month <= 6 else "2 (Julio–Diciembre)")

        boton(self.f_generador, "Generar y Abrir Reporte ➔", "acento", self.generar, height=50).pack(fill="x", pady=(0, 14))

        self.estado = ctk.CTkLabel(self.f_generador, text="", font=(F_TEXTO, 13, "bold"), anchor="w", wraplength=800)
        self.estado.pack(fill="x")

        # Inicialización
        self.f_metricas.pack(fill="both", expand=True, padx=30)
        self._actualizar()
        self._cargar_metricas()

    def _crear_tarjeta_kpi(self, parent, col, etiqueta_txt, valor_txt, sub_txt):
        card = tarjeta(parent)
        card.grid(row=0, column=col, padx=(0 if col == 0 else 6, 0 if col == 3 else 6), sticky="nsew")
        etiqueta(card, etiqueta_txt, font=(F_TEXTO, 10, "bold"), color=SUAVE).pack(anchor="w", padx=14, pady=(10, 2))
        lbl_val = etiqueta(card, valor_txt, font=(F_TITULO, 22, "bold"), color=PRIMARIO)
        lbl_val.pack(anchor="w", padx=14)
        etiqueta(card, sub_txt, font=(F_TEXTO, 10), color=SUAVE).pack(anchor="w", padx=14, pady=(2, 10))
        return lbl_val

    def _cambiar_pestana(self, valor):
        if "Métricas" in valor:
            self.f_generador.pack_forget()
            self.f_metricas.pack(fill="both", expand=True, padx=30)
            self._cargar_metricas()
        else:
            self.f_metricas.pack_forget()
            self.f_generador.pack(fill="both", expand=True, padx=30)
            self._actualizar()

    def _on_cambio_filtro_curso(self, valor=None):
        self._cargar_metricas()

    def _actualizar_combo_cursos_grafica(self):
        cursos = self.db.fetch_all("SELECT id_curso, codigo, nombre FROM curso WHERE activo = 1 ORDER BY nombre ASC")
        self.mapa_cursos_filtro = {"Todos los Cursos (General)": None}
        vals = ["Todos los Cursos (General)"]
        for cu in cursos:
            lbl = f"{cu.get('codigo', '')} - {cu.get('nombre', '')}"
            self.mapa_cursos_filtro[lbl] = cu["id_curso"]
            vals.append(lbl)
        curr = self.cb_filtro_grafica.get()
        self.cb_filtro_grafica.configure(values=vals)
        if curr not in self.mapa_cursos_filtro:
            self.cb_filtro_grafica.set("Todos los Cursos (General)")

    def _cargar_metricas(self):
        """Consulta la base de datos y dibuja las 3 gráficas estadísticas."""
        try:
            self._actualizar_combo_cursos_grafica()
            sel = self.cb_filtro_grafica.get()
            id_curso = self.mapa_cursos_filtro.get(sel, None)
            m = self.db.metricas_graficas_instituto(id_curso_filtro=id_curso)
            kpis = m.get("kpis", {})

            # Actualizar tarjetas KPI
            self.kpi_total.configure(text=f"{kpis.get('total_asistencias', 0)}")
            self.kpi_pct.configure(text=f"{kpis.get('pct_global', 0)}%")
            self.kpi_cursos.configure(text=f"{kpis.get('cursos_activos', 0)}")
            self.kpi_alertas.configure(text=f"{kpis.get('alertas', 0)}")

            # 1. Gráfica de Dona (Light & Dark)
            dona_l = graficos_utils.dibujar_grafica_dona(m["dona"], size=(380, 240), is_dark=False)
            dona_d = graficos_utils.dibujar_grafica_dona(m["dona"], size=(380, 240), is_dark=True)
            self.lbl_graf_dona.configure(image=ctk.CTkImage(light_image=dona_l, dark_image=dona_d, size=(380, 240)))

            # 2. Gráfica de Barras (Light & Dark)
            barras_l = graficos_utils.dibujar_grafica_barras(m["barras"], size=(450, 240), is_dark=False)
            barras_d = graficos_utils.dibujar_grafica_barras(m["barras"], size=(450, 240), is_dark=True)
            self.lbl_graf_barras.configure(image=ctk.CTkImage(light_image=barras_l, dark_image=barras_d, size=(450, 240)))

            # 3. Gráfica de Líneas / Tendencia (Light & Dark)
            lineas_l = graficos_utils.dibujar_grafica_lineas(m["lineas"], size=(850, 190), is_dark=False)
            lineas_d = graficos_utils.dibujar_grafica_lineas(m["lineas"], size=(850, 190), is_dark=True)
            self.lbl_graf_lineas.configure(image=ctk.CTkImage(light_image=lineas_l, dark_image=lineas_d, size=(850, 190)))

        except Exception as e:
            messagebox.showerror(
                "Error al cargar las métricas",
                f"No se pudieron actualizar los indicadores de asistencia.\n\n{e}",
                parent=self.winfo_toplevel(),
            )

    @seguro
    def _exportar_informe_estadistico(self):
        """Exporta el reporte estadístico con todas las gráficas a PDF."""
        fecha_str = date.today().strftime("%Y_%m_%d")
        nombre_base = f"informe_estadistico_asistencia_{fecha_str}.pdf"
        ruta = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("Documento PDF", "*.pdf")],
            initialfile=nombre_base
        )
        if not ruta:
            return
        reports.generar_informe_estadistico_pdf(self.db, ruta)
        try:
            if sys.platform.startswith("win"):
                os.startfile(ruta)
            else:
                subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", ruta])
        except Exception:
            pass

    def _fila(self, parent, fila, texto, clase, **kw):
        etiqueta(parent, texto, font=(F_TEXTO, 13), width=150).grid(row=fila, column=0, padx=(22, 10), pady=7, sticky="w")
        w = clase(parent, **kw)
        w.grid(row=fila, column=1, padx=(0, 22), pady=7, sticky="ew")
        return w

    def refrescar(self):
        # Mapear secciones
        self.mapa_secciones = {s["etiqueta"]: s["id_seccion"] for s in self.db.secciones()}
        self.cb_sec.configure(values=list(self.mapa_secciones) or [""])
        if self.mapa_secciones and self.cb_sec.get() not in self.mapa_secciones:
            self.cb_sec.set(next(iter(self.mapa_secciones)))

        # Mapear cohortes activas de cursos
        cohortes = self.db.listar_cohortes()
        self.mapa_cohortes = {}
        self.mapa_cursos_filtro = {}
        for c in cohortes:
            lbl = f"{c.get('curso_codigo', '')} - {c.get('curso_nombre', '')} ({c.get('nombre_grupo', '')})"
            self.mapa_cohortes[lbl] = c["id_cohorte"]

        self.cb_cohorte.configure(values=list(self.mapa_cohortes) or ["Sin cohortes"])
        if self.mapa_cohortes and self.cb_cohorte.get() not in self.mapa_cohortes:
            self.cb_cohorte.set(next(iter(self.mapa_cohortes)))

        self._cargar_metricas()

    def _actualizar(self):
        cat = self.cb_categoria.get()
        periodo = self.seg_periodo.get()

        es_cohorte = (cat == "Acta de Asistencia por Curso Técnico / Cohorte")
        es_general_dia = (cat == "Reporte General Sabatino (Resumen del Día)")
        es_individual = cat in ("Historial Individual por Cédula (Participante)", "Individual por Cédula")
        es_seccion = cat in ("Resumen General por Sección", "Matriz Diaria por Sección (1 al 31)", "Carnets con Código de Barras (Por Sección)")
        es_carnets = (cat == "Carnets con Código de Barras (Por Sección)")
        es_matriz = (cat == "Matriz Diaria por Sección (1 al 31)")

        if es_matriz:
            self.seg_periodo.set("Mensual")
            self.seg_periodo.configure(state="disabled")
            periodo = "Mensual"
        elif es_carnets or es_cohorte or es_general_dia or es_individual:
            if es_carnets:
                self.seg_formato.set("PDF (.pdf)")
                self.seg_formato.configure(state="disabled")
            else:
                self.seg_formato.configure(state="normal")
            self.seg_periodo.configure(state="disabled")
        else:
            self.seg_formato.configure(state="normal")
            self.seg_periodo.configure(state="normal")

        self.cb_cohorte.configure(state="readonly" if es_cohorte else "disabled")
        self.e_ced.configure(state="normal" if es_individual else "disabled")
        self.cb_sec.configure(state="readonly" if es_seccion else "disabled")

        es_mensual = (periodo == "Mensual")
        desactivar_fechas = es_carnets or es_cohorte or es_general_dia or es_individual
        self.cb_mes.configure(state="readonly" if (es_mensual and not desactivar_fechas) else "disabled")
        self.cb_sem.configure(state="readonly" if (not es_mensual and not desactivar_fechas) else "disabled")
        self.cb_anio.configure(state="readonly" if not desactivar_fechas else "disabled")

    @seguro
    def generar(self):
        cat = self.cb_categoria.get()
        es_excel = "Excel" in self.seg_formato.get()
        tipo_periodo = self.seg_periodo.get()
        
        raw_anio = str(self.cb_anio.get()).strip()
        anio = int(raw_anio) if raw_anio.isdigit() else date.today().year
        
        if tipo_periodo == "Mensual":
            mes_txt = str(self.cb_mes.get()).strip()
            num_periodo = MESES.index(mes_txt) + 1 if mes_txt in MESES else date.today().month
        else:
            sem_txt = str(self.cb_sem.get()).strip()
            num_periodo = int(sem_txt[0]) if (sem_txt and sem_txt[0].isdigit()) else (1 if date.today().month <= 6 else 2)

        ext = ".xlsx" if es_excel else ".pdf"
        tipo_archivo = [("Excel Workbook", "*.xlsx")] if es_excel else [("Documento PDF", "*.pdf")]

        if cat == "Acta de Asistencia por Curso Técnico / Cohorte":
            cohorte_sel = self.cb_cohorte.get()
            if cohorte_sel not in self.mapa_cohortes:
                raise UserWarning("Por favor seleccione un curso o cohorte válida.")
            id_cohorte = self.mapa_cohortes[cohorte_sel]
            nombre_base = f"acta_curso_{id_cohorte}_{date.today().strftime('%Y%m%d')}{ext}"
            ruta = filedialog.asksaveasfilename(defaultextension=ext, filetypes=tipo_archivo, initialfile=nombre_base)
            if not ruta:
                return

            if es_excel:
                excel_reports.exportar_acta_cohorte_excel(self.db, id_cohorte, ruta)
            else:
                reports.generar_acta_cohorte_pdf(self.db, id_cohorte, ruta)

        elif cat == "Reporte General Sabatino (Resumen del Día)":
            f_hoy = date.today()
            nombre_base = f"resumen_general_sabatino_{f_hoy.strftime('%Y%m%d')}{ext}"
            ruta = filedialog.asksaveasfilename(defaultextension=ext, filetypes=tipo_archivo, initialfile=nombre_base)
            if not ruta:
                return

            if es_excel:
                excel_reports.exportar_reporte_diario_excel(self.db, f_hoy, ruta)
            else:
                reports.generar_reporte_diario_pdf(self.db, f_hoy, ruta)

        elif cat in ("Historial Individual por Cédula (Participante)", "Individual por Cédula"):
            cedula = self.e_ced.get().strip()
            if not cedula:
                raise UserWarning("Por favor ingrese la cédula del participante.")
            nombre_base = f"historial_participante_{cedula}_{date.today().strftime('%Y%m%d')}{ext}"
            ruta = filedialog.asksaveasfilename(defaultextension=ext, filetypes=tipo_archivo, initialfile=nombre_base)
            if not ruta:
                return

            if es_excel:
                excel_reports.exportar_historial_participante_excel(self.db, cedula, ruta)
            else:
                reports.generar_historial_participante_pdf(self.db, cedula, ruta)

        elif cat == "Resumen General por Sección":
            if self.cb_sec.get() not in self.mapa_secciones:
                raise UserWarning("Por favor seleccione una sección válida.")
            id_sec = self.mapa_secciones[self.cb_sec.get()]
            nombre_base = f"resumen_seccion_{id_sec}_{anio}_{num_periodo}{ext}"
            ruta = filedialog.asksaveasfilename(defaultextension=ext, filetypes=tipo_archivo, initialfile=nombre_base)
            if not ruta:
                return

            if es_excel:
                excel_reports.exportar_resumen_seccion_excel(self.db, tipo_periodo, id_sec, anio, num_periodo, ruta)
            else:
                reports.generar(self.db, tipo_periodo, "Sección", id_sec, anio, num_periodo, ruta)

        elif cat == "Matriz Diaria por Sección (1 al 31)":
            if self.cb_sec.get() not in self.mapa_secciones:
                raise UserWarning("Por favor seleccione una sección para la matriz.")
            id_sec = self.mapa_secciones[self.cb_sec.get()]
            nombre_base = f"matriz_asistencia_seccion_{id_sec}_{MESES[num_periodo - 1]}_{anio}{ext}"
            ruta = filedialog.asksaveasfilename(defaultextension=ext, filetypes=tipo_archivo, initialfile=nombre_base)
            if not ruta:
                return

            if es_excel:
                excel_reports.exportar_matriz_excel(self.db, id_sec, anio, num_periodo, ruta)
            else:
                reports.generar_matriz_pdf(self.db, id_sec, anio, num_periodo, ruta)

        elif cat == "Alerta Temprana de Inasistencias (> 25%)":
            nombre_base = f"alerta_inasistencias_{anio}_{num_periodo}{ext}"
            ruta = filedialog.asksaveasfilename(defaultextension=ext, filetypes=tipo_archivo, initialfile=nombre_base)
            if not ruta:
                return

            if es_excel:
                excel_reports.exportar_alerta_inasistencias_excel(self.db, anio, num_periodo, tipo_periodo, ruta, umbral=25.0)
            else:
                reports.generar_alerta_pdf(self.db, anio, num_periodo, tipo_periodo, ruta, umbral=25.0)

        elif cat == "Carnets con Código de Barras (Por Sección)":
            if self.cb_sec.get() not in self.mapa_secciones:
                raise UserWarning("Por favor seleccione una sección para emitir los carnets.")
            id_sec = self.mapa_secciones[self.cb_sec.get()]
            nombre_base = f"carnets_seccion_{id_sec}.pdf"
            ruta = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("Documento PDF", "*.pdf")], initialfile=nombre_base)
            if not ruta:
                return
            carnets.generar_carnets_seccion(self.db, id_sec, ruta)

        self.estado.configure(text="Reporte generado exitosamente: " + ruta, text_color=OK)

        # Abrir automáticamente en el visor predeterminado
        try:
            if sys.platform.startswith("win"):
                os.startfile(ruta)  # noqa: S606
            else:
                subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", ruta])
        except Exception:  # noqa: BLE001
            pass
