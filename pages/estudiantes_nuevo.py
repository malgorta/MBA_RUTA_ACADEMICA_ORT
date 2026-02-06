import streamlit as st
import pandas as pd
from datetime import datetime, date
from io import BytesIO
from lib.db import get_session
from lib.models import Estudiante, Meeting, Ruta
from lib.utils import get_logger, format_date
import tempfile
import os

logger = get_logger(__name__)

def run():
    st.set_page_config(page_title="Estudiantes", layout="wide")
    st.title("👥 Gestión de Estudiantes")
    
    tab1, tab2, tab3, tab4 = st.tabs(["Listar", "Crear/Editar", "Importar", "Reuniones"])
    
    # ========== TAB 1: LISTAR ==========
    with tab1:
        st.subheader("Listado de Estudiantes")
        
        with get_session() as session:
            estudiantes = session.query(Estudiante).all()
            
            if not estudiantes:
                st.info("No hay estudiantes registrados")
            else:
                # Preparar datos con información de reuniones
                df_estudiantes = pd.DataFrame()
                datos = []
                
                for e in estudiantes:
                    # Obtener última reunión
                    ultima_reunion = None
                    orientacion_objetivo = None
                    
                    if e.meetings:
                        ultima_reunion = max(e.meetings, key=lambda m: m.fecha) if e.meetings else None
                        if ultima_reunion:
                            orientacion_objetivo = ultima_reunion.orientacion_objetivo
                    
                    datos.append({
                        "ID": e.id,
                        "Documento": e.documento,
                        "Nombre": e.nombre,
                        "Email": e.email or "-",
                        "Teléfono": e.telefono or "-",
                        "Ruta": e.ruta.nombre if e.ruta else "-",
                        "Estado": e.estado,
                        "Tiene Reunión": "✓ Sí" if ultima_reunion else "✗ No",
                        "Orientación Objetivo": orientacion_objetivo or "-",
                        "Creado": format_date(e.creado_en),
                    })
                
                df_estudiantes = pd.DataFrame(datos)
                
                # Filtros
                st.subheader("Filtros")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    estados = ["Todos"] + sorted(df_estudiantes["Estado"].unique().tolist())
                    selected_estado = st.selectbox("Estado", estados, key="filter_estado")
                
                with col2:
                    tiene_reunion_opts = ["Todos"] + df_estudiantes["Tiene Reunión"].unique().tolist()
                    selected_reunion = st.selectbox("Tiene Reunión", tiene_reunion_opts, key="filter_reunion")
                
                with col3:
                    rutas = ["Todos"] + [r for r in df_estudiantes["Ruta"].unique() if r and r != "-"]
                    selected_ruta = st.selectbox("Ruta", rutas, key="filter_ruta")
                
                # Aplicar filtros
                df_filtered = df_estudiantes.copy()
                
                if selected_estado != "Todos":
                    df_filtered = df_filtered[df_filtered["Estado"] == selected_estado]
                
                if selected_reunion != "Todos":
                    df_filtered = df_filtered[df_filtered["Tiene Reunión"] == selected_reunion]
                
                if selected_ruta != "Todos":
                    df_filtered = df_filtered[df_filtered["Ruta"] == selected_ruta]
                
                # Mostrar tabla
                st.divider()
                st.write(f"**Estudiantes encontrados: {len(df_filtered)} de {len(df_estudiantes)}**")
                
                st.dataframe(
                    df_filtered,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "ID": st.column_config.NumberColumn(width="small"),
                        "Documento": st.column_config.TextColumn(width="medium"),
                        "Nombre": st.column_config.TextColumn(width="large"),
                        "Email": st.column_config.TextColumn(width="medium"),
                        "Teléfono": st.column_config.TextColumn(width="small"),
                        "Ruta": st.column_config.TextColumn(width="medium"),
                    }
                )
                
                # Descargar
                st.divider()
                csv = df_filtered.to_csv(index=False)
                st.download_button(
                    label="📥 Descargar Listado (CSV)",
                    data=csv,
                    file_name="estudiantes.csv",
                    mime="text/csv",
                    key="download_estudiantes"
                )
    
    # ========== TAB 2: CREAR/EDITAR ==========
    with tab2:
        st.subheader("Crear o Editar Estudiante")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            with get_session() as session:
                estudiantes = session.query(Estudiante).all()
                
                editar = len(estudiantes) > 0 and st.checkbox("Editar estudiante existente")
                
                if editar:
                    opciones = {f"{e.nombre} ({e.documento})": e.id for e in estudiantes}
                    selected = st.selectbox("Selecciona estudiante", list(opciones.keys()), key="select_edit")
                    
                    if selected:
                        est_id = opciones[selected]
                        estudiante = session.query(Estudiante).filter_by(id=est_id).first()
                        
                        documento = st.text_input("Documento", value=estudiante.documento)
                        nombre = st.text_input("Nombre", value=estudiante.nombre)
                        email = st.text_input("Email", value=estudiante.email or "")
                        telefono = st.text_input("Teléfono", value=estudiante.telefono or "")
                        
                        rutas = session.query(Ruta).all()
                        ruta_options = {r.nombre: r.id for r in rutas}
                        ruta_id = st.selectbox(
                            "Ruta",
                            list(ruta_options.keys()),
                            index=list(ruta_options.values()).index(estudiante.ruta_id) if estudiante.ruta_id else 0
                        )
                        
                        estado = st.selectbox("Estado", ["activo", "inactivo"], 
                                            index=0 if estudiante.estado == "activo" else 1)
                        
                        if st.button("💾 Actualizar Estudiante", use_container_width=True):
                            try:
                                estudiante.documento = documento
                                estudiante.nombre = nombre
                                estudiante.email = email or None
                                estudiante.telefono = telefono or None
                                estudiante.ruta_id = ruta_options[ruta_id]
                                estudiante.estado = estado
                                estudiante.actualizado_en = datetime.utcnow()
                                
                                session.commit()
                                st.success("✅ Estudiante actualizado correctamente")
                                logger.info(f"Estudiante actualizado: {nombre} ({documento})")
                            except Exception as e:
                                st.error(f"❌ Error al actualizar: {str(e)}")
                                logger.error(f"Error al actualizar estudiante: {str(e)}")
                else:
                    # Crear nuevo
                    st.write("**Crear nuevo estudiante**")
                    
                    documento = st.text_input("Documento *", placeholder="Ej: 12345678")
                    nombre = st.text_input("Nombre Completo *", placeholder="Ej: Juan Pérez García")
                    email = st.text_input("Email", placeholder="juan@example.com")
                    telefono = st.text_input("Teléfono", placeholder="+34 600 000 000")
                    
                    rutas = session.query(Ruta).all()
                    ruta_options = {r.nombre: r.id for r in rutas}
                    ruta_id = st.selectbox("Ruta", list(ruta_options.keys()) or ["Sin rutas"])
                    
                    if st.button("➕ Crear Estudiante", use_container_width=True):
                        if not documento or not nombre:
                            st.error("⚠️ Documento y Nombre son obligatorios")
                        else:
                            try:
                                # Verificar si existe
                                existe = session.query(Estudiante).filter_by(documento=documento).first()
                                if existe:
                                    st.error("❌ Ya existe un estudiante con este documento")
                                else:
                                    nuevo = Estudiante(
                                        documento=documento,
                                        nombre=nombre,
                                        email=email or None,
                                        telefono=telefono or None,
                                        ruta_id=ruta_options.get(ruta_id),
                                        estado="activo"
                                    )
                                    session.add(nuevo)
                                    session.commit()
                                    st.success("✅ Estudiante creado correctamente")
                                    logger.info(f"Nuevo estudiante creado: {nombre} ({documento})")
                            except Exception as e:
                                st.error(f"❌ Error al crear: {str(e)}")
                                logger.error(f"Error al crear estudiante: {str(e)}")
    
    # ========== TAB 3: IMPORTAR ==========
    with tab3:
        st.subheader("Importar Estudiantes desde Excel/CSV")
        
        uploaded_file = st.file_uploader(
            "Selecciona archivo Excel o CSV",
            type=["xlsx", "xls", "csv"],
            help="El archivo debe contener columnas con datos de estudiantes"
        )
        
        if uploaded_file:
            try:
                # Leer archivo
                if uploaded_file.name.endswith('.csv'):
                    df = pd.read_csv(uploaded_file)
                else:
                    df = pd.read_excel(uploaded_file)
                
                st.success(f"✓ Archivo cargado: {len(df)} filas")
                
                # Mostrar columnas disponibles
                st.subheader("Mapeo de Columnas")
                st.info("Mapea las columnas de tu archivo a los campos requeridos")
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    col_documento = st.selectbox(
                        "Documento",
                        [""] + df.columns.tolist(),
                        key="map_documento"
                    )
                
                with col2:
                    col_nombre = st.selectbox(
                        "Nombre",
                        [""] + df.columns.tolist(),
                        key="map_nombre"
                    )
                
                with col3:
                    col_email = st.selectbox(
                        "Email",
                        [""] + df.columns.tolist(),
                        key="map_email"
                    )
                
                with col4:
                    col_telefono = st.selectbox(
                        "Teléfono",
                        [""] + df.columns.tolist(),
                        key="map_telefono"
                    )
                
                # Vista previa
                st.subheader("Vista Previa")
                preview_cols = [c for c in [col_documento, col_nombre, col_email, col_telefono] if c]
                if preview_cols:
                    st.dataframe(df[preview_cols].head(5), use_container_width=True, hide_index=True)
                
                # Importar
                if st.button("🚀 Importar Estudiantes", use_container_width=True):
                    if not col_documento or not col_nombre:
                        st.error("⚠️ Documento y Nombre son obligatorios")
                    else:
                        with st.spinner("Importando estudiantes..."):
                            with get_session() as session:
                                creados = 0
                                duplicados = 0
                                errores = []
                                
                                for idx, row in df.iterrows():
                                    try:
                                        documento = str(row[col_documento]).strip()
                                        nombre = str(row[col_nombre]).strip()
                                        email = str(row[col_email]).strip() if col_email else None
                                        telefono = str(row[col_telefono]).strip() if col_telefono else None
                                        
                                        if not documento or not nombre:
                                            errores.append(f"Fila {idx+2}: Documento o nombre vacío")
                                            continue
                                        
                                        existe = session.query(Estudiante).filter_by(documento=documento).first()
                                        
                                        if existe:
                                            duplicados += 1
                                        else:
                                            nuevo = Estudiante(
                                                documento=documento,
                                                nombre=nombre,
                                                email=email if email and email != "None" else None,
                                                telefono=telefono if telefono and telefono != "None" else None,
                                                estado="activo"
                                            )
                                            session.add(nuevo)
                                            creados += 1
                                    
                                    except Exception as e:
                                        errores.append(f"Fila {idx+2}: {str(e)}")
                                
                                session.commit()
                        
                        st.success(f"✅ Importación completada")
                        col1, col2, col3 = st.columns(3)
                        col1.metric("Creados", creados)
                        col2.metric("Duplicados", duplicados)
                        col3.metric("Errores", len(errores))
                        
                        if errores:
                            with st.expander("Ver errores"):
                                for error in errores[:10]:
                                    st.error(error, icon="❌")
                                if len(errores) > 10:
                                    st.info(f"... y {len(errores) - 10} errores más")
            
            except Exception as e:
                st.error(f"❌ Error al leer archivo: {str(e)}")
    
    # ========== TAB 4: REUNIONES ==========
    with tab4:
        st.subheader("Gestión de Reuniones de Estudiantes")
        
        with get_session() as session:
            estudiantes = session.query(Estudiante).all()
            
            if not estudiantes:
                st.info("No hay estudiantes registrados")
            else:
                # Seleccionar estudiante
                opciones = {f"{e.nombre} ({e.documento})": e.id for e in estudiantes}
                selected = st.selectbox("Selecciona estudiante", list(opciones.keys()), key="select_student_meeting")
                
                if selected:
                    est_id = opciones[selected]
                    estudiante = session.query(Estudiante).filter_by(id=est_id).first()
                    
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.write(f"**Estudiante:** {estudiante.nombre}")
                        st.write(f"**Documento:** {estudiante.documento}")
                    
                    with col2:
                        if st.button("➕ Nueva Reunión", use_container_width=True):
                            st.session_state.crear_reunion = True
                    
                    st.divider()
                    
                    # Crear nueva reunión
                    if st.session_state.get("crear_reunion"):
                        st.subheader("Crear Nueva Reunión")
                        
                        fecha = st.date_input("Fecha de Reunión *", value=date.today())
                        orientacion = st.text_area(
                            "Orientación/Objetivo *",
                            placeholder="Describe el objetivo o orientación de la reunión",
                            height=100
                        )
                        acuerdo = st.text_area(
                            "Acuerdo/Compromisos",
                            placeholder="Acuerdos alcanzados en la reunión",
                            height=100
                        )
                        notas = st.text_area(
                            "Notas Adicionales",
                            placeholder="Notas o comentarios adicionales",
                            height=80
                        )
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            if st.button("💾 Guardar Reunión", use_container_width=True):
                                if not fecha or not orientacion:
                                    st.error("⚠️ Fecha y Orientación/Objetivo son obligatorios")
                                else:
                                    try:
                                        nueva_reunion = Meeting(
                                            estudiante_id=est_id,
                                            fecha=fecha,
                                            orientacion_objetivo=orientacion,
                                            acuerdo_texto=acuerdo or None,
                                            notas=notas or None,
                                            estado="completada"
                                        )
                                        session.add(nueva_reunion)
                                        session.commit()
                                        st.success("✅ Reunión guardada correctamente")
                                        st.session_state.crear_reunion = False
                                        logger.info(f"Nueva reunión creada para: {estudiante.nombre}")
                                    except Exception as e:
                                        st.error(f"❌ Error al guardar: {str(e)}")
                        
                        with col2:
                            if st.button("❌ Cancelar", use_container_width=True):
                                st.session_state.crear_reunion = False
                    
                    # Listar reuniones
                    st.subheader("Historial de Reuniones")
                    
                    reuniones = session.query(Meeting).filter_by(estudiante_id=est_id).order_by(Meeting.fecha.desc()).all()
                    
                    if not reuniones:
                        st.info("No hay reuniones registradas para este estudiante")
                    else:
                        for reunion in reuniones:
                            with st.expander(f"📅 {reunion.fecha} - {reunion.orientacion_objetivo[:50]}..."):
                                col1, col2 = st.columns([3, 1])
                                
                                with col1:
                                    st.write(f"**Fecha:** {reunion.fecha}")
                                    st.write(f"**Orientación/Objetivo:**")
                                    st.write(reunion.orientacion_objetivo)
                                    
                                    if reunion.acuerdo_texto:
                                        st.write(f"**Acuerdo:**")
                                        st.write(reunion.acuerdo_texto)
                                    
                                    if reunion.notas:
                                        st.write(f"**Notas:**")
                                        st.write(reunion.notas)
                                    
                                    st.caption(f"Creado: {format_date(reunion.creado_en)}")
                                
                                with col2:
                                    if st.button("✏️ Editar", key=f"edit_{reunion.id}"):
                                        st.session_state[f"edit_reunion_{reunion.id}"] = True
                                    
                                    if st.button("🗑️ Eliminar", key=f"del_{reunion.id}"):
                                        session.delete(reunion)
                                        session.commit()
                                        st.success("Reunión eliminada")
                                        st.rerun()
                                
                                # Editar reunión
                                if st.session_state.get(f"edit_reunion_{reunion.id}"):
                                    st.divider()
                                    fecha_edit = st.date_input("Fecha", value=reunion.fecha, key=f"fecha_edit_{reunion.id}")
                                    orientacion_edit = st.text_area(
                                        "Orientación/Objetivo",
                                        value=reunion.orientacion_objetivo,
                                        key=f"orientacion_edit_{reunion.id}"
                                    )
                                    acuerdo_edit = st.text_area(
                                        "Acuerdo",
                                        value=reunion.acuerdo_texto or "",
                                        key=f"acuerdo_edit_{reunion.id}"
                                    )
                                    notas_edit = st.text_area(
                                        "Notas",
                                        value=reunion.notas or "",
                                        key=f"notas_edit_{reunion.id}"
                                    )
                                    
                                    if st.button("💾 Guardar Cambios", key=f"save_edit_{reunion.id}"):
                                        try:
                                            reunion.fecha = fecha_edit
                                            reunion.orientacion_objetivo = orientacion_edit
                                            reunion.acuerdo_texto = acuerdo_edit or None
                                            reunion.notas = notas_edit or None
                                            reunion.actualizado_en = datetime.utcnow()
                                            session.commit()
                                            st.success("Reunión actualizada")
                                            st.session_state[f"edit_reunion_{reunion.id}"] = False
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"Error: {str(e)}")

if __name__ == "__main__":
    run()
