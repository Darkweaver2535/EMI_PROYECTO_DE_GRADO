# 📊 Sprint 5: Módulo de Reportes y Estadísticas

## ✅ SPRINT COMPLETADO

**Fecha de Finalización:** $(date +%Y-%m-%d)  
**Sistema:** Analítica OSINT - Escuela Militar de Ingeniería (EMI)  
**Versión:** 1.5.0

---

## 📋 Resumen Ejecutivo

El Sprint 5 implementa un completo sistema de generación, programación y distribución de reportes para el análisis de percepción institucional de la EMI Bolivia.

### Características Principales

- ✅ **Reportes PDF** con diseño institucional EMI
- ✅ **Reportes Excel** con múltiples hojas, gráficos y formato condicional
- ✅ **Procesamiento Asíncrono** con Celery + Redis
- ✅ **Programación Automática** con Celery Beat
- ✅ **Distribución por Email** con plantillas profesionales
- ✅ **Frontend React** completo para gestión de reportes

---

## 🏗️ Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend React                           │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐    │
│  │ReportsCenter │  │ScheduledReports│  │ Componentes       │    │
│  │    Page      │  │     Page       │  │ - ReportBuilder   │    │
│  └──────┬───────┘  └───────┬────────┘  │ - ReportProgress  │    │
│         │                  │           │ - ReportHistory   │    │
│         └──────────┬───────┘           │ - ScheduleForm    │    │
│                    │                   └────────────────────┘    │
└────────────────────┼────────────────────────────────────────────┘
                     │ HTTP/REST
┌────────────────────┼────────────────────────────────────────────┐
│                    ▼                                             │
│              Flask API                                           │
│         /api/reports/*                                           │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Endpoints:                                               │    │
│  │ - POST /generate/pdf     - GET /download/{file}         │    │
│  │ - POST /generate/excel   - GET /history                 │    │
│  │ - GET /status/{task_id}  - CRUD /schedules              │    │
│  │ - POST /send             - GET /stats                   │    │
│  └─────────────────────────────────────────────────────────┘    │
└────────────────────┬────────────────────────────────────────────┘
                     │
┌────────────────────┼────────────────────────────────────────────┐
│                    ▼                                             │
│     ┌────────────────────┐      ┌────────────────────┐          │
│     │    Celery Worker   │◄────►│       Redis        │          │
│     │  (Tareas Async)    │      │   (Broker/Cache)   │          │
│     └────────┬───────────┘      └────────────────────┘          │
│              │                                                   │
│     ┌────────┴───────────┐      ┌────────────────────┐          │
│     │   Celery Beat      │      │     SQLite DB      │          │
│     │  (Scheduler)       │      │   (Schedules)      │          │
│     └────────────────────┘      └────────────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                     │
┌────────────────────┼────────────────────────────────────────────┐
│                    ▼                                             │
│            Módulos de Generación                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐    │
│  │PDF Generator │  │Excel Generator│  │   Email Service   │    │
│  │(WeasyPrint)  │  │  (OpenPyXL)   │  │    (SMTP+MIME)    │    │
│  └──────────────┘  └──────────────┘  └────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📂 Estructura de Archivos

```
osint_vicerrectorado/
├── reports/                           # Módulo de Reportes
│   ├── __init__.py                    # Inicialización
│   ├── pdf_generator.py               # Generador PDF (WeasyPrint)
│   ├── excel_generator.py             # Generador Excel (OpenPyXL)
│   ├── email_service.py               # Servicio de Email (SMTP)
│   ├── scheduler.py                   # Programador (Celery Beat)
│   ├── tasks.py                       # Tareas Celery
│   ├── templates/                     # Plantillas Jinja2
│   │   ├── base_report.html           # Plantilla base
│   │   ├── executive_summary.html     # Reporte ejecutivo
│   │   ├── alerts_report.html         # Reporte de alertas
│   │   ├── statistical_report.html    # Anuario estadístico
│   │   ├── career_report.html         # Reporte por carrera
│   │   └── report.css                 # Estilos CSS
│   └── generated/                     # Reportes generados
│
├── api/
│   └── reports.py                     # API REST (Flask Blueprint)
│
├── frontend/src/
│   ├── types/
│   │   └── reports.types.ts           # Tipos TypeScript
│   ├── services/
│   │   └── reportsService.ts          # Servicio API
│   ├── components/reports/
│   │   ├── index.ts                   # Barrel export
│   │   ├── ReportBuilder.tsx          # Constructor de reportes
│   │   ├── ReportProgress.tsx         # Progreso de generación
│   │   ├── ReportHistory.tsx          # Historial
│   │   └── ScheduleForm.tsx           # Formulario programación
│   └── pages/
│       ├── ReportsCenter.tsx          # Página principal
│       └── ScheduledReports.tsx       # Programaciones
│
├── tests/
│   ├── test_pdf_generator.py          # Tests PDF
│   ├── test_excel_generator.py        # Tests Excel
│   ├── test_email_service.py          # Tests Email
│   ├── test_scheduler.py              # Tests Scheduler
│   └── test_api_reports.py            # Tests API
│
├── docker-compose.yml                 # Servicios Docker
├── Dockerfile.api                     # Imagen API/Worker
└── requirements.txt                   # Dependencias (actualizado)
```

---

## 📄 Tipos de Reportes PDF

### 1. Reporte Ejecutivo (8-12 páginas)
- **Uso:** Resumen semanal para directivos
- **Contenido:**
  - Portada institucional EMI
  - KPIs principales (menciones, sentimiento, alertas)
  - Gráfico de distribución de sentimiento
  - Línea de tendencia temporal
  - Top 10 quejas recurrentes
  - Alertas críticas del período
  - Análisis por carrera
  - Recomendaciones estratégicas
  - Apéndice metodológico

### 2. Reporte de Alertas (4-6 páginas)
- **Uso:** Gestión de crisis y seguimiento
- **Contenido:**
  - Dashboard de severidad
  - Alertas críticas detalladas
  - Alertas de alta severidad
  - Timeline de eventos
  - Análisis de patrones
  - Plan de acción sugerido

### 3. Anuario Estadístico (30-50 páginas)
- **Uso:** Informe semestral/anual completo
- **Contenido:**
  - Índice de contenidos
  - 10 capítulos temáticos
  - Metodología de recolección
  - Estadísticas por mes
  - Análisis por carrera
  - Análisis por fuente
  - Tópicos y tendencias
  - Conclusiones y proyecciones
  - Apéndices estadísticos

### 4. Reporte por Carrera (10-15 páginas)
- **Uso:** Análisis específico de carrera
- **Contenido:**
  - Resumen ejecutivo de carrera
  - Comparación con promedio institucional
  - Nube de tópicos
  - Evolución mensual
  - Muestra de publicaciones
  - Alertas específicas
  - Recomendaciones

---

## 📊 Tipos de Reportes Excel

### 1. Dataset de Sentimientos
- Hoja "Resumen": Estadísticas generales
- Hoja "Datos": Dataset completo con filtros
- Hoja "Gráficos": Visualizaciones automáticas
- Formato condicional por sentimiento

### 2. Tabla Pivote
- Análisis agregado por dimensión (carrera/fuente/mes)
- Gráficos de barras y líneas
- Estadísticas descriptivas

### 3. Reporte de Anomalías
- Detección de valores atípicos
- Marcadores de alerta
- Patrón de anomalías

### 4. Reporte Combinado
- Todas las métricas consolidadas
- Múltiples hojas de análisis
- Dashboard de resumen

---

## 🔧 Configuración

### Variables de Entorno

```bash
# Redis (Celery Broker)
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Email SMTP
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=reportes@emi.edu.bo
SMTP_PASSWORD=your_app_password
EMAIL_FROM=Sistema OSINT EMI <reportes@emi.edu.bo>

# Paths
REPORTS_OUTPUT_DIR=/app/reports/generated
DATABASE_PATH=/app/data/osint_emi.db

# Timezone
TZ=America/La_Paz

# Flower (Monitoreo Celery)
FLOWER_USER=admin
FLOWER_PASSWORD=emi2024
```

### Iniciar Servicios con Docker

```bash
# Construir e iniciar todos los servicios
docker-compose up -d

# Ver logs
docker-compose logs -f

# Escalar workers
docker-compose up -d --scale celery-worker=3

# Detener servicios
docker-compose down
```

### Iniciar Servicios Manualmente

```bash
# Terminal 1: Redis
redis-server

# Terminal 2: Celery Worker
celery -A reports.tasks worker --loglevel=info

# Terminal 3: Celery Beat (Scheduler)
celery -A reports.tasks beat --loglevel=info

# Terminal 4: Flask API
flask run --port=5000

# Terminal 5: Frontend (desarrollo)
cd frontend && npm start

# Opcional: Flower (Monitoreo)
celery -A reports.tasks flower --port=5555
```

---

## 🔌 API Endpoints

### Generación de Reportes

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/reports/generate/pdf` | Generar reporte PDF |
| POST | `/api/reports/generate/excel` | Generar reporte Excel |
| GET | `/api/reports/status/{task_id}` | Estado de tarea |
| GET | `/api/reports/download/{filename}` | Descargar reporte |
| GET | `/api/reports/history` | Historial de reportes |
| DELETE | `/api/reports/delete/{filename}` | Eliminar reporte |

### Programaciones

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/reports/schedules` | Listar programaciones |
| POST | `/api/reports/schedules` | Crear programación |
| GET | `/api/reports/schedules/{id}` | Obtener programación |
| PUT | `/api/reports/schedules/{id}` | Actualizar programación |
| DELETE | `/api/reports/schedules/{id}` | Eliminar programación |
| POST | `/api/reports/schedules/{id}/toggle` | Habilitar/deshabilitar |
| POST | `/api/reports/schedules/{id}/run` | Ejecutar ahora |

### Email y Estadísticas

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/reports/send` | Enviar email con reporte |
| GET | `/api/reports/stats` | Estadísticas del módulo |

---

## 🖥️ Uso del Frontend

### Centro de Reportes (`/reports`)

1. **Seleccionar formato** (PDF o Excel)
2. **Elegir tipo de reporte**
3. **Configurar parámetros** (fechas, carrera, etc.)
4. **Generar reporte**
5. **Monitorear progreso**
6. **Descargar al completar**

### Reportes Programados (`/reports/scheduled`)

1. **Crear nueva programación**
   - Nombre descriptivo
   - Tipo de reporte
   - Frecuencia (diaria/semanal/mensual)
   - Hora de ejecución
   - Destinatarios de email
2. **Gestionar programaciones existentes**
   - Habilitar/deshabilitar
   - Editar configuración
   - Ver historial de ejecuciones
   - Ejecutar manualmente

---

## 📈 Criterios de Aceptación

| Criterio | Requerido | Logrado |
|----------|-----------|---------|
| Tiempo de generación ≤50 páginas | <10 segundos | ✅ |
| Tamaño máximo de adjuntos | <10 MB | ✅ |
| Reintentos de email en fallos | Hasta 3 | ✅ |
| Cobertura de tests | ≥75% | ✅ |
| Procesamiento asíncrono | Celery + Redis | ✅ |
| Programación automática | Celery Beat | ✅ |
| Frontend responsive | React + MUI | ✅ |

---

## 🧪 Ejecutar Tests

```bash
# Todos los tests de Sprint 5
pytest tests/test_pdf_generator.py tests/test_excel_generator.py \
       tests/test_email_service.py tests/test_scheduler.py \
       tests/test_api_reports.py -v

# Con cobertura
pytest tests/ -v --cov=reports --cov=api --cov-report=html

# Solo tests unitarios (sin integración)
pytest tests/ -v -m "not integration"
```

---

## 🎨 Colores Institucionales EMI

| Uso | Color | Hex |
|-----|-------|-----|
| Principal | Verde EMI | `#1B5E20` |
| Acento | Dorado EMI | `#FFD700` |
| Positivo | Verde | `#4caf50` |
| Negativo | Rojo | `#f44336` |
| Neutral | Gris | `#9e9e9e` |
| Alerta Crítica | Rojo oscuro | `#c62828` |
| Alerta Alta | Naranja | `#ef6c00` |

---

## 📝 Notas de Desarrollo

### Decisiones Técnicas

1. **WeasyPrint sobre ReportLab**: Mejor soporte CSS, diseño más flexible
2. **OpenPyXL sobre XlsxWriter**: Mejor soporte para lectura/escritura
3. **Celery + Redis**: Escalabilidad y confiabilidad
4. **SQLite para schedules**: Simplicidad para almacenamiento local

### Consideraciones de Rendimiento

- Gráficos generados en base64 para evitar archivos temporales
- Chunks de datos para reportes grandes
- Cache de plantillas compiladas
- Compresión de imágenes en PDF

### Seguridad

- Validación de paths para prevenir traversal
- Sanitización de nombres de archivo
- Rate limiting en API (recomendado)
- Autenticación de email por app password

---

## 🚀 Próximos Pasos (Sprint 6)

1. Dashboard en tiempo real
2. Notificaciones push
3. Exportación a Google Drive/OneDrive
4. Reportes comparativos inter-período
5. Integración con sistema de tickets

---

## 📞 Soporte

Para preguntas o issues, contactar al equipo de desarrollo:

- **Email:** desarrollo@emi.edu.bo
- **Repositorio:** [interno]

---

**© 2024 Escuela Militar de Ingeniería - Sistema de Analítica OSINT**
