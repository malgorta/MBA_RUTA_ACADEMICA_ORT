import streamlit as st
import pandas as pd
from lib.db import get_session
from lib.models import Cambio, Estudiante, Ruta
from lib.utils import get_logger

logger = get_logger(__name__)

def run():
    st.title("⚡ Solicitudes de Cambio de Ruta")
    
    tab1, tab2 = st.tabs(["Listar", "Nueva Solicitud"])
    
    with tab1:
        with get_session() as session:
            cambios = session.query(Cambio).all()
        
        if cambios:
            df = pd.DataFrame([{
                "ID": c.id,
                "Estudiante": c.estudiante.nombre if c.estudiante else "-",
                "Ruta Anterior": c.ruta_anterior or "-",
                "Ruta Nueva": c.ruta_nueva,
                "Motivo": c.motivo or "-",
                "Estado": c.estado,
                "Solicitado": c.fecha_solicitud.strftime("%Y-%m-%d") if c.fecha_solicitud else "-"
            } for c in cambios])
            
            st.dataframe(df, use_container_width=True)
            
            col1, col2 = st.columns(2)
            with col1:
                csv = df.to_csv(index=False)
                st.download_button(
                    label="📥 Descargar CSV",
                    data=csv,
                    file_name="cambios.csv",
                    mime="text/csv"
                )
            
            with col2:
                estados = df["Estado"].unique()
                filtro_estado = st.selectbox("Filtrar por Estado", ["Todos"] + list(estados))
                if filtro_estado != "Todos":
                    df_filtrado = df[df["Estado"] == filtro_estado]
                    st.write(f"**{len(df_filtrado)} registros**")
                    st.dataframe(df_filtrado, use_container_width=True)
        else:
            st.info("No hay solicitudes de cambio")
    
    with tab2:
        st.subheader("Solicitar Cambio de Ruta")
        
        with get_session() as session:
            estudiantes = session.query(Estudiante).filter(Estudiante.estado == "activo").all()
            rutas = session.query(Ruta).filter(Ruta.estado == "activo").all()
        
        if not estudiantes:
            st.warning("No hay estudiantes activos")
        elif not rutas:
            st.warning("No hay rutas activas")
        else:
            est_dict = {f"{e.nombre} ({e.documento})": e.id for e in estudiantes}
            ruta_dict = {r.nombre: r.codigo for r in rutas}
            
            est_sel = st.selectbox("Estudiante *", list(est_dict.keys()), index=None)
            estudiante_id = est_dict[est_sel] if est_sel else None
            
            ruta_actual = "-"
            if estudiante_id:
                with get_session() as session:
                    est = session.query(Estudiante).filter_by(id=estudiante_id).first()
                    if est and est.ruta:
                        ruta_actual = est.ruta.nombre
            
            st.info(f"Ruta actual: **{ruta_actual}**")
            
            ruta_nueva_sel = st.selectbox("Ruta Nueva *", list(ruta_dict.keys()), index=None)
            ruta_nueva = ruta_dict[ruta_nueva_sel] if ruta_nueva_sel else None
            
            motivo = st.text_area("Motivo de cambio *", placeholder="Describe el motivo...")
            
            if st.button("✨ Solicitar Cambio", type="primary"):
                if not estudiante_id or not ruta_nueva or not motivo:
                    st.error("❌ Todos los campos son requeridos")
                else:
                    try:
                        with get_session() as session:
                            cambio = Cambio(
                                estudiante_id=estudiante_id,
                                ruta_anterior=ruta_actual,
                                ruta_nueva=ruta_nueva,
                                motivo=motivo,
                                estado="pendiente"
                            )
                            session.add(cambio)
                            session.commit()
                            logger.info(f"Cambio solicitado por estudiante {estudiante_id}")
                        
                        st.success("✅ Solicitud de cambio creada. Estado: Pendiente")
                        st.rerun()
                    
                    except Exception as e:
                        logger.error(f"Error creando cambio: {str(e)}")
                        st.error(f"❌ Error: {str(e)}")
