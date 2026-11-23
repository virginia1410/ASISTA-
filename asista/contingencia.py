"""Módulo de Protocolo de Contingencia y Tolerancia a Fallos (Modo Offline).
Almacena registros en búfer local SQLite cuando se cae la red o el servidor MySQL,
y los sincroniza automáticamente cuando se restablece la conexión.
"""
import os
import sqlite3
from datetime import datetime, date, time

import sys
if getattr(sys, "frozen", False):
    _base_contingencia = os.path.dirname(sys.executable)
else:
    _base_contingencia = os.path.dirname(os.path.abspath(__file__))
RUTA_BD_LOCAL = os.path.join(_base_contingencia, "contingencia_local.db")


def obtener_conexion():
    conn = sqlite3.connect(RUTA_BD_LOCAL)
    conn.row_factory = sqlite3.Row
    return conn


def inicializar_contingencia():
    """Crea la tabla del búfer local si no existe."""
    with obtener_conexion() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS cola_contingencia (
            id_cola INTEGER PRIMARY KEY AUTOINCREMENT,
            cedula TEXT NOT NULL,
            id_persona INTEGER,
            id_cohorte INTEGER,
            fecha TEXT NOT NULL,
            hora TEXT NOT NULL,
            tipo_evento TEXT NOT NULL, -- 'Entrada', 'Salida', 'Ausente', 'Clase'
            estado TEXT NOT NULL,      -- 'Presente', 'Retraso', 'Salida Temprana', 'Ausente'
            observaciones TEXT,
            id_usuario INTEGER,
            creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            sincronizado INTEGER DEFAULT 0,
            error_sincronizacion TEXT
        );
        """)
        try:
            conn.execute("ALTER TABLE cola_contingencia ADD COLUMN id_cohorte INTEGER;")
        except Exception:
            pass
        conn.commit()


# Inicializar al importar
inicializar_contingencia()


def guardar_evento_contingencia(cedula, id_persona, fecha, hora, tipo_evento, estado, observaciones="", id_usuario=None, id_cohorte=None):
    """Guarda un registro de marcaje en el almacenamiento seguro local ante falla de red."""
    f_str = fecha.isoformat() if isinstance(fecha, (date, datetime)) else str(fecha)
    h_str = hora.strftime("%H:%M:%S") if isinstance(hora, time) else str(hora)

    with obtener_conexion() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO cola_contingencia 
            (cedula, id_persona, id_cohorte, fecha, hora, tipo_evento, estado, observaciones, id_usuario, sincronizado)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
        """, (cedula, id_persona, id_cohorte, f_str, h_str, tipo_evento, estado, observaciones or "", id_usuario))
        conn.commit()
        return cur.lastrowid


def contar_pendientes():
    """Devuelve la cantidad de registros en contingencia que aún no se han sincronizado con MySQL."""
    try:
        with obtener_conexion() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM cola_contingencia WHERE sincronizado = 0")
            return cur.fetchone()[0]
    except Exception:
        return 0


def obtener_pendientes():
    """Devuelve la lista de registros pendientes por sincronizar."""
    with obtener_conexion() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM cola_contingencia WHERE sincronizado = 0 ORDER BY id_cola ASC")
        return [dict(r) for r in cur.fetchall()]


def sincronizar_con_mysql(db):
    """Intenta transferir todos los registros pendientes del búfer local al servidor MySQL central."""
    pendientes = obtener_pendientes()
    if not pendientes:
        return 0, 0, "No hay registros pendientes por sincronizar."

    # Verificar si MySQL está accesible
    try:
        db.connection()
    except Exception as e:
        return 0, len(pendientes), f"El servidor MySQL sigue inaccesible: {e}"

    exitosos = 0
    fallidos = 0

    with obtener_conexion() as conn:
        for r in pendientes:
            id_cola = r["id_cola"]
            cedula = r["cedula"]
            f_str = r["fecha"]
            h_str = r["hora"]
            tipo_evento = r["tipo_evento"]
            estado = r["estado"]
            obs = r["observaciones"] or ""
            id_usuario = r["id_usuario"]

            try:
                # Obtener o verificar id_persona
                p = db.persona_por_cedula(cedula)
                if not p:
                    raise ValueError(f"No existe persona activa con cédula {cedula} en el servidor central.")

                id_persona = p["id_persona"]
                f_date = datetime.strptime(f_str, "%Y-%m-%d").date()
                h_time = datetime.strptime(h_str, "%H:%M:%S").time()

                ex = db.asistencia_de(id_persona, f_date)

                if r.get("id_cohorte") or tipo_evento == "Clase":
                    db.registrar_asistencia_estudiante_curso(
                        id_persona, r["id_cohorte"], f_date, h_time, estado,
                        obs + " [Sincronizado vía contingencia]", id_usuario
                    )
                elif tipo_evento == "Entrada":
                    obs_final = (obs + " [Sincronizado vía contingencia]").strip()
                    db.registrar_entrada(id_persona, f_date, h_time, estado, obs_final, id_usuario, existe=bool(ex))
                elif tipo_evento == "Salida":
                    if ex:
                        obs_final = " | ".join(x for x in (ex.get("observaciones") or "", obs, "[Sincronizado vía contingencia]") if x)
                        db.registrar_salida(ex["id_asistencia"], h_time, estado, obs_final)
                    else:
                        db.registrar_entrada(id_persona, f_date, None, estado, obs, id_usuario, existe=False)
                        ex2 = db.asistencia_de(id_persona, f_date)
                        db.registrar_salida(ex2["id_asistencia"], h_time, estado, obs + " [Sincronizado vía contingencia]")
                elif tipo_evento == "Ausente":
                    if not ex:
                        db.registrar_ausencia(id_persona, f_date, obs + " [Sincronizado vía contingencia]", id_usuario)

                # Marcar como sincronizado
                conn.execute("UPDATE cola_contingencia SET sincronizado = 1, error_sincronizacion = NULL WHERE id_cola = ?", (id_cola,))
                exitosos += 1

            except Exception as err:
                fallidos += 1
                conn.execute("UPDATE cola_contingencia SET error_sincronizacion = ? WHERE id_cola = ?", (str(err), id_cola))

        conn.commit()

    return exitosos, fallidos, f"Sincronización finalizada: {exitosos} subidos a MySQL, {fallidos} con observaciones."
