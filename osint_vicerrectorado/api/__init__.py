"""
API Flask - Sistema OSINT EMI
"""

from .ai_endpoints import create_app, ai_bp

__all__ = ['create_app', 'ai_bp']
