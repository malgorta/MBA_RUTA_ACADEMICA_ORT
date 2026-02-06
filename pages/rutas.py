import streamlit as st
import pandas as pd
from lib.db import get_session
from lib.models import Ruta, Cronograma
from lib.validators import RutaSchema
from lib.io_excel import exportar_excel, importar_excel
from lib.utils import get_logger
from pydantic import ValidationError

logger = get_logger(__name__)

def run():
    st.title("🛣️ Gestión de Rutas Académicas")
    
    tab1, tab2, tab3 = st.tabs(["Listar", "Crear", "Importar/Exportar"])
    
    with tab1:
        with get_session() as session:
            rutas = session.query(Ruta).all()
        
        if rutas:
            df = pd.DataFrame([{
                "ID": r.id,
                "Código": r.codigo,
                "Nombre": r.nombre,
                "Énfasis": r.enfasis or "-",
                "Semestres": r.semestres,
                "Cronograma": r.cronograma.nombre if r.cronograma else "-",
                "Estado": r.estado
            } for r in rutas])
            
            st.dataframe(df, use_container_width=True)
            
            csv = df.to_csv(index=False)
            st.download_button(
                label="📥 Descargar CSV",
                data=csv,
                file_name="rutas.csv",
                mime="text/csv"
            )
        else:
            st.info("No hay rutas registradas")
    
    with tab2:
        st.subheader("Crear Nueva Ruta")
        
        col1, col2 = st.columns(2)
        with col1:
            codigo = st.text_input("Código *", placeholder="ej: MBA-FIN")
        with col2:
            nombre = st.text_input("Nombre *", placeholder="ej: MBA Finanzas")
        
        with get_session() as session:
            cronogramas = session.query(Cronograma).filter(Cronograma.estado == "activo").all()
        
        cronograma_id = None
        if cronogramas:
            crono_dict = {c.nombre: c.id for c in cronogramas}
            crono_sel = st.selectbox("Cronograma *", list(crono_dict.keys()), index=None)
            if crono_sel:
                cronograma_id = crono_dict[crono_sel]
        else:
            st.warning("No hay cronogramas activos. Crea uno primero.")
        
        col3, col4 = st.columns(2)
        with col3:
            enfasis = st.text_input("Énfasis", placeholder="Opcional")
        with col4:
            semestres = st.number_input("Semestres", min_value=1, max_value=8, value=4)
        
        if st.button("✨ Crear Ruta", type="primary"):
            if not cronograma_id:
                st.error("❌ Debes seleccionar un cronograma")
            else:
                try:
                    schema = RutaSchema(
                        codigo=codigo,
                        nombre=nombre,
                        enfasis=enfasis or None,
                        semestres=int(semestres),
                        cronograma_id=cronograma_id
                    )
                    
                    with get_session() as session:
                        nueva = Ruta(**schema.model_dump())
                        session.add(nueva)
                        session.commit()
                        logger.info(f"Ruta creada: {nueva.codigo}")
                    
                    st.success("✅ Ruta creada exitosamente")
                    st.rerun()
                
                except ValidationError as e:
                    st.error(f"❌ Error de validación: {e.errors()[0]['msg']}")
                except Exception as e:
                    logger.error(f"Error creando ruta: {str(e)}")
                    st.error(f"❌ Error: {str(e)}")
    
    with tab3:
        st.subheader("Importar/Exportar Rutas")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.caption("📤 Exportar a Excel")
            if st.button("Descargar Rutas (Excel)", key="export_rutas"):
                try:
                    buffer = exportar_excel("rutas")
                    st.download_button(
                        label="Descargar",
                        data=buffer,
                        file_name="rutas.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                except Exception as e:
                    st.error(f"❌ Error en exportación: {str(e)}")
        
        with col2:
            st.caption("📥 Importar desde Excel")
            archivo = st.file_uploader("Selecciona archivo Excel", type=["xlsx", "xls"], key="import_rutas")
            if archivo and st.button("Importar", key="import_btn_rutas"):
                try:
                    exito, msg = importar_excel(archivo, "rutas")
                    if exito:
                        st.success(f"✅ {msg}")
                        st.rerun()
                    else:
                        st.error(f"❌ {msg}")
                except Exception as e:
                    logger.error(f"Error importando: {str(e)}")
                    st.error(f"❌ Error: {str(e)}")
