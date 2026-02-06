2026-02-06: ✅ ESTABILIZACIÓN DE TESTS - Inicialización perezosa del engine BD (lib/db.py) y conftest en raíz para setup consistente de tests. Todos los tests pasan (4/4).
2026-02-06: Creada página `pages/05_Cambios.py` - visor de ChangeLog con filtros por fecha, estudiante, entidad y export CSV.
2026-02-06: Creada página `pages/04_Inscripciones.py` - reconciliación entre plan y enrollments, edición y alertas.
2026-02-06: Creada página `pages/06_Reportes.py` - reportes: demanda por curso, demanda electivas por mes/módulo, cumplimiento y lista de riesgo (con exportación).
2026-02-06: Agregado `lib/seed_demo.py` y tests mínimos `tests/test_import_and_validators.py` para import_schedule_excel, check_orientation_rule y dedupe de CourseSource.
2026-02-05: Creado modelo `Enrollment` en `lib/models.py` - matrículas reales de estudiantes con status, notas y validaciones.
2026-02-05: Creada página `pages/03_Rutas.py` - gestión de versiones de plan, agregar materias, historial y validaciones.
