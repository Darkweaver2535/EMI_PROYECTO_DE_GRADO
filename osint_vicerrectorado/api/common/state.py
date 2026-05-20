"""
Shared state — Thread-safe globals used by multiple blueprints.
"""
import threading
from datetime import datetime

# ========================
# OSINT Execution Status
# ========================
OSINT_STATUS_LOCK = threading.Lock()
OSINT_EXECUTION_STATUS = {
    'running': False,
    'status': 'idle',
    'progress': 0,
    'current_step': 'Sin ejecución activa',
    'started_at': None,
    'finished_at': None,
    'message': None,
    'steps': []
}


def _osint_set_status(**kwargs):
    """Actualiza estado global OSINT en forma thread-safe."""
    step = kwargs.pop('step_message', None)
    with OSINT_STATUS_LOCK:
        OSINT_EXECUTION_STATUS.update(kwargs)
        if step:
            OSINT_EXECUTION_STATUS.setdefault('steps', []).append({
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'message': step
            })
            OSINT_EXECUTION_STATUS['steps'] = OSINT_EXECUTION_STATUS['steps'][-30:]


# ========================
# TikTok Scraping Sessions
# ========================
tiktok_scraping_sessions = {}


# ========================
# Utility helpers
# ========================
def _extract_deactivation_reason(detalle):
    """Normaliza el texto guardado en log para exponer solo el motivo."""
    if not detalle:
        return None
    prefix = 'Motivo: '
    if isinstance(detalle, str) and detalle.startswith(prefix):
        return detalle[len(prefix):].strip()
    return detalle
