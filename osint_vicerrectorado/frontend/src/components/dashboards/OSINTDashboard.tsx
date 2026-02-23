/**
 * ═══════════════════════════════════════════════════════════════
 * Dashboard de Inteligencia OSINT
 * ═══════════════════════════════════════════════════════════════
 * 
 * OE1: Técnicas de OSINT múltiple (no solo web scraping)
 * OE2: Patrones identificados, intereses académicos, UEBU
 * OE3: Clasificación temática usando NLP
 * 
 * Muestra:
 * - Resumen de técnicas OSINT utilizadas (SOCMINT, NEWSINT, TRENDINT)
 * - Patrones identificados con recomendaciones
 * - Intereses académicos de la comunidad estudiantil
 * - Distribución de temas
 * - Noticias sobre la EMI
 * - Contenido relevante para la UEBU/Vicerrectorado
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Globe,
  Search,
  TrendingUp,
  AlertTriangle,
  BookOpen,
  MessageSquare,
  BarChart3,
  Newspaper,
  GraduationCap,
  Target,
  Lightbulb,
  RefreshCw,
  Loader2,
  ChevronRight,
  Shield,
  Eye,
  Zap,
  CheckCircle,
  ArrowUpRight,
  ArrowDownRight,
  Minus,
  Users,
  Building,
  DollarSign,
  Award,
  FileText,
  Activity,
  PieChart,
  ExternalLink,
  ThumbsUp,
  ThumbsDown,
  Hash,
} from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5001/api';

// ─── Tipos ───────────────────────────────────────────────────

interface OSINTTecnica {
  tipo_tecnica: string;
  nombre_fuente: string;
  descripcion?: string;
  total_datos_recolectados: number;
  ultima_recoleccion?: string;
}

interface PatronIdentificado {
  id: number;
  nombre_patron: string;
  tipo_patron: string;
  descripcion: string;
  impacto: string;
  recomendacion_accion: string;
  relevancia_vicerrectorado: boolean;
  datos_soporte?: any[];
  fecha_ultima_deteccion: string;
}

interface Tema {
  tema_principal: string;
  cantidad: number;
  academicos: number;
  relevantes_uebu: number;
}

interface Noticia {
  id: number;
  titulo: string;
  resumen: string;
  fuente: string;
  url: string;
  fecha_publicacion: string;
  relevancia_score: number;
  temas_json: string;
}

interface InteresesAcademicos {
  intereses_por_tema: { tema_principal: string; menciones: number; academico: number; uebu: number }[];
  problemas_detectados: { tema_principal: string; palabras_clave: string; texto: string }[];
  elogios_detectados: { tema_principal: string; palabras_clave: string; texto: string }[];
  total_contenido_academico: number;
}

// ─── Nombres legibles de temas ────────────────────────────────
const TEMAS_LABELS: Record<string, { label: string; icon: React.ReactNode; color: string }> = {
  inscripcion: { label: 'Inscripciones y Admisión', icon: <FileText size={16} />, color: '#3b82f6' },
  becas: { label: 'Becas y Beneficios', icon: <Award size={16} />, color: '#8b5cf6' },
  calidad_academica: { label: 'Calidad Académica', icon: <GraduationCap size={16} />, color: '#059669' },
  infraestructura: { label: 'Infraestructura', icon: <Building size={16} />, color: '#d97706' },
  empleo: { label: 'Empleo y Egresados', icon: <Users size={16} />, color: '#0891b2' },
  carreras: { label: 'Carreras de Ingeniería', icon: <BookOpen size={16} />, color: '#7c3aed' },
  queja: { label: 'Quejas y Reclamos', icon: <ThumbsDown size={16} />, color: '#dc2626' },
  elogio: { label: 'Elogios y Reconocimiento', icon: <ThumbsUp size={16} />, color: '#16a34a' },
  disciplina: { label: 'Disciplina y Valores', icon: <Shield size={16} />, color: '#475569' },
  tecnologia: { label: 'Tecnología e Innovación', icon: <Zap size={16} />, color: '#2563eb' },
  vida_estudiantil: { label: 'Vida Estudiantil', icon: <Users size={16} />, color: '#ec4899' },
  costo: { label: 'Costos y Pagos', icon: <DollarSign size={16} />, color: '#ea580c' },
};

const TECNICA_INFO: Record<string, { icon: React.ReactNode; color: string; desc: string }> = {
  SOCMINT: { icon: <MessageSquare size={20} />, color: '#3b82f6', desc: 'Social Media Intelligence' },
  NEWSINT: { icon: <Newspaper size={20} />, color: '#dc2626', desc: 'News Intelligence' },
  TRENDINT: { icon: <TrendingUp size={20} />, color: '#059669', desc: 'Trends Intelligence' },
  SEINT: { icon: <Search size={20} />, color: '#7c3aed', desc: 'Search Engine Intelligence' },
};

// ─── Estilos ─────────────────────────────────────────────────
const s: Record<string, React.CSSProperties> = {
  page: {
    padding: '24px',
    backgroundColor: '#f0f4f8',
    minHeight: '100vh',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  },
  header: {
    background: 'linear-gradient(135deg, #0f172a 0%, #1e3a5f 50%, #0f172a 100%)',
    borderRadius: '16px',
    padding: '28px 32px',
    marginBottom: '24px',
    color: 'white',
  },
  headerTitle: {
    fontSize: '26px',
    fontWeight: 800,
    display: 'flex',
    alignItems: 'center',
    gap: '14px',
    marginBottom: '8px',
  },
  headerSubtitle: {
    fontSize: '14px',
    color: '#94a3b8',
    marginBottom: '20px',
  },
  headerStats: {
    display: 'flex',
    gap: '24px',
    flexWrap: 'wrap' as const,
  },
  headerStat: {
    backgroundColor: 'rgba(255,255,255,0.1)',
    borderRadius: '12px',
    padding: '14px 20px',
    minWidth: '140px',
    backdropFilter: 'blur(10px)',
  },
  headerStatNum: {
    fontSize: '24px',
    fontWeight: 700,
  },
  headerStatLabel: {
    fontSize: '12px',
    color: '#94a3b8',
    marginTop: '2px',
  },
  grid2: {
    display: 'grid',
    gridTemplateColumns: 'repeat(2, 1fr)',
    gap: '20px',
    marginBottom: '24px',
  },
  grid3: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
    gap: '20px',
    marginBottom: '24px',
  },
  card: {
    backgroundColor: 'white',
    borderRadius: '16px',
    padding: '24px',
    boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
    border: '1px solid #e2e8f0',
  },
  cardTitle: {
    fontSize: '16px',
    fontWeight: 700,
    color: '#1e293b',
    marginBottom: '16px',
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
  },
  badge: {
    fontSize: '11px',
    fontWeight: 600,
    padding: '3px 8px',
    borderRadius: '6px',
    display: 'inline-flex',
    alignItems: 'center',
    gap: '4px',
  },
  tecnicaCard: {
    display: 'flex',
    alignItems: 'center',
    gap: '16px',
    padding: '16px',
    borderRadius: '12px',
    border: '1px solid #e2e8f0',
    marginBottom: '12px',
    backgroundColor: '#fafbfc',
  },
  tecnicaIcon: {
    width: '48px',
    height: '48px',
    borderRadius: '12px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  temaBar: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    padding: '10px 14px',
    borderRadius: '8px',
    marginBottom: '8px',
    backgroundColor: '#f8fafc',
    border: '1px solid #f1f5f9',
  },
  patronCard: {
    padding: '18px',
    borderRadius: '12px',
    marginBottom: '12px',
    border: '1px solid #e2e8f0',
    backgroundColor: '#fafbfc',
  },
  noticiaCard: {
    padding: '14px 18px',
    borderRadius: '10px',
    marginBottom: '10px',
    border: '1px solid #e2e8f0',
    cursor: 'pointer',
    transition: 'all 0.2s',
  },
  btnPrimary: {
    padding: '10px 20px',
    borderRadius: '10px',
    border: 'none',
    backgroundColor: '#1e3a5f',
    color: 'white',
    fontWeight: 600,
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    fontSize: '14px',
  },
  contentItem: {
    padding: '12px 16px',
    borderRadius: '8px',
    marginBottom: '8px',
    backgroundColor: '#f8fafc',
    border: '1px solid #f1f5f9',
    fontSize: '13px',
    lineHeight: 1.5,
    color: '#334155',
  },
  fullWidth: {
    gridColumn: '1 / -1',
  },
  loading: {
    display: 'flex',
    flexDirection: 'column' as const,
    alignItems: 'center',
    justifyContent: 'center',
    padding: '80px 20px',
  },
  impactBadge: {
    fontSize: '11px',
    fontWeight: 600,
    padding: '2px 8px',
    borderRadius: '4px',
  },
};

// ─── Componente Principal ────────────────────────────────────

const OSINTDashboard: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [executing, setExecuting] = useState(false);
  const [resumen, setResumen] = useState<any>(null);
  const [patrones, setPatrones] = useState<PatronIdentificado[]>([]);
  const [temas, setTemas] = useState<any>(null);
  const [noticias, setNoticias] = useState<Noticia[]>([]);
  const [intereses, setIntereses] = useState<InteresesAcademicos | null>(null);
  const [activeTab, setActiveTab] = useState<'patrones' | 'temas' | 'noticias' | 'uebu'>('patrones');

  // Cargar datos
  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [resRes, patRes, temRes, notRes, intRes] = await Promise.all([
        fetch(`${API_URL}/osint/resumen`).then(r => r.json()).catch(() => null),
        fetch(`${API_URL}/osint/patrones`).then(r => r.json()).catch(() => []),
        fetch(`${API_URL}/osint/temas`).then(r => r.json()).catch(() => null),
        fetch(`${API_URL}/osint/noticias`).then(r => r.json()).catch(() => []),
        fetch(`${API_URL}/osint/intereses-academicos`).then(r => r.json()).catch(() => null),
      ]);
      
      setResumen(resRes);
      setPatrones(patRes);
      setTemas(temRes);
      setNoticias(notRes);
      setIntereses(intRes);
    } catch (err) {
      console.error('Error cargando datos OSINT:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Ejecutar OSINT completo
  const handleExecuteOSINT = async () => {
    if (!confirm('¿Ejecutar recolección OSINT completa?\n\nEsto ejecutará:\n1. Búsqueda de noticias (NEWSINT)\n2. Análisis de tendencias (TRENDINT)\n3. Clasificación temática (NLP)\n4. Identificación de patrones')) {
      return;
    }
    
    setExecuting(true);
    try {
      await fetch(`${API_URL}/osint/ejecutar`, { method: 'POST' });
      
      // Esperar a que termine y recargar
      setTimeout(async () => {
        await fetchData();
        setExecuting(false);
      }, 8000);
    } catch {
      setExecuting(false);
    }
  };

  // Helpers
  const getImpactColor = (impact: string) => {
    switch (impact) {
      case 'alto': return { bg: '#fee2e2', color: '#991b1b' };
      case 'medio': return { bg: '#fef3c7', color: '#92400e' };
      case 'bajo': return { bg: '#dcfce7', color: '#166534' };
      default: return { bg: '#f1f5f9', color: '#475569' };
    }
  };

  if (loading) {
    return (
      <div style={s.loading}>
        <Loader2 size={40} style={{ animation: 'spin 1s linear infinite' }} color="#1e3a5f" />
        <p style={{ marginTop: '16px', color: '#64748b' }}>Cargando inteligencia OSINT...</p>
        <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  const totalDatos = resumen?.total_datos || 0;
  const totalTecnicas = (resumen?.tecnicas_osint || []).length;
  const totalPatrones = patrones.length;
  const totalTemas = temas?.total_clasificados || 0;

  return (
    <div style={s.page}>
      {/* ─── Header Principal ─── */}
      <div style={s.header}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <div style={s.headerTitle}>
              <Globe size={28} />
              Inteligencia OSINT — Vicerrectorado EMI
            </div>
            <p style={s.headerSubtitle}>
              Open Source Intelligence: Análisis multifuente de datos abiertos para la toma de decisiones académicas
            </p>
          </div>
          <button 
            style={{ ...s.btnPrimary, backgroundColor: executing ? '#475569' : '#22c55e' }}
            onClick={handleExecuteOSINT}
            disabled={executing}
          >
            {executing ? (
              <Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} />
            ) : (
              <Zap size={16} />
            )}
            {executing ? 'Ejecutando OSINT...' : 'Ejecutar OSINT Completo'}
          </button>
        </div>
        
        <div style={s.headerStats}>
          <div style={s.headerStat}>
            <div style={s.headerStatNum}>{totalTecnicas}</div>
            <div style={s.headerStatLabel}>Técnicas OSINT</div>
          </div>
          <div style={s.headerStat}>
            <div style={{ ...s.headerStatNum, color: '#22c55e' }}>{totalDatos}</div>
            <div style={s.headerStatLabel}>Datos Recolectados</div>
          </div>
          <div style={s.headerStat}>
            <div style={{ ...s.headerStatNum, color: '#f59e0b' }}>{totalPatrones}</div>
            <div style={s.headerStatLabel}>Patrones Identificados</div>
          </div>
          <div style={s.headerStat}>
            <div style={{ ...s.headerStatNum, color: '#8b5cf6' }}>{totalTemas}</div>
            <div style={s.headerStatLabel}>Contenidos Clasificados</div>
          </div>
          <div style={s.headerStat}>
            <div style={{ ...s.headerStatNum, color: '#06b6d4' }}>{noticias.length}</div>
            <div style={s.headerStatLabel}>Noticias Monitoreadas</div>
          </div>
        </div>
      </div>

      {/* ─── Técnicas OSINT Utilizadas ─── */}
      <div style={{ ...s.card, marginBottom: '24px' }}>
        <div style={s.cardTitle}>
          <Shield size={20} color="#1e3a5f" />
          Técnicas OSINT Implementadas
          <span style={{ ...s.badge, backgroundColor: '#dbeafe', color: '#1e40af', marginLeft: 'auto' }}>
            Marco OSINT Framework
          </span>
        </div>
        <div style={s.grid3}>
          {(resumen?.tecnicas_osint || []).map((t: OSINTTecnica, i: number) => {
            const info = TECNICA_INFO[t.tipo_tecnica] || TECNICA_INFO.SOCMINT;
            return (
              <div key={i} style={s.tecnicaCard}>
                <div style={{ ...s.tecnicaIcon, backgroundColor: `${info.color}15`, color: info.color }}>
                  {info.icon}
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: '13px', fontWeight: 700, color: '#1e293b' }}>
                    {t.tipo_tecnica}
                  </div>
                  <div style={{ fontSize: '12px', color: '#64748b' }}>{info.desc}</div>
                  <div style={{ fontSize: '12px', color: '#475569', marginTop: '4px' }}>
                    {t.nombre_fuente}
                  </div>
                  <div style={{ fontSize: '14px', fontWeight: 600, color: info.color, marginTop: '4px' }}>
                    {t.total_datos_recolectados || 0} datos
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* ─── Tabs de Análisis ─── */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '20px', flexWrap: 'wrap' }}>
        {[
          { key: 'patrones', label: 'Patrones Identificados', icon: <Target size={16} /> },
          { key: 'temas', label: 'Distribución Temática', icon: <PieChart size={16} /> },
          { key: 'uebu', label: 'Intereses Académicos (UEBU)', icon: <GraduationCap size={16} /> },
          { key: 'noticias', label: 'Noticias EMI', icon: <Newspaper size={16} /> },
        ].map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key as any)}
            style={{
              padding: '10px 18px',
              borderRadius: '10px',
              border: activeTab === tab.key ? '2px solid #1e3a5f' : '1px solid #e2e8f0',
              backgroundColor: activeTab === tab.key ? '#1e3a5f' : 'white',
              color: activeTab === tab.key ? 'white' : '#475569',
              fontWeight: 600,
              fontSize: '13px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}
          >
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {/* ─── TAB: Patrones Identificados ─── */}
      {activeTab === 'patrones' && (
        <div style={s.grid2}>
          {/* Patrones principales */}
          <div style={{ ...s.card, ...s.fullWidth }}>
            <div style={s.cardTitle}>
              <Target size={20} color="#dc2626" />
              Patrones Identificados por el Sistema
              <span style={{ ...s.badge, backgroundColor: '#fee2e2', color: '#991b1b', marginLeft: 'auto' }}>
                {patrones.length} patrones activos
              </span>
            </div>
            
            {patrones.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '40px', color: '#94a3b8' }}>
                <Target size={48} style={{ opacity: 0.3, marginBottom: '12px' }} />
                <p>No se han identificado patrones aún.</p>
                <p style={{ fontSize: '13px' }}>Ejecuta el OSINT completo para analizar los datos.</p>
              </div>
            ) : (
              patrones.map((p, i) => {
                const impactStyle = getImpactColor(p.impacto);
                return (
                  <div key={i} style={s.patronCard}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
                      <span style={{ ...s.impactBadge, backgroundColor: impactStyle.bg, color: impactStyle.color }}>
                        {p.impacto?.toUpperCase()}
                      </span>
                      {p.relevancia_vicerrectorado && (
                        <span style={{ ...s.badge, backgroundColor: '#dbeafe', color: '#1e40af' }}>
                          <GraduationCap size={12} /> Relevante Vicerrectorado
                        </span>
                      )}
                      <span style={{ fontSize: '11px', color: '#94a3b8', marginLeft: 'auto' }}>
                        {p.tipo_patron}
                      </span>
                    </div>
                    <div style={{ fontSize: '15px', fontWeight: 600, color: '#1e293b', marginBottom: '6px' }}>
                      {p.nombre_patron}
                    </div>
                    <div style={{ fontSize: '13px', color: '#475569', marginBottom: '10px', lineHeight: 1.6 }}>
                      {p.descripcion}
                    </div>
                    <div style={{ 
                      fontSize: '13px', color: '#059669', backgroundColor: '#f0fdf4', 
                      padding: '10px 14px', borderRadius: '8px', border: '1px solid #bbf7d0',
                      display: 'flex', alignItems: 'flex-start', gap: '8px'
                    }}>
                      <Lightbulb size={16} style={{ flexShrink: 0, marginTop: '2px' }} />
                      <span><strong>Recomendación:</strong> {p.recomendacion_accion}</span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}

      {/* ─── TAB: Distribución Temática ─── */}
      {activeTab === 'temas' && (
        <div style={s.grid2}>
          {/* Distribución de temas */}
          <div style={s.card}>
            <div style={s.cardTitle}>
              <Hash size={20} color="#7c3aed" />
              Distribución de Temas
            </div>
            {(temas?.distribucion || []).length === 0 ? (
              <div style={{ textAlign: 'center', padding: '30px', color: '#94a3b8' }}>
                <PieChart size={40} style={{ opacity: 0.3 }} />
                <p>Sin clasificaciones temáticas. Ejecuta el OSINT.</p>
              </div>
            ) : (
              (temas?.distribucion || []).map((tema: Tema, i: number) => {
                const info = TEMAS_LABELS[tema.tema_principal] || { label: tema.tema_principal, icon: <Hash size={16} />, color: '#64748b' };
                const maxCount = Math.max(...(temas?.distribucion || []).map((t: Tema) => t.cantidad));
                const pct = maxCount > 0 ? (tema.cantidad / maxCount * 100) : 0;
                
                return (
                  <div key={i} style={s.temaBar}>
                    <div style={{ color: info.color, flexShrink: 0 }}>{info.icon}</div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: '13px', fontWeight: 600, color: '#334155' }}>{info.label}</div>
                      <div style={{ 
                        height: '6px', borderRadius: '3px', backgroundColor: '#e2e8f0', marginTop: '6px',
                        overflow: 'hidden'
                      }}>
                        <div style={{ height: '100%', width: `${pct}%`, backgroundColor: info.color, borderRadius: '3px' }} />
                      </div>
                    </div>
                    <div style={{ fontSize: '14px', fontWeight: 700, color: info.color, minWidth: '40px', textAlign: 'right' }}>
                      {tema.cantidad}
                    </div>
                  </div>
                );
              })
            )}
          </div>

          {/* Detalle por tipo */}
          <div style={s.card}>
            <div style={s.cardTitle}>
              <BarChart3 size={20} color="#0891b2" />
              Clasificación del Contenido
            </div>
            <div style={{ 
              display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '16px'
            }}>
              <div style={{ backgroundColor: '#f0fdf4', padding: '16px', borderRadius: '12px', textAlign: 'center' }}>
                <div style={{ fontSize: '28px', fontWeight: 700, color: '#16a34a' }}>
                  {(temas?.distribucion || []).filter((t: Tema) => t.academicos > 0).reduce((sum: number, t: Tema) => sum + t.academicos, 0)}
                </div>
                <div style={{ fontSize: '12px', color: '#166534' }}>Contenido Académico</div>
              </div>
              <div style={{ backgroundColor: '#eff6ff', padding: '16px', borderRadius: '12px', textAlign: 'center' }}>
                <div style={{ fontSize: '28px', fontWeight: 700, color: '#2563eb' }}>
                  {(temas?.distribucion || []).filter((t: Tema) => t.relevantes_uebu > 0).reduce((sum: number, t: Tema) => sum + t.relevantes_uebu, 0)}
                </div>
                <div style={{ fontSize: '12px', color: '#1e40af' }}>Relevante para UEBU</div>
              </div>
            </div>

            <div style={{ fontSize: '13px', color: '#64748b', marginTop: '16px' }}>
              <strong>Temas académicos:</strong> Inscripciones, Becas, Calidad Académica, Carreras, Empleo, Tecnología, Costos
            </div>
            <div style={{ fontSize: '13px', color: '#64748b', marginTop: '8px' }}>
              <strong>Temas UEBU:</strong> Inscripciones, Becas, Calidad, Quejas, Infraestructura, Costos, Vida Estudiantil
            </div>
          </div>
        </div>
      )}

      {/* ─── TAB: Intereses Académicos (UEBU) ─── */}
      {activeTab === 'uebu' && (
        <div style={s.grid2}>
          {/* Intereses principales */}
          <div style={s.card}>
            <div style={s.cardTitle}>
              <GraduationCap size={20} color="#7c3aed" />
              Intereses Académicos Identificados
              <span style={{ ...s.badge, backgroundColor: '#f3e8ff', color: '#7c3aed', marginLeft: 'auto' }}>
                {intereses?.total_contenido_academico || 0} menciones
              </span>
            </div>
            
            {(intereses?.intereses_por_tema || []).length === 0 ? (
              <div style={{ textAlign: 'center', padding: '30px', color: '#94a3b8' }}>
                <GraduationCap size={40} style={{ opacity: 0.3 }} />
                <p>Sin datos de intereses académicos. Ejecuta el OSINT.</p>
              </div>
            ) : (
              (intereses?.intereses_por_tema || []).map((int_item, i) => {
                const info = TEMAS_LABELS[int_item.tema_principal] || { label: int_item.tema_principal, icon: <Hash size={16} />, color: '#64748b' };
                return (
                  <div key={i} style={{ ...s.temaBar, borderLeft: `3px solid ${info.color}` }}>
                    <div style={{ color: info.color }}>{info.icon}</div>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: '13px', fontWeight: 600, color: '#334155' }}>{info.label}</div>
                    </div>
                    <div style={{ fontSize: '14px', fontWeight: 700, color: info.color }}>
                      {int_item.menciones}
                    </div>
                  </div>
                );
              })
            )}
          </div>

          {/* Problemas detectados */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div style={s.card}>
              <div style={s.cardTitle}>
                <ThumbsDown size={20} color="#dc2626" />
                Problemas y Quejas Detectadas
              </div>
              {(intereses?.problemas_detectados || []).length === 0 ? (
                <p style={{ color: '#94a3b8', fontSize: '13px' }}>No se detectaron quejas explícitas</p>
              ) : (
                (intereses?.problemas_detectados || []).slice(0, 5).map((p, i) => (
                  <div key={i} style={{ ...s.contentItem, borderLeft: '3px solid #dc2626' }}>
                    "{p.texto?.slice(0, 150)}..."
                    {p.palabras_clave && (
                      <div style={{ fontSize: '11px', color: '#dc2626', marginTop: '4px' }}>
                        Palabras clave: {p.palabras_clave}
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>

            <div style={s.card}>
              <div style={s.cardTitle}>
                <ThumbsUp size={20} color="#16a34a" />
                Elogios y Reconocimientos
              </div>
              {(intereses?.elogios_detectados || []).length === 0 ? (
                <p style={{ color: '#94a3b8', fontSize: '13px' }}>No se detectaron elogios explícitos</p>
              ) : (
                (intereses?.elogios_detectados || []).slice(0, 5).map((e, i) => (
                  <div key={i} style={{ ...s.contentItem, borderLeft: '3px solid #16a34a' }}>
                    "{e.texto?.slice(0, 150)}..."
                    {e.palabras_clave && (
                      <div style={{ fontSize: '11px', color: '#16a34a', marginTop: '4px' }}>
                        Palabras clave: {e.palabras_clave}
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}

      {/* ─── TAB: Noticias ─── */}
      {activeTab === 'noticias' && (
        <div style={{ ...s.card, ...s.fullWidth }}>
          <div style={s.cardTitle}>
            <Newspaper size={20} color="#dc2626" />
            Noticias Monitoreadas sobre la EMI
            <span style={{ ...s.badge, backgroundColor: '#fee2e2', color: '#991b1b', marginLeft: 'auto' }}>
              NEWSINT
            </span>
          </div>
          
          {noticias.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '40px', color: '#94a3b8' }}>
              <Newspaper size={48} style={{ opacity: 0.3, marginBottom: '12px' }} />
              <p>No hay noticias recolectadas aún.</p>
              <p style={{ fontSize: '13px' }}>Ejecuta el OSINT completo para buscar noticias sobre la EMI.</p>
            </div>
          ) : (
            noticias.map((n, i) => (
              <div key={i} style={s.noticiaCard} onClick={() => n.url && window.open(n.url, '_blank')}>
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
                  <Newspaper size={18} color="#dc2626" style={{ flexShrink: 0, marginTop: '2px' }} />
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: '14px', fontWeight: 600, color: '#1e293b', marginBottom: '4px' }}>
                      {n.titulo}
                      <ExternalLink size={12} style={{ marginLeft: '6px', opacity: 0.4 }} />
                    </div>
                    {n.resumen && (
                      <div style={{ fontSize: '13px', color: '#64748b', lineHeight: 1.5 }}>
                        {n.resumen.slice(0, 200)}...
                      </div>
                    )}
                    <div style={{ display: 'flex', gap: '12px', marginTop: '6px', fontSize: '11px', color: '#94a3b8' }}>
                      {n.fuente && <span>Fuente: {n.fuente}</span>}
                      {n.fecha_publicacion && <span>Fecha: {n.fecha_publicacion}</span>}
                      {n.relevancia_score > 0 && (
                        <span style={{ color: '#059669' }}>Relevancia: {(n.relevancia_score * 100).toFixed(0)}%</span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* ─── Info de Metodología OSINT ─── */}
      <div style={{ ...s.card, marginTop: '24px', background: 'linear-gradient(135deg, #f0f9ff, #eff6ff)' }}>
        <div style={s.cardTitle}>
          <BookOpen size={20} color="#1e40af" />
          Metodología OSINT Aplicada
        </div>
        <div style={s.grid2}>
          <div>
            <h4 style={{ fontSize: '14px', color: '#1e293b', marginBottom: '8px' }}>Técnicas de Recolección</h4>
            <ul style={{ fontSize: '13px', color: '#475569', lineHeight: 2, paddingLeft: '20px' }}>
              <li><strong>SOCMINT</strong> (Social Media Intelligence): Monitoreo de Facebook y TikTok de la EMI</li>
              <li><strong>NEWSINT</strong> (News Intelligence): Monitoreo de noticias en Google News RSS</li>
              <li><strong>TRENDINT</strong> (Trends Intelligence): Análisis de tendencias de búsqueda y actividad</li>
              <li><strong>SEINT</strong> (Search Engine Intelligence): Búsqueda en motores de datos públicos</li>
            </ul>
          </div>
          <div>
            <h4 style={{ fontSize: '14px', color: '#1e293b', marginBottom: '8px' }}>Técnicas de Análisis</h4>
            <ul style={{ fontSize: '13px', color: '#475569', lineHeight: 2, paddingLeft: '20px' }}>
              <li><strong>NLP</strong>: Clasificación temática automática de contenido</li>
              <li><strong>Análisis de Sentimiento</strong>: BETO (BERT en español) 3 clases</li>
              <li><strong>Clustering</strong>: K-Means con TF-IDF para agrupación de opiniones</li>
              <li><strong>Detección de Anomalías</strong>: Isolation Forest para alertas</li>
              <li><strong>Identificación de Patrones</strong>: Temporal, temático y de engagement</li>
            </ul>
          </div>
        </div>
      </div>

      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  );
};

export default OSINTDashboard;
