"""
Auth routes
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
# Permisos por defecto según rol (fuente única en users.routes)
from api.users.routes import get_default_permisos

bp = Blueprint('auth', __name__)

# ============== AUTH (DB-backed) ==============
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

@bp.route('/api/auth/login', methods=['POST'])
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

@bp.route('/api/auth/me')
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

@bp.route('/api/auth/logout', methods=['POST'])
def auth_logout():
    """Logout"""
    return jsonify({'message': 'Sesión cerrada'})

@bp.route('/api/auth/refresh', methods=['POST'])
def auth_refresh():
    """Refresh token"""
    data = request.json or {}
    refresh = data.get('refreshToken', '')
    if refresh:
        return jsonify({'accessToken': refresh.replace('refresh_', 'token_')})
    return jsonify({'error': 'Token inválido'}), 401

@bp.route('/api/auth/change-password', methods=['POST'])
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


