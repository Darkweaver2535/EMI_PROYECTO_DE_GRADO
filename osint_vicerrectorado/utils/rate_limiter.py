"""
RateLimiter - Control de límites de tasa de requests
Sistema de Analítica EMI

Proporciona control de rate limiting para evitar bloqueos:
- Límites por hora/minuto configurables
- Delays aleatorios entre requests
- Tracking de requests realizados
- Backoff exponencial en caso de errores

Autor: Sistema OSINT EMI
Fecha: Diciembre 2024
"""

import time
import random
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional, Callable, Any
from collections import deque
import logging


class RateLimiter:
    """
    Controlador de rate limiting para scrapers.
    
    Implementa un sistema de ventana deslizante para controlar
    la cantidad de requests en un período de tiempo.
    
    Attributes:
        requests_per_hour (int): Límite de requests por hora
        min_delay (float): Delay mínimo entre requests (segundos)
        max_delay (float): Delay máximo entre requests (segundos)
        request_times (deque): Cola de timestamps de requests
        logger (logging.Logger): Logger para registrar operaciones
    """
    
    def __init__(self, 
                 requests_per_hour: int = 60,
                 min_delay: float = 3.0,
                 max_delay: float = 7.0,
                 name: str = "default"):
        """
        Inicializa el rate limiter.
        
        Args:
            requests_per_hour: Máximo de requests permitidos por hora
            min_delay: Delay mínimo entre requests en segundos
            max_delay: Delay máximo entre requests en segundos
            name: Nombre identificador del limiter
        """
        self.name = name
        self.requests_per_hour = requests_per_hour
        self.min_delay = min_delay
        self.max_delay = max_delay
        
        # Cola para tracking de requests (ventana de 1 hora)
        self.request_times: deque = deque()
        
        # Último request realizado
        self.last_request_time: Optional[datetime] = None
        
        # Estadísticas
        self.total_requests = 0
        self.total_waits = 0
        self.total_wait_time = 0.0
        
        self.logger = logging.getLogger(f"OSINT.RateLimiter.{name}")
        self.logger.info(
            f"RateLimiter inicializado: {requests_per_hour} req/h, "
            f"delay {min_delay}-{max_delay}s"
        )
    
    def _clean_old_requests(self) -> None:
        """
        Elimina requests antiguos fuera de la ventana de tiempo.
        """
        cutoff = datetime.now() - timedelta(hours=1)
        
        while self.request_times and self.request_times[0] < cutoff:
            self.request_times.popleft()
    
    def can_make_request(self) -> bool:
        """
        Verifica si se puede hacer un request ahora.
        
        Returns:
            bool: True si está dentro del límite
        """
        self._clean_old_requests()
        return len(self.request_times) < self.requests_per_hour
    
    def get_wait_time(self) -> float:
        """
        Calcula el tiempo de espera necesario antes del próximo request.
        
        Returns:
            float: Segundos a esperar (0 si se puede hacer inmediatamente)
        """
        self._clean_old_requests()
        
        # Si no hemos alcanzado el límite, solo aplicar delay mínimo
        if len(self.request_times) < self.requests_per_hour:
            if self.last_request_time:
                elapsed = (datetime.now() - self.last_request_time).total_seconds()
                if elapsed < self.min_delay:
                    return self.min_delay - elapsed
            return 0.0
        
        # Si alcanzamos el límite, calcular cuándo expira el request más antiguo
        oldest = self.request_times[0]
        wait_until = oldest + timedelta(hours=1)
        wait_seconds = (wait_until - datetime.now()).total_seconds()
        
        return max(0, wait_seconds)
    
    def get_random_delay(self) -> float:
        """
        Genera un delay aleatorio dentro del rango configurado.
        
        Returns:
            float: Delay aleatorio en segundos
        """
        return random.uniform(self.min_delay, self.max_delay)
    
    def wait(self) -> float:
        """
        Espera el tiempo necesario antes de hacer un request (síncrono).
        
        Returns:
            float: Tiempo total esperado en segundos
        """
        wait_time = self.get_wait_time()
        
        if wait_time > 0:
            self.logger.debug(f"Rate limit: esperando {wait_time:.2f}s")
            time.sleep(wait_time)
            self.total_waits += 1
            self.total_wait_time += wait_time
        
        # Agregar delay aleatorio adicional para simular comportamiento humano
        random_delay = self.get_random_delay()
        time.sleep(random_delay)
        self.total_wait_time += random_delay
        
        return wait_time + random_delay
    
    async def wait_async(self) -> float:
        """
        Espera el tiempo necesario antes de hacer un request (asíncrono).
        
        Returns:
            float: Tiempo total esperado en segundos
        """
        wait_time = self.get_wait_time()
        
        if wait_time > 0:
            self.logger.debug(f"Rate limit: esperando {wait_time:.2f}s")
            await asyncio.sleep(wait_time)
            self.total_waits += 1
            self.total_wait_time += wait_time
        
        # Agregar delay aleatorio adicional
        random_delay = self.get_random_delay()
        await asyncio.sleep(random_delay)
        self.total_wait_time += random_delay
        
        return wait_time + random_delay
    
    def record_request(self) -> None:
        """
        Registra que se realizó un request.
        """
        now = datetime.now()
        self.request_times.append(now)
        self.last_request_time = now
        self.total_requests += 1
    
    def execute_with_limit(self, func: Callable, *args, **kwargs) -> Any:
        """
        Ejecuta una función respetando el rate limit (síncrono).
        
        Args:
            func: Función a ejecutar
            *args: Argumentos posicionales
            **kwargs: Argumentos de palabra clave
            
        Returns:
            Resultado de la función
        """
        self.wait()
        result = func(*args, **kwargs)
        self.record_request()
        return result
    
    async def execute_with_limit_async(self, func: Callable, *args, **kwargs) -> Any:
        """
        Ejecuta una función asíncrona respetando el rate limit.
        
        Args:
            func: Función asíncrona a ejecutar
            *args: Argumentos posicionales
            **kwargs: Argumentos de palabra clave
            
        Returns:
            Resultado de la función
        """
        await self.wait_async()
        result = await func(*args, **kwargs)
        self.record_request()
        return result
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del rate limiter.
        
        Returns:
            Dict: Estadísticas de uso
        """
        self._clean_old_requests()
        
        return {
            'name': self.name,
            'total_requests': self.total_requests,
            'requests_in_window': len(self.request_times),
            'requests_per_hour_limit': self.requests_per_hour,
            'requests_remaining': self.requests_per_hour - len(self.request_times),
            'total_waits': self.total_waits,
            'total_wait_time_seconds': round(self.total_wait_time, 2),
            'avg_wait_time': round(self.total_wait_time / max(1, self.total_requests), 2)
        }
    
    def reset(self) -> None:
        """
        Reinicia el rate limiter.
        """
        self.request_times.clear()
        self.last_request_time = None
        self.total_requests = 0
        self.total_waits = 0
        self.total_wait_time = 0.0
        self.logger.info("Rate limiter reiniciado")


class MultiRateLimiter:
    """
    Gestor de múltiples rate limiters para diferentes fuentes.
    
    Permite manejar límites diferentes para cada plataforma
    (ej: Facebook 60 req/h, TikTok 30 req/h).
    """
    
    def __init__(self):
        """Inicializa el gestor de rate limiters."""
        self.limiters: Dict[str, RateLimiter] = {}
        self.logger = logging.getLogger("OSINT.MultiRateLimiter")
    
    def add_limiter(self, name: str, 
                    requests_per_hour: int = 60,
                    min_delay: float = 3.0,
                    max_delay: float = 7.0) -> RateLimiter:
        """
        Agrega un nuevo rate limiter.
        
        Args:
            name: Nombre/identificador del limiter
            requests_per_hour: Límite de requests por hora
            min_delay: Delay mínimo entre requests
            max_delay: Delay máximo entre requests
            
        Returns:
            RateLimiter: El limiter creado
        """
        limiter = RateLimiter(
            requests_per_hour=requests_per_hour,
            min_delay=min_delay,
            max_delay=max_delay,
            name=name
        )
        self.limiters[name] = limiter
        return limiter
    
    def get_limiter(self, name: str) -> Optional[RateLimiter]:
        """
        Obtiene un rate limiter por nombre.
        
        Args:
            name: Nombre del limiter
            
        Returns:
            RateLimiter o None si no existe
        """
        return self.limiters.get(name)
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        Obtiene estadísticas de todos los rate limiters.
        
        Returns:
            Dict: Estadísticas por nombre de limiter
        """
        return {name: limiter.get_stats() for name, limiter in self.limiters.items()}
    
    def reset_all(self) -> None:
        """Reinicia todos los rate limiters."""
        for limiter in self.limiters.values():
            limiter.reset()


# Rate limiters predefinidos para las plataformas
def create_facebook_limiter() -> RateLimiter:
    """Crea un rate limiter optimizado para Facebook."""
    return RateLimiter(
        requests_per_hour=60,
        min_delay=3.0,
        max_delay=7.0,
        name="facebook"
    )


def create_tiktok_limiter() -> RateLimiter:
    """Crea un rate limiter optimizado para TikTok."""
    return RateLimiter(
        requests_per_hour=30,
        min_delay=5.0,
        max_delay=10.0,
        name="tiktok"
    )


if __name__ == "__main__":
    # Test del rate limiter
    logging.basicConfig(level=logging.INFO)
    
    print("=== Test de RateLimiter ===\n")
    
    limiter = RateLimiter(requests_per_hour=10, min_delay=0.5, max_delay=1.0, name="test")
    
    # Simular algunos requests
    for i in range(5):
        print(f"Request {i+1}:")
        print(f"  Puede hacer request: {limiter.can_make_request()}")
        print(f"  Tiempo de espera: {limiter.get_wait_time():.2f}s")
        
        waited = limiter.wait()
        limiter.record_request()
        print(f"  Esperó: {waited:.2f}s")
    
    print("\nEstadísticas:")
    stats = limiter.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
