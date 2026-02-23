/**
 * Dashboard de Ayuda del Sistema
 * SADUTO - Sistema de Analisis de Datos Universitarios con Tecnicas OSINT
 * EMI Bolivia
 */

import React, { useState } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Chip,
  Divider,
  Paper,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Tabs,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Alert,
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  Help as HelpIcon,
  TravelExplore as OSINTIcon,
  SentimentSatisfied as SentimentIcon,
  Stars as ReputationIcon,
  Warning as AlertsIcon,
  BarChart as BenchmarkingIcon,
  Psychology as NLPIcon,
  FactCheck as EvaluacionIcon,
  Forum as PostsIcon,
  Settings as SettingsIcon,
  PeopleAlt as UsersIcon,
  Security as SecurityIcon,
  Speed as SpeedIcon,
  SmartToy as AIIcon,
  CheckCircle as CheckIcon,
  Info as InfoIcon,
  School as SchoolIcon,
} from '@mui/icons-material';
import { useAuth } from '../../contexts';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;
  return (
    <div role="tabpanel" hidden={value !== index} {...other}>
      {value === index && <Box sx={{ pt: 3 }}>{children}</Box>}
    </div>
  );
}

const AyudaDashboard: React.FC = () => {
  const { user } = useAuth();
  const [tabValue, setTabValue] = useState(0);

  const rolLabels: Record<string, string> = {
    administrador: 'Administrador del Sistema',
    vicerrector: 'Vicerrector / Jefe',
    uebu: 'Usuario UEBU',
  };

  const modules = [
    {
      icon: <OSINTIcon color="primary" />,
      name: 'Inteligencia OSINT',
      path: '/dashboard/osint',
      roles: ['administrador', 'vicerrector'],
      description: 'Panel central de tecnicas OSINT multifuente. Incluye SOCMINT (redes sociales), NEWSINT (noticias), TRENDINT (tendencias) y clasificacion tematica con identificacion de patrones.',
      features: [
        'Ejecucion de recoleccion OSINT completa (4 tecnicas)',
        'Patrones identificados con recomendaciones',
        'Clasificacion tematica automatica (12 categorias)',
        'Monitoreo de noticias via Google News RSS',
        'Analisis de intereses academicos (UEBU)',
      ],
    },
    {
      icon: <PostsIcon color="primary" />,
      name: 'Posts y Comentarios',
      path: '/dashboard/posts',
      roles: ['administrador', 'vicerrector'],
      description: 'Visualizacion y exploracion de todos los datos recolectados de Facebook y TikTok. Permite filtrar, buscar y analizar publicaciones y comentarios individuales.',
      features: [
        'Tabla interactiva de posts con paginacion',
        'Filtros por plataforma, fecha y sentimiento',
        'Detalles de engagement (likes, comentarios, compartidos)',
        'Comentarios asociados a cada publicacion',
        'Exportacion de datos',
      ],
    },
    {
      icon: <SentimentIcon color="primary" />,
      name: 'Analisis de Sentimientos',
      path: '/dashboard/sentiment',
      roles: ['administrador', 'vicerrector', 'uebu'],
      description: 'Analisis de sentimientos usando el modelo BETO (Bidirectional Encoder Representations from Transformers) fine-tuned en espanol. Clasificacion en Positivo, Negativo y Neutro con alta confianza.',
      features: [
        'Modelo BETO fine-tuned en dataset TASS (espanol)',
        'Distribucion de sentimientos (pie chart)',
        'Evolucion temporal de sentimientos',
        'Confianza promedio del modelo (94-99%)',
        'Comparativa por plataforma',
      ],
    },
    {
      icon: <ReputationIcon color="primary" />,
      name: 'Reputacion',
      path: '/dashboard/reputation',
      roles: ['administrador', 'vicerrector', 'uebu'],
      description: 'Indice de reputacion digital de la EMI calculado a partir del analisis de sentimientos, engagement y volumen de publicaciones.',
      features: [
        'Score de reputacion en tiempo real',
        'Tendencia historica',
        'Factores que afectan la reputacion',
        'Comparativa entre plataformas',
      ],
    },
    {
      icon: <AlertsIcon sx={{ color: '#f57c00' }} />,
      name: 'Alertas y Anomalias',
      path: '/dashboard/alerts',
      roles: ['administrador', 'vicerrector', 'uebu'],
      description: 'Sistema de alertas inteligente que detecta anomalias usando Isolation Forest, picos de engagement, sentimientos negativos criticos y cambios de reputacion.',
      features: [
        'Deteccion de anomalias con Isolation Forest (ML)',
        'Alertas por severidad (critica, alta, media, baja)',
        'Notificaciones en tiempo real en el navbar',
        'Flujo de trabajo: nueva -> en proceso -> resuelta',
        'Historial completo de alertas',
      ],
    },
    {
      icon: <BenchmarkingIcon color="primary" />,
      name: 'Benchmarking',
      path: '/dashboard/benchmarking',
      roles: ['administrador', 'vicerrector', 'uebu'],
      description: 'Analisis comparativo entre carreras de la EMI. Correlaciones estadisticas, perfiles por carrera y tendencias de engagement.',
      features: [
        'Correlaciones de Pearson entre metricas',
        'Perfiles individuales por carrera',
        'Tendencias de engagement por carrera',
        'Comparativa lado a lado entre carreras',
        'Matriz de correlaciones visual',
      ],
    },
    {
      icon: <NLPIcon color="primary" />,
      name: 'IA / ML / NLP',
      path: '/dashboard/nlp',
      roles: ['administrador', 'vicerrector', 'uebu'],
      description: 'Pipeline completo de procesamiento de lenguaje natural. Keywords (TF-IDF), modelado de topicos (LDA), clustering (K-Means) y reconocimiento de entidades nombradas (NER).',
      features: [
        'Extraccion de keywords con TF-IDF',
        'Modelado de topicos con LDA (Latent Dirichlet Allocation)',
        'Clustering de documentos con K-Means + PCA',
        'NER: reconocimiento de entidades nombradas',
        'Nube de palabras interactiva',
      ],
    },
    {
      icon: <EvaluacionIcon color="primary" />,
      name: 'Evaluacion del Sistema',
      path: '/dashboard/evaluacion',
      roles: ['administrador', 'vicerrector'],
      description: 'Panel de evaluacion integral del sistema SADUTO. Muestra metricas de rendimiento, completitud de datos, calidad de los modelos de IA y estado general del sistema.',
      features: [
        'Score general del sistema (actualmente 95.2%)',
        'Metricas por componente (recoleccion, procesamiento, IA)',
        'Estado de salud de la base de datos',
        'Benchmarks de rendimiento',
      ],
    },
  ];

  const faqs = [
    {
      q: 'Que es SADUTO?',
      a: 'SADUTO (Sistema de Analisis de Datos Universitarios con Tecnicas OSINT) es una plataforma desarrollada para la Escuela Militar de Ingenieria (EMI) de Bolivia. Recopila y analiza datos de redes sociales (Facebook, TikTok) usando tecnicas OSINT, inteligencia artificial y procesamiento de lenguaje natural para apoyar la toma de decisiones del Vicerrectorado.',
    },
    {
      q: 'Que modelo de IA se usa para el analisis de sentimientos?',
      a: 'Se utiliza BETO (finiteautomata/beto-sentiment-analysis), un modelo basado en BERT pre-entrenado en espanol y fine-tuned en el dataset TASS para analisis de sentimientos. Tiene ~110 millones de parametros y alcanza una confianza promedio del 94-99% en nuestros datos.',
    },
    {
      q: 'De donde se extraen los datos?',
      a: 'Los datos se recolectan mediante web scraping etico de paginas publicas de Facebook (pagina oficial de la EMI) y TikTok (@abordemilitar). Adicionalmente, el modulo OSINT recolecta noticias de Google News RSS y analiza tendencias de busqueda.',
    },
    {
      q: 'Que significa cada nivel de severidad en las alertas?',
      a: 'Critica: requiere atencion inmediata (ej. sentimiento muy negativo con alta confianza). Alta: importante pero no urgente. Media: informativa, para seguimiento. Baja: registrada para historico.',
    },
    {
      q: 'Como funciona la deteccion de anomalias?',
      a: 'Se utiliza el algoritmo Isolation Forest, un metodo de machine learning no supervisado que detecta puntos de datos que "se aislan" facilmente del resto. Se aplica sobre metricas de engagement para identificar publicaciones con comportamiento inusual.',
    },
    {
      q: 'Que tecnicas NLP se aplican?',
      a: 'El pipeline NLP incluye: TF-IDF para extraccion de palabras clave, LDA (Latent Dirichlet Allocation) para modelado de topicos, K-Means con reduccion PCA para clustering de documentos, y reconocimiento de entidades nombradas (NER) con spaCy.',
    },
    {
      q: 'Que es el Benchmarking de carreras?',
      a: 'Es un modulo que compara el rendimiento en redes sociales de las distintas carreras de la EMI usando correlaciones estadisticas de Pearson, perfiles individuales y tendencias temporales para identificar patrones de interes.',
    },
    {
      q: 'Con que frecuencia se actualizan los datos?',
      a: 'Los datos pueden actualizarse manualmente mediante el boton "Ejecutar OSINT Completo" en el panel de Inteligencia OSINT. El scraping de redes sociales se ejecuta bajo demanda desde la interfaz.',
    },
  ];

  const techStack = [
    { category: 'Backend', items: 'Python 3.13, Flask, SQLite3' },
    { category: 'Frontend', items: 'React 18, TypeScript, Material UI 5, Vite' },
    { category: 'IA/ML', items: 'BETO (HuggingFace Transformers), Isolation Forest (scikit-learn), scipy.stats' },
    { category: 'NLP', items: 'TF-IDF, LDA (gensim), K-Means, spaCy (NER)' },
    { category: 'Scraping', items: 'Selenium, BeautifulSoup, Requests' },
    { category: 'Graficos', items: 'Recharts, Lucide React' },
    { category: 'Hardware', items: 'Apple Silicon (MPS) para inferencia de modelos' },
  ];

  const userRole = user?.rol || 'uebu';
  const visibleModules = modules.filter(m => m.roles.includes(userRole));

  return (
    <Box>
      <Typography variant="h4" component="h1" fontWeight={600} sx={{ mb: 1 }}>
        Centro de Ayuda
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        Documentacion y guia de uso del sistema SADUTO
      </Typography>

      <Alert severity="info" sx={{ mb: 3 }}>
        Sesion activa como <strong>{user?.name || user?.username}</strong> con rol{' '}
        <Chip label={rolLabels[userRole] || userRole} size="small" color="primary" sx={{ mx: 0.5 }} />.
        {userRole === 'uebu' && ' Algunas secciones del sistema no estan disponibles para tu rol.'}
        {userRole === 'vicerrector' && ' Tienes acceso a todos los dashboards y configuracion.'}
        {userRole === 'administrador' && ' Tienes acceso completo a todas las funcionalidades.'}
      </Alert>

      <Tabs value={tabValue} onChange={(_, v) => setTabValue(v)} sx={{ mb: 1 }}>
        <Tab icon={<HelpIcon />} label="Modulos del Sistema" iconPosition="start" />
        <Tab icon={<InfoIcon />} label="Preguntas Frecuentes" iconPosition="start" />
        <Tab icon={<AIIcon />} label="Tecnologias" iconPosition="start" />
        <Tab icon={<SecurityIcon />} label="Roles y Permisos" iconPosition="start" />
      </Tabs>

      {/* Tab: Modulos */}
      <TabPanel value={tabValue} index={0}>
        <Grid container spacing={2}>
          {visibleModules.map((mod) => (
            <Grid item xs={12} md={6} key={mod.path}>
              <Card sx={{ height: '100%' }}>
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
                    {mod.icon}
                    <Typography variant="h6" fontWeight={600}>
                      {mod.name}
                    </Typography>
                  </Box>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    {mod.description}
                  </Typography>
                  <Divider sx={{ mb: 1.5 }} />
                  <Typography variant="caption" fontWeight={600} color="text.secondary" sx={{ mb: 1, display: 'block' }}>
                    FUNCIONALIDADES
                  </Typography>
                  <List dense disablePadding>
                    {mod.features.map((feat, i) => (
                      <ListItem key={i} disablePadding sx={{ py: 0.2 }}>
                        <ListItemIcon sx={{ minWidth: 28 }}>
                          <CheckIcon sx={{ fontSize: 16, color: 'success.main' }} />
                        </ListItemIcon>
                        <ListItemText
                          primary={feat}
                          primaryTypographyProps={{ variant: 'body2' }}
                        />
                      </ListItem>
                    ))}
                  </List>
                  <Box sx={{ mt: 1.5, display: 'flex', gap: 0.5 }}>
                    {mod.roles.map((r) => (
                      <Chip
                        key={r}
                        label={r}
                        size="small"
                        variant="outlined"
                        color={r === 'administrador' ? 'error' : r === 'vicerrector' ? 'warning' : 'info'}
                        sx={{ fontSize: '0.65rem', height: 20 }}
                      />
                    ))}
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      </TabPanel>

      {/* Tab: FAQ */}
      <TabPanel value={tabValue} index={1}>
        {faqs.map((faq, i) => (
          <Accordion key={i} defaultExpanded={i === 0}>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography fontWeight={600}>{faq.q}</Typography>
            </AccordionSummary>
            <AccordionDetails>
              <Typography variant="body2" color="text.secondary">
                {faq.a}
              </Typography>
            </AccordionDetails>
          </Accordion>
        ))}
      </TabPanel>

      {/* Tab: Tecnologias */}
      <TabPanel value={tabValue} index={2}>
        <Card>
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
              <SpeedIcon color="primary" />
              <Typography variant="h6" fontWeight={600}>
                Stack Tecnologico
              </Typography>
            </Box>
            <TableContainer component={Paper} variant="outlined">
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell sx={{ fontWeight: 600 }}>Componente</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>Tecnologias</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {techStack.map((row) => (
                    <TableRow key={row.category} hover>
                      <TableCell>
                        <Chip label={row.category} size="small" color="primary" variant="outlined" />
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">{row.items}</Typography>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>

            <Box sx={{ mt: 3 }}>
              <Typography variant="subtitle2" fontWeight={600} gutterBottom>
                Arquitectura del Sistema
              </Typography>
              <Paper variant="outlined" sx={{ p: 2, fontFamily: 'monospace', fontSize: '0.8rem', bgcolor: 'grey.50' }}>
                <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>
{`Navegador (React + MUI)
    |
    v
Vite Dev Server (:3000) --proxy--> Flask API (:5001)
                                        |
                                  +-----------+
                                  |  SQLite3  |
                                  | osint_emi |
                                  +-----------+
                                        |
                          +-------------+-------------+
                          |             |             |
                        BETO      Isolation     NLP Pipeline
                     (Sentiment)   Forest      (TF-IDF, LDA,
                                 (Anomalies)   K-Means, NER)
                          |             |             |
                    HuggingFace   scikit-learn   gensim + spaCy
                   Transformers`}
                </pre>
              </Paper>
            </Box>

            <Box sx={{ mt: 3 }}>
              <Typography variant="subtitle2" fontWeight={600} gutterBottom>
                Sobre el Proyecto
              </Typography>
              <Typography variant="body2" color="text.secondary">
                SADUTO fue desarrollado como proyecto de grado para la Escuela Militar de Ingenieria (EMI) de Bolivia,
                con el objetivo de proporcionar al Vicerrectorado herramientas avanzadas de analisis de datos
                provenientes de redes sociales usando tecnicas OSINT (Open Source Intelligence), inteligencia
                artificial y procesamiento de lenguaje natural.
              </Typography>
            </Box>
          </CardContent>
        </Card>
      </TabPanel>

      {/* Tab: Roles y Permisos */}
      <TabPanel value={tabValue} index={3}>
        <Card>
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
              <SecurityIcon color="primary" />
              <Typography variant="h6" fontWeight={600}>
                Matriz de Permisos por Rol
              </Typography>
            </Box>
            <TableContainer component={Paper} variant="outlined">
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell sx={{ fontWeight: 600 }}>Seccion</TableCell>
                    <TableCell align="center" sx={{ fontWeight: 600 }}>
                      <Chip label="Administrador" size="small" color="error" />
                    </TableCell>
                    <TableCell align="center" sx={{ fontWeight: 600 }}>
                      <Chip label="Vicerrector" size="small" color="warning" />
                    </TableCell>
                    <TableCell align="center" sx={{ fontWeight: 600 }}>
                      <Chip label="UEBU" size="small" color="info" />
                    </TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {[
                    { section: 'Inteligencia OSINT', admin: true, vice: true, uebu: false },
                    { section: 'Posts y Comentarios', admin: true, vice: true, uebu: false },
                    { section: 'Analisis de Sentimientos', admin: true, vice: true, uebu: true },
                    { section: 'Reputacion', admin: true, vice: true, uebu: true },
                    { section: 'Alertas y Anomalias', admin: true, vice: true, uebu: true },
                    { section: 'Benchmarking', admin: true, vice: true, uebu: true },
                    { section: 'IA / ML / NLP', admin: true, vice: true, uebu: true },
                    { section: 'Evaluacion del Sistema', admin: true, vice: true, uebu: false },
                    { section: 'Configuracion', admin: true, vice: true, uebu: false },
                    { section: 'Gestion de Usuarios', admin: true, vice: false, uebu: false },
                    { section: 'Ayuda', admin: true, vice: true, uebu: true },
                  ].map((row) => (
                    <TableRow key={row.section} hover>
                      <TableCell>{row.section}</TableCell>
                      <TableCell align="center">
                        {row.admin ? <CheckIcon color="success" fontSize="small" /> : <Typography color="text.disabled">-</Typography>}
                      </TableCell>
                      <TableCell align="center">
                        {row.vice ? <CheckIcon color="success" fontSize="small" /> : <Typography color="text.disabled">-</Typography>}
                      </TableCell>
                      <TableCell align="center">
                        {row.uebu ? <CheckIcon color="success" fontSize="small" /> : <Typography color="text.disabled">-</Typography>}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>

            <Box sx={{ mt: 3 }}>
              <Typography variant="subtitle2" fontWeight={600} gutterBottom>
                Descripcion de Roles
              </Typography>
              <Grid container spacing={2}>
                {[
                  {
                    rol: 'Administrador',
                    color: 'error' as const,
                    icon: <UsersIcon />,
                    desc: 'Control total del sistema. Puede gestionar usuarios, configurar alertas, ejecutar OSINT y acceder a todos los modulos de analisis y evaluacion.',
                  },
                  {
                    rol: 'Vicerrector / Jefe',
                    color: 'warning' as const,
                    icon: <SchoolIcon />,
                    desc: 'Acceso completo a todos los dashboards de analisis, configuracion de alertas y evaluacion del sistema. No puede gestionar usuarios.',
                  },
                  {
                    rol: 'Usuario UEBU',
                    color: 'info' as const,
                    icon: <InfoIcon />,
                    desc: 'Acceso a los dashboards de Analisis AI (sentimientos, reputacion, alertas, benchmarking) e IA/ML/NLP para consulta y monitoreo.',
                  },
                ].map((r) => (
                  <Grid item xs={12} md={4} key={r.rol}>
                    <Paper variant="outlined" sx={{ p: 2 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                        {r.icon}
                        <Chip label={r.rol} size="small" color={r.color} />
                      </Box>
                      <Typography variant="body2" color="text.secondary">
                        {r.desc}
                      </Typography>
                    </Paper>
                  </Grid>
                ))}
              </Grid>
            </Box>
          </CardContent>
        </Card>
      </TabPanel>
    </Box>
  );
};

export default AyudaDashboard;
