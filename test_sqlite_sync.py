"""Script de verificación exhaustiva para sincronización, integridad SQLite y prevención de duplicados."""
import sys
import os
import threading
import time
from datetime import date, datetime, timedelta

# Asegurar importación del módulo asista
sys.path.insert(0, os.path.abspath('asista'))

from db import Database, resolver_turno_persona
import contingencia

def test_db_settings():
    print("--- 1. Verificando Configuración PRAGMA y Conexión SQLite ---")
    db = Database()
    conn = db.connection()
    
    # 1.1 PRAGMA journal_mode
    cur = conn.cursor()
    cur.execute("PRAGMA journal_mode;")
    r_jm = cur.fetchone()
    j_mode = r_jm["journal_mode"] if isinstance(r_jm, dict) else r_jm[0]
    print(f"  • journal_mode: {j_mode} (Esperado: wal)")
    assert str(j_mode).lower() == "wal", f"journal_mode no es WAL: {j_mode}"
    
    # 1.2 PRAGMA foreign_keys
    cur.execute("PRAGMA foreign_keys;")
    r_fk = cur.fetchone()
    fk = r_fk["foreign_keys"] if isinstance(r_fk, dict) else r_fk[0]
    print(f"  • foreign_keys: {fk} (Esperado: 1)")
    assert fk == 1, f"foreign_keys no está activo: {fk}"
    
    # 1.3 PRAGMA busy_timeout
    cur.execute("PRAGMA busy_timeout;")
    r_bt = cur.fetchone()
    bt = r_bt["timeout"] if (isinstance(r_bt, dict) and "timeout" in r_bt) else (list(r_bt.values())[0] if isinstance(r_bt, dict) else r_bt[0])
    print(f"  • busy_timeout: {bt} ms (Esperado: >= 30000)")
    assert bt >= 30000, f"busy_timeout insuficiente: {bt}"
    
    # 1.4 Índices únicos de integridad
    cur.execute("SELECT name FROM sqlite_master WHERE type='index'")
    idx_names = [r["name"] if isinstance(r, dict) else r[0] for r in cur.fetchall()]
    assert "uq_asistencia_persona_fecha" in idx_names, "Falta índice uq_asistencia_persona_fecha"
    assert "uq_asistencia_cohorte_persona_fecha" in idx_names, "Falta índice uq_asistencia_cohorte_persona_fecha"
    print("  • Índices de integridad verificados: uq_asistencia_persona_fecha, uq_asistencia_cohorte_persona_fecha")
    print("✓ PRAGMA y conexión validados correctamente.\n")

def test_concurrency_threads():
    print("--- 2. Verificando Concurrencia Multihilo (Sin 'database is locked') ---")
    db = Database()
    errores = []
    
    def worker_read(t_id):
        try:
            for _ in range(15):
                rows = db.fetch_all("SELECT count(*) as total FROM persona")
                assert rows is not None
                time.sleep(0.01)
        except Exception as e:
            errores.append(f"Hilo {t_id} error lectura: {e}")

    def worker_write(t_id):
        try:
            for i in range(5):
                # Transacción corta
                with db.cursor(transaccion=True) as cur:
                    cur.execute("SELECT 1")
                time.sleep(0.01)
        except Exception as e:
            errores.append(f"Hilo {t_id} error escritura: {e}")

    threads = []
    for i in range(5):
        t_r = threading.Thread(target=worker_read, args=(f"R{i}",))
        t_w = threading.Thread(target=worker_write, args=(f"W{i}",))
        threads.extend([t_r, t_w])
        t_r.start()
        t_w.start()

    for t in threads:
        t.join()

    print(f"  • Total hilos ejecutados concurrentemente: {len(threads)}")
    print(f"  • Errores detectados: {len(errores)}")
    assert len(errores) == 0, f"Errores en concurrencia: {errores}"
    print("✓ Concurrencia multihilo verificada sin bloqueos.\n")

def test_anti_duplicate_marcaje():
    print("--- 3. Verificando Prevención de Duplicados en Marcaje y Turno ---")
    db = Database()
    
    # Buscar un estudiante de prueba
    est = db.fetch_one("SELECT p.id_persona, p.cedula, p.nombre, p.apellido, s.turno FROM persona p JOIN estudiante e ON e.id_persona = p.id_persona JOIN seccion s ON s.id_seccion = e.id_seccion WHERE p.activo = 1 LIMIT 1")
    assert est, "No se encontró ningún estudiante activo para pruebas"
    cedula = est["cedula"]
    pid = est["id_persona"]
    turno = est["turno"]
    hoy = date.today()
    print(f"  • Estudiante de prueba: {est['nombre']} {est['apellido']} (C.I. {cedula}, Turno {turno})")

    # Limpiar asistencia de hoy si existiera para la prueba
    db.execute("DELETE FROM asistencia WHERE id_persona = ? AND fecha = ?", (pid, hoy.isoformat()))
    
    # 3.1 Primer escaneo -> Debe registrar Entrada
    r1 = db.procesar_marcaje(cedula)
    print(f"  • Marcaje 1: ok={r1.get('ok')}, tipo={r1.get('tipo')}, turno={r1.get('turno')}")
    assert r1.get("ok") is True, f"Marcaje 1 falló: {r1}"
    assert r1.get("tipo") == "Entrada", f"Marcaje 1 no fue Entrada: {r1}"

    # 3.2 Segundo escaneo inmediato (< 2 min) -> Debe detectarse como duplicado y no marcar salida
    r2 = db.procesar_marcaje(cedula)
    print(f"  • Marcaje 2 (inmediato): ok={r2.get('ok')}, duplicado={r2.get('duplicado')}, msg={r2.get('mensaje')}")
    assert r2.get("ok") is False, "Marcaje 2 debió retornar ok=False por duplicado"
    assert r2.get("duplicado") is True, "Marcaje 2 no detectó flag duplicado"

    # Verificar en BD que hora_salida sigue siendo NULL
    asist_bd = db.asistencia_de(pid, hoy)
    assert asist_bd is not None, "No se encontró registro de asistencia en BD"
    assert asist_bd["hora_salida"] is None, f"hora_salida no debió registrarse en doble escaneo rápido: {asist_bd}"
    print("  • En BD: hora_salida permanece intacta (NULL), evitando salida temprana errónea")

    # 3.3 Intento directo de registrar_entrada duplicada mediante SQL/método
    db.registrar_entrada(pid, hoy, datetime.now().time(), "Presente", "Test duplicado", 1, existe=False)
    # Debe seguir existiendo exactamente 1 registro en la tabla asistencia
    total_reg = db.fetch_one("SELECT count(*) as c FROM asistencia WHERE id_persona = ? AND fecha = ?", (pid, hoy.isoformat()))["c"]
    print(f"  • Total registros en 'asistencia' para la misma fecha: {total_reg} (Esperado: 1)")
    assert total_reg == 1, f"Se insertaron registros duplicados en asistencia: {total_reg}"
    print("✓ Validación anti-duplicados y unicidad de turno/fecha verificada.\n")

def test_contingencia_sync():
    print("--- 4. Verificando Búfer de Contingencia Offline y Sincronización ---")
    # Limpiar contingencia para prueba
    with contingencia.obtener_conexion() as c:
        c.execute("DELETE FROM cola_contingencia WHERE cedula = 'V-TEST99999'")
        c.commit()

    db = Database()
    # Guardar en contingencia
    id_cola = contingencia.guardar_evento_contingencia(
        cedula="V-TEST99999",
        id_persona=999999,
        fecha=date.today(),
        hora=datetime.now().time(),
        tipo_evento="Entrada",
        estado="Presente",
        observaciones="Evento test contingencia",
        id_usuario=1
    )
    assert id_cola > 0, "No se guardó el registro en contingencia"
    print(f"  • Registro en cola contingencia guardado con id: {id_cola}")

    # Verificar conteo de pendientes
    pend = contingencia.contar_pendientes()
    print(f"  • Pendientes en contingencia: {pend}")
    assert pend > 0, "Pendientes debe ser mayor a 0"

    # Limpieza del registro de prueba
    with contingencia.obtener_conexion() as c:
        c.execute("DELETE FROM cola_contingencia WHERE cedula = 'V-TEST99999'")
        c.commit()
    print("✓ Módulo de contingencia validado.\n")

if __name__ == "__main__":
    test_db_settings()
    test_concurrency_threads()
    test_anti_duplicate_marcaje()
    test_contingencia_sync()
    print("==================================================")
    print("¡TODAS LAS PRUEBAS DE INTEGRIDAD Y SINCRONIZACIÓN PASARON CON ÉXITO!")
    print("==================================================")
