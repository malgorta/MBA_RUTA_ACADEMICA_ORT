import streamlit as st
from lib.db import get_session
from lib.models import Estudiante, PlanVersion, StudentPlanItem, Enrollment, Course
from lib.metrics import check_electives_count, check_orientation_rule
from datetime import date, datetime
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
    st.title("📝 Inscripciones — Reconciliación con Plan")

    with get_session() as session:
        estudiantes = session.query(Estudiante).order_by(Estudiante.nombre).all()

    if not estudiantes:
        st.info("No hay estudiantes registrados")
        return

    est_map = {f"{e.nombre} ({e.documento})": e.id for e in estudiantes}
    sel = st.selectbox("Seleccionar Estudiante", list(est_map.keys()))
    estudiante_id = est_map.get(sel)

    if not estudiante_id:
        return

    with get_session() as session:
        current_version = session.query(PlanVersion).filter(
            PlanVersion.estudiante_id == estudiante_id,
            PlanVersion.vigente_hasta == None
        ).order_by(PlanVersion.creado_en.desc()).first()

        plan_items = []
        if current_version:
            plan_items = session.query(StudentPlanItem).filter(
                StudentPlanItem.plan_version_id == current_version.id
            ).all()

        enrollments = session.query(Enrollment).filter(Enrollment.estudiante_id == estudiante_id).all()

    st.subheader("Plan vigente vs Enrollments reales")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Plan (vigente)**")
        if current_version and plan_items:
            for it in plan_items:
                curso = it.course.nombre if it.course else f"ID {it.course_id}"
                st.write(f"- {curso} | Año: {it.ano} | Tipo: {it.course.tipo_materia if it.course else '-'} | Prioridad: {it.prioridad} | Backup: {it.es_backup}")
        else:
            st.info("No hay plan vigente o no tiene items")

    with col2:
        st.markdown("**Enrollments reales**")
        if enrollments:
            for en in enrollments:
                curso = en.course.nombre if en.course else f"ID {en.course_id}"
                with st.expander(f"{curso} — {en.status}"):
                    st.write(f"Semestre: {en.semestre} | Año: {en.ano} | Nota: {en.nota} | Nota num: {en.nota_numerica}")
                    # Edit form
                    with st.form(f"edit_en_{en.id}"):
                        status = st.selectbox("Status", ["planned","in_progress","completed","dropped"], index=["planned","in_progress","completed","dropped"].index(en.status) if en.status in ["planned","in_progress","completed","dropped"] else 0)
                        nota = st.text_input("Nota (texto)", value=en.nota or "")
                        nota_num = st.number_input("Nota numérica", value=en.nota_numerica if en.nota_numerica is not None else 0.0, format="%.2f")
                        ano = st.number_input("Año", value=en.ano or date.today().year)
                        semestre = st.number_input("Semestre", value=en.semestre or 1, min_value=1, max_value=8)
                        submitted = st.form_submit_button("Guardar cambios")
                        if submitted:
                            with get_session() as session:
                                e = session.query(Enrollment).get(en.id)
                                e.status = status
                                e.nota = nota or None
                                e.nota_numerica = float(nota_num) if nota_num else None
                                e.ano = int(ano)
                                e.semestre = int(semestre)
                                session.commit()
                                _append_changelog(f"Estudiante {estudiante_id}: edit Enrollment {e.id} status={e.status}")
                            st.success("Enrollment actualizado")
                            st.experimental_rerun()

                    if st.button("❌ Eliminar enrollment", key=f"del_en_{en.id}"):
                        if st.confirm("Confirmar eliminación de enrollment?"):
                            with get_session() as session:
                                e = session.query(Enrollment).get(en.id)
                                session.delete(e)
                                session.commit()
                                _append_changelog(f"Estudiante {estudiante_id}: eliminado Enrollment {en.id}")
                            st.success("Enrollment eliminado")
                            st.experimental_rerun()
        else:
            st.info("No hay enrollments registrados para este estudiante")

    st.markdown("---")
    st.subheader("Acciones de reconciliación")
    if st.button("🔁 Reconciliar: crear enrollments faltantes (status=planned) basados en el plan"):
        if not current_version or not plan_items:
            st.error("No hay plan vigente para reconciliar")
        else:
            created = 0
            with get_session() as session:
                existing_course_ids = {e.course_id for e in session.query(Enrollment).filter(Enrollment.estudiante_id == estudiante_id).all()}
                for it in plan_items:
                    if it.course_id not in existing_course_ids:
                        en = Enrollment(
                            estudiante_id=estudiante_id,
                            course_id=it.course_id,
                            status='planned',
                            ano=it.ano,
                            semestre=1
                        )
                        session.add(en)
                        created += 1
                session.commit()
                if created:
                    _append_changelog(f"Estudiante {estudiante_id}: reconciliación creó {created} enrollments (status=planned)")
            st.success(f"Reconciliación completada: {created} enrollments creados")
            st.experimental_rerun()

    st.markdown("---")
    st.subheader("Alertas automáticas")
    # Alert: curso cursado que no está en plan
    with get_session() as session:
        plan_course_ids = {it.course_id for it in session.query(StudentPlanItem).filter(StudentPlanItem.plan_version_id == current_version.id).all()} if current_version else set()
        enroll_course_ids = [e.course_id for e in session.query(Enrollment).filter(Enrollment.estudiante_id == estudiante_id).all()]

    not_in_plan = [cid for cid in enroll_course_ids if cid not in plan_course_ids]
    if not_in_plan:
        st.warning(f"Cursos matriculados que NO están en el plan vigente: {len(not_in_plan)}")
        with get_session() as session:
            for cid in not_in_plan:
                c = session.query(Course).get(cid)
                st.write(f"- {c.nombre if c else 'ID ' + str(cid)}")

    # Repeated enrollments
    with get_session() as session:
        enrolls = session.query(Enrollment).filter(Enrollment.estudiante_id == estudiante_id).all()
    repeats = {}
    for e in enrolls:
        repeats.setdefault(e.course_id, 0)
        repeats[e.course_id] += 1
    repeated = [cid for cid, cnt in repeats.items() if cnt > 1]
    if repeated:
        st.warning(f"Cursos repetidos en enrollments: {len(repeated)}")
        with get_session() as session:
            for cid in repeated:
                c = session.query(Course).get(cid)
                st.write(f"- {c.nombre if c else 'ID ' + str(cid)} (veces: {repeats[cid]})")

    # Alerta crítica: baja que compromete 5/8 (si el estudiante baja un enrollment planeado/in_progress que es clave)
    electivas = check_electives_count(estudiante_id)
    orient = check_orientation_rule(estudiante_id)
    if electivas.get('electivas_planeadas_o_completadas', 0) < 8:
        st.warning(f"Objetivo electivas no alcanzado: {electivas.get('electivas_planeadas_o_completadas',0)}/8")
    if not orient.get('cumple_regla', True):
        st.info(f"Orientación objetivo no alcanzada: máximo {orient.get('max_electivas',0)} de 5")
import streamlit as st
from datetime import date, datetime
import pandas as pd
from lib.db import get_session
from lib.models import (
    Estudiante, Course, StudentPlanItem, PlanVersion, Enrollment
)
from lib.metrics import check_electives_count, check_orientation_rule
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


def get_plan_items(estudiante_id: int, session):
    """Obtener items del plan vigente de un estudiante."""
    current_version = session.query(PlanVersion).filter(
        PlanVersion.estudiante_id == estudiante_id,
        PlanVersion.vigente_hasta == None
    ).order_by(PlanVersion.creado_en.desc()).first()
    
    if not current_version:
        return []
    
    items = session.query(StudentPlanItem).filter(
        StudentPlanItem.plan_version_id == current_version.id
    ).all()
    return items


def get_enrollments(estudiante_id: int, session):
    """Obtener enrollments de un estudiante."""
    enrollments = session.query(Enrollment).filter(
        Enrollment.estudiante_id == estudiante_id
    ).all()
    return enrollments


def check_alerts(estudiante_id: int, session):
    """Verificar alertas sobre el plan vs enrollments."""
    alerts = []
    
    plan_items = get_plan_items(estudiante_id, session)
    enrollments = get_enrollments(estudiante_id, session)
    
    plan_courses = {item.course_id for item in plan_items}
    enrolled_courses = {e.course_id: e for e in enrollments}
    
    # Alert 1: Cursó materia que no está en plan
    for enrollment in enrollments:
        if enrollment.course_id not in plan_courses and enrollment.status in ["completed", "in_progress"]:
            course = session.query(Course).get(enrollment.course_id)
            alerts.append({
                "tipo": "⚠️ Fuera del plan",
                "mensaje": f"Cursó {course.nombre} que no está en su plan vigente",
                "severidad": "warning",
                "course_id": enrollment.course_id
            })
    
    # Alert 2: Materia repetida
    course_enrollments = {}
    for enrollment in enrollments:
        if enrollment.course_id not in course_enrollments:
            course_enrollments[enrollment.course_id] = []
        course_enrollments[enrollment.course_id].append(enrollment)
    
    for course_id, enrs in course_enrollments.items():
        completed = [e for e in enrs if e.status == "completed"]
        if len(completed) > 1:
            course = session.query(Course).get(course_id)
            alerts.append({
                "tipo": "⚠️ Materia repetida",
                "mensaje": f"Completó {course.nombre} {len(completed)} veces",
                "severidad": "warning",
                "course_id": course_id
            })
    
    # Alert 3: Baja de materia crítica para alcanzar 5/8
    # Verificar si hay items en el plan con status CANCELLED que sean críticos para orientación
    orientation_rule = check_orientation_rule(estudiante_id)
    if not orientation_rule.get("cumple_regla", False):
        max_elect = orientation_rule.get("max_electivas", 0)
        target_orient = orientation_rule.get("orientacion_principal")
        
        # Obtener items cancelados del plan
        cancelled_items = [item for item in plan_items if item.estado == "CANCELLED"]
        
        for item in cancelled_items:
            # Verificar si este item fue crítico para la orientación
            course = session.query(Course).get(item.course_id)
            if course and course.tipo_materia == "Electiva":
                from lib.models import CourseSource
                sources = session.query(CourseSource).filter(
                    CourseSource.course_id == item.course_id
                ).all()
                
                for source in sources:
                    if source.orientacion == target_orient:
                        alerts.append({
                            "tipo": "🔴 Materia crítica cancelada",
                            "mensaje": (
                                f"Canceló {course.nombre} ({source.orientacion}), "
                                f"necesita 5 en {target_orient} y solo tiene {max_elect}"
                            ),
                            "severidad": "danger",
                            "course_id": item.course_id
                        })
                        break
    
    return alerts


def run():
    st.title("📋 Gestión de Enrollments e Inscripciones")
    
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
    
    with get_session() as session:
        estudiante = session.query(Estudiante).get(estudiante_id)
        plan_items = get_plan_items(estudiante_id, session)
        enrollments = get_enrollments(estudiante_id, session)
        alerts = check_alerts(estudiante_id, session)
    
    # Mostrar alertas
    if alerts:
        st.markdown("### ⚠️ Alertas")
        for alert in alerts:
            if alert["severidad"] == "danger":
                st.error(f"{alert['tipo']}: {alert['mensaje']}")
            elif alert["severidad"] == "warning":
                st.warning(f"{alert['tipo']}: {alert['mensaje']}")
            else:
                st.info(f"{alert['tipo']}: {alert['mensaje']}")
    
    # Tabs para diferentes vistas
    tab1, tab2, tab3, tab4 = st.tabs(["Plan vs Enrollments", "Agregar Enrollment", "Reconciliar", "Historial"])
    
    with tab1:
        st.subheader("Plan vigente vs Enrollments reales")
        
        # Crear DataFrame comparativo
        comparison = []
        enrolled_course_ids = {e.course_id for e in enrollments}
        
        for item in plan_items:
            course = None
            with get_session() as session:
                course = session.query(Course).get(item.course_id)
            
            enrollment = None
            for e in enrollments:
                if e.course_id == item.course_id and e.status == "completed":
                    enrollment = e
                    break
            
            status_plan = "✅" if item.estado == "PLANNED" else "🔴" if item.estado == "CANCELLED" else "✓"
            status_enroll = "✅ Completada" if enrollment else "⏳ Sin enrollment" if item.course_id not in enrolled_course_ids else "🔄 En progreso"
            
            comparison.append({
                "Materia": course.nombre if course else f"ID {item.course_id}",
                "Programa": course.programa if course else "-",
                "Tipo": course.tipo_materia if course else "-",
                "Plan": status_plan,
                "Enrollment": status_enroll,
                "Nota": enrollment.nota if enrollment else "-",
                "Numérica": enrollment.nota_numerica if enrollment else "-",
                "item_id": item.id,
                "course_id": item.course_id,
                "enrollment_id": enrollment.id if enrollment else None
            })
        
        if comparison:
            df_comp = pd.DataFrame(comparison)
            # Mostrar sin columns internas
            display_cols = ["Materia", "Programa", "Tipo", "Plan", "Enrollment", "Nota", "Numérica"]
            st.dataframe(df_comp[display_cols], use_container_width=True)
        else:
            st.info("No hay items en el plan vigente")
    
    with tab2:
        st.subheader("Agregar o editar Enrollment")
        
        with st.form("add_enrollment_form"):
            # Filtros para seleccionar curso
            with get_session() as session:
                all_courses = session.query(Course).filter(Course.estado == "activo").all()
                course_map = {f"{c.nombre} ({c.programa})": c.id for c in all_courses}
            
            course_sel = st.selectbox("Seleccionar materia", list(course_map.keys()), key="course_sel_form")
            course_id = course_map.get(course_sel)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                status = st.selectbox("Status", ["planned", "in_progress", "completed", "dropped"])
            with col2:
                nota = st.text_input("Nota (ej: A+, B, C)", "")
            with col3:
                nota_numerica = st.number_input("Nota numérica (ej: 4.5, 3.8)", min_value=0.0, max_value=5.0, step=0.1)
            
            col4, col5 = st.columns(2)
            with col4:
                semestre = st.number_input("Semestre", min_value=1, max_value=8, value=1)
            with col5:
                ano = st.number_input("Año", min_value=2020, max_value=2030, value=date.today().year)
            
            submitted = st.form_submit_button("💾 Guardar Enrollment", type="primary")
        
        if submitted and course_id:
            try:
                with get_session() as session:
                    # Verificar si ya existe enrollment
                    existing = session.query(Enrollment).filter(
                        Enrollment.estudiante_id == estudiante_id,
                        Enrollment.course_id == course_id
                    ).first()
                    
                    if existing:
                        existing.status = status
                        existing.nota = nota if nota else None
                        existing.nota_numerica = nota_numerica if nota_numerica > 0 else None
                        existing.semestre = semestre
                        existing.ano = ano
                        existing.actualizado_en = datetime.utcnow()
                        session.commit()
                        _append_changelog(f"Estudiante {estudiante_id}: actualizado Enrollment para Course {course_id}")
                        st.success("✅ Enrollment actualizado")
                    else:
                        new_enroll = Enrollment(
                            estudiante_id=estudiante_id,
                            course_id=course_id,
                            status=status,
                            nota=nota if nota else None,
                            nota_numerica=nota_numerica if nota_numerica > 0 else None,
                            semestre=semestre,
                            ano=ano
                        )
                        session.add(new_enroll)
                        session.commit()
                        _append_changelog(f"Estudiante {estudiante_id}: creado Enrollment para Course {course_id}")
                        st.success("✅ Enrollment agregado")
                
                st.experimental_rerun()
            except Exception as e:
                logger.error(f"Error guardando enrollment: {e}")
                st.error(f"❌ Error: {str(e)}")
    
    with tab3:
        st.subheader("Reconciliar: Sugerir enrollments faltantes")
        
        if st.button("🔄 Reconciliar con plan vigente"):
            with get_session() as session:
                missing = []
                for item in plan_items:
                    # Buscar si existe enrollment para este curso
                    existing = session.query(Enrollment).filter(
                        Enrollment.estudiante_id == estudiante_id,
                        Enrollment.course_id == item.course_id
                    ).first()
                    
                    if not existing:
                        course = session.query(Course).get(item.course_id)
                        missing.append({
                            "course_id": item.course_id,
                            "nombre": course.nombre if course else f"ID {item.course_id}",
                            "programa": course.programa if course else "-",
                            "tipo": course.tipo_materia if course else "-"
                        })
                
                if missing:
                    st.info(f"Se encontraron {len(missing)} materias del plan sin enrollment")
                    
                    df_missing = pd.DataFrame(missing)
                    st.dataframe(df_missing, use_container_width=True)
                    
                    # Botón para crear todos los enrollments faltantes con status "planned"
                    if st.button("✅ Crear enrollments faltantes (status: planned)"):
                        try:
                            for item in missing:
                                new_enroll = Enrollment(
                                    estudiante_id=estudiante_id,
                                    course_id=item["course_id"],
                                    status="planned",
                                    ano=date.today().year
                                )
                                session.add(new_enroll)
                            
                            session.commit()
                            _append_changelog(f"Estudiante {estudiante_id}: reconciliados {len(missing)} enrollments faltantes")
                            st.success(f"✅ Se crearon {len(missing)} enrollments con status 'planned'")
                            st.experimental_rerun()
                        except Exception as e:
                            logger.error(f"Error reconciliando: {e}")
                            st.error(f"❌ Error: {str(e)}")
                else:
                    st.success("✅ Todos los items del plan tienen enrollment")
    
    with tab4:
        st.subheader("Historial de Enrollments")
        
        if enrollments:
            df_hist = pd.DataFrame([{
                "Materia": (lambda cid: (lambda c: c.nombre if c else f"ID {cid}")(
                    next((c for c in [session.query(Course).get(cid)] if session.query(Course).get(cid)), None)
                ))(e.course_id),
                "Status": e.status,
                "Nota": e.nota or "-",
                "Numérica": e.nota_numerica or "-",
                "Semestre": e.semestre or "-",
                "Año": e.ano or "-",
                "Actualizado": e.actualizado_en.date() if e.actualizado_en else "-",
                "id": e.id
            } for e in enrollments])
            
            display_cols = ["Materia", "Status", "Nota", "Numérica", "Semestre", "Año", "Actualizado"]
            st.dataframe(df_hist[display_cols], use_container_width=True)
            
            # Opciones de edición
            st.markdown("#### Editar Enrollment")
            select_enroll = st.selectbox(
                "Seleccionar enrollment",
                [f"{e.id}: {next((c.nombre for c in [session.query(Course).get(e.course_id)]), 'N/A')}" 
                 for e in enrollments],
                key="edit_enroll_select"
            )
            
            if select_enroll:
                with get_session() as session:
                    enr_id = int(select_enroll.split(":")[0])
                    enr = session.query(Enrollment).get(enr_id)
                    
                    if enr:
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            new_status = st.selectbox("Nuevo Status", 
                                ["planned", "in_progress", "completed", "dropped"], 
                                index=["planned", "in_progress", "completed", "dropped"].index(enr.status),
                                key="edit_status"
                            )
                        with col2:
                            new_nota = st.text_input("Nueva nota", value=enr.nota or "", key="edit_nota")
                        with col3:
                            new_nota_num = st.number_input("Nueva nota numérica", 
                                min_value=0.0, max_value=5.0, step=0.1,
                                value=enr.nota_numerica or 0.0, key="edit_nota_num"
                            )
                        
                        col4, col5 = st.columns(2)
                        with col4:
                            if st.button("💾 Actualizar", key="save_edit"):
                                enr.status = new_status
                                enr.nota = new_nota if new_nota else None
                                enr.nota_numerica = new_nota_num if new_nota_num > 0 else None
                                session.commit()
                                _append_changelog(f"Estudiante {estudiante_id}: actualizado Enrollment {enr_id}")
                                st.success("✅ Enrollment actualizado")
                                st.experimental_rerun()
                        
                        with col5:
                            if st.button("🗑️ Eliminar", key="delete_enroll"):
                                session.delete(enr)
                                session.commit()
                                _append_changelog(f"Estudiante {estudiante_id}: eliminado Enrollment {enr_id}")
                                st.success("✅ Enrollment eliminado")
                                st.experimental_rerun()
        else:
            st.info("No hay enrollments para este estudiante")

