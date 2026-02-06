import streamlit as st
import pandas as pd
from lib.db import get_session
from lib.models import Inscripcion, Estudiante, Cronograma
from lib.validators import InscripcionSchema
from lib.io_excel import exportar_excel
from lib.utils import get_logger
from pydantic import ValidationError

logger = get_logger(__name__)

def run():
    st.title("📝 Gestión de Inscripciones")
    
    tab1, tab2 = st.tabs(["Listar", "Crear"])
    
    with tab1:
        with get_session() as session:
            inscripciones = session.query(Inscripcion).all()
        
        if inscripciones:
            df = pd.DataFrame([{
                "ID": i.id,
                "Estudiante": i.estudiante.nombre,
                "Documento": i.estudiante.documento,
                "Cronograma": i.estudiante.ruta.cronograma.nombre if i.estudiante.ruta and i.estudiante.ruta.cronograma else "-",
                "Semestre": i.semestre,
                "Estado": i.estado,
                "Promedio": i.calificacion_promedio or "-",
                "Fecha": i.fecha_inscripcion.strftime("%Y-%m-%d") if i.fecha_inscripcion else "-"
            } for i in inscripciones])
            
            col1, col2 = st.columns([3, 1])
            with col1:
                st.dataframe(df, use_container_width=True)
            with col2:
                csv = df.to_csv(index=False)
                st.download_button(
                    label="📥 CSV",
                    data=csv,
                    file_name="inscripciones.csv",
                    mime="text/csv"
                )
        else:
            st.info("No hay inscripciones registradas")
    
    with tab2:
        st.subheader("Crear Nueva Inscripción")
        
        with get_session() as session:
            estudiantes = session.query(Estudiante).filter(Estudiante.estado == "activo").all()
            cronogramas = session.query(Cronograma).filter(Cronograma.estado == "activo").all()
        
        if not estudiantes:
            st.warning("No hay estudiantes activos")
        elif not cronogramas:
            st.warning("No hay cronogramas activos")
        else:
            est_dict = {f"{e.nombre} ({e.documento})": e.id for e in estudiantes}
            crono_dict = {c.nombre: c.id for c in cronogramas}
            
            col1, col2 = st.columns(2)
            with col1:
                est_sel = st.selectbox("Estudiante *", list(est_dict.keys()), index=None)
                estudiante_id = est_dict[est_sel] if est_sel else None
            with col2:
                crono_sel = st.selectbox("Cronograma *", list(crono_dict.keys()), index=None)
                cronograma_id = crono_dict[crono_sel] if crono_sel else None
            
            col3, col4 = st.columns(2)
            with col3:
                semestre = st.number_input("Semestre *", min_value=1, max_value=8, value=1)
            with col4:
                estado = st.selectbox("Estado", ["matriculado", "activo", "suspendido", "graduado"], index=0)
            
            calificacion = st.number_input("Calificación (opcional)", min_value=0.0, max_value=5.0, value=None, step=0.1)
            
            if st.button("✨ Crear Inscripción", type="primary"):
                if not estudiante_id or not cronograma_id:
                    st.error("❌ Debes seleccionar estudiante y cronograma")
                else:
                    try:
                        schema = InscripcionSchema(
                            estudiante_id=estudiante_id,
                            cronograma_id=cronograma_id,
                            semestre=int(semestre)
                        )
                        
                        with get_session() as session:
                            nueva = Inscripcion(
                                **schema.model_dump(),
                                estado=estado,
                                calificacion_promedio=calificacion
                            )
                            session.add(nueva)
                            session.commit()
                            logger.info(f"Inscripción creada para estudiante {estudiante_id}")
                        
                        st.success("✅ Inscripción creada exitosamente")
                        st.rerun()
                    
                    except ValidationError as e:
                        st.error(f"❌ Error de validación: {e.errors()[0]['msg']}")
                    except Exception as e:
                        logger.error(f"Error creando inscripción: {str(e)}")
                        st.error(f"❌ Error: {str(e)}")
