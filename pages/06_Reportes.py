import streamlit as st
import pandas as pd
from datetime import datetime
from lib.db import get_session
from lib.models import (
    Estudiante, Course, CourseSource, StudentPlanItem, PlanVersion, Enrollment
)
from lib.metrics import compute_orientation_counts, check_electives_count, get_student_risk_report
from lib.utils import get_logger

logger = get_logger(__name__)


ELECTIVE_TYPE = "Electiva"


def _append_changelog(text: str):
    ts = datetime.utcnow().isoformat()
    line = f"[{ts}] {text}\n"
    try:
        with open('ChangeLog.md', 'a', encoding='utf-8') as f:
            f.write(line)
    except Exception as e:
        logger.error(f"No se pudo escribir ChangeLog: {e}")


def run():
    st.title("📈 Reportes Académicos")

    with get_session() as session:
        programas = [p[0] for p in session.query(Course.programa).distinct().all() if p[0]]
        anos = sorted({c.ano for c in session.query(Course).filter(Course.ano.isnot(None)).all()})
        orientaciones = [o[0] for o in session.query(CourseSource.orientacion).distinct().all() if o[0]]

        estudiantes = session.query(Estudiante).order_by(Estudiante.nombre).all()

    st.sidebar.header("Filtros globales")
    prog_sel = st.sidebar.multiselect("Programa", options=programas, default=programas)
    ano_sel = st.sidebar.multiselect("Año (materia)", options=[str(a) for a in anos], default=[str(a) for a in anos])
    orient_sel = st.sidebar.multiselect("Orientación", options=orientaciones, default=orientaciones)

    tab1, tab2, tab3, tab4 = st.tabs([
        "Demanda por Course",
        "Demanda Electiva por Mes/Módulo",
        "Cumplimiento y Orientaciones",
        "Lista de Riesgo"
    ])

    # Report 1: Demanda por Course (plan vigente)
    with tab1:
        st.subheader("Demanda de cupos por Course (Plan vigente)")
        rows = []
        with get_session() as session:
            # Obtener versiones vigentes por estudiante
            pvq = session.query(PlanVersion).filter(PlanVersion.vigente_hasta == None).all()
            student_versions = {pv.estudiante_id: pv.id for pv in pvq}

            # Count students planning each course
            q = session.query(StudentPlanItem).join(Course, StudentPlanItem.course_id == Course.id)
            q = q.filter(StudentPlanItem.plan_version_id.isnot(None))
            if prog_sel:
                q = q.filter(Course.programa.in_(prog_sel))
            if ano_sel:
                anos_int = [int(a) for a in ano_sel if a.isdigit()]
                if anos_int:
                    q = q.filter(Course.ano.in_(anos_int))
            items = q.all()

            counts = {}
            for it in items:
                # only count if item belongs to a current plan version
                if it.plan_version_id and it.estudiante_id in student_versions:
                    # check orientation via CourseSource
                    orient_vals = [s.orientacion for s in it.course.sources if s.orientacion]
                    orient_ok = any(o in orient_sel for o in orient_vals) if orient_sel else True
                    if not orient_ok:
                        continue
                    counts.setdefault(it.course_id, set()).add(it.estudiante_id)

            data = []
            for cid, students_set in counts.items():
                c = session.query(Course).get(cid)
                data.append({
                    "course_id": cid,
                    "nombre": c.nombre if c else f"ID {cid}",
                    "programa": c.programa if c else None,
                    "ano": c.ano if c else None,
                    "demand": len(students_set)
                })

        if data:
            df = pd.DataFrame(data).sort_values(by="demand", ascending=False)
            st.dataframe(df, use_container_width=True)
            st.download_button("📥 Exportar CSV", data=df.to_csv(index=False), file_name="demanda_courses.csv")
        else:
            st.info("No se encontraron datos de demanda con los filtros aplicados")

    # Report 2: Demanda por electiva única por mes/módulo
    with tab2:
        st.subheader("Demanda de electivas — por mes / módulo")
        with get_session() as session:
            q = session.query(StudentPlanItem).join(Course, StudentPlanItem.course_id == Course.id)
            q = q.filter(Course.tipo_materia == ELECTIVE_TYPE)
            if prog_sel:
                q = q.filter(Course.programa.in_(prog_sel))
            if ano_sel:
                anos_int = [int(a) for a in ano_sel if a.isdigit()]
                if anos_int:
                    q = q.filter(Course.ano.in_(anos_int))
            items = q.all()

            rows = []
            for it in items:
                ts = it.creado_en or datetime.utcnow()
                month = ts.strftime('%Y-%m')
                # módulo desde CourseSource.modulo (puede tener varias fuentes)
                modulo_vals = [s.modulo for s in it.course.sources if s.modulo]
                modulo = modulo_vals[0] if modulo_vals else 'N/A'
                rows.append({
                    'month': month,
                    'modulo': modulo,
                    'course_id': it.course_id,
                    'course_nombre': it.course.nombre if it.course else None,
                    'estudiante_id': it.estudiante_id
                })

            if rows:
                df = pd.DataFrame(rows)
                grouped = df.groupby(['month','modulo']).agg({'estudiante_id':pd.Series.nunique}).reset_index()
                grouped = grouped.rename(columns={'estudiante_id':'unique_students'})
                st.dataframe(grouped.sort_values(['month','unique_students'], ascending=[False,False]), use_container_width=True)
                st.download_button("📥 Exportar CSV", data=grouped.to_csv(index=False), file_name="demanda_electivas_mes_modulo.csv")
            else:
                st.info("No hay electivas en los datos")

    # Report 3: Cumplimiento
    with tab3:
        st.subheader("Cumplimiento objetivo 5/8 y distribución por orientación")
        with get_session() as session:
            students = session.query(Estudiante).all()

        rows = []
        orient_distribution = {}
        achieved_count = 0
        total_students = len(students)
        total_completed_electivas = 0

        for s in students:
            elect = check_electives_count(s.id)
            orient = compute_orientation_counts(s.id, datetime.utcnow().year)
            max_e = 0
            if orient.get('orientaciones'):
                max_e = max(orient.get('orientaciones').values())
            achieved = (max_e >= 5)
            if achieved:
                achieved_count += 1
            total_completed_electivas += elect.get('electivas_completadas', 0)
            # accumulate orientation distribution
            for o, cnt in orient.get('orientaciones', {}).items():
                orient_distribution[o] = orient_distribution.get(o, 0) + cnt

            rows.append({
                'estudiante_id': s.id,
                'nombre': s.nombre,
                'electivas_completadas': elect.get('electivas_completadas', 0),
                'electivas_planeadas': elect.get('electivas_planeadas_o_completadas', 0),
                'cumple_5_8': achieved
            })

        df = pd.DataFrame(rows)
        pct_cumplen = round((achieved_count / total_students * 100), 2) if total_students > 0 else 0
        avg_completed = round((total_completed_electivas / total_students), 2) if total_students > 0 else 0

        st.metric("% estudiantes con 5/8 logrado", f"{pct_cumplen}%")
        st.metric("Promedio electivas completadas por estudiante", f"{avg_completed}")

        st.markdown("**Distribución por orientación (total de electivas completadas)**")
        if orient_distribution:
            df_or = pd.DataFrame([{'orientacion':k,'count':v} for k,v in orient_distribution.items()])
            st.dataframe(df_or.sort_values('count', ascending=False), use_container_width=True)
            st.download_button("📥 Exportar CSV distribución orientación", data=df_or.to_csv(index=False), file_name="distrib_orientacion.csv")
        else:
            st.info("No hay datos de orientaciones")

        st.dataframe(df.sort_values('electivas_completadas', ascending=False), use_container_width=True)
        st.download_button("📥 Exportar CSV cumplimiento", data=df.to_csv(index=False), file_name="cumplimiento_estudiantes.csv")

    # Report 4: Lista de riesgo
    with tab4:
        st.subheader("Lista de riesgo — estudiantes que podrían no alcanzar 5/8")
        with get_session() as session:
            students = session.query(Estudiante).all()

        risk_rows = []
        for s in students:
            risk = get_student_risk_report(s.id)
            if risk.get('en_riesgo'):
                risk_rows.append({
                    'estudiante_id': s.id,
                    'nombre': s.nombre,
                    'resumen': risk.get('resumen'),
                    'factores_riesgo': '; '.join(risk.get('factores_riesgo', []))
                })

        if risk_rows:
            df_risk = pd.DataFrame(risk_rows)
            st.dataframe(df_risk, use_container_width=True)
            st.download_button("📥 Exportar CSV lista riesgo", data=df_risk.to_csv(index=False), file_name="lista_riesgo.csv")
        else:
            st.info("No se detectaron estudiantes en riesgo con los criterios actuales")

    _append_changelog("Generado reportes en pages/06_Reportes.py")
