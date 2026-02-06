# Función import_schedule_excel()

## Descripción

La función `import_schedule_excel(path)` importa datos de un archivo Excel con el cronograma consolidado de cursos, validando, normalizando e insertando/actualizando los registros en la base de datos.

## Ubicación

- **Módulo**: `lib/io_excel.py`
- **Función**: `import_schedule_excel(path: str) -> Dict`

## Parámetros

- `path` (str): Ruta absoluta o relativa al archivo Excel que contiene la hoja "CronogramaConsolidado"

## Valor de retorno

Retorna un diccionario con el siguiente resumen de importación:

```python
{
    "cursos_creados": int,           # Cantidad de cursos nuevos creados
    "cursos_actualizados": int,      # Cantidad de cursos actualizados
    "sources_creados": int,          # Cantidad de fuentes nuevas creadas
    "sources_actualizados": int,     # Cantidad de fuentes actualizadas
    "errores_count": int,            # Cantidad total de errores
    "total_filas": int,              # Total de filas procesadas
    "errores": List[str]             # Lista con detalles de errores por fila
}
```

## Requisitos de Excel

### Hoja requerida
- Nombre exacto: **"CronogramaConsolidado"**

### Columnas obligatorias
Se debe incluir exactamente estas columnas en el Excel:

1. **Programa** - Nombre del programa académico
2. **Año** - Año del cronograma (número)
3. **Módulo** - Módulo del curso
4. **Materia** - Nombre de la materia/curso
5. **Horas** - Cantidad de horas (número)
6. **Profesor 1** - Primer profesor
7. **Profesor 2** - Segundo profesor
8. **Profesor 3** - Tercer profesor
9. **Inicio** - Fecha de inicio (YYYY-MM-DD)
10. **Final** - Fecha de término (YYYY-MM-DD)
11. **Día** - Día/días de clase
12. **Horario** - Horario de clase
13. **Formato** - Formato de clase (presencial, virtual, etc.)
14. **Orientación** - Orientación pedagógica
15. **Comentarios** - Observaciones adicionales
16. **TipoMateria** - Tipo de materia
17. **SolapaFuente** - Identificador de fuente/pestaña
18. **MateriaID** - ID único de la materia (clave para upsert)
19. **MateriaKey** - Clave alternativa de la materia

## Lógica de operación

### 1. Validación
- ✓ Verifica que el archivo exista
- ✓ Valida que la hoja "CronogramaConsolidado" exista
- ✓ Verifica todas las columnas requeridas

### 2. Procesamiento por fila
Para cada fila del Excel:

#### Course (Curso)
- **UPSERT por MateriaID**: Si existe un curso con ese MateriaID, se actualiza; si no existe, se crea
- Actualiza campos: nombre, programa, año, tipo_materia, horas, materia_key

#### CourseSource (Fuente del Curso)
- **UPSERT por (course_id + solapa_fuente + modulo)**: Si esta combinación existe, actualiza; si no, crea
- Actualiza campos: profesores 1-3, fechas (inicio/final), día, horario, formato, orientación, comentarios

### 3. Normalización de datos

- **Strings**: Se convierten a string, se quita espacios en blanco (trim), se elimina NaN
- **Fechas**: Se convierten a tipo `date` (sin hora), formato esperado YYYY-MM-DD
- **Números**: Se convierten a int (para año y horas)
- **Orientaciones**: Se normalizan a valores válidos:
  - Presencial, Virtual, Híbrida, Asincrónica
  - Case-insensitive (se acepta cualquier mayúscula/minúscula)

### 4. Manejo de errores
- Errores de validación por columnas: Se reporta y retorna vacío
- Errores por fila: Se registra la fila y el error específico, continúa con la siguiente
- Se genera log detallado con todos los errores encontrados

## Ejemplo de uso básico

```python
from lib.io_excel import import_schedule_excel

# Importar cronograma
resultado = import_schedule_excel("data/Cronograma_2026_verificado_completo.xlsx")

# Verificar resultado
print(f"Cursos creados: {resultado['cursos_creados']}")
print(f"Cursos actualizados: {resultado['cursos_actualizados']}")
print(f"Sources creados: {resultado['sources_creados']}")
print(f"Sources actualizados: {resultado['sources_actualizados']}")
print(f"Errores: {resultado['errores_count']}")

# Ver detalles de errores
if resultado['errores']:
    for error in resultado['errores']:
        print(f"  - {error}")
```

## Ejemplo de uso en Streamlit

```python
import streamlit as st
from lib.io_excel import import_schedule_excel

st.title("Importar Cronograma")

archivo = st.file_uploader("Selecciona el archivo Excel", type=["xlsx"])

if archivo:
    # Guardar archivo temporalmente
    with open("temp.xlsx", "wb") as f:
        f.write(archivo.getbuffer())
    
    # Importar
    with st.spinner("Importando cronograma..."):
        resultado = import_schedule_excel("temp.xlsx")
    
    # Mostrar resultado
    st.success(f"✓ {resultado['cursos_creados']} cursos creados, {resultado['cursos_actualizados']} actualizados")
    st.info(f"✓ {resultado['sources_creados']} sources creados, {resultado['sources_actualizados']} actualizados")
    
    if resultado['errores_count'] > 0:
        st.warning(f"⚠ {resultado['errores_count']} errores encontrados")
        with st.expander("Ver errores"):
            for error in resultado['errores']:
                st.write(error)
```

## Modelos de base de datos

#### Course
```
id (Primary Key)
materia_id (String, Unique) - Identificador único de la materia
materia_key (String)
nombre (String)
programa (String)
ano (Integer)
tipo_materia (String)
horas (Integer)
estado (String, default="activo")
creado_en (DateTime)
actualizado_en (DateTime)
```

#### CourseSource
```
id (Primary Key)
course_id (Foreign Key -> Course)
solapa_fuente (String) - Fuente/pestaña origen
modulo (String)
profesor_1, profesor_2, profesor_3 (String)
inicio, final (Date)
dia (String)
horario (String)
formato (String)
orientacion (String)
comentarios (Text)
estado (String, default="activo")
creado_en (DateTime)
actualizado_en (DateTime)
```

## Funciones auxiliares internas

- `_normalize_string(value)`: Normaliza strings (trim, elimina NaN)
- `_normalize_int(value)`: Convierte a entero
- `_normalize_date(value)`: Convierte a tipo date
- `_normalize_orientation(value, valid_set)`: Normaliza orientaciones

## Logging y monitoreo

La función registra detalladamente todos los eventos:
- INFO: Resumen total de importación
- DEBUG: Eventos por curso (creación/actualización)
- WARNING: Orientaciones no válidas
- ERROR: Errores críticos y de validación

Todos los logs se guardan en el archivo configurado (`LOG_FILE` en config.py)

## Consideraciones importantes

1. **Transacciones**: Si ocurre un error crítico, todavía se pueden haber committeado registros anteriores. Los errores por fila no afectan la importación de otras filas.

2. **Duplicados**: El UPSERT previene duplicados:
   - Cursos: No puede haber dos con el mismo MateriaID
   - Sources: No puede haber dos con la misma combinación (course_id + solapa_fuente + modulo)

3. **Auditoría**: Todos los registros tienen timestamps de creación y actualización para auditoría.

4. **Validación de datos**: Valores inválidos se normalizan a `None` (null en BD), no genera error.

## Troubleshooting

| Problema | Causa | Solución |
|----------|-------|----------|
| "Archivo no existe" | Ruta incorrecta | Verificar path absoluto |
| "Columnas faltantes" | Falta columna en Excel | Agregar todas las columnas requeridas |
| "Error leyendo hoja" | Nombre hoja incorrecto | Debe ser exactamente "CronogramaConsolidado" |
| Muchos errores por fila | Datos mal formateados | Verificar formato de fechas (YYYY-MM-DD) |
| Pocos registros importados | Error por fila silenciado | Revisar logs en `logs/app.log` |

## Testing

Se incluye script de prueba `test_import_schedule.py` que:
1. Inicializa la base de datos
2. Ejecuta la importación
3. Muestra resultados en formato JSON
4. Lista errores encontrados

Uso:
```bash
python test_import_schedule.py
```
