import streamlit as st
import pandas as pd
from lib.metrics import get_kpi_estudiantes, get_kpi_rutas, get_kpi_inscripciones, get_kpi_cambios
from lib.db import get_session
from lib.models import Estudiante, Inscripcion, Ruta
from lib.utils import get_logger

logger = get_logger(__name__)

def run():
    st.title("📊 Reportes y KPIs")
    
    tab1, tab2, tab3 = st.tabs(["KPIs", "Análisis", "Detalle"])
    
    with tab1:
        st.subheader("Indicadores Clave de Desempeño")
        
        kpi_est = get_kpi_estudiantes()
        kpi_insc = get_kpi_inscripciones()
        kpi_camb = get_kpi_cambios()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Estudiantes Activos",
                kpi_est.get("activos", 0),
                f"{kpi_est.get('tasa_activos', 0)}%"
            )
        
        with col2:
            st.metric(
                "Total Inscripciones",
                kpi_insc.get("total_inscripciones", 0),
                f"{kpi_insc.get('tasa_permanencia', 0)}% permanencia"
            )
        
        with col3:
            st.metric(
                "Promedio Calificación",
                f"{kpi_insc.get('promedio_calificacion', 0):.2f}",
                "sobre 5.0"
            )
        
        with col4:
            st.metric(
                "Cambios Pendientes",
                kpi_camb.get("pendientes", 0),
                f"{kpi_camb.get('total', 0)} total"
            )
    
    with tab2:
        st.subheader("Análisis de Distribución")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.caption("📚 Estudiantes por Ruta")
            kpi_rutas = get_kpi_rutas()
            if "distribucion" in kpi_rutas and kpi_rutas["distribucion"]:
                dist_data = kpi_rutas["distribucion"]
                df_dist = pd.DataFrame(list(dist_data.items()), columns=["Ruta", "Cantidad"])
                st.bar_chart(df_dist.set_index("Ruta"), use_container_width=True)
            else:
                st.info("Sin datos")
        
        with col2:
            st.caption("⚡ Estado de Cambios")
            kpi_camb = get_kpi_cambios()
            estado_data = {
                "Pendientes": kpi_camb.get("pendientes", 0),
                "Aprobados": kpi_camb.get("aprobados", 0),
                "Rechazados": kpi_camb.get("rechazados", 0)
            }
            df_estado = pd.DataFrame(list(estado_data.items()), columns=["Estado", "Cantidad"])
            st.bar_chart(df_estado.set_index("Estado"), use_container_width=True)
    
    with tab3:
        st.subheader("Detalles por Estudiante")
        
        with get_session() as session:
            estudiantes = session.query(Estudiante).filter(Estudiante.estado == "activo").all()
        
        if estudiantes:
            est_dict = {e.nombre: e.id for e in estudiantes}
            est_sel = st.selectbox("Selecciona estudiante", list(est_dict.keys()), index=None)
            
            if est_sel:
                with get_session() as session:
                    est = session.query(Estudiante).filter_by(id=est_dict[est_sel]).first()
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Nombre", est.nombre)
                    with col2:
                        st.metric("Documento", est.documento)
                    with col3:
                        st.metric("Ruta", est.ruta.nombre if est.ruta else "-")
                    
                    inscripciones = session.query(Inscripcion).filter_by(estudiante_id=est.id).all()
                    
                    if inscripciones:
                        st.caption("Inscripciones")
                        df_insc = pd.DataFrame([{
                            "Semestre": i.semestre,
                            "Estado": i.estado,
                            "Promedio": i.calificacion_promedio or "-",
                            "Fecha": i.fecha_inscripcion.strftime("%Y-%m-%d") if i.fecha_inscripcion else "-"
                        } for i in inscripciones])
                        st.dataframe(df_insc, use_container_width=True)
        else:
            st.info("No hay estudiantes")
