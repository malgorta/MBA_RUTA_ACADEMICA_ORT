import streamlit as st
import pandas as pd
from lib.db import get_session
from lib.models import Estudiante, Ruta
from lib.validators import EstudianteSchema
from lib.io_excel import exportar_excel, importar_excel
from lib.utils import get_logger
from pydantic import ValidationError

logger = get_logger(__name__)

def run():
    st.title("👥 Gestión de Estudiantes")
    
    tab1, tab2, tab3 = st.tabs(["Listar", "Crear", "Importar/Exportar"])
    
    with tab1:
        with get_session() as session:
            estudiantes = session.query(Estudiante).all()
        
        if estudiantes:
            df = pd.DataFrame([{
                "ID": e.id,
                "Documento": e.documento,
                "Nombre": e.nombre,
                "Email": e.email or "-",
                "Teléfono": e.telefono or "-",
                "Ruta": e.ruta.nombre if e.ruta else "-",
                "Estado": e.estado
            } for e in estudiantes])
            
            st.dataframe(df, use_container_width=True)
            
            csv = df.to_csv(index=False)
            st.download_button(
                label="📥 Descargar CSV",
                data=csv,
                file_name="estudiantes.csv",
                mime="text/csv"
            )
        else:
            st.info("No hay estudiantes registrados")
    
    with tab2:
        st.subheader("Crear Nuevo Estudiante")
        
        col1, col2 = st.columns(2)
        with col1:
            documento = st.text_input("Documento *", placeholder="ej: 12345678")
        with col2:
            nombre = st.text_input("Nombre Completo *", placeholder="ej: Juan Pérez")
        
        col3, col4 = st.columns(2)
        with col3:
            email = st.text_input("Email", placeholder="Opcional")
        with col4:
            telefono = st.text_input("Teléfono", placeholder="Opcional")
        
        with get_session() as session:
            rutas = session.query(Ruta).filter(Ruta.estado == "activo").all()
        
        ruta_id = None
        if rutas:
            ruta_nombres = {r.nombre: r.id for r in rutas}
            ruta_seleccionada = st.selectbox("Ruta", list(ruta_nombres.keys()), index=None)
            if ruta_seleccionada:
                ruta_id = ruta_nombres[ruta_seleccionada]
        
        if st.button("✨ Crear Estudiante", type="primary"):
            try:
                schema = EstudianteSchema(
                    documento=documento,
                    nombre=nombre,
                    email=email or None,
                    telefono=telefono or None,
                    ruta_id=ruta_id
                )
                
                with get_session() as session:
                    nuevo = Estudiante(**schema.model_dump())
                    session.add(nuevo)
                    session.commit()
                    logger.info(f"Estudiante creado: {nuevo.documento}")
                
                st.success("✅ Estudiante creado exitosamente")
                st.rerun()
            
            except ValidationError as e:
                st.error(f"❌ Error de validación: {e.errors()[0]['msg']}")
            except Exception as e:
                logger.error(f"Error creando estudiante: {str(e)}")
                st.error(f"❌ Error: {str(e)}")
    
    with tab3:
        st.subheader("Importar/Exportar Estudiantes")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.caption("📤 Exportar a Excel")
            if st.button("Descargar Estudiantes (Excel)", key="export_est"):
                try:
                    buffer = exportar_excel("estudiantes")
                    st.download_button(
                        label="Descargar",
                        data=buffer,
                        file_name="estudiantes.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                except Exception as e:
                    st.error(f"❌ Error en exportación: {str(e)}")
        
        with col2:
            st.caption("📥 Importar desde Excel")
            archivo = st.file_uploader("Selecciona archivo Excel", type=["xlsx", "xls"], key="import_est")
            if archivo and st.button("Importar", key="import_btn_est"):
                try:
                    exito, msg = importar_excel(archivo, "estudiantes")
                    if exito:
                        st.success(f"✅ {msg}")
                        st.rerun()
                    else:
                        st.error(f"❌ {msg}")
                except Exception as e:
                    logger.error(f"Error importando: {str(e)}")
                    st.error(f"❌ Error: {str(e)}")
