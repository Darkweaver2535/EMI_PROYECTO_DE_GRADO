import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Loader2,
  CheckCircle,
  AlertTriangle,
  X,
  Play,
  Pause,
  RefreshCw,
  MessageSquare,
  Video,
  Clock,
  Zap,
  ExternalLink,
  Shield,
} from 'lucide-react';

const API_URL = 'http://localhost:5001/api';

// Tipos
interface VideoInfo {
  id: number;
  description: string;
  comments_expected: number;
  comments_extracted: number;
}

interface ScrapingStats {
  videos_total: number;
  videos_processed: number;
  comments_total: number;
  comments_extracted: number;
  errors: number;
}

interface ScrapingEvent {
  type: string;
  message: string;
  data: Record<string, any>;
  timestamp: string;
}

interface TikTokScrapingModalProps {
  isOpen: boolean;
  onClose: () => void;
  sourceId: number;
  sourceName: string;
  onComplete: () => void;
}

// Estilos del modal
const styles: Record<string, React.CSSProperties> = {
  overlay: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1000,
    backdropFilter: 'blur(4px)',
  },
  modal: {
    backgroundColor: 'white',
    borderRadius: '16px',
    width: '90%',
    maxWidth: '700px',
    maxHeight: '85vh',
    overflow: 'hidden',
    display: 'flex',
    flexDirection: 'column',
    boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
  },
  header: {
    background: 'linear-gradient(135deg, #000 0%, #25F4EE 50%, #FE2C55 100%)',
    padding: '20px 24px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  headerTitle: {
    color: 'white',
    fontSize: '20px',
    fontWeight: 700,
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  },
  closeButton: {
    background: 'rgba(255,255,255,0.2)',
    border: 'none',
    borderRadius: '8px',
    padding: '8px',
    cursor: 'pointer',
    color: 'white',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    transition: 'background 0.2s',
  },
  content: {
    padding: '24px',
    overflowY: 'auto',
    flex: 1,
  },
  statusBanner: {
    padding: '16px 20px',
    borderRadius: '12px',
    marginBottom: '20px',
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  },
  statusBannerWaiting: {
    backgroundColor: '#fef3c7',
    border: '2px solid #f59e0b',
  },
  statusBannerRunning: {
    backgroundColor: '#dbeafe',
    border: '2px solid #3b82f6',
  },
  statusBannerComplete: {
    backgroundColor: '#dcfce7',
    border: '2px solid #22c55e',
  },
  statusBannerError: {
    backgroundColor: '#fee2e2',
    border: '2px solid #ef4444',
  },
  statusText: {
    flex: 1,
    fontSize: '15px',
    fontWeight: 500,
  },
  actionButton: {
    padding: '10px 20px',
    borderRadius: '8px',
    border: 'none',
    fontWeight: 600,
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    transition: 'all 0.2s',
    fontSize: '14px',
  },
  primaryButton: {
    backgroundColor: '#FE2C55',
    color: 'white',
  },
  secondaryButton: {
    backgroundColor: '#f1f5f9',
    color: '#475569',
  },
  statsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
    gap: '12px',
    marginBottom: '20px',
  },
  statCard: {
    backgroundColor: '#f8fafc',
    padding: '16px',
    borderRadius: '12px',
    textAlign: 'center' as const,
    border: '1px solid #e2e8f0',
  },
  statNumber: {
    fontSize: '28px',
    fontWeight: 700,
    color: '#1e293b',
  },
  statLabel: {
    fontSize: '12px',
    color: '#64748b',
    marginTop: '4px',
  },
  videosSection: {
    marginTop: '20px',
  },
  sectionTitle: {
    fontSize: '14px',
    fontWeight: 600,
    color: '#475569',
    marginBottom: '12px',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  videoItem: {
    display: 'flex',
    alignItems: 'center',
    padding: '12px 16px',
    backgroundColor: '#f8fafc',
    borderRadius: '8px',
    marginBottom: '8px',
    gap: '12px',
    border: '1px solid #e2e8f0',
  },
  videoItemActive: {
    backgroundColor: '#eff6ff',
    borderColor: '#3b82f6',
  },
  videoItemComplete: {
    backgroundColor: '#f0fdf4',
    borderColor: '#22c55e',
  },
  videoIcon: {
    width: '32px',
    height: '32px',
    borderRadius: '8px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  videoInfo: {
    flex: 1,
    minWidth: 0,
  },
  videoDescription: {
    fontSize: '13px',
    color: '#334155',
    whiteSpace: 'nowrap' as const,
    overflow: 'hidden',
    textOverflow: 'ellipsis',
  },
  videoStats: {
    fontSize: '12px',
    color: '#64748b',
    marginTop: '2px',
  },
  logSection: {
    marginTop: '20px',
    borderTop: '1px solid #e2e8f0',
    paddingTop: '20px',
  },
  logContainer: {
    backgroundColor: '#0f172a',
    borderRadius: '12px',
    padding: '16px',
    maxHeight: '200px',
    overflowY: 'auto' as const,
    fontFamily: 'Monaco, Consolas, monospace',
    fontSize: '12px',
  },
  logEntry: {
    color: '#94a3b8',
    marginBottom: '6px',
    lineHeight: 1.5,
  },
  logTimestamp: {
    color: '#64748b',
    marginRight: '8px',
  },
  footer: {
    padding: '16px 24px',
    borderTop: '1px solid #e2e8f0',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: '#f8fafc',
  },
  instructions: {
    backgroundColor: '#fef3c7',
    borderRadius: '12px',
    padding: '16px 20px',
    marginBottom: '20px',
    border: '1px solid #fcd34d',
  },
  instructionTitle: {
    fontWeight: 600,
    color: '#92400e',
    marginBottom: '8px',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  instructionList: {
    listStyle: 'decimal',
    paddingLeft: '20px',
    color: '#78350f',
    fontSize: '14px',
    lineHeight: 1.8,
  },
};

export const TikTokScrapingModal: React.FC<TikTokScrapingModalProps> = ({
  isOpen,
  onClose,
  sourceId,
  sourceName,
  onComplete,
}) => {
  // Estados
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [status, setStatus] = useState<'idle' | 'starting' | 'running' | 'waiting' | 'complete' | 'error'>('idle');
  const [stats, setStats] = useState<ScrapingStats>({
    videos_total: 0,
    videos_processed: 0,
    comments_total: 0,
    comments_extracted: 0,
    errors: 0,
  });
  const [videos, setVideos] = useState<VideoInfo[]>([]);
  const [currentVideoIndex, setCurrentVideoIndex] = useState<number>(-1);
  const [logs, setLogs] = useState<ScrapingEvent[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [waitingMessage, setWaitingMessage] = useState<string>('');
  
  // Refs
  const eventSourceRef = useRef<EventSource | null>(null);
  const logContainerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll logs
  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [logs]);

  // Limpiar al cerrar
  useEffect(() => {
    if (!isOpen) {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    }
  }, [isOpen]);

  // Manejar eventos SSE
  const handleEvent = useCallback((event: ScrapingEvent) => {
    setLogs(prev => [...prev, event]);

    switch (event.type) {
      case 'started':
        setStatus('running');
        break;
      
      case 'browser_opening':
        if (event.data.videos_info) {
          setVideos(event.data.videos_info);
        }
        break;
      
      case 'browser_ready':
        break;
      
      case 'captcha_detected':
      case 'waiting_user':
        setStatus('waiting');
        setWaitingMessage(event.message);
        break;
      
      case 'captcha_resolved':
        setStatus('running');
        setWaitingMessage('');
        break;
      
      case 'video_started':
        setCurrentVideoIndex(event.data.video_index - 1);
        break;
      
      case 'video_completed':
        if (event.data.stats) {
          setStats(event.data.stats);
        }
        // Actualizar video en la lista
        if (event.data.video_id) {
          setVideos(prev => prev.map(v => 
            v.id === event.data.video_id 
              ? { ...v, comments_extracted: v.comments_extracted + (event.data.comments_saved || 0) }
              : v
          ));
        }
        break;
      
      case 'completed':
        setStatus('complete');
        if (event.data.stats) {
          setStats(event.data.stats);
        }
        break;
      
      case 'error':
        if (event.message.includes('cancelado')) {
          setStatus('idle');
        } else {
          setStatus('error');
          setErrorMessage(event.message);
        }
        break;
    }
  }, []);

  // Iniciar scraping
  const startScraping = async () => {
    setStatus('starting');
    setLogs([]);
    setErrorMessage(null);
    setVideos([]);
    setCurrentVideoIndex(-1);
    setStats({
      videos_total: 0,
      videos_processed: 0,
      comments_total: 0,
      comments_extracted: 0,
      errors: 0,
    });

    try {
      // Iniciar sesión
      const res = await fetch(`${API_URL}/tiktok/scraping/start/${sourceId}`, {
        method: 'POST',
      });

      const data = await res.json();
      
      if (!res.ok) {
        throw new Error(data.error || 'Error al iniciar scraping');
      }

      setSessionId(data.session_id);
      setStatus('running');

      // Conectar a SSE
      const eventSource = new EventSource(`${API_URL}/tiktok/scraping/events/${data.session_id}`);
      eventSourceRef.current = eventSource;

      eventSource.onmessage = (e) => {
        try {
          const event = JSON.parse(e.data) as ScrapingEvent;
          handleEvent(event);
        } catch {
          // Ignorar eventos no parseables (heartbeats)
        }
      };

      eventSource.onerror = () => {
        // La conexión puede cerrarse normalmente al terminar
        if (status === 'running') {
          setStatus('error');
          setErrorMessage('Se perdió la conexión con el servidor');
        }
        eventSource.close();
      };

    } catch (err) {
      setStatus('error');
      setErrorMessage(err instanceof Error ? err.message : 'Error desconocido');
    }
  };

  // Continuar después de CAPTCHA
  const handleContinue = async () => {
    if (!sessionId) return;

    try {
      await fetch(`${API_URL}/tiktok/scraping/continue/${sessionId}`, {
        method: 'POST',
      });
      setStatus('running');
      setWaitingMessage('');
    } catch (err) {
      console.error('Error al continuar:', err);
    }
  };

  // Cancelar scraping
  const handleCancel = async () => {
    if (sessionId) {
      try {
        await fetch(`${API_URL}/tiktok/scraping/cancel/${sessionId}`, {
          method: 'POST',
        });
      } catch {
        // Ignorar errores al cancelar
      }
    }

    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    setStatus('idle');
  };

  // Cerrar modal
  const handleClose = () => {
    if (status === 'running' || status === 'waiting') {
      if (!confirm('¿Estás seguro de cancelar el scraping?')) {
        return;
      }
      handleCancel();
    }

    if (status === 'complete') {
      onComplete();
    }

    onClose();
  };

  // Formatear timestamp
  const formatTime = (timestamp: string) => {
    try {
      return new Date(timestamp).toLocaleTimeString();
    } catch {
      return '';
    }
  };

  // Obtener color del log
  const getLogColor = (type: string) => {
    switch (type) {
      case 'error': return '#ef4444';
      case 'completed': return '#22c55e';
      case 'captcha_detected':
      case 'waiting_user': return '#f59e0b';
      case 'video_completed': return '#22c55e';
      default: return '#94a3b8';
    }
  };

  if (!isOpen) return null;

  return (
    <div style={styles.overlay}>
      <div style={styles.modal}>
        {/* Header */}
        <div style={styles.header}>
          <div style={styles.headerTitle}>
            <Video size={24} />
            <span>Extracción de Comentarios TikTok</span>
          </div>
          <button
            style={styles.closeButton}
            onClick={handleClose}
            title="Cerrar"
          >
            <X size={20} />
          </button>
        </div>

        {/* Content */}
        <div style={styles.content}>
          {/* Estado inicial */}
          {status === 'idle' && (
            <>
              <div style={styles.instructions}>
                <div style={styles.instructionTitle}>
                  <Shield size={18} />
                  <span>Instrucciones Importantes</span>
                </div>
                <ol style={styles.instructionList}>
                  <li>Se abrirá un <strong>navegador visible</strong> con TikTok</li>
                  <li>Si aparece un <strong>CAPTCHA</strong>, resuélvelo manualmente</li>
                  <li>Luego presiona <strong>"Continuar"</strong> en esta ventana</li>
                  <li>El sistema extraerá los comentarios automáticamente</li>
                </ol>
              </div>

              <div style={{ textAlign: 'center', padding: '20px' }}>
                <p style={{ color: '#64748b', marginBottom: '20px' }}>
                  Se extraerán comentarios de la fuente: <strong>{sourceName}</strong>
                </p>
                <button
                  style={{ ...styles.actionButton, ...styles.primaryButton, margin: '0 auto' }}
                  onClick={startScraping}
                >
                  <Play size={18} />
                  Iniciar Extracción
                </button>
              </div>
            </>
          )}

          {/* Iniciando */}
          {status === 'starting' && (
            <div style={{ ...styles.statusBanner, ...styles.statusBannerRunning }}>
              <Loader2 size={24} style={{ animation: 'spin 1s linear infinite' }} color="#3b82f6" />
              <span style={styles.statusText}>Iniciando sesión de scraping...</span>
            </div>
          )}

          {/* Esperando usuario (CAPTCHA) */}
          {status === 'waiting' && (
            <>
              <div style={{ ...styles.statusBanner, ...styles.statusBannerWaiting }}>
                <AlertTriangle size={24} color="#f59e0b" />
                <span style={{ ...styles.statusText, color: '#92400e' }}>{waitingMessage}</span>
              </div>
              
              <div style={styles.instructions}>
                <div style={styles.instructionTitle}>
                  <Zap size={18} />
                  <span>Acción Requerida</span>
                </div>
                <ol style={styles.instructionList}>
                  <li>Busca el <strong>navegador de TikTok</strong> que se abrió</li>
                  <li>Resuelve el <strong>CAPTCHA o verificación</strong></li>
                  <li>Cuando hayas terminado, presiona el botón de abajo</li>
                </ol>
              </div>

              <div style={{ textAlign: 'center', marginTop: '20px' }}>
                <button
                  style={{ ...styles.actionButton, ...styles.primaryButton, margin: '0 auto' }}
                  onClick={handleContinue}
                >
                  <CheckCircle size={18} />
                  He Resuelto el CAPTCHA - Continuar
                </button>
              </div>
            </>
          )}

          {/* En progreso */}
          {status === 'running' && (
            <>
              <div style={{ ...styles.statusBanner, ...styles.statusBannerRunning }}>
                <Loader2 size={24} style={{ animation: 'spin 1s linear infinite' }} color="#3b82f6" />
                <span style={{ ...styles.statusText, color: '#1e40af' }}>
                  Extrayendo comentarios... No cierres el navegador.
                </span>
              </div>

              {/* Estadísticas */}
              <div style={styles.statsGrid}>
                <div style={styles.statCard}>
                  <div style={styles.statNumber}>{stats.videos_processed}/{stats.videos_total}</div>
                  <div style={styles.statLabel}>Videos Procesados</div>
                </div>
                <div style={styles.statCard}>
                  <div style={{ ...styles.statNumber, color: '#22c55e' }}>{stats.comments_extracted}</div>
                  <div style={styles.statLabel}>Comentarios Extraídos</div>
                </div>
                <div style={styles.statCard}>
                  <div style={{ ...styles.statNumber, color: stats.errors > 0 ? '#ef4444' : '#64748b' }}>{stats.errors}</div>
                  <div style={styles.statLabel}>Errores</div>
                </div>
              </div>

              {/* Lista de videos */}
              {videos.length > 0 && (
                <div style={styles.videosSection}>
                  <div style={styles.sectionTitle}>
                    <Video size={16} />
                    <span>Progreso por Video</span>
                  </div>
                  {videos.map((video, idx) => {
                    const isActive = idx === currentVideoIndex;
                    const isComplete = idx < currentVideoIndex;
                    
                    return (
                      <div
                        key={video.id}
                        style={{
                          ...styles.videoItem,
                          ...(isActive ? styles.videoItemActive : {}),
                          ...(isComplete ? styles.videoItemComplete : {}),
                        }}
                      >
                        <div
                          style={{
                            ...styles.videoIcon,
                            backgroundColor: isComplete ? '#dcfce7' : isActive ? '#dbeafe' : '#f1f5f9',
                          }}
                        >
                          {isComplete ? (
                            <CheckCircle size={18} color="#22c55e" />
                          ) : isActive ? (
                            <Loader2 size={18} color="#3b82f6" style={{ animation: 'spin 1s linear infinite' }} />
                          ) : (
                            <Clock size={18} color="#94a3b8" />
                          )}
                        </div>
                        <div style={styles.videoInfo}>
                          <div style={styles.videoDescription}>
                            {video.description || `Video ${video.id}`}
                          </div>
                          <div style={styles.videoStats}>
                            <MessageSquare size={12} style={{ verticalAlign: 'middle', marginRight: '4px' }} />
                            {video.comments_extracted}/{video.comments_expected} comentarios
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </>
          )}

          {/* Completado */}
          {status === 'complete' && (
            <>
              <div style={{ ...styles.statusBanner, ...styles.statusBannerComplete }}>
                <CheckCircle size={24} color="#22c55e" />
                <span style={{ ...styles.statusText, color: '#166534' }}>
                  ¡Extracción completada exitosamente!
                </span>
              </div>

              <div style={styles.statsGrid}>
                <div style={styles.statCard}>
                  <div style={styles.statNumber}>{stats.videos_processed}</div>
                  <div style={styles.statLabel}>Videos Procesados</div>
                </div>
                <div style={styles.statCard}>
                  <div style={{ ...styles.statNumber, color: '#22c55e' }}>{stats.comments_extracted}</div>
                  <div style={styles.statLabel}>Comentarios Nuevos</div>
                </div>
                <div style={styles.statCard}>
                  <div style={{ ...styles.statNumber, color: stats.errors > 0 ? '#ef4444' : '#64748b' }}>{stats.errors}</div>
                  <div style={styles.statLabel}>Errores</div>
                </div>
              </div>

              <div style={{ textAlign: 'center', marginTop: '20px' }}>
                <button
                  style={{ ...styles.actionButton, ...styles.primaryButton, margin: '0 auto' }}
                  onClick={handleClose}
                >
                  <CheckCircle size={18} />
                  Cerrar y Ver Resultados
                </button>
              </div>
            </>
          )}

          {/* Error */}
          {status === 'error' && (
            <>
              <div style={{ ...styles.statusBanner, ...styles.statusBannerError }}>
                <AlertTriangle size={24} color="#ef4444" />
                <span style={{ ...styles.statusText, color: '#991b1b' }}>
                  {errorMessage || 'Ocurrió un error durante la extracción'}
                </span>
              </div>

              <div style={{ textAlign: 'center', marginTop: '20px', display: 'flex', gap: '12px', justifyContent: 'center' }}>
                <button
                  style={{ ...styles.actionButton, ...styles.secondaryButton }}
                  onClick={handleClose}
                >
                  <X size={18} />
                  Cerrar
                </button>
                <button
                  style={{ ...styles.actionButton, ...styles.primaryButton }}
                  onClick={startScraping}
                >
                  <RefreshCw size={18} />
                  Reintentar
                </button>
              </div>
            </>
          )}

          {/* Logs */}
          {logs.length > 0 && (
            <div style={styles.logSection}>
              <div style={styles.sectionTitle}>
                <ExternalLink size={16} />
                <span>Registro de Actividad</span>
              </div>
              <div style={styles.logContainer} ref={logContainerRef}>
                {logs.map((log, idx) => (
                  <div key={idx} style={styles.logEntry}>
                    <span style={styles.logTimestamp}>[{formatTime(log.timestamp)}]</span>
                    <span style={{ color: getLogColor(log.type) }}>{log.message}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div style={styles.footer}>
          <span style={{ fontSize: '13px', color: '#64748b' }}>
            {sourceName}
          </span>
          {(status === 'running' || status === 'waiting') && (
            <button
              style={{ ...styles.actionButton, ...styles.secondaryButton }}
              onClick={handleCancel}
            >
              <Pause size={16} />
              Cancelar
            </button>
          )}
        </div>

        {/* CSS para animación de spin */}
        <style>{`
          @keyframes spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
          }
        `}</style>
      </div>
    </div>
  );
};

export default TikTokScrapingModal;
