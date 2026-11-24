# Contexto del Proyecto: ASISTA

## Arquitectura y Stack
- Base de datos: SQLite (usar consultas parametrizadas con ?, activar PRAGMA journal_mode=WAL; y PRAGMA foreign_keys=ON;, y configurar timeout adecuado).
- Flujo: Módulo móvil registra asistencia y la envía/sincroniza con el sistema de escritorio.
- Entorno: Python en Windows (Asista_Sistema / asista).

## Reglas para los agentes
1. No borrar ni renombrar tablas o columnas existentes sin documentarlo.
2. Evitar 'database is locked' usando conexiones cortas, manejo de transacciones (BEGIN / COMMIT / ROLLBACK) y try/except.
3. Mantener una interfaz limpia, clara y agradable de ver sin romper la lógica de datos.
4. No agregar librerías innecesarias si ya hay una solución simple y estable.
