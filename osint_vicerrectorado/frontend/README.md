# 📊 Sistema de Analítica EMI - Frontend

## Módulo de Dashboards Interactivos (Sprint 4)

Frontend interactivo para el Sistema de Inteligencia OSINT del Vicerrectorado de la Escuela Militar de Ingeniería (EMI) de Bolivia.

---

## 🚀 Tecnologías

| Tecnología | Versión | Propósito |
|------------|---------|-----------|
| React | 18.2.0 | Framework UI |
| TypeScript | 5.3.0 | Tipado estricto |
| Vite | 5.0.0 | Build tool |
| Material-UI | 5.14.0 | Componentes UI |
| Recharts | 2.10.0 | Gráficos |
| Axios | 1.6.0 | Cliente HTTP |
| Jest | 29.7.0 | Testing |

---

## 📦 Instalación

```bash
# Navegar al directorio frontend
cd frontend

# Instalar dependencias
npm install

# Iniciar en modo desarrollo
npm run dev

# Construir para producción
npm run build

# Ejecutar tests
npm test

# Ver cobertura de tests
npm run test:coverage
```

---

## 🏗️ Estructura del Proyecto

```
frontend/
├── src/
│   ├── components/
│   │   ├── charts/           # Componentes de gráficos
│   │   │   ├── SentimentLineChart.tsx
│   │   │   ├── SentimentPieChart.tsx
│   │   │   ├── CareerBarChart.tsx
│   │   │   ├── RadarChart.tsx
│   │   │   ├── WordCloudChart.tsx
│   │   │   ├── HeatmapChart.tsx
│   │   │   └── CorrelationMatrixChart.tsx
│   │   │
│   │   ├── common/           # Componentes reutilizables
│   │   │   ├── Header.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   ├── KPICard.tsx
│   │   │   ├── LoadingSpinner.tsx
│   │   │   ├── ErrorBoundary.tsx
│   │   │   ├── ExportButton.tsx
│   │   │   ├── DateRangePicker.tsx
│   │   │   └── EmptyState.tsx
│   │   │
│   │   ├── dashboards/       # Dashboards principales
│   │   │   ├── SentimentDashboard.tsx
│   │   │   ├── ReputationDashboard.tsx
│   │   │   ├── AlertsDashboard.tsx
│   │   │   └── BenchmarkingDashboard.tsx
│   │   │
│   │   └── filters/          # Componentes de filtrado
│   │       ├── SourceFilter.tsx
│   │       ├── CareerFilter.tsx
│   │       └── SeverityFilter.tsx
│   │
│   ├── contexts/             # Contextos React
│   │   ├── AuthContext.tsx
│   │   ├── FilterContext.tsx
│   │   └── ThemeContext.tsx
│   │
│   ├── hooks/               # Hooks personalizados
│   │   ├── useDebounce.ts
│   │   ├── useLocalStorage.ts
│   │   └── useApi.ts
│   │
│   ├── pages/               # Páginas principales
│   │   ├── Login.tsx
│   │   ├── DashboardLayout.tsx
│   │   └── NotFound.tsx
│   │
│   ├── services/            # Servicios API
│   │   ├── api.ts
│   │   ├── authService.ts
│   │   ├── sentimentService.ts
│   │   ├── reputationService.ts
│   │   ├── alertsService.ts
│   │   └── benchmarkingService.ts
│   │
│   ├── types/               # Tipos TypeScript
│   │   └── index.ts
│   │
│   ├── utils/               # Utilidades
│   │   ├── dateHelpers.ts
│   │   └── formatters.ts
│   │
│   ├── __tests__/           # Tests
│   │
│   ├── App.tsx              # Componente raíz
│   ├── main.tsx             # Entry point
│   └── index.css            # Estilos globales
│
├── public/
├── package.json
├── tsconfig.json
├── vite.config.ts
└── jest.config.ts
```

---

## 📊 Dashboards Disponibles

### 1. Dashboard de Sentimiento
- **Ruta:** `/dashboard/sentiment`
- **Funcionalidades:**
  - Gráfico de tendencia temporal (positivo/negativo/neutral)
  - Distribución de sentimiento en gráfico de dona
  - KPIs: % positivo, índice de satisfacción, total de posts
  - Lista de posts más relevantes con tabs por sentimiento
  - Exportación a PNG/Excel/PDF

### 2. Dashboard de Reputación
- **Ruta:** `/dashboard/reputation`
- **Funcionalidades:**
  - Word Cloud de términos frecuentes
  - Clusters de tópicos identificados
  - Mapa de calor día/hora de actividad
  - Comparación con competidores
  - Métricas de reputación institucional

### 3. Dashboard de Alertas
- **Ruta:** `/dashboard/alerts`
- **Funcionalidades:**
  - Tabla paginada de alertas con filtros
  - Estadísticas por severidad (crítica/alta/media/baja)
  - Resolución de alertas con diálogos
  - Cards de alertas recientes
  - Distribución de severidad en gráfico

### 4. Dashboard de Benchmarking
- **Ruta:** `/dashboard/benchmarking`
- **Funcionalidades:**
  - Ranking de carreras por métricas
  - Gráfico radar de comparación multi-carrera
  - Matriz de correlación entre variables
  - Toggle entre vista de gráfico y tabla
  - Selección de métricas para comparar

---

## 🎨 Tema Institucional EMI

```typescript
// Colores principales
primary: '#1B5E20'    // Verde EMI
secondary: '#FFD700'  // Dorado EMI

// Paleta de sentimiento
positive: '#4CAF50'   // Verde
negative: '#F44336'   // Rojo
neutral: '#9E9E9E'    // Gris

// Severidad de alertas
critical: '#B71C1C'   // Rojo oscuro
high: '#E65100'       // Naranja
medium: '#F9A825'     // Amarillo
low: '#2E7D32'        // Verde
```

---

## 🔐 Autenticación

El sistema utiliza autenticación JWT:

```typescript
// Login
POST /api/auth/login
Body: { email: string, password: string }
Response: { token: string, refreshToken: string, user: User }

// Refresh Token
POST /api/auth/refresh
Body: { refreshToken: string }
Response: { token: string }
```

Los tokens se almacenan en `localStorage` y se incluyen automáticamente en las peticiones via interceptor de Axios.

---

## 🔧 Variables de Entorno

Crear archivo `.env` en la raíz del frontend:

```env
VITE_API_URL=http://localhost:8000/api
VITE_APP_NAME=Sistema OSINT EMI
VITE_APP_VERSION=1.0.0
```

---

## 📱 Responsive Design

El sistema está optimizado para:
- **Desktop:** 1920px - 1280px
- **Tablet:** 1024px - 768px
- **Mobile:** 767px - 320px

El Sidebar se colapsa automáticamente en pantallas pequeñas.

---

## ⚡ Performance

### Métricas objetivo:
- **Tiempo de carga inicial:** < 3 segundos
- **Respuesta de filtros:** < 500ms
- **Cobertura de tests:** ≥ 70%

### Optimizaciones implementadas:
- Lazy loading de rutas y dashboards
- Code splitting por módulo
- Debounce en filtros de búsqueda
- Memoización de componentes pesados
- Skeleton loading states

---

## 🧪 Testing

```bash
# Ejecutar todos los tests
npm test

# Ejecutar con cobertura
npm run test:coverage

# Ejecutar en modo watch
npm run test:watch

# Ejecutar un archivo específico
npm test -- KPICard.test.tsx
```

### Estructura de tests:
```
src/__tests__/
├── components/
│   ├── KPICard.test.tsx
│   ├── common.test.tsx
│   ├── filters.test.tsx
│   └── charts.test.tsx
├── contexts/
│   └── contexts.test.tsx
├── hooks/
│   └── hooks.test.ts
├── services/
│   ├── sentimentService.test.ts
│   ├── alertsService.test.ts
│   ├── benchmarkingService.test.ts
│   └── reputationService.test.ts
└── utils/
    └── dateHelpers.test.ts
```

---

## 📤 Exportación

Los dashboards soportan exportación en múltiples formatos:

| Formato | Librería | Descripción |
|---------|----------|-------------|
| PNG | html2canvas | Captura visual del dashboard |
| Excel | xlsx | Datos tabulados con formato |
| PDF | jsPDF | Reporte completo con gráficos |

---

## 🚀 Despliegue

### Desarrollo
```bash
npm run dev
```

### Producción
```bash
npm run build
npm run preview
```

### Docker
```bash
docker build -t emi-frontend .
docker run -p 80:80 emi-frontend
```

---

## 📚 API Endpoints

### Sentimiento
- `GET /api/sentiment/trend` - Tendencia temporal
- `GET /api/sentiment/distribution` - Distribución
- `GET /api/sentiment/posts` - Posts más relevantes
- `POST /api/sentiment/analyze` - Analizar textos

### Reputación
- `GET /api/reputation/wordcloud` - Nube de palabras
- `GET /api/reputation/topics` - Tópicos
- `GET /api/reputation/heatmap` - Mapa de calor
- `GET /api/reputation/competitors` - Competidores

### Alertas
- `GET /api/alerts` - Lista de alertas
- `GET /api/alerts/:id` - Detalle de alerta
- `PUT /api/alerts/:id/resolve` - Resolver alerta
- `GET /api/alerts/stats` - Estadísticas

### Benchmarking
- `GET /api/benchmarking/ranking` - Ranking de carreras
- `GET /api/benchmarking/correlations` - Correlaciones
- `GET /api/benchmarking/radar` - Perfil radar

---

## 👥 Equipo

**Proyecto:** Sistema de Inteligencia OSINT  
**Institución:** Escuela Militar de Ingeniería (EMI)  
**Sprint:** 4 - Módulo de Dashboards Interactivos

---

## 📄 Licencia

Proyecto desarrollado para el Vicerrectorado de la EMI Bolivia.
Todos los derechos reservados.
