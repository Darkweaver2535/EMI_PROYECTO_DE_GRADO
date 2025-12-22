# Sistema OSINT - Vicerrectorado EMI Bolivia

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Status](https://img.shields.io/badge/Status-Sprint%201--2-orange.svg)

Sistema de recolección y análisis de datos de fuentes abiertas (OSINT) para el Vicerrectorado de la Escuela Militar de Ingeniería (EMI) Bolivia.

## 📋 Descripción

Este proyecto implementa un sistema automatizado de Open Source Intelligence (OSINT) que:

- **Recolecta** datos públicos de redes sociales (Facebook y TikTok)
- **Procesa** los datos mediante un pipeline ETL (Extract, Transform, Load)
- **Almacena** la información en una base de datos SQLite estructurada
- **Automatiza** la recolección periódica mediante un scheduler

### Objetivo Específico 1
> "Analizar datos provenientes de fuentes abiertas, utilizando técnicas de Open Source Intelligence (OSINT) para construir una base de datos de la información"

## 🎯 Fuentes de Datos Configuradas

| Plataforma | Cuenta | URL |
|------------|--------|-----|
| Facebook | EMI Oficial | https://www.facebook.com/profile.php?id=61574626396439 |
| Facebook | EMI UALP | https://www.facebook.com/EMI.UALP |
| TikTok | EMI La Paz Oficial | https://www.tiktok.com/@emilapazoficial |

## 🚀 Instalación

### Prerrequisitos

- Python 3.10 o superior
- pip (gestor de paquetes de Python)
- Git

### Pasos de Instalación

1. **Clonar el repositorio**
```bash
cd SISTEMA_ANALÍTICA_EMI
cd osint_vicerrectorado
```

2. **Crear entorno virtual**
```bash
python -m venv venv
source venv/bin/activate  # En macOS/Linux
# o
venv\Scripts\activate  # En Windows
```

3. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

4. **Instalar Playwright**
```bash
playwright install chromium
```

5. **Inicializar base de datos**
```bash
python main.py --init-db
```

## 📖 Uso

### Comandos Principales

| Comando | Descripción |
|---------|-------------|
| `--collect` | Ejecutar recolección de datos OSINT |
| `--process` | Ejecutar procesamiento ETL |
| `--stats` | Mostrar estadísticas del sistema |
| `--schedule-start` | Iniciar scheduler automático |
| `--init-db` | Inicializar base de datos |
| `--export` | Exportar datos a CSV |

### Ejemplos

**Recolección manual de todas las fuentes:**
```bash
python main.py --collect
```

**Recolección con límite específico:**
```bash
python main.py --collect --limit 50
```

**Recolección solo de Facebook:**
```bash
python main.py --collect --source facebook
```

**Ejecutar procesamiento ETL:**
```bash
python main.py --process
```

**Ver estadísticas:**
```bash
python main.py --stats
```

**Iniciar scheduler automático (12 horas):**
```bash
python main.py --schedule-start
```

**Exportar datos procesados:**
```bash
python main.py --export --output datos_osint.csv
```

## 📁 Estructura del Proyecto

```
osint_vicerrectorado/
├── main.py                 # CLI principal
├── config.json             # Configuración del sistema
├── requirements.txt        # Dependencias Python
├── README.md               # Este archivo
│
├── scrapers/               # Módulos de scraping
│   ├── __init__.py
│   ├── base_scraper.py     # Clase base con Template Method
│   ├── facebook_scraper.py # Scraper de Facebook
│   └── tiktok_scraper.py   # Scraper de TikTok
│
├── database/               # Módulo de base de datos
│   ├── __init__.py
│   ├── schema.sql          # Esquema SQLite
│   └── db_writer.py        # Gestor de base de datos
│
├── etl/                    # Módulos ETL
│   ├── __init__.py
│   ├── data_cleaner.py     # Limpieza de datos
│   ├── data_transformer.py # Transformación de datos
│   ├── data_validator.py   # Validación de datos
│   └── etl_controller.py   # Controlador del pipeline
│
├── controllers/            # Controladores principales
│   ├── __init__.py
│   └── osint_controller.py # Orquestador de scrapers
│
├── utils/                  # Utilidades
│   ├── __init__.py
│   ├── rate_limiter.py     # Control de tasa de peticiones
│   └── logger.py           # Configuración de logging
│
├── tests/                  # Tests unitarios
│   ├── __init__.py
│   ├── conftest.py         # Configuración de pytest
│   ├── test_scrapers.py    # Tests de scrapers
│   ├── test_etl.py         # Tests de ETL
│   ├── test_database.py    # Tests de base de datos
│   └── test_controller.py  # Tests del controlador
│
└── data/                   # Datos y logs (gitignored)
    ├── osint_emi.db        # Base de datos SQLite
    └── logs/               # Archivos de log
```

## 🗄️ Esquema de Base de Datos

### Tablas Principales

#### `fuente_osint`
Almacena información de las fuentes de datos configuradas.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | INTEGER | ID primario |
| nombre | TEXT | Nombre descriptivo |
| tipo | TEXT | Facebook, TikTok, etc. |
| url | TEXT | URL de la fuente |
| identificador | TEXT | ID único de la plataforma |
| activo | INTEGER | Estado activo/inactivo |

#### `dato_recolectado`
Almacena los datos raw recolectados de las fuentes.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | INTEGER | ID primario |
| id_fuente | INTEGER | FK a fuente_osint |
| id_externo | TEXT | ID del post en la plataforma |
| contenido | TEXT | Texto del post |
| fecha_publicacion | DATETIME | Fecha de publicación |
| likes | INTEGER | Número de likes |
| comentarios | INTEGER | Número de comentarios |
| compartidos | INTEGER | Número de compartidos |
| tipo_contenido | TEXT | post, video, etc. |
| metadata | TEXT | JSON con datos adicionales |

#### `dato_procesado`
Almacena los datos después del procesamiento ETL.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | INTEGER | ID primario |
| id_dato_raw | INTEGER | FK a dato_recolectado |
| contenido_limpio | TEXT | Texto procesado |
| sentimiento | TEXT | positive, negative, neutral |
| categoria | TEXT | Clasificación del contenido |
| semestre_academico | TEXT | Período académico |
| engagement_score | REAL | Score normalizado |

#### `log_ejecucion`
Registra las ejecuciones del sistema.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | INTEGER | ID primario |
| tipo | TEXT | recoleccion, etl |
| fuente | TEXT | Fuente procesada |
| inicio | DATETIME | Hora de inicio |
| fin | DATETIME | Hora de fin |
| exito | INTEGER | Estado de éxito |
| procesados | INTEGER | Total procesados |

## 🧪 Tests

### Ejecutar todos los tests
```bash
pytest tests/ -v
```

### Ejecutar con cobertura
```bash
pytest tests/ -v --cov=. --cov-report=html
```

### Ejecutar tests específicos
```bash
# Solo scrapers
pytest tests/test_scrapers.py -v

# Solo ETL
pytest tests/test_etl.py -v

# Solo database
pytest tests/test_database.py -v
```

### Cobertura Objetivo
- **Mínimo**: 85% en módulos core
- **Tests**: 15+ tests unitarios

## ⚙️ Configuración

El archivo `config.json` contiene toda la configuración del sistema:

```json
{
  "database": {
    "path": "data/osint_emi.db",
    "type": "sqlite"
  },
  "sources": {
    "facebook": {
      "enabled": true,
      "pages": [...]
    },
    "tiktok": {
      "enabled": true,
      "accounts": [...]
    }
  },
  "scraping": {
    "min_delay_seconds": 3,
    "max_delay_seconds": 7,
    "max_retries": 3
  },
  "scheduler": {
    "collection_interval_hours": 12,
    "etl_interval_hours": 6
  }
}
```

## 🔒 Técnicas Anti-Detección

El sistema implementa varias técnicas para evitar bloqueos:

1. **Rotación de User-Agents**: 15+ user agents diferentes
2. **Delays aleatorios**: 3-7 segundos entre peticiones
3. **Rate limiting**: Límites por plataforma (60 req/h Facebook, 30 req/h TikTok)
4. **Navegador headless**: Chromium con configuración stealth
5. **Viewport realista**: 1920x1080 (desktop) o móvil para TikTok

## 📊 Pipeline ETL

### 1. Extracción (Extract)
- Lectura de datos no procesados de `dato_recolectado`
- Conversión a DataFrame de pandas

### 2. Limpieza (Clean)
- Eliminación de URLs
- Normalización de espacios
- Corrección de encoding UTF-8
- Opcional: eliminación de emojis, menciones, hashtags

### 3. Transformación (Transform)
- Extracción de características temporales (día, hora, semestre académico)
- Normalización de engagement (0-100)
- Clasificación de contenido (Felicitación, Queja, Sugerencia, etc.)
- Análisis de sentimiento básico

### 4. Validación (Validate)
- Verificación de campos requeridos
- Validación de rangos numéricos
- Filtrado de registros inválidos

### 5. Carga (Load)
- Guardado en `dato_procesado`
- Marcado de registros raw como procesados
- Registro de ejecución en logs

## 📈 Metodología Scrum

### Sprint 1: Módulo de Recolección Automatizada
- [x] Configuración de fuentes
- [x] Scrapers para Facebook y TikTok
- [x] Almacenamiento en base de datos
- [x] Scheduler para automatización

### Sprint 2: Pipeline ETL
- [x] Limpieza de datos
- [x] Transformación y enriquecimiento
- [x] Validación de datos
- [x] Tests unitarios (15+)

## 🛠️ Tecnologías Utilizadas

| Categoría | Tecnología |
|-----------|------------|
| Lenguaje | Python 3.10+ |
| Web Scraping | Playwright, BeautifulSoup4 |
| Base de Datos | SQLite |
| ETL | pandas, numpy |
| Scheduler | APScheduler |
| Testing | pytest, pytest-cov |
| Logging | logging (Python stdlib) |

## 📝 Notas Importantes

1. **Datos Reales**: Este sistema recolecta datos reales de fuentes públicas. No se utilizan datos simulados.

2. **Uso Responsable**: Respetar los términos de servicio de las plataformas y las leyes de protección de datos.

3. **Rate Limiting**: Los límites de tasa están configurados para evitar sobrecarga en los servidores.

4. **Logs**: Todos los logs se almacenan en `data/logs/` para auditoría.

## 📄 Licencia

Este proyecto es para uso académico de la Escuela Militar de Ingeniería (EMI) Bolivia.

## 👥 Autor

Sistema desarrollado para el Vicerrectorado EMI como parte del proyecto de analítica de datos.

---

**Versión**: 1.0.0  
**Última actualización**: Diciembre 2024
