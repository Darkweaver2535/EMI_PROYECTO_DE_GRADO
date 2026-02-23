/**
 * ═══════════════════════════════════════════════════════════════
 * Dashboard de IA, ML y NLP — OE3
 * ═══════════════════════════════════════════════════════════════
 * 
 * Muestra los resultados del pipeline NLP:
 * - Keywords extraídas (TF-IDF)
 * - Tópicos descubiertos (LDA)
 * - Clusters de opiniones (K-Means)
 * - Entidades reconocidas (NER)
 * - Sentimiento por aspecto
 * - Resumen ejecutivo automático
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Brain,
  Hash,
  Layers,
  Users,
  Target,
  Zap,
  Loader2,
  BarChart3,
  RefreshCw,
  MessageSquare,
  Tag,
  PieChart,
  BookOpen,
  Lightbulb,
  AlertTriangle,
  CheckCircle,
  TrendingUp,
  TrendingDown,
  Minus,
} from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5001/api';

// Colores para diferentes categorías
const COLORS = ['#3b82f6', '#8b5cf6', '#059669', '#dc2626', '#d97706', '#0891b2', '#7c3aed', '#ec4899', '#ea580c', '#16a34a'];

const s: Record<string, React.CSSProperties> = {
  page: {
    padding: '24px',
    backgroundColor: '#f0f4f8',
    minHeight: '100vh',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  },
  header: {
    background: 'linear-gradient(135deg, #1e1b4b 0%, #3730a3 50%, #1e1b4b 100%)',
    borderRadius: '16px',
    padding: '28px 32px',
    marginBottom: '24px',
    color: 'white',
  },
  headerTitle: { fontSize: '26px', fontWeight: 800, display: 'flex', alignItems: 'center', gap: '14px', marginBottom: '8px' },
  headerSub: { fontSize: '14px', color: '#a5b4fc', marginBottom: '20px' },
  stats: { display: 'flex', gap: '20px', flexWrap: 'wrap' as const },
  stat: { backgroundColor: 'rgba(255,255,255,0.1)', borderRadius: '12px', padding: '14px 20px', minWidth: '130px' },
  statNum: { fontSize: '24px', fontWeight: 700 },
  statLabel: { fontSize: '11px', color: '#a5b4fc', marginTop: '2px' },
  grid2: { display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '20px', marginBottom: '24px' },
  grid3: { display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '20px', marginBottom: '24px' },
  card: { backgroundColor: 'white', borderRadius: '16px', padding: '24px', boxShadow: '0 1px 3px rgba(0,0,0,0.08)', border: '1px solid #e2e8f0' },
  cardTitle: { fontSize: '16px', fontWeight: 700, color: '#1e293b', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '10px' },
  badge: { fontSize: '11px', fontWeight: 600, padding: '3px 8px', borderRadius: '6px', display: 'inline-flex', alignItems: 'center', gap: '4px' },
  keyword: { display: 'inline-flex', alignItems: 'center', gap: '4px', padding: '5px 12px', borderRadius: '20px', fontSize: '13px', fontWeight: 500, margin: '3px', border: '1px solid #e2e8f0', backgroundColor: '#f8fafc' },
  barRow: { display: 'flex', alignItems: 'center', gap: '12px', padding: '10px 14px', borderRadius: '8px', marginBottom: '8px', backgroundColor: '#f8fafc', border: '1px solid #f1f5f9' },
  topicCard: { padding: '16px', borderRadius: '12px', marginBottom: '12px', border: '1px solid #e2e8f0', backgroundColor: '#fafbfc' },
  clusterCard: { padding: '16px', borderRadius: '12px', marginBottom: '12px', border: '1px solid #e2e8f0' },
  aspectBar: { display: 'flex', alignItems: 'center', gap: '12px', padding: '12px 16px', borderRadius: '10px', marginBottom: '10px', backgroundColor: '#f8fafc', border: '1px solid #e2e8f0' },
  btn: { padding: '10px 20px', borderRadius: '10px', border: 'none', backgroundColor: '#4f46e5', color: 'white', fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '14px' },
  loading: { display: 'flex', flexDirection: 'column' as const, alignItems: 'center', justifyContent: 'center', padding: '80px 20px' },
  fullWidth: { gridColumn: '1 / -1' },
};

const NLPDashboard: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [executing, setExecuting] = useState(false);
  const [resumen, setResumen] = useState<any>(null);
  const [keywords, setKeywords] = useState<any[]>([]);
  const [topicos, setTopicos] = useState<any[]>([]);
  const [clusters, setClusters] = useState<any[]>([]);
  const [entidades, setEntidades] = useState<any>({});
  const [sentAspecto, setSentAspecto] = useState<any>({});

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [resRes, kwRes, topRes, clRes, entRes, saRes] = await Promise.all([
        fetch(`${API_URL}/nlp/resumen`).then(r => r.json()).catch(() => null),
        fetch(`${API_URL}/nlp/keywords`).then(r => r.json()).catch(() => []),
        fetch(`${API_URL}/nlp/topicos`).then(r => r.json()).catch(() => []),
        fetch(`${API_URL}/nlp/clusters`).then(r => r.json()).catch(() => []),
        fetch(`${API_URL}/nlp/entidades`).then(r => r.json()).catch(() => ({})),
        fetch(`${API_URL}/nlp/sentimiento-aspecto`).then(r => r.json()).catch(() => ({})),
      ]);
      setResumen(resRes);
      setKeywords(kwRes);
      setTopicos(topRes);
      setClusters(clRes);
      setEntidades(entRes);
      setSentAspecto(saRes);
    } catch (err) {
      console.error('Error:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleExecuteNLP = async () => {
    if (!confirm('¿Ejecutar Pipeline NLP Completo?\n\nSe aplicará:\n1. TF-IDF para keywords\n2. LDA para tópicos\n3. K-Means para clustering\n4. NER para entidades\n5. Análisis de sentimiento por aspecto')) return;
    setExecuting(true);
    try {
      await fetch(`${API_URL}/nlp/ejecutar`, { method: 'POST' });
      setTimeout(async () => { await fetchData(); setExecuting(false); }, 10000);
    } catch { setExecuting(false); }
  };

  if (loading) return (
    <div style={s.loading}>
      <Loader2 size={40} style={{ animation: 'spin 1s linear infinite' }} color="#4f46e5" />
      <p style={{ marginTop: '16px', color: '#64748b' }}>Cargando análisis NLP...</p>
      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  );

  const nTecnicas = (resumen?.tecnicas_aplicadas || []).length;
  const maxKwScore = keywords.length > 0 ? keywords[0].tfidf_score : 1;

  return (
    <div style={s.page}>
      {/* Header */}
      <div style={s.header}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <div style={s.headerTitle}><Brain size={28} /> Análisis IA / ML / NLP</div>
            <p style={s.headerSub}>OE3: Modelos de Inteligencia Artificial, Machine Learning y Procesamiento de Lenguaje Natural</p>
          </div>
          <button style={{ ...s.btn, backgroundColor: executing ? '#475569' : '#22c55e' }} onClick={handleExecuteNLP} disabled={executing}>
            {executing ? <Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} /> : <Zap size={16} />}
            {executing ? 'Ejecutando NLP...' : 'Ejecutar Pipeline NLP'}
          </button>
        </div>
        <div style={s.stats}>
          <div style={s.stat}><div style={s.statNum}>{nTecnicas}</div><div style={s.statLabel}>Técnicas IA/ML</div></div>
          <div style={s.stat}><div style={{ ...s.statNum, color: '#818cf8' }}>{keywords.length}</div><div style={s.statLabel}>Keywords TF-IDF</div></div>
          <div style={s.stat}><div style={{ ...s.statNum, color: '#34d399' }}>{topicos.length}</div><div style={s.statLabel}>Tópicos LDA</div></div>
          <div style={s.stat}><div style={{ ...s.statNum, color: '#fbbf24' }}>{clusters.length}</div><div style={s.statLabel}>Clusters K-Means</div></div>
          <div style={s.stat}><div style={{ ...s.statNum, color: '#f472b6' }}>{Object.values(entidades).reduce((sum: number, arr: any) => sum + (Array.isArray(arr) ? arr.length : 0), 0)}</div><div style={s.statLabel}>Entidades NER</div></div>
        </div>
      </div>

      {/* Técnicas aplicadas */}
      <div style={{ ...s.card, marginBottom: '24px' }}>
        <div style={s.cardTitle}><Layers size={20} color="#4f46e5" /> Técnicas de IA/ML/NLP Aplicadas
          <span style={{ ...s.badge, backgroundColor: '#eef2ff', color: '#4338ca', marginLeft: 'auto' }}>{nTecnicas} técnicas</span>
        </div>
        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
          {(resumen?.tecnicas_aplicadas || []).map((t: any, i: number) => (
            <div key={i} style={{ padding: '12px 18px', borderRadius: '12px', border: '1px solid #e2e8f0', backgroundColor: '#fafbfc', display: 'flex', gap: '12px', alignItems: 'center', minWidth: '200px' }}>
              <div style={{ width: '40px', height: '40px', borderRadius: '10px', backgroundColor: `${COLORS[i % COLORS.length]}15`, color: COLORS[i % COLORS.length], display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                {t.tipo === 'ML' ? <BarChart3 size={18} /> : t.tipo === 'Deep Learning' ? <Brain size={18} /> : <Hash size={18} />}
              </div>
              <div>
                <div style={{ fontSize: '13px', fontWeight: 600, color: '#1e293b' }}>{t.nombre}</div>
                <div style={{ fontSize: '11px', color: '#64748b' }}>{t.tipo} — {t.resultados} resultados</div>
              </div>
            </div>
          ))}
          {nTecnicas === 0 && (
            <div style={{ textAlign: 'center', width: '100%', padding: '30px', color: '#94a3b8' }}>
              <Brain size={48} style={{ opacity: 0.3, marginBottom: '8px' }} />
              <p>Ejecuta el Pipeline NLP para aplicar las técnicas de IA/ML</p>
            </div>
          )}
        </div>
      </div>

      <div style={s.grid2}>
        {/* Keywords TF-IDF */}
        <div style={s.card}>
          <div style={s.cardTitle}><Hash size={20} color="#3b82f6" /> Palabras Clave (TF-IDF)</div>
          {keywords.length === 0 ? (
            <p style={{ color: '#94a3b8', textAlign: 'center', padding: '20px' }}>Sin keywords. Ejecuta el NLP.</p>
          ) : (
            <>
              {keywords.slice(0, 20).map((kw: any, i: number) => (
                <div key={i} style={s.barRow}>
                  <span style={{ fontSize: '13px', fontWeight: 600, color: '#334155', flex: 1 }}>{kw.palabra}</span>
                  <div style={{ flex: 2, height: '8px', borderRadius: '4px', backgroundColor: '#e2e8f0', overflow: 'hidden' }}>
                    <div style={{ height: '100%', width: `${(kw.tfidf_score / maxKwScore) * 100}%`, backgroundColor: COLORS[i % COLORS.length], borderRadius: '4px' }} />
                  </div>
                  <span style={{ fontSize: '12px', color: '#64748b', minWidth: '60px', textAlign: 'right' }}>
                    {kw.tfidf_score.toFixed(4)}
                  </span>
                  <span style={{ ...s.badge, backgroundColor: kw.tipo === 'carrera' ? '#dbeafe' : kw.tipo === 'academico' ? '#dcfce7' : '#f1f5f9', color: kw.tipo === 'carrera' ? '#1e40af' : kw.tipo === 'academico' ? '#166534' : '#475569' }}>
                    {kw.tipo}
                  </span>
                </div>
              ))}
            </>
          )}
        </div>

        {/* Tópicos LDA */}
        <div style={s.card}>
          <div style={s.cardTitle}><PieChart size={20} color="#8b5cf6" /> Tópicos Descubiertos (LDA)</div>
          {topicos.length === 0 ? (
            <p style={{ color: '#94a3b8', textAlign: 'center', padding: '20px' }}>Sin tópicos. Ejecuta el NLP.</p>
          ) : (
            topicos.map((t: any, i: number) => (
              <div key={i} style={{ ...s.topicCard, borderLeft: `4px solid ${COLORS[i % COLORS.length]}` }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <span style={{ fontSize: '14px', fontWeight: 600, color: COLORS[i % COLORS.length] }}>
                    {t.nombre_topico || `Tópico ${t.topico_id}`}
                  </span>
                  <span style={{ ...s.badge, backgroundColor: '#f1f5f9', color: '#475569' }}>
                    {t.num_documentos} docs
                  </span>
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                  {(Array.isArray(t.palabras_clave) ? t.palabras_clave : []).slice(0, 8).map((w: string, j: number) => (
                    <span key={j} style={{ ...s.keyword, color: COLORS[i % COLORS.length], borderColor: `${COLORS[i % COLORS.length]}30`, backgroundColor: `${COLORS[i % COLORS.length]}08` }}>
                      {w}
                    </span>
                  ))}
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      <div style={s.grid2}>
        {/* Clusters K-Means */}
        <div style={s.card}>
          <div style={s.cardTitle}><Users size={20} color="#d97706" /> Clusters de Opiniones (K-Means)</div>
          {clusters.length === 0 ? (
            <p style={{ color: '#94a3b8', textAlign: 'center', padding: '20px' }}>Sin clusters. Ejecuta el NLP.</p>
          ) : (
            clusters.map((c: any, i: number) => (
              <div key={i} style={{ ...s.clusterCard, borderLeft: `4px solid ${COLORS[i % COLORS.length]}` }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                  <span style={{ fontSize: '14px', fontWeight: 600, color: '#1e293b' }}>
                    {c.etiqueta}
                  </span>
                  <span style={{ fontSize: '12px', color: '#64748b' }}>{c.num_documentos} opiniones</span>
                </div>
                <div style={{ fontSize: '12px', color: '#64748b', marginBottom: '8px' }}>
                  Sentimiento: <span style={{ fontWeight: 600, color: c.sentimiento_predominante === 'Positivo' ? '#16a34a' : c.sentimiento_predominante === 'Negativo' ? '#dc2626' : '#64748b' }}>{c.sentimiento_predominante}</span>
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                  {(Array.isArray(c.palabras_clave) ? c.palabras_clave : []).slice(0, 6).map((w: string, j: number) => (
                    <span key={j} style={s.keyword}>{w}</span>
                  ))}
                </div>
                {(Array.isArray(c.textos_representativos) ? c.textos_representativos : []).slice(0, 1).map((t: string, j: number) => (
                  <div key={j} style={{ fontSize: '12px', color: '#94a3b8', marginTop: '8px', fontStyle: 'italic' }}>
                    "{t?.slice(0, 120)}..."
                  </div>
                ))}
              </div>
            ))
          )}
          {clusters.length > 0 && (
            <div style={{ textAlign: 'center', fontSize: '12px', color: '#64748b', marginTop: '8px' }}>
              Silhouette Score: <strong>{clusters[0]?.silhouette_score?.toFixed(4) || 'N/A'}</strong>
            </div>
          )}
        </div>

        {/* Sentimiento por Aspecto */}
        <div style={s.card}>
          <div style={s.cardTitle}><Target size={20} color="#dc2626" /> Sentimiento por Aspecto</div>
          {Object.keys(sentAspecto).length === 0 ? (
            <p style={{ color: '#94a3b8', textAlign: 'center', padding: '20px' }}>Sin datos de aspecto. Ejecuta el NLP.</p>
          ) : (
            Object.entries(sentAspecto).map(([aspecto, data]: [string, any], i: number) => {
              const scoreColor = data.score > 20 ? '#16a34a' : data.score < -20 ? '#dc2626' : '#d97706';
              return (
                <div key={i} style={s.aspectBar}>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: '13px', fontWeight: 600, color: '#1e293b' }}>{aspecto}</div>
                    <div style={{ fontSize: '11px', color: '#94a3b8' }}>{data.total_menciones} menciones</div>
                  </div>
                  <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                    <span style={{ fontSize: '11px', color: '#16a34a' }}>+{data.positivos}</span>
                    <span style={{ fontSize: '11px', color: '#94a3b8' }}>{data.neutrales}</span>
                    <span style={{ fontSize: '11px', color: '#dc2626' }}>-{data.negativos}</span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '4px', minWidth: '60px', justifyContent: 'flex-end' }}>
                    {data.score > 10 ? <TrendingUp size={14} color={scoreColor} /> : data.score < -10 ? <TrendingDown size={14} color={scoreColor} /> : <Minus size={14} color={scoreColor} />}
                    <span style={{ fontSize: '14px', fontWeight: 700, color: scoreColor }}>{data.score >= 0 ? '+' : ''}{data.score}</span>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Entidades NER */}
      <div style={{ ...s.card, marginBottom: '24px' }}>
        <div style={s.cardTitle}><Tag size={20} color="#059669" /> Entidades Reconocidas (NER)</div>
        <div style={s.grid3}>
          {Object.entries(entidades).map(([tipo, items]: [string, any], i: number) => (
            <div key={i}>
              <div style={{ fontSize: '13px', fontWeight: 700, color: COLORS[i % COLORS.length], marginBottom: '10px', textTransform: 'capitalize' }}>
                {tipo.replace(/_/g, ' ')}
              </div>
              {(Array.isArray(items) ? items : []).slice(0, 8).map((item: any, j: number) => (
                <div key={j} style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 8px', fontSize: '12px', borderRadius: '4px', marginBottom: '3px', backgroundColor: j % 2 === 0 ? '#f8fafc' : 'transparent' }}>
                  <span style={{ color: '#334155' }}>{item.entidad}</span>
                  <span style={{ color: '#94a3b8', fontWeight: 600 }}>{item.frecuencia}</span>
                </div>
              ))}
              {(!Array.isArray(items) || items.length === 0) && (
                <p style={{ fontSize: '12px', color: '#94a3b8' }}>Sin entidades</p>
              )}
            </div>
          ))}
          {Object.keys(entidades).length === 0 && (
            <div style={{ ...s.fullWidth, textAlign: 'center', padding: '30px', color: '#94a3b8' }}>
              <Tag size={40} style={{ opacity: 0.3, marginBottom: '8px' }} />
              <p>Sin entidades extraídas. Ejecuta el NLP.</p>
            </div>
          )}
        </div>
      </div>

      {/* Info metodológica */}
      <div style={{ ...s.card, background: 'linear-gradient(135deg, #eef2ff, #f5f3ff)' }}>
        <div style={s.cardTitle}><BookOpen size={20} color="#4338ca" /> Metodología de IA/ML/NLP Aplicada</div>
        <div style={s.grid2}>
          <div>
            <h4 style={{ fontSize: '14px', color: '#1e293b', marginBottom: '8px' }}>Modelos de Machine Learning</h4>
            <ul style={{ fontSize: '13px', color: '#475569', lineHeight: 2, paddingLeft: '20px' }}>
              <li><strong>BETO</strong> (BERT en español): Análisis de sentimiento 3 clases</li>
              <li><strong>K-Means</strong>: Clustering de opiniones con selección automática de K</li>
              <li><strong>LDA</strong>: Latent Dirichlet Allocation para modelado de tópicos</li>
              <li><strong>Isolation Forest</strong>: Detección de anomalías multivariada</li>
            </ul>
          </div>
          <div>
            <h4 style={{ fontSize: '14px', color: '#1e293b', marginBottom: '8px' }}>Técnicas de NLP</h4>
            <ul style={{ fontSize: '13px', color: '#475569', lineHeight: 2, paddingLeft: '20px' }}>
              <li><strong>TF-IDF</strong>: Extracción de keywords con vectorización</li>
              <li><strong>NER</strong>: Reconocimiento de entidades (reglas + dominio)</li>
              <li><strong>ABSA</strong>: Análisis de sentimiento basado en aspectos</li>
              <li><strong>Tokenización</strong>: Procesamiento de texto en español</li>
            </ul>
          </div>
        </div>
      </div>

      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  );
};

export default NLPDashboard;
