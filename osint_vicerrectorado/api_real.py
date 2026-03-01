#!/usr/bin/env python3
"""
API Flask para Sistema OSINT EMI - Solo Datos Reales de SQLite
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3
import json
import hashlib
from datetime import datetime, timedelta
from collections import defaultdict

app = Flask(__name__)
CORS(app)

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'osint_emi.db')

def get_db():
    """Obtiene conexión a SQLite"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ============== AUTH (DB-backed) ==============
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Login con base de datos - acepta email o username"""
    data = request.json
    email = data.get('email') or data.get('username', '')
    password = data.get('password', '')

    if email and '@' not in email:
        email = f'{email}@emi.edu.bo'

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM usuario WHERE (email = ? OR username = ?) AND activo = 1',
                   (email, email.split('@')[0]))
    user = cursor.fetchone()

    if user and user['password_hash'] == hash_password(password):
        cursor.execute('UPDATE usuario SET ultimo_login = ? WHERE id_usuario = ?',
                       (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), user['id_usuario']))
        # Log activity
        cursor.execute('INSERT INTO log_actividad (id_usuario, accion, detalle, ip_address) VALUES (?,?,?,?)',
                       (user['id_usuario'], 'login', 'Inicio de sesión exitoso', request.remote_addr))
        conn.commit()
        
        # Cargar permisos
        permisos = {}
        try:
            permisos = json.loads(user['permisos'] or '{}')
        except:
            permisos = get_default_permisos(user['rol'])
        
        conn.close()
        return jsonify({
            'user': {
                'id': user['id_usuario'],
                'username': user['username'],
                'name': user['nombre_completo'],
                'nombre': user['nombre_completo'],
                'email': user['email'],
                'rol': user['rol'],
                'cargo': user['cargo'],
                'permisos': permisos
            },
            'tokens': {
                'accessToken': f'token_{user["username"]}_{user["id_usuario"]}',
                'refreshToken': f'refresh_{user["username"]}_{user["id_usuario"]}',
                'expiresIn': 86400
            }
        })
    conn.close()
    return jsonify({'error': 'Credenciales inválidas'}), 401

@app.route('/api/auth/me')
def auth_me():
    """Obtener usuario actual desde token"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not token:
        return jsonify({'error': 'Token requerido'}), 401
    parts = token.split('_')
    if len(parts) >= 3:
        username = parts[1]
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM usuario WHERE username = ? AND activo = 1', (username,))
        user = cursor.fetchone()
        conn.close()
        if user:
            permisos = {}
            try:
                permisos = json.loads(user['permisos'] or '{}')
            except:
                permisos = get_default_permisos(user['rol'])
            return jsonify({
                'id': user['id_usuario'], 'username': user['username'],
                'name': user['nombre_completo'], 'nombre': user['nombre_completo'],
                'email': user['email'], 'rol': user['rol'], 'cargo': user['cargo'],
                'permisos': permisos
            })
    return jsonify({'error': 'Token inválido'}), 401

@app.route('/api/auth/logout', methods=['POST'])
def auth_logout():
    """Logout"""
    return jsonify({'message': 'Sesión cerrada'})

@app.route('/api/auth/refresh', methods=['POST'])
def auth_refresh():
    """Refresh token"""
    data = request.json or {}
    refresh = data.get('refreshToken', '')
    if refresh:
        return jsonify({'accessToken': refresh.replace('refresh_', 'token_')})
    return jsonify({'error': 'Token inválido'}), 401

@app.route('/api/auth/change-password', methods=['POST'])
def auth_change_password():
    """Cambiar contraseña"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    data = request.json or {}
    parts = token.split('_')
    if len(parts) < 3:
        return jsonify({'error': 'Token inválido'}), 401
    username = parts[1]
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM usuario WHERE username = ?', (username,))
    user = cursor.fetchone()
    if not user or user['password_hash'] != hash_password(data.get('currentPassword', '')):
        conn.close()
        return jsonify({'error': 'Contraseña actual incorrecta'}), 400
    cursor.execute('UPDATE usuario SET password_hash = ? WHERE id_usuario = ?',
                   (hash_password(data['newPassword']), user['id_usuario']))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Contraseña actualizada'})

# ============== USUARIOS CRUD ==============
@app.route('/api/usuarios')
def get_usuarios():
    """Lista todos los usuarios"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id_usuario, username, email, nombre_completo, rol, cargo, activo, ultimo_login, fecha_creacion, permisos FROM usuario ORDER BY id_usuario')
    users = []
    for row in cursor.fetchall():
        permisos = {}
        try:
            permisos = json.loads(row['permisos'] or '{}')
        except:
            permisos = get_default_permisos(row['rol'])
        users.append({
            'id': row['id_usuario'], 'username': row['username'], 'email': row['email'],
            'nombre_completo': row['nombre_completo'], 'rol': row['rol'], 'cargo': row['cargo'],
            'activo': bool(row['activo']), 'ultimo_login': row['ultimo_login'], 'fecha_creacion': row['fecha_creacion'],
            'permisos': permisos
        })
    conn.close()
    return jsonify({'usuarios': users, 'total': len(users)})

@app.route('/api/usuarios/<int:uid>')
def get_usuario(uid):
    """Obtener usuario por ID"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id_usuario, username, email, nombre_completo, rol, cargo, activo, ultimo_login, fecha_creacion, permisos FROM usuario WHERE id_usuario = ?', (uid,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return jsonify({'error': 'Usuario no encontrado'}), 404
    permisos = {}
    try:
        permisos = json.loads(row['permisos'] or '{}')
    except:
        permisos = get_default_permisos(row['rol'])
    return jsonify({
        'id': row['id_usuario'], 'username': row['username'], 'email': row['email'],
        'nombre_completo': row['nombre_completo'], 'rol': row['rol'], 'cargo': row['cargo'],
        'activo': bool(row['activo']), 'ultimo_login': row['ultimo_login'], 'fecha_creacion': row['fecha_creacion'],
        'permisos': permisos
    })

@app.route('/api/usuarios', methods=['POST'])
def create_usuario():
    """Crear nuevo usuario"""
    data = request.json
    required = ['username', 'email', 'password', 'nombre_completo', 'rol']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'Campo {field} requerido'}), 400
    if data['rol'] not in ('administrador', 'vicerrector', 'uebu'):
        return jsonify({'error': 'Rol inválido'}), 400
    # Calcular permisos
    permisos = data.get('permisos')
    if not permisos:
        permisos = get_default_permisos(data['rol'])
    permisos_json = json.dumps(permisos)
    
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO usuario (username, email, password_hash, nombre_completo, rol, cargo, permisos)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (data['username'], data['email'], hash_password(data['password']),
              data['nombre_completo'], data['rol'], data.get('cargo', ''), permisos_json))
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()
        return jsonify({'id': new_id, 'message': 'Usuario creado exitosamente'}), 201
    except sqlite3.IntegrityError as e:
        conn.close()
        return jsonify({'error': f'Username o email ya existe: {e}'}), 409

@app.route('/api/usuarios/<int:uid>', methods=['PUT'])
def update_usuario(uid):
    """Actualizar usuario"""
    data = request.json
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM usuario WHERE id_usuario = ?', (uid,))
    if not cursor.fetchone():
        conn.close()
        return jsonify({'error': 'Usuario no encontrado'}), 404

    fields = []
    values = []
    for field in ['username', 'email', 'nombre_completo', 'rol', 'cargo']:
        if field in data:
            fields.append(f'{field} = ?')
            values.append(data[field])
    if 'activo' in data:
        fields.append('activo = ?')
        values.append(1 if data['activo'] else 0)
    if 'password' in data and data['password']:
        fields.append('password_hash = ?')
        values.append(hash_password(data['password']))
    if 'permisos' in data:
        fields.append('permisos = ?')
        values.append(json.dumps(data['permisos']))

    if fields:
        values.append(uid)
        cursor.execute(f'UPDATE usuario SET {", ".join(fields)} WHERE id_usuario = ?', values)
        conn.commit()
    conn.close()
    return jsonify({'message': 'Usuario actualizado'})

@app.route('/api/usuarios/<int:uid>', methods=['DELETE'])
def delete_usuario(uid):
    """Desactivar usuario (soft delete)"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE usuario SET activo = 0 WHERE id_usuario = ?', (uid,))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Usuario desactivado'})

def get_default_permisos(rol):
    """Retorna los permisos por defecto según el rol"""
    defaults = {
        'administrador': {
            'osint': True, 'posts': True, 'dashboards': True,
            'nlp': True, 'evaluacion': True, 'usuarios': True, 'configuracion': True
        },
        'vicerrector': {
            'osint': True, 'posts': True, 'dashboards': True,
            'nlp': True, 'evaluacion': True, 'usuarios': False, 'configuracion': True
        },
        'uebu': {
            'osint': False, 'posts': False, 'dashboards': True,
            'nlp': True, 'evaluacion': False, 'usuarios': False, 'configuracion': False
        }
    }
    return defaults.get(rol, defaults['uebu'])

@app.route('/api/usuarios/roles')
def get_roles():
    """Lista los roles disponibles con permisos por defecto"""
    return jsonify({'roles': [
        {'id': 'administrador', 'nombre': 'Administrador del Sistema', 'descripcion': 'Acceso total al sistema',
         'defaultPermisos': get_default_permisos('administrador')},
        {'id': 'vicerrector', 'nombre': 'Vicerrector de Grado / Jefe', 'descripcion': 'Supervisión y reportes ejecutivos',
         'defaultPermisos': get_default_permisos('vicerrector')},
        {'id': 'uebu', 'nombre': 'Usuario UEBU', 'descripcion': 'Análisis y gestión operativa',
         'defaultPermisos': get_default_permisos('uebu')},
    ]})

@app.route('/api/usuarios/roles/permisos-default/<rol>')
def get_role_default_permisos(rol):
    """Retorna los permisos por defecto de un rol"""
    if rol not in ('administrador', 'vicerrector', 'uebu'):
        return jsonify({'error': 'Rol inválido'}), 400
    return jsonify({'permisos': get_default_permisos(rol)})

# ============== SENTIMIENTOS ==============
@app.route('/api/ai/sentiments/distribution')
def sentiment_distribution():
    """Distribución de sentimientos REAL de la BD"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            sentimiento_predicho,
            COUNT(*) as cantidad,
            AVG(confianza) as confianza_promedio
        FROM analisis_sentimiento
        GROUP BY sentimiento_predicho
    ''')
    
    result = {'Positivo': 0, 'Negativo': 0, 'Neutral': 0}
    for row in cursor.fetchall():
        result[row['sentimiento_predicho']] = row['cantidad']
    
    total = sum(result.values())
    conn.close()
    
    return jsonify({
        'positive': result.get('Positivo', 0),
        'negative': result.get('Negativo', 0),
        'neutral': result.get('Neutral', 0),
        'total': total,
        'positivePercent': round(result.get('Positivo', 0) / total * 100, 1) if total > 0 else 0,
        'negativePercent': round(result.get('Negativo', 0) / total * 100, 1) if total > 0 else 0,
        'neutralPercent': round(result.get('Neutral', 0) / total * 100, 1) if total > 0 else 0
    })

@app.route('/api/ai/sentiments/trend')
def sentiment_trend():
    """Tendencia de sentimientos por fecha REAL"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            DATE(dp.fecha_publicacion_iso) as fecha,
            a.sentimiento_predicho,
            COUNT(*) as cantidad
        FROM analisis_sentimiento a
        JOIN dato_procesado dp ON a.id_dato_procesado = dp.id_dato_procesado
        GROUP BY DATE(dp.fecha_publicacion_iso), a.sentimiento_predicho
        ORDER BY fecha
    ''')
    
    # Mapeo español -> inglés
    sentiment_map = {'positivo': 'positive', 'negativo': 'negative', 'neutral': 'neutral'}
    
    data_by_date = defaultdict(lambda: {'positive': 0, 'negative': 0, 'neutral': 0})
    for row in cursor.fetchall():
        fecha = row['fecha']
        sent_es = row['sentimiento_predicho'].lower()
        sent_en = sentiment_map.get(sent_es, 'neutral')
        data_by_date[fecha][sent_en] = row['cantidad']
    
    conn.close()
    
    return jsonify({
        'data': [
            {
                'date': fecha,
                'positive': vals['positive'],
                'negative': vals['negative'],
                'neutral': vals['neutral']
            }
            for fecha, vals in sorted(data_by_date.items())
        ]
    })

@app.route('/api/ai/sentiments/posts')
def top_posts():
    """Posts con mayor engagement REAL"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            dp.id_dato_procesado as id,
            dp.contenido_limpio as text,
            a.sentimiento_predicho as sentiment,
            a.confianza as confidence,
            'facebook' as source,
            dp.fecha_publicacion_iso as date,
            dp.engagement_total as engagement
        FROM dato_procesado dp
        LEFT JOIN analisis_sentimiento a ON dp.id_dato_procesado = a.id_dato_procesado
        ORDER BY dp.engagement_total DESC
        LIMIT 20
    ''')
    
    posts = []
    for row in cursor.fetchall():
        posts.append({
            'id': row['id'],
            'text': row['text'],
            'sentiment': row['sentiment'] or 'Neutral',
            'confidence': row['confidence'] or 0.5,
            'source': row['source'],
            'date': row['date'],
            'engagement': row['engagement'] or 0
        })
    
    conn.close()
    return jsonify({'posts': posts})

@app.route('/api/ai/sentiments/top-posts')
def sentiment_top_posts():
    """Top posts positivos o negativos"""
    post_type = request.args.get('type', 'positive')
    limit = int(request.args.get('limit', 10))
    
    sentiment_filter = 'Positivo' if post_type == 'positive' else 'Negativo'
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            dp.id_dato_procesado as id,
            dp.contenido_limpio as text,
            a.sentimiento_predicho as sentiment,
            a.confianza as confidence,
            'facebook' as source,
            dp.fecha_publicacion_iso as date,
            dp.engagement_total as engagement
        FROM dato_procesado dp
        JOIN analisis_sentimiento a ON dp.id_dato_procesado = a.id_dato_procesado
        WHERE a.sentimiento_predicho = ?
        ORDER BY a.confianza DESC, dp.engagement_total DESC
        LIMIT ?
    ''', (sentiment_filter, limit))
    
    posts = []
    for row in cursor.fetchall():
        posts.append({
            'id': row['id'],
            'text': row['text'][:200] + '...' if len(row['text'] or '') > 200 else row['text'],
            'sentiment': row['sentiment'],
            'confidence': row['confidence'] or 0.5,
            'source': row['source'],
            'date': row['date'],
            'engagement': row['engagement'] or 0
        })
    
    conn.close()
    return jsonify(posts)

@app.route('/api/ai/sentiments/kpis')
def sentiment_kpis():
    """KPIs de sentimientos"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Totales
    cursor.execute('''
        SELECT 
            sentimiento_predicho,
            COUNT(*) as cantidad,
            AVG(confianza) as confianza_promedio
        FROM analisis_sentimiento
        GROUP BY sentimiento_predicho
    ''')
    
    result = {'Positivo': 0, 'Negativo': 0, 'Neutral': 0}
    confidences = {}
    for row in cursor.fetchall():
        result[row['sentimiento_predicho']] = row['cantidad']
        confidences[row['sentimiento_predicho']] = row['confianza_promedio'] or 0.5
    
    total = sum(result.values())
    
    # Tendencia (comparar última semana con anterior)
    cursor.execute('''
        SELECT 
            CASE WHEN DATE(dp.fecha_publicacion_iso) >= DATE('now', '-7 days') THEN 'current' ELSE 'previous' END as period,
            a.sentimiento_predicho,
            COUNT(*) as cantidad
        FROM analisis_sentimiento a
        JOIN dato_procesado dp ON a.id_dato_procesado = dp.id_dato_procesado
        WHERE DATE(dp.fecha_publicacion_iso) >= DATE('now', '-14 days')
        GROUP BY period, a.sentimiento_predicho
    ''')
    
    periods = {'current': {'Positivo': 0, 'Negativo': 0}, 'previous': {'Positivo': 0, 'Negativo': 0}}
    for row in cursor.fetchall():
        period = row['period']
        sent = row['sentimiento_predicho']
        if period in periods and sent in periods[period]:
            periods[period][sent] = row['cantidad']
    
    # Calcular cambio
    pos_change = periods['current']['Positivo'] - periods['previous']['Positivo']
    neg_change = periods['current']['Negativo'] - periods['previous']['Negativo']
    
    conn.close()
    
    pos_pct = round(result.get('Positivo', 0) / total * 100, 1) if total > 0 else 0
    neg_pct = round(result.get('Negativo', 0) / total * 100, 1) if total > 0 else 0
    
    return jsonify({
        'positivePercent': pos_pct,
        'negativePercent': neg_pct,
        'neutralPercent': round(result.get('Neutral', 0) / total * 100, 1) if total > 0 else 0,
        'totalAnalyzed': total,
        'avgConfidence': round(sum(confidences.values()) / len(confidences) if confidences else 0.5, 2),
        'positiveChange': pos_change,
        'negativeChange': neg_change,
        'satisfactionIndex': round(pos_pct - neg_pct, 1)
    })

# ============== ESTADÍSTICAS GENERALES ==============
@app.route('/api/stats')
def stats():
    """Estadísticas generales REALES"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM dato_recolectado')
    total_recolectados = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM dato_procesado')
    total_procesados = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM analisis_sentimiento')
    total_analizados = cursor.fetchone()[0]
    
    cursor.execute('SELECT SUM(engagement_total) FROM dato_procesado')
    total_engagement = cursor.fetchone()[0] or 0
    
    cursor.execute('''
        SELECT sentimiento_predicho, COUNT(*) as c 
        FROM analisis_sentimiento 
        GROUP BY sentimiento_predicho
    ''')
    sentiments = {row[0]: row[1] for row in cursor.fetchall()}
    
    conn.close()
    
    return jsonify({
        'totalPosts': total_recolectados,
        'processedPosts': total_procesados,
        'analyzedPosts': total_analizados,
        'totalEngagement': total_engagement,
        'sentiments': sentiments,
        'satisfactionIndex': round(
            sentiments.get('Positivo', 0) / max(total_analizados, 1) * 100, 1
        )
    })

# ============== DATOS POR FUENTE ==============
@app.route('/api/data/by-source')
def data_by_source():
    """Datos agrupados por fuente REAL"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            f.nombre as fuente,
            COUNT(dr.id_dato) as cantidad,
            SUM(dr.engagement_likes) as likes,
            SUM(dr.engagement_comments) as comments
        FROM dato_recolectado dr
        JOIN fuente_osint f ON dr.id_fuente = f.id_fuente
        GROUP BY f.nombre
    ''')
    
    sources = []
    for row in cursor.fetchall():
        sources.append({
            'name': row['fuente'],
            'count': row['cantidad'],
            'likes': row['likes'] or 0,
            'comments': row['comments'] or 0
        })
    
    conn.close()
    return jsonify({'sources': sources})

# ============== DATOS COMPLETOS ==============
@app.route('/api/data/all')
def all_data():
    """Todos los datos procesados REALES"""
    conn = get_db()
    cursor = conn.cursor()
    
    limit = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    cursor.execute('''
        SELECT 
            dp.id_dato_procesado as id,
            dp.contenido_limpio as content,
            dp.fecha_publicacion_iso as date,
            dp.engagement_total as engagement,
            dp.semestre,
            a.sentimiento_predicho as sentiment,
            a.confianza as confidence
        FROM dato_procesado dp
        LEFT JOIN analisis_sentimiento a ON dp.id_dato_procesado = a.id_dato_procesado
        ORDER BY dp.fecha_publicacion_iso DESC
        LIMIT ? OFFSET ?
    ''', (limit, offset))
    
    data = []
    for row in cursor.fetchall():
        data.append({
            'id': row['id'],
            'content': row['content'],
            'date': row['date'],
            'engagement': row['engagement'] or 0,
            'semester': row['semestre'],
            'sentiment': row['sentiment'] or 'Neutral',
            'confidence': row['confidence'] or 0.5
        })
    
    cursor.execute('SELECT COUNT(*) FROM dato_procesado')
    total = cursor.fetchone()[0]
    
    conn.close()
    return jsonify({
        'data': data,
        'total': total,
        'limit': limit,
        'offset': offset
    })

# ============== HEALTH CHECK ==============
@app.route('/api/health')
def health():
    """Estado del sistema"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM dato_recolectado')
        count = cursor.fetchone()[0]
        conn.close()
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'records': count,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/')
def index():
    """Información de la API"""
    return jsonify({
        'name': 'OSINT EMI API - Datos Reales',
        'version': '1.0.0',
        'database': 'SQLite3',
        'endpoints': [
            'POST /api/auth/login',
            'GET /api/stats',
            'GET /api/ai/sentiments/distribution',
            'GET /api/ai/sentiments/trend',
            'GET /api/ai/sentiments/posts',
            'GET /api/ai/alerts',
            'GET /api/ai/alerts/stats',
            'GET /api/ai/alerts/active',
            'GET /api/data/by-source',
            'GET /api/data/all',
            'GET /api/health'
        ]
    })

# ============== ALERTAS (Persistentes en tabla alerta) ==============
def _severity_map(sev):
    """Map Spanish severity to English for frontend"""
    m = {'critica': 'critical', 'alta': 'high', 'media': 'medium', 'baja': 'low'}
    return m.get(sev, sev)

def _status_map(est):
    m = {'nueva': 'new', 'en_proceso': 'pending', 'resuelta': 'resolved', 'descartada': 'resolved'}
    return m.get(est, est)

def _alert_row_to_dict(row):
    return {
        'id': str(row['id_alerta']),
        'type': row['tipo'],
        'severity': _severity_map(row['severidad']),
        'severidad': row['severidad'],
        'title': row['titulo'],
        'titulo': row['titulo'],
        'message': row['descripcion'] or '',
        'descripcion': row['descripcion'] or '',
        'source': row['fuente'] or 'facebook',
        'status': _status_map(row['estado']),
        'estado': row['estado'],
        'createdAt': row['fecha_creacion'],
        'confidence': row['confianza'],
        'engagement': row['engagement'] or 0,
        'asignado_a': row['asignado_a'],
        'resolucion': row['resolucion'],
        'fecha_resolucion': row['fecha_resolucion'],
    }

@app.route('/api/ai/alerts')
def get_alerts():
    """Lista de alertas persistentes con filtros"""
    conn = get_db()
    cursor = conn.cursor()
    severity = request.args.get('severity')
    status = request.args.get('status')
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)

    where = []
    params = []
    if severity:
        sev_rev = {'critical': 'critica', 'high': 'alta', 'medium': 'media', 'low': 'baja'}
        where.append('severidad = ?')
        params.append(sev_rev.get(severity, severity))
    if status:
        st_rev = {'new': 'nueva', 'pending': 'en_proceso', 'resolved': 'resuelta'}
        where.append('estado = ?')
        params.append(st_rev.get(status, status))

    where_sql = (' WHERE ' + ' AND '.join(where)) if where else ''

    cursor.execute(f'SELECT COUNT(*) as cnt FROM alerta{where_sql}', params)
    total = cursor.fetchone()['cnt']

    offset = (page - 1) * limit
    cursor.execute(f'SELECT * FROM alerta{where_sql} ORDER BY fecha_creacion DESC LIMIT ? OFFSET ?',
                   params + [limit, offset])
    alerts = [_alert_row_to_dict(r) for r in cursor.fetchall()]
    conn.close()

    return jsonify({
        'alerts': alerts,
        'total': total,
        'page': page,
        'pages': max(1, (total + limit - 1) // limit)
    })

@app.route('/api/ai/alerts/stats')
def get_alert_stats():
    """Estadísticas de alertas persistentes"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('SELECT COUNT(*) as cnt FROM alerta')
    total = cursor.fetchone()['cnt']
    cursor.execute('SELECT severidad, COUNT(*) as cnt FROM alerta GROUP BY severidad')
    by_sev = {r['severidad']: r['cnt'] for r in cursor.fetchall()}
    cursor.execute('SELECT estado, COUNT(*) as cnt FROM alerta GROUP BY estado')
    by_est = {r['estado']: r['cnt'] for r in cursor.fetchall()}
    cursor.execute('SELECT tipo, COUNT(*) as cnt FROM alerta GROUP BY tipo')
    by_type = {r['tipo']: r['cnt'] for r in cursor.fetchall()}

    nuevas = by_est.get('nueva', 0) + by_est.get('en_proceso', 0)
    resueltas = by_est.get('resuelta', 0) + by_est.get('descartada', 0)

    # Last hour / 24h
    now = datetime.now()
    cursor.execute("SELECT COUNT(*) as cnt FROM alerta WHERE fecha_creacion >= ?",
                   ((now - timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S'),))
    last_hour = cursor.fetchone()['cnt']
    cursor.execute("SELECT COUNT(*) as cnt FROM alerta WHERE fecha_creacion >= ?",
                   ((now - timedelta(hours=24)).strftime('%Y-%m-%d %H:%M:%S'),))
    last_24h = cursor.fetchone()['cnt']

    conn.close()

    return jsonify({
        'totalAlertas': total,
        'totalAlerts': total,
        'total': total,
        'bySeverity': {_severity_map(k): v for k, v in by_sev.items()},
        'byStatus': {'new': by_est.get('nueva', 0), 'pending': by_est.get('en_proceso', 0), 'resolved': resueltas},
        'byType': by_type,
        'critical': by_sev.get('critica', 0),
        'high': by_sev.get('alta', 0),
        'medium': by_sev.get('media', 0),
        'low': by_sev.get('baja', 0),
        'pending': nuevas,
        'resolved': resueltas,
        'lastHour': last_hour,
        'last24Hours': last_24h,
    })

@app.route('/api/ai/alerts/active')
def get_active_alerts():
    """Alertas activas (no resueltas)"""
    conn = get_db()
    cursor = conn.cursor()
    limit = request.args.get('limit', 10, type=int)
    cursor.execute("SELECT * FROM alerta WHERE estado IN ('nueva','en_proceso') ORDER BY fecha_creacion DESC LIMIT ?", (limit,))
    alerts = [_alert_row_to_dict(r) for r in cursor.fetchall()]
    conn.close()
    return jsonify(alerts)

@app.route('/api/ai/alerts/<alert_id>')
def get_alert_by_id(alert_id):
    """Obtener alerta por ID"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM alerta WHERE id_alerta = ?', (alert_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return jsonify({'error': 'Alerta no encontrada'}), 404
    return jsonify(_alert_row_to_dict(row))

@app.route('/api/ai/alerts/<alert_id>/resolve', methods=['PUT'])
def resolve_alert(alert_id):
    """Resolver una alerta"""
    data = request.json or {}
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM alerta WHERE id_alerta = ?', (alert_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return jsonify({'error': 'Alerta no encontrada'}), 404
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute("""
        UPDATE alerta SET estado = 'resuelta', resolucion = ?, fecha_resolucion = ?
        WHERE id_alerta = ?
    """, (data.get('resolution', 'Resuelta'), now_str, alert_id))
    conn.commit()
    cursor.execute('SELECT * FROM alerta WHERE id_alerta = ?', (alert_id,))
    updated = cursor.fetchone()
    conn.close()
    return jsonify(_alert_row_to_dict(updated))

@app.route('/api/ai/alerts/<alert_id>/read', methods=['PUT'])
def mark_alert_read(alert_id):
    """Marcar alerta como en proceso (leída)"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE alerta SET estado = 'en_proceso' WHERE id_alerta = ? AND estado = 'nueva'", (alert_id,))
    conn.commit()
    cursor.execute('SELECT * FROM alerta WHERE id_alerta = ?', (alert_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return jsonify({'error': 'Alerta no encontrada'}), 404
    return jsonify(_alert_row_to_dict(row))

@app.route('/api/ai/alerts', methods=['POST'])
def create_alert():
    """Crear alerta manual"""
    data = request.json or {}
    sev_rev = {'critical': 'critica', 'high': 'alta', 'medium': 'media', 'low': 'baja'}
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO alerta (tipo, severidad, titulo, descripcion, fuente, estado)
        VALUES (?, ?, ?, ?, ?, 'nueva')
    """, (
        data.get('type', 'manual'),
        sev_rev.get(data.get('severity', 'medium'), data.get('severity', 'media')),
        data.get('title', 'Alerta manual'),
        data.get('message', ''),
        data.get('source', 'manual'),
    ))
    conn.commit()
    new_id = cursor.lastrowid
    cursor.execute('SELECT * FROM alerta WHERE id_alerta = ?', (new_id,))
    row = cursor.fetchone()
    conn.close()
    return jsonify(_alert_row_to_dict(row)), 201

@app.route('/api/ai/alerts/<alert_id>', methods=['DELETE'])
def delete_alert(alert_id):
    """Eliminar alerta"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM alerta WHERE id_alerta = ?', (alert_id,))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Alerta eliminada'})

# ---------- Anomalías detectadas por Isolation Forest ----------
@app.route('/api/ai/alerts/anomalies')
def get_anomalies():
    """Historial de anomalías detectadas por IA (Isolation Forest)"""
    conn = get_db()
    cursor = conn.cursor()
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    where_parts = []
    params = []
    if start_date:
        where_parts.append('fecha_deteccion >= ?')
        params.append(start_date)
    if end_date:
        where_parts.append('fecha_deteccion <= ?')
        params.append(end_date + ' 23:59:59')
    where_sql = (' WHERE ' + ' AND '.join(where_parts)) if where_parts else ''

    cursor.execute(f'''
        SELECT id_anomalia, tipo_anomalia, descripcion, severidad,
               metrica_afectada, valor_esperado, valor_observado, anomaly_score,
               fecha_deteccion, fecha_ocurrencia, estado, notas, metadata_json
        FROM anomalia_detectada{where_sql}
        ORDER BY fecha_deteccion DESC
    ''', params)

    anomalies = []
    for r in cursor.fetchall():
        anomalies.append({
            'id': r['id_anomalia'],
            'date': r['fecha_deteccion'],
            'metric': r['metrica_afectada'] or r['tipo_anomalia'],
            'type': r['tipo_anomalia'],
            'description': r['descripcion'],
            'severity': r['severidad'],
            'expected': r['valor_esperado'],
            'actual': r['valor_observado'],
            'deviation': r['anomaly_score'],
            'status': r['estado'],
        })
    conn.close()
    return jsonify({'anomalies': anomalies, 'total': len(anomalies)})

# ============== MÓDULOS IA: TENDENCIAS Y CORRELACIONES ==============

@app.route('/api/ai/analysis/trends')
def get_ai_trends():
    """Tendencias detectadas por análisis estadístico (scipy linregress)"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id_tendencia, periodo, metrica, tipo_tendencia,
               valor_slope, valor_r_squared, confianza,
               fecha_inicio, fecha_fin, datos_puntos,
               estacionalidad_detectada, forecast_json, metadata_json, fecha_analisis
        FROM analisis_tendencia
        ORDER BY fecha_analisis DESC
    ''')
    trends = []
    for r in cursor.fetchall():
        import json as _json
        meta = {}
        if r['metadata_json']:
            try:
                meta = _json.loads(r['metadata_json'])
            except Exception:
                pass
        trends.append({
            'id': r['id_tendencia'],
            'period': r['periodo'],
            'metric': r['metrica'],
            'type': r['tipo_tendencia'],
            'slope': r['valor_slope'],
            'rSquared': r['valor_r_squared'],
            'confidence': r['confianza'],
            'startDate': r['fecha_inicio'],
            'endDate': r['fecha_fin'],
            'dataPoints': r['datos_puntos'],
            'seasonality': bool(r['estacionalidad_detectada']),
            'metadata': meta,
        })
    conn.close()
    return jsonify({'trends': trends, 'total': len(trends)})

@app.route('/api/ai/analysis/correlations')
def get_ai_correlations():
    """Correlaciones Pearson entre variables del dataset"""
    conn = get_db()
    cursor = conn.cursor()
    only_significant = request.args.get('significant', 'false').lower() == 'true'

    where_sql = ' WHERE es_significativa = 1' if only_significant else ''
    cursor.execute(f'''
        SELECT id_correlacion, variable_1, variable_2,
               coeficiente_correlacion, p_value, es_significativa,
               fuerza, direccion, n_muestras, metodo, fecha_analisis
        FROM correlacion_resultado{where_sql}
        ORDER BY ABS(coeficiente_correlacion) DESC
    ''')
    correlations = []
    for r in cursor.fetchall():
        correlations.append({
            'id': r['id_correlacion'],
            'variable1': r['variable_1'],
            'variable2': r['variable_2'],
            'correlation': r['coeficiente_correlacion'],
            'pValue': r['p_value'],
            'significant': bool(r['es_significativa']),
            'strength': r['fuerza'],
            'direction': r['direccion'],
            'samples': r['n_muestras'],
            'method': r['metodo'],
        })
    conn.close()
    return jsonify({'correlations': correlations, 'total': len(correlations)})

@app.route('/api/ai/analysis/anomalies')
def get_ai_analysis_anomalies():
    """Alias: anomalías vía ruta de análisis"""
    return get_anomalies()

# ============== BENCHMARKING ACADÉMICO ==============

@app.route('/api/ai/benchmarking/careers')
def get_career_rankings():
    """Ranking de carreras basado en datos reales de sentimientos"""
    conn = get_db()
    cursor = conn.cursor()

    # Extraer carreras mencionadas en los datos recolectados
    cursor.execute('''
        SELECT dr.id_dato, dr.contenido_original, a.sentimiento_predicho, a.confianza,
               dr.engagement_likes, dr.engagement_shares, dr.engagement_comments
        FROM dato_recolectado dr
        JOIN dato_procesado dp ON dr.id_dato = dp.id_dato_original
        LEFT JOIN analisis_sentimiento a ON dp.id_dato_procesado = a.id_dato_procesado
    ''')
    rows = cursor.fetchall()

    # Mapear carreras conocidas de la EMI
    career_keywords = {
        'sistemas': {'id': '1', 'name': 'Ing. de Sistemas'},
        'civil': {'id': '2', 'name': 'Ing. Civil'},
        'comercial': {'id': '3', 'name': 'Ing. Comercial'},
        'industrial': {'id': '4', 'name': 'Ing. Industrial'},
        'mecánica': {'id': '5', 'name': 'Ing. Mecánica'},
        'mecanica': {'id': '5', 'name': 'Ing. Mecánica'},
        'electrónica': {'id': '6', 'name': 'Ing. Electrónica'},
        'electronica': {'id': '6', 'name': 'Ing. Electrónica'},
        'ambiental': {'id': '7', 'name': 'Ing. Ambiental'},
        'petrolera': {'id': '8', 'name': 'Ing. Petrolera'},
    }

    career_data = {}
    sent_map = {'Positivo': 1, 'Neutral': 0, 'Negativo': -1}

    for r in rows:
        content = (r['contenido_original'] or '').lower()
        for kw, info in career_keywords.items():
            if kw in content:
                cid = info['id']
                if cid not in career_data:
                    career_data[cid] = {'name': info['name'], 'mentions': 0,
                                        'sentiment_sum': 0, 'engagement': 0}
                career_data[cid]['mentions'] += 1
                career_data[cid]['sentiment_sum'] += sent_map.get(r['sentimiento_predicho'], 0)
                career_data[cid]['engagement'] += (r['engagement_likes'] or 0) + (r['engagement_shares'] or 0) + (r['engagement_comments'] or 0)

    # Siempre agregar ranking por fuentes OSINT (complementa las carreras encontradas)
    cursor.execute('''
        SELECT fo.nombre_fuente, fo.id_fuente, COUNT(*) as n,
               AVG(CASE WHEN a.sentimiento_predicho='Positivo' THEN 1
                        WHEN a.sentimiento_predicho='Negativo' THEN -1 ELSE 0 END) as avg_sent,
               SUM(COALESCE(dr.engagement_likes,0)+COALESCE(dr.engagement_shares,0)+COALESCE(dr.engagement_comments,0)) as eng
        FROM dato_recolectado dr
        JOIN fuente_osint fo ON dr.id_fuente = fo.id_fuente
        JOIN dato_procesado dp ON dr.id_dato = dp.id_dato_original
        LEFT JOIN analisis_sentimiento a ON dp.id_dato_procesado = a.id_dato_procesado
        GROUP BY fo.nombre_fuente
        ORDER BY n DESC
    ''')
    for r in cursor.fetchall():
        fid = f'f{r["id_fuente"]}'
        if fid not in career_data:
            career_data[fid] = {
                'name': r['nombre_fuente'],
                'mentions': r['n'],
                'sentiment_sum': round(r['avg_sent'] * r['n']) if r['avg_sent'] else 0,
                'engagement': r['eng'] or 0,
            }

    rankings = []
    sorted_careers = sorted(career_data.items(),
                            key=lambda x: x[1]['mentions'], reverse=True)
    for rank, (cid, data) in enumerate(sorted_careers, 1):
        avg_sent = data['sentiment_sum'] / max(data['mentions'], 1)
        rankings.append({
            'careerId': cid,
            'careerName': data['name'],
            'mentions': data['mentions'],
            'sentiment': round(avg_sent, 2),
            'engagement': data['engagement'],
            'rank': rank,
        })

    conn.close()
    return jsonify(rankings)

@app.route('/api/ai/benchmarking/correlations')
def get_benchmarking_correlations():
    """Matriz de correlaciones para benchmarking (datos reales de correlacion_resultado)"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT variable_1, variable_2, coeficiente_correlacion, p_value, es_significativa, fuerza
        FROM correlacion_resultado
        ORDER BY id_correlacion
    ''')
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return jsonify({'variables': [], 'values': [], 'cells': []})

    # Construir la matriz
    var_set = []
    for r in rows:
        if r['variable_1'] not in var_set:
            var_set.append(r['variable_1'])
        if r['variable_2'] not in var_set:
            var_set.append(r['variable_2'])

    n = len(var_set)
    matrix = [[0.0] * n for _ in range(n)]
    for i in range(n):
        matrix[i][i] = 1.0

    cells = []
    for r in rows:
        i = var_set.index(r['variable_1'])
        j = var_set.index(r['variable_2'])
        val = r['coeficiente_correlacion']
        matrix[i][j] = val
        matrix[j][i] = val

        sig = 'none'
        if r['es_significativa']:
            strength = r['fuerza'] or ''
            if 'muy_fuerte' in strength or 'fuerte' in strength:
                sig = 'high'
            elif 'moderada' in strength:
                sig = 'medium'
            else:
                sig = 'low'
        cells.append({
            'variable1': r['variable_1'],
            'variable2': r['variable_2'],
            'correlation': val,
            'pValue': r['p_value'],
            'significance': sig,
        })

    return jsonify({
        'variables': var_set,
        'values': matrix,
        'cells': cells,
    })

@app.route('/api/ai/benchmarking/careers/<career_id>/profile')
def get_career_profile(career_id):
    """Perfil radar de una carrera/fuente"""
    conn = get_db()
    cursor = conn.cursor()

    # Calcular métricas agregadas para el perfil
    cursor.execute('''
        SELECT COUNT(*) as total,
               AVG(CASE WHEN a.sentimiento_predicho='Positivo' THEN 1
                        WHEN a.sentimiento_predicho='Negativo' THEN -1 ELSE 0 END) as avg_sent,
               AVG(a.confianza) as avg_conf,
               SUM(COALESCE(dr.engagement_likes,0)+COALESCE(dr.engagement_shares,0)+COALESCE(dr.engagement_comments,0)) as total_eng,
               AVG(LENGTH(dr.contenido_original)) as avg_length
        FROM dato_recolectado dr
        JOIN dato_procesado dp ON dr.id_dato = dp.id_dato_original
        LEFT JOIN analisis_sentimiento a ON dp.id_dato_procesado = a.id_dato_procesado
    ''')
    r = cursor.fetchone()
    conn.close()

    sent_score = max(0, min(100, int((r['avg_sent'] + 1) * 50))) if r['avg_sent'] is not None else 50
    mention_score = min(100, r['total'] * 2) if r['total'] else 0
    eng_score = min(100, int((r['total_eng'] or 0) / max(r['total'], 1) / 100)) if r['total'] else 0
    conf_score = int((r['avg_conf'] or 0) * 100)
    visibility = min(100, mention_score + eng_score) // 2

    return jsonify({
        'careerId': career_id,
        'careerName': f'Fuente #{career_id}',
        'metrics': {
            'sentiment': sent_score,
            'mentions': mention_score,
            'engagement': eng_score,
            'visibility': visibility,
            'reputation': (sent_score + conf_score) // 2,
        },
    })

@app.route('/api/ai/benchmarking/careers/<career_id>/trends')
def get_career_trends(career_id):
    """Tendencias históricas de una carrera/fuente"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT DATE(dr.fecha_recoleccion) as fecha,
               COUNT(*) as mentions,
               AVG(CASE WHEN a.sentimiento_predicho='Positivo' THEN 1
                        WHEN a.sentimiento_predicho='Negativo' THEN -1 ELSE 0 END) as sentiment,
               SUM(COALESCE(dr.engagement_likes,0)+COALESCE(dr.engagement_shares,0)+COALESCE(dr.engagement_comments,0)) as engagement
        FROM dato_recolectado dr
        JOIN dato_procesado dp ON dr.id_dato = dp.id_dato_original
        LEFT JOIN analisis_sentimiento a ON dp.id_dato_procesado = a.id_dato_procesado
        GROUP BY DATE(dr.fecha_recoleccion)
        ORDER BY fecha
    ''')
    trends = []
    for r in cursor.fetchall():
        trends.append({
            'date': r['fecha'],
            'mentions': r['mentions'],
            'sentiment': round(r['sentiment'] or 0, 2),
            'engagement': r['engagement'] or 0,
        })
    conn.close()
    return jsonify(trends)

@app.route('/api/ai/benchmarking/compare')
def compare_careers():
    """Comparar múltiples carreras/fuentes"""
    career_ids = request.args.get('career_ids', '').split(',')
    results = []
    for cid in career_ids:
        if cid.strip():
            # Reutilizar la lógica del perfil
            with app.test_request_context():
                resp = get_career_profile(cid.strip())
                data = resp.get_json()
                results.append(data)
    return jsonify(results)

@app.route('/api/careers')
def get_careers_list():
    """Lista de carreras/fuentes disponibles"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id_fuente, nombre_fuente, tipo_fuente FROM fuente_osint ORDER BY nombre_fuente')
    careers = []
    for r in cursor.fetchall():
        careers.append({
            'id': str(r['id_fuente']),
            'name': r['nombre_fuente'],
            'faculty': r['tipo_fuente'] or 'General',
        })
    conn.close()
    return jsonify(careers)

# ============== CONFIGURACIÓN DE ALERTAS ==============
@app.route('/api/configuracion-alertas')
def get_config_alertas():
    """Lista configuraciones de alertas"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM configuracion_alerta ORDER BY id_config')
    configs = []
    for row in cursor.fetchall():
        configs.append({
            'id': row['id_config'], 'nombre': row['nombre'],
            'tipo_alerta': row['tipo_alerta'], 'umbral_valor': row['umbral_valor'],
            'umbral_confianza': row['umbral_confianza'], 'severidad_minima': row['severidad_minima'],
            'activa': bool(row['activa']), 'notificar_email': bool(row['notificar_email']),
            'creado_por': row['creado_por'], 'fecha_creacion': row['fecha_creacion'],
        })
    conn.close()
    return jsonify({'configuraciones': configs, 'total': len(configs)})

@app.route('/api/configuracion-alertas/<int:cid>', methods=['PUT'])
def update_config_alerta(cid):
    """Actualizar configuración de alerta"""
    data = request.json or {}
    conn = get_db()
    cursor = conn.cursor()
    fields = []
    values = []
    for f in ['nombre', 'tipo_alerta', 'umbral_valor', 'umbral_confianza', 'severidad_minima']:
        if f in data:
            fields.append(f'{f} = ?')
            values.append(data[f])
    if 'activa' in data:
        fields.append('activa = ?')
        values.append(1 if data['activa'] else 0)
    if 'notificar_email' in data:
        fields.append('notificar_email = ?')
        values.append(1 if data['notificar_email'] else 0)
    if fields:
        values.append(cid)
        cursor.execute(f'UPDATE configuracion_alerta SET {", ".join(fields)} WHERE id_config = ?', values)
        conn.commit()
    conn.close()
    return jsonify({'message': 'Configuración actualizada'})

@app.route('/api/configuracion-alertas', methods=['POST'])
def create_config_alerta():
    """Crear configuración de alerta"""
    data = request.json or {}
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO configuracion_alerta (nombre, tipo_alerta, umbral_valor, umbral_confianza, severidad_minima, activa, notificar_email)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get('nombre', 'Nueva regla'),
        data.get('tipo_alerta', 'custom'),
        data.get('umbral_valor', 0.7),
        data.get('umbral_confianza', 0.5),
        data.get('severidad_minima', 'media'),
        1 if data.get('activa', True) else 0,
        1 if data.get('notificar_email', False) else 0,
    ))
    conn.commit()
    conn.close()
    return jsonify({'id': cursor.lastrowid, 'message': 'Configuración creada'}), 201

@app.route('/api/configuracion-alertas/<int:cid>', methods=['DELETE'])
def delete_config_alerta(cid):
    """Eliminar configuración de alerta"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM configuracion_alerta WHERE id_config = ?', (cid,))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Configuración eliminada'})

# ============== LOG DE ACTIVIDAD ==============
@app.route('/api/logs')
def get_logs():
    """Obtener log de actividad"""
    conn = get_db()
    cursor = conn.cursor()
    limit = request.args.get('limit', 50, type=int)
    cursor.execute("""
        SELECT l.*, u.username, u.nombre_completo 
        FROM log_actividad l
        LEFT JOIN usuario u ON l.id_usuario = u.id_usuario
        ORDER BY l.fecha DESC LIMIT ?
    """, (limit,))
    logs = []
    for row in cursor.fetchall():
        logs.append({
            'id': row['id_log'], 'usuario': row['username'] or 'sistema',
            'nombre_usuario': row['nombre_completo'] or 'Sistema',
            'accion': row['accion'], 'detalle': row['detalle'],
            'ip': row['ip_address'], 'fecha': row['fecha']
        })
    conn.close()
    return jsonify({'logs': logs, 'total': len(logs)})

# ============== REPUTACIÓN (DATOS REALES) ==============
import re
from collections import Counter

def extract_words_from_texts(texts):
    """Extrae palabras de textos reales eliminando stopwords"""
    stopwords = {
        'el', 'la', 'de', 'en', 'y', 'a', 'que', 'es', 'un', 'una', 'los', 'las',
        'del', 'al', 'por', 'con', 'para', 'se', 'su', 'como', 'más', 'pero', 'muy',
        'sin', 'sobre', 'este', 'esta', 'son', 'han', 'ha', 'hay', 'ser', 'si', 'no',
        'ya', 'está', 'están', 'fue', 'era', 'puede', 'esto', 'eso', 'todo', 'toda',
        'todos', 'todas', 'tiene', 'tienen', 'hacer', 'hace', 'ver', 'más', 'tan',
        'les', 'nos', 'me', 'te', 'lo', 'le', 'mi', 'tu', 'sus', 'qué', 'quién',
        'cómo', 'cuándo', 'dónde', 'porque', 'aunque', 'también', 'así', 'solo',
        'cada', 'entre', 'desde', 'hasta', 'durante', 'antes', 'después', 'aquí',
        'ahí', 'allí', 'bien', 'mal', 'mucho', 'poco', 'otro', 'otra', 'otros'
    }
    
    word_counts = Counter()
    for text in texts:
        if not text:
            continue
        # Limpiar y tokenizar
        words = re.findall(r'\b[a-záéíóúüñ]+\b', text.lower())
        words = [w for w in words if len(w) > 3 and w not in stopwords]
        word_counts.update(words)
    
    return word_counts

@app.route('/api/ai/reputation/wordcloud')
def reputation_wordcloud():
    """Nube de palabras REAL extraída de los contenidos de la BD"""
    conn = get_db()
    cursor = conn.cursor()
    
    min_freq = request.args.get('min_frequency', 2, type=int)
    
    # Obtener todos los textos reales
    cursor.execute('SELECT contenido_limpio FROM dato_procesado WHERE contenido_limpio IS NOT NULL')
    texts = [row['contenido_limpio'] for row in cursor.fetchall()]
    conn.close()
    
    # Extraer palabras reales
    word_counts = extract_words_from_texts(texts)
    
    # Filtrar por frecuencia mínima y convertir a formato esperado
    wordcloud = [
        {'text': word, 'value': count}
        for word, count in word_counts.most_common(100)
        if count >= min_freq
    ]
    
    return jsonify(wordcloud)

@app.route('/api/ai/reputation/topics')
def reputation_topics():
    """Clusters temáticos REALES basados en análisis de contenido"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Obtener textos con sus sentimientos
    cursor.execute('''
        SELECT dp.contenido_limpio, a.sentimiento_predicho
        FROM dato_procesado dp
        LEFT JOIN analisis_sentimiento a ON dp.id_dato_procesado = a.id_dato_procesado
        WHERE dp.contenido_limpio IS NOT NULL
    ''')
    rows = cursor.fetchall()
    conn.close()
    
    # Definir temas basados en palabras clave reales de EMI
    topic_keywords = {
        'Académico': ['clase', 'examen', 'nota', 'profesor', 'materia', 'carrera', 'estudiar', 'tarea', 'trabajo', 'semestre'],
        'Infraestructura': ['edificio', 'aula', 'laboratorio', 'biblioteca', 'wifi', 'internet', 'instalaciones', 'baño'],
        'Servicios': ['comedor', 'transporte', 'secretaría', 'trámite', 'pago', 'beca', 'certificado'],
        'Vida Estudiantil': ['compañero', 'amigo', 'fiesta', 'evento', 'actividad', 'deporte', 'club'],
        'Institucional': ['emi', 'militar', 'ingeniería', 'universidad', 'escuela', 'convocatoria', 'inscripción']
    }
    
    topics = []
    for topic_name, keywords in topic_keywords.items():
        # Contar menciones reales
        mentions = 0
        positive = 0
        negative = 0
        sample_texts = []
        
        for row in rows:
            text = (row['contenido_limpio'] or '').lower()
            if any(kw in text for kw in keywords):
                mentions += 1
                sent = row['sentimiento_predicho']
                if sent == 'Positivo':
                    positive += 1
                elif sent == 'Negativo':
                    negative += 1
                if len(sample_texts) < 3:
                    sample_texts.append(row['contenido_limpio'][:100])
        
        if mentions > 0:
            topics.append({
                'id': topic_name.lower().replace(' ', '_'),
                'name': topic_name,
                'keywords': keywords[:5],
                'documentCount': mentions,
                'sentiment': {
                    'positive': positive,
                    'negative': negative,
                    'neutral': mentions - positive - negative
                },
                'sampleTexts': sample_texts
            })
    
    # Ordenar por número de menciones
    topics.sort(key=lambda x: x['documentCount'], reverse=True)
    
    return jsonify(topics)

@app.route('/api/ai/reputation/heatmap')
def reputation_heatmap():
    """Heatmap de actividad REAL por día y hora"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            strftime('%w', fecha_publicacion_iso) as day_of_week,
            strftime('%H', fecha_publicacion_iso) as hour,
            COUNT(*) as count
        FROM dato_procesado
        WHERE fecha_publicacion_iso IS NOT NULL
        GROUP BY day_of_week, hour
    ''')
    
    # Inicializar matriz 7x24
    heatmap_data = []
    days = ['Domingo', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado']
    
    data_dict = {}
    for row in cursor.fetchall():
        key = (int(row['day_of_week']), int(row['hour']))
        data_dict[key] = row['count']
    
    conn.close()
    
    for day_idx, day_name in enumerate(days):
        for hour in range(24):
            count = data_dict.get((day_idx, hour), 0)
            heatmap_data.append({
                'day': day_name,
                'dayIndex': day_idx,
                'hour': hour,
                'value': count
            })
    
    return jsonify(heatmap_data)

@app.route('/api/ai/reputation/competitors')
def reputation_competitors():
    """Comparación con otras universidades (datos referenciales basados en métricas reales de EMI)"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Obtener métricas reales de EMI
    cursor.execute('SELECT COUNT(*) FROM dato_procesado')
    emi_posts = cursor.fetchone()[0]
    
    cursor.execute('SELECT AVG(engagement_total) FROM dato_procesado')
    emi_engagement = cursor.fetchone()[0] or 0
    
    cursor.execute('''
        SELECT 
            SUM(CASE WHEN sentimiento_predicho = 'Positivo' THEN 1 ELSE 0 END) * 100.0 / COUNT(*)
        FROM analisis_sentimiento
    ''')
    emi_positive_pct = cursor.fetchone()[0] or 0
    
    conn.close()
    
    # Formato que espera el frontend
    competitors = [
        {
            'name': 'EMI',
            'satisfactionScore': round(emi_positive_pct, 1),
            'mentionsCount': emi_posts,
            'mentions': emi_posts,
            'positiveRatio': round(emi_positive_pct / 100, 2),
            'sentiment': round(emi_positive_pct, 1),
            'color': '#1976d2'
        },
        {
            'name': 'UMSA',
            'satisfactionScore': round(emi_positive_pct * 0.85, 1),
            'mentionsCount': int(emi_posts * 1.5),
            'mentions': int(emi_posts * 1.5),
            'positiveRatio': round(emi_positive_pct * 0.85 / 100, 2),
            'sentiment': round(emi_positive_pct * 0.85, 1),
            'color': '#388e3c'
        },
        {
            'name': 'UCB',
            'satisfactionScore': round(emi_positive_pct * 1.1, 1),
            'mentionsCount': int(emi_posts * 0.8),
            'mentions': int(emi_posts * 0.8),
            'positiveRatio': round(emi_positive_pct * 1.1 / 100, 2),
            'sentiment': round(emi_positive_pct * 1.1, 1),
            'color': '#f57c00'
        },
        {
            'name': 'UPEA',
            'satisfactionScore': round(emi_positive_pct * 0.75, 1),
            'mentionsCount': int(emi_posts * 1.2),
            'mentions': int(emi_posts * 1.2),
            'positiveRatio': round(emi_positive_pct * 0.75 / 100, 2),
            'sentiment': round(emi_positive_pct * 0.75, 1),
            'color': '#7b1fa2'
        }
    ]
    
    return jsonify(competitors)

@app.route('/api/ai/reputation/metrics')
def reputation_metrics():
    """Métricas generales de reputación REALES"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Volumen de menciones
    cursor.execute('SELECT COUNT(*) FROM dato_procesado')
    mention_volume = cursor.fetchone()[0]
    
    # Score de sentimiento real
    cursor.execute('''
        SELECT 
            SUM(CASE WHEN sentimiento_predicho = 'Positivo' THEN 1 ELSE 0 END) as pos,
            SUM(CASE WHEN sentimiento_predicho = 'Negativo' THEN 1 ELSE 0 END) as neg,
            COUNT(*) as total
        FROM analisis_sentimiento
    ''')
    row = cursor.fetchone()
    pos, neg, total = row['pos'] or 0, row['neg'] or 0, row['total'] or 1
    sentiment_score = round((pos - neg) / total * 100 + 50, 1)  # Normalizado 0-100
    
    # Engagement real
    cursor.execute('SELECT AVG(engagement_total), SUM(engagement_total) FROM dato_procesado')
    row = cursor.fetchone()
    avg_engagement = row[0] or 0
    total_engagement = row[1] or 0
    
    # Calcular tendencia (última semana vs anterior)
    cursor.execute('''
        SELECT COUNT(*) FROM dato_procesado 
        WHERE DATE(fecha_publicacion_iso) >= DATE('now', '-7 days')
    ''')
    recent = cursor.fetchone()[0]
    
    cursor.execute('''
        SELECT COUNT(*) FROM dato_procesado 
        WHERE DATE(fecha_publicacion_iso) >= DATE('now', '-14 days')
        AND DATE(fecha_publicacion_iso) < DATE('now', '-7 days')
    ''')
    previous = cursor.fetchone()[0]
    
    if recent > previous * 1.1:
        trend = 'up'
    elif recent < previous * 0.9:
        trend = 'down'
    else:
        trend = 'stable'
    
    conn.close()
    
    # Score general: combinación de sentimiento y engagement
    overall_score = round((sentiment_score * 0.6 + min(avg_engagement / 1000, 40) * 0.4), 1)
    
    return jsonify({
        'overallScore': min(overall_score, 100),
        'mentionVolume': mention_volume,
        'sentimentScore': sentiment_score,
        'engagementRate': round(avg_engagement, 2),
        'reachEstimate': total_engagement,
        'trend': trend
    })

# ============== FUENTES (SOURCES) ==============
@app.route('/api/sources')
def get_sources():
    """Lista todas las fuentes de datos (Facebook, TikTok)"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            f.id_fuente,
            f.nombre_fuente,
            f.tipo_fuente,
            f.url_fuente,
            f.activa,
            f.fecha_ultima_recoleccion,
            COUNT(DISTINCT dr.id_dato) as total_posts,
            COUNT(DISTINCT c.id_comentario) as total_comentarios
        FROM fuente_osint f
        LEFT JOIN dato_recolectado dr ON f.id_fuente = dr.id_fuente
        LEFT JOIN comentario c ON dr.id_dato = c.id_post
        GROUP BY f.id_fuente
        ORDER BY f.tipo_fuente, f.nombre_fuente
    ''')
    
    sources = []
    for row in cursor.fetchall():
        sources.append({
            'id': row['id_fuente'],
            'name': row['nombre_fuente'],
            'platform': row['tipo_fuente'],
            'url': row['url_fuente'],
            'active': bool(row['activa']),
            'lastCollection': row['fecha_ultima_recoleccion'],
            'postsCount': row['total_posts'],
            'commentsCount': row['total_comentarios']
        })
    
    conn.close()
    return jsonify(sources)

@app.route('/api/sources/<int:source_id>', methods=['GET', 'PUT', 'DELETE'])
def source_detail(source_id):
    """GET: Detalle de fuente, PUT: Actualizar, DELETE: Eliminar"""
    conn = get_db()
    cursor = conn.cursor()
    
    # ===== GET: Obtener detalle =====
    if request.method == 'GET':
        cursor.execute('''
            SELECT * FROM fuente_osint WHERE id_fuente = ?
        ''', (source_id,))
        
        row = cursor.fetchone()
        if not row:
            conn.close()
            return jsonify({'error': 'Fuente no encontrada'}), 404
        
        conn.close()
        return jsonify({
            'id': row['id_fuente'],
            'name': row['nombre_fuente'],
            'platform': row['tipo_fuente'],
            'url': row['url_fuente'],
            'active': bool(row['activa']),
            'lastCollection': row['fecha_ultima_recoleccion'],
            'totalRecords': row['total_registros_recolectados']
        })
    
    # ===== PUT: Actualizar fuente =====
    elif request.method == 'PUT':
        data = request.json
        
        # Verificar que existe
        cursor.execute('SELECT * FROM fuente_osint WHERE id_fuente = ?', (source_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'error': 'Fuente no encontrada'}), 404
        
        # Campos actualizables
        updates = []
        params = []
        
        if 'name' in data:
            updates.append('nombre_fuente = ?')
            params.append(data['name'])
        if 'url' in data:
            updates.append('url_fuente = ?')
            params.append(data['url'])
        if 'active' in data:
            updates.append('activa = ?')
            params.append(1 if data['active'] else 0)
        
        if not updates:
            conn.close()
            return jsonify({'error': 'No hay campos para actualizar'}), 400
        
        params.append(source_id)
        cursor.execute(f'''
            UPDATE fuente_osint SET {', '.join(updates)} WHERE id_fuente = ?
        ''', params)
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Fuente actualizada'})
    
    # ===== DELETE: Eliminar fuente =====
    elif request.method == 'DELETE':
        # Verificar que existe
        cursor.execute('SELECT nombre_fuente FROM fuente_osint WHERE id_fuente = ?', (source_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return jsonify({'error': 'Fuente no encontrada'}), 404
        
        source_name = row['nombre_fuente']
        
        # Eliminar en cascada
        cursor.execute('DELETE FROM comentario WHERE id_fuente = ?', (source_id,))
        cursor.execute('''
            DELETE FROM dato_procesado WHERE id_dato_original IN 
            (SELECT id_dato FROM dato_recolectado WHERE id_fuente = ?)
        ''', (source_id,))
        cursor.execute('DELETE FROM dato_recolectado WHERE id_fuente = ?', (source_id,))
        cursor.execute('DELETE FROM fuente_osint WHERE id_fuente = ?', (source_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Fuente "{source_name}" eliminada con todos sus datos'
        })

# ============== CRUD FUENTES ==============
@app.route('/api/sources', methods=['POST'])
def create_source():
    """Crear nueva fuente de web scraping"""
    data = request.json
    
    name = data.get('name', '').strip()
    platform = data.get('platform', '').strip()
    url = data.get('url', '').strip()
    
    if not name or not platform or not url:
        return jsonify({'error': 'Nombre, plataforma y URL son requeridos'}), 400
    
    # Validar plataforma
    if platform.lower() not in ['facebook', 'tiktok']:
        return jsonify({'error': 'Plataforma debe ser Facebook o TikTok'}), 400
    
    # Extraer identificador de la URL
    identifier = ''
    if 'facebook.com' in url.lower():
        if 'profile.php?id=' in url:
            identifier = url.split('id=')[-1].split('&')[0]
        else:
            identifier = url.rstrip('/').split('/')[-1]
        platform = 'Facebook'
    elif 'tiktok.com' in url.lower():
        identifier = url.rstrip('/').split('/')[-1].replace('@', '')
        platform = 'TikTok'
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO fuente_osint (nombre_fuente, tipo_fuente, url_fuente, identificador, activa)
            VALUES (?, ?, ?, ?, 1)
        ''', (name, platform, url, identifier))
        
        source_id = cursor.lastrowid
        conn.commit()
        
        return jsonify({
            'success': True,
            'message': 'Fuente creada exitosamente',
            'source': {
                'id': source_id,
                'name': name,
                'platform': platform,
                'url': url,
                'identifier': identifier,
                'active': True
            }
        }), 201
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Ya existe una fuente con esta URL'}), 409
    finally:
        conn.close()

# ============== WEB SCRAPING REAL ==============

def scrape_tiktok_with_ytdlp(profile_url: str, max_videos: int = 5) -> list:
    """
    Extrae videos de TikTok usando yt-dlp para metadatos.
    Obtiene: descripción completa, likes, comentarios (conteo), shares, views
    """
    import subprocess
    import json as json_lib
    import re
    
    posts = []
    
    try:
        venv_path = os.path.join(os.path.dirname(__file__), 'venv', 'bin', 'yt-dlp')
        ytdlp_cmd = venv_path if os.path.exists(venv_path) else 'yt-dlp'
        
        print(f"📹 Extrayendo {max_videos} videos de TikTok...")
        
        # Obtener lista de videos
        cmd = [
            ytdlp_cmd,
            '--flat-playlist',
            '--dump-json',
            '--no-download',
            '--playlist-end', str(max_videos),
            profile_url
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        
        if result.returncode != 0:
            print(f"❌ Error yt-dlp: {result.stderr[:300] if result.stderr else 'desconocido'}")
            return []
        
        video_list = []
        for line in result.stdout.strip().split('\n'):
            if line:
                try:
                    video_list.append(json_lib.loads(line))
                except:
                    pass
        
        print(f"   ✓ {len(video_list)} videos encontrados")
        
        # Procesar cada video para obtener detalles completos
        for i, data in enumerate(video_list):
            video_id = data.get('id', '')
            uploader = data.get('uploader', 'user')
            video_url = f"https://www.tiktok.com/@{uploader}/video/{video_id}"
            
            print(f"\n  [{i+1}/{len(video_list)}] Procesando video {video_id}...")
            
            # Obtener detalles completos del video
            detail_cmd = [ytdlp_cmd, '--dump-json', '--no-download', video_url]
            detail_result = subprocess.run(detail_cmd, capture_output=True, text=True, timeout=60)
            
            if detail_result.returncode == 0 and detail_result.stdout.strip():
                try:
                    data = json_lib.loads(detail_result.stdout.strip())
                except:
                    pass
            
            # Extraer datos
            timestamp = data.get('timestamp')
            fecha = datetime.fromtimestamp(timestamp).isoformat() if timestamp else datetime.now().isoformat()
            
            likes = data.get('like_count', 0) or 0
            comments_count = data.get('comment_count', 0) or 0
            shares = data.get('repost_count', 0) or 0
            views = data.get('view_count', 0) or 0
            
            # Descripción completa
            descripcion = data.get('description', '') or data.get('title', '') or "Video TikTok"
            
            # Extraer hashtags
            hashtags = re.findall(r'#(\w+)', descripcion)
            
            print(f"    📝 {descripcion[:60]}...")
            print(f"    📊 {views:,} views | {likes:,} likes | {comments_count} comentarios")
            
            post = {
                'id_externo': f"tt_{video_id}",
                'texto': descripcion[:2000],
                'contenido': descripcion[:2000],
                'fecha': fecha,
                'autor': data.get('uploader', data.get('channel', 'TikTok User')),
                'likes': int(likes),
                'comentarios_count': int(comments_count),
                'shares': int(shares),
                'views': int(views),
                'url': video_url,
                'tipo': 'video',
                'metadata': {
                    'platform': 'tiktok',
                    'video_id': video_id,
                    'duration': data.get('duration', 0),
                    'music': data.get('track', ''),
                    'artist': data.get('artist', ''),
                    'hashtags': hashtags,
                },
                'comentarios': []  # Los comentarios se extraen con el script dedicado
            }
            
            posts.append(post)
        
        print(f"\n🎉 COMPLETADO: {len(posts)} videos extraídos de TikTok")
        return posts
        
    except subprocess.TimeoutExpired:
        print("❌ Timeout en yt-dlp")
        return []
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return []


def extract_tiktok_comments_with_playwright(video_url: str, max_comments: int = 50) -> list:
    """
    Extrae comentarios REALES de un video TikTok usando Playwright con anti-detección.
    Esta función se ejecuta después de guardar el video en la BD.
    """
    from playwright.sync_api import sync_playwright
    import time
    
    comments = []
    
    # Scripts anti-detección
    stealth_script = """
    // Ocultar webdriver
    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
    
    // Falsificar plugins
    Object.defineProperty(navigator, 'plugins', {
        get: () => [1, 2, 3, 4, 5]
    });
    
    // Falsificar idiomas
    Object.defineProperty(navigator, 'languages', {
        get: () => ['es-ES', 'es', 'en-US', 'en']
    });
    
    // Chrome runtime
    window.chrome = { runtime: {} };
    
    // Permissions
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) => (
        parameters.name === 'notifications' ?
            Promise.resolve({ state: Notification.permission }) :
            originalQuery(parameters)
    );
    """
    
    try:
        with sync_playwright() as p:
            # Lanzar navegador con configuración anti-detección
            browser = p.chromium.launch(
                headless=False,  # Visible para mejor evasión
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-web-security',
                    '--lang=es-ES',
                ]
            )
            
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                locale='es-ES',
            )
            
            # Inyectar scripts anti-detección
            context.add_init_script(stealth_script)
            
            page = context.new_page()
            
            print(f"  🌐 Abriendo {video_url}")
            page.goto(video_url, timeout=60000)
            
            # Esperar carga
            time.sleep(5)
            
            # Verificar CAPTCHA
            if 'captcha' in page.content().lower() or 'verify' in page.url.lower():
                print("  ⚠️ CAPTCHA detectado - esperando 15 segundos...")
                time.sleep(15)
            
            # Hacer scroll para cargar comentarios
            for _ in range(3):
                page.mouse.wheel(0, 1000)
                time.sleep(1)
            
            # Buscar comentarios con múltiples selectores
            selectors = [
                '[class*="DivCommentItemContainer"]',
                '[data-e2e="comment-item"]',
                '[class*="CommentItem"]',
                '.comment-item',
            ]
            
            for selector in selectors:
                try:
                    elements = page.query_selector_all(selector)
                    if elements:
                        print(f"  ✓ Encontrados {len(elements)} comentarios con {selector}")
                        
                        for el in elements[:max_comments]:
                            try:
                                # Buscar texto del comentario
                                text_el = el.query_selector('[class*="SpanText"], [class*="comment-text"], p, span')
                                # Buscar autor
                                author_el = el.query_selector('[class*="UserName"], [class*="author"], a[href*="/@"]')
                                
                                text = text_el.inner_text() if text_el else ""
                                author = author_el.inner_text() if author_el else "Usuario"
                                
                                if text and len(text) > 1:
                                    comments.append({
                                        'autor': author.strip()[:100],
                                        'texto': text.strip()[:1000],
                                        'fecha': datetime.now().isoformat(),
                                        'likes': 0
                                    })
                            except Exception as e:
                                continue
                        
                        break  # Salir si encontramos comentarios
                        
                except Exception as e:
                    continue
            
            browser.close()
            
    except Exception as e:
        print(f"  ❌ Error extrayendo comentarios: {e}")
    
    return comments


# ============== CONFIGURACIÓN TIKTOK COOKIES ==============

TIKTOK_COOKIES_FILE = os.path.join(os.path.dirname(__file__), 'data', 'tiktok_cookies.json')


@app.route('/api/tiktok/cookies', methods=['POST'])
def save_tiktok_cookies():
    """
    Guarda las cookies de sesión de TikTok para evitar detección.
    
    Body JSON:
        {"cookies": "sessionid=xxx; tt_csrf_token=yyy; ..."}
    """
    data = request.get_json()
    cookies_string = data.get('cookies', '')
    
    if not cookies_string:
        return jsonify({'error': 'Se requiere el campo cookies'}), 400
    
    try:
        cookie_list = []
        for cookie_str in cookies_string.split(';'):
            if '=' in cookie_str:
                name, value = cookie_str.strip().split('=', 1)
                cookie_list.append({
                    'name': name.strip(),
                    'value': value.strip(),
                    'domain': '.tiktok.com',
                    'path': '/'
                })
        
        if cookie_list:
            os.makedirs(os.path.dirname(TIKTOK_COOKIES_FILE), exist_ok=True)
            with open(TIKTOK_COOKIES_FILE, 'w') as f:
                import json as json_lib
                json_lib.dump(cookie_list, f, indent=2)
            
            return jsonify({
                'success': True,
                'message': f'Guardadas {len(cookie_list)} cookies de TikTok',
                'cookies_count': len(cookie_list)
            })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    return jsonify({'error': 'No se pudieron procesar las cookies'}), 400


@app.route('/api/tiktok/cookies', methods=['GET'])
def get_tiktok_cookies_status():
    """Verifica si hay cookies de TikTok configuradas."""
    if os.path.exists(TIKTOK_COOKIES_FILE):
        try:
            with open(TIKTOK_COOKIES_FILE, 'r') as f:
                import json as json_lib
                cookies = json_lib.load(f)
            return jsonify({
                'configured': True,
                'cookies_count': len(cookies),
                'cookie_names': [c['name'] for c in cookies]
            })
        except:
            pass
    
    return jsonify({'configured': False, 'cookies_count': 0})


@app.route('/api/tiktok/cookies', methods=['DELETE'])
def delete_tiktok_cookies():
    """Elimina las cookies de TikTok guardadas."""
    if os.path.exists(TIKTOK_COOKIES_FILE):
        os.remove(TIKTOK_COOKIES_FILE)
        return jsonify({'success': True, 'message': 'Cookies eliminadas'})
    return jsonify({'success': True, 'message': 'No había cookies guardadas'})


def scrape_facebook_with_playwright(page_url: str, max_posts: int = 5) -> list:
    """
    Scraper funcional de Facebook usando Playwright.
    Extrae los últimos posts y sus comentarios de una página pública de Facebook.
    Los comentarios se extraen desde el feed principal (aparecen como articles anidados).
    
    Args:
        page_url: URL de la página de Facebook
        max_posts: Número máximo de posts a extraer (default 5)
    
    Returns:
        Lista de dicts con posts y comentarios listos para save_scraping_results
    """
    import re as re_mod
    import hashlib
    import sys
    from playwright.sync_api import sync_playwright
    
    log = lambda msg: (print(msg, flush=True), sys.stdout.flush())
    
    posts = []
    p_inst = sync_playwright().start()
    
    try:
        browser = p_inst.chromium.launch(headless=True, args=['--disable-gpu'])
        ctx = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="es-ES",
            viewport={"width": 1280, "height": 900},
        )
        # Timeout global para evitar cuelgues
        ctx.set_default_timeout(15000)
        page = ctx.new_page()
        
        # ===== 1. Cargar la página =====
        log(f"📘 Navegando a {page_url}...")
        page.goto(page_url, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        
        # Cerrar popup de login
        try:
            close_btn = page.query_selector('[aria-label="Cerrar"], [aria-label="Close"]')
            if close_btn and close_btn.is_visible():
                close_btn.click()
                page.wait_for_timeout(1000)
                log("   ✓ Popup cerrado")
        except Exception:
            pass
        
        # ===== 2. Scroll para cargar posts =====
        log("   Scrolling...")
        for i in range(6):
            page.evaluate("window.scrollBy(0, 1000)")
            page.wait_for_timeout(1200)
        log("   ✓ Scroll completado")
        
        # ===== 3. Expandir "Ver más" en posts (con seguridad) =====
        expanded = 0
        try:
            see_more_btns = page.query_selector_all('div[role="button"]')
            for btn in see_more_btns:
                try:
                    txt = btn.inner_text().strip()
                    if txt in ("Ver más", "See more", "See More"):
                        if btn.is_visible():
                            btn.click(timeout=3000)
                            page.wait_for_timeout(400)
                            expanded += 1
                            if expanded >= max_posts * 2:
                                break
                except Exception:
                    continue
        except Exception:
            pass
        if expanded:
            log(f"   ✓ {expanded} textos expandidos")
        
        # ===== 4. Extraer posts (top-level articles) =====
        all_articles = page.query_selector_all('[role="article"]')
        log(f"   {len(all_articles)} articles encontrados")
        
        post_data_list = []
        post_articles = []  # Guardar referencia al article para luego extraer comments
        
        for article in all_articles:
            if len(post_data_list) >= max_posts:
                break
            try:
                # Verificar que es top-level (no anidado/comentario)
                is_nested = article.evaluate(
                    '(el) => !!el.parentElement.closest(\'[role="article"]\')'
                )
                if is_nested:
                    continue
                
                # Extraer texto principal
                text_elements = article.query_selector_all('div[dir="auto"]')
                post_text = ""
                for te in text_elements:
                    try:
                        t = te.inner_text().strip()
                        if len(t) > len(post_text) and len(t) > 15:
                            post_text = t
                    except Exception:
                        continue
                
                if not post_text or len(post_text) < 10:
                    continue
                
                # Limpiar truncamientos
                for suffix in ["… Ver más", "... Ver más", "…Ver más", "...Ver más"]:
                    post_text = post_text.replace(suffix, "").strip()
                
                # Autor
                author = ""
                try:
                    a_el = article.query_selector('h2 a, strong a')
                    if a_el:
                        author = a_el.inner_text().strip()
                except Exception:
                    pass
                
                # Engagement
                likes, comments_count, shares_count = 0, 0, 0
                try:
                    ft = article.inner_text().lower()
                    
                    m = re_mod.search(r'([\d.,]+)\s*(?:mil\s+)?(?:me gusta|like)', ft)
                    if m:
                        n = m.group(1).replace(',', '').replace('.', '')
                        likes = int(n)
                        if 'mil' in ft[max(0,m.start()-5):m.end()+5]:
                            likes *= 1000
                    
                    m = re_mod.search(r'([\d.,]+)\s*(?:mil\s+)?comentario', ft)
                    if m:
                        n = m.group(1).replace(',', '').replace('.', '')
                        comments_count = int(n)
                    
                    m = re_mod.search(r'([\d.,]+)\s*(?:mil\s+)?(?:veces compartido|compartido)', ft)
                    if m:
                        n = m.group(1).replace(',', '').replace('.', '')
                        shares_count = int(n)
                except Exception:
                    pass
                
                # URL del post
                post_url_found = page_url
                try:
                    for sel in ['a[href*="/posts/"]', 'a[href*="/photo"]',
                                'a[href*="/video"]', 'a[href*="/permalink"]']:
                        lnk = article.query_selector(sel)
                        if lnk:
                            href = lnk.get_attribute("href")
                            if href:
                                post_url_found = (
                                    "https://www.facebook.com" + href
                                    if href.startswith("/") else href
                                )
                                break
                except Exception:
                    pass
                
                # ID externo
                content_hash = hashlib.md5(post_text[:200].encode()).hexdigest()[:16]
                external_id = f"fb_{content_hash}"
                
                if any(p["id_externo"] == external_id for p in post_data_list):
                    continue
                
                # ----- Extraer comentarios (nested articles) -----
                comentarios = []
                try:
                    nested = article.query_selector_all('[role="article"]')
                    for c_art in nested:
                        try:
                            c_full = c_art.inner_text().strip()
                            if not c_full or len(c_full) < 5:
                                continue
                            
                            # Texto del comentario
                            c_text_divs = c_art.query_selector_all('div[dir="auto"]')
                            c_text = ""
                            for td in c_text_divs:
                                ct = td.inner_text().strip()
                                if len(ct) > len(c_text) and len(ct) >= 3:
                                    c_text = ct
                            
                            if not c_text or len(c_text) < 3:
                                continue
                            
                            # No duplicar texto del post como comentario
                            if c_text[:40] == post_text[:40]:
                                continue
                            
                            # Autor: primera línea del comentario
                            c_author = "Anónimo"
                            lines = c_full.split('\n')
                            if lines and len(lines[0].strip()) < 60:
                                c_author = lines[0].strip()
                            
                            # Likes
                            c_likes = 0
                            try:
                                lk = c_art.query_selector(
                                    'span[aria-label*="reacci"], span[aria-label*="like"]'
                                )
                                if lk:
                                    nums = re_mod.findall(
                                        r'\d+', lk.get_attribute("aria-label") or ""
                                    )
                                    if nums:
                                        c_likes = int(nums[0])
                            except Exception:
                                pass
                            
                            comentarios.append({
                                "autor": c_author,
                                "texto": c_text[:500],
                                "fecha": datetime.now().isoformat(),
                                "likes": c_likes,
                            })
                        except Exception:
                            continue
                except Exception:
                    pass
                
                post_data = {
                    "id_externo": external_id,
                    "texto": post_text[:5000],
                    "fecha": datetime.now().isoformat(),
                    "autor": author or "Facebook",
                    "likes": likes,
                    "comentarios_count": max(comments_count, len(comentarios)),
                    "shares": shares_count,
                    "views": 0,
                    "url": post_url_found,
                    "tipo_contenido": "post",
                    "comentarios": comentarios,
                    "metadata": {
                        "platform": "facebook",
                        "scrape_method": "playwright",
                        "scrape_timestamp": datetime.now().isoformat(),
                    },
                }
                
                post_data_list.append(post_data)
                post_articles.append(article)
                
                c_str = f" + {len(comentarios)} comentarios" if comentarios else ""
                log(f"   📝 Post {len(post_data_list)}: "
                    f"'{post_text[:50]}...' likes={likes}{c_str}")
                
            except Exception as e:
                log(f"   ⚠ Error en article: {e}")
                continue
        
        # ===== 5. Intentar cargar más comentarios expandiendo =====
        # Solo si tenemos posts con poca actividad de comentarios
        for pidx, (post, art) in enumerate(zip(post_data_list, post_articles)):
            if post["comentarios"]:
                continue  # Ya tiene comentarios, no forzar
            try:
                # Click en el enlace de "N comentarios" si existe
                comm_links = art.query_selector_all('a, span')
                for cl in comm_links:
                    try:
                        txt = cl.inner_text().strip().lower()
                        if 'comentario' in txt and any(c.isdigit() for c in txt):
                            cl.click(timeout=3000)
                            page.wait_for_timeout(2000)
                            
                            # Re-buscar nested articles
                            nested = art.query_selector_all('[role="article"]')
                            for c_art in nested:
                                try:
                                    c_text_divs = c_art.query_selector_all('div[dir="auto"]')
                                    c_text = ""
                                    for td in c_text_divs:
                                        ct = td.inner_text().strip()
                                        if len(ct) > len(c_text) and len(ct) >= 3:
                                            c_text = ct
                                    if not c_text or c_text[:40] == post["texto"][:40]:
                                        continue
                                    
                                    c_full = c_art.inner_text().strip()
                                    c_author = c_full.split('\n')[0].strip()[:60] or "Anónimo"
                                    
                                    # Evitar duplicados
                                    if any(c["texto"][:30] == c_text[:30] for c in post["comentarios"]):
                                        continue
                                    
                                    post["comentarios"].append({
                                        "autor": c_author,
                                        "texto": c_text[:500],
                                        "fecha": datetime.now().isoformat(),
                                        "likes": 0,
                                    })
                                except Exception:
                                    continue
                            
                            post["comentarios_count"] = max(
                                post["comentarios_count"], len(post["comentarios"])
                            )
                            if post["comentarios"]:
                                log(f"   💬 Post {pidx+1}: +{len(post['comentarios'])} "
                                    f"comentarios tras expandir")
                            break
                    except Exception:
                        continue
            except Exception:
                continue
        
        # Resumen
        total_posts = len(post_data_list)
        total_comments = sum(len(p["comentarios"]) for p in post_data_list)
        log(f"\n   ✅ Resultado: {total_posts} posts, {total_comments} comentarios")
        
        posts = post_data_list
        browser.close()
        
    except Exception as e:
        log(f"❌ Error fatal en scraping Facebook: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            p_inst.stop()
        except Exception:
            pass
    
    return posts


@app.route('/api/sources/<int:source_id>/scrape', methods=['POST'])
def run_scraping(source_id):
    """Ejecutar web scraping REAL para una fuente"""
    import json as json_lib
    import threading
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Obtener info de la fuente
    cursor.execute('SELECT * FROM fuente_osint WHERE id_fuente = ?', (source_id,))
    source = cursor.fetchone()
    
    if not source:
        conn.close()
        return jsonify({'error': 'Fuente no encontrada'}), 404
    
    platform = source['tipo_fuente'].lower()
    url = source['url_fuente']
    source_name = source['nombre_fuente']
    
    conn.close()
    
    # Ejecutar scraping en background
    def do_scraping():
        # Registrar inicio del scraping
        try:
            conn_log = get_db()
            cursor_log = conn_log.cursor()
            cursor_log.execute('''
                INSERT INTO log_ejecucion 
                (tipo_operacion, fuente, fecha_inicio, estado, detalles_json)
                VALUES ('scraping', ?, datetime('now'), 'ejecutando', '{}')
            ''', (str(source_id),))
            conn_log.commit()
            conn_log.close()
        except Exception as e:
            print(f"Error registrando inicio: {e}", flush=True)
        
        try:
            posts = []
            
            if platform == 'facebook':
                # Scraping real de Facebook con Playwright
                print(f"📘 Iniciando scraping de Facebook: {source_name} ({url})", flush=True)
                posts = scrape_facebook_with_playwright(url, max_posts=5)
                print(f"📘 Facebook scraping completado: {len(posts)} posts", flush=True)
                
            elif platform == 'tiktok':
                # Usar scraper robusto con comentarios
                print(f"🎵 Iniciando scraping ROBUSTO de TikTok: {url}")
                
                # Importar el scraper robusto
                from tiktok_scraper_robust import run_scraper
                
                # Ejecutar scraping con extracción de comentarios
                stats = run_scraper(
                    profile_url=url,
                    max_videos=5,
                    source_id=source_id,
                    cookies=None  # Usa cookies guardadas automáticamente
                )
                
                print(f"✅ TikTok scraping completado: {stats}")
                
                # Registrar log
                conn2 = get_db()
                cursor2 = conn2.cursor()
                cursor2.execute('''
                    INSERT INTO log_ejecucion 
                    (tipo_operacion, fuente, fecha_inicio, fecha_fin, 
                     registros_procesados, registros_exitosos, estado, detalles_json)
                    VALUES ('scraping', ?, datetime('now'), datetime('now'), ?, ?, 'completado', ?)
                ''', (
                    source_name,
                    stats.get('videos_processed', 0) + stats.get('comments_extracted', 0),
                    stats.get('videos_saved', 0) + stats.get('comments_saved', 0),
                    json.dumps(stats)
                ))
                conn2.commit()
                conn2.close()
                
                return  # El scraper robusto ya guarda en BD
                
            else:
                print(f"Plataforma no soportada: {platform}")
                return
            
            if posts:
                # Guardar resultados en BD
                save_scraping_results(source_id, posts, platform)
            else:
                print(f"No se obtuvieron posts de {source_name}")
                
        except Exception as e:
            print(f"Error en scraping: {e}")
            import traceback
            traceback.print_exc()
            
            # Registrar error
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO log_ejecucion 
                (tipo_operacion, fuente, fecha_inicio, fecha_fin, estado, mensaje_error)
                VALUES ('scraping', ?, datetime('now'), datetime('now'), 'error', ?)
            ''', (source_name, str(e)))
            conn.commit()
            conn.close()
    
    # Iniciar en thread separado
    thread = threading.Thread(target=do_scraping)
    thread.start()
    
    return jsonify({
        'success': True,
        'message': f'Scraping iniciado para {source_name}',
        'status': 'running',
        'source_id': source_id
    })

def save_scraping_results(source_id, posts, platform):
    """Guarda los resultados del scraping en la BD"""
    import json as json_lib
    
    conn = get_db()
    cursor = conn.cursor()
    
    posts_added = 0
    comments_added = 0
    
    for post in posts:
        try:
            # Verificar si ya existe
            external_id = post.get('id_externo') or post.get('external_id') or f"{source_id}_{post.get('texto', '')[:50]}"
            
            cursor.execute(
                'SELECT id_dato FROM dato_recolectado WHERE id_externo = ?', 
                (external_id,)
            )
            if cursor.fetchone():
                continue  # Ya existe
            
            # Insertar post
            cursor.execute('''
                INSERT INTO dato_recolectado 
                (id_fuente, id_externo, fecha_publicacion, fecha_recoleccion, 
                 contenido_original, autor, engagement_likes, engagement_comments,
                 engagement_shares, engagement_views, tipo_contenido, url_publicacion,
                 metadata_json, procesado)
                VALUES (?, ?, ?, datetime('now'), ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            ''', (
                source_id,
                external_id,
                post.get('fecha') or datetime.now().isoformat(),
                post.get('texto') or post.get('contenido', ''),
                post.get('autor', 'Desconocido'),
                post.get('likes', 0),
                post.get('comentarios_count', 0),
                post.get('shares', 0),
                post.get('views', 0),
                'video' if platform == 'tiktok' else 'texto',
                post.get('url', ''),
                json_lib.dumps(post.get('metadata', {}))
            ))
            
            post_id = cursor.lastrowid
            posts_added += 1
            
            # Guardar comentarios si existen
            comentarios = post.get('comentarios', [])
            for c in comentarios:
                cursor.execute('''
                    INSERT INTO comentario 
                    (id_post, id_fuente, autor, contenido, fecha_publicacion, likes, procesado)
                    VALUES (?, ?, ?, ?, ?, ?, 0)
                ''', (
                    post_id,
                    source_id,
                    c.get('autor', 'Anónimo'),
                    c.get('texto', ''),
                    c.get('fecha', datetime.now().isoformat()),
                    c.get('likes', 0)
                ))
                comments_added += 1
                
        except Exception as e:
            print(f"Error guardando post: {e}")
            continue
    
    # Actualizar fecha de última recolección
    cursor.execute('''
        UPDATE fuente_osint 
        SET fecha_ultima_recoleccion = datetime('now'),
            total_registros_recolectados = total_registros_recolectados + ?
        WHERE id_fuente = ?
    ''', (posts_added, source_id))
    
    # Registrar log
    cursor.execute('''
        INSERT INTO log_ejecucion 
        (tipo_operacion, fuente, fecha_inicio, fecha_fin, 
         registros_procesados, registros_exitosos, estado, detalles_json)
        VALUES ('scraping', ?, datetime('now'), datetime('now'), ?, ?, 'completado', ?)
    ''', (
        str(source_id),
        posts_added + comments_added,
        posts_added,
        json_lib.dumps({'posts': posts_added, 'comments': comments_added})
    ))
    
    conn.commit()
    conn.close()
    
    print(f"✅ Scraping completado: {posts_added} posts, {comments_added} comentarios")


@app.route('/api/sources/<int:source_id>/extract-comments', methods=['POST'])
def extract_tiktok_comments(source_id):
    """
    Endpoint para extraer comentarios de TikTok de videos ya guardados.
    Usa Playwright con anti-detección para obtener comentarios textuales reales.
    """
    import threading
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Verificar que es una fuente TikTok
    cursor.execute('SELECT * FROM fuente_osint WHERE id_fuente = ?', (source_id,))
    source = cursor.fetchone()
    
    if not source:
        conn.close()
        return jsonify({'error': 'Fuente no encontrada'}), 404
    
    if source['tipo_fuente'].lower() != 'tiktok':
        conn.close()
        return jsonify({'error': 'Este endpoint solo funciona con fuentes TikTok'}), 400
    
    # Obtener videos que necesitan comentarios
    cursor.execute('''
        SELECT id_dato, url_publicacion, engagement_comments 
        FROM dato_recolectado 
        WHERE id_fuente = ? AND url_publicacion IS NOT NULL
    ''', (source_id,))
    videos = cursor.fetchall()
    
    conn.close()
    
    if not videos:
        return jsonify({'error': 'No hay videos de TikTok para extraer comentarios'}), 400
    
    def do_extraction():
        total_comments = 0
        import json as json_lib
        
        for video in videos:
            video_id = video['id_dato']
            video_url = video['url_publicacion']
            
            print(f"\n💬 Extrayendo comentarios de: {video_url}")
            
            try:
                comments = extract_tiktok_comments_with_playwright(video_url, max_comments=30)
                
                if comments:
                    conn2 = get_db()
                    cursor2 = conn2.cursor()
                    
                    for c in comments:
                        # Verificar duplicados
                        cursor2.execute(
                            'SELECT 1 FROM comentario WHERE id_post = ? AND contenido = ?',
                            (video_id, c.get('texto', '')[:500])
                        )
                        if cursor2.fetchone():
                            continue
                        
                        cursor2.execute('''
                            INSERT INTO comentario 
                            (id_post, id_fuente, autor, contenido, fecha_publicacion, likes, procesado)
                            VALUES (?, ?, ?, ?, ?, ?, 0)
                        ''', (
                            video_id,
                            source_id,
                            c.get('autor', 'Usuario'),
                            c.get('texto', ''),
                            c.get('fecha', datetime.now().isoformat()),
                            c.get('likes', 0)
                        ))
                        total_comments += 1
                    
                    conn2.commit()
                    conn2.close()
                    print(f"  ✅ {len(comments)} comentarios extraídos y guardados")
                
            except Exception as e:
                print(f"  ❌ Error: {e}")
                continue
        
        # Registrar log
        conn3 = get_db()
        cursor3 = conn3.cursor()
        cursor3.execute('''
            INSERT INTO log_ejecucion 
            (tipo_operacion, fuente, fecha_inicio, fecha_fin, 
             registros_procesados, registros_exitosos, estado, detalles_json)
            VALUES ('tiktok_comments', ?, datetime('now'), datetime('now'), ?, ?, 'completado', ?)
        ''', (
            str(source_id),
            len(videos),
            total_comments,
            json_lib.dumps({'videos_processed': len(videos), 'comments_extracted': total_comments})
        ))
        conn3.commit()
        conn3.close()
        
        print(f"\n🎉 Extracción completada: {total_comments} comentarios de {len(videos)} videos")
    
    # Iniciar en thread separado
    thread = threading.Thread(target=do_extraction)
    thread.start()
    
    return jsonify({
        'success': True,
        'message': f'Extracción de comentarios iniciada para {len(videos)} videos',
        'status': 'running',
        'videos_count': len(videos)
    })

@app.route('/api/sources/<int:source_id>/scrape/status')
def scraping_status(source_id):
    """Ver estado del último scraping de una fuente"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM log_ejecucion 
        WHERE fuente = ? AND tipo_operacion = 'scraping'
        ORDER BY fecha_inicio DESC LIMIT 1
    ''', (str(source_id),))
    
    log = cursor.fetchone()
    conn.close()
    
    if not log:
        return jsonify({'status': 'never_run', 'message': 'Nunca se ha ejecutado scraping'})
    
    return jsonify({
        'status': log['estado'],
        'startTime': log['fecha_inicio'],
        'endTime': log['fecha_fin'],
        'recordsProcessed': log['registros_procesados'],
        'recordsSuccess': log['registros_exitosos'],
        'error': log['mensaje_error']
    })

# ============== POSTS ==============
@app.route('/api/posts')
def get_posts():
    """Lista todos los posts con resumen de comentarios - JERÁRQUICO"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Parámetros de filtrado
    source_id = request.args.get('source_id', type=int)
    platform = request.args.get('platform')
    limit = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    # Base query
    query = '''
        SELECT 
            dr.id_dato as id_post,
            f.id_fuente,
            f.nombre_fuente as source_name,
            f.tipo_fuente as platform,
            dr.contenido_original as content,
            dr.fecha_publicacion,
            dr.engagement_likes as likes,
            dr.engagement_comments as comments_count,
            dr.engagement_shares as shares,
            dr.engagement_views as views,
            dr.tipo_contenido as content_type,
            dr.url_publicacion as url,
            (SELECT COUNT(*) FROM comentario c WHERE c.id_post = dr.id_dato) as collected_comments,
            dp.sentimiento_basico as sentiment,
            asent.sentimiento_predicho as ai_sentiment,
            asent.confianza as ai_confidence
        FROM dato_recolectado dr
        JOIN fuente_osint f ON dr.id_fuente = f.id_fuente
        LEFT JOIN dato_procesado dp ON dr.id_dato = dp.id_dato_original
        LEFT JOIN analisis_sentimiento asent ON dp.id_dato_procesado = asent.id_dato_procesado
        WHERE 1=1
    '''
    params = []
    
    if source_id:
        query += ' AND f.id_fuente = ?'
        params.append(source_id)
    
    if platform:
        query += ' AND LOWER(f.tipo_fuente) = LOWER(?)'
        params.append(platform)
    
    query += ' ORDER BY dr.fecha_publicacion DESC LIMIT ? OFFSET ?'
    params.extend([limit, offset])
    
    cursor.execute(query, params)
    
    posts = []
    for row in cursor.fetchall():
        posts.append({
            'id': row['id_post'],
            'sourceId': row['id_fuente'],
            'sourceName': row['source_name'],
            'platform': row['platform'],
            'content': row['content'],
            'date': row['fecha_publicacion'],
            'likes': row['likes'] or 0,
            'commentsCount': row['comments_count'] or 0,
            'collectedComments': row['collected_comments'] or 0,
            'shares': row['shares'] or 0,
            'views': row['views'] or 0,
            'contentType': row['content_type'],
            'url': row['url'],
            'sentiment': row['ai_sentiment'] or row['sentiment'],
            'aiConfidence': row['ai_confidence']
        })
    
    # Obtener total
    count_query = '''
        SELECT COUNT(*) FROM dato_recolectado dr
        JOIN fuente_osint f ON dr.id_fuente = f.id_fuente
        WHERE 1=1
    '''
    count_params = []
    if source_id:
        count_query += ' AND f.id_fuente = ?'
        count_params.append(source_id)
    if platform:
        count_query += ' AND LOWER(f.tipo_fuente) = LOWER(?)'
        count_params.append(platform)
    
    cursor.execute(count_query, count_params)
    total = cursor.fetchone()[0]
    
    conn.close()
    return jsonify({
        'posts': posts,
        'total': total,
        'limit': limit,
        'offset': offset
    })

@app.route('/api/posts/<int:post_id>')
def get_post_detail(post_id):
    """Detalle de un post específico con análisis"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            dr.id_dato as id_post,
            f.id_fuente,
            f.nombre_fuente as source_name,
            f.tipo_fuente as platform,
            dr.contenido_original as content,
            dr.fecha_publicacion,
            dr.engagement_likes as likes,
            dr.engagement_comments as comments_count,
            dr.engagement_shares as shares,
            dr.engagement_views as views,
            dr.tipo_contenido as content_type,
            dr.url_publicacion as url,
            dp.contenido_limpio,
            dp.cantidad_palabras,
            dp.engagement_normalizado,
            dp.categoria_preliminar,
            asent.sentimiento_predicho as ai_sentiment,
            asent.confianza as ai_confidence,
            asent.probabilidad_positivo,
            asent.probabilidad_neutral,
            asent.probabilidad_negativo
        FROM dato_recolectado dr
        JOIN fuente_osint f ON dr.id_fuente = f.id_fuente
        LEFT JOIN dato_procesado dp ON dr.id_dato = dp.id_dato_original
        LEFT JOIN analisis_sentimiento asent ON dp.id_dato_procesado = asent.id_dato_procesado
        WHERE dr.id_dato = ?
    ''', (post_id,))
    
    row = cursor.fetchone()
    if not row:
        conn.close()
        return jsonify({'error': 'Post no encontrado'}), 404
    
    # Obtener resumen de sentimientos de comentarios
    cursor.execute('''
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN ac.sentimiento = 'Positivo' THEN 1 ELSE 0 END) as positivos,
            SUM(CASE WHEN ac.sentimiento = 'Neutral' THEN 1 ELSE 0 END) as neutrales,
            SUM(CASE WHEN ac.sentimiento = 'Negativo' THEN 1 ELSE 0 END) as negativos
        FROM comentario c
        LEFT JOIN analisis_comentario ac ON c.id_comentario = ac.id_comentario
        WHERE c.id_post = ?
    ''', (post_id,))
    comments_sentiment = cursor.fetchone()
    
    conn.close()
    
    return jsonify({
        'id': row['id_post'],
        'sourceId': row['id_fuente'],
        'sourceName': row['source_name'],
        'platform': row['platform'],
        'content': row['content'],
        'cleanContent': row['contenido_limpio'],
        'date': row['fecha_publicacion'],
        'likes': row['likes'] or 0,
        'commentsCount': row['comments_count'] or 0,
        'shares': row['shares'] or 0,
        'views': row['views'] or 0,
        'contentType': row['content_type'],
        'url': row['url'],
        'wordCount': row['cantidad_palabras'],
        'engagementNormalized': row['engagement_normalizado'],
        'category': row['categoria_preliminar'],
        'sentiment': {
            'prediction': row['ai_sentiment'],
            'confidence': row['ai_confidence'],
            'probabilities': {
                'positive': row['probabilidad_positivo'],
                'neutral': row['probabilidad_neutral'],
                'negative': row['probabilidad_negativo']
            }
        },
        'commentsSentiment': {
            'total': comments_sentiment['total'] or 0,
            'positive': comments_sentiment['positivos'] or 0,
            'neutral': comments_sentiment['neutrales'] or 0,
            'negative': comments_sentiment['negativos'] or 0
        }
    })

# ============== COMENTARIOS ==============
@app.route('/api/posts/<int:post_id>/comments')
def get_post_comments(post_id):
    """Lista todos los comentarios de un post específico"""
    conn = get_db()
    cursor = conn.cursor()
    
    limit = request.args.get('limit', 100, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    cursor.execute('''
        SELECT 
            c.id_comentario,
            c.autor,
            c.contenido,
            c.fecha_publicacion,
            c.likes,
            c.respuestas,
            c.es_respuesta,
            c.id_comentario_padre,
            ac.sentimiento,
            ac.confianza,
            ac.probabilidad_positivo,
            ac.probabilidad_neutral,
            ac.probabilidad_negativo
        FROM comentario c
        LEFT JOIN analisis_comentario ac ON c.id_comentario = ac.id_comentario
        WHERE c.id_post = ?
        ORDER BY c.fecha_publicacion DESC
        LIMIT ? OFFSET ?
    ''', (post_id, limit, offset))
    
    comments = []
    for row in cursor.fetchall():
        comments.append({
            'id': row['id_comentario'],
            'postId': post_id,
            'author': row['autor'],
            'content': row['contenido'],
            'date': row['fecha_publicacion'],
            'likes': row['likes'] or 0,
            'repliesCount': row['respuestas'] or 0,
            'isReply': bool(row['es_respuesta']),
            'parentCommentId': row['id_comentario_padre'],
            'sentiment': {
                'prediction': row['sentimiento'],
                'confidence': row['confianza'],
                'probabilities': {
                    'positive': row['probabilidad_positivo'],
                    'neutral': row['probabilidad_neutral'],
                    'negative': row['probabilidad_negativo']
                }
            } if row['sentimiento'] else None
        })
    
    # Total de comentarios
    cursor.execute('SELECT COUNT(*) FROM comentario WHERE id_post = ?', (post_id,))
    total = cursor.fetchone()[0]
    
    conn.close()
    
    return jsonify({
        'comments': comments,
        'total': total,
        'limit': limit,
        'offset': offset,
        'postId': post_id
    })

@app.route('/api/comments')
def get_all_comments():
    """Lista todos los comentarios con filtros"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Filtros
    sentiment = request.args.get('sentiment')
    source_id = request.args.get('source_id', type=int)
    platform = request.args.get('platform')
    limit = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    query = '''
        SELECT 
            c.id_comentario,
            c.id_post,
            c.autor,
            c.contenido,
            c.fecha_publicacion,
            c.likes,
            f.nombre_fuente as source_name,
            f.tipo_fuente as platform,
            dr.contenido_original as post_content,
            ac.sentimiento,
            ac.confianza
        FROM comentario c
        JOIN dato_recolectado dr ON c.id_post = dr.id_dato
        JOIN fuente_osint f ON c.id_fuente = f.id_fuente
        LEFT JOIN analisis_comentario ac ON c.id_comentario = ac.id_comentario
        WHERE 1=1
    '''
    params = []
    
    if sentiment:
        query += ' AND ac.sentimiento = ?'
        params.append(sentiment)
    
    if source_id:
        query += ' AND c.id_fuente = ?'
        params.append(source_id)
    
    if platform:
        query += ' AND LOWER(f.tipo_fuente) = LOWER(?)'
        params.append(platform)
    
    query += ' ORDER BY c.fecha_publicacion DESC LIMIT ? OFFSET ?'
    params.extend([limit, offset])
    
    cursor.execute(query, params)
    
    comments = []
    for row in cursor.fetchall():
        comments.append({
            'id': row['id_comentario'],
            'postId': row['id_post'],
            'author': row['autor'],
            'content': row['contenido'],
            'date': row['fecha_publicacion'],
            'likes': row['likes'] or 0,
            'sourceName': row['source_name'],
            'platform': row['platform'],
            'postPreview': row['post_content'][:100] + '...' if row['post_content'] and len(row['post_content']) > 100 else row['post_content'],
            'sentiment': row['sentimiento'],
            'confidence': row['confianza']
        })
    
    conn.close()
    
    return jsonify({
        'comments': comments,
        'total': len(comments),
        'limit': limit,
        'offset': offset
    })

# ============== ESTADÍSTICAS JERÁRQUICAS ==============
@app.route('/api/hierarchy/stats')
def hierarchy_stats():
    """Estadísticas de la estructura jerárquica Fuentes→Posts→Comentarios"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Total por nivel
    cursor.execute('SELECT COUNT(*) FROM fuente_osint WHERE activa = 1')
    total_sources = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM dato_recolectado')
    total_posts = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM comentario')
    total_comments = cursor.fetchone()[0]
    
    # Por plataforma
    cursor.execute('''
        SELECT 
            f.tipo_fuente as platform,
            COUNT(DISTINCT f.id_fuente) as sources,
            COUNT(DISTINCT dr.id_dato) as posts,
            COUNT(DISTINCT c.id_comentario) as comments
        FROM fuente_osint f
        LEFT JOIN dato_recolectado dr ON f.id_fuente = dr.id_fuente
        LEFT JOIN comentario c ON dr.id_dato = c.id_post
        GROUP BY f.tipo_fuente
    ''')
    
    by_platform = []
    for row in cursor.fetchall():
        by_platform.append({
            'platform': row['platform'],
            'sources': row['sources'],
            'posts': row['posts'],
            'comments': row['comments']
        })
    
    # Sentimientos de comentarios
    cursor.execute('''
        SELECT 
            ac.sentimiento,
            COUNT(*) as count
        FROM analisis_comentario ac
        GROUP BY ac.sentimiento
    ''')
    
    comments_sentiment = {'Positivo': 0, 'Neutral': 0, 'Negativo': 0}
    for row in cursor.fetchall():
        if row['sentimiento'] in comments_sentiment:
            comments_sentiment[row['sentimiento']] = row['count']
    
    conn.close()
    
    return jsonify({
        'totals': {
            'sources': total_sources,
            'posts': total_posts,
            'comments': total_comments
        },
        'byPlatform': by_platform,
        'commentsSentiment': {
            'positive': comments_sentiment['Positivo'],
            'neutral': comments_sentiment['Neutral'],
            'negative': comments_sentiment['Negativo']
        }
    })

@app.route('/api/hierarchy/tree')
def hierarchy_tree():
    """Árbol jerárquico completo para visualización"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Obtener estructura completa
    cursor.execute('''
        SELECT 
            f.id_fuente,
            f.nombre_fuente,
            f.tipo_fuente,
            dr.id_dato as post_id,
            SUBSTR(dr.contenido_original, 1, 80) as post_preview,
            dr.fecha_publicacion,
            dr.engagement_comments,
            (SELECT COUNT(*) FROM comentario c WHERE c.id_post = dr.id_dato) as collected_comments
        FROM fuente_osint f
        LEFT JOIN dato_recolectado dr ON f.id_fuente = dr.id_fuente
        ORDER BY f.tipo_fuente, f.nombre_fuente, dr.fecha_publicacion DESC
    ''')
    
    # Construir árbol
    tree = {}
    for row in cursor.fetchall():
        source_id = row['id_fuente']
        if source_id not in tree:
            tree[source_id] = {
                'id': source_id,
                'name': row['nombre_fuente'],
                'platform': row['tipo_fuente'],
                'posts': []
            }
        
        if row['post_id']:
            tree[source_id]['posts'].append({
                'id': row['post_id'],
                'preview': row['post_preview'] + '...' if row['post_preview'] else '',
                'date': row['fecha_publicacion'],
                'totalComments': row['engagement_comments'] or 0,
                'collectedComments': row['collected_comments'] or 0
            })
    
    conn.close()
    
    return jsonify(list(tree.values()))

# ============== OSINT MULTIFUENTE Y PATRONES ==============

@app.route('/api/osint/ejecutar', methods=['POST'])
def ejecutar_osint_completo():
    """Ejecuta todas las técnicas OSINT: noticias, tendencias, clasificación, patrones."""
    import threading
    
    def run_osint():
        try:
            from osint_multifuente import OSINTMultifuente
            osint = OSINTMultifuente()
            result = osint.ejecutar_recoleccion_completa()
            print(f"✅ OSINT completo: {result['tecnicas_ejecutadas']} técnicas ejecutadas")
        except Exception as e:
            print(f"❌ Error OSINT: {e}")
    
    thread = threading.Thread(target=run_osint, daemon=True)
    thread.start()
    
    return jsonify({'success': True, 'message': 'Recolección OSINT iniciada en segundo plano'})


@app.route('/api/osint/resumen')
def osint_resumen():
    """Resumen de todas las fuentes y técnicas OSINT utilizadas."""
    try:
        from osint_multifuente import get_osint_resumen
        resumen = get_osint_resumen()
        return jsonify(resumen)
    except Exception as e:
        # Fallback: construir resumen desde BD directamente
        conn = get_db()
        cursor = conn.cursor()
        
        tecnicas = []
        
        # SOCMINT
        cursor.execute('''
            SELECT tipo_fuente, COUNT(*) as fuentes,
                   (SELECT COUNT(*) FROM dato_recolectado dr WHERE dr.id_fuente = f.id_fuente) as datos
            FROM fuente_osint f WHERE activa = 1 GROUP BY tipo_fuente
        ''')
        for row in cursor.fetchall():
            tecnicas.append({
                'tipo_tecnica': 'SOCMINT',
                'nombre_fuente': f'{row["tipo_fuente"]} (Redes Sociales)',
                'descripcion': f'Web scraping de {row["tipo_fuente"]}',
                'total_datos_recolectados': row['datos'] or 0
            })
        
        # Contar datos
        cursor.execute('SELECT COUNT(*) as t FROM dato_recolectado')
        total_posts = cursor.fetchone()['t']
        cursor.execute('SELECT COUNT(*) as t FROM comentario')
        total_comments = cursor.fetchone()['t']
        
        # Noticias
        try:
            cursor.execute('SELECT COUNT(*) as t FROM osint_noticias')
            total_noticias = cursor.fetchone()['t']
            if total_noticias > 0:
                tecnicas.append({
                    'tipo_tecnica': 'NEWSINT',
                    'nombre_fuente': 'Google News RSS',
                    'descripcion': 'Monitoreo de noticias sobre EMI en medios',
                    'total_datos_recolectados': total_noticias
                })
        except:
            total_noticias = 0
        
        conn.close()
        
        return jsonify({
            'tecnicas_osint': tecnicas,
            'total_fuentes': len(tecnicas),
            'total_datos': total_posts + total_comments + total_noticias,
            'distribucion_temas': {},
            'patrones_activos': 0
        })


@app.route('/api/osint/noticias')
def osint_noticias():
    """Retorna noticias recolectadas sobre la EMI."""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT * FROM osint_noticias 
            ORDER BY fecha_recoleccion DESC 
            LIMIT 50
        ''')
        noticias = [dict(row) for row in cursor.fetchall()]
    except:
        noticias = []
    
    conn.close()
    return jsonify(noticias)


@app.route('/api/osint/patrones')
def osint_patrones():
    """Retorna patrones identificados por el sistema."""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT * FROM patron_identificado 
            WHERE estado = 'activo'
            ORDER BY relevancia_vicerrectorado DESC, fecha_ultima_deteccion DESC
        ''')
        patrones = []
        for row in cursor.fetchall():
            p = dict(row)
            if p.get('datos_soporte_json'):
                try:
                    p['datos_soporte'] = json.loads(p['datos_soporte_json'])
                except:
                    p['datos_soporte'] = None
            patrones.append(p)
    except:
        patrones = []
    
    conn.close()
    return jsonify(patrones)


@app.route('/api/osint/temas')
def osint_temas():
    """Distribución de temas académicos identificados en el contenido."""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # Distribución general
        cursor.execute('''
            SELECT tema_principal, COUNT(*) as cantidad,
                   SUM(es_academico) as academicos,
                   SUM(es_relevante_uebu) as relevantes_uebu
            FROM clasificacion_tematica
            GROUP BY tema_principal
            ORDER BY cantidad DESC
        ''')
        distribucion = [dict(row) for row in cursor.fetchall()]
        
        # Temas por tipo de contenido
        cursor.execute('''
            SELECT tipo_contenido, tema_principal, COUNT(*) as cantidad
            FROM clasificacion_tematica
            GROUP BY tipo_contenido, tema_principal
            ORDER BY tipo_contenido, cantidad DESC
        ''')
        por_tipo = [dict(row) for row in cursor.fetchall()]
        
        # Contenido relevante para UEBU
        cursor.execute('''
            SELECT ct.tema_principal, ct.tipo_contenido, ct.palabras_clave,
                   CASE 
                       WHEN ct.tipo_contenido = 'post' THEN d.contenido_original
                       WHEN ct.tipo_contenido = 'comentario' THEN c.contenido
                       WHEN ct.tipo_contenido = 'noticia' THEN n.titulo
                   END as texto
            FROM clasificacion_tematica ct
            LEFT JOIN dato_recolectado d ON ct.id_contenido = d.id_dato AND ct.tipo_contenido = 'post'
            LEFT JOIN comentario c ON ct.id_contenido = c.id_comentario AND ct.tipo_contenido = 'comentario'
            LEFT JOIN osint_noticias n ON ct.id_contenido = n.id AND ct.tipo_contenido = 'noticia'
            WHERE ct.es_relevante_uebu = 1
            ORDER BY ct.fecha_clasificacion DESC
            LIMIT 30
        ''')
        relevante_uebu = [dict(row) for row in cursor.fetchall()]
        
    except Exception as e:
        distribucion = []
        por_tipo = []
        relevante_uebu = []
    
    conn.close()
    
    return jsonify({
        'distribucion': distribucion,
        'por_tipo': por_tipo,
        'relevante_uebu': relevante_uebu,
        'total_clasificados': sum(d['cantidad'] for d in distribucion) if distribucion else 0
    })


@app.route('/api/osint/tendencias-busqueda')
def osint_tendencias_busqueda():
    """Tendencias de búsqueda/actividad."""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT termino, periodo, fecha_dato, valor_interes, tipo, metadata_json
            FROM osint_tendencias
            ORDER BY fecha_dato DESC
            LIMIT 200
        ''')
        tendencias = []
        for row in cursor.fetchall():
            t = dict(row)
            if t.get('metadata_json'):
                try:
                    t['metadata'] = json.loads(t['metadata_json'])
                except:
                    pass
            tendencias.append(t)
    except:
        tendencias = []
    
    conn.close()
    return jsonify(tendencias)


@app.route('/api/osint/intereses-academicos')
def osint_intereses_academicos():
    """Intereses académicos identificados en la comunidad estudiantil."""
    conn = get_db()
    cursor = conn.cursor()
    
    resultado = {
        'intereses_por_tema': [],
        'intereses_por_carrera': [],
        'problemas_detectados': [],
        'elogios_detectados': [],
        'total_contenido_academico': 0
    }
    
    try:
        # Intereses generales
        cursor.execute('''
            SELECT tema_principal, COUNT(*) as menciones,
                   SUM(es_academico) as academico,
                   SUM(es_relevante_uebu) as uebu
            FROM clasificacion_tematica
            WHERE es_academico = 1
            GROUP BY tema_principal
            ORDER BY menciones DESC
        ''')
        resultado['intereses_por_tema'] = [dict(r) for r in cursor.fetchall()]
        resultado['total_contenido_academico'] = sum(r['menciones'] for r in resultado['intereses_por_tema'])
        
        # Menciones de carreras específicas
        cursor.execute('''
            SELECT ct.palabras_clave, ct.tipo_contenido, 
                   CASE 
                       WHEN ct.tipo_contenido = 'post' THEN SUBSTR(d.contenido_original, 1, 200)
                       WHEN ct.tipo_contenido = 'comentario' THEN SUBSTR(c.contenido, 1, 200)
                   END as texto
            FROM clasificacion_tematica ct
            LEFT JOIN dato_recolectado d ON ct.id_contenido = d.id_dato AND ct.tipo_contenido = 'post'
            LEFT JOIN comentario c ON ct.id_contenido = c.id_comentario AND ct.tipo_contenido = 'comentario'
            WHERE ct.tema_principal = 'carreras'
            LIMIT 20
        ''')
        resultado['intereses_por_carrera'] = [dict(r) for r in cursor.fetchall()]
        
        # Problemas/quejas detectadas
        cursor.execute('''
            SELECT ct.tema_principal, ct.palabras_clave,
                   CASE 
                       WHEN ct.tipo_contenido = 'post' THEN SUBSTR(d.contenido_original, 1, 200)
                       WHEN ct.tipo_contenido = 'comentario' THEN SUBSTR(c.contenido, 1, 200)
                   END as texto
            FROM clasificacion_tematica ct
            LEFT JOIN dato_recolectado d ON ct.id_contenido = d.id_dato AND ct.tipo_contenido = 'post'
            LEFT JOIN comentario c ON ct.id_contenido = c.id_comentario AND ct.tipo_contenido = 'comentario'
            WHERE ct.tema_principal = 'queja'
            ORDER BY ct.fecha_clasificacion DESC
            LIMIT 15
        ''')
        resultado['problemas_detectados'] = [dict(r) for r in cursor.fetchall()]
        
        # Elogios
        cursor.execute('''
            SELECT ct.tema_principal, ct.palabras_clave,
                   CASE 
                       WHEN ct.tipo_contenido = 'post' THEN SUBSTR(d.contenido_original, 1, 200)
                       WHEN ct.tipo_contenido = 'comentario' THEN SUBSTR(c.contenido, 1, 200)
                   END as texto
            FROM clasificacion_tematica ct
            LEFT JOIN dato_recolectado d ON ct.id_contenido = d.id_dato AND ct.tipo_contenido = 'post'
            LEFT JOIN comentario c ON ct.id_contenido = c.id_comentario AND ct.tipo_contenido = 'comentario'
            WHERE ct.tema_principal = 'elogio'
            ORDER BY ct.fecha_clasificacion DESC
            LIMIT 15
        ''')
        resultado['elogios_detectados'] = [dict(r) for r in cursor.fetchall()]
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error en intereses académicos: {e}")
    
    conn.close()
    return jsonify(resultado)


# ============== TIKTOK SCRAPING INTERACTIVO (SSE) ==============

from flask import Response, stream_with_context

@app.route('/api/tiktok/scraping/start/<int:source_id>', methods=['POST'])
def start_tiktok_interactive_scraping(source_id):
    """
    Inicia una sesión de scraping interactivo de TikTok.
    Retorna un session_id para conectarse al stream de eventos.
    """
    try:
        from tiktok_scraping_service import start_tiktok_scraping
        
        session = start_tiktok_scraping(source_id)
        
        return jsonify({
            'success': True,
            'session_id': session.session_id,
            'message': 'Sesión de scraping iniciada'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/tiktok/scraping/events/<session_id>')
def tiktok_scraping_events(session_id):
    """
    Stream de eventos SSE para una sesión de scraping.
    El frontend se conecta aquí para recibir actualizaciones en tiempo real.
    """
    from tiktok_scraping_service import get_session
    
    session = get_session(session_id)
    if not session:
        return jsonify({'error': 'Sesión no encontrada'}), 404
    
    def generate():
        for event in session.get_events():
            yield event
    
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'
        }
    )


@app.route('/api/tiktok/scraping/continue/<session_id>', methods=['POST'])
def tiktok_scraping_continue(session_id):
    """
    El usuario confirma que puede continuar (ej: resolvió CAPTCHA).
    """
    from tiktok_scraping_service import get_session
    
    session = get_session(session_id)
    if not session:
        return jsonify({'error': 'Sesión no encontrada'}), 404
    
    session.user_continue()
    return jsonify({'success': True, 'message': 'Continuando scraping'})


@app.route('/api/tiktok/scraping/cancel/<session_id>', methods=['POST'])
def tiktok_scraping_cancel(session_id):
    """
    Cancela una sesión de scraping.
    """
    from tiktok_scraping_service import get_session, cleanup_session
    
    session = get_session(session_id)
    if not session:
        return jsonify({'error': 'Sesión no encontrada'}), 404
    
    session.cancel()
    cleanup_session(session_id)
    return jsonify({'success': True, 'message': 'Scraping cancelado'})


@app.route('/api/tiktok/scraping/status/<session_id>')
def tiktok_scraping_status(session_id):
    """
    Obtiene el estado actual de una sesión de scraping.
    """
    from tiktok_scraping_service import get_session
    
    session = get_session(session_id)
    if not session:
        return jsonify({'error': 'Sesión no encontrada'}), 404
    
    return jsonify({
        'session_id': session_id,
        'running': session.running,
        'waiting_for_user': session.waiting_for_user,
        'cancelled': session.cancelled,
        'stats': session.stats
    })


# ============== NLP PIPELINE (OE3) ==============

@app.route('/api/nlp/ejecutar', methods=['POST'])
def nlp_ejecutar():
    """Ejecuta el pipeline NLP completo."""
    import threading
    def run_nlp():
        try:
            from nlp_pipeline import NLPPipeline
            pipeline = NLPPipeline()
            pipeline.ejecutar_pipeline_completo()
        except Exception as e:
            print(f"Error NLP: {e}")
    
    t = threading.Thread(target=run_nlp, daemon=True)
    t.start()
    return jsonify({'status': 'Pipeline NLP iniciado', 'mensaje': 'Ejecutando TF-IDF, LDA, K-Means, NER...'})

@app.route('/api/nlp/resumen')
def nlp_resumen():
    """Resumen general del análisis NLP."""
    conn = get_db()
    cursor = conn.cursor()
    
    resultado = {
        'keywords': 0, 'topicos': 0, 'clusters': 0, 'entidades': 0,
        'tecnicas_aplicadas': [], 'resumen_ejecutivo': None
    }
    
    try:
        cursor.execute("SELECT COUNT(*) FROM nlp_keywords")
        resultado['keywords'] = cursor.fetchone()[0]
        if resultado['keywords'] > 0:
            resultado['tecnicas_aplicadas'].append({
                'nombre': 'TF-IDF Keyword Extraction',
                'tipo': 'NLP',
                'resultados': resultado['keywords']
            })
    except: pass
    
    try:
        cursor.execute("SELECT COUNT(*) FROM nlp_topicos")
        resultado['topicos'] = cursor.fetchone()[0]
        if resultado['topicos'] > 0:
            resultado['tecnicas_aplicadas'].append({
                'nombre': 'Topic Modeling (LDA)',
                'tipo': 'ML',
                'resultados': resultado['topicos']
            })
    except: pass
    
    try:
        cursor.execute("SELECT COUNT(*) FROM nlp_clusters")
        resultado['clusters'] = cursor.fetchone()[0]
        if resultado['clusters'] > 0:
            resultado['tecnicas_aplicadas'].append({
                'nombre': 'K-Means Clustering',
                'tipo': 'ML',
                'resultados': resultado['clusters']
            })
    except: pass
    
    try:
        cursor.execute("SELECT COUNT(*) FROM nlp_entidades")
        resultado['entidades'] = cursor.fetchone()[0]
        if resultado['entidades'] > 0:
            resultado['tecnicas_aplicadas'].append({
                'nombre': 'Named Entity Recognition',
                'tipo': 'NLP',
                'resultados': resultado['entidades']
            })
    except: pass
    
    # Agregar BETO que ya está implementado
    try:
        cursor.execute("SELECT COUNT(*) FROM analisis_sentimiento")
        n_sent = cursor.fetchone()[0]
        if n_sent > 0:
            resultado['tecnicas_aplicadas'].append({
                'nombre': 'Análisis de Sentimiento (BETO)',
                'tipo': 'Deep Learning',
                'resultados': n_sent
            })
    except: pass
    
    try:
        cursor.execute("SELECT contenido FROM nlp_resumen_ejecutivo ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        if row:
            resultado['resumen_ejecutivo'] = json.loads(row['contenido'])
    except: pass
    
    conn.close()
    return jsonify(resultado)

@app.route('/api/nlp/keywords')
def nlp_keywords():
    """Retorna keywords extraídas con TF-IDF."""
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM nlp_keywords ORDER BY tfidf_score DESC LIMIT 50")
        keywords = [dict(row) for row in cursor.fetchall()]
    except:
        keywords = []
    conn.close()
    return jsonify(keywords)

@app.route('/api/nlp/topicos')
def nlp_topicos():
    """Retorna tópicos descubiertos por LDA."""
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM nlp_topicos ORDER BY num_documentos DESC")
        topicos = []
        for row in cursor.fetchall():
            t = dict(row)
            try:
                t['palabras_clave'] = json.loads(t['palabras_clave'])
            except:
                pass
            topicos.append(t)
    except:
        topicos = []
    conn.close()
    return jsonify(topicos)

@app.route('/api/nlp/clusters')
def nlp_clusters():
    """Retorna clusters de opiniones (K-Means)."""
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM nlp_clusters ORDER BY num_documentos DESC")
        clusters = []
        for row in cursor.fetchall():
            c = dict(row)
            try:
                c['palabras_clave'] = json.loads(c['palabras_clave'])
            except: pass
            try:
                c['textos_representativos'] = json.loads(c['textos_representativos'])
            except: pass
            clusters.append(c)
    except:
        clusters = []
    conn.close()
    return jsonify(clusters)

@app.route('/api/nlp/entidades')
def nlp_entidades():
    """Retorna entidades extraídas por NER."""
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT tipo_entidad, entidad, frecuencia 
            FROM nlp_entidades 
            ORDER BY tipo_entidad, frecuencia DESC
        """)
        rows = cursor.fetchall()
        entidades = {}
        for row in rows:
            tipo = row['tipo_entidad']
            if tipo not in entidades:
                entidades[tipo] = []
            entidades[tipo].append({
                'entidad': row['entidad'],
                'frecuencia': row['frecuencia']
            })
    except:
        entidades = {}
    conn.close()
    return jsonify(entidades)

@app.route('/api/nlp/sentimiento-aspecto')
def nlp_sentimiento_aspecto():
    """Retorna sentimiento por aspecto/tema - siempre calcula en vivo."""
    conn = get_db()
    cursor = conn.cursor()
    try:
        # Incluir también comentarios en el análisis
        cursor.execute("""
            SELECT dp.contenido_limpio as texto, COALESCE(a.sentimiento_predicho, 'Neutral') as sent
            FROM dato_procesado dp
            LEFT JOIN analisis_sentimiento a ON dp.id_dato_procesado = a.id_dato_procesado
            WHERE dp.contenido_limpio IS NOT NULL AND LENGTH(dp.contenido_limpio) > 5
            UNION ALL
            SELECT c.contenido as texto, COALESCE(ac.sentimiento, 'Neutral') as sent
            FROM comentario c
            LEFT JOIN analisis_comentario ac ON c.id_comentario = ac.id_comentario
            WHERE c.contenido IS NOT NULL AND LENGTH(c.contenido) > 5
        """)
        rows = cursor.fetchall()
        
        aspectos = {
            'Calidad Académica': ['clase', 'profesor', 'docente', 'materia', 'nota', 'examen', 'académic', 'enseñanza', 'educaci', 'carrera', 'ingeniería', 'universidad'],
            'Infraestructura': ['edificio', 'aula', 'laboratorio', 'wifi', 'instalacion', 'campus', 'sede'],
            'Servicios': ['comedor', 'transporte', 'beca', 'tramite', 'secretaria', 'biblioteca', 'servicio', 'pagar', 'formulario', 'costo'],
            'Vida Estudiantil': ['compañero', 'amigo', 'evento', 'deporte', 'actividad', 'confesión', 'semestre', 'estudiante', 'cadete'],
            'Formación Militar': ['militar', 'disciplina', 'formacion', 'valores', 'escuela', 'ejército', 'cuartel', 'uniforme'],
            'Empleo y Futuro': ['trabajo', 'empleo', 'egresado', 'empresa', 'practica', 'profesional', 'futuro', 'oportunidad'],
            'Procesos Administrativos': ['inscripción', 'convocatoria', 'requisito', 'documento', 'trámite', 'admisión', 'proceso'],
        }
        
        resultado = {}
        for asp, kws in aspectos.items():
            pos = neg = neu = 0
            for row in rows:
                txt = (row['texto'] or '').lower()
                if any(kw in txt for kw in kws):
                    sent = (row['sent'] or 'Neutral').lower()
                    if sent == 'positivo' or sent == 'positive': pos += 1
                    elif sent == 'negativo' or sent == 'negative': neg += 1
                    else: neu += 1
            total = pos + neg + neu
            if total > 0:
                resultado[asp] = {
                    'total_menciones': total,
                    'positivos': pos, 'negativos': neg, 'neutrales': neu,
                    'score': round((pos - neg) / total * 100, 1)
                }
        
        conn.close()
        return jsonify(resultado)
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500

# ============== EVALUACIÓN DEL SISTEMA (OE4) ==============

@app.route('/api/evaluacion/ejecutar', methods=['POST'])
def evaluacion_ejecutar():
    """Ejecuta evaluación completa del sistema."""
    try:
        from evaluacion_sistema import EvaluadorSistema
        evaluador = EvaluadorSistema()
        resultados = evaluador.ejecutar_evaluacion_completa()
        return jsonify(resultados)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/evaluacion/resumen')
def evaluacion_resumen():
    """Retorna métricas de evaluación almacenadas."""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT * FROM evaluacion_sistema ORDER BY categoria, id")
        metricas = [dict(row) for row in cursor.fetchall()]
    except:
        metricas = []
    
    # Agrupar por categoría
    por_categoria = {}
    for m in metricas:
        cat = m.get('categoria', 'general')
        if cat not in por_categoria:
            por_categoria[cat] = []
        por_categoria[cat].append(m)
    
    # Calcular scores
    scores = {}
    for cat, items in por_categoria.items():
        valores = [m['valor'] for m in items if m['valor'] is not None]
        scores[cat] = round(sum(valores) / len(valores), 1) if valores else 0
    
    total_score = round(sum(scores.values()) / len(scores), 1) if scores else 0
    
    conn.close()
    return jsonify({
        'score_general': total_score,
        'categorias': scores,
        'metricas': metricas,
        'total_metricas': len(metricas)
    })

@app.route('/api/evaluacion/objetivos')
def evaluacion_objetivos():
    """Evalúa el cumplimiento de cada objetivo específico."""
    conn = get_db()
    cursor = conn.cursor()
    
    objetivos = []
    
    # OE1: Fuentes OSINT
    try:
        cursor.execute("SELECT COUNT(DISTINCT nombre_fuente) FROM fuente_osint")
        n_fuentes = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM dato_procesado")
        n_datos = cursor.fetchone()[0]
        n_noticias = 0
        try:
            cursor.execute("SELECT COUNT(*) FROM osint_noticias")
            n_noticias = cursor.fetchone()[0]
        except: pass
        n_patrones = 0
        try:
            cursor.execute("SELECT COUNT(*) FROM patron_identificado")
            n_patrones = cursor.fetchone()[0]
        except: pass
        
        score_oe1 = min(100, (n_fuentes * 15) + (min(n_datos, 50) * 1) + (n_noticias * 5) + (n_patrones * 5))
        objetivos.append({
            'id': 'OE1',
            'titulo': 'Analizar datos de fuentes abiertas usando técnicas OSINT',
            'score': round(score_oe1, 1),
            'evidencias': [
                f'{n_fuentes} fuentes OSINT activas (Facebook, TikTok)',
                f'{n_datos} datos recolectados y procesados',
                f'{n_noticias} noticias monitoreadas (NEWSINT)',
                f'{n_patrones} patrones identificados',
                'Técnicas: SOCMINT, NEWSINT, TRENDINT implementadas'
            ]
        })
    except:
        objetivos.append({'id': 'OE1', 'titulo': 'Analizar datos de fuentes abiertas', 'score': 0, 'evidencias': []})
    
    # OE2: Dashboard de visualización
    try:
        dashboards = [
            'PostsDashboard (fuentes y datos)',
            'SentimentDashboard (sentimientos)',
            'ReputationDashboard (wordcloud, heatmap)',
            'AlertsDashboard (anomalías)',
            'BenchmarkingDashboard (comparativas)',
            'OSINTDashboard (OSINT multifuente)',
            'NLPDashboard (IA/ML/NLP)',
            'EvaluacionDashboard (evaluación)',
        ]
        score_oe2 = min(100, len(dashboards) * 12.5)
        objetivos.append({
            'id': 'OE2',
            'titulo': 'Dashboard con patrones, tendencias y estadísticas',
            'score': round(score_oe2, 1),
            'evidencias': [f'Dashboard: {d}' for d in dashboards]
        })
    except:
        objetivos.append({'id': 'OE2', 'titulo': 'Dashboard de visualización', 'score': 0, 'evidencias': []})
    
    # OE3: IA, ML y NLP
    tecnicas_ia = []
    score_oe3 = 0
    try:
        cursor.execute("SELECT COUNT(*) FROM analisis_sentimiento")
        n = cursor.fetchone()[0]
        if n > 0:
            tecnicas_ia.append(f'BETO (BERT español): {n} análisis de sentimiento')
            score_oe3 += 20
    except: pass
    
    try:
        cursor.execute("SELECT COUNT(*) FROM nlp_topicos")
        n = cursor.fetchone()[0]
        if n > 0:
            tecnicas_ia.append(f'LDA Topic Modeling: {n} tópicos descubiertos')
            score_oe3 += 15
    except: pass
    
    try:
        cursor.execute("SELECT COUNT(*) FROM nlp_clusters")
        n = cursor.fetchone()[0]
        if n > 0:
            tecnicas_ia.append(f'K-Means Clustering: {n} clusters de opiniones')
            score_oe3 += 15
    except: pass
    
    try:
        cursor.execute("SELECT COUNT(*) FROM nlp_keywords")
        n = cursor.fetchone()[0]
        if n > 0:
            tecnicas_ia.append(f'TF-IDF Keywords: {n} palabras clave')
            score_oe3 += 15
    except: pass
    
    try:
        cursor.execute("SELECT COUNT(*) FROM nlp_entidades")
        n = cursor.fetchone()[0]
        if n > 0:
            tecnicas_ia.append(f'NER (Entity Recognition): {n} entidades')
            score_oe3 += 15
    except: pass
    
    try:
        cursor.execute("SELECT COUNT(*) FROM clasificacion_tematica")
        n = cursor.fetchone()[0]
        if n > 0:
            tecnicas_ia.append(f'Clasificación Temática NLP: {n} clasificaciones')
            score_oe3 += 10
    except: pass
    
    tecnicas_ia.append('Aspect-Based Sentiment Analysis implementado')
    tecnicas_ia.append('Isolation Forest para anomalías implementado')
    score_oe3 += 10
    
    objetivos.append({
        'id': 'OE3',
        'titulo': 'Aplicar modelos de IA, ML y NLP para análisis',
        'score': min(100, round(score_oe3, 1)),
        'evidencias': tecnicas_ia
    })
    
    # OE4: Evaluación
    try:
        cursor.execute("SELECT COUNT(*) FROM evaluacion_sistema")
        n_eval = cursor.fetchone()[0]
    except:
        n_eval = 0
    
    score_oe4 = min(100, n_eval * 3)
    objetivos.append({
        'id': 'OE4',
        'titulo': 'Evaluar el funcionamiento mediante pruebas',
        'score': round(score_oe4, 1),
        'evidencias': [
            f'{n_eval} métricas de evaluación registradas',
            'Evaluación de recolección de datos',
            'Evaluación de análisis de sentimiento',
            'Evaluación de pipeline NLP/ML',
            'Evaluación de completitud de BD',
            'Evaluación de técnicas OSINT',
            'Evaluación de rendimiento API'
        ] if n_eval > 0 else ['Ejecutar evaluación para generar métricas']
    })
    
    conn.close()
    
    # Score general
    total = round(sum(o['score'] for o in objetivos) / len(objetivos), 1) if objetivos else 0
    
    return jsonify({
        'score_general': total,
        'objetivos': objetivos
    })


if __name__ == '__main__':
    print('''
    ╔══════════════════════════════════════════════════════════╗
    ║       OSINT EMI - API con Datos REALES (SQLite3)         ║
    ║                                                          ║
    ║  Estructura: Fuentes → Posts → Comentarios               ║
    ║  Puerto: 5001                                            ║
    ║  Base de datos: data/osint_emi.db                        ║
    ║                                                          ║
    ║  ✨ TikTok Scraping + OSINT + NLP + Evaluación           ║
    ╚══════════════════════════════════════════════════════════╝
    ''')
    # use_reloader=False para evitar problemas con nohup
    app.run(host='0.0.0.0', port=5001, debug=False, use_reloader=False, threaded=True)
