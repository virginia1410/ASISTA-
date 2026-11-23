"""Módulo Inicio (Dashboard): Resumen diario de asistencia, estadísticas y accesos rápidos."""
from datetime import date, datetime
import customtkinter as ctk

from config import DIAS, HORA_LIMITE_ENTRADA, HORA_SALIDA_MINIMA, MESES
from db import fmt_hora
from tema import ACENTO, AVISO, BORDE, CARD, F_TEXTO, F_TITULO, OK, PRIMARIO, SUAVE, TEXTO
from .ui_utils import Vista, seguro, tarjeta, etiqueta, boton, campo, crear_tabla, insertar, limpiar
from .componentes import Banner, Calendario


class Inicio(Vista):
    def __init__(self, master, app):
        super().__init__(master, app)
        self.banner = Banner(self)
        self.banner.pack(fill="x", padx=30, pady=(26, 16))
        fila = ctk.CTkFrame(self, fg_color="transparent")
        fila.pack(fill="x", padx=30)
        self.numeros = {}
        for i, (k, txt, col, glifo) in enumerate([
            ("asist", "Asistencias hoy", OK, "✓"),
            ("retr", "Retrasos", AVISO, "!"),
            ("aus", "Ausencias", ACENTO, "✕"),
            ("just", "Justificaciones", PRIMARIO, "✎")
        ]):
            fila.grid_columnconfigure(i, weight=1, uniform="c")
            c = tarjeta(fila)
            c.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 12, 0))
            ctk.CTkLabel(c, text=glifo, width=50, height=50, corner_radius=16, fg_color=col, text_color="white",
                         font=(F_TEXTO, 20, "bold")).grid(row=0, column=0, rowspan=2, padx=(18, 12), pady=18)
            n = ctk.CTkLabel(c, text="0", font=(F_TEXTO, 32, "bold"), text_color=TEXTO, anchor="w")
            n.grid(row=0, column=1, sticky="sw", pady=(14, 0))
            etiqueta(c, txt).grid(row=1, column=1, sticky="nw", pady=(0, 14))
            self.numeros[k] = n

        self.l_poblacion = ctk.CTkLabel(
            self,
            text="",
            font=(F_TEXTO, 11, "bold"),
            text_color=SUAVE,
            anchor="w",
        )
        self.l_poblacion.pack(fill="x", padx=30, pady=(8, 0))
        self.l_congruencia = ctk.CTkLabel(
            self,
            text="",
            font=(F_TEXTO, 10),
            text_color=SUAVE,
            anchor="w",
        )
        self.l_congruencia.pack(fill="x", padx=30, pady=(2, 0))

        bajo = ctk.CTkFrame(self, fg_color="transparent")
        bajo.pack(fill="both", expand=True, padx=30, pady=(10, 24))
        bajo.grid_columnconfigure(0, weight=1)
        bajo.grid_rowconfigure(0, weight=1)
        izq = ctk.CTkFrame(bajo, fg_color="transparent")
        izq.grid(row=0, column=0, sticky="nsew", padx=(0, 16))
        t = tarjeta(izq)
        t.pack(fill="both", expand=True)
        ctk.CTkLabel(t, text="Últimos registros de hoy", font=(F_TITULO, 16, "bold"), text_color=TEXTO,
                     anchor="w").pack(fill="x", padx=20, pady=(16, 8))
        cont, self.tabla = crear_tabla(t, [("hora", "Entrada", 90), ("nombre", "Nombre", 280),
                                           ("tipo", "Tipo", 110), ("estado", "Estado", 140)], 6)
        cont.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        q = tarjeta(izq)
        q.pack(fill="x", pady=(14, 0))
        f = ctk.CTkFrame(q, fg_color="transparent")
        f.pack(fill="x", padx=16, pady=14)
        self.e_ced = campo(f, placeholder_text="Registro rápido: escriba la cédula…", height=44)
        self.e_ced.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.e_ced.bind("<Return>", lambda e: self.ir_marcaje())
        boton(f, "Ir a marcaje  →", "acento", self.ir_marcaje, width=150, height=44).pack(side="left")
        boton(f, "📱 Móvil Docente", "suave", self.abrir_qr_movil, width=145, height=44).pack(side="left", padx=(8, 0))

        # Monitor de Clases en Tiempo Real para la Directora
        self.card_monitor = tarjeta(izq)
        self.card_monitor.pack(fill="x", pady=(14, 0))

        f_mon_head = ctk.CTkFrame(self.card_monitor, fg_color="transparent")
        f_mon_head.pack(fill="x", padx=16, pady=(12, 6))

        ctk.CTkLabel(
            f_mon_head,
            text="📡 Monitor de Clases en Tiempo Real (Aulas y Talleres)",
            font=(F_TITULO, 14, "bold"),
            text_color=TEXTO
        ).pack(side="left")

        boton(
            f_mon_head,
            "🔄 Actualizar",
            "suave",
            self._actualizar_clases_en_vivo,
            width=115,
            height=30
        ).pack(side="right")

        self.f_clases_vivo = ctk.CTkFrame(self.card_monitor, fg_color="transparent")
        self.f_clases_vivo.pack(fill="x", padx=16, pady=(0, 12))

        der = ctk.CTkFrame(bajo, fg_color="transparent")
        der.grid(row=0, column=1, sticky="n")

        # Reloj digital en tiempo real
        self.card_reloj = tarjeta(der)
        self.card_reloj.pack(fill="x", pady=(0, 14))

        f_reloj_head = ctk.CTkFrame(self.card_reloj, fg_color="transparent")
        f_reloj_head.pack(fill="x", padx=16, pady=(12, 2))
        ctk.CTkLabel(f_reloj_head, text="🕒 HORA EN TIEMPO REAL", font=(F_TEXTO, 10, "bold"), text_color=TEXTO).pack(side="left")

        self.badge_turno = ctk.CTkFrame(f_reloj_head, fg_color=("#E0F2FE", "#162C55"), corner_radius=6)
        self.badge_turno.pack(side="right")
        self.l_turno_badge = ctk.CTkLabel(self.badge_turno, text="Turno Mañana", font=(F_TEXTO, 9, "bold"), text_color=("#0369A1", "#38BDF8"))
        self.l_turno_badge.pack(padx=6, pady=1)

        self.l_reloj_tiempo = ctk.CTkLabel(
            self.card_reloj,
            text="00:00:00 --",
            font=(F_TITULO, 28, "bold"),
            text_color=PRIMARIO[0] if isinstance(PRIMARIO, tuple) else PRIMARIO
        )
        self.l_reloj_tiempo.pack(padx=16, pady=(2, 2))

        self.l_reloj_fecha = ctk.CTkLabel(
            self.card_reloj,
            text="",
            font=(F_TEXTO, 11),
            text_color=TEXTO
        )
        self.l_reloj_fecha.pack(padx=16, pady=(0, 12))

        self.cal = Calendario(der)
        self.cal.pack()
        self._reloj_job = None
        self._actualizar_reloj_tiempo_real()
        h = tarjeta(der)
        h.pack(fill="x", pady=(14, 0))
        ctk.CTkLabel(h, text="Horarios de Referencia por Turno", font=(F_TITULO, 13, "bold"), text_color=TEXTO).pack(
            anchor="w", padx=18, pady=(12, 6))
        self.f_horarios_dash = ctk.CTkFrame(h, fg_color="transparent")
        self.f_horarios_dash.pack(fill="x", padx=18, pady=(0, 8))
        self._dibujar_horarios_referencia()
        self._actualizar_clases_en_vivo()

    def _dibujar_horarios_referencia(self):
        if not hasattr(self, "f_horarios_dash"):
            return
        for w in self.f_horarios_dash.winfo_children():
            w.destroy()

        import config
        ht = getattr(config, "HORARIOS_TURNO", {})
        m_ent = ht.get("Mañana", {}).get("str_entrada") or f"{config.HORA_LIMITE_ENTRADA:%H:%M}"
        m_sal = ht.get("Mañana", {}).get("str_salida") or f"{config.HORA_SALIDA_MINIMA:%H:%M}"
        t_ent = ht.get("Tarde", {}).get("str_entrada", "12:45")
        t_sal = ht.get("Tarde", {}).get("str_salida", "17:30")

        items = [
            (f"🌅 Mañana: Entrada {m_ent} | Salida {m_sal}", OK),
            (f"🌇 Tarde:   Entrada {t_ent} | Salida {t_sal}", PRIMARIO)
        ]
        for txt, col in items:
            r = ctk.CTkFrame(self.f_horarios_dash, fg_color="transparent")
            r.pack(fill="x", pady=(0, 4))
            ctk.CTkLabel(r, text="", width=8, height=8, corner_radius=4, fg_color=col).pack(side="left", padx=(0, 8))
            etiqueta(r, txt, color=TEXTO, font=(F_TEXTO, 10, "bold")).pack(side="left")

    def actualizar_tema(self):
        self.banner.actualizar_tema()

    def ir_marcaje(self):
        cedula = self.e_ced.get().strip()
        self.app.mostrar("marcaje")
        if cedula:
            self.app.vistas["marcaje"].buscar(cedula)
            self.e_ced.delete(0, "end")

    def _actualizar_reloj_tiempo_real(self):
        try:
            ahora = datetime.now()
            hora_str = ahora.strftime("%I:%M:%S %p")
            dias_esp = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
            dia_str = dias_esp[ahora.weekday()]
            mes_str = MESES[ahora.month - 1]
            fecha_str = f"{dia_str}, {ahora.day} de {mes_str} de {ahora.year}"

            es_manana = ahora.hour < 12
            turno_txt = "🌅 Turno Mañana" if es_manana else "🌇 Turno Tarde"

            if hasattr(self, "l_reloj_tiempo"):
                self.l_reloj_tiempo.configure(text=hora_str)
            if hasattr(self, "l_reloj_fecha"):
                self.l_reloj_fecha.configure(text=fecha_str)
            if hasattr(self, "l_turno_badge"):
                self.l_turno_badge.configure(text=turno_txt)
        except Exception:
            pass

        try:
            self._reloj_job = self.after(1000, self._actualizar_reloj_tiempo_real)
        except Exception:
            pass

    @seguro
    def abrir_qr_movil(self):
        from .componentes import DialogoQRMovil
        DialogoQRMovil(self)

    def refrescar(self):
        h, hora = date.today(), datetime.now().hour
        saludo = "Buenos días" if hora < 12 else "Buenas tardes" if hora < 19 else "Buenas noches"
        self.banner.poner("PANEL DE CONTROL", saludo,
                          f"{DIAS[h.weekday()].capitalize()} {h.day} de {MESES[h.month - 1]} de {h.year}")
        self.cal.dibujar()
        self._dibujar_horarios_referencia()
        self._actualizar_clases_en_vivo()
        estadisticas = self.db.stats_hoy()
        for k in self.numeros:
            v = estadisticas[k]
            self.numeros[k].configure(text=str(v))
        total_marcados = estadisticas["asist"] + estadisticas["aus"]
        self.l_poblacion.configure(
            text=(
                f"Población activa: {estadisticas['estudiantes']} estudiantes + "
                f"{estadisticas['personal']} personal = {estadisticas['activos']} personas"
                f"   ·   Marcajes: {total_marcados}/{estadisticas['activos']}"
                f"   ·   Sin registro: {estadisticas['pendientes']}"
            )
        )
        self.l_congruencia.configure(
            text=(
                "Cruce portería–aula: "
                f"{estadisticas['sin_entrada']} estudiante(s) con presente/retraso en clase "
                "sin entrada válida registrada en portería"
            )
        )
        limpiar(self.tabla)
        for r in self.db.registros_hoy():
            insertar(self.tabla, (fmt_hora(r["hora_entrada"]), r["nombre"], r["tipo_persona"], r["estado"]),
                     (r["estado"],))


    def _actualizar_clases_en_vivo(self):
        """Dibuja el estado en tiempo real de las clases y talleres para la Directora."""
        if not hasattr(self, "f_clases_vivo"):
            return
        for w in self.f_clases_vivo.winfo_children():
            w.destroy()

        try:
            clases = self.db.monitoreo_clases_tiempo_real()
        except Exception:
            clases = []

        if not clases:
            ctk.CTkLabel(
                self.f_clases_vivo,
                text="No hay cursos activos programados para el día de hoy.",
                font=(F_TEXTO, 11),
                text_color=SUAVE
            ).pack(pady=10)
            return

        for c in clases:
            card_c = ctk.CTkFrame(
                self.f_clases_vivo,
                fg_color=("#F8FAFC", "#162C55"),
                border_width=1,
                border_color=BORDE,
                corner_radius=12
            )
            card_c.pack(fill="x", pady=4)

            f_info = ctk.CTkFrame(card_c, fg_color="transparent")
            f_info.pack(fill="x", padx=14, pady=8)

            f_top_c = ctk.CTkFrame(f_info, fg_color="transparent")
            f_top_c.pack(fill="x")

            ctk.CTkLabel(
                f_top_c,
                text=f"{c['curso_codigo']} · {c['curso_nombre']} ({c['nombre_grupo']})",
                font=(F_TITULO, 12, "bold"),
                text_color=TEXTO
            ).pack(side="left")

            # Determinar estado
            insc = c.get("total_inscritos") or 0
            marc = c.get("total_marcados") or 0
            pres = c.get("total_presentes") or 0
            est_sesion = c.get("estado_sesion") or "Abierta"

            if est_sesion == "Cerrada":
                badge_bg = ("#E2E8F0", "#1E3A6D")
                badge_fg = ("#475569", "#BAE6FD")
                h_c = str(c.get("hora_cierre"))[:5] if c.get("hora_cierre") else ""
                badge_txt = f"🔒 Concluida ({h_c})" if h_c else "🔒 Concluida"
            elif marc > 0:
                pct = int((pres / insc * 100)) if insc > 0 else 100
                badge_bg = ("#ECFDF5", "#064E3B")
                badge_fg = ("#059669", "#34D399")
                badge_txt = f"🟢 En Clase ({pres}/{insc} · {pct}%)"
            else:
                badge_bg = ("#FFFBEB", "#78350F")
                badge_fg = ("#D97706", "#FBBF24")
                badge_txt = "🟡 En Espera"

            f_badge = ctk.CTkFrame(f_top_c, fg_color=badge_bg, corner_radius=8)
            f_badge.pack(side="right")
            ctk.CTkLabel(
                f_badge,
                text=f" {badge_txt} ",
                font=(F_TEXTO, 10, "bold"),
                text_color=badge_fg
            ).pack(padx=6, pady=2)

            # Subtitulo docente y aula
            doc = c.get("docente_nombre") or "Docente no asignado"
            aula = c.get("aula") or "Aula Principal"
            h_ini = str(c.get("hora_inicio"))[:5] if c.get("hora_inicio") else ""
            h_fin = str(c.get("hora_fin"))[:5] if c.get("hora_fin") else ""
            horario = f" · {h_ini}-{h_fin}" if h_ini else ""

            ctk.CTkLabel(
                f_info,
                text=f"👨‍🏫 {doc}  |  📍 {aula}{horario}",
                font=(F_TEXTO, 10),
                text_color=SUAVE
            ).pack(anchor="w", pady=(2, 0))
