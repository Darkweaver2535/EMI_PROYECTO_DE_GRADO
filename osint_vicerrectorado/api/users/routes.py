"""
User CRUD routes
Auto-extracted from api_real.py during modularization.
"""
import os
import json
import hashlib
import sqlite3
import threading
import logging
from datetime import datetime, timedelta
from collections import defaultdict
from flask import Blueprint, jsonify, request

from api.common.database import get_db
from api.common.filters import EXTERNAL_POSTS_FILTER, EXTERNAL_PROCESADOS_SUBQUERY
from api.common.auth import hash_password, get_active_tokens, get_current_user
from api.common.state import _extract_deactivation_reason

bp = Blueprint('users', __name__)

# ============== USUARIOS CRUD ==============
@bp.route('/api/usuarios')
def get_usuarios():
    """Lista todos los usuarios"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT
            u.id_usuario,
            u.username,
            u.email,
            u.nombre_completo,
            u.rol,
            u.cargo,
            u.activo,
            u.ultimo_login,
            u.fecha_creacion,
            u.permisos,
            (
                SELECT l.detalle
                FROM log_actividad l
                WHERE l.id_usuario = u.id_usuario
                AND l.accion = 'usuario_desactivado'
                ORDER BY l.fecha DESC
                LIMIT 1
            ) AS motivo_desactivacion,
            (
                SELECT l.fecha
                FROM log_actividad l
                WHERE l.id_usuario = u.id_usuario
                AND l.accion = 'usuario_desactivado'
                ORDER BY l.fecha DESC
                LIMIT 1
            ) AS fecha_desactivacion
        FROM usuario u
        ORDER BY u.id_usuario
    ''')
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
            'permisos': permisos,
            'motivo_desactivacion': _extract_deactivation_reason(row['motivo_desactivacion']),
            'fecha_desactivacion': row['fecha_desactivacion']
        })
    conn.close()
    return jsonify({'usuarios': users, 'total': len(users)})

@bp.route('/api/usuarios/<int:uid>')
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

@bp.route('/api/usuarios', methods=['POST'])
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

@bp.route('/api/usuarios/<int:uid>', methods=['PUT'])
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

@bp.route('/api/usuarios/<int:uid>', methods=['DELETE'])
def delete_usuario(uid):
    """Desactivar usuario (soft delete)"""
    data = request.get_json(silent=True) or {}
    motivo = (data.get('motivo') or '').strip()

    if not motivo:
        return jsonify({'error': 'El motivo de desactivación es obligatorio'}), 400

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('SELECT id_usuario FROM usuario WHERE id_usuario = ?', (uid,))
    if not cursor.fetchone():
        conn.close()
        return jsonify({'error': 'Usuario no encontrado'}), 404

    cursor.execute('UPDATE usuario SET activo = 0 WHERE id_usuario = ?', (uid,))
    cursor.execute(
        'INSERT INTO log_actividad (id_usuario, accion, detalle, ip_address) VALUES (?,?,?,?)',
        (uid, 'usuario_desactivado', f'Motivo: {motivo}', request.remote_addr)
    )
    conn.commit()
    conn.close()
    return jsonify({'message': 'Usuario desactivado', 'motivo': motivo})

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

@bp.route('/api/usuarios/roles')
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

@bp.route('/api/usuarios/roles/permisos-default/<rol>')
def get_role_default_permisos(rol):
    """Retorna los permisos por defecto de un rol"""
    if rol not in ('administrador', 'vicerrector', 'uebu'):
        return jsonify({'error': 'Rol inválido'}), 400
    return jsonify({'permisos': get_default_permisos(rol)})


