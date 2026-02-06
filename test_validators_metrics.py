#!/usr/bin/env python
"""
Script de prueba para funciones de validación y métricas de plan académico.
"""

import json
from lib.db import init_db, get_session
from lib.models import (
    Estudiante, Course, CourseSource, StudentPlanItem, Ruta, Cronograma
)
from lib.validators import check_student_plan_coherence, check_orientation_rule
from lib.metrics import (
    compute_orientation_counts, check_electives_count, get_student_risk_report
)
from datetime import date

def setup_test_data():
    """Crear datos de prueba."""
    with get_session() as session:
        # Crear cronograma
        cronograma = Cronograma(
            nombre="Cronograma Test",
            fecha_inicio=date(2024, 1, 1),
            fecha_fin=date(2025, 12, 31)
        )
        session.add(cronograma)
        session.flush()
        
        # Crear ruta
        ruta = Ruta(
            cronograma_id=cronograma.id,
            codigo="MBA_TEST",
            nombre="MBA Test"
        )
        session.add(ruta)
        session.flush()
        
        # Crear estudiante
        estudiante = Estudiante(
            documento="123456789",
            nombre="Juan Test",
            email="juan@test.com",
            ruta_id=ruta.id
        )
        session.add(estudiante)
        session.flush()
        
        # Crear cursos
        cursos = []
        
        # Curso obligatorio 1: Plan de negocio
        c1 = Course(
            materia_id="PLAN_NEG_001",
            materia_key="PLAN_NEG",
            nombre="Plan de Negocio",
            programa="MBA",
            ano=2024,
            tipo_materia="Plan de negocio",
            horas=40
        )
        session.add(c1)
        session.flush()
        cursos.append((c1.id, "Plan de negocio"))
        
        # Curso obligatorio 2: Examen Inglés
        c2 = Course(
            materia_id="EXAM_ING_001",
            materia_key="EXAM_ING",
            nombre="Examen Inglés",
            programa="MBA",
            ano=2024,
            tipo_materia="Examen Inglés",
            horas=20
        )
        session.add(c2)
        session.flush()
        cursos.append((c2.id, "Examen Inglés"))
        
        # Electivas con orientación
        electivas = [
            ("ELEC_FIN_001", "Finanzas Avanzadas", "Finanzas"),
            ("ELEC_FIN_002", "Inversiones", "Finanzas"),
            ("ELEC_FIN_003", "Financial Planning", "Finanzas"),
            ("ELEC_FIN_004", "Corporate Finance", "Finanzas"),
            ("ELEC_FIN_005", "Análisis Financiero", "Finanzas"),
            ("ELEC_MKT_001", "Marketing Digital", "Marketing"),
            ("ELEC_MKT_002", "Brand Management", "Marketing"),
            ("ELEC_OPE_001", "Gestión Operacional", "Operaciones"),
        ]
        
        for i, (materia_id, nombre, orientacion) in enumerate(electivas):
            c = Course(
                materia_id=materia_id,
                materia_key=materia_id[:8],
                nombre=nombre,
                programa="MBA",
                ano=2024,
                tipo_materia="Electiva",
                horas=30
            )
            session.add(c)
            session.flush()
            cursos.append((c.id, "Electiva"))
            
            # Crear CourseSource con orientación
            cs = CourseSource(
                course_id=c.id,
                solapa_fuente="Consolid",
                modulo="Electivas",
                orientacion=orientacion
            )
            session.add(cs)
        
        session.commit()
        
        # Crear StudentPlanItems
        # Plan de negocio (obligatorio, COMPLETED)
        spi1 = StudentPlanItem(
            estudiante_id=estudiante.id,
            course_id=cursos[0][0],
            ano=2024,
            estado="COMPLETED",
            calificacion=4.5
        )
        session.add(spi1)
        
        # Examen Inglés (obligatorio, COMPLETED)
        spi2 = StudentPlanItem(
            estudiante_id=estudiante.id,
            course_id=cursos[1][0],
            ano=2024,
            estado="COMPLETED",
            calificacion=4.0
        )
        session.add(spi2)
        
        # Electivas completadas (Finanzas)
        for i in range(2, 7):  # 5 de Finanzas completadas
            spi = StudentPlanItem(
                estudiante_id=estudiante.id,
                course_id=cursos[i][0],
                ano=2024,
                estado="COMPLETED",
                calificacion=4.2
            )
            session.add(spi)
        
        # Electivas planeadas (Marketing)
        for i in range(7, 9):  # 2 de Marketing planeadas
            spi = StudentPlanItem(
                estudiante_id=estudiante.id,
                course_id=cursos[i][0],
                ano=2024,
                estado="PLANNED"
            )
            session.add(spi)
        
        session.commit()
        return estudiante.id


def test_validators():
    """Probar funciones de validación."""
    print("\n" + "="*80)
    print("PRUEBAS DE VALIDACIÓN")
    print("="*80)
    
    student_id = setup_test_data()
    
    print(f"\n✓ Datos de prueba creados. ID Estudiante: {student_id}")
    
    # Test 1: Validar coherencia del plan
    print("\n📋 Test 1: check_student_plan_coherence()")
    print("-" * 80)
    result = check_student_plan_coherence(student_id)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    # Test 2: Validar regla de orientación
    print("\n📋 Test 2: check_orientation_rule()")
    print("-" * 80)
    result = check_orientation_rule(student_id)
    print(json.dumps(result, indent=2, ensure_ascii=False))


def test_metrics():
    """Probar funciones de métricas."""
    print("\n" + "="*80)
    print("PRUEBAS DE MÉTRICAS")
    print("="*80)
    
    with get_session() as session:
        student = session.query(Estudiante).first()
        if not student:
            print("❌ No hay estudiantes en BD")
            return
        
        student_id = student.id
        print(f"\n✓ Usando estudiante: {student.nombre} (ID: {student_id})")
    
    # Test 1: compute_orientation_counts
    print("\n📊 Test 1: compute_orientation_counts()")
    print("-" * 80)
    result = compute_orientation_counts(student_id, 2024)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    # Test 2: check_electives_count
    print("\n📊 Test 2: check_electives_count()")
    print("-" * 80)
    result = check_electives_count(student_id)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    # Test 3: get_student_risk_report
    print("\n📊 Test 3: get_student_risk_report()")
    print("-" * 80)
    result = get_student_risk_report(student_id)
    print(json.dumps(result, indent=2, ensure_ascii=False))


def main():
    """Ejecutar todas las pruebas."""
    try:
        init_db()
        print("✓ Base de datos inicializada")
        
        # Limpiar datos anteriores
        from sqlalchemy import text
        with get_session() as session:
            # Se limpian en orden inverso de dependencias
            session.execute(text("DELETE FROM student_plan_items"))
            session.execute(text("DELETE FROM course_sources"))
            session.execute(text("DELETE FROM courses"))
            session.execute(text("DELETE FROM meetings"))
            session.execute(text("DELETE FROM inscripciones"))
            session.execute(text("DELETE FROM estudiantes"))
            session.execute(text("DELETE FROM rutas"))
            session.execute(text("DELETE FROM cronogramas"))
            session.execute(text("DELETE FROM cambios"))
            session.commit()
        print("✓ Datos previos limpiados")
        
        test_validators()
        test_metrics()
        
        print("\n" + "="*80)
        print("✅ TODAS LAS PRUEBAS COMPLETADAS")
        print("="*80)
        
    except Exception as e:
        print(f"\n❌ Error durante las pruebas: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
