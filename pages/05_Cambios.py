import streamlit as st
import pandas as pd
from datetime import datetime, date
from lib.db import get_session
from lib.models import Estudiante
from lib.utils import get_logger
import re

logger = get_logger(__name__)


def _parse_changelog_line(line: str):
    """Parsea una línea de ChangeLog en (ts, texto, estudiante_id, entidad)
    Soporta formatos:
    - [ISO_TIMESTAMP] texto
    - YYYY-MM-DD: texto
    """
    line = line.strip()
    if not line:
        return None
    ts = None
    texto = line
    m = re.match(r"^\[(.*?)\]\s*(.*)$", line)
    if m:
        try:
            ts = datetime.fromisoformat(m.group(1))
        except Exception:
            ts = None
        texto = m.group(2)
    else:
        m2 = re.match(r"^(\d{4}-\d{2}-\d{2})[:T\s-]*(.*)$", line)
        if m2:
            try:
                ts = datetime.fromisoformat(m2.group(1))
            except Exception:
                ts = None
            texto = m2.group(2).strip()

    # Extraer estudiante_id si aparece en texto como 'Estudiante <id>'
    est_id = None
    m3 = re.search(r"Estudiante\s+(\d+)", texto)
    if m3:
        est_id = int(m3.group(1))

    # Extraer entidad simple (palabra clave como PlanVersion, Course, etc.)
    entidad = None
    m4 = re.search(r"PlanVersion|Course|StudentPlanItem|Inscripcion|Cambio|Ruta|Cronograma", texto)
    if m4:
        entidad = m4.group(0)

    return {
        "timestamp": ts,
        "texto": texto,
        "estudiante_id": est_id,
        "entidad": entidad
    }


def run():
    st.title("📝 ChangeLog — Consultas y Export")

    # Cargar estudiantes para filtro
    with get_session() as session:
        estudiantes = session.query(Estudiante).order_by(Estudiante.nombre).all()

    est_map = {"(Todos)": None}
    for e in estudiantes:
        est_map[f"{e.nombre} ({e.documento})"] = e.id

    col1, col2 = st.columns([2, 3])
    with col1:
        fecha_inicio = st.date_input("Fecha inicio", value=date(2024, 1, 1))
    with col2:
        fecha_fin = st.date_input("Fecha fin", value=date.today())

    est_sel = st.selectbox("Filtrar por estudiante", list(est_map.keys()))
    entidad_filter = st.text_input("Filtrar por entidad (texto)")
    texto_buscar = st.text_input("Buscar en texto")

    # Leer ChangeLog.md
    try:
        with open('ChangeLog.md', 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except FileNotFoundError:
        st.error("No se encontró ChangeLog.md")
        return

    rows = []
    for line in lines:
        parsed = _parse_changelog_line(line)
        if not parsed:
            continue
        rows.append(parsed)

    if not rows:
        st.info("ChangeLog vacío")
        return

    df = pd.DataFrame(rows)

    # Normalizar timestamps nulos con fecha mínima
    df['timestamp'] = df['timestamp'].apply(lambda x: x if x is not None else datetime(1970,1,1))

    # Aplicar filtros
    mask = (df['timestamp'].dt.date >= fecha_inicio) & (df['timestamp'].dt.date <= fecha_fin)

    if est_map.get(est_sel) is not None:
        mask = mask & (df['estudiante_id'] == est_map.get(est_sel))

    if entidad_filter:
        mask = mask & df['texto'].str.contains(entidad_filter, case=False, na=False)

    if texto_buscar:
        mask = mask & df['texto'].str.contains(texto_buscar, case=False, na=False)

    df_filtr = df[mask].copy()

    if df_filtr.empty:
        st.info("No hay entradas que coincidan con los filtros")
        return

    # Mostrar tabla
    df_show = df_filtr.copy()
    df_show['timestamp'] = df_show['timestamp'].apply(lambda x: x.isoformat() if x and isinstance(x, datetime) else '')
    st.dataframe(df_show[['timestamp','texto','estudiante_id','entidad']], use_container_width=True)

    # Exportar a CSV
    csv = df_filtr.to_csv(index=False)
    st.download_button("📥 Exportar CSV (filtrado)", data=csv, file_name="changelog_filtrado.csv", mime="text/csv")

    # Buscar simple dentro del changelog
    if st.button("🔎 Abrir búsqueda avanzada"):
        st.write("Use los filtros arriba para refinar la búsqueda")
