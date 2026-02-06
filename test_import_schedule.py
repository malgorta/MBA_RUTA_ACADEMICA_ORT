#!/usr/bin/env python3
"""
Script de prueba para la función import_schedule_excel
"""

import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent))

from lib.io_excel import import_schedule_excel
from lib.database import init_db
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    # Inicializar BD
    init_db()
    
    # Path al archivo de prueba
    excel_path = Path(__file__).parent / "data" / "Cronograma_2026_verificado_completo.xlsx"
    
    if not excel_path.exists():
        logger.error(f"Archivo de prueba no encontrado: {excel_path}")
        logger.info(f"Por favor, coloca el archivo en: {excel_path}")
        return
    
    # Ejecutar importación
    logger.info(f"Importando cronograma desde: {excel_path}")
    result = import_schedule_excel(str(excel_path))
    
    # Mostrar resultado
    print("\n" + "="*60)
    print("RESULTADO DE IMPORTACIÓN")
    print("="*60)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print("="*60)
    
    # Mostrar resumen
    print(f"\n✓ Cursos creados: {result['cursos_creados']}")
    print(f"✓ Cursos actualizados: {result['cursos_actualizados']}")
    print(f"✓ Sources creados: {result['sources_creados']}")
    print(f"✓ Sources actualizados: {result['sources_actualizados']}")
    print(f"✗ Errores: {result['errores_count']}")
    
    if result['errores']:
        print("\nDetalles de errores:")
        for error in result['errores'][:5]:  # Mostrar primeros 5
            print(f"  - {error}")
        if len(result['errores']) > 5:
            print(f"  ... y {len(result['errores']) - 5} errores más")

if __name__ == "__main__":
    main()
