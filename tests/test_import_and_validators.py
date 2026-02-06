import tempfile
import pandas as pd
import os
from lib.db import init_db, get_session
from lib.models import CourseSource, Course, Estudiante, StudentPlanItem
from lib.io_excel import import_schedule_excel
from lib.validators import check_orientation_rule
from datetime import date


def setup_function():
    init_db()
    # limpiar tablas relevantes
    from sqlalchemy import text
    with get_session() as session:
        session.execute(text("DELETE FROM student_plan_items"))
        session.execute(text("DELETE FROM course_sources"))
        session.execute(text("DELETE FROM courses"))
        session.execute(text("DELETE FROM estudiantes"))
        session.commit()


def test_import_schedule_excel_dedupe():
    # Crear un Excel temporal con dos filas idénticas (mismo MateriaID, SolapaFuente, Modulo)
    df = pd.DataFrame([
        {
            "Programa": "MBA",
            "Año": 2024,
            "Módulo": "Mod1",
            "Materia": "Demo Materia",
            "Horas": 20,
            "Profesor 1": "Prof A",
            "Profesor 2": "",
            "Profesor 3": "",
            "Inicio": "2024-01-01",
            "Final": "2024-06-30",
            "Día": "Lunes",
            "Horario": "18:00",
            "Formato": "Presencial",
            "Orientación": "Finanzas",
            "Comentarios": "",
            "TipoMateria": "Electiva",
            "SolapaFuente": "Consolid",
            "MateriaID": "M_DEMO_001",
            "MateriaKey": "M_DEMO"
        },
        {
            "Programa": "MBA",
            "Año": 2024,
            "Módulo": "Mod1",
            "Materia": "Demo Materia",
            "Horas": 20,
            "Profesor 1": "Prof A",
            "Profesor 2": "",
            "Profesor 3": "",
            "Inicio": "2024-01-01",
            "Final": "2024-06-30",
            "Día": "Lunes",
            "Horario": "18:00",
            "Formato": "Presencial",
            "Orientación": "Finanzas",
            "Comentarios": "",
            "TipoMateria": "Electiva",
            "SolapaFuente": "Consolid",
            "MateriaID": "M_DEMO_001",
            "MateriaKey": "M_DEMO"
        }
    ])

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
    try:
        with pd.ExcelWriter(tmp.name, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="CronogramaConsolidado")

        summary = import_schedule_excel(tmp.name)
        # Debe crear 1 curso y 1 source (no duplicar)
        assert summary["cursos_creados"] == 1
        assert summary["sources_creados"] == 1
        assert summary["errores_count"] == 0
    finally:
        os.unlink(tmp.name)


def test_check_orientation_rule_true():
    # Crear estudiante, 5 cursos electivas con CourseSource orientacion Finanzas y StudentPlanItem COMPLETED
    with get_session() as session:
        estudiante = Estudiante(documento="9999", nombre="Orient Test")
        session.add(estudiante)
        session.flush()

        course_ids = []
        for i in range(5):
            c = Course(
                materia_id=f"OR_{i}",
                materia_key=f"OR_{i}",
                nombre=f"Electiva OR {i}",
                programa="MBA",
                ano=2024,
                tipo_materia="Electiva",
                horas=20
            )
            session.add(c)
            session.flush()
            cs = CourseSource(course_id=c.id, solapa_fuente="S", modulo="M", orientacion="Finanzas")
            session.add(cs)
            session.flush()
            course_ids.append(c.id)

        # Añadir StudentPlanItem completados
        for cid in course_ids:
            spi = StudentPlanItem(estudiante_id=estudiante.id, course_id=cid, ano=2024, estado="COMPLETED")
            session.add(spi)

        session.commit()
        student_id = estudiante.id

    # avoid using detached ORM instance
    result = check_orientation_rule(student_id)
    assert result["cumple_regla"] is True
    assert result["max_electivas"] >= 5
