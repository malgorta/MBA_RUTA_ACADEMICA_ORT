# GUÍA RÁPIDA: import_schedule_excel()

## 🚀 Uso en 30 segundos

```python
from lib.io_excel import import_schedule_excel

# Importar cronograma
resultado = import_schedule_excel("ruta/al/archivo.xlsx")

# Ver resultado
print(resultado)
# {
#   'cursos_creados': 45,
#   'cursos_actualizados': 12,
#   'sources_creados': 89,
#   'sources_actualizados': 23,
#   'errores_count': 0,
#   'total_filas': 124,
#   'errores': []
# }
```

---

## 📋 Requisitos del Excel

**Hoja**: exactamente `"CronogramaConsolidado"`

**Columnas** (18): 
```
Programa, Año, Módulo, Materia, Horas, 
Profesor 1, Profesor 2, Profesor 3, Inicio, Final, 
Día, Horario, Formato, Orientación, Comentarios, 
TipoMateria, SolapaFuente, MateriaID, MateriaKey
```

**Formatos**:
- Fechas: `YYYY-MM-DD`
- Orientación: Presencial / Virtual / Híbrida / Asincrónica
- Números: enteros normales

---

## 🎯 Qué hace

1. ✅ Lee Excel
2. ✅ Valida columnas
3. ✅ Crea/actualiza Cursos (por MateriaID)
4. ✅ Crea/actualiza CourseSource (por course_id+solapa+módulo)
5. ✅ Normaliza datos
6. ✅ Reporta resumen

---

## 🔄 Flujo de retorno

```python
{
    "cursos_creados": int,        # Nuevos cursos
    "cursos_actualizados": int,   # Cursos modificados
    "sources_creados": int,       # Nuevas fuentes
    "sources_actualizados": int,  # Fuentes modificadas
    "errores_count": int,         # Cantidad de errores
    "total_filas": int,           # Filas procesadas
    "errores": [str, ...]         # Detalles de errores
}
```

---

## 📲 En Streamlit

```python
import streamlit as st
from lib.io_excel import import_schedule_excel
import tempfile

st.title("Importar Cronograma")

archivo = st.file_uploader("Excel", type=["xlsx"])

if archivo:
    # Guardar temp
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        f.write(archivo.getbuffer())
        temp_path = f.name
    
    # Importar
    resultado = import_schedule_excel(temp_path)
    
    # Mostrar
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Cursos +", resultado['cursos_creados'])
    col2.metric("Cursos ~", resultado['cursos_actualizados'])
    col3.metric("Sources +", resultado['sources_creados'])
    col4.metric("Errores ✗", resultado['errores_count'])
    
    if resultado['errores']:
        st.warning(f"{resultado['errores_count']} errores")
        with st.expander("Ver"):
            for e in resultado['errores'][:10]:
                st.write(e)
```

---

## ⚙️ Funciones internas (normalizadores)

Uso si necesitás normalizar datos manualmente:

```python
from lib.io_excel import (
    _normalize_string,      # Trim, elimina NaN
    _normalize_int,         # String → int
    _normalize_date,        # String/datetime → date
    _normalize_orientation  # Valida orientación
)

_normalize_string("  Presencial  ")        # → "Presencial"
_normalize_int("42")                        # → 42
_normalize_date("2026-02-05")               # → date(2026,2,5)
_normalize_orientation("virtual", {...})    # → "Virtual"
```

---

## 🐛 Debugging

### Ver detalles de errores
```python
resultado = import_schedule_excel(path)
for error in resultado['errores']:
    print(error)
```

### Ver logs
```bash
tail -f logs/app.log | grep "import_schedule"
```

### Validar Excel antes
```python
import pandas as pd

df = pd.read_excel(path, sheet_name="CronogramaConsolidado", nrows=1)
print(df.columns.tolist())  # Ver columnas
```

---

## ✅ Validaciones automáticas

La función valida:
- ✅ Archivo existe
- ✅ Hoja "CronogramaConsolidado" existe
- ✅ Todas las 18 columnas presentes
- ✅ MateriaID y Materia no vacíos
- ✅ Fechas formato YYYY-MM-DD
- ✅ Orientación válida

Si falla una validación, se reporta en `resultado['errores']`

---

## 🔗 BD - Modelos Creados

### Tabla: courses
```sql
CREATE TABLE courses (
    id INTEGER PRIMARY KEY,
    materia_id VARCHAR(100) UNIQUE NOT NULL,
    nombre VARCHAR(255) NOT NULL,
    programa VARCHAR(255),
    horas INTEGER,
    ...
)
```

### Tabla: course_sources
```sql
CREATE TABLE course_sources (
    id INTEGER PRIMARY KEY,
    course_id INTEGER FOREIGN KEY,
    solapa_fuente VARCHAR(100),
    modulo VARCHAR(100),
    profesor_1 VARCHAR(255),
    inicio DATE,
    ...
)
```

**Upsert**: 
- Cursos por `materia_id`
- Sources por `(course_id, solapa_fuente, modulo)`

---

## 📚 Documentación Completa

- 📖 [IMPORT_SCHEDULE_DOCS.md](./IMPORT_SCHEDULE_DOCS.md) - Técnica detallada
- 🔧 [EJEMPLOS_INTEGRACION.py](./EJEMPLOS_INTEGRACION.py) - 5 ejemplos Streamlit
- 🧪 [test_import_schedule.py](./test_import_schedule.py) - Script de prueba
- ✅ [verificar_implementacion.py](./verificar_implementacion.py) - Validación

---

## 🆘 Errores Comunes

| Error | Solución |
|-------|----------|
| "Archivo no existe" | Verificar ruta |
| "Columnas faltantes" | Incluir todas 18 columnas en Excel |
| "Error leyendo hoja" | Hoja debe ser exactamente "CronogramaConsolidado" |
| Muchos errores por fila | Ver formato de fechas (YYYY-MM-DD) |

---

## 🎓 Ejemplos Reales

### Ejemplo 1: Importación básica
```python
resultado = import_schedule_excel("Cronograma_2026_verificado_completo.xlsx")
print(f"✓ Importados: {resultado['cursos_creados']} cursos nuevos")
```

### Ejemplo 2: Con validación
```python
resultado = import_schedule_excel(path)
if resultado['errores_count'] > 0:
    print(f"⚠️  Revisar {resultado['errores_count']} errores")
    for err in resultado['errores'][:5]:
        print(f"   - {err}")
else:
    print("✅ Importación sin errores")
```

### Ejemplo 3: Logging
```python
import logging
logger = logging.getLogger(__name__)

resultado = import_schedule_excel(path)
logger.info(f"Import: {resultado['cursos_creados']} cursos, "
           f"{resultado['errores_count']} errores")
```

---

**¿Necesitas más ayuda?** 
→ Ver [IMPORT_SCHEDULE_DOCS.md](./IMPORT_SCHEDULE_DOCS.md)
