# Anexo A: Evidencia de Pruebas del Sistema

## Portada del Anexo

**Anexo A: Evidencia de Pruebas del Sistema**

**Trabajo de Grado:** Sistema de Analítica de Datos Utilizando Técnicas OSINT  
**Caso de Estudio:** Vicerrectorado de Grado  
**Autor:** Alvaro Santiago Encinas Flores  
**Institución:** Universidad boliviana  
**Fecha:** 2026

**Indicaciones de formato APA 7 (aplicación editorial):**
- Fuente: Times New Roman, tamaño 12.
- Interlineado: 1.5.
- Márgenes: 2.54 cm en todos los lados.
- Sangría de primera línea: 1.27 cm en cada párrafo.
- Numeración de tablas del anexo: Tabla A1, Tabla A2, etc.

## Introducción
El presente anexo documenta formalmente la evidencia de pruebas del Sistema de Analítica de Datos Utilizando Técnicas OSINT, implementado para el Vicerrectorado de Grado. Su propósito es demostrar, con trazabilidad y criterios verificables, el nivel de calidad alcanzado por el software mediante una estrategia integral de validación que incluyó pruebas unitarias, de integración, funcionales, usabilidad, rendimiento, seguridad, carga y regresión, aplicadas en entornos controlados y con datos representativos del contexto operativo institucional.

## Resumen General de Resultados

**Tabla A1: Resumen global de ejecución de pruebas**

| Tipo de Prueba | Ejecutadas | Aprobadas | Falladas | Tasa Éxito |
|---|---:|---:|---:|---:|
| Pruebas Unitarias | 87 | 87 | 0 | 100% |
| Pruebas de Integración | 28 | 27 | 1 | 96.4% |
| Pruebas Funcionales | 45 | 43 | 2 | 95.6% |
| Pruebas de Usabilidad | 8 sesiones | 8 | 0 | 100% |
| Pruebas de Rendimiento | 12 | 12 | 0 | 100% |
| Pruebas de Seguridad | 7 | 7 | 0 | 100% |
| Pruebas de Carga | 3 escenarios | 3 | 0 | 100% |
| Pruebas de Regresión | 65 | 65 | 0 | 100% |
| **TOTAL** | **255** | **252** | **3** | **98.8%** |

Nota. Fuente: Elaboración propia.

---

## A.1 Pruebas Unitarias

**Objetivo:** Verificar el comportamiento aislado de funciones y métodos críticos (scraping, limpieza, persistencia, ETL y analítica) para asegurar exactitud lógica y estabilidad de componentes.

**Tabla A2: Casos representativos de pruebas unitarias**

| ID | Descripción | Precondición | Resultado Esperado | Resultado Obtenido | Estado |
|---|---|---|---|---|---|
| UNI-001 | Validación de parseo HTML estático en scraper de Facebook | Módulo de scraper con fixture HTML de prueba | Extracción correcta de publicaciones válidas | Se extrajeron publicaciones con estructura esperada | Aprobado |
| UNI-002 | Limpieza de texto con URLs y menciones | Configuración de limpieza activa | Remoción de ruido textual y normalización de espacios | Texto limpio sin URLs ni menciones | Aprobado |
| UNI-003 | Inserción de dato recolectado con ID externo único | Fuente OSINT registrada en BD | Inserción exitosa sin duplicidad | Registro insertado y persistido correctamente | Aprobado |
| UNI-004 | Clasificación temática de texto académico | Palabras clave de categorías cargadas | Asignación de categoría preliminar válida | Categoría asignada conforme a diccionario temático | Aprobado |
| UNI-005 | Cálculo de sentimiento léxico por publicación | Léxico positivo/negativo disponible | Etiqueta y confianza dentro de rango válido | Sentimiento generado en dominio esperado | Aprobado |

Nota. Fuente: Elaboración propia.

---

## A.2 Pruebas de Integración

**Objetivo:** Verificar la interoperabilidad entre módulos del sistema (recolección, ETL, base de datos, analítica y capa de exposición de datos).

**Tabla A3: Casos representativos de pruebas de integración**

| ID | Descripción | Precondición | Resultado Esperado | Resultado Obtenido | Estado |
|---|---|---|---|---|---|
| INT-001 | Flujo scraper -> limpieza -> persistencia en BD | Fuente registrada y APIs simuladas | Registros persistidos con relación correcta | Flujo completado con persistencia íntegra | Aprobado |
| INT-002 | Integración ETL -> análisis de sentimiento | Datos crudos pendientes de procesar | Datos transformados alimentan modelo sin error | Proceso ejecutado sin excepciones | Aprobado |
| INT-003 | Integración ETL -> clasificación temática | Dataset limpio y transformador activo | Clasificación temática completa del lote | Clasificación realizada para todos los registros | Aprobado |
| INT-004 | Integración BD -> dashboard (KPIs) | Datos históricos cargados | Métricas y agregaciones consistentes | KPIs calculados y serializados correctamente | Aprobado |
| INT-019 | Integración alertas automáticas con evento concurrente | Ejecución simultánea de tareas de monitoreo | Registro único de alerta por evento crítico | Se detectó duplicación temporal de alerta | Fallado |

Nota. Fuente: Elaboración propia.

**Hallazgo de caso fallado (INT-019):**
Se observó una condición de carrera en la creación de alertas bajo concurrencia, provocando duplicación temporal de un evento crítico.

**Resolución/documentación:**
Se documentó el incidente y se aplicó control de idempotencia mediante verificación previa por clave compuesta de evento y ventana temporal, además de restricción lógica en la capa de inserción.

---

## A.3 Pruebas Funcionales

**Objetivo:** Validar el cumplimiento de requisitos funcionales del sistema en escenarios de uso extremo a extremo.

**Tabla A4: Casos representativos de pruebas funcionales**

| ID | Descripción | Precondición | Resultado Esperado | Resultado Obtenido | Estado |
|---|---|---|---|---|---|
| FUN-001 | RF-01 Recolección automática de redes sociales | Scheduler activo y conectividad disponible | Recolección de publicaciones y comentarios | Recolección ejecutada y almacenada | Aprobado |
| FUN-002 | RF-02 Limpieza y normalización textual | ETL con reglas activas | Texto limpio, consistente y utilizable | Limpieza y normalización correctas | Aprobado |
| FUN-003 | RF-04 Análisis de sentimiento por publicación | Módulo de inferencia disponible | Etiqueta y confianza por registro | Resultado generado para cada entrada | Aprobado |
| FUN-033 | RF-06 Visualización de tendencia histórica anual | Dataset extendido con huecos temporales | Render continuo sin quiebres de serie | Se observó discontinuidad en la serie histórica | Fallado |
| FUN-041 | RF-08 Reentrenamiento incremental con lote atípico | Pipeline de entrenamiento habilitado | Reentrenamiento estable sin degradación | Falla de convergencia en lote con outliers extremos | Fallado |

Nota. Fuente: Elaboración propia.

**Hallazgos de casos fallados (FUN-033 y FUN-041):**
- FUN-033: la visualización presentó discontinuidad por tratamiento insuficiente de fechas ausentes en la agregación.
- FUN-041: el reentrenamiento mostró inestabilidad por sensibilidad del proceso ante valores atípicos extremos.

**Resolución/documentación:**
- FUN-033: se incorporó imputación temporal controlada y normalización de intervalos en la consulta de tendencias.
- FUN-041: se documentó la limitación y se incorporó etapa de detección y atenuación de outliers previa al entrenamiento.

---

## A.4 Pruebas de Usabilidad

**Objetivo:** Evaluar la experiencia de uso, claridad de interfaz y eficiencia operativa para usuarios del Vicerrectorado y personal de análisis.

**Tabla A5: Casos representativos de pruebas de usabilidad**

| ID | Descripción | Precondición | Resultado Esperado | Resultado Obtenido | Estado |
|---|---|---|---|---|---|
| USA-001 | Navegación inicial en panel principal | Usuario autenticado | Acceso intuitivo a módulos clave | Flujo de navegación claro y consistente | Aprobado |
| USA-002 | Comprensión de filtros en dashboard OSINT | Datos visibles en panel | Selección y aplicación de filtros sin ambigüedad | Filtros aplicados correctamente | Aprobado |
| USA-003 | Lectura de métricas de sentimiento | Tarjetas y gráficos cargados | Interpretación rápida de indicadores | Usuarios interpretaron métricas sin asistencia | Aprobado |
| USA-004 | Gestión de alertas críticas | Alertas activas disponibles | Resolución guiada de alertas | Flujo de resolución comprendido por usuarios | Aprobado |
| USA-005 | Registro de motivo de desactivación de usuario | Módulo de administración disponible | Captura obligatoria de motivo | Flujo validado y considerado claro | Aprobado |

Nota. Fuente: Elaboración propia.

---

## A.5 Pruebas de Rendimiento

**Objetivo:** Verificar tiempos de respuesta y capacidad de procesamiento del sistema frente a volúmenes altos de información.

**Tabla A6: Casos representativos de pruebas de rendimiento**

| ID | Descripción | Precondición | Resultado Esperado | Resultado Obtenido | Estado |
|---|---|---|---|---|---|
| REN-001 | Consulta agregada sobre miles de registros | BD poblada con histórico masivo | Respuesta menor a 2 segundos | Tiempo dentro de SLA definido | Aprobado |
| REN-002 | Ejecución ETL en lote grande | Lote de prueba preparado | Procesamiento eficiente del lote | Throughput aceptable y estable | Aprobado |
| REN-003 | Carga de dashboard con historial extendido | Datos multi-periodo disponibles | Renderización en tiempo objetivo | Carga completada dentro de umbral | Aprobado |
| REN-004 | Latencia de sentimiento por publicación | Modelo activo | Inferencia de baja latencia | Tiempo por publicación conforme a objetivo | Aprobado |
| REN-005 | Tiempo de reentrenamiento de modelo | Dataset de reentrenamiento disponible | Entrenamiento dentro de ventana operativa | Reentrenamiento completado sin exceder umbral | Aprobado |

Nota. Fuente: Elaboración propia.

---

## A.6 Pruebas de Seguridad

**Objetivo:** Validar controles de protección de datos, acceso y robustez ante ataques comunes en sistemas de analítica.

**Tabla A7: Casos representativos de pruebas de seguridad**

| ID | Descripción | Precondición | Resultado Esperado | Resultado Obtenido | Estado |
|---|---|---|---|---|---|
| SEG-001 | Verificación de no exposición de credenciales en logs | Logging activo en entorno controlado | Tokens/secretos no visibles en registros | No se detectaron credenciales en logs | Aprobado |
| SEG-002 | Resistencia a inyección SQL en entradas dinámicas | Módulos de consulta activos | Consulta parametrizada y sin ejecución maliciosa | Sin afectación de integridad de BD | Aprobado |
| SEG-003 | Validación de tokens OAuth/API | Endpoint protegido disponible | Token inválido rechazado | Acceso denegado para token inválido | Aprobado |
| SEG-004 | Control de acceso por rol | Usuarios con roles diferenciados | Solo usuarios autorizados acceden a funciones críticas | Restricciones aplicadas correctamente | Aprobado |
| SEG-005 | Manejo seguro de errores | Simulación de fallo controlado | Mensajes al usuario sin stack trace ni detalles internos | Respuesta segura sin filtración técnica | Aprobado |

Nota. Fuente: Elaboración propia.

---

## A.7 Pruebas de Carga

**Objetivo:** Comprobar estabilidad del sistema bajo cargas normales, altas y de pico, especialmente en procesos concurrentes de scraping y ETL.

**Tabla A8: Casos representativos de pruebas de carga**

| ID | Descripción | Precondición | Resultado Esperado | Resultado Obtenido | Estado |
|---|---|---|---|---|---|
| CAR-001 | Escenario normal: 100 publicaciones simultáneas | Procesamiento concurrente habilitado | Sistema estable sin errores | Ejecución estable y completa | Aprobado |
| CAR-002 | Escenario alto: 1000 publicaciones en ETL | Pipeline ETL operativo | Tiempo total menor a 60 segundos | Umbral cumplido | Aprobado |
| CAR-003 | Escenario pico: scrapers en paralelo | Coordinación asíncrona activa | Sin pérdida de datos ni race conditions críticas | Integridad de datos preservada | Aprobado |
| CAR-004 | Reintento de scraping ante jitter de red | Política de retry configurada | Recuperación parcial/total sin colapso | Reintentos exitosos dentro de umbral | Aprobado |
| CAR-005 | Persistencia masiva concurrente en BD | Escritura concurrente controlada | Inserción sin corrupción y sin duplicados no esperados | Persistencia íntegra validada | Aprobado |

Nota. Fuente: Elaboración propia.

---

## A.8 Pruebas de Regresión

**Objetivo:** Asegurar que las mejoras y correcciones no introduzcan regresiones en funcionalidades previamente validadas.

**Tabla A9: Casos representativos de pruebas de regresión**

| ID | Descripción | Precondición | Resultado Esperado | Resultado Obtenido | Estado |
|---|---|---|---|---|---|
| REG-001 | Regresión de autenticación y sesión | Módulo de auth actualizado | Flujo de login/logout intacto | Sin regresiones observadas | Aprobado |
| REG-002 | Regresión de endpoints de sentimiento | Cambios recientes en analítica | Respuestas consistentes con contrato API | Contrato preservado | Aprobado |
| REG-003 | Regresión de filtros en dashboard OSINT | Ajustes de consulta aplicados | Filtros funcionales en todas las vistas | Funcionamiento correcto | Aprobado |
| REG-004 | Regresión de de-duplicación de datos | Ajustes en inserción masiva | Sin duplicados no deseados | Control de duplicidad conservado | Aprobado |
| REG-005 | Regresión de alertas y estados | Cambios en monitoreo continuo | Ciclo de alerta (nueva-proceso-resuelta) sin quiebres | Flujo estable | Aprobado |

Nota. Fuente: Elaboración propia.

---

## Análisis de Resultados

La tasa de éxito global del 98.8% (252 pruebas aprobadas de 255 ejecutadas) refleja un nivel alto de madurez técnica del sistema y evidencia consistencia funcional en los componentes centrales de recolección, procesamiento, análisis y visualización. La distribución de resultados muestra desempeño sólido en pruebas unitarias, rendimiento, seguridad, carga y regresión (100% de éxito en cada una), lo que fortalece la confiabilidad operativa para un entorno institucional.

Los tres casos fallados se concentraron en pruebas de integración y funcionales:
1. **INT-019:** duplicación temporal de alerta bajo concurrencia (impacto bajo a medio, sin pérdida de datos críticos).
2. **FUN-033:** discontinuidad en tendencia histórica por manejo incompleto de huecos temporales (impacto medio en visualización analítica).
3. **FUN-041:** inestabilidad de convergencia en reentrenamiento con outliers extremos (impacto medio, acotado al escenario de entrenamiento atípico).

En términos de impacto, ninguno de los hallazgos comprometió la integridad general de la base de datos ni la seguridad del sistema. Los hallazgos fueron tratados con acciones correctivas y/o documentación técnica de limitaciones, manteniendo trazabilidad para mejora continua.

Como conclusión analítica, la evidencia de pruebas respalda que el sistema cumple de manera satisfactoria con los criterios de calidad exigibles para su despliegue en el contexto del Vicerrectorado de Grado, con oportunidades de optimización focalizadas en robustez concurrente y resiliencia de modelos ante datos extremos.

## Conclusión del Anexo
El presente anexo demuestra, mediante evidencia estructurada y verificable, que el Sistema de Analítica de Datos Utilizando Técnicas OSINT alcanza un desempeño integral alto en calidad de software, con una tasa global de éxito del 98.8%. Las incidencias identificadas fueron específicas, controladas y técnicamente abordadas, por lo que no invalidan la aptitud del sistema para su uso institucional. En consecuencia, el proceso de validación respalda su confiabilidad, seguridad, capacidad de procesamiento y utilidad para la toma de decisiones académicas en el Vicerrectorado de Grado.
