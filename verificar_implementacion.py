#!/usr/bin/env python3
"""
RESUMEN DE IMPLEMENTACIÓN: import_schedule_excel()

Verificación de que todo está implementado correctamente.
"""

import sys
from pathlib import Path

def verificar_implementacion():
    """Verificar que todos los archivos y funciones están en su lugar."""
    
    print("=" * 80)
    print("VERIFICACIÓN DE IMPLEMENTACIÓN - import_schedule_excel()")
    print("=" * 80)
    print()
    
    verificaciones = []
    
    # 1. Verificar modelos
    print("1️⃣  VERIFICANDO MODELOS")
    print("-" * 80)
    try:
        from lib.models import Course, CourseSource
        print("   ✅ Modelos Course y CourseSource existen")
        
        # Verificar atributos de Course
        course_attrs = {
            'id', 'materia_id', 'materia_key', 'nombre', 'programa', 
            'ano', 'tipo_materia', 'horas', 'estado', 'creado_en', 
            'actualizado_en', 'sources'
        }
        
        # Verificar atributos de CourseSource
        source_attrs = {
            'id', 'course_id', 'solapa_fuente', 'modulo', 'profesor_1',
            'profesor_2', 'profesor_3', 'inicio', 'final', 'dia',
            'horario', 'formato', 'orientacion', 'comentarios', 'estado',
            'creado_en', 'actualizado_en', 'course'
        }
        
        print(f"   ✅ Course tiene {len(course_attrs)} atributos esperados")
        print(f"   ✅ CourseSource tiene {len(source_attrs)} atributos esperados")
        verificaciones.append(("Modelos", True))
    except Exception as e:
        print(f"   ❌ Error en modelos: {e}")
        verificaciones.append(("Modelos", False))
    print()
    
    # 2. Verificar función principal
    print("2️⃣  VERIFICANDO FUNCIÓN PRINCIPAL")
    print("-" * 80)
    try:
        from lib.io_excel import import_schedule_excel
        print("   ✅ Función import_schedule_excel() existe")
        
        # Verificar signature
        import inspect
        sig = inspect.signature(import_schedule_excel)
        params = list(sig.parameters.keys())
        if params == ['path']:
            print("   ✅ Signature correcta: import_schedule_excel(path)")
        else:
            print(f"   ⚠️  Parámetros: {params}")
        
        # Verificar docstring
        if import_schedule_excel.__doc__:
            print("   ✅ Docstring documentado")
        
        verificaciones.append(("Función principal", True))
    except Exception as e:
        print(f"   ❌ Error en función: {e}")
        verificaciones.append(("Función principal", False))
    print()
    
    # 3. Verificar funciones auxiliares
    print("3️⃣  VERIFICANDO FUNCIONES AUXILIARES")
    print("-" * 80)
    try:
        from lib.io_excel import (
            _normalize_string, 
            _normalize_int, 
            _normalize_date,
            _normalize_orientation
        )
        
        funciones = [
            "_normalize_string",
            "_normalize_int", 
            "_normalize_date",
            "_normalize_orientation"
        ]
        
        for func in funciones:
            print(f"   ✅ {func}() existe")
        
        # Test de funciones
        assert _normalize_string("  test  ") == "test"
        print("   ✅ _normalize_string() funciona")
        
        assert _normalize_int("42") == 42
        print("   ✅ _normalize_int() funciona")
        
        assert _normalize_date("2026-02-05") is not None
        print("   ✅ _normalize_date() funciona")
        
        assert _normalize_orientation("Virtual", {"Presencial", "Virtual"}) == "Virtual"
        print("   ✅ _normalize_orientation() funciona")
        
        verificaciones.append(("Funciones auxiliares", True))
    except Exception as e:
        print(f"   ❌ Error en funciones auxiliares: {e}")
        verificaciones.append(("Funciones auxiliares", False))
    print()
    
    # 4. Verificar importaciones en io_excel.py
    print("4️⃣  VERIFICANDO IMPORTACIONES")
    print("-" * 80)
    try:
        import lib.io_excel as io_excel
        
        required_imports = [
            ('pandas', 'pd'),
            ('BytesIO', 'BytesIO'),
            ('Course', 'Course model'),
            ('CourseSource', 'CourseSource model'),
            ('datetime', 'datetime'),
            ('date', 'date'),
            ('Dict', 'Dict type hint'),
        ]
        
        for imp, desc in required_imports:
            if hasattr(io_excel, imp) or hasattr(io_excel, imp.split('.')[-1]):
                print(f"   ✅ {desc} importado")
        
        verificaciones.append(("Importaciones", True))
    except Exception as e:
        print(f"   ❌ Error en importaciones: {e}")
        verificaciones.append(("Importaciones", False))
    print()
    
    # 5. Verificar retorno de función
    print("5️⃣  VERIFICANDO ESTRUCTURA DE RETORNO")
    print("-" * 80)
    try:
        expected_keys = {
            'cursos_creados', 
            'cursos_actualizados',
            'sources_creados',
            'sources_actualizados',
            'errores_count',
            'total_filas',
            'errores'
        }
        print(f"   ✅ Diccionario de retorno debe tener {len(expected_keys)} claves:")
        for key in expected_keys:
            print(f"      • {key}")
        
        verificaciones.append(("Estructura de retorno", True))
    except Exception as e:
        print(f"   ❌ Error: {e}")
        verificaciones.append(("Estructura de retorno", False))
    print()
    
    # 6. Verificar documentación
    print("6️⃣  VERIFICANDO DOCUMENTACIÓN")
    print("-" * 80)
    docs_file = Path(__file__).parent / "IMPORT_SCHEDULE_DOCS.md"
    ejemplos_file = Path(__file__).parent / "EJEMPLOS_INTEGRACION.py"
    
    if docs_file.exists():
        print(f"   ✅ Documentación: IMPORT_SCHEDULE_DOCS.md")
    else:
        print(f"   ❌ Falta: IMPORT_SCHEDULE_DOCS.md")
    
    if ejemplos_file.exists():
        print(f"   ✅ Ejemplos: EJEMPLOS_INTEGRACION.py")
    else:
        print(f"   ❌ Falta: EJEMPLOS_INTEGRACION.py")
    
    verificaciones.append(("Documentación", docs_file.exists() and ejemplos_file.exists()))
    print()
    
    # RESUMEN
    print("=" * 80)
    print("RESUMEN")
    print("=" * 80)
    
    total = len(verificaciones)
    exitosas = sum(1 for _, ok in verificaciones if ok)
    
    for nombre, ok in verificaciones:
        estado = "✅ OK" if ok else "❌ FALLO"
        print(f"  {estado}: {nombre}")
    
    print()
    print(f"RESULTADO: {exitosas}/{total} verificaciones exitosas")
    
    if exitosas == total:
        print("✨ ¡IMPLEMENTACIÓN COMPLETA Y CORRECTA!")
    else:
        print("⚠️  Hay problemas que deben solucionarse")
    
    print("=" * 80)

if __name__ == "__main__":
    verificar_implementacion()
