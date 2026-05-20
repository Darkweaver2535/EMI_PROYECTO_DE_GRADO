"""
Auth utilities — Password hashing and token-based authentication.
"""
import hashlib
from functools import wraps
from flask import request, jsonify

from api.common.database import get_db


# In-memory token store (for current simple auth)
# In the future this should be replaced with JWT
_active_tokens: dict = {}


def hash_password(password: str) -> str:
    """Hash a password with SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()


def get_active_tokens() -> dict:
    """Returns the active tokens dict (mutable reference)."""
    return _active_tokens


def get_current_user():
    """
    Extracts the current user from the Authorization header.
    Returns the user dict or None.
    """
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        token = auth_header.split(' ', 1)[1]
        return _active_tokens.get(token)
    return None


def require_auth(f):
    """Decorator that requires a valid auth token."""
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({'error': 'No autorizado'}), 401
        return f(*args, **kwargs)
    return decorated


def require_role(*roles):
    """Decorator that requires specific roles."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user = get_current_user()
            if not user:
                return jsonify({'error': 'No autorizado'}), 401
            if user.get('rol') not in roles:
                return jsonify({'error': 'Permisos insuficientes'}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator
