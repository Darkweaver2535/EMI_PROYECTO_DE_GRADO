/**
 * Dashboard de Posts y Comentarios - Vista Jerárquica Principal
 * Estructura: Fuentes (Facebook/TikTok) → Posts → Comentarios
 * Incluye: CRUD de fuentes y Web Scraping REAL
 * 
 * Sistema de Analítica OSINT - EMI Bolivia
 * Trabajo de Grado - Versión Profesional
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  BarChart3,
  Database,
  FileText,
  MessageSquare,
  Plus,
  RefreshCw,
  Edit3,
  Trash2,
  Save,
  X,
  Clock,
  Heart,
  Download,
  User,
  CornerDownRight,
  AlertTriangle,
  Loader2,
  Globe,
  CheckCircle2,
  ThumbsUp,
  Minus,
  ThumbsDown,
  Facebook,
  Music2,
  ChevronRight,
  ArrowLeft,
  Info,
  Inbox
} from 'lucide-react';

// Modal de TikTok Scraping Interactivo
import TikTokScrapingModal from '../TikTokScrapingModal';

// Tipos
interface Source {
  id: number;
  name: string;
  platform: string;
  url: string;
  active: boolean;
  lastCollection: string | null;
  postsCount: number;
  commentsCount: number;
}

interface Post {
  id: number;
  sourceId: number;
  sourceName: string;
  platform: string;
  content: string;
  date: string;
  likes: number;
  commentsCount: number;
  collectedComments: number;
  shares: number;
  views: number;
  contentType: string;
  url: string;
  sentiment: string | null;
  aiConfidence: number | null;
}

interface Comment {
  id: number;
  postId: number;
  author: string;
  content: string;
  date: string;
  likes: number;
  repliesCount: number;
  isReply: boolean;
  parentCommentId: number | null;
  sentiment: {
    prediction: string;
    confidence: number;
    probabilities: {
      positive: number;
      neutral: number;
      negative: number;
    };
  } | null;
}

interface HierarchyStats {
  totals: {
    sources: number;
    posts: number;
    comments: number;
  };
  byPlatform: {
    platform: string;
    sources: number;
    posts: number;
    comments: number;
  }[];
  commentsSentiment: {
    positive: number;
    neutral: number;
    negative: number;
  };
}

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5001/api';

const PostsDashboard: React.FC = () => {
  // Estados principales
  const [sources, setSources] = useState<Source[]>([]);
  const [posts, setPosts] = useState<Post[]>([]);
  const [comments, setComments] = useState<Comment[]>([]);
  const [stats, setStats] = useState<HierarchyStats | null>(null);
  const [selectedSource, setSelectedSource] = useState<number | null>(null);
  const [selectedPost, setSelectedPost] = useState<Post | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingComments, setLoadingComments] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Estados para gestión de fuentes
  const [showAddSource, setShowAddSource] = useState(false);
  const [showEditSource, setShowEditSource] = useState<Source | null>(null);
  const [newSource, setNewSource] = useState({ name: '', platform: 'Facebook', url: '' });
  const [savingSource, setSavingSource] = useState(false);
  const [scrapingSource, setScrapingSource] = useState<number | null>(null);
  const [scrapingMessage, setScrapingMessage] = useState<string | null>(null);

  // Estado para modal de TikTok scraping interactivo
  const [tiktokScrapingModal, setTiktokScrapingModal] = useState<{
    isOpen: boolean;
    sourceId: number;
    sourceName: string;
  } | null>(null);

  // Cargar datos iniciales
  const fetchInitialData = useCallback(async () => {
    try {
      setLoading(true);
      const [sourcesRes, statsRes] = await Promise.all([
        fetch(`${API_URL}/sources`),
        fetch(`${API_URL}/hierarchy/stats`)
      ]);
      
      if (!sourcesRes.ok || !statsRes.ok) {
        throw new Error('Error al cargar datos');
      }
      
      const sourcesData = await sourcesRes.json();
      const statsData = await statsRes.json();
      
      setSources(sourcesData);
      setStats(statsData);
      await fetchPosts();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error desconocido');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchInitialData();
  }, [fetchInitialData]);

  // Cargar posts
  const fetchPosts = async (sourceId?: number) => {
    try {
      const url = sourceId 
        ? `${API_URL}/posts?source_id=${sourceId}&limit=50`
        : `${API_URL}/posts?limit=50`;
      
      const res = await fetch(url);
      if (!res.ok) throw new Error('Error al cargar posts');
      
      const data = await res.json();
      setPosts(data.posts);
    } catch (err) {
      console.error('Error fetching posts:', err);
    }
  };

  // Cargar comentarios de un post
  const fetchComments = async (postId: number) => {
    try {
      setLoadingComments(true);
      const res = await fetch(`${API_URL}/posts/${postId}/comments`);
      if (!res.ok) throw new Error('Error al cargar comentarios');
      
      const data = await res.json();
      setComments(data.comments);
    } catch (err) {
      console.error('Error fetching comments:', err);
    } finally {
      setLoadingComments(false);
    }
  };

  // ========== CRUD FUENTES ==========
  
  // Crear nueva fuente
  const handleCreateSource = async () => {
    if (!newSource.name || !newSource.url) {
      alert('Nombre y URL son requeridos');
      return;
    }

    setSavingSource(true);
    try {
      const res = await fetch(`${API_URL}/sources`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newSource)
      });

      const data = await res.json();
      
      if (!res.ok) {
        throw new Error(data.error || 'Error al crear fuente');
      }

      // Recargar fuentes
      await fetchInitialData();
      setShowAddSource(false);
      setNewSource({ name: '', platform: 'Facebook', url: '' });
      alert('Fuente creada exitosamente');
    } catch (err) {
      alert(`Error: ${err instanceof Error ? err.message : 'Error desconocido'}`);
    } finally {
      setSavingSource(false);
    }
  };

  // Actualizar fuente
  const handleUpdateSource = async () => {
    if (!showEditSource) return;

    setSavingSource(true);
    try {
      const res = await fetch(`${API_URL}/sources/${showEditSource.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: showEditSource.name,
          url: showEditSource.url,
          active: showEditSource.active
        })
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.error || 'Error al actualizar');
      }

      await fetchInitialData();
      setShowEditSource(null);
      alert('Fuente actualizada');
    } catch (err) {
      alert(`Error: ${err instanceof Error ? err.message : 'Error desconocido'}`);
    } finally {
      setSavingSource(false);
    }
  };

  // Eliminar fuente
  const handleDeleteSource = async (sourceId: number, sourceName: string) => {
    if (!confirm(`¿Eliminar "${sourceName}" y TODOS sus posts y comentarios?`)) {
      return;
    }

    try {
      const res = await fetch(`${API_URL}/sources/${sourceId}`, {
        method: 'DELETE'
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.error || 'Error al eliminar');
      }

      await fetchInitialData();
      if (selectedSource === sourceId) {
        setSelectedSource(null);
        setPosts([]);
      }
      alert('Fuente eliminada');
    } catch (err) {
      alert(`Error: ${err instanceof Error ? err.message : 'Error desconocido'}`);
    }
  };

  // ========== WEB SCRAPING ==========
  
  const handleRunScraping = async (sourceId: number) => {
    const source = sources.find(s => s.id === sourceId);
    if (!source) return;

    // Para TikTok, usar el modal interactivo
    if (source.platform.toLowerCase() === 'tiktok') {
      setTiktokScrapingModal({
        isOpen: true,
        sourceId: source.id,
        sourceName: source.name
      });
      return;
    }

    // Para otras plataformas (Facebook), usar el scraping normal
    if (!confirm(`¿Ejecutar Web Scraping para "${source.name}"?\n\nEsto buscará nuevos posts y comentarios en ${source.platform}.`)) {
      return;
    }

    setScrapingSource(sourceId);
    setScrapingMessage(`Iniciando scraping de ${source.name}...`);

    try {
      const res = await fetch(`${API_URL}/sources/${sourceId}/scrape`, {
        method: 'POST'
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.error || 'Error al iniciar scraping');
      }

      setScrapingMessage(`Scraping iniciado para ${source.name}. Esto puede tardar unos minutos...`);
      
      // Esperar y recargar datos
      setTimeout(async () => {
        await fetchInitialData();
        if (selectedSource === sourceId) {
          await fetchPosts(sourceId);
        }
        setScrapingSource(null);
        setScrapingMessage(`Scraping completado. Revisa los nuevos posts.`);
        
        setTimeout(() => setScrapingMessage(null), 5000);
      }, 10000);

    } catch (err) {
      setScrapingMessage(`Error: ${err instanceof Error ? err.message : 'Error desconocido'}`);
      setScrapingSource(null);
      setTimeout(() => setScrapingMessage(null), 5000);
    }
  };

  // Callback cuando el scraping de TikTok se completa
  const handleTikTokScrapingComplete = async () => {
    await fetchInitialData();
    if (tiktokScrapingModal && selectedSource === tiktokScrapingModal.sourceId) {
      await fetchPosts(tiktokScrapingModal.sourceId);
    }
    setScrapingMessage('✅ Extracción de comentarios TikTok completada');
    setTimeout(() => setScrapingMessage(null), 5000);
  };

  // Seleccionar fuente
  const handleSelectSource = (sourceId: number | null) => {
    setSelectedSource(sourceId);
    setSelectedPost(null);
    setComments([]);
    fetchPosts(sourceId || undefined);
  };

  // Seleccionar post
  const handleSelectPost = (post: Post) => {
    setSelectedPost(post);
    fetchComments(post.id);
  };

  // Formatear fecha
  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return 'Sin fecha';
    const date = new Date(dateStr);
    return date.toLocaleDateString('es-BO', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // Color por sentimiento
  const getSentimentColor = (sentiment: string | null) => {
    switch (sentiment?.toLowerCase()) {
      case 'positivo':
      case 'positive':
        return '#10b981';
      case 'negativo':
      case 'negative':
        return '#ef4444';
      default:
        return '#6b7280';
    }
  };

  // Icono de plataforma
  const PlatformIcon: React.FC<{ platform: string; size?: number }> = ({ platform, size = 16 }) => {
    switch (platform.toLowerCase()) {
      case 'facebook':
        return <Facebook size={size} color="#1877f2" />;
      case 'tiktok':
        return <Music2 size={size} color="#000000" />;
      default:
        return <Globe size={size} color="#6b7280" />;
    }
  };

  // Icono de sentimiento
  const SentimentIcon: React.FC<{ sentiment: string | null; size?: number }> = ({ sentiment, size = 14 }) => {
    switch (sentiment?.toLowerCase()) {
      case 'positivo':
      case 'positive':
        return <ThumbsUp size={size} color="#10b981" />;
      case 'negativo':
      case 'negative':
        return <ThumbsDown size={size} color="#ef4444" />;
      default:
        return <Minus size={size} color="#6b7280" />;
    }
  };

  if (loading) {
    return (
      <div style={styles.loading}>
        <Loader2 size={40} style={{ animation: 'spin 1s linear infinite' }} color="#4f46e5" />
        <p style={{ marginTop: '16px', color: '#64748b' }}>Cargando estructura de datos...</p>
        <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  if (error) {
    return (
      <div style={styles.error}>
        <AlertTriangle size={48} color="#dc2626" />
        <h3 style={{ margin: '16px 0 8px', color: '#dc2626' }}>Error</h3>
        <p>{error}</p>
        <button onClick={() => window.location.reload()} style={styles.retryButton}>
          <RefreshCw size={16} style={{ marginRight: '8px' }} />
          Reintentar
        </button>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      {/* Header con estadísticas */}
      <div style={styles.header}>
        <div style={styles.headerTop}>
          <div>
            <h1 style={styles.title}>
              <BarChart3 size={28} style={{ marginRight: '12px', verticalAlign: 'middle' }} />
              Posts y Comentarios de Estudiantes
            </h1>
            <p style={styles.subtitle}>
              Análisis jerárquico: Fuentes <ChevronRight size={14} style={{ verticalAlign: 'middle' }} /> Posts <ChevronRight size={14} style={{ verticalAlign: 'middle' }} /> Comentarios
            </p>
          </div>
          <button 
            onClick={() => setShowAddSource(true)}
            style={styles.addButton}
          >
            <Plus size={18} style={{ marginRight: '8px' }} />
            Agregar Fuente
          </button>
        </div>
        
        {/* Mensaje de scraping */}
        {scrapingMessage && (
          <div style={styles.scrapingMessage}>
            <RefreshCw size={16} style={{ marginRight: '8px', animation: scrapingSource ? 'spin 1s linear infinite' : 'none' }} />
            {scrapingMessage}
          </div>
        )}
        
        {stats && (
          <div style={styles.statsRow}>
            <div style={styles.statCard}>
              <Database size={20} color="#4f46e5" style={{ marginBottom: '8px' }} />
              <span style={styles.statNumber}>{stats.totals.sources}</span>
              <span style={styles.statLabel}>Fuentes</span>
            </div>
            <div style={styles.statCard}>
              <FileText size={20} color="#0891b2" style={{ marginBottom: '8px' }} />
              <span style={styles.statNumber}>{stats.totals.posts}</span>
              <span style={styles.statLabel}>Posts</span>
            </div>
            <div style={styles.statCard}>
              <MessageSquare size={20} color="#7c3aed" style={{ marginBottom: '8px' }} />
              <span style={styles.statNumber}>{stats.totals.comments}</span>
              <span style={styles.statLabel}>Comentarios</span>
            </div>
            <div style={{...styles.statCard, backgroundColor: '#dcfce7'}}>
              <ThumbsUp size={20} color="#16a34a" style={{ marginBottom: '8px' }} />
              <span style={{...styles.statNumber, color: '#16a34a'}}>{stats.commentsSentiment.positive}</span>
              <span style={styles.statLabel}>Positivos</span>
            </div>
            <div style={{...styles.statCard, backgroundColor: '#fef9c3'}}>
              <Minus size={20} color="#ca8a04" style={{ marginBottom: '8px' }} />
              <span style={{...styles.statNumber, color: '#ca8a04'}}>{stats.commentsSentiment.neutral}</span>
              <span style={styles.statLabel}>Neutrales</span>
            </div>
            <div style={{...styles.statCard, backgroundColor: '#fee2e2'}}>
              <ThumbsDown size={20} color="#dc2626" style={{ marginBottom: '8px' }} />
              <span style={{...styles.statNumber, color: '#dc2626'}}>{stats.commentsSentiment.negative}</span>
              <span style={styles.statLabel}>Negativos</span>
            </div>
          </div>
        )}
      </div>

      {/* Modal Agregar Fuente */}
      {showAddSource && (
        <div style={styles.modalOverlay}>
          <div style={styles.modal}>
            <h2 style={styles.modalTitle}>
              <Plus size={20} style={{ marginRight: '8px' }} />
              Agregar Nueva Fuente de Web Scraping
            </h2>
            
            <div style={styles.formGroup}>
              <label style={styles.label}>Nombre de la fuente:</label>
              <input
                type="text"
                value={newSource.name}
                onChange={(e) => setNewSource({...newSource, name: e.target.value})}
                placeholder="Ej: EMI Oficial Facebook"
                style={styles.input}
              />
            </div>

            <div style={styles.formGroup}>
              <label style={styles.label}>Plataforma:</label>
              <select
                value={newSource.platform}
                onChange={(e) => setNewSource({...newSource, platform: e.target.value})}
                style={styles.select}
              >
                <option value="Facebook">Facebook</option>
                <option value="TikTok">TikTok</option>
              </select>
            </div>

            <div style={styles.formGroup}>
              <label style={styles.label}>URL de la página/perfil:</label>
              <input
                type="url"
                value={newSource.url}
                onChange={(e) => setNewSource({...newSource, url: e.target.value})}
                placeholder="https://www.facebook.com/..."
                style={styles.input}
              />
              <small style={styles.hint}>
                Facebook: URL de la página pública | TikTok: URL del perfil (@usuario)
              </small>
            </div>

            <div style={styles.modalButtons}>
              <button 
                onClick={() => setShowAddSource(false)}
                style={styles.cancelButton}
              >
                <X size={16} style={{ marginRight: '6px' }} />
                Cancelar
              </button>
              <button 
                onClick={handleCreateSource}
                disabled={savingSource}
                style={styles.saveButton}
              >
                {savingSource ? (
                  <Loader2 size={16} style={{ marginRight: '6px', animation: 'spin 1s linear infinite' }} />
                ) : (
                  <Save size={16} style={{ marginRight: '6px' }} />
                )}
                {savingSource ? 'Guardando...' : 'Guardar Fuente'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal Editar Fuente */}
      {showEditSource && (
        <div style={styles.modalOverlay}>
          <div style={styles.modal}>
            <h2 style={styles.modalTitle}>
              <Edit3 size={20} style={{ marginRight: '8px' }} />
              Editar Fuente
            </h2>
            
            <div style={styles.formGroup}>
              <label style={styles.label}>Nombre:</label>
              <input
                type="text"
                value={showEditSource.name}
                onChange={(e) => setShowEditSource({...showEditSource, name: e.target.value})}
                style={styles.input}
              />
            </div>

            <div style={styles.formGroup}>
              <label style={styles.label}>URL:</label>
              <input
                type="url"
                value={showEditSource.url}
                onChange={(e) => setShowEditSource({...showEditSource, url: e.target.value})}
                style={styles.input}
              />
            </div>

            <div style={styles.formGroup}>
              <label style={styles.checkboxLabel}>
                <input
                  type="checkbox"
                  checked={showEditSource.active}
                  onChange={(e) => setShowEditSource({...showEditSource, active: e.target.checked})}
                  style={{ marginRight: '8px' }}
                />
                Fuente activa
              </label>
            </div>

            <div style={styles.modalButtons}>
              <button 
                onClick={() => setShowEditSource(null)}
                style={styles.cancelButton}
              >
                <X size={16} style={{ marginRight: '6px' }} />
                Cancelar
              </button>
              <button 
                onClick={handleUpdateSource}
                disabled={savingSource}
                style={styles.saveButton}
              >
                {savingSource ? (
                  <Loader2 size={16} style={{ marginRight: '6px', animation: 'spin 1s linear infinite' }} />
                ) : (
                  <Save size={16} style={{ marginRight: '6px' }} />
                )}
                {savingSource ? 'Guardando...' : 'Actualizar'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Layout de 3 columnas */}
      <div style={styles.threeColumns}>
        {/* Columna 1: Fuentes */}
        <div style={styles.column}>
          <h2 style={styles.columnTitle}>
            <Database size={18} style={{ marginRight: '8px' }} />
            Fuentes de Datos
          </h2>
          
          <button
            onClick={() => handleSelectSource(null)}
            style={{
              ...styles.sourceItem,
              backgroundColor: selectedSource === null ? '#e0e7ff' : 'white'
            }}
          >
            <span style={{ display: 'flex', alignItems: 'center' }}>
              <Globe size={16} style={{ marginRight: '8px' }} />
              Todas las fuentes
            </span>
            <span style={styles.badge}>{stats?.totals.sources || 0}</span>
          </button>
          
          {sources.map(source => (
            <div
              key={source.id}
              style={{
                ...styles.sourceCard,
                backgroundColor: selectedSource === source.id ? '#e0e7ff' : 'white',
                opacity: source.active ? 1 : 0.6
              }}
            >
              <div 
                onClick={() => handleSelectSource(source.id)}
                style={styles.sourceInfo}
              >
                <div style={styles.sourceName}>
                  <PlatformIcon platform={source.platform} />
                  <span style={{ marginLeft: '8px' }}>{source.name}</span>
                  {!source.active && <span style={styles.inactiveBadge}> (inactiva)</span>}
                </div>
                <div style={styles.sourceStats}>
                  <span style={styles.sourceStatItem}>
                    <FileText size={12} />
                    <span>{source.postsCount} posts</span>
                  </span>
                  <span style={styles.sourceStatItem}>
                    <MessageSquare size={12} />
                    <span>{source.commentsCount} comentarios</span>
                  </span>
                </div>
                {source.lastCollection && (
                  <div style={styles.lastScrape}>
                    <Clock size={11} />
                    <span style={{ marginLeft: '4px' }}>Último: {formatDate(source.lastCollection)}</span>
                  </div>
                )}
              </div>
              
              <div style={styles.sourceActions}>
                <button
                  onClick={() => handleRunScraping(source.id)}
                  disabled={scrapingSource === source.id}
                  style={{
                    ...styles.scrapeButton,
                    opacity: scrapingSource === source.id ? 0.5 : 1
                  }}
                  title="Ejecutar Web Scraping"
                >
                  {scrapingSource === source.id ? (
                    <Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} />
                  ) : (
                    <RefreshCw size={14} />
                  )}
                </button>
                <button
                  onClick={() => setShowEditSource(source)}
                  style={styles.editButton}
                  title="Editar fuente"
                >
                  <Edit3 size={14} />
                </button>
                <button
                  onClick={() => handleDeleteSource(source.id, source.name)}
                  style={styles.deleteButton}
                  title="Eliminar fuente"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
          ))}

          {sources.length === 0 && (
            <div style={styles.emptyState}>
              <Inbox size={40} color="#94a3b8" />
              <p>No hay fuentes configuradas</p>
              <button 
                onClick={() => setShowAddSource(true)}
                style={styles.addSourceSmall}
              >
                <Plus size={14} style={{ marginRight: '6px' }} />
                Agregar primera fuente
              </button>
            </div>
          )}
        </div>

        {/* Columna 2: Posts */}
        <div style={styles.column}>
          <div style={styles.columnHeader}>
            <h2 style={styles.columnTitle}>
              <FileText size={18} style={{ marginRight: '8px' }} />
              Posts {selectedSource ? `(${sources.find(s => s.id === selectedSource)?.name || ''})` : '(Todos)'}
            </h2>
            {selectedSource && (
              <button
                onClick={() => handleRunScraping(selectedSource)}
                disabled={scrapingSource !== null}
                style={styles.updateButton}
              >
                <RefreshCw size={14} style={{ marginRight: '6px' }} />
                Actualizar
              </button>
            )}
          </div>
          
          <div style={styles.postsList}>
            {posts.length === 0 ? (
              <div style={styles.emptyState}>
                <Inbox size={40} color="#94a3b8" />
                <p>No hay posts disponibles</p>
                <small>Ejecuta el Web Scraping para obtener posts</small>
              </div>
            ) : (
              posts.map(post => (
                <div
                  key={post.id}
                  onClick={() => handleSelectPost(post)}
                  style={{
                    ...styles.postCard,
                    borderLeft: `4px solid ${getSentimentColor(post.sentiment)}`,
                    backgroundColor: selectedPost?.id === post.id ? '#f0f9ff' : 'white'
                  }}
                >
                  <div style={styles.postHeader}>
                    <span style={styles.platformBadge}>
                      <PlatformIcon platform={post.platform} size={14} />
                      <span style={{ marginLeft: '6px' }}>{post.sourceName}</span>
                    </span>
                    <span style={styles.postDate}>
                      <Clock size={11} style={{ marginRight: '4px' }} />
                      {formatDate(post.date)}
                    </span>
                  </div>
                  
                  <p style={styles.postContent}>
                    {post.content.length > 150 
                      ? post.content.substring(0, 150) + '...' 
                      : post.content}
                  </p>
                  
                  <div style={styles.postFooter}>
                    <span style={styles.footerItem}>
                      <Heart size={12} />
                      <span>{post.likes}</span>
                    </span>
                    <span style={styles.footerItem}>
                      <MessageSquare size={12} />
                      <span>{post.commentsCount}</span>
                    </span>
                    <span style={styles.footerItem}>
                      <Download size={12} />
                      <span>{post.collectedComments} recolectados</span>
                    </span>
                    {post.sentiment && (
                      <span style={{
                        ...styles.sentimentBadge,
                        backgroundColor: getSentimentColor(post.sentiment) + '20',
                        color: getSentimentColor(post.sentiment)
                      }}>
                        <SentimentIcon sentiment={post.sentiment} />
                        <span style={{ marginLeft: '4px' }}>{post.sentiment}</span>
                      </span>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Columna 3: Comentarios */}
        <div style={styles.column}>
          <h2 style={styles.columnTitle}>
            <MessageSquare size={18} style={{ marginRight: '8px' }} />
            Comentarios {selectedPost ? `(Post #${selectedPost.id})` : ''}
          </h2>
          
          {!selectedPost ? (
            <div style={styles.emptyState}>
              <ArrowLeft size={40} color="#94a3b8" />
              <p>Selecciona un post</p>
              <small>Los comentarios aparecerán aquí</small>
            </div>
          ) : loadingComments ? (
            <div style={styles.loading}>
              <Loader2 size={32} style={{ animation: 'spin 1s linear infinite' }} color="#4f46e5" />
              <p style={{ marginTop: '12px' }}>Cargando comentarios...</p>
            </div>
          ) : comments.length === 0 ? (
            <div style={styles.emptyState}>
              <Inbox size={40} color="#94a3b8" />
              <p>Sin comentarios recolectados</p>
              <small>
                Este post tiene {selectedPost.commentsCount} comentarios.
                Ejecuta el scraping para obtenerlos.
              </small>
            </div>
          ) : (
            <div style={styles.commentsList}>
              {comments.map(comment => (
                <div
                  key={comment.id}
                  style={{
                    ...styles.commentCard,
                    borderLeft: `3px solid ${getSentimentColor(comment.sentiment?.prediction || null)}`
                  }}
                >
                  <div style={styles.commentHeader}>
                    <span style={styles.commentAuthor}>
                      <User size={12} />
                      <span style={{ marginLeft: '6px' }}>{comment.author || 'Anónimo'}</span>
                    </span>
                    <span style={styles.commentDate}>
                      <Clock size={10} style={{ marginRight: '4px' }} />
                      {formatDate(comment.date)}
                    </span>
                  </div>
                  
                  <p style={styles.commentContent}>{comment.content}</p>
                  
                  <div style={styles.commentFooter}>
                    <span style={styles.footerItem}>
                      <Heart size={11} />
                      <span>{comment.likes}</span>
                    </span>
                    {comment.repliesCount > 0 && (
                      <span style={styles.footerItem}>
                        <CornerDownRight size={11} />
                        <span>{comment.repliesCount}</span>
                      </span>
                    )}
                    {comment.sentiment && (
                      <span style={{
                        ...styles.sentimentBadge,
                        backgroundColor: getSentimentColor(comment.sentiment.prediction) + '20',
                        color: getSentimentColor(comment.sentiment.prediction)
                      }}>
                        <SentimentIcon sentiment={comment.sentiment.prediction} />
                        <span style={{ marginLeft: '4px' }}>
                          {comment.sentiment.prediction}
                          {comment.sentiment.confidence && 
                            ` (${Math.round(comment.sentiment.confidence * 100)}%)`
                          }
                        </span>
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Instrucciones */}
      <div style={styles.infoBox}>
        <h3 style={styles.infoTitle}>
          <Info size={18} style={{ marginRight: '8px' }} />
          Guía de uso del sistema
        </h3>
        <ol style={styles.infoList}>
          <li><strong>Agregar Fuente:</strong> Crea una nueva fuente con la URL de Facebook o TikTok</li>
          <li><strong>Web Scraping:</strong> Haz clic en el icono de actualización para extraer posts y comentarios reales</li>
          <li><strong>Explorar:</strong> Selecciona una fuente, luego un post, para ver los comentarios</li>
          <li><strong>Análisis:</strong> El sistema analiza automáticamente los sentimientos de los comentarios</li>
        </ol>
      </div>

      {/* Modal de TikTok Scraping Interactivo */}
      {tiktokScrapingModal && (
        <TikTokScrapingModal
          isOpen={tiktokScrapingModal.isOpen}
          onClose={() => setTiktokScrapingModal(null)}
          sourceId={tiktokScrapingModal.sourceId}
          sourceName={tiktokScrapingModal.sourceName}
          onComplete={handleTikTokScrapingComplete}
        />
      )}

      {/* Estilos de animación */}
      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};

// Estilos
const styles: { [key: string]: React.CSSProperties } = {
  container: {
    padding: '24px',
    backgroundColor: '#f8fafc',
    minHeight: '100vh',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
  },
  header: {
    marginBottom: '24px'
  },
  headerTop: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: '20px'
  },
  title: {
    fontSize: '26px',
    fontWeight: '600',
    color: '#1e293b',
    margin: '0 0 8px 0',
    display: 'flex',
    alignItems: 'center'
  },
  subtitle: {
    color: '#64748b',
    margin: 0,
    fontSize: '14px',
    display: 'flex',
    alignItems: 'center',
    gap: '4px'
  },
  addButton: {
    backgroundColor: '#4f46e5',
    color: 'white',
    border: 'none',
    padding: '12px 20px',
    borderRadius: '8px',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: '500',
    display: 'flex',
    alignItems: 'center',
    transition: 'background-color 0.2s'
  },
  scrapingMessage: {
    backgroundColor: '#dbeafe',
    border: '1px solid #93c5fd',
    color: '#1e40af',
    padding: '12px 16px',
    borderRadius: '8px',
    marginBottom: '16px',
    display: 'flex',
    alignItems: 'center',
    fontSize: '14px'
  },
  statsRow: {
    display: 'flex',
    gap: '12px',
    flexWrap: 'wrap'
  },
  statCard: {
    backgroundColor: 'white',
    padding: '16px 24px',
    borderRadius: '10px',
    boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    minWidth: '110px',
    border: '1px solid #e2e8f0'
  },
  statNumber: {
    fontSize: '28px',
    fontWeight: '700',
    color: '#1e293b'
  },
  statLabel: {
    fontSize: '12px',
    color: '#64748b',
    marginTop: '4px',
    textTransform: 'uppercase',
    letterSpacing: '0.5px'
  },
  threeColumns: {
    display: 'grid',
    gridTemplateColumns: '320px 1fr 1fr',
    gap: '20px',
    marginBottom: '24px'
  },
  column: {
    backgroundColor: 'white',
    borderRadius: '12px',
    padding: '20px',
    boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
    maxHeight: 'calc(100vh - 340px)',
    overflowY: 'auto',
    border: '1px solid #e2e8f0'
  },
  columnHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '16px',
    paddingBottom: '12px',
    borderBottom: '1px solid #e2e8f0'
  },
  columnTitle: {
    fontSize: '15px',
    fontWeight: '600',
    color: '#1e293b',
    margin: 0,
    display: 'flex',
    alignItems: 'center'
  },
  updateButton: {
    backgroundColor: '#f0f9ff',
    color: '#0369a1',
    border: '1px solid #bae6fd',
    padding: '6px 12px',
    borderRadius: '6px',
    cursor: 'pointer',
    fontSize: '12px',
    display: 'flex',
    alignItems: 'center',
    fontWeight: '500'
  },
  sourceItem: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    width: '100%',
    padding: '12px 14px',
    border: '1px solid #e2e8f0',
    borderRadius: '8px',
    cursor: 'pointer',
    marginBottom: '10px',
    textAlign: 'left',
    backgroundColor: 'white',
    fontSize: '14px',
    transition: 'all 0.2s'
  },
  sourceCard: {
    border: '1px solid #e2e8f0',
    borderRadius: '8px',
    marginBottom: '10px',
    padding: '14px',
    transition: 'all 0.2s'
  },
  sourceInfo: {
    cursor: 'pointer',
    marginBottom: '10px'
  },
  sourceName: {
    fontWeight: '500',
    marginBottom: '6px',
    display: 'flex',
    alignItems: 'center',
    fontSize: '14px'
  },
  inactiveBadge: {
    color: '#94a3b8',
    fontSize: '11px',
    marginLeft: '6px'
  },
  sourceStats: {
    display: 'flex',
    gap: '14px',
    fontSize: '12px',
    color: '#64748b'
  },
  sourceStatItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '4px'
  },
  lastScrape: {
    fontSize: '11px',
    color: '#94a3b8',
    marginTop: '6px',
    display: 'flex',
    alignItems: 'center'
  },
  sourceActions: {
    display: 'flex',
    gap: '6px',
    borderTop: '1px solid #e2e8f0',
    paddingTop: '10px'
  },
  scrapeButton: {
    backgroundColor: '#dbeafe',
    border: 'none',
    padding: '8px 10px',
    borderRadius: '6px',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: '#1d4ed8',
    transition: 'background-color 0.2s'
  },
  editButton: {
    backgroundColor: '#fef3c7',
    border: 'none',
    padding: '8px 10px',
    borderRadius: '6px',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: '#92400e',
    transition: 'background-color 0.2s'
  },
  deleteButton: {
    backgroundColor: '#fee2e2',
    border: 'none',
    padding: '8px 10px',
    borderRadius: '6px',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: '#dc2626',
    transition: 'background-color 0.2s'
  },
  badge: {
    backgroundColor: '#e0e7ff',
    color: '#4f46e5',
    padding: '3px 10px',
    borderRadius: '12px',
    fontSize: '12px',
    fontWeight: '600'
  },
  postsList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px'
  },
  postCard: {
    padding: '14px',
    border: '1px solid #e2e8f0',
    borderRadius: '8px',
    cursor: 'pointer',
    transition: 'all 0.2s'
  },
  postHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '10px'
  },
  platformBadge: {
    fontSize: '12px',
    color: '#64748b',
    display: 'flex',
    alignItems: 'center'
  },
  postDate: {
    fontSize: '11px',
    color: '#94a3b8',
    display: 'flex',
    alignItems: 'center'
  },
  postContent: {
    fontSize: '13px',
    color: '#334155',
    margin: '0 0 10px 0',
    lineHeight: '1.5'
  },
  postFooter: {
    display: 'flex',
    gap: '14px',
    fontSize: '11px',
    color: '#64748b',
    alignItems: 'center',
    flexWrap: 'wrap'
  },
  footerItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '4px'
  },
  sentimentBadge: {
    padding: '3px 10px',
    borderRadius: '12px',
    fontSize: '11px',
    fontWeight: '500',
    display: 'flex',
    alignItems: 'center'
  },
  commentsList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '10px'
  },
  commentCard: {
    padding: '12px',
    backgroundColor: '#f8fafc',
    borderRadius: '8px'
  },
  commentHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '8px'
  },
  commentAuthor: {
    fontSize: '12px',
    fontWeight: '500',
    color: '#334155',
    display: 'flex',
    alignItems: 'center'
  },
  commentDate: {
    fontSize: '10px',
    color: '#94a3b8',
    display: 'flex',
    alignItems: 'center'
  },
  commentContent: {
    fontSize: '13px',
    color: '#1e293b',
    margin: '0 0 8px 0',
    lineHeight: '1.4'
  },
  commentFooter: {
    display: 'flex',
    gap: '12px',
    fontSize: '11px',
    color: '#64748b',
    alignItems: 'center',
    flexWrap: 'wrap'
  },
  emptyState: {
    textAlign: 'center',
    padding: '40px 20px',
    color: '#64748b',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '8px'
  },
  addSourceSmall: {
    backgroundColor: '#4f46e5',
    color: 'white',
    border: 'none',
    padding: '10px 16px',
    borderRadius: '6px',
    cursor: 'pointer',
    marginTop: '8px',
    display: 'flex',
    alignItems: 'center',
    fontSize: '13px',
    fontWeight: '500'
  },
  loading: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '60px 40px',
    color: '#64748b'
  },
  error: {
    textAlign: 'center',
    padding: '60px',
    backgroundColor: '#fef2f2',
    borderRadius: '12px',
    margin: '40px',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center'
  },
  retryButton: {
    backgroundColor: '#4f46e5',
    color: 'white',
    border: 'none',
    padding: '12px 20px',
    borderRadius: '8px',
    cursor: 'pointer',
    marginTop: '16px',
    display: 'flex',
    alignItems: 'center',
    fontSize: '14px',
    fontWeight: '500'
  },
  modalOverlay: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0,0,0,0.5)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1000
  },
  modal: {
    backgroundColor: 'white',
    borderRadius: '12px',
    padding: '28px',
    width: '90%',
    maxWidth: '480px',
    boxShadow: '0 20px 25px -5px rgba(0,0,0,0.15)'
  },
  modalTitle: {
    fontSize: '18px',
    fontWeight: '600',
    marginBottom: '24px',
    color: '#1e293b',
    display: 'flex',
    alignItems: 'center'
  },
  formGroup: {
    marginBottom: '18px'
  },
  label: {
    display: 'block',
    fontSize: '13px',
    fontWeight: '500',
    color: '#374151',
    marginBottom: '6px'
  },
  checkboxLabel: {
    display: 'flex',
    alignItems: 'center',
    fontSize: '14px',
    color: '#374151',
    cursor: 'pointer'
  },
  input: {
    width: '100%',
    padding: '10px 14px',
    border: '1px solid #d1d5db',
    borderRadius: '8px',
    fontSize: '14px',
    boxSizing: 'border-box',
    transition: 'border-color 0.2s'
  },
  select: {
    width: '100%',
    padding: '10px 14px',
    border: '1px solid #d1d5db',
    borderRadius: '8px',
    fontSize: '14px',
    boxSizing: 'border-box',
    backgroundColor: 'white'
  },
  hint: {
    fontSize: '12px',
    color: '#6b7280',
    marginTop: '6px',
    display: 'block'
  },
  modalButtons: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: '12px',
    marginTop: '28px'
  },
  cancelButton: {
    backgroundColor: '#f3f4f6',
    color: '#4b5563',
    border: 'none',
    padding: '10px 18px',
    borderRadius: '8px',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    fontSize: '14px',
    fontWeight: '500'
  },
  saveButton: {
    backgroundColor: '#4f46e5',
    color: 'white',
    border: 'none',
    padding: '10px 18px',
    borderRadius: '8px',
    cursor: 'pointer',
    fontWeight: '500',
    display: 'flex',
    alignItems: 'center',
    fontSize: '14px'
  },
  infoBox: {
    backgroundColor: '#f0f9ff',
    border: '1px solid #bae6fd',
    borderRadius: '12px',
    padding: '20px 24px'
  },
  infoTitle: {
    fontSize: '15px',
    fontWeight: '600',
    color: '#0c4a6e',
    margin: '0 0 12px 0',
    display: 'flex',
    alignItems: 'center'
  },
  infoList: {
    margin: '0',
    paddingLeft: '20px',
    color: '#0369a1',
    fontSize: '13px',
    lineHeight: '1.8'
  }
};

export default PostsDashboard;
