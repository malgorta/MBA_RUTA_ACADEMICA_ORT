import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import date
from lib.db import get_session
from lib.models import Course, CourseSource
from lib.io_excel import import_schedule_excel, exportar_excel
from lib.utils import get_logger, format_date

logger = get_logger(__name__)

def run():
    st.set_page_config(page_title="Cronograma", layout="wide")
    st.title("📅 Gestión de Cronograma")
    
    tab1, tab2, tab3 = st.tabs(["Importar", "Cursos", "Fuentes"])
    
    # ========== TAB 1: IMPORTAR ==========
    with tab1:
        st.subheader("Importar Cronograma desde Excel")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            uploaded_file = st.file_uploader(
                "Selecciona archivo Excel (CronogramaConsolidado)",
                type=["xlsx", "xls"],
                help="El archivo debe contener la hoja 'CronogramaConsolidado'"
            )
        
        with col2:
            st.write("")
            st.write("")
            import_button = st.button("🚀 Importar", use_container_width=True, key="import_btn")
        
        if import_button:
            if uploaded_file is None:
                st.error("⚠️ Por favor selecciona un archivo Excel")
            else:
                with st.spinner("Importando cronograma..."):
                    # Guardar archivo temporal
                    import tempfile
                    import os
                    
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
                        tmp.write(uploaded_file.getbuffer())
                        tmp_path = tmp.name
                    
                    try:
                        # Importar
                        result = import_schedule_excel(tmp_path)
                        
                        # Mostrar resumen
                        st.success("✅ Importación completada")
                        
                        # Métricas principales
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            st.metric(
                                "Cursos Creados",
                                result["cursos_creados"],
                                delta=None
                            )
                        
                        with col2:
                            st.metric(
                                "Cursos Actualizados",
                                result["cursos_actualizados"],
                                delta=None
                            )
                        
                        with col3:
                            st.metric(
                                "Fuentes Creadas",
                                result["sources_creados"],
                                delta=None
                            )
                        
                        with col4:
                            st.metric(
                                "Fuentes Actualizadas",
                                result["sources_actualizados"],
                                delta=None
                            )
                        
                        st.divider()
                        
                        # Resumen detallado
                        col1, col2 = st.columns([1, 1])
                        
                        with col1:
                            st.info(f"📊 Total de filas procesadas: {result['total_filas']}")
                        
                        with col2:
                            if result["errores_count"] > 0:
                                st.warning(f"⚠️ Errores encontrados: {result['errores_count']}")
                            else:
                                st.success("✓ Sin errores")
                        
                        # Mostrar errores si existen
                        if result["errores"] and len(result["errores"]) > 0:
                            st.divider()
                            st.subheader("Errores encontrados")
                            
                            with st.expander(f"Ver {len(result['errores'])} error(es)", expanded=False):
                                for i, error in enumerate(result["errores"][:20], 1):
                                    st.error(f"{i}. {error}", icon="❌")
                                
                                if len(result["errores"]) > 20:
                                    st.info(f"... y {len(result['errores']) - 20} errores más")
                    
                    finally:
                        # Limpiar archivo temporal
                        if os.path.exists(tmp_path):
                            os.remove(tmp_path)
    
    # ========== TAB 2: CURSOS ==========
    with tab2:
        st.subheader("Visualizar Cursos")
        
        with get_session() as session:
            courses = session.query(Course).all()
            
            if not courses:
                st.info("No hay cursos registrados. Importa un cronograma primero.")
            else:
                # Preparar datos
                df_courses = pd.DataFrame([{
                    "ID": c.id,
                    "MateriaID": c.materia_id,
                    "MateriaKey": c.materia_key,
                    "Nombre": c.nombre,
                    "Programa": c.programa or "-",
                    "Año": c.ano or "-",
                    "TipoMateria": c.tipo_materia or "-",
                    "Horas": c.horas or "-",
                    "Estado": c.estado,
                    "Creado": format_date(c.creado_en),
                    "Actualizado": format_date(c.actualizado_en)
                } for c in courses])
                
                # Filtros
                st.subheader("Filtros")
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    programas = ["Todos"] + sorted([p for p in df_courses["Programa"].unique() if p and p != "-"])
                    selected_programa = st.selectbox("Programa", programas, key="filter_programa")
                
                with col2:
                    anos = ["Todos"] + sorted([str(a) for a in df_courses["Año"].unique() if a and a != "-"])
                    selected_ano = st.selectbox("Año", anos, key="filter_ano")
                
                with col3:
                    tipos = ["Todos"] + sorted([t for t in df_courses["TipoMateria"].unique() if t and t != "-"])
                    selected_tipo = st.selectbox("Tipo de Materia", tipos, key="filter_tipo")
                
                with col4:
                    estados = ["Todos"] + sorted(df_courses["Estado"].unique().tolist())
                    selected_estado = st.selectbox("Estado", estados, key="filter_estado")
                
                # Aplicar filtros
                df_filtered = df_courses.copy()
                
                if selected_programa != "Todos":
                    df_filtered = df_filtered[df_filtered["Programa"] == selected_programa]
                
                if selected_ano != "Todos":
                    df_filtered = df_filtered[df_filtered["Año"] == int(selected_ano)]
                
                if selected_tipo != "Todos":
                    df_filtered = df_filtered[df_filtered["TipoMateria"] == selected_tipo]
                
                if selected_estado != "Todos":
                    df_filtered = df_filtered[df_filtered["Estado"] == selected_estado]
                
                # Mostrar tabla
                st.divider()
                st.write(f"**Cursos encontrados: {len(df_filtered)} de {len(df_courses)}**")
                
                st.dataframe(
                    df_filtered,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "ID": st.column_config.NumberColumn(width="small"),
                        "MateriaID": st.column_config.TextColumn(width="medium"),
                        "MateriaKey": st.column_config.TextColumn(width="medium"),
                        "Nombre": st.column_config.TextColumn(width="large"),
                        "Programa": st.column_config.TextColumn(width="medium"),
                        "Año": st.column_config.NumberColumn(width="small"),
                        "TipoMateria": st.column_config.TextColumn(width="medium"),
                        "Horas": st.column_config.NumberColumn(width="small"),
                    }
                )
                
                # Descargar
                st.divider()
                csv = df_filtered.to_csv(index=False)
                st.download_button(
                    label="📥 Descargar Cursos (CSV)",
                    data=csv,
                    file_name="cursos.csv",
                    mime="text/csv",
                    key="download_courses"
                )
    
    # ========== TAB 3: FUENTES (CourseSource) ==========
    with tab3:
        st.subheader("Visualizar Fuentes de Cronograma")
        
        with get_session() as session:
            sources = session.query(CourseSource).all()
            
            if not sources:
                st.info("No hay fuentes de cronograma registradas. Importa un cronograma primero.")
            else:
                # Preparar datos
                df_sources = pd.DataFrame([{
                    "ID": s.id,
                    "MateriaID": s.course.materia_id if s.course else "-",
                    "Materia": s.course.nombre if s.course else "-",
                    "Módulo": s.modulo,
                    "SolapaFuente": s.solapa_fuente,
                    "Profesor1": s.profesor_1 or "-",
                    "Profesor2": s.profesor_2 or "-",
                    "Profesor3": s.profesor_3 or "-",
                    "Inicio": s.inicio,
                    "Final": s.final,
                    "Día": s.dia or "-",
                    "Horario": s.horario or "-",
                    "Formato": s.formato or "-",
                    "Orientación": s.orientacion or "-",
                    "Comentarios": s.comentarios or "-",
                    "Estado": s.estado,
                    "Creado": format_date(s.creado_en),
                    "Actualizado": format_date(s.actualizado_en)
                } for s in sources])
                
                # Filtros
                st.subheader("Filtros")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    solapas = ["Todas"] + sorted([s for s in df_sources["SolapaFuente"].unique() if s and s != "-"])
                    selected_solapa = st.selectbox("Solapa Fuente", solapas, key="filter_solapa")
                
                with col2:
                    modulos = ["Todos"] + sorted([m for m in df_sources["Módulo"].unique() if m and m != "-"])
                    selected_modulo = st.selectbox("Módulo", modulos, key="filter_modulo")
                
                with col3:
                    formatos = ["Todos los"] + sorted([f for f in df_sources["Formato"].unique() if f and f != "-"])
                    selected_formato = st.selectbox("Formato", formatos, key="filter_formato")
                
                # Aplicar filtros
                df_filtered = df_sources.copy()
                
                if selected_solapa != "Todas":
                    df_filtered = df_filtered[df_filtered["SolapaFuente"] == selected_solapa]
                
                if selected_modulo != "Todos":
                    df_filtered = df_filtered[df_filtered["Módulo"] == selected_modulo]
                
                if selected_formato != "Todos los":
                    df_filtered = df_filtered[df_filtered["Formato"] == selected_formato]
                
                # Mostrar tabla
                st.divider()
                st.write(f"**Fuentes encontradas: {len(df_filtered)} de {len(df_sources)}**")
                
                st.dataframe(
                    df_filtered,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "ID": st.column_config.NumberColumn(width="small"),
                        "MateriaID": st.column_config.TextColumn(width="medium"),
                        "Materia": st.column_config.TextColumn(width="large"),
                        "Módulo": st.column_config.TextColumn(width="medium"),
                        "SolapaFuente": st.column_config.TextColumn(width="medium"),
                        "Inicio": st.column_config.DateColumn(width="small"),
                        "Final": st.column_config.DateColumn(width="small"),
                    }
                )
                
                # Descargar
                st.divider()
                
                col1, col2 = st.columns(2)
                
                with col1:
                    csv = df_filtered.to_csv(index=False)
                    st.download_button(
                        label="📥 Descargar Fuentes (CSV)",
                        data=csv,
                        file_name="course_sources.csv",
                        mime="text/csv",
                        key="download_sources"
                    )
                
                with col2:
                    # Opción de exportar Excel completo
                    if st.button("📊 Exportar a Excel", use_container_width=True, key="export_excel"):
                        with st.spinner("Generando Excel..."):
                            try:
                                # Crear archivo Excel con múltiples hojas
                                output = BytesIO()
                                
                                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                                    # Hoja de cursos
                                    with get_session() as session:
                                        courses = session.query(Course).all()
                                        df_all_courses = pd.DataFrame([{
                                            "MateriaID": c.materia_id,
                                            "MateriaKey": c.materia_key,
                                            "Nombre": c.nombre,
                                            "Programa": c.programa or "",
                                            "Año": c.ano or "",
                                            "TipoMateria": c.tipo_materia or "",
                                            "Horas": c.horas or "",
                                            "Estado": c.estado
                                        } for c in courses])
                                        
                                        df_all_courses.to_excel(
                                            writer,
                                            sheet_name="Cursos",
                                            index=False
                                        )
                                        
                                        # Hoja de fuentes
                                        sources = session.query(CourseSource).all()
                                        df_all_sources = pd.DataFrame([{
                                            "MateriaID": s.course.materia_id if s.course else "",
                                            "Materia": s.course.nombre if s.course else "",
                                            "Módulo": s.modulo,
                                            "SolapaFuente": s.solapa_fuente,
                                            "Profesor1": s.profesor_1 or "",
                                            "Profesor2": s.profesor_2 or "",
                                            "Profesor3": s.profesor_3 or "",
                                            "Inicio": s.inicio,
                                            "Final": s.final,
                                            "Día": s.dia or "",
                                            "Horario": s.horario or "",
                                            "Formato": s.formato or "",
                                            "Orientación": s.orientacion or "",
                                            "Comentarios": s.comentarios or ""
                                        } for s in sources])
                                        
                                        df_all_sources.to_excel(
                                            writer,
                                            sheet_name="Fuentes",
                                            index=False
                                        )
                                
                                # Descargar
                                output.seek(0)
                                st.download_button(
                                    label="💾 Descargar Cronograma Completo",
                                    data=output.getvalue(),
                                    file_name="cronograma_completo.xlsx",
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    key="download_complete"
                                )
                                
                                st.success("✅ Excel generado correctamente")
                            
                            except Exception as e:
                                st.error(f"Error al exportar: {str(e)}")

if __name__ == "__main__":
    run()
