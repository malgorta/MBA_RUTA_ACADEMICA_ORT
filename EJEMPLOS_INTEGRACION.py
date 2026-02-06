"""
Ejemplos de integración de import_schedule_excel() en las páginas Streamlit
"""

# ===============================================================
# EJEMPLO 1: Página de importación en pages/cronograma.py
# ===============================================================

example_cronograma_py = """
import streamlit as st
import pandas as pd
from lib.io_excel import import_schedule_excel
from lib.database import get_session
from lib.models import Course, CourseSource
import tempfile
import os

st.set_page_config(page_title="Cronograma", layout="wide")

tab1, tab2, tab3 = st.tabs(["Importar", "Cursos", "Fuentes"])

with tab1:
    st.header("📥 Importar Cronograma")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.info(
            "Carga un archivo Excel con la hoja 'CronogramaConsolidado'. "
            "Las columnas requeridas se validarán automáticamente."
        )
        
        archivo = st.file_uploader(
            "Selecciona archivo Excel (.xlsx)",
            type=["xlsx"],
            key="cronograma_upload"
        )
    
    if archivo:
        # Crear archivo temporal
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, archivo.name)
        
        with open(temp_path, "wb") as f:
            f.write(archivo.getbuffer())
        
        # Botón para importar
        if st.button("🚀 Importar Cronograma", type="primary"):
            with st.spinner("Procesando cronograma..."):
                resultado = import_schedule_excel(temp_path)
            
            # Mostrar resumen
            st.success("✅ Importación completada")
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Cursos Creados", resultado['cursos_creados'])
            col2.metric("Cursos Actualizados", resultado['cursos_actualizados'])
            col3.metric("Sources Creados", resultado['sources_creados'])
            col4.metric("Sources Actualizados", resultado['sources_actualizados'])
            
            if resultado['errores_count'] > 0:
                with st.expander(f"⚠️ {resultado['errores_count']} Errores encontrados"):
                    for error in resultado['errores'][:10]:
                        st.write(f"• {error}")
                    if len(resultado['errores']) > 10:
                        st.write(f"... y {len(resultado['errores']) - 10} errores más")
            else:
                st.success("✓ Sin errores")
            
            # Limpiar archivo temporal
            os.remove(temp_path)

with tab2:
    st.header("📚 Cursos")
    
    try:
        with get_session() as session:
            cursos = session.query(Course).all()
            
            if cursos:
                df = pd.DataFrame([{
                    "ID": c.id,
                    "MateriaID": c.materia_id,
                    "Nombre": c.nombre,
                    "Programa": c.programa,
                    "Año": c.ano,
                    "Horas": c.horas,
                    "Tipo": c.tipo_materia,
                    "Estado": c.estado
                } for c in cursos])
                
                st.dataframe(df, use_container_width=True, hide_index=True)
                st.info(f"Total: {len(cursos)} cursos")
            else:
                st.info("No hay cursos importados aún")
    except Exception as e:
        st.error(f"Error: {e}")

with tab3:
    st.header("🔗 Fuentes de Cursos")
    
    try:
        with get_session() as session:
            sources = session.query(CourseSource).join(Course).all()
            
            if sources:
                df = pd.DataFrame([{
                    "ID": s.id,
                    "Curso": s.course.nombre,
                    "Módulo": s.modulo,
                    "Solapa": s.solapa_fuente,
                    "Profesor": s.profesor_1,
                    "Inicio": s.inicio,
                    "Final": s.final,
                    "Horario": s.horario,
                    "Formato": s.formato,
                    "Orientación": s.orientacion
                } for s in sources])
                
                st.dataframe(df, use_container_width=True, hide_index=True)
                st.info(f"Total: {len(sources)} fuentes")
            else:
                st.info("No hay fuentes importadas aún")
    except Exception as e:
        st.error(f"Error: {e}")
"""

# ===============================================================
# EJEMPLO 2: Función auxiliar para validación previa
# ===============================================================

example_validation = """
def validar_cronograma_excel(path: str) -> tuple[bool, str]:
    \"\"\"
    Validar estructura del Excel antes de importar.
    
    Returns:
        (es_válido, mensaje)
    \"\"\"
    import pandas as pd
    
    REQUIRED_COLUMNS = {
        "Programa", "Año", "Módulo", "Materia", "Horas",
        "Profesor 1", "Profesor 2", "Profesor 3", "Inicio", "Final",
        "Día", "Horario", "Formato", "Orientación", "Comentarios",
        "TipoMateria", "SolapaFuente", "MateriaID", "MateriaKey"
    }
    
    try:
        # Leer primeras filas
        df = pd.read_excel(path, sheet_name="CronogramaConsolidado", nrows=1)
        
        # Validar columnas
        missing = REQUIRED_COLUMNS - set(df.columns)
        if missing:
            return False, f"Columnas faltantes: {', '.join(sorted(missing))}"
        
        return True, "Excel válido"
    
    except Exception as e:
        return False, f"Error: {str(e)}"

# Uso en Streamlit
is_valid, msg = validar_cronograma_excel(temp_path)
if not is_valid:
    st.error(msg)
else:
    st.success(msg)
"""

# ===============================================================
# EJEMPLO 3: Reporte de cambios después de importar
# ===============================================================

example_report = """
def generar_reporte_importacion(resultado: dict) -> str:
    \"\"\"Generar reporte HTML de la importación.\"\"\"
    
    html = f\"\"\"
    <div style='background-color: #f0f2f6; padding: 20px; border-radius: 10px;'>
        <h3>📊 Reporte de Importación</h3>
        
        <div style='display: grid; grid-template-columns: 1fr 1fr; gap: 15px;'>
            <div style='background-color: #e7f3ff; padding: 15px; border-radius: 5px;'>
                <h4>✨ Creaciones</h4>
                <p><strong>Cursos:</strong> {resultado['cursos_creados']}</p>
                <p><strong>Sources:</strong> {resultado['sources_creados']}</p>
            </div>
            
            <div style='background-color: #e6f7ff; padding: 15px; border-radius: 5px;'>
                <h4>🔄 Actualizaciones</h4>
                <p><strong>Cursos:</strong> {resultado['cursos_actualizados']}</p>
                <p><strong>Sources:</strong> {resultado['sources_actualizados']}</p>
            </div>
        </div>
        
        <div style='margin-top: 15px;'>
            <p><strong>Total procesados:</strong> {resultado['total_filas']}</p>
            <p style='color: red;'><strong>Errores:</strong> {resultado['errores_count']}</p>
        </div>
    </div>
    \"\"\"
    
    return html

# Uso
st.markdown(generar_reporte_importacion(resultado), unsafe_allow_html=True)
"""

# ===============================================================
# EJEMPLO 4: Descarga de reporte de errores
# ===============================================================

example_error_download = """
import json
from datetime import datetime

def descargar_reporte_errores(resultado: dict):
    \"\"\"Generar archivo con errores para descargar.\"\"\"
    
    if not resultado['errores']:
        st.info("No hay errores para descargar")
        return
    
    # Crear JSON con errores
    reporte = {
        "fecha": datetime.now().isoformat(),
        "total_errores": resultado['errores_count'],
        "total_filas": resultado['total_filas'],
        "errores": resultado['errores']
    }
    
    json_str = json.dumps(reporte, indent=2, ensure_ascii=False)
    
    st.download_button(
        label="📥 Descargar reporte de errores (JSON)",
        data=json_str,
        file_name=f"cronograma_errores_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        mime="application/json"
    )

# Uso en la página
if resultado['errores']:
    descargar_reporte_errores(resultado)
"""

# ===============================================================
# EJEMPLO 5: Monitoreo y logs  
# ===============================================================

example_monitoring = """
def mostrar_logs_importacion():
    \"\"\"Mostrar últimas líneas del log.\"\"\"
    from pathlib import Path
    
    log_file = Path("logs/app.log")
    
    if log_file.exists():
        with open(log_file, "r") as f:
            lineas = f.readlines()
            ultimas = lineas[-20:]  # Últimas 20 líneas
        
        with st.expander("📋 Últimos logs"):
            for linea in ultimas:
                st.code(linea, language="text")
    else:
        st.info("No hay logs aún")

# Uso
mostrar_logs_importacion()
"""

print("Ejemplos de integración guardados en memoria para referencia")
