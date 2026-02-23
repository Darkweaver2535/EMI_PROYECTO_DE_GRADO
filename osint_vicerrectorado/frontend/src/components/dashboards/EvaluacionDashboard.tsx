/**
 * ═══════════════════════════════════════════════════════════════
 * Dashboard de Evaluación del Sistema — OE4
 * ═══════════════════════════════════════════════════════════════
 * 
 * Muestra:
 * - Score general del sistema
 * - Cumplimiento de cada objetivo específico (OE1-OE4)
 * - Métricas de evaluación por categoría
 * - Resultados de pruebas de efectividad
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  ClipboardCheck,
  Award,
  Target,
  CheckCircle,
  AlertTriangle,
  XCircle,
  Zap,
  Loader2,
  BarChart3,
  TrendingUp,
  Shield,
  Database,
  Brain,
  Globe,
  Activity,
  RefreshCw,
} from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5001/api';

const CAT_ICONS: Record<string, React.ReactNode> = {
  recoleccion: <Database size={18} />,
  sentimiento: <Brain size={18} />,
  rendimiento: <Activity size={18} />,
  nlp_ml: <Brain size={18} />,
  completitud: <Database size={18} />,
  osint: <Globe size={18} />,
};

const CAT_COLORS: Record<string, string> = {
  recoleccion: '#3b82f6',
  sentimiento: '#8b5cf6',
  rendimiento: '#059669',
  nlp_ml: '#d97706',
  completitud: '#0891b2',
  osint: '#dc2626',
};

const OE_COLORS = ['#3b82f6', '#8b5cf6', '#059669', '#d97706'];

const s: Record<string, React.CSSProperties> = {
  page: { padding: '24px', backgroundColor: '#f0f4f8', minHeight: '100vh', fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif' },
  header: { background: 'linear-gradient(135deg, #14532d 0%, #166534 50%, #14532d 100%)', borderRadius: '16px', padding: '28px 32px', marginBottom: '24px', color: 'white' },
  headerTitle: { fontSize: '26px', fontWeight: 800, display: 'flex', alignItems: 'center', gap: '14px', marginBottom: '8px' },
  headerSub: { fontSize: '14px', color: '#86efac', marginBottom: '20px' },
  grid2: { display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '20px', marginBottom: '24px' },
  grid4: { display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px', marginBottom: '24px' },
  card: { backgroundColor: 'white', borderRadius: '16px', padding: '24px', boxShadow: '0 1px 3px rgba(0,0,0,0.08)', border: '1px solid #e2e8f0' },
  cardTitle: { fontSize: '16px', fontWeight: 700, color: '#1e293b', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '10px' },
  badge: { fontSize: '11px', fontWeight: 600, padding: '3px 8px', borderRadius: '6px', display: 'inline-flex', alignItems: 'center', gap: '4px' },
  btn: { padding: '10px 20px', borderRadius: '10px', border: 'none', backgroundColor: '#16a34a', color: 'white', fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '14px' },
  loading: { display: 'flex', flexDirection: 'column' as const, alignItems: 'center', justifyContent: 'center', padding: '80px 20px' },
  scoreCircle: { width: '120px', height: '120px', borderRadius: '50%', display: 'flex', flexDirection: 'column' as const, alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px' },
  prueba: { display: 'flex', alignItems: 'center', gap: '12px', padding: '10px 14px', borderRadius: '8px', marginBottom: '6px', backgroundColor: '#f8fafc', border: '1px solid #f1f5f9' },
  fullWidth: { gridColumn: '1 / -1' },
};

const EvaluacionDashboard: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [executing, setExecuting] = useState(false);
  const [evaluacion, setEvaluacion] = useState<any>(null);
  const [objetivos, setObjetivos] = useState<any>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [evalRes, objRes] = await Promise.all([
        fetch(`${API_URL}/evaluacion/resumen`).then(r => r.json()).catch(() => null),
        fetch(`${API_URL}/evaluacion/objetivos`).then(r => r.json()).catch(() => null),
      ]);
      setEvaluacion(evalRes);
      setObjetivos(objRes);
    } catch (err) {
      console.error('Error:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleExecuteEval = async () => {
    setExecuting(true);
    try {
      const resp = await fetch(`${API_URL}/evaluacion/ejecutar`, { method: 'POST' });
      if (resp.ok) {
        await fetchData();
      }
    } catch (err) {
      console.error('Error:', err);
    } finally {
      setExecuting(false);
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 70) return '#16a34a';
    if (score >= 40) return '#d97706';
    return '#dc2626';
  };

  const getStatusIcon = (estado: string) => {
    switch (estado) {
      case 'aprobado': return <CheckCircle size={16} color="#16a34a" />;
      case 'parcial': return <AlertTriangle size={16} color="#d97706" />;
      case 'fallido': case 'no ejecutado': return <XCircle size={16} color="#dc2626" />;
      default: return <AlertTriangle size={16} color="#94a3b8" />;
    }
  };

  if (loading) return (
    <div style={s.loading}>
      <Loader2 size={40} style={{ animation: 'spin 1s linear infinite' }} color="#16a34a" />
      <p style={{ marginTop: '16px', color: '#64748b' }}>Cargando evaluación...</p>
      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  );

  const scoreGeneral = evaluacion?.score_general || 0;
  const categorias = evaluacion?.categorias || {};

  return (
    <div style={s.page}>
      {/* Header */}
      <div style={s.header}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <div style={s.headerTitle}><ClipboardCheck size={28} /> Evaluación del Sistema</div>
            <p style={s.headerSub}>OE4: Evaluación del funcionamiento mediante pruebas de efectividad</p>
          </div>
          <button style={{ ...s.btn, backgroundColor: executing ? '#475569' : '#22c55e' }} onClick={handleExecuteEval} disabled={executing}>
            {executing ? <Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} /> : <Zap size={16} />}
            {executing ? 'Evaluando...' : 'Ejecutar Evaluación Completa'}
          </button>
        </div>
      </div>

      {/* Score general + Objetivos */}
      <div style={s.grid2}>
        {/* Score general */}
        <div style={s.card}>
          <div style={s.cardTitle}><Award size={20} color="#d97706" /> Score General del Sistema</div>
          <div style={{ ...s.scoreCircle, border: `6px solid ${getScoreColor(scoreGeneral)}`, backgroundColor: `${getScoreColor(scoreGeneral)}10` }}>
            <span style={{ fontSize: '32px', fontWeight: 800, color: getScoreColor(scoreGeneral) }}>{scoreGeneral}%</span>
          </div>
          <div style={{ textAlign: 'center', fontSize: '14px', color: '#64748b', marginBottom: '16px' }}>
            {scoreGeneral >= 70 ? 'Sistema funcionando correctamente' : scoreGeneral >= 40 ? 'Sistema parcialmente funcional' : 'Se requieren mejoras'}
          </div>

          {/* Categorías */}
          {Object.entries(categorias).map(([cat, score]: [string, any], i: number) => {
            const catScore = typeof score === 'number' ? score : 0;
            const color = CAT_COLORS[cat] || '#64748b';
            return (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '8px 12px', borderRadius: '8px', marginBottom: '6px', backgroundColor: '#f8fafc' }}>
                <div style={{ color }}>{CAT_ICONS[cat] || <BarChart3 size={18} />}</div>
                <span style={{ fontSize: '13px', fontWeight: 500, color: '#334155', flex: 1, textTransform: 'capitalize' }}>{cat.replace(/_/g, ' ')}</span>
                <div style={{ width: '120px', height: '6px', borderRadius: '3px', backgroundColor: '#e2e8f0', overflow: 'hidden' }}>
                  <div style={{ height: '100%', width: `${catScore}%`, backgroundColor: color, borderRadius: '3px' }} />
                </div>
                <span style={{ fontSize: '13px', fontWeight: 700, color, minWidth: '40px', textAlign: 'right' }}>{catScore}%</span>
              </div>
            );
          })}
          {Object.keys(categorias).length === 0 && (
            <p style={{ textAlign: 'center', color: '#94a3b8', fontSize: '13px' }}>Ejecuta la evaluación para ver resultados</p>
          )}
        </div>

        {/* Objetivos específicos */}
        <div style={s.card}>
          <div style={s.cardTitle}><Target size={20} color="#dc2626" /> Cumplimiento de Objetivos Específicos</div>
          {(objetivos?.objetivos || []).map((obj: any, i: number) => (
            <div key={i} style={{ padding: '16px', borderRadius: '12px', marginBottom: '12px', border: '1px solid #e2e8f0', borderLeft: `4px solid ${OE_COLORS[i]}` }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <span style={{ fontSize: '14px', fontWeight: 700, color: OE_COLORS[i] }}>{obj.id}</span>
                <span style={{ fontSize: '20px', fontWeight: 800, color: getScoreColor(obj.score) }}>{obj.score}%</span>
              </div>
              <div style={{ fontSize: '13px', color: '#334155', marginBottom: '10px', lineHeight: 1.4 }}>{obj.titulo}</div>
              <div style={{ width: '100%', height: '8px', borderRadius: '4px', backgroundColor: '#e2e8f0', overflow: 'hidden', marginBottom: '10px' }}>
                <div style={{ height: '100%', width: `${obj.score}%`, backgroundColor: getScoreColor(obj.score), borderRadius: '4px', transition: 'width 0.5s' }} />
              </div>
              <div style={{ fontSize: '11px', color: '#64748b' }}>
                {(obj.evidencias || []).slice(0, 4).map((e: string, j: number) => (
                  <div key={j} style={{ display: 'flex', gap: '6px', marginBottom: '3px' }}>
                    <CheckCircle size={12} color="#16a34a" style={{ flexShrink: 0, marginTop: '2px' }} />
                    <span>{e}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
          {(!objetivos?.objetivos || objetivos.objetivos.length === 0) && (
            <p style={{ textAlign: 'center', color: '#94a3b8', fontSize: '13px', padding: '20px' }}>
              Ejecuta la evaluación para ver el cumplimiento de objetivos
            </p>
          )}
          {objetivos?.score_general !== undefined && (
            <div style={{ textAlign: 'center', padding: '12px', borderRadius: '10px', backgroundColor: '#f0fdf4', border: '1px solid #bbf7d0' }}>
              <span style={{ fontSize: '13px', color: '#166534' }}>Cumplimiento General: </span>
              <span style={{ fontSize: '18px', fontWeight: 800, color: getScoreColor(objetivos.score_general) }}>{objetivos.score_general}%</span>
            </div>
          )}
        </div>
      </div>

      {/* Métricas detalladas */}
      {(evaluacion?.metricas || []).length > 0 && (
        <div style={{ ...s.card, marginBottom: '24px' }}>
          <div style={s.cardTitle}><BarChart3 size={20} color="#0891b2" /> Métricas de Evaluación Detalladas
            <span style={{ ...s.badge, backgroundColor: '#e0f2fe', color: '#0369a1', marginLeft: 'auto' }}>
              {(evaluacion?.metricas || []).length} métricas
            </span>
          </div>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
              <thead>
                <tr style={{ borderBottom: '2px solid #e2e8f0' }}>
                  <th style={{ padding: '10px 12px', textAlign: 'left', color: '#64748b', fontWeight: 600 }}>Métrica</th>
                  <th style={{ padding: '10px 12px', textAlign: 'left', color: '#64748b', fontWeight: 600 }}>Categoría</th>
                  <th style={{ padding: '10px 12px', textAlign: 'center', color: '#64748b', fontWeight: 600 }}>Score</th>
                  <th style={{ padding: '10px 12px', textAlign: 'left', color: '#64748b', fontWeight: 600 }}>Detalle</th>
                </tr>
              </thead>
              <tbody>
                {(evaluacion?.metricas || []).map((m: any, i: number) => (
                  <tr key={i} style={{ borderBottom: '1px solid #f1f5f9' }}>
                    <td style={{ padding: '8px 12px', color: '#334155', fontWeight: 500 }}>{m.metrica}</td>
                    <td style={{ padding: '8px 12px' }}>
                      <span style={{ ...s.badge, backgroundColor: `${CAT_COLORS[m.categoria] || '#64748b'}15`, color: CAT_COLORS[m.categoria] || '#64748b', textTransform: 'capitalize' }}>
                        {(m.categoria || '').replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td style={{ padding: '8px 12px', textAlign: 'center' }}>
                      <span style={{ fontWeight: 700, color: getScoreColor(m.valor) }}>{m.valor}%</span>
                    </td>
                    <td style={{ padding: '8px 12px', color: '#64748b', fontSize: '12px' }}>{m.detalle}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  );
};

export default EvaluacionDashboard;
