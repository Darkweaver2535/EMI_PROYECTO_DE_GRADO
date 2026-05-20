"""
Flask App Factory — Sistema OSINT EMI
======================================

Creates and configures the Flask application with all blueprints.
This replaces the monolithic api_real.py.

Usage:
    from api.app import create_app
    app = create_app()
    app.run(host='0.0.0.0', port=5001)
"""
import os
import sys

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from flask_cors import CORS


def create_app() -> Flask:
    """
    Application factory.
    
    Returns:
        Configured Flask application with all blueprints registered.
    """
    app = Flask(__name__)
    CORS(app)
    
    # ---- Register Blueprints ----
    
    from api.auth.routes import bp as auth_bp
    app.register_blueprint(auth_bp)
    
    from api.users.routes import bp as users_bp
    app.register_blueprint(users_bp)
    
    from api.sentiment.routes import bp as sentiment_bp
    app.register_blueprint(sentiment_bp)
    
    from api.stats.routes import bp as stats_bp
    app.register_blueprint(stats_bp)
    
    from api.alerts.routes import bp as alerts_bp
    app.register_blueprint(alerts_bp)
    
    from api.benchmarking.routes import bp as benchmarking_bp
    app.register_blueprint(benchmarking_bp)
    
    from api.sources.routes import bp as sources_bp
    app.register_blueprint(sources_bp)
    
    from api.posts.routes import bp as posts_bp
    app.register_blueprint(posts_bp)
    
    from api.osint.routes import bp as osint_bp
    app.register_blueprint(osint_bp)
    
    from api.nlp.routes import bp as nlp_bp
    app.register_blueprint(nlp_bp)
    
    from api.evaluacion.routes import bp as evaluacion_bp
    app.register_blueprint(evaluacion_bp)
    
    return app


if __name__ == '__main__':
    app = create_app()
    
    print('''
    ╔══════════════════════════════════════════════════════════╗
    ║       OSINT EMI - API Modular (Flask Blueprints)         ║
    ║                                                          ║
    ║  Estructura: Fuentes → Posts → Comentarios               ║
    ║  Puerto: 5001                                            ║
    ║  Base de datos: data/osint_emi.db                        ║
    ║                                                          ║
    ║  ✨ Modularizado: 11 blueprints                          ║
    ╚══════════════════════════════════════════════════════════╝
    ''')
    
    # List registered routes
    rules = sorted(app.url_map.iter_rules(), key=lambda r: r.rule)
    print(f"  📋 {len(rules)} routes registered across {11} blueprints\n")
    
    app.run(host='0.0.0.0', port=5001, debug=False, use_reloader=False, threaded=True)
