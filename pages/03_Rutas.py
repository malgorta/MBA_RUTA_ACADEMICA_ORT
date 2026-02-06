import streamlit as st
from datetime import date, datetime
import pandas as pd
from lib.db import get_session
from lib.models import Estudiante, Course, CourseSource, StudentPlanItem, PlanVersion
from lib.metrics import check_electives_count, compute_orientation_counts, get_student_risk_report
from lib.validators import check_student_plan_coherence, check_orientation_rule
from lib.utils import get_logger

logger = get_logger(__name__)


def _append_changelog(text: str):
    ts = datetime.utcnow().isoformat()
    line = f"[{ts}] {text}\n"
    try:
        with open('ChangeLog.md', 'a', encoding='utf-8') as f:
            f.write(line)
    except Exception as e:
        logger.error(f"No se pudo escribir ChangeLog: {e}")


def run():
    st.title("📚 Gestión de Planes y Versiones (Rutas)")

    with get_session() as session:
        estudiantes = session.query(Estudiante).order_by(Estudiante.nombre).all()

    if not estudiantes:
        st.info("No hay estudiantes registrados.")
        return

    est_map = {f"{e.nombre} ({e.documento})": e.id for e in estudiantes}
    sel = st.selectbox("Seleccionar Estudiante", list(est_map.keys()))
    estudiante_id = est_map.get(sel)

    if not estudiante_id:
        return

    # Cargar versión vigente (vigente_hasta is NULL)
    with get_session() as session:
        current_version = session.query(PlanVersion).filter(
            PlanVersion.estudiante_id == estudiante_id,
            PlanVersion.vigente_hasta == None
        ).order_by(PlanVersion.creado_en.desc()).first()

    col1, col2, col3 = st.columns([2, 2, 1])

    with col1:
        if st.button("➕ Crear nueva versión"):
            today = date.today()
            with get_session() as session:
                # Cerrar versión abierta si existe
                abierta = session.query(PlanVersion).filter(
                    PlanVersion.estudiante_id == estudiante_id,
                    PlanVersion.vigente_hasta == None
                ).all()
                for a in abierta:
                    a.vigente_hasta = today
                    a.estado = 'cerrada'
                nueva = PlanVersion(
                    estudiante_id=estudiante_id,
                    nombre=f"Versión {today.isoformat()}",
                    vigente_desde=today,
                    estado='abierta'
                )
                session.add(nueva)
                session.commit()
                _append_changelog(f"Estudiante {estudiante_id}: creada nueva PlanVersion {nueva.id}")
            st.success("Nueva versión creada")
            st.experimental_rerun()

    with col2:
        if current_version:
            if st.button("🔒 Cerrar versión vigente"):
                with get_session() as session:
                    pv = session.query(PlanVersion).get(current_version.id)
                    pv.vigente_hasta = date.today()
                    pv.estado = 'cerrada'
                    session.commit()
                    _append_changelog(f"Estudiante {estudiante_id}: cerrada PlanVersion {pv.id}")
                st.success("Versión cerrada")
                st.experimental_rerun()
        else:
            st.info("No hay versión vigente. Crea una nueva versión.")

    with get_session() as session:
        # Filtros para buscar materias
        programas = [p[0] for p in session.query(Course.programa).distinct().all() if p[0]]
        anos = [a[0] for a in session.query(Course.ano).distinct().order_by(Course.ano).all() if a[0]]
        tipos = [t[0] for t in session.query(Course.tipo_materia).distinct().all() if t[0]]
        orientaciones = [o[0] for o in session.query(CourseSource.orientacion).distinct().all() if o[0]]

    st.markdown("**Agregar materias al plan (filtros)**")
    with st.form("add_course_form"):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            programa = st.selectbox("Programa", [""] + programas)
        with c2:
            ano = st.selectbox("Año (materia)", [""] + [str(a) for a in anos])
        with c3:
            orient = st.selectbox("Orientación", [""] + orientaciones)
        with c4:
            tipo = st.selectbox("Tipo materia", [""] + tipos)

        nombre_buscar = st.text_input("Buscar por nombre")
        es_backup = st.checkbox("Agregar como backup")
        prioridad = st.number_input("Prioridad (mayor = más prioridad)", value=0, step=1)

        submitted = st.form_submit_button("Buscar materias")

    results = []
    if submitted:
        with get_session() as session:
            q = session.query(Course).filter(Course.estado == 'activo')
            if programa:
                q = q.filter(Course.programa == programa)
            if ano:
                try:
                    q = q.filter(Course.ano == int(ano))
                except:
                    pass
            if tipo:
                q = q.filter(Course.tipo_materia == tipo)
            if nombre_buscar:
                q = q.filter(Course.nombre.ilike(f"%{nombre_buscar}%"))
            courses = q.limit(200).all()

        if courses:
            for c in courses:
                # obtener orientaciones de fuentes
                with get_session() as session:
                    sources = session.query(CourseSource).filter(CourseSource.course_id == c.id).all()
                orient_vals = ", ".join([s.orientacion for s in sources if s.orientacion])
                results.append({
                    "id": c.id,
                    "nombre": c.nombre,
                    "programa": c.programa or "-",
                    "ano": c.ano or "-",
                    "tipo": c.tipo_materia or "-",
                    "orientaciones": orient_vals
                })

            df = pd.DataFrame(results)
            st.dataframe(df, use_container_width=True)

            for row in results:
                key = f"add_{row['id']}"
                if st.button(f"Agregar: {row['nombre']}", key=key):
                    if not current_version:
                        st.error("No hay versión vigente. Crea una nueva versión primero.")
                    else:
                        with get_session() as session:
                            item = StudentPlanItem(
                                estudiante_id=estudiante_id,
                                course_id=row['id'],
                                ano=int(row['ano']) if isinstance(row['ano'], int) or row['ano'].isdigit() else date.today().year,
                                estado='PLANNED',
                                prioridad=int(prioridad),
                                es_backup=bool(es_backup),
                                plan_version_id=current_version.id
                            )
                            session.add(item)
                            session.commit()
                            _append_changelog(f"Estudiante {estudiante_id}: agregado Course {row['id']} a PlanVersion {current_version.id}")
                        st.success("Materia agregada al plan")
                        st.experimental_rerun()
        else:
            st.info("No se encontraron materias con esos filtros")

    st.markdown("---")

    st.subheader("Plan vigente")
    if current_version:
        with get_session() as session:
            items = session.query(StudentPlanItem).filter(
                StudentPlanItem.plan_version_id == current_version.id
            ).all()

        if items:
            # Mostrar items con acciones de Editar / Eliminar
            items_sorted = sorted(items, key=lambda x: x.prioridad or 0, reverse=True)
            for it in items_sorted:
                cols = st.columns([4, 1, 1, 1, 1])
                with cols[0]:
                    st.markdown(f"**{it.course.nombre if it.course else 'ID '+str(it.course_id)}**  ")
                    st.text(f"Programa: {it.course.programa if it.course else '-'}  | Año: {it.ano}  | Tipo: {it.course.tipo_materia if it.course else '-'}")
                    st.caption(f"Prioridad: {it.prioridad}  | Backup: {it.es_backup}  | Estado: {it.estado}")

                # Editar
                with cols[1]:
                    if st.button("Editar", key=f"edit_{it.id}"):
                        with st.form(f"edit_form_{it.id}"):
                            new_prioridad = st.number_input("Prioridad", value=int(it.prioridad or 0), step=1)
                            new_backup = st.checkbox("Es backup", value=bool(it.es_backup))
                            new_ano = st.number_input("Año", value=int(it.ano or date.today().year), step=1)
                            new_estado = st.selectbox("Estado", ["PLANNED", "COMPLETED", "CANCELLED"], index=["PLANNED", "COMPLETED", "CANCELLED"].index(it.estado) if it.estado in ["PLANNED","COMPLETED","CANCELLED"] else 0)
                            submitted_edit = st.form_submit_button("Guardar cambios")
                            if submitted_edit:
                                with get_session() as session:
                                    item_db = session.query(StudentPlanItem).get(it.id)
                                    if item_db:
                                        item_db.prioridad = int(new_prioridad)
                                        item_db.es_backup = bool(new_backup)
                                        item_db.ano = int(new_ano)
                                        item_db.estado = new_estado
                                        session.commit()
                                        _append_changelog(f"Estudiante {estudiante_id}: editado StudentPlanItem {it.id} (prioridad={new_prioridad}, backup={new_backup}, ano={new_ano}, estado={new_estado})")
                                        st.success("Cambios guardados")
                                        st.experimental_rerun()

                # Mover a backup / restore quick toggle
                with cols[2]:
                    if st.button("Toggle Backup", key=f"toggle_{it.id}"):
                        with get_session() as session:
                            item_db = session.query(StudentPlanItem).get(it.id)
                            if item_db:
                                item_db.es_backup = not bool(item_db.es_backup)
                                session.commit()
                                _append_changelog(f"Estudiante {estudiante_id}: toggle backup StudentPlanItem {it.id} -> {item_db.es_backup}")
                                st.experimental_rerun()

                # Eliminar
                with cols[3]:
                    if st.button("Eliminar", key=f"del_{it.id}"):
                        if st.confirm(f"Confirma eliminar item {it.id} - {it.course.nombre if it.course else it.course_id}?"):
                            with get_session() as session:
                                item_db = session.query(StudentPlanItem).get(it.id)
                                if item_db:
                                    session.delete(item_db)
                                    session.commit()
                                    _append_changelog(f"Estudiante {estudiante_id}: eliminado StudentPlanItem {it.id}")
                                    st.success("Item eliminado")
                                    st.experimental_rerun()

                # Espacio
                with cols[4]:
                    st.write("")

            # Validaciones y métricas
            electivas = check_electives_count(estudiante_id)
            orient = check_orientation_rule(estudiante_id)
            coherencia = check_student_plan_coherence(estudiante_id)

            if electivas.get('electivas_planeadas_o_completadas', 0) < 8:
                st.warning(f"El plan tiene {electivas.get('electivas_planeadas_o_completadas',0)} electivas planeadas/completadas (objetivo 8)")

            if not orient.get('cumple_regla', False):
                st.warning(f"No alcanza 5 en una orientación: máximo {orient.get('max_electivas',0)}")

            if not coherencia.get('es_valido', True):
                st.error(f"Inconsistencias en plan: {len(coherencia.get('errores',[]))} errores detectados")

        else:
            st.info("La versión vigente no tiene materias agregadas.")
    else:
        st.info("No hay versión vigente para este estudiante.")

    st.markdown("---")
    st.subheader("Historial de versiones")
    with get_session() as session:
        versions = session.query(PlanVersion).filter(PlanVersion.estudiante_id == estudiante_id).order_by(PlanVersion.creado_en.desc()).all()

    if versions:
        dfv = pd.DataFrame([{
            "ID": v.id,
            "Nombre": v.nombre,
            "Desde": v.vigente_desde,
            "Hasta": v.vigente_hasta or "(vigente)",
            "Estado": v.estado
        } for v in versions])
        st.dataframe(dfv, use_container_width=True)
    else:
        st.info("No hay versiones previas")
