import streamlit as st
import pandas as pd
from datetime import datetime, date
from lib.db import get_session
from lib.models import Cronograma
from lib.validators import CronogramaSchema
from lib.utils import get_logger, format_date
from pydantic import ValidationError

logger = get_logger(__name__)

def run():
    st.title("📅 Gestión de Cronogramas")
    
    tab1, tab2 = st.tabs(["Listar", "Crear"])
    
    with tab1:
        with get_session() as session:
            cronogramas = session.query(Cronograma).all()
        
        if cronogramas:
            df = pd.DataFrame([{
                "ID": c.id,
                "Nombre": c.nombre,
                "Descripción": c.descripcion or "-",
                "Inicio": format_date(c.fecha_inicio),
                "Fin": format_date(c.fecha_fin),
                "Estado": c.estado,
                "Creado": c.creado_en.strftime("%Y-%m-%d") if c.creado_en else "-"
            } for c in cronogramas])
            
            st.dataframe(df, use_container_width=True)
            
            csv = df.to_csv(index=False)
            st.download_button(
                label="📥 Descargar CSV",
                data=csv,
                file_name="cronogramas.csv",
                mime="text/csv"
            )
        else:
            st.info("No hay cronogramas registrados")
    
    with tab2:
        st.subheader("Crear Nuevo Cronograma")
        
        col1, col2 = st.columns(2)
        with col1:
            nombre = st.text_input("Nombre *", placeholder="ej: MBA 2024-I")
        with col2:
            descripcion = st.text_area("Descripción", placeholder="Opcional")
        
        col3, col4 = st.columns(2)
        with col3:
            fecha_inicio = st.date_input("Fecha Inicio *")
        with col4:
            fecha_fin = st.date_input("Fecha Fin *")
        
        if st.button("✨ Crear Cronograma", type="primary"):
            try:
                schema = CronogramaSchema(
                    nombre=nombre,
                    descripcion=descripcion,
                    fecha_inicio=fecha_inicio,
                    fecha_fin=fecha_fin
                )
                
                with get_session() as session:
                    nuevo = Cronograma(
                        nombre=schema.nombre,
                        descripcion=schema.descripcion,
                        fecha_inicio=schema.fecha_inicio,
                        fecha_fin=schema.fecha_fin
                    )
                    session.add(nuevo)
                    session.commit()
                    logger.info(f"Cronograma creado: {nuevo.nombre}")
                
                st.success("✅ Cronograma creado exitosamente")
                st.rerun()
            
            except ValidationError as e:
                st.error(f"❌ Error de validación: {e.errors()[0]['msg']}")
            except Exception as e:
                logger.error(f"Error creando cronograma: {str(e)}")
                st.error(f"❌ Error: {str(e)}")
