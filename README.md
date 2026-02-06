# 📚 MBA Routes Manager

Sistema integral de gestión de rutas académicas para programas MBA usando Streamlit + SQLAlchemy + SQLite.

## Instalación

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Acceso: http://localhost:8501

## Estructura

- `streamlit_app.py`: Router principal
- `lib/`: Módulos DB, modelos, validadores, Excel I/O, métricas, utilidades
- `pages/`: 6 páginas (Cronograma, Estudiantes, Rutas, Inscripciones, Cambios, Reportes)

## Características

- 📅 Cronogramas académicos
- 👥 Gestión de estudiantes (CRUD, import/export)
- 🛣️ Rutas con énfasis y semestres
- 📝 Inscripciones con calificaciones
- ⚡ Solicitudes de cambio
- 📊 KPIs y reportes

## Tecnología

Streamlit + SQLAlchemy + SQLite + Pydantic + Pandas + openpyxl

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://blank-app-template.streamlit.app/)

### How to run it on your own machine

1. Install the requirements

   ```
   $ pip install -r requirements.txt
   ```

2. Run the app

   ```
   $ streamlit run streamlit_app.py
   ```
