"""Módulo Marcaje: Registro diario de asistencias con Protocolo de Escáner y Búfer de Contingencia Offline."""
from datetime import date, datetime
import customtkinter as ctk
from tkinter import messagebox

import config
from db import fmt_hora, resolver_turno_persona
from tema import (
    ACENTO, ACENTO_H, ACENTO_TEXTO, AVISO, AVISO_BG, AVISO_TEXTO, BORDE, CARD,
    ESTADO_COLOR, F_TEXTO, F_TITULO, OK, PRIMARIO, SUAVE, SUAVE_BG, TEXTO
)
from .ui_utils import Vista, seguro, tarjeta, campo, boton, etiqueta, area, chip, feedback_boton
import contingencia


def _beep_exito():
    try:
        import winsound
        winsound.Beep(1400, 100)
    except Exception:
        pass


def _beep_alerta():
    try:
        import winsound
        winsound.Beep(700, 200)
    except Exception:
        pass


class Marcaje(Vista):
    def __init__(self, master, app):
        super().__init__(master, app)
        self.persona = None

        # Encabezado
        self.titulo("Control de Asistencia y Marcaje", "Lector de carnet y portal móvil · Tolerancia a fallos")

        # Barra superior de protocolo de escáner y contingencia
        barra_protocolo = ctk.CTkFrame(self, fg_color="transparent")
        barra_protocolo.pack(fill="x", padx=30, pady=(0, 12))

        self.sw_escaner = ctk.CTkSwitch(
            barra_protocolo, text="Modo Escáner / Lector de Carnets (Automático)",
            font=(F_TEXTO, 13, "bold"), text_color=TEXTO, progress_color=ACENTO
        )
        self.sw_escaner.select()  # Activado por defecto para facilitar el flujo en garita
        self.sw_escaner.pack(side="left")

        # Indicador visual de escáner manos libres
        self.badge_escaner = ctk.CTkFrame(
            barra_protocolo, fg_color=SUAVE_BG, corner_radius=12,
            border_width=1, border_color=BORDE
        )
        self.badge_escaner.pack(side="left", padx=14)
        ctk.CTkLabel(
            self.badge_escaner,
            text="✓ Captura Automática Manos Libres Activa (Sin Clic)",
            font=(F_TEXTO, 11, "bold"),
            text_color=ACENTO_TEXTO
        ).pack(padx=10, pady=4)

        # Botón e indicador de contingencia
        self.btn_sync = ctk.CTkButton(
            barra_protocolo, text="Sincronizar Contingencia (0)",
            command=self.sincronizar_contingencia,
            fg_color=AVISO, hover_color=AVISO, text_color="#FFFFFF",
            height=32, corner_radius=16, font=(F_TEXTO, 11, "bold")
        )
        self.btn_sync.pack(side="right")

        self.btn_portal_movil = ctk.CTkButton(
            barra_protocolo,
            text="Portal móvil",
            command=self._abrir_qr_movil,
            fg_color=ACENTO,
            hover_color=ACENTO_H,
            text_color=PRIMARIO,
            height=32,
            corner_radius=16,
            font=(F_TEXTO, 11, "bold"),
        )
        self.btn_portal_movil.pack(side="right", padx=(0, 8))

        # Cuerpo principal
        cuerpo = ctk.CTkFrame(self, fg_color="transparent")
        cuerpo.pack(fill="both", expand=True, padx=30, pady=(0, 20))
        cuerpo.grid_columnconfigure(0, weight=3)
        cuerpo.grid_columnconfigure(1, weight=2, minsize=300)
        cuerpo.grid_rowconfigure(0, weight=1)

        izq = ctk.CTkFrame(cuerpo, fg_color="transparent")
        izq.grid(row=0, column=0, sticky="new", padx=(0, 16))

        # Caja de entrada
        caja = tarjeta(izq)
        caja.pack(fill="x")
        f = ctk.CTkFrame(caja, fg_color="transparent")
        f.pack(fill="x", padx=20, pady=16)

        self.e_ced = campo(f, placeholder_text="Pase el carnet o escriba la cédula y presione Enter…", height=48, font=(F_TEXTO, 16))
        self.e_ced.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.e_ced.bind("<Return>", lambda e: self.procesar_lector())

        # Intercepción global de teclado para escáner manos libres (sin necesidad de clic)
        self.bind_all("<Key>", self._interceptar_teclado_escaner, add="+")
        self.bind("<Button-1>", lambda e: self.e_ced.focus_set())

        boton(f, "Buscar / Marcar", "primario", self.procesar_lector, width=140, height=48).pack(side="left")

        # Ficha de la persona
        res = tarjeta(izq)
        res.pack(fill="x", pady=(14, 0))
        cab = ctk.CTkFrame(res, fg_color="transparent")
        cab.pack(fill="x", padx=20, pady=(16, 8))

        self.avatar = ctk.CTkLabel(cab, text="?", width=72, height=72, corner_radius=36, fg_color=PRIMARIO,
                                   text_color="white", font=(F_TITULO, 24, "bold"))
        self.avatar.pack(side="left")

        info = ctk.CTkFrame(cab, fg_color="transparent")
        info.pack(side="left", padx=16)
        self.l_nombre = ctk.CTkLabel(info, text="Esperando lectura de carnet…", font=(F_TITULO, 20, "bold"),
                                     text_color=TEXTO, anchor="w")
        self.l_nombre.pack(anchor="w")
        self.l_detalle = etiqueta(info, "Escanee el código de barras o ingrese el número.", font=(F_TEXTO, 13))
        self.l_detalle.pack(anchor="w")
        self.l_hoy = etiqueta(info, "", font=(F_TEXTO, 13, "bold"))
        self.l_hoy.pack(anchor="w")

        etiqueta(res, "Justificación / observaciones (obligatoria en retrasos o salidas manuales)").pack(
            fill="x", padx=20)
        self.txt = area(res, height=70)
        self.txt.pack(fill="x", padx=20, pady=(4, 10))

        bt = ctk.CTkFrame(res, fg_color="transparent")
        bt.pack(fill="x", padx=20, pady=(0, 8))
        for i, (t, tipo, cmd) in enumerate([("Registrar Entrada", "ok", self.entrada),
                                            ("Registrar Salida", "primario", self.salida),
                                            ("Marcar Ausente", "acento", self.ausente)]):
            bt.grid_columnconfigure(i, weight=1, uniform="b")
            btn = boton(bt, t, tipo, cmd, height=42)
            btn.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 8, 0))
            setattr(self, ("btn_entrada", "btn_salida", "btn_ausente")[i], btn)

        self.msg = ctk.CTkLabel(
            res, text="", font=(F_TEXTO, 13, "bold"), anchor="w", wraplength=550,
            corner_radius=10, height=38, border_width=1, border_color=BORDE
        )
        self.msg.pack(fill="x", padx=20, pady=(4, 14))

        # Panel lateral de reglas y estatus
        der = tarjeta(cuerpo)
        der.grid(row=0, column=1, sticky="new")

        ctk.CTkLabel(der, text="Reglas de Asistencia por Turno", font=(F_TITULO, 16, "bold"), text_color=TEXTO, anchor="w").pack(
            fill="x", padx=20, pady=(16, 8))

        # Tarjeta informativa de horarios institucionales
        self.f_horarios_info = ctk.CTkFrame(
            der, fg_color=CARD, corner_radius=10, border_width=1, border_color=BORDE
        )
        self.f_horarios_info.pack(fill="x", padx=18, pady=(0, 10))
        self.l_horarios_txt = ctk.CTkLabel(
            self.f_horarios_info,
            text="",
            font=(F_TEXTO, 11),
            text_color=ACENTO_TEXTO,
            justify="left",
            anchor="w"
        )
        self.l_horarios_txt.pack(fill="x", padx=12, pady=8)
        self._actualizar_info_horarios()

        for tag, color, txt in [
            ("Presente", OK, "Llegada puntual según su turno"),
            ("Retraso", AVISO, "Entrada posterior a la hora límite"),
            ("Salida Temprana", AVISO, "Salida antes del horario mínimo"),
            ("Ausente", AVISO, "Inasistencia registrada")
        ]:
            r = ctk.CTkFrame(der, fg_color="transparent")
            r.pack(fill="x", padx=20, pady=4)
            chip(r, tag, color).pack(side="left")
            etiqueta(r, txt, color=TEXTO).pack(side="left", padx=8)

        etiqueta(
            der,
            "El lector USB envía la cédula con terminación Enter y ejecuta el registro en menos de 0.5s.",
            font=(F_TEXTO, 11), wraplength=260
        ).pack(fill="x", padx=20, pady=(12, 10))

        ctk.CTkFrame(der, height=1, fg_color=BORDE).pack(fill="x", padx=20, pady=8)

        ctk.CTkLabel(der, text="Protocolo de Contingencia", font=(F_TITULO, 15, "bold"), text_color=TEXTO, anchor="w").pack(
            fill="x", padx=20, pady=(4, 4))
        etiqueta(
            der,
            "Si la red o el servidor central fallan, el sistema conmuta automáticamente a búfer local SQLite.",
            font=(F_TEXTO, 10.5), wraplength=260
        ).pack(fill="x", padx=20, pady=(0, 16))

    def _interceptar_teclado_escaner(self, event):
        """Intercepción global para que el escáner registre la cédula sin necesidad de hacer clic en la barra."""
        if not self.winfo_ismapped():
            return

        foco = self.focus_get()
        if foco is not None:
            # Si el foco está en otra ventana modal, no interferir
            try:
                if foco.winfo_toplevel() != self.winfo_toplevel():
                    return
            except Exception:
                pass
            # Si el usuario está escribiendo en el cuadro de justificaciones
            if hasattr(self, "txt") and (foco == self.txt or foco == getattr(self.txt, "_textbox", None)):
                return
            # Si ya está en la barra de cédula
            if hasattr(self, "e_ced") and (foco == self.e_ced or foco == getattr(self.e_ced, "_entry", None)):
                return

        # Si se presionó Enter
        if event.keysym in ("Return", "KP_Enter"):
            self.after(20, self.procesar_lector)
            return

        # Si es un carácter imprimible (dígitos, letras, guiones de cédula)
        if event.char and event.char.isprintable() and len(event.char) == 1:
            if hasattr(self, "e_ced"):
                self.e_ced.focus_set()
                self.e_ced.insert("end", event.char)

    def _abrir_qr_movil(self):
        from .componentes import DialogoQRMovil
        DialogoQRMovil(self)

    def refrescar(self):
        self._actualizar_info_horarios()
        self.actualizar_contador_contingencia()
        self.after(100, lambda: self.e_ced.focus_set())

    def actualizar_contador_contingencia(self):
        n = contingencia.contar_pendientes()
        if n > 0:
            self.btn_sync.configure(
                text=f"Sincronizar Contingencia ({n} pendientes)",
                fg_color=ACENTO, hover_color=ACENTO_H
            )
        else:
            self.btn_sync.configure(
                text="Contingencia: Al día (0)",
                fg_color=OK[0], hover_color=OK[1]
            )

    def sincronizar_contingencia(self):
        exitos, fallos, msg = contingencia.sincronizar_con_mysql(self.db)
        self.actualizar_contador_contingencia()
        if exitos > 0:
            messagebox.showinfo("Sincronización Exitosa", msg)
        else:
            messagebox.showwarning("Información de Sincronización", msg)

    def _actualizar_info_horarios(self):
        h = getattr(config, "HORARIOS_TURNO", {})
        m_ent = h.get("Mañana", {}).get("str_entrada", "07:15")
        m_sal = h.get("Mañana", {}).get("str_salida", "12:00")
        t_ent = h.get("Tarde", {}).get("str_entrada", "12:45")
        t_sal = h.get("Tarde", {}).get("str_salida", "17:30")
        txt = (
            f"🌅 Turno Mañana: Entrada hasta {m_ent} | Salida {m_sal}\n"
            f"🌇 Turno Tarde:  Entrada hasta {t_ent} | Salida {t_sal}"
        )
        if hasattr(self, "l_horarios_txt"):
            self.l_horarios_txt.configure(text=txt)

    def _aviso(self, texto, color):
        if isinstance(color, tuple):
            color_texto = color[0]
        else:
            color_texto = color

        if not texto:
            self.msg.configure(text="", fg_color="transparent", border_color="transparent")
            return

        if color_texto in (OK[0], OK[1], ACENTO[0], ACENTO[1]):
            fondo, borde, texto_color = (SUAVE_BG, BORDE, ACENTO_TEXTO)
        elif color_texto in (AVISO[0], AVISO[1]):
            fondo, borde, texto_color = (AVISO_BG, AVISO, AVISO_TEXTO)
        else:
            fondo, borde, texto_color = (CARD, BORDE, ACENTO_TEXTO)
        self.msg.configure(
            text=f"  {texto}", text_color=texto_color, fg_color=fondo, border_color=borde
        )

    def procesar_lector(self):
        """Punto de entrada cuando se escanea un carnet o se presiona Enter."""
        cedula = self.e_ced.get().strip()
        self.e_ced.delete(0, "end")
        self.e_ced.focus_set()
        if not cedula:
            return

        # Desduplicación inteligente si vino carácter por carácter duplicado (ej: 3311122233778899)
        solo_num = "".join(c for c in cedula if c.isdigit())
        if solo_num and len(solo_num) >= 12 and len(solo_num) % 2 == 0:
            if all(solo_num[i] == solo_num[i+1] for i in range(0, len(solo_num), 2)):
                posible_dedup = "".join(solo_num[i] for i in range(0, len(solo_num), 2))
                try:
                    if not self.db.persona_por_cedula(cedula) and self.db.persona_por_cedula(posible_dedup):
                        cedula = posible_dedup
                except Exception:
                    cedula = posible_dedup

        if self.sw_escaner.get():
            self._marcado_automatico_escaner(cedula)
        else:
            self.buscar(cedula)

    def _marcado_automatico_escaner(self, cedula):
        """Protocolo Rápido: decide automáticamente si es Entrada o Salida."""
        ahora = datetime.now()
        hora = ahora.time().replace(microsecond=0)
        hoy = ahora.date()

        try:
            p = self.db.persona_por_cedula(cedula)
        except Exception:
            # Falla de conexión a MySQL -> Activar Contingencia
            self._guardar_contingencia_automatica(cedula, hoy, hora)
            return

        if not p:
            _beep_alerta()
            self.avatar.configure(text="?", fg_color=AVISO)
            self.l_nombre.configure(text=f"Cédula {cedula} no encontrada")
            self.l_detalle.configure(text="No está registrado en la base de datos.")
            self._aviso(f"Carnet no reconocido: C.I. {cedula}", AVISO)
            self.e_ced.delete(0, "end")
            self.e_ced.focus_set()
            return

        self.persona = p
        turno_activo = resolver_turno_persona(p, hora)
        horarios = getattr(config, "HORARIOS_TURNO", {}).get(turno_activo, {})
        limite_entrada = horarios.get("entrada_limite", config.HORA_LIMITE_ENTRADA)
        minima_salida = horarios.get("salida_minima", config.HORA_SALIDA_MINIMA)

        self.avatar.configure(text=(p["nombre"][:1] + p["apellido"][:1]).upper(), fg_color=PRIMARIO)
        self.l_nombre.configure(text=f"{p['nombre']} {p['apellido']}")
        self.l_detalle.configure(text=f"{p['tipo_persona']} · {p['detalle'] or '—'} · Turno: {turno_activo} · C.I. {p['cedula']}")

        try:
            ex = self.db.asistencia_de(p["id_persona"], hoy)
        except Exception:
            self._guardar_contingencia_automatica(cedula, hoy, hora, p["id_persona"])
            return

        # Decisión automática con control de turno:
        if not ex or ex["hora_entrada"] is None:
            # REGISTRAR ENTRADA
            estado = "Retraso" if hora > limite_entrada else "Presente"
            obs = f"Entrada puntual por escáner (Turno {turno_activo})" if estado == "Presente" else f"Llegada tardía por escáner (Turno {turno_activo} > {limite_entrada:%H:%M})"

            try:
                self.db.registrar_entrada(p["id_persona"], hoy, hora, estado, obs, config.USUARIO_ID, existe=bool(ex))
                _beep_exito()
                self._listo(f"✓ Entrada registrada a las {hora:%H:%M} · {estado} (Turno {turno_activo})", OK if estado == "Presente" else AVISO)
            except Exception:
                self._guardar_contingencia_automatica(cedula, hoy, hora, p["id_persona"], "Entrada", estado, obs)

        elif ex["hora_salida"] is None:
            # Validar si es doble escaneo / duplicado accidental (< 120 segundos tras la entrada)
            h_ent = ex.get("hora_entrada")
            t_ent = None
            if isinstance(h_ent, str):
                try:
                    t_ent = datetime.strptime(h_ent[:8], "%H:%M:%S").time()
                except Exception:
                    pass
            elif isinstance(h_ent, datetime):
                t_ent = h_ent.time()
            elif hasattr(h_ent, "strftime"):
                t_ent = h_ent

            if t_ent:
                dt_ent = datetime.combine(hoy, t_ent)
                if 0 <= (ahora - dt_ent).total_seconds() < 120:
                    _beep_alerta()
                    self._aviso(f"ℹ Doble lectura prevenida: {p['nombre']} ya registró su Entrada a las {dt_ent.strftime('%I:%M %p')} (Turno {turno_activo}).", AVISO)
                    self.e_ced.delete(0, "end")
                    self.e_ced.focus_set()
                    return

            # REGISTRAR SALIDA
            temprana = hora < minima_salida
            estado = "Salida Temprana" if temprana else ex["estado"]
            obs = f"Salida anticipada por escáner (Turno {turno_activo} < {minima_salida:%H:%M})" if temprana else f"Salida registrada por escáner (Turno {turno_activo})"
            obs_final = " | ".join(x for x in ((ex.get("observaciones") or "").strip(), obs) if x)

            try:
                self.db.registrar_salida(ex["id_asistencia"], hora, estado, obs_final)
                _beep_exito()
                self._listo(f"✓ Salida registrada a las {hora:%H:%M}" + (f" (Salida Temprana - Turno {turno_activo})" if temprana else f" (Turno {turno_activo})"), AVISO if temprana else OK)
            except Exception:
                self._guardar_contingencia_automatica(cedula, hoy, hora, p["id_persona"], "Salida", estado, obs_final)

        else:
            _beep_alerta()
            self._aviso(f"ℹ {p['nombre']} ya completó su entrada ({fmt_hora(ex['hora_entrada'])}) y salida ({fmt_hora(ex['hora_salida'])}) hoy.", AVISO)

        self.e_ced.delete(0, "end")
        self.e_ced.focus_set()

    def _guardar_contingencia_automatica(self, cedula, fecha, hora, id_persona=None, tipo="Entrada", estado="Presente", obs=""):
        """Guarda en búfer local de contingencia ante caída de red."""
        _beep_alerta()
        contingencia.guardar_evento_contingencia(
            cedula=cedula,
            id_persona=id_persona,
            fecha=fecha,
            hora=hora,
            tipo_evento=tipo,
            estado=estado,
            observaciones=obs or "Guardado automáticamente en contingencia offline",
            id_usuario=config.USUARIO_ID
        )
        self.actualizar_contador_contingencia()
        self._aviso(f"⚡ MODO CONTINGENCIA: Marcaje para C.I. {cedula} guardado localmente en búfer seguro.", AVISO)
        self.e_ced.delete(0, "end")
        self.e_ced.focus_set()

    @seguro
    def buscar(self, cedula=None):
        if cedula:
            self.e_ced.delete(0, "end")
            self.e_ced.insert(0, cedula)
        cedula = self.e_ced.get().strip()
        if not cedula:
            raise UserWarning("Ingrese una cédula.")

        p = self.db.persona_por_cedula(cedula)
        if not p:
            self.persona = None
            self.avatar.configure(text="?", fg_color=AVISO)
            self.l_nombre.configure(text="Cédula no encontrada")
            self.l_detalle.configure(text="Verifique el número o regístrela en el módulo Personas.")
            self.l_hoy.configure(text="")
            self._aviso("", TEXTO)
            return

        self.persona = p
        self.avatar.configure(text=(p["nombre"][:1] + p["apellido"][:1]).upper(), fg_color=PRIMARIO)
        self.l_nombre.configure(text=f"{p['nombre']} {p['apellido']}")
        turno_act = resolver_turno_persona(p)
        self.l_detalle.configure(text=f"{p['tipo_persona']} · {p['detalle'] or '—'} · Turno: {turno_act} · C.I. {p['cedula']}")
        self._aviso("", TEXTO)
        self._estado_hoy()

    def _estado_hoy(self):
        a = self.db.asistencia_de(self.persona["id_persona"], date.today())
        if not a:
            self.l_hoy.configure(text="Hoy: sin registro", text_color=SUAVE)
        else:
            self.l_hoy.configure(text=f"Hoy: {a['estado']} · Entrada {fmt_hora(a['hora_entrada'])} · "
                                      f"Salida {fmt_hora(a['hora_salida'])}", text_color=ESTADO_COLOR[a["estado"]])

    def _requiere_persona(self):
        if not self.persona:
            raise UserWarning("Primero busque una persona por su cédula o pase su carnet.")
        return self.persona

    def _obs(self):
        return self.txt.get("1.0", "end").strip()

    def _listo(self, texto, color=OK):
        self.txt.delete("1.0", "end")
        if self.persona:
            self._estado_hoy()
        self._aviso(texto, color)

    @seguro
    def entrada(self):
        p = self._requiere_persona()
        ahora = datetime.now()
        hora = ahora.time().replace(microsecond=0)
        ex = self.db.asistencia_de(p["id_persona"], ahora.date())
        if ex and ex["hora_entrada"] is not None:
            raise UserWarning("Esta persona ya registró su entrada hoy.")
        turno_activo = resolver_turno_persona(p, hora)
        horarios = getattr(config, "HORARIOS_TURNO", {}).get(turno_activo, {})
        limite_entrada = horarios.get("entrada_limite", config.HORA_LIMITE_ENTRADA)

        estado = "Retraso" if hora > limite_entrada else "Presente"
        obs = self._obs()
        if estado == "Retraso" and len(obs) < 5:
            raise UserWarning(f"Llegó después de la hora límite del Turno {turno_activo} ({limite_entrada:%H:%M}): escriba la justificación del retraso.")
        self.db.registrar_entrada(p["id_persona"], ahora.date(), hora, estado,
                                  obs or (ex["observaciones"] if ex else ""), config.USUARIO_ID, existe=bool(ex))
        _beep_exito()
        self._listo(f"Entrada registrada a las {hora:%H:%M} · {estado} (Turno {turno_activo})", OK if estado == "Presente" else AVISO)
        feedback_boton(self.btn_entrada, "✓ Entrada registrada")

    @seguro
    def salida(self):
        p = self._requiere_persona()
        ahora = datetime.now()
        hora = ahora.time().replace(microsecond=0)
        ex = self.db.asistencia_de(p["id_persona"], ahora.date())
        if not ex or ex["hora_entrada"] is None:
            raise UserWarning("No hay una entrada registrada hoy para esta persona.")
        if ex["hora_salida"] is not None:
            raise UserWarning("Esta persona ya registró su salida hoy.")
        turno_activo = resolver_turno_persona(p, hora)
        horarios = getattr(config, "HORARIOS_TURNO", {}).get(turno_activo, {})
        minima_salida = horarios.get("salida_minima", config.HORA_SALIDA_MINIMA)

        temprana = hora < minima_salida
        obs = self._obs()
        if temprana and len(obs) < 5:
            raise UserWarning(f"Salida antes del horario mínimo del Turno {turno_activo} ({minima_salida:%H:%M}): escriba el motivo del retiro.")
        estado = "Salida Temprana" if temprana else ex["estado"]
        obs_final = " | ".join(x for x in ((ex["observaciones"] or "").strip(), obs) if x)
        self.db.registrar_salida(ex["id_asistencia"], hora, estado, obs_final)
        _beep_exito()
        self._listo(f"Salida registrada a las {hora:%H:%M} (Turno {turno_activo})", AVISO if temprana else OK)
        feedback_boton(self.btn_salida, "✓ Salida registrada")

    @seguro
    def ausente(self):
        p = self._requiere_persona()
        if self.db.asistencia_de(p["id_persona"], date.today()):
            raise UserWarning("Esta persona ya tiene un registro hoy.")
        self.db.registrar_ausencia(p["id_persona"], date.today(), self._obs(), config.USUARIO_ID)
        self._listo("Ausencia registrada", ACENTO)
        feedback_boton(self.btn_ausente, "✓ Ausencia registrada", tipo="acento")
