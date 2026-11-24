"""Capa de acceso a SQLite: base de datos portable, conexión y consultas de ASISTA."""
import calendar
import hashlib
import os
import re
import sqlite3
import subprocess
import threading
from contextlib import contextmanager
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path

import config
from config import DB_CONFIG, DB_PATH


def fmt_hora(v):
    """TIME (timedelta), time o string -> 'HH:MM'."""
    if v is None:
        return "—"
    if isinstance(v, timedelta):
        s = int(v.total_seconds())
        return f"{s // 3600:02d}:{s % 3600 // 60:02d}"
    if isinstance(v, str):
        return v[:5] if len(v) >= 5 else v
    return v.strftime("%H:%M")


CONFLICT_TARGETS = {
    "cierre_diario": "fecha",
    "configuracion_institucional": "clave",
    "periodo": "codigo",
    "curso": "codigo",
    "matricula": "id_persona, id_cohorte",
    "asistencia_curso": "id_cohorte, id_persona, fecha",
    "sesion_clase": "id_cohorte, fecha",
    "usuario": "username",
    "asistencia": "id_persona, fecha",
}


def _adaptar_sql(sql: str) -> str:
    """Adapta sintaxis SQL de MySQL a SQLite."""
    # 1. Quitar cláusulas de collation y engine MySQL
    sql = re.sub(r'\bCOLLATE\s+utf8mb4_[a-zA-Z0-9_]+\b', '', sql, flags=re.IGNORECASE)
    sql = re.sub(r'\bENGINE\s*=\s*[a-zA-Z0-9_]+\b', '', sql, flags=re.IGNORECASE)
    sql = re.sub(r'\bDEFAULT\s+CHARSET\s*=\s*[a-zA-Z0-9_]+\b', '', sql, flags=re.IGNORECASE)
    sql = re.sub(r'\bCHARSET\s*=\s*[a-zA-Z0-9_]+\b', '', sql, flags=re.IGNORECASE)

    # 2. Convertir ENUM(...) a TEXT
    sql = re.sub(r'\bENUM\s*\([^)]*\)', 'TEXT', sql, flags=re.IGNORECASE)

    # 3. Convertir tipos MySQL comunes a SQLite
    sql = re.sub(r'\bINT(?:EGER)?\s+UNSIGNED\s+AUTO_INCREMENT\s+PRIMARY\s+KEY\b', 'INTEGER PRIMARY KEY AUTOINCREMENT', sql, flags=re.IGNORECASE)
    sql = re.sub(r'\bAUTO_INCREMENT\b', 'AUTOINCREMENT', sql, flags=re.IGNORECASE)
    sql = re.sub(r'\b(?:TINYINT|SMALLINT|MEDIUMINT|BIGINT|INT)\s*(?:\(\d+\))?\s*(?:UNSIGNED)?\b', 'INTEGER', sql, flags=re.IGNORECASE)

    # 4. Quitar KEY idx_...(...) que SQLite no soporta dentro de CREATE TABLE
    sql = re.sub(r'^\s*KEY\s+[a-zA-Z0-9_]+\s*\([^)]+\),?\s*$', '', sql, flags=re.IGNORECASE | re.MULTILINE)
    sql = re.sub(r'\bUNIQUE\s+KEY\s+[a-zA-Z0-9_]+\s*', 'UNIQUE ', sql, flags=re.IGNORECASE)

    # Limpiar comas huérfanas antes de cerrar paréntesis en DDL
    sql = re.sub(r',\s*\)', ')', sql)

    # 5. Interceptar DESCRIBE y SHOW TABLES de MySQL
    stripped = sql.strip().rstrip(';')
    if re.match(r'^DESCRIBE\s+([a-zA-Z0-9_]+)$', stripped, flags=re.IGNORECASE):
        tbl = re.match(r'^DESCRIBE\s+([a-zA-Z0-9_]+)$', stripped, flags=re.IGNORECASE).group(1)
        return f"PRAGMA table_info({tbl})"
    if re.match(r'^SHOW\s+TABLES$', stripped, flags=re.IGNORECASE):
        return "SELECT name AS Tables_in_db FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"

    # 6. Traducir ON DUPLICATE KEY UPDATE de MySQL a SQLite ON CONFLICT DO UPDATE SET
    if "ON DUPLICATE KEY UPDATE" in sql.upper():
        m = re.search(r'INSERT\s+(?:OR\s+\w+\s+)?INTO\s+[`"]?([a-zA-Z0-9_]+)[`"]?', sql, re.IGNORECASE)
        if m:
            tbl_name = m.group(1).lower()
            target = CONFLICT_TARGETS.get(tbl_name)
            if target:
                sql = re.sub(r'ON\s+DUPLICATE\s+KEY\s+UPDATE', f'ON CONFLICT({target}) DO UPDATE SET', sql, flags=re.IGNORECASE)
                sql = re.sub(r'\bVALUES\s*\(\s*([a-zA-Z0-9_]+)\s*\)', r'excluded.\1', sql, flags=re.IGNORECASE)

    # 7. Reemplazar %s por ? de forma segura respetando % literals (ej: LIKE '%...%')
    sql = sql.replace('%%', '__ESCAPED_PERCENT__')
    sql = sql.replace('%s', '?')
    sql = sql.replace('__ESCAPED_PERCENT__', '%')
    return sql


def _adaptar_params(params):
    """Adapta tipos de parámetros de Python para SQLite."""
    if not params:
        return ()
    if isinstance(params, (str, bytes)):
        params = (params,)
    elif not isinstance(params, (list, tuple, set)):
        params = (params,)
    new_p = []
    for p in params:
        if isinstance(p, Decimal):
            new_p.append(float(p))
        elif isinstance(p, (date, datetime)):
            new_p.append(p.isoformat())
        elif isinstance(p, time):
            new_p.append(p.strftime("%H:%M:%S"))
        else:
            new_p.append(p)
    return tuple(new_p)


def _sqlite_row_factory(cursor, row):
    """Convierte filas de SQLite a diccionario y parsea fechas automáticamente."""
    d = {}
    for idx, col in enumerate(cursor.description):
        name = col[0]
        val = row[idx]
        if isinstance(val, str):
            if len(val) == 10 and val[4] == '-' and val[7] == '-':
                try:
                    val = datetime.strptime(val, "%Y-%m-%d").date()
                except Exception:
                    pass
            elif len(val) >= 19 and val[4] == '-' and val[7] == '-' and val[10] in (' ', 'T'):
                try:
                    val = datetime.strptime(val[:19].replace('T', ' '), "%Y-%m-%d %H:%M:%S")
                except Exception:
                    pass
        d[name] = val
    return d


class _CursorProxy:
    """Cursor envoltorio que traduce sintaxis SQL y emula MySQL Dictionary Cursor."""
    def __init__(self, raw_cur):
        self._cur = raw_cur
        self._is_describe = False

    def execute(self, sql, params=()):
        clean_sql = _adaptar_sql(sql)
        self._is_describe = clean_sql.startswith("PRAGMA table_info")
        clean_params = _adaptar_params(params)
        return self._cur.execute(clean_sql, clean_params)

    def executemany(self, sql, seq_of_params):
        clean_sql = _adaptar_sql(sql)
        clean_seq = [_adaptar_params(p) for p in seq_of_params]
        return self._cur.executemany(clean_sql, clean_seq)

    def fetchone(self):
        row = self._cur.fetchone()
        if self._is_describe and row is not None:
            # PRAGMA table_info: cid, name, type, notnull, dflt_value, pk
            # Mapear a MySQL DESCRIBE: Field, Type, Null, Key, Default, Extra
            field_name = row["name"] if isinstance(row, dict) else row[1]
            return {"Field": field_name, "Type": "TEXT", "Null": "YES", "Key": "", "Default": None, "Extra": ""}
        return row

    def fetchall(self):
        rows = self._cur.fetchall()
        if self._is_describe and rows:
            mapped = []
            for r in rows:
                field_name = r["name"] if isinstance(r, dict) else r[1]
                mapped.append({"Field": field_name, "Type": "TEXT", "Null": "YES", "Key": "", "Default": None, "Extra": ""})
            return mapped
        return rows

    def fetchmany(self, size=None):
        return self._cur.fetchmany(size) if size else self._cur.fetchmany()

    @property
    def lastrowid(self):
        return self._cur.lastrowid

    @property
    def rowcount(self):
        return self._cur.rowcount

    @property
    def description(self):
        return self._cur.description

    def close(self):
        return self._cur.close()


def _crear_conexion_sqlite(ruta_bd):
    """Crea una conexión a SQLite con WAL, Foreign Keys y funciones de compatibilidad MySQL."""
    conn = sqlite3.connect(str(ruta_bd), check_same_thread=False, timeout=30.0)
    conn.row_factory = _sqlite_row_factory
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA busy_timeout = 30000;")

    # Funciones de compatibilidad MySQL registradas en SQLite
    conn.create_function("CONCAT", -1, lambda *args: "".join(str(a) for a in args if a is not None))
    conn.create_function("CONCAT_WS", -1, lambda sep, *args: "" if sep is None else str(sep).join(str(a) for a in args if a is not None))
    conn.create_function("IF", 3, lambda cond, a, b: a if cond else b)
    conn.create_function("CURDATE", 0, lambda: date.today().isoformat())
    conn.create_function("NOW", 0, lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    conn.create_function("CHAR_LENGTH", 1, lambda v: len(str(v)) if v is not None else 0)
    conn.create_function("SHA2", 2, lambda v, b: hashlib.sha256(str(v).encode('utf-8')).hexdigest() if v is not None else None)
    conn.create_function("ELT", -1, lambda idx, *args: args[int(idx) - 1] if 1 <= int(idx) <= len(args) else None)
    conn.create_function("WEEKDAY", 1, lambda v: datetime.strptime(str(v)[:10], "%Y-%m-%d").weekday() if v else 0)
    conn.create_function("LPAD", 3, lambda s, n, pad: str(s).rjust(int(n), str(pad)))
    conn.create_function("DAY", 1, lambda v: int(str(v)[8:10]) if v and len(str(v)) >= 10 else 1)
    conn.create_function("MONTH", 1, lambda v: int(str(v)[5:7]) if v and len(str(v)) >= 7 else 1)
    conn.create_function("YEAR", 1, lambda v: int(str(v)[0:4]) if v and len(str(v)) >= 4 else 2026)

    def _date_format(val, fmt):
        if not val:
            return ""
        try:
            py_fmt = fmt.replace("%i", "%M").replace("%s", "%S").replace("%k", "%H")
            if isinstance(val, str):
                dt = datetime.strptime(val[:19].replace('T', ' '), "%Y-%m-%d %H:%M:%S" if len(val) > 10 else "%Y-%m-%d")
            elif isinstance(val, (date, datetime)):
                dt = val
            else:
                return str(val)
            return dt.strftime(py_fmt)
        except Exception:
            return str(val)

    conn.create_function("DATE_FORMAT", 2, _date_format)
    return conn


PERSONA_SQL = """
SELECT p.id_persona, p.cedula, p.nombre, p.apellido, p.telefono, p.tipo_persona, p.foto,
       e.id_seccion, s.turno, pe.cargo,
       e.representante, e.telefono_representante,
       COALESCE(CONCAT(s.seccion_letra, ' (', s.turno, ')'), pe.cargo) AS detalle
  FROM persona p
  LEFT JOIN estudiante e ON e.id_persona = p.id_persona
  LEFT JOIN seccion s    ON s.id_seccion = e.id_seccion
  LEFT JOIN personal pe  ON pe.id_persona = p.id_persona
"""


def resolver_turno_persona(persona, hora_actual=None):
    """Determina si se evalúa horario de Mañana o Tarde para la persona."""
    if not persona:
        return "Mañana"

    turno = persona.get("turno")
    if turno in ("Mañana", "Tarde"):
        return turno

    if hora_actual is None:
        hora_actual = datetime.now().time()

    return "Mañana" if hora_actual < time(11, 30) else "Tarde"



class Database:
    def __init__(self, cfg=None):
        self.cfg = cfg or DB_CONFIG
        self.db_path = Path(self.cfg.get("database", DB_PATH))
        self._local = threading.local()

    @property
    def _conn(self):
        return getattr(self._local, "conn", None)

    @_conn.setter
    def _conn(self, val):
        self._local.conn = val

    # -- conexión -----------------------------------------------------------
    def connection(self):
        conn = getattr(self._local, "conn", None)
        if conn is None:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            nueva_conexion = _crear_conexion_sqlite(self.db_path)
            try:
                self._asegurar_tablas_base(nueva_conexion, self.db_path)
                self._asegurar_columna_foto(nueva_conexion)
                self._asegurar_esquema_auth(nueva_conexion)
                self._asegurar_indices_integridad(nueva_conexion)
            except Exception:
                nueva_conexion.close()
                raise
            self._local.conn = nueva_conexion
            conn = nueva_conexion
        return conn

    @staticmethod
    def _asegurar_indices_integridad(conn):
        """Asegura que los índices únicos de integridad existan para evitar duplicados en SQLite."""
        cur = conn.cursor()
        try:
            cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_asistencia_persona_fecha ON asistencia (id_persona, fecha);")
            cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_asistencia_cohorte_persona_fecha ON asistencia_curso (id_cohorte, id_persona, fecha);")
            cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_sesion_cohorte_fecha ON sesion_clase (id_cohorte, fecha);")
            cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_matricula_persona_cohorte ON matricula (id_persona, id_cohorte);")
            conn.commit()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
        finally:
            cur.close()

    @staticmethod
    def _asegurar_tablas_base(conn, db_path):
        """Verifica que las tablas esenciales existan; si no, restaura el esquema y datos iniciales."""
        cur = conn.cursor()
        try:
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='persona'")
            if not cur.fetchone():
                db_dir = Path(db_path).resolve().parent
                seed_sql = db_dir / "asista_schema_seed.sql"
                if not seed_sql.exists():
                    seed_sql = config.BASE_DIR / "database" / "asista_schema_seed.sql"
                if seed_sql.exists():
                    conn.execute("PRAGMA foreign_keys = OFF;")
                    with open(seed_sql, "r", encoding="utf-8") as f:
                        conn.executescript(f.read())
                    conn.commit()
                    conn.execute("PRAGMA foreign_keys = ON;")
                else:
                    print(f"Advertencia: No se encontró archivo seed SQL para auto-inicializar.")
        finally:
            cur.close()

    @staticmethod
    def _asegurar_esquema_auth(conn):
        """Asegura columnas para primer inicio de sesión y tabla de bitácora de asistencia en SQLite."""
        cur = conn.cursor()
        try:
            cur.execute("PRAGMA table_info(usuario)")
            cols = [r["name"] if isinstance(r, dict) else r[1] for r in cur.fetchall()]
            if "primer_ingreso" not in cols:
                cur.execute("ALTER TABLE usuario ADD COLUMN primer_ingreso INTEGER NOT NULL DEFAULT 1")
            if "ultimo_cambio_pass" not in cols:
                cur.execute("ALTER TABLE usuario ADD COLUMN ultimo_cambio_pass TEXT NULL")
        finally:
            cur.close()

    @staticmethod
    def _asegurar_columna_foto(conn):
        """Migra instalaciones previas para que la ficha de persona soporte fotos."""
        cur = conn.cursor()
        try:
            cur.execute("PRAGMA table_info(persona)")
            cols = [r["name"] if isinstance(r, dict) else r[1] for r in cur.fetchall()]
            if "foto" not in cols:
                cur.execute("ALTER TABLE persona ADD COLUMN foto TEXT NULL")
        finally:
            cur.close()

    @contextmanager
    def cursor(self, transaccion=False):
        conn = self.connection()
        raw_cur = conn.cursor()
        cur = _CursorProxy(raw_cur)
        try:
            if transaccion and not conn.in_transaction:
                try:
                    raw_cur.execute("BEGIN IMMEDIATE")
                except Exception:
                    pass
            yield cur
            if transaccion:
                conn.commit()
        except Exception:
            if transaccion:
                try:
                    conn.rollback()
                except Exception:
                    pass
            raise
        finally:
            cur.close()

    def fetch_all(self, sql, params=()):
        with self.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()

    def fetch_one(self, sql, params=()):
        rows = self.fetch_all(sql, params)
        return rows[0] if rows else None

    def execute(self, sql, params=()):
        with self.cursor(transaccion=True) as cur:
            cur.execute(sql, params)

    def call(self, nombre, args=()):
        """Ejecuta stored procedures emulados nativamente para SQLite."""
        nom = nombre.lower().strip()
        if nom == "sp_cierre_mensual":
            return self._sp_cierre_mensual(*args)
        elif nom == "sp_reporte_mensual_cedula":
            return self._sp_reporte_mensual_cedula(*args)
        elif nom == "sp_reporte_semestral":
            return self._sp_reporte_semestral(*args)
        else:
            raise NotImplementedError(f"Procedimiento almacenado no soportado en SQLite: {nombre}")

    def _sp_cierre_mensual(self, anio, mes, id_usuario, archivar):
        p_anio = int(anio)
        p_mes = int(mes)
        p_id_usuario = id_usuario
        p_archivar = int(archivar)

        if not (1 <= p_mes <= 12) or p_anio < 2000:
            raise ValueError("Año o mes inválido")

        v_inicio = date(p_anio, p_mes, 1)
        _, last_day = calendar.monthrange(p_anio, p_mes)
        v_fin = date(p_anio, p_mes, last_day) + timedelta(days=1)

        if v_inicio > date.today():
            raise ValueError("No se puede cerrar un mes futuro")

        if self.fetch_one("SELECT 1 FROM cierre_mensual WHERE anio = ? AND mes = ?", (p_anio, p_mes)):
            raise ValueError("Ese mes ya fue cerrado")

        if not self.fetch_one("SELECT 1 FROM asistencia WHERE fecha >= ? AND fecha < ?", (v_inicio.isoformat(), v_fin.isoformat())):
            raise ValueError("No hay registros de asistencia en ese mes")

        with self.cursor(transaccion=True) as cur:
            cur.execute("""
                INSERT INTO asistencia_historico
                  (id_persona, anio, mes, total_asistencias, total_ausencias, total_retrasos,
                   total_salidas_tempranas, total_dias_registrados, id_usuario_cierre)
                SELECT id_persona, ?, ?,
                       SUM(estado = 'Presente'),
                       SUM(estado = 'Ausente'),
                       SUM(estado = 'Retraso'),
                       SUM(estado = 'Salida Temprana'),
                       COUNT(*),
                       ?
                  FROM asistencia
                 WHERE fecha >= ? AND fecha < ?
                 GROUP BY id_persona
            """, (p_anio, p_mes, p_id_usuario, v_inicio.isoformat(), v_fin.isoformat()))
            v_personas = cur.rowcount

            if p_archivar == 1:
                cur.execute("""
                    INSERT INTO asistencia_archivo
                      (id_asistencia, id_persona, fecha, hora_entrada, hora_salida, estado,
                       observaciones, id_usuario_registro)
                    SELECT id_asistencia, id_persona, fecha, hora_entrada, hora_salida, estado,
                           observaciones, id_usuario_registro
                      FROM asistencia
                     WHERE fecha >= ? AND fecha < ?
                """, (v_inicio.isoformat(), v_fin.isoformat()))

                cur.execute("DELETE FROM asistencia WHERE fecha >= ? AND fecha < ?", (v_inicio.isoformat(), v_fin.isoformat()))

            cur.execute("""
                INSERT INTO cierre_mensual (anio, mes, total_personas, archivado, id_usuario_cierre)
                VALUES (?, ?, ?, ?, ?)
            """, (p_anio, p_mes, v_personas, 1 if p_archivar == 1 else 0, p_id_usuario))

        return [[{
            "anio": p_anio,
            "mes": p_mes,
            "personas_consolidadas": v_personas,
            "registros_archivados": "Sí" if p_archivar == 1 else "No",
            "mensaje": "Cierre mensual realizado correctamente"
        }]]

    def _sp_reporte_mensual_cedula(self, cedula, anio, mes):
        p_anio = int(anio)
        p_mes = int(mes)
        if not (1 <= p_mes <= 12) or p_anio < 2000:
            raise ValueError("Año o mes inválido")

        p = self.fetch_one("""
            SELECT p.id_persona, p.cedula, (p.nombre || ' ' || p.apellido) AS nombre_completo, p.tipo_persona,
                   COALESCE(s.grado_ano || '° "' || s.seccion_letra || '" - ' || s.turno, pe.cargo) AS seccion_o_cargo
              FROM persona p
              LEFT JOIN estudiante e ON e.id_persona = p.id_persona
              LEFT JOIN seccion s ON s.id_seccion = e.id_seccion
              LEFT JOIN personal pe ON pe.id_persona = p.id_persona
             WHERE p.cedula = ?
        """, (str(cedula).strip(),))

        if not p:
            raise ValueError("No existe una persona con esa cédula")

        pid = p["id_persona"]
        f_ini = f"{p_anio:04d}-{p_mes:02d}-01"
        _, last_day = calendar.monthrange(p_anio, p_mes)
        f_fin = f"{p_anio:04d}-{p_mes:02d}-{last_day:02d}"

        t = self.fetch_one("""
            SELECT SUM(estado = 'Presente') AS presentes,
                   SUM(estado = 'Ausente') AS ausencias,
                   SUM(estado = 'Retraso') AS retrasos,
                   SUM(estado = 'Salida Temprana') AS salidas_tempranas,
                   COUNT(*) AS total_dias
              FROM v_asistencia_total
             WHERE id_persona = ? AND fecha BETWEEN ? AND ?
        """, (pid, f_ini, f_fin)) or {}

        presentes = t.get("presentes") or 0
        ausencias = t.get("ausencias") or 0
        retrasos = t.get("retrasos") or 0
        salidas_tempranas = t.get("salidas_tempranas") or 0
        total_dias = t.get("total_dias") or 0
        pct = round(100.0 * (presentes + retrasos + salidas_tempranas) / total_dias, 2) if total_dias > 0 else 0.0

        resumen = [{
            "cedula": p["cedula"],
            "nombre_completo": p["nombre_completo"],
            "tipo_persona": p["tipo_persona"],
            "seccion_o_cargo": p["seccion_o_cargo"],
            "anio": p_anio,
            "mes": p_mes,
            "asistencias": presentes,
            "ausencias": ausencias,
            "retrasos": retrasos,
            "salidas_tempranas": salidas_tempranas,
            "dias_registrados": total_dias,
            "porcentaje_asistencia": pct
        }]

        dias_nom = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        rows = self.fetch_all("""
            SELECT fecha, hora_entrada, hora_salida, estado, observaciones
              FROM v_asistencia_total
             WHERE id_persona = ? AND fecha BETWEEN ? AND ?
             ORDER BY fecha
        """, (pid, f_ini, f_fin))
        detalle = []
        for r in rows:
            f_val = r["fecha"]
            if isinstance(f_val, str):
                f_dt = datetime.strptime(f_val[:10], "%Y-%m-%d").date()
            else:
                f_dt = f_val
            detalle.append({
                "fecha": f_dt,
                "dia_semana": dias_nom[f_dt.weekday()],
                "hora_entrada": r["hora_entrada"],
                "hora_salida": r["hora_salida"],
                "estado": r["estado"],
                "observaciones": r["observaciones"]
            })

        return [resumen, detalle]

    def _sp_reporte_semestral(self, cedula, anio, semestre):
        p_anio = int(anio)
        p_sem = int(semestre)
        if p_sem not in (1, 2):
            raise ValueError("Semestre inválido (use 1 o 2)")

        p = self.fetch_one("""
            SELECT p.id_persona, p.cedula, (p.nombre || ' ' || p.apellido) AS nombre_completo, p.tipo_persona
              FROM persona p WHERE p.cedula = ?
        """, (str(cedula).strip(),))

        if not p:
            raise ValueError("No existe una persona con esa cédula")

        pid = p["id_persona"]
        mes_ini = 1 if p_sem == 1 else 7
        mes_fin = 6 if p_sem == 1 else 12

        t = self.fetch_one("""
            SELECT COUNT(*) AS meses_cerrados,
                   SUM(total_asistencias) AS asistencias,
                   SUM(total_ausencias) AS ausencias,
                   SUM(total_retrasos) AS retrasos,
                   SUM(total_salidas_tempranas) AS salidas_tempranas,
                   SUM(total_dias_registrados) AS dias_registrados
              FROM asistencia_historico
             WHERE id_persona = ? AND anio = ? AND mes BETWEEN ? AND ?
        """, (pid, p_anio, mes_ini, mes_fin)) or {}

        meses_cerrados = t.get("meses_cerrados") or 0
        asistencias = t.get("asistencias") or 0
        ausencias = t.get("ausencias") or 0
        retrasos = t.get("retrasos") or 0
        salidas_tempranas = t.get("salidas_tempranas") or 0
        dias_registrados = t.get("dias_registrados") or 0
        pct = round(100.0 * (asistencias + retrasos + salidas_tempranas) / dias_registrados, 2) if dias_registrados > 0 else 0.0

        acumulado = [{
            "cedula": p["cedula"],
            "nombre_completo": p["nombre_completo"],
            "tipo_persona": p["tipo_persona"],
            "anio": p_anio,
            "semestre": p_sem,
            "meses_cerrados": meses_cerrados,
            "asistencias": asistencias,
            "ausencias": ausencias,
            "retrasos": retrasos,
            "salidas_tempranas": salidas_tempranas,
            "dias_registrados": dias_registrados,
            "porcentaje_asistencia": pct
        }]

        nombres_meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                         "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        rows = self.fetch_all("""
            SELECT mes, total_asistencias, total_ausencias, total_retrasos,
                   total_salidas_tempranas, total_dias_registrados
              FROM asistencia_historico
             WHERE id_persona = ? AND anio = ? AND mes BETWEEN ? AND ?
             ORDER BY mes
        """, (pid, p_anio, mes_ini, mes_fin))

        desglose = []
        for r in rows:
            m_num = r["mes"]
            desglose.append({
                "mes": m_num,
                "nombre_mes": nombres_meses[m_num - 1],
                "total_asistencias": r["total_asistencias"],
                "total_ausencias": r["total_ausencias"],
                "total_retrasos": r["total_retrasos"],
                "total_salidas_tempranas": r["total_salidas_tempranas"],
                "total_dias_registrados": r["total_dias_registrados"]
            })

        return [acumulado, desglose]

    # -- dashboard ----------------------------------------------------------
    def stats_hoy(self):
        hoy = date.today()
        c = {r["estado"]: r["n"] for r in self.fetch_all(
            "SELECT a.estado, COUNT(*) AS n FROM asistencia a "
            "JOIN persona p ON p.id_persona = a.id_persona "
            "WHERE a.fecha = %s AND p.activo = 1 GROUP BY a.estado", (hoy,))}
        poblacion = self.fetch_one(
            "SELECT COUNT(*) AS total, "
            "COALESCE(SUM(tipo_persona = 'Estudiante'), 0) AS estudiantes, "
            "COALESCE(SUM(tipo_persona = 'Personal'), 0) AS personal "
            "FROM persona WHERE activo = 1"
        ) or {}
        just = self.fetch_one(
            "SELECT COUNT(*) AS n FROM asistencia a "
            "JOIN persona p ON p.id_persona = a.id_persona "
            "WHERE a.fecha = %s AND p.activo = 1 AND a.estado <> 'Presente' "
            "AND CHAR_LENGTH(TRIM(a.observaciones)) > 0", (hoy,))["n"]
        sin_entrada = self.fetch_one(
            """
            SELECT COUNT(DISTINCT ac.id_persona) AS n
              FROM asistencia_curso ac
              JOIN persona p ON p.id_persona = ac.id_persona
              LEFT JOIN asistencia a
                ON a.id_persona = ac.id_persona AND a.fecha = ac.fecha
             WHERE ac.fecha = %s
               AND p.activo = 1
               AND p.tipo_persona = 'Estudiante'
               AND ac.estado IN ('Presente', 'Retraso')
               AND (a.id_asistencia IS NULL OR a.estado = 'Ausente')
            """,
            (hoy,),
        )["n"]
        total_activos = poblacion.get("total", 0)
        total_registros = sum(c.values())
        return {"asist": sum(v for k, v in c.items() if k != "Ausente"),
                "retr": c.get("Retraso", 0), "aus": c.get("Ausente", 0), "just": just,
                "estudiantes": poblacion.get("estudiantes", 0),
                "personal": poblacion.get("personal", 0),
                "activos": total_activos,
                "pendientes": max(total_activos - total_registros, 0),
                "sin_entrada": sin_entrada}

    def registros_hoy(self, limite=30):
        sql = """
            SELECT a.id_asistencia, a.hora_entrada, a.hora_salida, a.estado, a.observaciones,
                   p.cedula, p.nombre, p.apellido, p.tipo_persona,
                   COALESCE(CONCAT(s.grado_ano, '° "', s.seccion_letra, '" - ', s.turno), pe.cargo, '—') AS detalle
              FROM asistencia a
              JOIN persona p ON p.id_persona = a.id_persona
              LEFT JOIN estudiante e ON e.id_persona = p.id_persona
              LEFT JOIN seccion s ON s.id_seccion = e.id_seccion
              LEFT JOIN personal pe ON pe.id_persona = p.id_persona
             WHERE a.fecha = %s
             ORDER BY a.id_asistencia DESC
             LIMIT %s
        """
        return self.fetch_all(sql, (date.today(), limite))

    # -- personas -----------------------------------------------------------
    def secciones(self):
        return self.fetch_all(
            "SELECT id_seccion, CONCAT(seccion_letra, ' (', turno, ')') AS etiqueta "
            "FROM seccion ORDER BY id_seccion")

    def persona_por_cedula(self, cedula):
        if not cedula:
            return None
        ced = str(cedula).strip()
        # 1. Búsqueda directa
        res = self.fetch_one(PERSONA_SQL + " WHERE p.cedula = %s AND p.activo = 1", (ced,))
        if res:
            return res
        # 2. Búsqueda tolerante a prefijos V-, E- y espacios
        solo_digitos = "".join(c for c in ced if c.isdigit())
        if solo_digitos:
            res = self.fetch_one(
                PERSONA_SQL + " WHERE REPLACE(REPLACE(REPLACE(p.cedula, 'V-', ''), 'E-', ''), ' ', '') = %s AND p.activo = 1",
                (solo_digitos,)
            )
            if res:
                return res

        # 3. Búsqueda tolerante a duplicación de caracteres por escáner/teclado (ej: 3311122233778899 -> 31123789)
        if solo_digitos and len(solo_digitos) >= 12 and len(solo_digitos) % 2 == 0:
            if all(solo_digitos[i] == solo_digitos[i+1] for i in range(0, len(solo_digitos), 2)):
                dedup = "".join(solo_digitos[i] for i in range(0, len(solo_digitos), 2))
                res = self.fetch_one(
                    PERSONA_SQL + " WHERE REPLACE(REPLACE(REPLACE(p.cedula, 'V-', ''), 'E-', ''), ' ', '') = %s AND p.activo = 1",
                    (dedup,)
                )
                if res:
                    return res
        return None

    def persona_por_id(self, id_persona):
        if not id_persona:
            return None
        return self.fetch_one(PERSONA_SQL + " WHERE p.id_persona = %s", (id_persona,))

    def procesar_marcaje(self, cedula, id_usuario=None):
        """Procesa un marcaje de asistencia autónomo (Entrada o Salida) según horarios institucionales y valida duplicados."""
        from datetime import date, datetime, time
        p = self.persona_por_cedula(cedula)
        if not p:
            return {
                "ok": False,
                "error": "no_encontrado",
                "mensaje": f"Persona con C.I. {cedula} no está registrada en el sistema."
            }

        ahora = datetime.now()
        hora = ahora.time().replace(microsecond=0)
        hoy = ahora.date()

        turno_activo = resolver_turno_persona(p, hora)
        import config
        horarios = getattr(config, "HORARIOS_TURNO", {}).get(turno_activo, {})
        limite_entrada = horarios.get("entrada_limite", config.HORA_LIMITE_ENTRADA)
        minima_salida = horarios.get("salida_minima", config.HORA_SALIDA_MINIMA)
        uid = id_usuario or getattr(config, "USUARIO_ID", 1) or 1

        ex = self.asistencia_de(p["id_persona"], hoy)

        if not ex or ex["hora_entrada"] is None:
            # REGISTRAR ENTRADA
            estado = "Retraso" if hora > limite_entrada else "Presente"
            obs = f"Entrada puntual autónoma (Turno {turno_activo})" if estado == "Presente" else f"Llegada tardía autónoma (Turno {turno_activo} > {limite_entrada:%H:%M})"
            self.registrar_entrada(p["id_persona"], hoy, hora, estado, obs, uid, existe=bool(ex))
            return {
                "ok": True,
                "tipo": "Entrada",
                "estado": estado,
                "persona": f"{p['nombre']} {p['apellido']}",
                "nombre": p["nombre"],
                "apellido": p["apellido"],
                "cedula": p["cedula"],
                "tipo_persona": p["tipo_persona"],
                "detalle": p["detalle"] or "",
                "turno": turno_activo,
                "hora": f"{hora:%H:%M:%S}",
                "hora_fmt": ahora.strftime("%I:%M %p"),
                "mensaje": f"✓ Entrada registrada a las {ahora.strftime('%I:%M %p')} · {estado} (Turno {turno_activo})"
            }
        elif ex["hora_salida"] is None:
            # Validación anti-duplicados por doble escaneo accidental (< 120 segundos)
            h_ent = ex.get("hora_entrada")
            t_ent = None
            if isinstance(h_ent, str):
                try:
                    t_ent = datetime.strptime(h_ent[:8], "%H:%M:%S").time()
                except Exception:
                    pass
            elif isinstance(h_ent, time):
                t_ent = h_ent

            if t_ent:
                dt_ent = datetime.combine(hoy, t_ent)
                seg_dif = (ahora - dt_ent).total_seconds()
                if 0 <= seg_dif < 120:
                    return {
                        "ok": False,
                        "duplicado": True,
                        "tipo": "Entrada",
                        "persona": f"{p['nombre']} {p['apellido']}",
                        "nombre": p["nombre"],
                        "apellido": p["apellido"],
                        "cedula": p["cedula"],
                        "tipo_persona": p["tipo_persona"],
                        "detalle": p["detalle"] or "",
                        "turno": turno_activo,
                        "hora": f"{t_ent:%H:%M:%S}",
                        "hora_fmt": dt_ent.strftime("%I:%M %p"),
                        "mensaje": f"ℹ Marcaje duplicado detectado: {p['nombre']} {p['apellido']} ya registró su Entrada a las {dt_ent.strftime('%I:%M %p')} (Turno {turno_activo})."
                    }

            # REGISTRAR SALIDA
            temprana = hora < minima_salida
            estado = "Salida Temprana" if temprana else ex["estado"]
            obs = f"Salida anticipada autónoma (Turno {turno_activo} < {minima_salida:%H:%M})" if temprana else f"Salida registrada autónoma (Turno {turno_activo})"
            obs_final = " | ".join(x for x in ((ex.get("observaciones") or "").strip(), obs) if x)
            self.registrar_salida(ex["id_asistencia"], hora, estado, obs_final)
            return {
                "ok": True,
                "tipo": "Salida",
                "estado": estado,
                "persona": f"{p['nombre']} {p['apellido']}",
                "nombre": p["nombre"],
                "apellido": p["apellido"],
                "cedula": p["cedula"],
                "tipo_persona": p["tipo_persona"],
                "detalle": p["detalle"] or "",
                "turno": turno_activo,
                "hora": f"{hora:%H:%M:%S}",
                "hora_fmt": ahora.strftime("%I:%M %p"),
                "mensaje": f"✓ Salida registrada a las {ahora.strftime('%I:%M %p')}" + (" (Salida Temprana)" if temprana else "")
            }
        else:
            return {
                "ok": False,
                "ya_completado": True,
                "duplicado": True,
                "persona": f"{p['nombre']} {p['apellido']}",
                "cedula": p["cedula"],
                "turno": turno_activo,
                "mensaje": f"ℹ {p['nombre']} {p['apellido']} ya completó su entrada y salida del Turno {turno_activo} hoy."
            }

    def listar_personas(self, texto="", tipo="Todos"):
        sql, params = PERSONA_SQL + " WHERE p.activo = 1", []
        if tipo != "Todos":
            sql += " AND p.tipo_persona = %s"
            params.append(tipo)
        if texto:
            sql += (" AND CONCAT_WS(' ', p.cedula, p.nombre, p.apellido, s.grado_ano, s.seccion_letra, "
                    "s.turno, CONCAT(s.grado_ano, s.seccion_letra), pe.cargo) LIKE %s")
            params.append(f"%{texto}%")
        return self.fetch_all(sql + " ORDER BY p.apellido, p.nombre LIMIT 500", params)

    def crear_persona(self, d):
        with self.cursor(transaccion=True) as cur:
            cur.execute("INSERT INTO persona (cedula, nombre, apellido, telefono, tipo_persona, foto) "
                        "VALUES (%s, %s, %s, %s, %s, %s)",
                        (d["cedula"], d["nombre"], d["apellido"], d["telefono"], d["tipo"], d.get("foto")))
            pid = cur.lastrowid
            if d["tipo"] == "Estudiante":
                cur.execute("INSERT INTO estudiante (id_persona, id_seccion, representante, telefono_representante) VALUES (%s, %s, %s, %s)",
                            (pid, d["id_seccion"], d.get("representante"), d.get("telefono_representante")))
            else:
                cur.execute("INSERT INTO personal (id_persona, cargo) VALUES (%s, %s)", (pid, d["cargo"]))

    def actualizar_persona(self, id_persona, d):
        with self.cursor(transaccion=True) as cur:
            if "foto" in d:
                cur.execute("UPDATE persona SET cedula=%s, nombre=%s, apellido=%s, telefono=%s, foto=%s WHERE id_persona=%s",
                            (d["cedula"], d["nombre"], d["apellido"], d["telefono"], d.get("foto"), id_persona))
            else:
                cur.execute("UPDATE persona SET cedula=%s, nombre=%s, apellido=%s, telefono=%s WHERE id_persona=%s",
                            (d["cedula"], d["nombre"], d["apellido"], d["telefono"], id_persona))
            if d["tipo"] == "Estudiante":
                cur.execute("UPDATE estudiante SET id_seccion=%s, representante=%s, telefono_representante=%s WHERE id_persona=%s",
                            (d["id_seccion"], d.get("representante"), d.get("telefono_representante"), id_persona))
            else:
                cur.execute("UPDATE personal SET cargo=%s WHERE id_persona=%s", (d["cargo"], id_persona))

    # -- asistencia ---------------------------------------------------------
    def asistencia_de(self, id_persona, fecha):
        return self.fetch_one("SELECT * FROM asistencia WHERE id_persona = %s AND fecha = %s", (id_persona, fecha))

    def registrar_entrada(self, id_persona, fecha, hora, estado, obs, id_usuario, existe=False):
        """Registra la entrada garantizando atomicidad y previniendo duplicados en SQLite."""
        with self.cursor(transaccion=True) as cur:
            sql = """
                INSERT INTO asistencia (id_persona, fecha, hora_entrada, estado, observaciones, id_usuario_registro)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT(id_persona, fecha) DO UPDATE SET
                    hora_entrada = CASE 
                        WHEN asistencia.hora_entrada IS NULL THEN excluded.hora_entrada 
                        ELSE asistencia.hora_entrada 
                    END,
                    estado = CASE 
                        WHEN asistencia.estado = 'Ausente' THEN excluded.estado 
                        ELSE asistencia.estado 
                    END,
                    observaciones = CASE 
                        WHEN asistencia.observaciones IS NULL OR asistencia.observaciones = '' THEN excluded.observaciones 
                        ELSE asistencia.observaciones 
                    END,
                    id_usuario_registro = COALESCE(excluded.id_usuario_registro, asistencia.id_usuario_registro)
            """
            cur.execute(sql, (id_persona, fecha, hora, estado, obs, id_usuario))

    def registrar_salida(self, id_asistencia, hora, estado, obs):
        with self.cursor(transaccion=True) as cur:
            cur.execute("UPDATE asistencia SET hora_salida=%s, estado=%s, observaciones=%s WHERE id_asistencia=%s",
                         (hora, estado, obs, id_asistencia))

    def registrar_ausencia(self, id_persona, fecha, obs, id_usuario):
        with self.cursor(transaccion=True) as cur:
            sql = """
                INSERT INTO asistencia (id_persona, fecha, estado, observaciones, id_usuario_registro)
                VALUES (%s, %s, 'Ausente', %s, %s)
                ON CONFLICT(id_persona, fecha) DO NOTHING
            """
            cur.execute(sql, (id_persona, fecha, obs, id_usuario))

    # -- justificaciones y cierres -----------------------------------------
    def no_presentes(self, fecha):
        """Retorna inasistencias o retrasos tanto de asistencia general como de cursos sabatinos."""
        sql = """
            SELECT CONCAT('gral_', a.id_asistencia) AS id_clave,
                   a.id_asistencia, NULL AS id_asistencia_curso,
                   p.id_persona, p.cedula, CONCAT(p.nombre, ' ', p.apellido) AS nombre, p.tipo_persona,
                   'General' COLLATE utf8mb4_unicode_ci AS origen,
                   a.estado COLLATE utf8mb4_unicode_ci AS estado,
                   a.observaciones COLLATE utf8mb4_unicode_ci AS observaciones
              FROM asistencia a
              JOIN persona p ON p.id_persona = a.id_persona
             WHERE a.fecha = %s AND a.estado <> 'Presente'
            UNION ALL
            SELECT CONCAT('cur_', ac.id_asistencia_curso) AS id_clave,
                   NULL AS id_asistencia, ac.id_asistencia_curso,
                   p.id_persona, p.cedula, CONCAT(p.nombre, ' ', p.apellido) AS nombre, p.tipo_persona,
                   CONCAT('Curso: ', c.nombre) COLLATE utf8mb4_unicode_ci AS origen,
                   ac.estado COLLATE utf8mb4_unicode_ci AS estado,
                   ac.observaciones COLLATE utf8mb4_unicode_ci AS observaciones
              FROM asistencia_curso ac
              JOIN persona p ON p.id_persona = ac.id_persona
              JOIN cohorte ch ON ch.id_cohorte = ac.id_cohorte
              JOIN curso c ON c.id_curso = ch.id_curso
             WHERE ac.fecha = %s AND ac.estado <> 'Presente'
             ORDER BY estado, nombre
        """
        return self.fetch_all(sql, (fecha, fecha))

    def guardar_justificacion(self, id_asistencia=None, id_asistencia_curso=None, obs="", soporte=""):
        """Guarda justificación con motivo y soporte, cambiando el estado a Justificado en cursos sabatinos."""
        texto_justif = f"{obs.strip()} [Soporte: {soporte.strip()}]" if soporte and soporte.strip() else obs.strip()
        if id_asistencia_curso:
            self.execute(
                "UPDATE asistencia_curso SET observaciones = %s, estado = 'Justificado' WHERE id_asistencia_curso = %s",
                (texto_justif, id_asistencia_curso)
            )
            ac = self.fetch_one(
                "SELECT id_matricula, id_persona, id_cohorte, fecha FROM asistencia_curso WHERE id_asistencia_curso = %s",
                (id_asistencia_curso,)
            )
            if ac:
                self.recalcular_asistencia_matricula(ac["id_matricula"])
                self.registrar_bitacora_asistencia(
                    id_asistencia_curso=id_asistencia_curso,
                    id_matricula=ac["id_matricula"],
                    id_persona=ac["id_persona"],
                    id_cohorte=ac["id_cohorte"],
                    fecha_asistencia=ac["fecha"],
                    estado_anterior="Ausente",
                    estado_nuevo="Justificado",
                    accion="JUSTIFICACION",
                    observaciones=texto_justif
                )
        elif id_asistencia:
            self.execute("UPDATE asistencia SET observaciones = %s WHERE id_asistencia = %s", (texto_justif, id_asistencia))

    def cierres(self):
        return self.fetch_all("SELECT anio, mes, fecha_cierre, total_personas, archivado FROM cierre_mensual "
                              "ORDER BY anio DESC, mes DESC LIMIT 12")

    # -- cierres diarios automatizados --------------------------------------
    def obtener_estadisticas_dia(self, fecha):
        """Calcula estadísticas consolidadas y registros de asistencia para una fecha."""
        from datetime import datetime
        if isinstance(fecha, str):
            fecha = datetime.strptime(fecha.strip(), "%Y-%m-%d").date()

        row_mat = self.fetch_one("SELECT COUNT(*) AS total FROM persona WHERE activo = 1")
        total_matricula = row_mat["total"] if row_mat else 0

        sql = """
            SELECT a.id_asistencia, a.id_persona, p.cedula, p.nombre, p.apellido,
                   p.tipo_persona, s.grado_ano, s.seccion_letra, s.turno, pe.cargo,
                   COALESCE(CONCAT(s.seccion_letra, ' (', s.turno, ')'), pe.cargo) AS detalle,
                   a.fecha, a.hora_entrada, a.hora_salida, a.estado, a.observaciones
              FROM asistencia a
              JOIN persona p ON p.id_persona = a.id_persona
              LEFT JOIN estudiante e ON e.id_persona = p.id_persona
              LEFT JOIN seccion s ON s.id_seccion = e.id_seccion
              LEFT JOIN personal pe ON pe.id_persona = p.id_persona
             WHERE a.fecha = %s
             ORDER BY p.tipo_persona DESC, s.grado_ano, s.seccion_letra, p.apellido, p.nombre
        """
        registros = list(self.fetch_all(sql, (fecha,)))

        # Incluir registros de cursos sabatinos
        sql_cursos = """
            SELECT CONCAT('cur_', ac.id_asistencia_curso) AS id_asistencia,
                   ac.id_persona, p.cedula, p.nombre, p.apellido,
                   p.tipo_persona,
                   NULL AS grado_ano, NULL AS seccion_letra, NULL AS turno, NULL AS cargo,
                   CONCAT('Curso: ', c.nombre, ' (', ch.nombre_grupo, ')') AS detalle,
                   ac.fecha, ac.hora AS hora_entrada, NULL AS hora_salida, ac.estado, ac.observaciones
              FROM asistencia_curso ac
              JOIN persona p ON p.id_persona = ac.id_persona
              JOIN cohorte ch ON ch.id_cohorte = ac.id_cohorte
              JOIN curso c ON c.id_curso = ch.id_curso
             WHERE ac.fecha = %s
             ORDER BY c.nombre, ch.nombre_grupo, p.apellido, p.nombre
        """
        registros_cursos = self.fetch_all(sql_cursos, (fecha,))
        if registros_cursos:
            registros.extend(registros_cursos)

        # Si no hay matrícula regular en esa fecha (ej. sábado de cursos), usar la matrícula de participantes de cursos
        if total_matricula == 0 or len(registros_cursos) > 0:
            total_matricula = max(total_matricula, len(registros))

        presentes = sum(1 for r in registros if r["estado"] == "Presente")
        retrasos = sum(1 for r in registros if r["estado"] == "Retraso")
        salidas_tempranas = sum(1 for r in registros if r["estado"] == "Salida Temprana")
        ausencias = sum(1 for r in registros if r["estado"] == "Ausente")
        justificados = sum(1 for r in registros if r["estado"] == "Justificado" or (r["observaciones"] or "").strip())

        total_asistieron = presentes + retrasos + justificados
        pct = (total_asistieron / total_matricula * 100.0) if total_matricula > 0 else 0.0

        return {
            "fecha": fecha,
            "total_matricula": total_matricula,
            "presentes": presentes,
            "retrasos": retrasos,
            "salidas_tempranas": salidas_tempranas,
            "ausencias": ausencias,
            "justificados": justificados,
            "pct_asistencia": round(pct, 2),
            "registros": registros
        }

    def ejecutar_cierre_diario(self, fecha=None, id_usuario=None):
        """Ejecuta el cierre diario a las 11:59 PM o bajo demanda: genera PDF, Excel y actualiza BD."""
        from datetime import datetime, date
        if fecha is None:
            fecha = date.today()
        elif isinstance(fecha, str):
            fecha = datetime.strptime(fecha.strip(), "%Y-%m-%d").date()

        stats = self.obtener_estadisticas_dia(fecha)

        import config
        from pathlib import Path
        dir_cierres = config.BASE_DIR / "respaldos" / "cierres_diarios"
        dir_pdf = dir_cierres / "pdf"
        dir_excel = dir_cierres / "excel"
        dir_pdf.mkdir(parents=True, exist_ok=True)
        dir_excel.mkdir(parents=True, exist_ok=True)

        nombre_base = f"cierre_diario_{fecha.strftime('%Y_%m_%d')}"
        ruta_pdf = dir_pdf / f"{nombre_base}.pdf"
        ruta_excel = dir_excel / f"{nombre_base}.xlsx"

        try:
            import reports
            reports.generar_reporte_diario_pdf(self, fecha, str(ruta_pdf))
        except Exception as e_pdf:
            print(f"Aviso generando PDF de cierre diario: {e_pdf}")

        try:
            import excel_reports
            excel_reports.exportar_reporte_diario_excel(self, fecha, str(ruta_excel))
        except Exception as e_xl:
            print(f"Aviso generando Excel de cierre diario: {e_xl}")

        sql = """
            INSERT INTO cierre_diario (
                fecha, total_matricula, presentes, retrasos, salidas_tempranas,
                ausencias, justificados, pct_asistencia, archivo_pdf, archivo_excel,
                id_usuario_cierre
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                total_matricula = VALUES(total_matricula),
                presentes = VALUES(presentes),
                retrasos = VALUES(retrasos),
                salidas_tempranas = VALUES(salidas_tempranas),
                ausencias = VALUES(ausencias),
                justificados = VALUES(justificados),
                pct_asistencia = VALUES(pct_asistencia),
                archivo_pdf = VALUES(archivo_pdf),
                archivo_excel = VALUES(archivo_excel),
                id_usuario_cierre = VALUES(id_usuario_cierre),
                creado_en = CURRENT_TIMESTAMP
        """
        self.execute(sql, (
            fecha, stats["total_matricula"], stats["presentes"], stats["retrasos"],
            stats["salidas_tempranas"], stats["ausencias"], stats["justificados"],
            stats["pct_asistencia"], str(ruta_pdf), str(ruta_excel), id_usuario
        ))

        return {
            **stats,
            "archivo_pdf": str(ruta_pdf),
            "archivo_excel": str(ruta_excel)
        }

    def listar_cierres_diarios(self, filtro_fecha=None):
        """Lista los cierres diarios almacenados para búsqueda y descargas."""
        sql = """
            SELECT c.*, u.username AS usuario_nombre,
                   DATE_FORMAT(c.fecha, '%Y-%m-%d') AS fecha_str,
                   DATE_FORMAT(c.creado_en, '%d/%m/%Y %H:%i') AS fecha_cierre_fmt
              FROM cierre_diario c
              LEFT JOIN usuario u ON u.id_usuario = c.id_usuario_cierre
        """
        params = []
        if filtro_fecha:
            sql += " WHERE c.fecha = %s "
            params.append(filtro_fecha)
        sql += " ORDER BY c.fecha DESC LIMIT 60"
        return self.fetch_all(sql, params)

    def obtener_cierre_diario(self, fecha):
        return self.fetch_one("SELECT * FROM cierre_diario WHERE fecha = %s", (fecha,))

    # -- reportes avanzados -------------------------------------------------
    def matriz_asistencia_seccion(self, id_seccion, anio, mes):
        """Devuelve los datos organizados día a día (1 al 31) para toda una sección."""
        sec = self.fetch_one(
            "SELECT id_seccion, grado_ano, seccion_letra, turno, "
            "CONCAT(grado_ano, '° \"', seccion_letra, '\" - ', turno) AS etiqueta "
            "FROM seccion WHERE id_seccion = %s", (id_seccion,)
        )
        if not sec:
            raise UserWarning("La sección indicada no existe.")

        alumnos = self.fetch_all(
            "SELECT p.id_persona, p.cedula, p.apellido, p.nombre "
            "FROM estudiante e "
            "JOIN persona p ON p.id_persona = e.id_persona "
            "WHERE e.id_seccion = %s AND p.activo = 1 "
            "ORDER BY p.apellido, p.nombre", (id_seccion,)
        )

        dias_mes = calendar.monthrange(anio, mes)[1]
        inicio = date(anio, mes, 1)
        fin = date(anio, mes, dias_mes)

        registros = self.fetch_all(
            "SELECT a.id_persona, a.fecha, a.estado, a.hora_entrada, a.hora_salida, a.observaciones "
            "FROM v_asistencia_total a "
            "JOIN estudiante e ON e.id_persona = a.id_persona "
            "WHERE e.id_seccion = %s AND a.fecha BETWEEN %s AND %s",
            (id_seccion, inicio, fin)
        )

        mapa_asist = {}
        for r in registros:
            pid = r["id_persona"]
            d = r["fecha"].day
            if pid not in mapa_asist:
                mapa_asist[pid] = {}
            mapa_asist[pid][d] = r

        return {
            "seccion": sec,
            "dias_mes": dias_mes,
            "anio": anio,
            "mes": mes,
            "alumnos": alumnos,
            "registros": mapa_asist
        }

    def alerta_inasistencias(self, anio, mes=None, semestre=None, umbral=25.0):
        """Lista estudiantes que superan el umbral porcentual de ausencias (Art. 109 LOE)."""
        if mes:
            condicion_fecha = "YEAR(a.fecha) = %s AND MONTH(a.fecha) = %s"
            params = [anio, mes]
        elif semestre == 1:
            condicion_fecha = "YEAR(a.fecha) = %s AND MONTH(a.fecha) BETWEEN 1 AND 6"
            params = [anio]
        elif semestre == 2:
            condicion_fecha = "YEAR(a.fecha) = %s AND MONTH(a.fecha) BETWEEN 7 AND 12"
            params = [anio]
        else:
            condicion_fecha = "YEAR(a.fecha) = %s"
            params = [anio]

        sql = f"""
        SELECT p.cedula,
               CONCAT(p.apellido, ' ', p.nombre) AS nombre_completo,
               p.telefono,
               CONCAT(s.grado_ano, '° \"', s.seccion_letra, '\" - ', s.turno) AS seccion,
               s.turno,
               COUNT(*) AS dias_registrados,
               COALESCE(SUM(a.estado = 'Presente'), 0) AS presentes,
               COALESCE(SUM(a.estado = 'Ausente'), 0) AS ausencias,
               COALESCE(SUM(a.estado = 'Retraso'), 0) AS retrasos,
               COALESCE(SUM(a.estado = 'Salida Temprana'), 0) AS salidas_tempranas,
               ROUND(100.0 * COALESCE(SUM(a.estado = 'Ausente'), 0) / NULLIF(COUNT(*), 0), 2) AS pct_ausencia
          FROM estudiante e
          JOIN persona p ON p.id_persona = e.id_persona
          JOIN seccion s ON s.id_seccion = e.id_seccion
          JOIN v_asistencia_total a ON a.id_persona = p.id_persona
         WHERE p.activo = 1 AND {condicion_fecha}
         GROUP BY p.id_persona, s.id_seccion
        HAVING pct_ausencia >= %s
         ORDER BY pct_ausencia DESC, s.grado_ano, s.seccion_letra, p.apellido
        """
        params.append(umbral)
        return self.fetch_all(sql, tuple(params))

    # -- parte administrativa (secciones y usuarios) ------------------------
    def listar_secciones_detalle(self):
        return self.fetch_all("""
            SELECT id_seccion, grado_ano, seccion_letra, turno, n_estudiantes,
                   CONCAT(grado_ano, '° "', seccion_letra, '" - ', turno) AS etiqueta
              FROM seccion
             ORDER BY grado_ano, seccion_letra, turno
        """)

    def crear_seccion(self, grado_ano, seccion_letra, turno):
        self.execute(
            "INSERT INTO seccion (grado_ano, seccion_letra, turno) VALUES (%s, %s, %s)",
            (grado_ano, seccion_letra.upper().strip(), turno)
        )

    def actualizar_seccion(self, id_seccion, grado_ano, seccion_letra, turno):
        self.execute(
            "UPDATE seccion SET grado_ano = %s, seccion_letra = %s, turno = %s WHERE id_seccion = %s",
            (grado_ano, seccion_letra.upper().strip(), turno, id_seccion)
        )

    def eliminar_seccion(self, id_seccion):
        sec = self.fetch_one("SELECT n_estudiantes FROM seccion WHERE id_seccion = %s", (id_seccion,))
        if not sec:
            raise UserWarning("La sección no existe.")
        if sec["n_estudiantes"] > 0:
            raise UserWarning(f"No se puede eliminar la sección porque tiene {sec['n_estudiantes']} estudiante(s) matriculado(s).")
        self.execute("DELETE FROM seccion WHERE id_seccion = %s", (id_seccion,))

  
    def listar_usuarios(self):
        """Lista únicamente los usuarios activos del sistema."""
        return self.fetch_all("""
            SELECT u.id_usuario, u.username, u.rol_sistema, u.activo, u.es_duena,
                   p.cedula, CONCAT(p.nombre, ' ', p.apellido) AS nombre_persona,
                   pe.cargo, pe.id_personal,
                   (SELECT MAX(ai.fecha_hora) FROM auditoria_ingresos ai WHERE ai.id_usuario = u.id_usuario) AS ultimo_ingreso
            FROM usuario u
            JOIN personal pe ON pe.id_personal = u.id_personal
            JOIN persona p ON p.id_persona = pe.id_persona
            WHERE u.activo = 1
            ORDER BY u.es_duena DESC, u.username ASC
        """)

    def listar_usuarios_archivados(self):
        """Lista los usuarios dados de baja (para acceso exclusivo de la Dueña)."""
        return self.fetch_all("""
            SELECT u.id_usuario, u.username, u.rol_sistema, u.activo, u.es_duena,
                   u.fecha_baja, u.motivo_baja,
                   p.cedula, CONCAT(p.nombre, ' ', p.apellido) AS nombre_persona,
                   pe.cargo, pe.id_personal,
                   (SELECT MAX(ai.fecha_hora) FROM auditoria_ingresos ai WHERE ai.id_usuario = u.id_usuario) AS ultimo_ingreso
            FROM usuario u
            JOIN personal pe ON pe.id_personal = u.id_personal
            JOIN persona p ON p.id_persona = pe.id_persona
            WHERE u.activo = 0
            ORDER BY u.fecha_baja DESC, u.username ASC
        """)

    def verificar_password_usuario(self, id_usuario, password):
        """Verifica la contraseña ingresada contra el hash en base de datos."""
        import bcrypt
        u = self.fetch_one("SELECT password_encriptada FROM usuario WHERE id_usuario = %s", (id_usuario,))
        if not u or not u["password_encriptada"]:
            return False
        pwd_hash = u["password_encriptada"]
        if pwd_hash.startswith("$2b$") or pwd_hash.startswith("$2a$"):
            try:
                return bcrypt.checkpw(password.encode('utf-8'), pwd_hash.encode('utf-8'))
            except Exception:
                return False
        else:
            res_sha = self.fetch_one("SELECT id_usuario FROM usuario WHERE id_usuario = %s AND password_encriptada = SHA2(%s, 256)", (id_usuario, password))
            return bool(res_sha)

    def dar_baja_usuario(self, id_usuario, motivo="Desvinculación laboral / Renuncia", usuario_operador=None):
        """Da de baja a un usuario (Soft Delete) y genera respaldo JSON en carpeta oculta."""
        import json
        from datetime import datetime
        import config

        u = self.fetch_one("""
            SELECT u.id_usuario, u.username, u.rol_sistema, u.es_duena,
                   p.cedula, p.nombre, p.apellido, pe.cargo
            FROM usuario u
            JOIN personal pe ON pe.id_personal = u.id_personal
            JOIN persona p ON p.id_persona = pe.id_persona
            WHERE u.id_usuario = %s
        """, (id_usuario,))
        if not u:
            raise UserWarning("El usuario especificado no existe.")
        if u.get("es_duena"):
            raise UserWarning("La cuenta de la Dueña / Propietaria del plantel no puede ser dada de baja.")

        ahora = datetime.now()
        self.execute("""
            UPDATE usuario
            SET activo = 0, fecha_baja = %s, motivo_baja = %s
            WHERE id_usuario = %s
        """, (ahora, motivo, id_usuario))

        carpeta_resp = config.BASE_DIR / "respaldos" / "usuarios_archivados"
        carpeta_resp.mkdir(parents=True, exist_ok=True)
        archivo_resp = carpeta_resp / f"usuario_{u['username']}_{ahora.strftime('%Y%m%d_%H%M%S')}.json"
        
        datos_respaldo = {
            "id_usuario": u["id_usuario"],
            "username": u["username"],
            "rol_sistema": u["rol_sistema"],
            "cedula": u["cedula"],
            "nombre_completo": f"{u['nombre']} {u['apellido']}",
            "cargo": u["cargo"],
            "fecha_baja": ahora.strftime("%Y-%m-%d %H:%M:%S"),
            "motivo_baja": motivo,
            "autorizado_por": usuario_operador or "Dueña / Dirección General"
        }
        with open(archivo_resp, "w", encoding="utf-8") as f:
            json.dump(datos_respaldo, f, ensure_ascii=False, indent=2)

        return str(archivo_resp)

    def reactivar_usuario(self, id_usuario):
        """Reactiva una cuenta de usuario previamente archivada."""
        self.execute("""
            UPDATE usuario
            SET activo = 1, fecha_baja = NULL, motivo_baja = NULL
            WHERE id_usuario = %s
        """, (id_usuario,))

    # --- Archivo Histórico de Estudiantes (5° Año y Bajas) -------------------
    def detectar_estudiantes_5to_ano(self):
        """Retorna todos los estudiantes activos matriculados en 5° Año."""
        return self.fetch_all("""
            SELECT p.id_persona, p.cedula, p.nombre, p.apellido, p.telefono,
                   s.id_seccion, s.grado_ano, s.seccion_letra, s.turno,
                   CONCAT(s.grado_ano, '° "', s.seccion_letra, '" - ', s.turno) AS seccion_nombre,
                   e.representante, e.telefono_representante
            FROM estudiante e
            JOIN persona p ON p.id_persona = e.id_persona
            JOIN seccion s ON s.id_seccion = e.id_seccion
            WHERE p.activo = 1 AND s.grado_ano = 5
            ORDER BY s.seccion_letra, p.apellido, p.nombre
        """)

    def procesar_egreso_5to_ano(self, usuario_operador=None):
        """Marca como inactivos / egresados a todos los estudiantes de 5° Año y crea respaldo JSON."""
        import json
        from datetime import datetime
        import config

        estudiantes = self.detectar_estudiantes_5to_ano()
        if not estudiantes:
            return 0, ""

        ahora = datetime.now()
        motivo = "Egresado de 5° Año (Bachiller de la República)"

        carpeta_resp = config.BASE_DIR / "respaldos" / "estudiantes_archivados"
        carpeta_resp.mkdir(parents=True, exist_ok=True)
        archivo_resp = carpeta_resp / f"promocion_egresados_5to_{ahora.strftime('%Y%m%d_%H%M%S')}.json"

        datos_respaldo = {
            "fecha_egreso": ahora.strftime("%Y-%m-%d %H:%M:%S"),
            "evento": "Egreso de 5to Año - Culminación de Bachillerato",
            "autorizado_por": usuario_operador or "Administración Asista",
            "total_egresados": len(estudiantes),
            "estudiantes": estudiantes
        }
        with open(archivo_resp, "w", encoding="utf-8") as f:
            json.dump(datos_respaldo, f, ensure_ascii=False, indent=2)

        ids = [e["id_persona"] for e in estudiantes]
        format_strings = ','.join(['%s'] * len(ids))
        self.execute(f"""
            UPDATE persona
            SET activo = 0, fecha_inactivo = %s, motivo_inactivo = %s
            WHERE id_persona IN ({format_strings})
        """, [ahora, motivo] + ids)

        return len(estudiantes), str(archivo_resp)

    def dar_baja_estudiante(self, id_persona, motivo="Retiro Voluntario", usuario_operador=None):
        """Pasa a un estudiante a inactivo (baja manual) y genera respaldo en carpeta."""
        import json
        from datetime import datetime
        import config

        p = self.fetch_one("""
            SELECT p.id_persona, p.cedula, p.nombre, p.apellido,
                   s.grado_ano, s.seccion_letra, s.turno,
                   e.representante, e.telefono_representante
            FROM persona p
            LEFT JOIN estudiante e ON e.id_persona = p.id_persona
            LEFT JOIN seccion s ON s.id_seccion = e.id_seccion
            WHERE p.id_persona = %s
        """, (id_persona,))
        if not p:
            raise UserWarning("El estudiante no fue encontrado.")

        ahora = datetime.now()
        self.execute("""
            UPDATE persona
            SET activo = 0, fecha_inactivo = %s, motivo_inactivo = %s
            WHERE id_persona = %s
        """, (ahora, motivo, id_persona))

        carpeta_resp = config.BASE_DIR / "respaldos" / "estudiantes_archivados"
        carpeta_resp.mkdir(parents=True, exist_ok=True)
        archivo_resp = carpeta_resp / f"estudiante_inactivo_{p['cedula']}_{ahora.strftime('%Y%m%d_%H%M%S')}.json"

        datos_respaldo = {
            "id_persona": p["id_persona"],
            "cedula": p["cedula"],
            "nombre_completo": f"{p['nombre']} {p['apellido']}",
            "seccion": f"{p['grado_ano']}° {p['seccion_letra']} ({p['turno']})" if p.get("grado_ano") else "Sin sección",
            "representante": p.get("representante"),
            "fecha_baja": ahora.strftime("%Y-%m-%d %H:%M:%S"),
            "motivo": motivo,
            "autorizado_por": usuario_operador or "Administración"
        }
        with open(archivo_resp, "w", encoding="utf-8") as f:
            json.dump(datos_respaldo, f, ensure_ascii=False, indent=2)

        return str(archivo_resp)

    def reactivar_estudiante(self, id_persona):
        """Reactiva a un estudiante previamente archivado."""
        self.execute("""
            UPDATE persona
            SET activo = 1, fecha_inactivo = NULL, motivo_inactivo = NULL
            WHERE id_persona = %s
        """, (id_persona,))

    def listar_estudiantes_inactivos(self, texto=""):
        """Devuelve el archivo histórico de estudiantes dados de baja y egresados."""
        sql = """
            SELECT p.id_persona, p.cedula, p.nombre, p.apellido, p.telefono,
                   p.fecha_inactivo, COALESCE(p.motivo_inactivo, 'Retiro') AS motivo_inactivo,
                   COALESCE(CONCAT(s.grado_ano, '° "', s.seccion_letra, '" - ', s.turno), 'Sin Sección') AS seccion_origen,
                   e.representante, e.telefono_representante
            FROM persona p
            LEFT JOIN estudiante e ON e.id_persona = p.id_persona
            LEFT JOIN seccion s ON s.id_seccion = e.id_seccion
            WHERE p.tipo_persona = 'Estudiante' AND p.activo = 0
        """
        params = []
        if texto:
            sql += " AND CONCAT_WS(' ', p.cedula, p.nombre, p.apellido, s.grado_ano, s.seccion_letra, p.motivo_inactivo) LIKE %s"
            params.append(f"%{texto}%")
        sql += " ORDER BY p.fecha_inactivo DESC, p.apellido, p.nombre"
        return self.fetch_all(sql, params)

    def obtener_usuario_por_id(self, id_usuario):
        return self.fetch_one("""
            SELECT u.id_usuario, u.username, u.rol_sistema, u.activo,
                   p.cedula, CONCAT(p.nombre, ' ', p.apellido) AS nombre_persona,
                   pe.cargo, pe.id_personal
            FROM usuario u
            LEFT JOIN personal pe ON pe.id_personal = u.id_personal
            LEFT JOIN persona p ON p.id_persona = pe.id_persona
            WHERE u.id_usuario = %s
        """, (id_usuario,))
    def personal_sin_usuario(self):
        return self.fetch_all("""
            SELECT pe.id_personal, p.cedula, CONCAT(p.apellido, ' ', p.nombre) AS nombre_persona, pe.cargo,
                   CONCAT(p.cedula, ' · ', p.apellido, ' ', p.nombre, ' (', pe.cargo, ')') AS etiqueta
              FROM personal pe
              JOIN persona p ON p.id_persona = pe.id_persona
             WHERE pe.id_personal NOT IN (SELECT id_personal FROM usuario WHERE id_personal IS NOT NULL)
               AND p.activo = 1
             ORDER BY p.apellido, p.nombre
        """)

    def crear_personal_y_usuario(self, cedula, nombre, apellido, cargo, username, password_hash, rol_sistema="Administrador"):
        """Registra un nuevo personal institucional y le crea su cuenta de usuario en una sola operación."""
        ced = cedula.strip().replace(" ", "")
        user = username.strip()

        existe_u = self.fetch_one("SELECT id_usuario FROM usuario WHERE username = %s", (user,))
        if existe_u:
            raise UserWarning(f"El nombre de usuario '{user}' ya se encuentra registrado.")

        p = self.fetch_one("SELECT id_persona, tipo_persona, nombre, apellido FROM persona WHERE cedula = %s", (ced,))
        if p:
            if p["tipo_persona"] == "Estudiante":
                raise UserWarning(
                    f"La cédula '{ced}' ya se encuentra registrada en el sistema como Estudiante ({p['nombre']} {p['apellido']}).\n\n"
                    "Por normatíva escolar y reglas de seguridad institucional (RBAC), los estudiantes matriculados no pueden poseer cuentas de usuario del personal.\n"
                    "Por favor ingrese una cédula diferente correspondiente a un miembro del personal docente o administrativo."
                )
            id_persona = p["id_persona"]
            pe = self.fetch_one("SELECT id_personal FROM personal WHERE id_persona = %s", (id_persona,))
            if not pe:
                self.execute("INSERT INTO personal (id_persona, cargo) VALUES (%s, %s)", (id_persona, cargo))
                id_personal = self.fetch_one("SELECT id_personal FROM personal WHERE id_persona = %s", (id_persona,))["id_personal"]
            else:
                id_personal = pe["id_personal"]
                u_act = self.fetch_one("SELECT id_usuario FROM usuario WHERE id_personal = %s", (id_personal,))
                if u_act:
                    raise UserWarning("Este personal institucional ya posee una cuenta de usuario asignada.")
        else:
            self.execute(
                "INSERT INTO persona (cedula, nombre, apellido, tipo_persona, activo) VALUES (%s, %s, %s, 'Personal', 1)",
                (ced, nombre.strip(), apellido.strip())
            )
            id_persona = self.fetch_one("SELECT id_persona FROM persona WHERE cedula = %s", (ced,))["id_persona"]
            self.execute("INSERT INTO personal (id_persona, cargo) VALUES (%s, %s)", (id_persona, cargo))
            id_personal = self.fetch_one("SELECT id_personal FROM personal WHERE id_persona = %s", (id_persona,))["id_personal"]

        self.execute(
            "INSERT INTO usuario (id_personal, username, password_encriptada, rol_sistema, activo, primer_ingreso) VALUES (%s, %s, %s, %s, 1, 1)",
            (id_personal, user, password_hash, rol_sistema)
        )

    def crear_usuario(self, id_personal, username, password_hash, rol_sistema="Docente"):
        self.execute(
            "INSERT INTO usuario (id_personal, username, password_encriptada, rol_sistema, activo, primer_ingreso) "
            "VALUES (%s, %s, %s, %s, 1, 1)",
            (id_personal, username.strip(), password_hash, rol_sistema)
        )

    def cambiar_estado_usuario(self, id_usuario, nuevo_estado):
        self.execute("UPDATE usuario SET activo = %s WHERE id_usuario = %s", (nuevo_estado, id_usuario))

    def cambiar_password_usuario(self, id_usuario, password_hash):
        self.execute("UPDATE usuario SET password_encriptada = %s, ultimo_cambio_pass = CURRENT_TIMESTAMP WHERE id_usuario = %s", (password_hash, id_usuario))

    def cambiar_password_primer_ingreso(self, id_usuario, password_hash):
        """Actualiza la contraseña y desmarca el flag de primer ingreso requerido."""
        self.execute(
            "UPDATE usuario SET password_encriptada = %s, primer_ingreso = 0, ultimo_cambio_pass = CURRENT_TIMESTAMP WHERE id_usuario = %s",
            (password_hash, id_usuario)
        )

    def resetear_password_usuario(self, id_usuario, password_hash, forzar_cambio=True):
        """Restablece la contraseña por parte del administrador y fuerza el cambio en el próximo login."""
        flag = 1 if forzar_cambio else 0
        self.execute(
            "UPDATE usuario SET password_encriptada = %s, primer_ingreso = %s WHERE id_usuario = %s",
            (password_hash, flag, id_usuario)
        )

    def actualizar_usuario_admin(self, id_usuario, username, rol_sistema, activo=1, id_cohorte=None):
        """Actualiza nombre de usuario, rol, estado y opcionalmente reasigna el docente a un curso sabatino."""
        self.execute(
            "UPDATE usuario SET username = %s, rol_sistema = %s, activo = %s WHERE id_usuario = %s",
            (username.strip(), rol_sistema, activo, id_usuario)
        )
        if id_cohorte is not None:
            u = self.fetch_one("""
                SELECT pe.id_persona FROM usuario u
                JOIN personal pe ON pe.id_personal = u.id_personal
                WHERE u.id_usuario = %s
            """, (id_usuario,))
            if u and u.get("id_persona"):
                id_pers = u["id_persona"]
                if id_cohorte > 0:
                    self.execute("UPDATE cohorte SET id_docente = %s WHERE id_cohorte = %s", (id_pers, id_cohorte))

    def cambiar_rol_usuario(self, id_usuario, nuevo_rol):
        self.execute("UPDATE usuario SET rol_sistema = %s WHERE id_usuario = %s", (nuevo_rol, id_usuario))


    # -- Respaldo de Base de Datos (SQLite nativo) --------------------------
    def buscar_mysqldump(self):
        return "sqlite_portable"

    def generar_respaldo_sql(self, ruta_archivo=None):
        """Genera un respaldo completo de la base de datos SQLite sin dependencias externas."""
        if not ruta_archivo:
            carpeta_backups = config.BASE_DIR / "backups"
            carpeta_backups.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            ruta_archivo = str(carpeta_backups / f"respaldo_asista_db_{timestamp}.sql")
        else:
            Path(ruta_archivo).parent.mkdir(parents=True, exist_ok=True)

        conn = self.connection()
        if str(ruta_archivo).endswith(".sql"):
            with open(ruta_archivo, "w", encoding="utf-8") as f:
                for line in conn.iterdump():
                    f.write(f"{line}\n")
        else:
            dest_conn = sqlite3.connect(ruta_archivo)
            with dest_conn:
                conn.backup(dest_conn)
            dest_conn.close()

        tamano_bytes = os.path.getsize(ruta_archivo)
        tamano_kb = round(tamano_bytes / 1024, 2)
        tamano_mb = round(tamano_bytes / (1024 * 1024), 2)

        return {
            "archivo": ruta_archivo,
            "nombre": os.path.basename(ruta_archivo),
            "tamano_bytes": tamano_bytes,
            "tamano_kb": tamano_kb,
            "tamano_mb": tamano_mb,
            "fecha": datetime.now()
        }

    def buscar_mysql_cli(self):
        return "sqlite_portable"

    def restaurar_respaldo_sql(self, ruta_archivo):
        """Restaura la base de datos a partir de un archivo .sql o .sqlite."""
        if not os.path.isfile(ruta_archivo):
            raise FileNotFoundError(f"No se encontró el archivo de respaldo: {ruta_archivo}")

        conn = self.connection()
        if str(ruta_archivo).endswith(".sql"):
            with open(ruta_archivo, "r", encoding="utf-8") as f:
                script = f.read()
            conn.executescript(script)
        else:
            src_conn = sqlite3.connect(ruta_archivo)
            with conn:
                src_conn.backup(conn)
            src_conn.close()

        return True

    def listar_respaldos(self):
        """Lista los archivos de respaldo (.sql y .sqlite) disponibles en la carpeta backups."""
        from pathlib import Path
        from datetime import datetime

        carpeta = Path(__file__).resolve().parent / "backups"
        if not carpeta.exists():
            return []

        respaldos = []
        for p in list(carpeta.glob("*.sql")) + list(carpeta.glob("*.sqlite")):
            try:
                stat = p.stat()
                tamano_kb = round(stat.st_size / 1024, 2)
                respaldos.append({
                    "nombre": p.name,
                    "ruta": str(p),
                    "tamano_kb": tamano_kb,
                    "fecha": datetime.fromtimestamp(stat.st_mtime)
                })
            except Exception:
                continue

        respaldos.sort(key=lambda x: x["fecha"], reverse=True)
        return respaldos

    # -- Configuración institucional y horarios por turno ---------------------
    def cargar_configuracion_institucional(self):
        """Carga parámetros institucionales y horarios por turno desde MySQL."""
        from datetime import time
        import config

        try:
            self.execute("""
                CREATE TABLE IF NOT EXISTS configuracion_institucional (
                    clave VARCHAR(60) NOT NULL,
                    valor VARCHAR(255) NOT NULL,
                    descripcion VARCHAR(255) NULL,
                    PRIMARY KEY (clave)
                );
            """)
            filas = self.fetch_all("SELECT clave, valor FROM configuracion_institucional")
            cfg = {f["clave"]: f["valor"] for f in filas} if filas else {}
        except Exception as e:
            print(f"Aviso al cargar configuración institucional: {e}")
            cfg = {}

        def _p_time(val_str, default_val):
            try:
                partes = val_str.strip().split(":")
                return time(int(partes[0]), int(partes[1]))
            except Exception:
                return default_val

        h_ent_m = _p_time(cfg.get("hora_entrada_manana", "07:15"), time(7, 15))
        h_sal_m = _p_time(cfg.get("hora_salida_manana", "12:00"), time(12, 0))
        h_ent_t = _p_time(cfg.get("hora_entrada_tarde", "12:45"), time(12, 45))
        h_sal_t = _p_time(cfg.get("hora_salida_tarde", "17:30"), time(17, 30))
        nombre_inst = cfg.get("nombre_institucion", getattr(config, "INSTITUCION", "Unidad Educativa Prof. Aristóbulo Istúriz"))
        try:
            tolerancia = int(cfg.get("tolerancia_minutos", "15"))
        except Exception:
            tolerancia = 15

        res = {
            "institucion": nombre_inst,
            "tolerancia_minutos": tolerancia,
            "Mañana": {
                "entrada_limite": h_ent_m,
                "salida_minima": h_sal_m,
                "str_entrada": h_ent_m.strftime("%H:%M"),
                "str_salida": h_sal_m.strftime("%H:%M")
            },
            "Tarde": {
                "entrada_limite": h_ent_t,
                "salida_minima": h_sal_t,
                "str_entrada": h_ent_t.strftime("%H:%M"),
                "str_salida": h_sal_t.strftime("%H:%M")
            }
        }

        # Sincronizar variables globales de config
        config.HORARIOS_TURNO = {
            "Mañana": res["Mañana"],
            "Tarde": res["Tarde"]
        }
        config.HORA_LIMITE_ENTRADA = h_ent_m
        config.HORA_SALIDA_MINIMA = h_sal_m
        config.INSTITUCION = nombre_inst

        return res

    def guardar_configuracion_institucional(self, ent_m, sal_m, ent_t, sal_t, nombre_inst=None, tolerancia=None):
        """Persiste los horarios y datos institucionales en la base de datos."""
        valores = [
            ("hora_entrada_manana", ent_m.strip(), "Hora límite de entrada para el Turno Mañana"),
            ("hora_salida_manana", sal_m.strip(), "Hora mínima de salida para el Turno Mañana"),
            ("hora_entrada_tarde", ent_t.strip(), "Hora límite de entrada para el Turno Tarde"),
            ("hora_salida_tarde", sal_t.strip(), "Hora mínima de salida para el Turno Tarde")
        ]
        if nombre_inst:
            valores.append(("nombre_institucion", nombre_inst.strip(), "Nombre oficial de la institución"))
        if tolerancia is not None:
            valores.append(("tolerancia_minutos", str(tolerancia).strip(), "Minutos de cortesía/tolerancia"))

        for clave, valor, desc in valores:
            self.execute("""
                INSERT INTO configuracion_institucional (clave, valor, descripcion)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE valor = VALUES(valor), descripcion = VALUES(descripcion)
            """, (clave, valor, desc))

        return self.cargar_configuracion_institucional()

    # =========================================================================
    # GESTIÓN INSTITUTO: PERIODOS, CURSOS, COHORTES, MATRÍCULAS Y ASISTENCIA
    # =========================================================================

    def migrar_tablas_instituto(self):
        """Crea automáticamente las tablas del instituto si no existen."""
        ddl = [
            """
            CREATE TABLE IF NOT EXISTS periodo (
                id_periodo INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre VARCHAR(80) NOT NULL,
                codigo VARCHAR(20) NOT NULL UNIQUE,
                fecha_inicio DATE NOT NULL,
                fecha_fin DATE NOT NULL,
                estado TEXT NOT NULL DEFAULT 'Activo' CHECK(estado IN ('Planificado', 'Activo', 'Finalizado', 'Archivado')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS curso (
                id_curso INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo VARCHAR(25) NOT NULL UNIQUE,
                nombre VARCHAR(120) NOT NULL,
                descripcion TEXT NULL,
                duracion_semanas INTEGER NOT NULL DEFAULT 12,
                activo INTEGER NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS cohorte (
                id_cohorte INTEGER PRIMARY KEY AUTOINCREMENT,
                id_curso INTEGER NOT NULL,
                id_periodo INTEGER NOT NULL,
                id_docente INTEGER NULL,
                nombre_grupo VARCHAR(60) NOT NULL,
                dias_semana VARCHAR(60) NOT NULL,
                hora_inicio TIME NOT NULL,
                hora_fin TIME NOT NULL,
                aula VARCHAR(60) NULL DEFAULT 'Aula Principal',
                cupo_maximo INTEGER NOT NULL DEFAULT 30,
                estado TEXT NOT NULL DEFAULT 'Inscripciones' CHECK(estado IN ('Inscripciones', 'En Curso', 'Finalizado', 'Archivado')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT fk_cohorte_curso FOREIGN KEY (id_curso) REFERENCES curso(id_curso) ON UPDATE CASCADE ON DELETE RESTRICT,
                CONSTRAINT fk_cohorte_periodo FOREIGN KEY (id_periodo) REFERENCES periodo(id_periodo) ON UPDATE CASCADE ON DELETE RESTRICT,
                CONSTRAINT fk_cohorte_docente FOREIGN KEY (id_docente) REFERENCES persona(id_persona) ON UPDATE CASCADE ON DELETE SET NULL
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS matricula (
                id_matricula INTEGER PRIMARY KEY AUTOINCREMENT,
                id_persona INTEGER NOT NULL,
                id_cohorte INTEGER NOT NULL,
                fecha_inscripcion DATE NOT NULL,
                estado TEXT NOT NULL DEFAULT 'En Curso' CHECK(estado IN ('Inscrito', 'En Curso', 'Egresado', 'Aprobado', 'Reprobado', 'Retirado')),
                porcentaje_asistencia DECIMAL(5,2) NOT NULL DEFAULT 0.00,
                observaciones VARCHAR(255) NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (id_persona, id_cohorte),
                CONSTRAINT fk_matricula_persona FOREIGN KEY (id_persona) REFERENCES persona(id_persona) ON UPDATE CASCADE ON DELETE RESTRICT,
                CONSTRAINT fk_matricula_cohorte FOREIGN KEY (id_cohorte) REFERENCES cohorte(id_cohorte) ON UPDATE CASCADE ON DELETE RESTRICT
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS asistencia_curso (
                id_asistencia_curso INTEGER PRIMARY KEY AUTOINCREMENT,
                id_matricula INTEGER NOT NULL,
                id_cohorte INTEGER NOT NULL,
                id_persona INTEGER NOT NULL,
                fecha DATE NOT NULL,
                hora TIME NOT NULL,
                estado TEXT NOT NULL DEFAULT 'Presente' CHECK(estado IN ('Presente', 'Retraso', 'Ausente', 'Justificado')),
                observaciones VARCHAR(255) NULL DEFAULT '',
                registrado_por INTEGER NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (id_matricula, fecha),
                CONSTRAINT fk_asist_matricula FOREIGN KEY (id_matricula) REFERENCES matricula(id_matricula) ON UPDATE CASCADE ON DELETE CASCADE,
                CONSTRAINT fk_asist_cohorte FOREIGN KEY (id_cohorte) REFERENCES cohorte(id_cohorte) ON UPDATE CASCADE ON DELETE CASCADE,
                CONSTRAINT fk_asist_persona FOREIGN KEY (id_persona) REFERENCES persona(id_persona) ON UPDATE CASCADE ON DELETE RESTRICT
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS sesion_clase (
                id_sesion INTEGER PRIMARY KEY AUTOINCREMENT,
                id_cohorte INTEGER NOT NULL,
                fecha DATE NOT NULL,
                hora_apertura TIME NULL,
                hora_cierre TIME NULL,
                id_docente INTEGER NULL,
                estado TEXT NOT NULL DEFAULT 'Abierta' CHECK(estado IN ('Abierta', 'Cerrada')),
                total_presentes INTEGER NOT NULL DEFAULT 0,
                total_ausentes INTEGER NOT NULL DEFAULT 0,
                total_retrasos INTEGER NOT NULL DEFAULT 0,
                total_justificados INTEGER NOT NULL DEFAULT 0,
                firma_docente VARCHAR(120) NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (id_cohorte, fecha),
                CONSTRAINT fk_sesion_cohorte FOREIGN KEY (id_cohorte)
                    REFERENCES cohorte(id_cohorte) ON UPDATE CASCADE ON DELETE CASCADE,
                CONSTRAINT fk_sesion_docente FOREIGN KEY (id_docente)
                    REFERENCES persona(id_persona) ON UPDATE CASCADE ON DELETE SET NULL
            );
            """
        ]
        for sql in ddl:
            try:
                self.execute(sql)
            except Exception as e:
                print(f"Aviso en migrar_tablas_instituto: {e}")

    # --- PERIODOS (Ciclos trimestrales de 3 meses) ---------------------------
    def listar_periodos(self, incluir_archivados=False):
        sql = "SELECT * FROM periodo WHERE 1=1"
        if not incluir_archivados:
            sql += " AND estado <> 'Archivado'"
        sql += " ORDER BY fecha_inicio DESC"
        return self.fetch_all(sql)

    def crear_periodo(self, nombre, codigo, fecha_inicio, fecha_fin, estado="Activo"):
        sql = """
            INSERT INTO periodo (nombre, codigo, fecha_inicio, fecha_fin, estado)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE nombre=VALUES(nombre), fecha_inicio=VALUES(fecha_inicio),
                                    fecha_fin=VALUES(fecha_fin), estado=VALUES(estado)
        """
        self.execute(sql, (nombre.strip(), codigo.strip().upper(), fecha_inicio, fecha_fin, estado))

    def cambiar_estado_periodo(self, id_periodo, nuevo_estado):
        self.execute("UPDATE periodo SET estado = %s WHERE id_periodo = %s", (nuevo_estado, id_periodo))

    def obtener_periodo_activo(self):
        return self.fetch_one("SELECT * FROM periodo WHERE estado = 'Activo' ORDER BY fecha_inicio DESC LIMIT 1")

    # --- CURSOS / ESPECIALIDADES (Catálogo) -----------------------------------
    def listar_cursos(self, solo_activos=False):
        sql = "SELECT * FROM curso WHERE 1=1"
        if solo_activos:
            sql += " AND activo = 1"
        sql += " ORDER BY nombre ASC"
        return self.fetch_all(sql)

    def crear_curso(self, codigo, nombre, descripcion="", duracion_semanas=12):
        sql = """
            INSERT INTO curso (codigo, nombre, descripcion, duracion_semanas, activo)
            VALUES (%s, %s, %s, %s, 1)
            ON DUPLICATE KEY UPDATE nombre=VALUES(nombre), descripcion=VALUES(descripcion),
                                    duracion_semanas=VALUES(duracion_semanas), activo=1
        """
        self.execute(sql, (codigo.strip().upper(), nombre.strip(), descripcion.strip(), duracion_semanas))

    def actualizar_curso(self, id_curso, codigo, nombre, descripcion, duracion_semanas, activo=1):
        sql = """
            UPDATE curso
            SET codigo=%s, nombre=%s, descripcion=%s, duracion_semanas=%s, activo=%s
            WHERE id_curso=%s
        """
        self.execute(sql, (codigo.strip().upper(), nombre.strip(), descripcion.strip(), duracion_semanas, activo, id_curso))

    def alternar_activo_curso(self, id_curso):
        self.execute("UPDATE curso SET activo = 1 - activo WHERE id_curso = %s", (id_curso,))

    # --- COHORTES / HORARIOS Y CICLO DE VIDA (SOFT DELETE / RESPALDO) ---------
    def listar_cohortes(self, id_periodo=None, id_docente=None, estado=None, incluir_archivados=False):
        sql = """
            SELECT c.id_cohorte, c.id_curso, c.id_periodo, c.id_docente, c.nombre_grupo,
                   c.dias_semana, c.hora_inicio, c.hora_fin, c.aula, c.cupo_maximo, c.estado,
                   cu.nombre AS curso_nombre, cu.codigo AS curso_codigo,
                   p.nombre AS periodo_nombre, p.codigo AS periodo_codigo,
                   CONCAT(IFNULL(per.nombre, ''), ' ', IFNULL(per.apellido, '')) AS docente_nombre,
                   per.cedula AS docente_cedula,
                   (SELECT COUNT(*) FROM matricula m WHERE m.id_cohorte = c.id_cohorte AND m.estado <> 'Retirado') AS total_inscritos
            FROM cohorte c
            JOIN curso cu ON cu.id_curso = c.id_curso
            JOIN periodo p ON p.id_periodo = c.id_periodo
            LEFT JOIN persona per ON per.id_persona = c.id_docente
            WHERE 1=1
        """
        params = []
        if id_periodo:
            sql += " AND c.id_periodo = %s"
            params.append(id_periodo)
        if id_docente:
            sql += " AND c.id_docente = %s"
            params.append(id_docente)
        if estado:
            sql += " AND c.estado = %s"
            params.append(estado)
        elif not incluir_archivados:
            sql += " AND c.estado <> 'Archivado'"

        sql += " ORDER BY c.estado ASC, cu.nombre ASC, c.nombre_grupo ASC"
        return self.fetch_all(sql, tuple(params))

    def crear_cohorte(self, id_curso, id_periodo, id_docente, nombre_grupo, dias_semana,
                       hora_inicio, hora_fin, aula="Aula Principal", cupo_maximo=30):
        sql = """
            INSERT INTO cohorte (id_curso, id_periodo, id_docente, nombre_grupo, dias_semana,
                                 hora_inicio, hora_fin, aula, cupo_maximo, estado)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'Inscripciones')
        """
        self.execute(sql, (id_curso, id_periodo, id_docente, nombre_grupo.strip(), dias_semana.strip(),
                           hora_inicio, hora_fin, aula.strip(), cupo_maximo))

    def actualizar_cohorte(self, id_cohorte, nombre_grupo, dias_semana, hora_inicio, hora_fin, aula, cupo_maximo, id_docente=None):
        sql = """
            UPDATE cohorte
            SET nombre_grupo=%s, dias_semana=%s, hora_inicio=%s, hora_fin=%s, aula=%s, cupo_maximo=%s, id_docente=%s
            WHERE id_cohorte=%s
        """
        self.execute(sql, (nombre_grupo.strip(), dias_semana.strip(), hora_inicio, hora_fin, aula.strip(), cupo_maximo, id_docente, id_cohorte))

    def cambiar_estado_cohorte(self, id_cohorte, nuevo_estado):
        """Permite abrir, activar, cerrar o archivar (Soft Delete) un curso/cohorte."""
        self.execute("UPDATE cohorte SET estado = %s WHERE id_cohorte = %s", (nuevo_estado, id_cohorte))
        if nuevo_estado in ('Finalizado', 'Archivado'):
            self.execute("""
                UPDATE matricula
                SET estado = 'Egresado'
                WHERE id_cohorte = %s AND estado = 'En Curso'
            """, (id_cohorte,))

    # --- MATRÍCULAS E HISTORIAL DEL ESTUDIANTE (ALUMNOS RECURRENTES) ----------
    def inscribir_estudiante_cohorte(self, id_persona, id_cohorte, observaciones=""):
        from datetime import date
        hoy = date.today()
        sql = """
            INSERT INTO matricula (id_persona, id_cohorte, fecha_inscripcion, estado, observaciones)
            VALUES (%s, %s, %s, 'En Curso', %s)
            ON DUPLICATE KEY UPDATE estado = 'En Curso', observaciones = VALUES(observaciones)
        """
        self.execute(sql, (id_persona, id_cohorte, hoy, observaciones.strip()))

    def listar_estudiantes_cohorte(self, id_cohorte):
        """Devuelve los alumnos inscritos en una cohorte para tomar lista o asistencia móvil."""
        sql = """
            SELECT m.id_matricula, m.id_persona, m.estado AS estado_matricula,
                   m.porcentaje_asistencia, m.observaciones,
                   p.cedula, p.nombre, p.apellido, p.telefono
            FROM matricula m
            JOIN persona p ON p.id_persona = m.id_persona
            WHERE m.id_cohorte = %s AND m.estado <> 'Retirado'
            ORDER BY p.apellido ASC, p.nombre ASC
        """
        return self.fetch_all(sql, (id_cohorte,))

    def obtener_historial_academico_estudiante(self, id_persona):
        """Historial acumulativo de cursos realizados por el estudiante a lo largo del tiempo."""
        sql = """
            SELECT m.id_matricula, m.fecha_inscripcion, m.estado AS estado_matricula,
                   m.porcentaje_asistencia, m.observaciones,
                   cu.nombre AS curso_nombre, cu.codigo AS curso_codigo, cu.duracion_semanas,
                   c.nombre_grupo, c.dias_semana, c.hora_inicio, c.hora_fin, c.aula,
                   p.nombre AS periodo_nombre, p.codigo AS periodo_codigo,
                   CONCAT(IFNULL(per.nombre, ''), ' ', IFNULL(per.apellido, '')) AS docente_nombre
            FROM matricula m
            JOIN cohorte c ON c.id_cohorte = m.id_cohorte
            JOIN curso cu ON cu.id_curso = c.id_curso
            JOIN periodo p ON p.id_periodo = c.id_periodo
            LEFT JOIN persona per ON per.id_persona = c.id_docente
            WHERE m.id_persona = %s
            ORDER BY m.fecha_inscripcion DESC, c.id_cohorte DESC
        """
        return self.fetch_all(sql, (id_persona,))

    def obtener_historial_asistencias_participante(self, cedula):
        """Devuelve datos de la persona y todo el registro detallado de asistencias a sus cursos sabatinos."""
        persona = self.persona_por_cedula(cedula)
        if not persona:
            return None
        id_persona = persona["id_persona"]
        sql = """
            SELECT ac.id_asistencia_curso, ac.fecha, ac.hora, ac.estado, ac.observaciones,
                   c.nombre AS curso_nombre, c.codigo AS curso_codigo, ch.nombre_grupo,
                   CONCAT(IFNULL(doc.nombre, ''), ' ', IFNULL(doc.apellido, '')) AS docente_nombre
              FROM asistencia_curso ac
              JOIN cohorte ch ON ch.id_cohorte = ac.id_cohorte
              JOIN curso c ON c.id_curso = ch.id_curso
              LEFT JOIN persona doc ON doc.id_persona = ch.id_docente
             WHERE ac.id_persona = %s
             ORDER BY ac.fecha DESC, ac.hora DESC
        """
        registros = self.fetch_all(sql, (id_persona,))
        matriculas = self.obtener_historial_academico_estudiante(id_persona)
        return {
            "persona": persona,
            "matriculas": matriculas,
            "registros": registros
        }

    # --- ASISTENCIA POR CLASE / MÓVIL DOCENTE ---------------------------------
    def registrar_bitacora_asistencia(self, id_asistencia_curso, id_matricula, id_persona, id_cohorte,
                                      fecha_asistencia, estado_anterior, estado_nuevo, accion,
                                      id_usuario_operador=None, nombre_operador="Sistema", rol_operador="Sistema",
                                      ip_origen=None, observaciones=None):
        """Registra auditoría detallada de cada inserción o modificación de asistencia."""
        sql = """
            INSERT INTO bitacora_asistencia
            (id_asistencia_curso, id_matricula, id_persona, id_cohorte, fecha_asistencia,
             estado_anterior, estado_nuevo, accion, id_usuario_operador, nombre_operador,
             rol_operador, ip_origen, observaciones)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        try:
            self.execute(sql, (
                id_asistencia_curso, id_matricula, id_persona, id_cohorte, fecha_asistencia,
                estado_anterior, estado_nuevo, accion, id_usuario_operador, nombre_operador,
                rol_operador, ip_origen, observaciones
            ))
        except Exception as e:
            import logging
            logging.error(f"Error registrando en bitacora_asistencia: {e}")

    def consultar_bitacora_asistencia(self, id_cohorte=None, fecha=None, limit=100):
        """Consulta el registro histórico de quién marcó o modificó asistencias."""
        sql = """
            SELECT b.*, CONCAT(p.nombre, ' ', p.apellido) AS nombre_participante, p.cedula
            FROM bitacora_asistencia b
            JOIN persona p ON p.id_persona = b.id_persona
            WHERE 1=1
        """
        params = []
        if id_cohorte:
            sql += " AND b.id_cohorte = %s"
            params.append(id_cohorte)
        if fecha:
            sql += " AND b.fecha_asistencia = %s"
            params.append(fecha)
        sql += " ORDER BY b.id_bitacora DESC LIMIT %s"
        params.append(limit)
        return self.fetch_all(sql, params)

    def registrar_asistencia_estudiante_curso(self, id_persona, id_cohorte, fecha, hora, estado, obs="", registrado_por=None, ip_origen=None):
        """Registra la asistencia de un participante en un curso específico (desde celular o PC) y audita la operación."""
        mat = self.fetch_one("SELECT id_matricula FROM matricula WHERE id_persona = %s AND id_cohorte = %s",
                             (id_persona, id_cohorte))
        if not mat:
            self.inscribir_estudiante_cohorte(id_persona, id_cohorte, "Inscrito automáticamente por marcaje")
            mat = self.fetch_one("SELECT id_matricula FROM matricula WHERE id_persona = %s AND id_cohorte = %s",
                                 (id_persona, id_cohorte))

        id_matricula = mat["id_matricula"]

        # Determinar si es registro inicial o modificación para la bitácora
        asist_ant = self.fetch_one(
            "SELECT id_asistencia_curso, estado FROM asistencia_curso WHERE id_matricula = %s AND fecha = %s",
            (id_matricula, fecha)
        )
        estado_ant = asist_ant["estado"] if asist_ant else None
        accion = "MODIFICACION" if asist_ant else "REGISTRO_INICIAL"

        sql = """
            INSERT INTO asistencia_curso (id_matricula, id_cohorte, id_persona, fecha, hora, estado, observaciones, registrado_por)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE hora = VALUES(hora), estado = VALUES(estado),
                                    observaciones = VALUES(observaciones), registrado_por = VALUES(registrado_por)
        """
        self.execute(sql, (id_matricula, id_cohorte, id_persona, fecha, hora, estado, obs, registrado_por))
        self.recalcular_asistencia_matricula(id_matricula)

        # Sincronización automática con la tabla principal de asistencias institucional
        try:
            asis_gral = self.asistencia_de(id_persona, fecha)
            if not asis_gral:
                self.registrar_entrada(id_persona, fecha, hora, estado, obs or "Marcaje registrado en aula/curso", registrado_por, False)
            elif asis_gral.get("estado") == "Ausente":
                self.registrar_entrada(id_persona, fecha, hora, estado, obs or "Marcaje registrado en aula/curso", registrado_por, True)
        except Exception as e_gral:
            print(f"Aviso al sincronizar con asistencia institucional: {e_gral}")

        # Obtener el ID final de la asistencia
        asist_nueva = self.fetch_one(
            "SELECT id_asistencia_curso FROM asistencia_curso WHERE id_matricula = %s AND fecha = %s",
            (id_matricula, fecha)
        )
        id_asist = asist_nueva["id_asistencia_curso"] if asist_nueva else None

        # Datos del operador para la auditoría
        nom_operador = "Sistema"
        rol_operador = "Sistema"
        if registrado_por:
            u_op = self.fetch_one("""
                SELECT u.username, u.rol_sistema, CONCAT(p.nombre, ' ', p.apellido) as nombre_completo
                FROM usuario u
                LEFT JOIN personal pe ON pe.id_personal = u.id_personal
                LEFT JOIN persona p ON p.id_persona = pe.id_persona
                WHERE u.id_usuario = %s
            """, (registrado_por,))
            if u_op:
                nom_operador = u_op.get("nombre_completo") or u_op.get("username")
                rol_operador = u_op.get("rol_sistema") or "Docente"

        self.registrar_bitacora_asistencia(
            id_asistencia_curso=id_asist,
            id_matricula=id_matricula,
            id_persona=id_persona,
            id_cohorte=id_cohorte,
            fecha_asistencia=fecha,
            estado_anterior=estado_ant,
            estado_nuevo=estado,
            accion=accion,
            id_usuario_operador=registrado_por,
            nombre_operador=nom_operador,
            rol_operador=rol_operador,
            ip_origen=ip_origen,
            observaciones=obs
        )

    def recalcular_asistencia_matricula(self, id_matricula):
        stats = self.fetch_all("""
            SELECT estado, COUNT(*) as cantidad
            FROM asistencia_curso
            WHERE id_matricula = %s
            GROUP BY estado
        """, (id_matricula,))
        if not stats:
            return

        totales = sum(s["cantidad"] for s in stats)
        presentes = sum(s["cantidad"] for s in stats if s["estado"] in ("Presente", "Retraso", "Justificado"))
        pct = round((presentes / totales) * 100, 2) if totales > 0 else 0.0

        self.execute("UPDATE matricula SET porcentaje_asistencia = %s WHERE id_matricula = %s", (pct, id_matricula))

    def obtener_asistencia_cohorte_fecha(self, id_cohorte, fecha):
        sql = """
            SELECT p.id_persona, p.cedula, CONCAT(p.apellido, ', ', p.nombre) AS nombre_completo,
                   ac.hora, ac.estado, ac.observaciones
            FROM matricula m
            JOIN persona p ON p.id_persona = m.id_persona
            LEFT JOIN asistencia_curso ac ON ac.id_matricula = m.id_matricula AND ac.fecha = %s
            WHERE m.id_cohorte = %s AND m.estado <> 'Retirado'
            ORDER BY p.apellido ASC, p.nombre ASC
        """
        return self.fetch_all(sql, (fecha, id_cohorte))

    def metricas_graficas_instituto(self, id_curso_filtro=None):
        """Genera métricas usando solo registros de asistencia de cursos."""
        cursos_base = self.fetch_all("""
            SELECT id_curso, codigo, nombre 
            FROM curso 
            WHERE activo = 1
            ORDER BY nombre ASC
        """)

        if id_curso_filtro:
            dist = self.fetch_all("""
                SELECT ac.estado, COUNT(*) AS total
                FROM asistencia_curso ac
                JOIN cohorte c ON c.id_cohorte = ac.id_cohorte
                WHERE c.id_curso = %s
                GROUP BY ac.estado
            """, (id_curso_filtro,))
        else:
            dist = self.fetch_all("""
                SELECT estado, COUNT(*) AS total
                FROM asistencia_curso
                GROUP BY estado
            """)
        
        dona = {r["estado"]: r["total"] for r in dist} if dist else {}
        for est in ["Presente", "Retraso", "Ausente", "Justificado"]:
            dona.setdefault(est, 0)

        cursos_visibles = [
            cu for cu in cursos_base
            if not id_curso_filtro or cu["id_curso"] == id_curso_filtro
        ]
        barras = []
        for cu in cursos_visibles:
            cid = cu["id_curso"]
            cnombre = cu["nombre"]
            ccod = cu.get("codigo", "")
            
            stat = self.fetch_one("""
                SELECT 
                    COUNT(ac.id_asistencia_curso) AS total_registros,
                    SUM(CASE WHEN ac.estado IN ('Presente', 'Retraso') THEN 1 ELSE 0 END) AS presentes
                FROM cohorte c
                JOIN asistencia_curso ac ON ac.id_cohorte = c.id_cohorte
                WHERE c.id_curso = %s
            """, (cid,))

            total_registros = int(stat["total_registros"] or 0) if stat else 0
            pres_s = int(stat["presentes"] or 0) if stat else 0

            barras.append({
                "id_curso": cid,
                "codigo": ccod,
                "curso": cnombre,
                "total_registros": total_registros,
                "presentes": pres_s
            })

        if id_curso_filtro:
            lineas = self.fetch_all("""
                SELECT ac.fecha,
                       COUNT(*) as total,
                       SUM(CASE WHEN ac.estado IN ('Presente', 'Retraso') THEN 1 ELSE 0 END) AS asistieron
                FROM asistencia_curso ac
                JOIN cohorte c ON c.id_cohorte = ac.id_cohorte
                WHERE c.id_curso = %s
                GROUP BY ac.fecha
                ORDER BY ac.fecha ASC
                LIMIT 30
            """, (id_curso_filtro,))
        else:
            lineas = self.fetch_all("""
                SELECT fecha,
                       COUNT(*) as total,
                       SUM(CASE WHEN estado IN ('Presente', 'Retraso') THEN 1 ELSE 0 END) AS asistieron
                FROM asistencia_curso
                GROUP BY fecha
                ORDER BY fecha ASC
                LIMIT 30
            """)

        tendencia = []
        for l in lineas:
            tot = l.get("total", 1) or 1
            asist = float(l.get("asistieron", 0) or 0)
            pct = int((asist / tot) * 100) if tot > 0 else 0
            tendencia.append({
                "fecha": str(l["fecha"]),
                "total": tot,
                "asistieron": asist,
                "porcentaje": pct
            })

        total_asist = sum(dona.values())
        asist_efectiva = dona.get("Presente", 0) + dona.get("Retraso", 0)
        pct_global = int((asist_efectiva / total_asist) * 100) if total_asist > 0 else 0
        cursos_activos = len(cursos_visibles)
        alertas = sum(
            1 for b in barras
            if b["total_registros"] > 0
            and float(b["presentes"]) / b["total_registros"] < 0.75
        )

        return {
            "dona": dona,
            "barras": barras,
            "lineas": tendencia,
            "kpis": {
                "total_asistencias": total_asist,
                "pct_global": pct_global,
                "cursos_activos": cursos_activos,
                "alertas": alertas
            }
        }

    def obtener_resumen_cohorte(self, id_cohorte):
        """Obtiene toda la información consolidada de una cohorte para el acta de asistencia oficial."""
        # 1. Info general de la cohorte
        sql_cohorte = """
            SELECT c.id_cohorte, c.id_curso, c.id_periodo, c.id_docente, c.nombre_grupo,
                   c.dias_semana, c.hora_inicio, c.hora_fin, c.aula, c.cupo_maximo, c.estado,
                   cu.nombre AS curso_nombre, cu.codigo AS curso_codigo, cu.duracion_semanas,
                   p.nombre AS periodo_nombre, p.codigo AS periodo_codigo,
                   CONCAT(IFNULL(per.nombre, ''), ' ', IFNULL(per.apellido, '')) AS docente_nombre,
                   per.cedula AS docente_cedula
            FROM cohorte c
            JOIN curso cu ON cu.id_curso = c.id_curso
            LEFT JOIN periodo p ON p.id_periodo = c.id_periodo
            LEFT JOIN persona per ON per.id_persona = c.id_docente
            WHERE c.id_cohorte = %s
        """
        cohorte = self.fetch_one(sql_cohorte, (id_cohorte,))
        if not cohorte:
            return None

        # 2. Total de sesiones dictadas para esta cohorte
        sql_sesiones = """
            SELECT COUNT(DISTINCT fecha) AS total_sesiones
            FROM asistencia_curso
            WHERE id_cohorte = %s
        """
        row_ses = self.fetch_one(sql_sesiones, (id_cohorte,))
        total_sesiones = row_ses["total_sesiones"] if row_ses else 0

        # 3. Lista de estudiantes inscritos con desglose de asistencias
        sql_estudiantes = """
            SELECT m.id_matricula, m.id_persona, m.estado AS estado_matricula,
                   p.cedula, p.nombre, p.apellido, p.telefono,
                   COALESCE(SUM(CASE WHEN ac.estado = 'Presente' THEN 1 ELSE 0 END), 0) AS presentes,
                   COALESCE(SUM(CASE WHEN ac.estado = 'Retraso' THEN 1 ELSE 0 END), 0) AS retrasos,
                   COALESCE(SUM(CASE WHEN ac.estado = 'Ausente' THEN 1 ELSE 0 END), 0) AS ausentes,
                   COALESCE(SUM(CASE WHEN ac.estado = 'Justificado' THEN 1 ELSE 0 END), 0) AS justificados
            FROM matricula m
            JOIN persona p ON p.id_persona = m.id_persona
            LEFT JOIN asistencia_curso ac ON ac.id_cohorte = m.id_cohorte AND ac.id_persona = m.id_persona
            WHERE m.id_cohorte = %s AND m.estado <> 'Retirado'
            GROUP BY m.id_matricula, m.id_persona, m.estado, p.cedula, p.nombre, p.apellido, p.telefono
            ORDER BY p.apellido ASC, p.nombre ASC
        """
        alumnos = self.fetch_all(sql_estudiantes, (id_cohorte,))

        estudiantes_resumen = []
        for a in alumnos:
            pres = int(a["presentes"] or 0)
            ret = int(a["retrasos"] or 0)
            aus = int(a["ausentes"] or 0)
            just = int(a["justificados"] or 0)

            sesiones_alumno = pres + ret + aus + just
            base = max(total_sesiones, sesiones_alumno)
            pct = round(((pres + ret) / base * 100), 1) if base > 0 else 100.0
            aprobado = "APROBADO" if pct >= 75.0 else "REPROBADO POR INASISTENCIA"

            estudiantes_resumen.append({
                "id_persona": a["id_persona"],
                "cedula": a["cedula"],
                "nombre_completo": f"{a['apellido']}, {a['nombre']}",
                "nombre": a["nombre"],
                "apellido": a["apellido"],
                "telefono": a["telefono"],
                "total_sesiones": base,
                "presentes": pres,
                "retrasos": ret,
                "ausentes": aus,
                "justificados": just,
                "porcentaje": pct,
                "estado_aprobacion": aprobado
            })

        return {
            "cohorte": cohorte,
            "total_sesiones": total_sesiones,
            "estudiantes": estudiantes_resumen
        }


    def listar_docentes(self):
        """Lista los docentes disponibles en la institucion y el total de cursos asignados."""
        return self.fetch_all("""
            SELECT p.id_persona, p.cedula, p.nombre, p.apellido,
                   CONCAT(p.nombre, ' ', p.apellido) AS nombre_completo,
                   COALESCE(per.cargo, 'Docente') AS cargo,
                   COUNT(c.id_cohorte) AS total_cohortes
            FROM persona p
            LEFT JOIN personal per ON per.id_persona = p.id_persona
            LEFT JOIN cohorte c ON c.id_docente = p.id_persona AND c.estado <> 'Archivado'
            WHERE p.tipo_persona IN ('Personal', 'Docente')
            GROUP BY p.id_persona, p.cedula, p.nombre, p.apellido, per.cargo
            ORDER BY p.nombre ASC, p.apellido ASC
        """)

    def obtener_o_crear_sesion_clase(self, id_cohorte, fecha=None, id_docente=None):
        """Obtiene o inicializa el registro de la sesion de clase de hoy."""
        from datetime import date, datetime
        f = fecha or date.today()
        h_actual = datetime.now().time()

        row = self.fetch_one("""
            SELECT * FROM sesion_clase
            WHERE id_cohorte = %s AND fecha = %s
        """, (id_cohorte, f))

        if row:
            return row

        self.execute("""
            INSERT INTO sesion_clase (id_cohorte, fecha, hora_apertura, id_docente, estado)
            VALUES (%s, %s, %s, %s, 'Abierta')
            ON DUPLICATE KEY UPDATE hora_apertura = COALESCE(hora_apertura, VALUES(hora_apertura))
        """, (id_cohorte, f, h_actual, id_docente))

        return self.fetch_one("""
            SELECT * FROM sesion_clase
            WHERE id_cohorte = %s AND fecha = %s
        """, (id_cohorte, f))

    def cerrar_sesion_clase(self, id_cohorte, fecha=None, id_docente=None, firma=None):
        """Cierra la sesion de clase, totaliza asistencias y registra la firma digital del docente."""
        from datetime import date, datetime
        f = fecha or date.today()
        h_cierre = datetime.now().time()

        self.obtener_o_crear_sesion_clase(id_cohorte, f, id_docente)

        totales = self.fetch_one("""
            SELECT
                SUM(CASE WHEN estado = 'Presente' THEN 1 ELSE 0 END) AS presentes,
                SUM(CASE WHEN estado = 'Ausente' THEN 1 ELSE 0 END) AS ausentes,
                SUM(CASE WHEN estado = 'Retraso' THEN 1 ELSE 0 END) AS retrasos,
                SUM(CASE WHEN estado = 'Justificado' THEN 1 ELSE 0 END) AS justificados
            FROM asistencia_curso
            WHERE id_cohorte = %s AND fecha = %s
        """, (id_cohorte, f)) or {}

        pres = totales.get("presentes") or 0
        aus = totales.get("ausentes") or 0
        ret = totales.get("retrasos") or 0
        just = totales.get("justificados") or 0

        self.execute("""
            UPDATE sesion_clase
            SET estado = 'Cerrada',
                hora_cierre = %s,
                id_docente = COALESCE(%s, id_docente),
                total_presentes = %s,
                total_ausentes = %s,
                total_retrasos = %s,
                total_justificados = %s,
                firma_docente = %s
            WHERE id_cohorte = %s AND fecha = %s
        """, (h_cierre, id_docente, pres, aus, ret, just, firma, id_cohorte, f))

        return {
            "estado": "Cerrada",
            "hora_cierre": str(h_cierre)[:5],
            "total_presentes": int(pres),
            "total_ausentes": int(aus),
            "total_retrasos": int(ret),
            "total_justificados": int(just),
            "firma_docente": firma
        }

    def reabrir_sesion_clase(self, id_cohorte, fecha=None):
        """Permite al docente o directiva reabrir la sesion para correcciones de ultima hora."""
        from datetime import date
        f = fecha or date.today()
        self.execute("""
            UPDATE sesion_clase
            SET estado = 'Abierta'
            WHERE id_cohorte = %s AND fecha = %s
        """, (id_cohorte, f))
        return {"estado": "Abierta"}

    def monitoreo_clases_tiempo_real(self, fecha=None):
        """Retorna el estado en tiempo real de todas las cohortes activas hoy para el monitor de la Directora."""
        from datetime import date
        f = fecha or date.today()

        return self.fetch_all("""
            SELECT
                c.id_cohorte,
                cu.codigo AS curso_codigo,
                cu.nombre AS curso_nombre,
                c.nombre_grupo,
                c.dias_semana,
                c.hora_inicio,
                c.hora_fin,
                c.aula,
                p.id_persona AS id_docente,
                CONCAT(p.nombre, ' ', p.apellido) AS docente_nombre,
                (SELECT COUNT(*) FROM matricula m WHERE m.id_cohorte = c.id_cohorte AND m.estado = 'En Curso') AS total_inscritos,
                (SELECT COUNT(*) FROM asistencia_curso ac WHERE ac.id_cohorte = c.id_cohorte AND ac.fecha = %s) AS total_marcados,
                (SELECT COUNT(*) FROM asistencia_curso ac WHERE ac.id_cohorte = c.id_cohorte AND ac.fecha = %s AND ac.estado IN ('Presente', 'Retraso')) AS total_presentes,
                COALESCE(sc.estado, 'Abierta') AS estado_sesion,
                sc.hora_apertura,
                sc.hora_cierre,
                sc.firma_docente
            FROM cohorte c
            JOIN curso cu ON cu.id_curso = c.id_curso
            LEFT JOIN persona p ON p.id_persona = c.id_docente
            LEFT JOIN sesion_clase sc ON sc.id_cohorte = c.id_cohorte AND sc.fecha = %s
            WHERE c.estado <> 'Archivado'
            ORDER BY c.hora_inicio ASC, cu.nombre ASC
        """, (f, f, f))
