"""
Exportador de Métricas Prometheus - Sistema OSINT EMI

Proporciona un endpoint HTTP para exponer métricas en formato Prometheus.
Puede ejecutarse como servidor standalone o integrarse con Flask.

Autor: Sistema OSINT EMI
Versión: 1.0.0
"""

import os
import threading
import time
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass
from http.server import HTTPServer, BaseHTTPRequestHandler
import json

# Intentar importar Flask
try:
    from flask import Flask, Response, Blueprint
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    Flask = None

# Importar métricas locales
from .metrics import (
    generate_metrics, get_content_type,
    PROMETHEUS_AVAILABLE, SCRAPER_REGISTRY,
    active_scrapers, scraper_health,
    MetricsRegistry
)


@dataclass
class ExporterConfig:
    """Configuración del exportador de métricas."""
    port: int = 9090
    host: str = "0.0.0.0"
    path: str = "/metrics"
    health_path: str = "/health"
    ready_path: str = "/ready"
    enable_default_metrics: bool = True
    
    @classmethod
    def from_env(cls) -> 'ExporterConfig':
        """Crea configuración desde variables de entorno."""
        return cls(
            port=int(os.getenv('METRICS_PORT', '9090')),
            host=os.getenv('METRICS_HOST', '0.0.0.0'),
            path=os.getenv('METRICS_PATH', '/metrics'),
            health_path=os.getenv('HEALTH_PATH', '/health'),
            ready_path=os.getenv('READY_PATH', '/ready'),
            enable_default_metrics=os.getenv('ENABLE_DEFAULT_METRICS', 'true').lower() == 'true'
        )


class MetricsHTTPHandler(BaseHTTPRequestHandler):
    """Handler HTTP para servir métricas Prometheus."""
    
    # Configuración compartida entre instancias
    config: ExporterConfig = ExporterConfig()
    health_checker: Optional[Callable[[], bool]] = None
    ready_checker: Optional[Callable[[], bool]] = None
    
    def log_message(self, format: str, *args):
        """Silencia logs por defecto."""
        pass
    
    def do_GET(self):
        """Maneja requests GET."""
        if self.path == self.config.path or self.path == f"{self.config.path}/":
            self._serve_metrics()
        elif self.path == self.config.health_path:
            self._serve_health()
        elif self.path == self.config.ready_path:
            self._serve_ready()
        else:
            self._serve_not_found()
    
    def _serve_metrics(self):
        """Sirve las métricas en formato Prometheus."""
        try:
            output = generate_metrics()
            self.send_response(200)
            self.send_header('Content-Type', get_content_type())
            self.send_header('Content-Length', len(output))
            self.end_headers()
            self.wfile.write(output)
        except Exception as e:
            self._serve_error(str(e))
    
    def _serve_health(self):
        """Sirve el endpoint de health check."""
        is_healthy = True
        
        if self.health_checker:
            try:
                is_healthy = self.health_checker()
            except Exception:
                is_healthy = False
        
        status = 200 if is_healthy else 503
        body = json.dumps({
            "status": "healthy" if is_healthy else "unhealthy",
            "timestamp": time.time()
        }).encode()
        
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)
    
    def _serve_ready(self):
        """Sirve el endpoint de readiness check."""
        is_ready = True
        
        if self.ready_checker:
            try:
                is_ready = self.ready_checker()
            except Exception:
                is_ready = False
        
        status = 200 if is_ready else 503
        body = json.dumps({
            "status": "ready" if is_ready else "not_ready",
            "timestamp": time.time()
        }).encode()
        
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)
    
    def _serve_not_found(self):
        """Sirve un 404."""
        body = json.dumps({
            "error": "Not Found",
            "available_endpoints": [
                self.config.path,
                self.config.health_path,
                self.config.ready_path
            ]
        }).encode()
        
        self.send_response(404)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)
    
    def _serve_error(self, message: str):
        """Sirve un error 500."""
        body = json.dumps({
            "error": "Internal Server Error",
            "message": message
        }).encode()
        
        self.send_response(500)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)


class PrometheusExporter:
    """
    Exportador de métricas Prometheus.
    
    Puede ejecutarse como servidor HTTP standalone o integrarse con Flask.
    
    Ejemplo standalone:
        exporter = PrometheusExporter()
        exporter.start()  # Inicia en background
        
        # O en foreground
        exporter.run_forever()
    
    Ejemplo con Flask:
        app = Flask(__name__)
        exporter = PrometheusExporter()
        exporter.register_flask(app)
    """
    
    def __init__(
        self,
        config: Optional[ExporterConfig] = None,
        health_checker: Optional[Callable[[], bool]] = None,
        ready_checker: Optional[Callable[[], bool]] = None
    ):
        self.config = config or ExporterConfig.from_env()
        self.health_checker = health_checker
        self.ready_checker = ready_checker
        
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        
        # Inicializar registro de métricas
        MetricsRegistry().initialize()
    
    def start(self) -> 'PrometheusExporter':
        """
        Inicia el servidor de métricas en un thread de background.
        
        Returns:
            self para encadenamiento
        """
        if self._running:
            return self
        
        # Configurar el handler
        MetricsHTTPHandler.config = self.config
        MetricsHTTPHandler.health_checker = self.health_checker
        MetricsHTTPHandler.ready_checker = self.ready_checker
        
        # Crear servidor
        self._server = HTTPServer(
            (self.config.host, self.config.port),
            MetricsHTTPHandler
        )
        
        # Iniciar thread
        self._thread = threading.Thread(
            target=self._serve_forever,
            daemon=True,
            name="prometheus-exporter"
        )
        self._running = True
        self._thread.start()
        
        print(f"📊 Prometheus metrics server started at http://{self.config.host}:{self.config.port}{self.config.path}")
        
        return self
    
    def _serve_forever(self):
        """Ejecuta el servidor hasta que se detenga."""
        try:
            self._server.serve_forever()
        except Exception as e:
            print(f"Metrics server error: {e}")
        finally:
            self._running = False
    
    def stop(self):
        """Detiene el servidor de métricas."""
        if self._server:
            self._server.shutdown()
            self._running = False
            if self._thread:
                self._thread.join(timeout=5)
            print("📊 Prometheus metrics server stopped")
    
    def run_forever(self):
        """Ejecuta el servidor en foreground (bloquea)."""
        self.start()
        try:
            while self._running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()
    
    def is_running(self) -> bool:
        """Verifica si el servidor está corriendo."""
        return self._running
    
    def get_url(self) -> str:
        """Obtiene la URL del servidor de métricas."""
        return f"http://{self.config.host}:{self.config.port}{self.config.path}"
    
    def register_flask(self, app: 'Flask') -> 'PrometheusExporter':
        """
        Registra endpoints de métricas en una aplicación Flask.
        
        Args:
            app: Aplicación Flask
            
        Returns:
            self para encadenamiento
        """
        if not FLASK_AVAILABLE:
            raise RuntimeError("Flask is not installed")
        
        @app.route(self.config.path)
        def metrics():
            return Response(
                generate_metrics(),
                mimetype=get_content_type()
            )
        
        @app.route(self.config.health_path)
        def health():
            is_healthy = True
            if self.health_checker:
                try:
                    is_healthy = self.health_checker()
                except Exception:
                    is_healthy = False
            
            return {
                "status": "healthy" if is_healthy else "unhealthy",
                "timestamp": time.time()
            }, 200 if is_healthy else 503
        
        @app.route(self.config.ready_path)
        def ready():
            is_ready = True
            if self.ready_checker:
                try:
                    is_ready = self.ready_checker()
                except Exception:
                    is_ready = False
            
            return {
                "status": "ready" if is_ready else "not_ready",
                "timestamp": time.time()
            }, 200 if is_ready else 503
        
        return self


def create_metrics_blueprint(
    config: Optional[ExporterConfig] = None,
    health_checker: Optional[Callable[[], bool]] = None,
    ready_checker: Optional[Callable[[], bool]] = None
) -> 'Blueprint':
    """
    Crea un Blueprint de Flask con los endpoints de métricas.
    
    Args:
        config: Configuración del exportador
        health_checker: Función para verificar health
        ready_checker: Función para verificar readiness
        
    Returns:
        Blueprint de Flask
    """
    if not FLASK_AVAILABLE:
        raise RuntimeError("Flask is not installed")
    
    config = config or ExporterConfig()
    bp = Blueprint('metrics', __name__)
    
    @bp.route(config.path)
    def metrics():
        return Response(
            generate_metrics(),
            mimetype=get_content_type()
        )
    
    @bp.route(config.health_path)
    def health():
        is_healthy = True
        if health_checker:
            try:
                is_healthy = health_checker()
            except Exception:
                is_healthy = False
        
        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "timestamp": time.time()
        }, 200 if is_healthy else 503
    
    @bp.route(config.ready_path)
    def ready():
        is_ready = True
        if ready_checker:
            try:
                is_ready = ready_checker()
            except Exception:
                is_ready = False
        
        return {
            "status": "ready" if is_ready else "not_ready",
            "timestamp": time.time()
        }, 200 if is_ready else 503
    
    return bp


def create_metrics_app(
    config: Optional[ExporterConfig] = None,
    health_checker: Optional[Callable[[], bool]] = None,
    ready_checker: Optional[Callable[[], bool]] = None
) -> 'Flask':
    """
    Crea una aplicación Flask dedicada para métricas.
    
    Args:
        config: Configuración del exportador
        health_checker: Función para verificar health
        ready_checker: Función para verificar readiness
        
    Returns:
        Aplicación Flask
    """
    if not FLASK_AVAILABLE:
        raise RuntimeError("Flask is not installed")
    
    config = config or ExporterConfig()
    app = Flask('metrics')
    
    exporter = PrometheusExporter(config, health_checker, ready_checker)
    exporter.register_flask(app)
    
    return app


def start_metrics_server(
    port: int = 9090,
    host: str = "0.0.0.0",
    health_checker: Optional[Callable[[], bool]] = None,
    ready_checker: Optional[Callable[[], bool]] = None
) -> PrometheusExporter:
    """
    Función de conveniencia para iniciar un servidor de métricas.
    
    Args:
        port: Puerto donde escuchar
        host: Host donde escuchar
        health_checker: Función para verificar health
        ready_checker: Función para verificar readiness
        
    Returns:
        PrometheusExporter iniciado
    """
    config = ExporterConfig(port=port, host=host)
    exporter = PrometheusExporter(config, health_checker, ready_checker)
    return exporter.start()


# =============================================================================
# INTEGRACIÓN CON GUNICORN
# =============================================================================

def gunicorn_child_exit(server, worker):
    """
    Hook para Gunicorn - maneja la salida de workers.
    
    Uso en gunicorn.conf.py:
        from monitoring.prometheus_exporter import gunicorn_child_exit
        child_exit = gunicorn_child_exit
    """
    if PROMETHEUS_AVAILABLE:
        from prometheus_client import multiprocess
        multiprocess.mark_process_dead(worker.pid)


def setup_multiprocess_dir():
    """
    Configura el directorio para métricas multiprocess de Prometheus.
    
    Debe llamarse antes de importar prometheus_client en entornos multiprocess.
    """
    import tempfile
    
    prometheus_dir = os.getenv('PROMETHEUS_MULTIPROC_DIR')
    if not prometheus_dir:
        prometheus_dir = tempfile.mkdtemp(prefix='prometheus_multiproc_')
        os.environ['PROMETHEUS_MULTIPROC_DIR'] = prometheus_dir
    
    # Limpiar archivos viejos
    if os.path.exists(prometheus_dir):
        for f in os.listdir(prometheus_dir):
            try:
                os.unlink(os.path.join(prometheus_dir, f))
            except Exception:
                pass
    
    return prometheus_dir


# =============================================================================
# CLI
# =============================================================================

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Prometheus Metrics Exporter')
    parser.add_argument('--port', type=int, default=9090, help='Port to listen on')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Host to bind to')
    
    args = parser.parse_args()
    
    print(f"Starting Prometheus metrics exporter on {args.host}:{args.port}")
    
    exporter = PrometheusExporter(
        ExporterConfig(port=args.port, host=args.host)
    )
    exporter.run_forever()
