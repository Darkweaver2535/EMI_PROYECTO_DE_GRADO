"""
Scraper Orchestrator - Sistema OSINT EMI

Orquestador para ejecución concurrente de múltiples scrapers.

Características:
- Ejecución concurrente con asyncio
- Integración con Circuit Breaker, Rate Limiter, Retry
- Métricas Prometheus por scraper
- Logging estructurado
- Recuperación automática de errores

Autor: Sistema OSINT EMI
Versión: 1.0.0
"""

import os
import asyncio
import time
from typing import Dict, Any, Optional, List, Callable, Awaitable, Type, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import yaml
import json

# Importar módulos internos
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from resilience import (
        ScraperCircuitBreaker, CircuitBreakerConfig,
        RetryManager, RetryConfig,
        AdaptiveRateLimiter, RateLimitConfig,
        TimeoutManager, TimeoutConfig
    )
    RESILIENCE_AVAILABLE = True
except ImportError:
    RESILIENCE_AVAILABLE = False

try:
    from monitoring import (
        ScraperMetrics, MetricsRegistry,
        ScraperLogger, get_logger, setup_logging
    )
    MONITORING_AVAILABLE = True
except ImportError:
    MONITORING_AVAILABLE = False
    # Mock básico para cuando monitoring no está disponible
    class ScraperMetrics:
        def __init__(self, *args, **kwargs): pass
        def record_success(self): pass
        def record_error(self, *args, **kwargs): pass
        def set_circuit_breaker_state(self, *args): pass
        def record_items_scraped(self, *args, **kwargs): pass
        def record_run(self): pass
    
    def get_logger(name, source):
        import logging
        return logging.getLogger(f"{name}.{source}")


# =============================================================================
# CONFIGURACIÓN
# =============================================================================

class ScraperState(Enum):
    """Estados posibles de un scraper."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    CIRCUIT_OPEN = "circuit_open"
    RATE_LIMITED = "rate_limited"


@dataclass
class OrchestratorConfig:
    """Configuración del orquestador."""
    max_concurrent_scrapers: int = 5
    default_interval_seconds: int = 300  # 5 minutos
    shutdown_timeout: int = 30
    health_check_interval: int = 60
    enable_circuit_breaker: bool = True
    enable_rate_limiter: bool = True
    enable_retry: bool = True
    enable_metrics: bool = True
    config_file: Optional[str] = None
    
    @classmethod
    def from_env(cls) -> 'OrchestratorConfig':
        """Crea configuración desde variables de entorno."""
        return cls(
            max_concurrent_scrapers=int(os.getenv('MAX_CONCURRENT_SCRAPERS', '5')),
            default_interval_seconds=int(os.getenv('DEFAULT_SCRAPE_INTERVAL', '300')),
            shutdown_timeout=int(os.getenv('SHUTDOWN_TIMEOUT', '30')),
            health_check_interval=int(os.getenv('HEALTH_CHECK_INTERVAL', '60')),
            enable_circuit_breaker=os.getenv('ENABLE_CIRCUIT_BREAKER', 'true').lower() == 'true',
            enable_rate_limiter=os.getenv('ENABLE_RATE_LIMITER', 'true').lower() == 'true',
            enable_retry=os.getenv('ENABLE_RETRY', 'true').lower() == 'true',
            enable_metrics=os.getenv('ENABLE_METRICS', 'true').lower() == 'true',
            config_file=os.getenv('SCRAPER_CONFIG_FILE'),
        )


@dataclass
class ScraperConfig:
    """Configuración individual de un scraper."""
    name: str
    source: str
    enabled: bool = True
    interval_seconds: int = 300
    priority: int = 5  # 1-10, mayor = más prioritario
    max_items_per_run: int = 100
    
    # Configuración de resiliencia
    circuit_breaker: Optional[CircuitBreakerConfig] = None
    rate_limiter: Optional[RateLimitConfig] = None
    retry: Optional[RetryConfig] = None
    timeout: Optional[TimeoutConfig] = None
    
    # Configuración específica del scraper
    extra_config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ScraperTask:
    """Representa una tarea de scraping."""
    scraper_name: str
    source: str
    config: ScraperConfig
    scraper_callable: Callable[..., Awaitable[Any]]
    state: ScraperState = ScraperState.IDLE
    last_run: Optional[datetime] = None
    last_success: Optional[datetime] = None
    consecutive_failures: int = 0
    total_runs: int = 0
    total_items: int = 0


@dataclass
class ScraperResult:
    """Resultado de una ejecución de scraper."""
    scraper_name: str
    source: str
    success: bool
    items_count: int = 0
    duration_seconds: float = 0.0
    error: Optional[str] = None
    error_type: Optional[str] = None
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OrchestratorStats:
    """Estadísticas del orquestador."""
    total_runs: int = 0
    successful_runs: int = 0
    failed_runs: int = 0
    total_items_scraped: int = 0
    active_scrapers: int = 0
    paused_scrapers: int = 0
    circuit_open_scrapers: int = 0
    uptime_seconds: float = 0.0
    started_at: Optional[datetime] = None


# =============================================================================
# ORQUESTADOR PRINCIPAL
# =============================================================================

class ScraperOrchestrator:
    """
    Orquestador para ejecución concurrente de scrapers.
    
    Gestiona múltiples scrapers con:
    - Ejecución concurrente limitada
    - Circuit breakers individuales
    - Rate limiting adaptativo
    - Reintentos con backoff
    - Métricas Prometheus
    - Logging estructurado
    
    Ejemplo:
        orchestrator = ScraperOrchestrator()
        
        # Registrar scrapers
        orchestrator.register_scraper(
            name="facebook",
            source="facebook.com",
            scraper_callable=facebook_scraper.scrape,
            config=ScraperConfig(...)
        )
        
        # Ejecutar una vez
        results = await orchestrator.run_all()
        
        # O ejecutar continuamente
        await orchestrator.start()
    """
    
    def __init__(self, config: Optional[OrchestratorConfig] = None):
        self.config = config or OrchestratorConfig.from_env()
        
        # Estado interno
        self._tasks: Dict[str, ScraperTask] = {}
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._running = False
        self._shutdown_event: Optional[asyncio.Event] = None
        self._stats = OrchestratorStats()
        
        # Componentes de resiliencia
        self._circuit_breakers: Dict[str, ScraperCircuitBreaker] = {}
        self._rate_limiters: Dict[str, AdaptiveRateLimiter] = {}
        self._retry_managers: Dict[str, RetryManager] = {}
        self._timeout_managers: Dict[str, TimeoutManager] = {}
        
        # Métricas y logging
        self._metrics: Dict[str, ScraperMetrics] = {}
        self._loggers: Dict[str, Any] = {}
        
        # Cargar configuración de archivo si existe
        if self.config.config_file:
            self._load_config_file()
    
    def _load_config_file(self):
        """Carga configuración desde archivo YAML."""
        if not self.config.config_file or not os.path.exists(self.config.config_file):
            return
        
        with open(self.config.config_file, 'r') as f:
            config_data = yaml.safe_load(f)
        
        # Procesar configuración global
        if 'orchestrator' in config_data:
            orch_config = config_data['orchestrator']
            self.config.max_concurrent_scrapers = orch_config.get(
                'max_concurrent_scrapers', 
                self.config.max_concurrent_scrapers
            )
            self.config.default_interval_seconds = orch_config.get(
                'default_interval_seconds',
                self.config.default_interval_seconds
            )
    
    def _get_logger(self, scraper_name: str, source: str):
        """Obtiene o crea un logger para un scraper."""
        key = f"{scraper_name}:{source}"
        if key not in self._loggers:
            if MONITORING_AVAILABLE:
                self._loggers[key] = get_logger(scraper_name, source)
            else:
                import logging
                self._loggers[key] = logging.getLogger(f"scraper.{scraper_name}")
        return self._loggers[key]
    
    def _get_metrics(self, scraper_name: str, source: str) -> ScraperMetrics:
        """Obtiene o crea métricas para un scraper."""
        key = f"{scraper_name}:{source}"
        if key not in self._metrics:
            if MONITORING_AVAILABLE:
                self._metrics[key] = MetricsRegistry().get_or_create(scraper_name, source)
            else:
                self._metrics[key] = ScraperMetrics(scraper_name, source)
        return self._metrics[key]
    
    def _setup_resilience(self, task: ScraperTask):
        """Configura componentes de resiliencia para una tarea."""
        key = f"{task.scraper_name}:{task.source}"
        
        if not RESILIENCE_AVAILABLE:
            return
        
        # Circuit Breaker
        if self.config.enable_circuit_breaker:
            cb_config = task.config.circuit_breaker or CircuitBreakerConfig(
                failure_threshold=5,
                timeout_duration=300,
                expected_exceptions=(Exception,)
            )
            self._circuit_breakers[key] = ScraperCircuitBreaker(
                name=task.scraper_name,
                source=task.source,
                config=cb_config
            )
        
        # Rate Limiter
        if self.config.enable_rate_limiter:
            rl_config = task.config.rate_limiter or RateLimitConfig(
                requests_per_minute=60,
                adaptive=True
            )
            self._rate_limiters[key] = AdaptiveRateLimiter(
                name=task.scraper_name,
                source=task.source,
                config=rl_config
            )
        
        # Retry Manager
        if self.config.enable_retry:
            retry_config = task.config.retry or RetryConfig(
                max_attempts=3,
                initial_delay=1.0,
                max_delay=60.0
            )
            self._retry_managers[key] = RetryManager(
                name=task.scraper_name,
                source=task.source,
                config=retry_config
            )
        
        # Timeout Manager
        timeout_config = task.config.timeout or TimeoutConfig(
            connect_timeout=10.0,
            read_timeout=30.0,
            total_timeout=60.0
        )
        self._timeout_managers[key] = TimeoutManager(
            name=task.scraper_name,
            source=task.source,
            config=timeout_config
        )
    
    # =========================================================================
    # GESTIÓN DE SCRAPERS
    # =========================================================================
    
    def register_scraper(
        self,
        name: str,
        source: str,
        scraper_callable: Callable[..., Awaitable[Any]],
        config: Optional[ScraperConfig] = None
    ) -> 'ScraperOrchestrator':
        """
        Registra un scraper para ser ejecutado.
        
        Args:
            name: Nombre único del scraper
            source: URL/dominio de la fuente
            scraper_callable: Función async que ejecuta el scrape
            config: Configuración opcional
            
        Returns:
            self para encadenamiento
        """
        if config is None:
            config = ScraperConfig(
                name=name,
                source=source,
                interval_seconds=self.config.default_interval_seconds
            )
        
        task = ScraperTask(
            scraper_name=name,
            source=source,
            config=config,
            scraper_callable=scraper_callable
        )
        
        key = f"{name}:{source}"
        self._tasks[key] = task
        
        # Configurar resiliencia
        self._setup_resilience(task)
        
        logger = self._get_logger(name, source)
        if hasattr(logger, 'info'):
            logger.info(f"Scraper registered: {name} for {source}")
        
        return self
    
    def unregister_scraper(self, name: str, source: str) -> bool:
        """Elimina un scraper registrado."""
        key = f"{name}:{source}"
        
        if key in self._tasks:
            del self._tasks[key]
            
            # Limpiar componentes asociados
            self._circuit_breakers.pop(key, None)
            self._rate_limiters.pop(key, None)
            self._retry_managers.pop(key, None)
            self._timeout_managers.pop(key, None)
            self._metrics.pop(key, None)
            self._loggers.pop(key, None)
            
            return True
        return False
    
    def get_scraper(self, name: str, source: str) -> Optional[ScraperTask]:
        """Obtiene una tarea de scraper."""
        return self._tasks.get(f"{name}:{source}")
    
    def list_scrapers(self) -> List[ScraperTask]:
        """Lista todos los scrapers registrados."""
        return list(self._tasks.values())
    
    def pause_scraper(self, name: str, source: str) -> bool:
        """Pausa un scraper."""
        task = self.get_scraper(name, source)
        if task and task.state not in (ScraperState.PAUSED, ScraperState.RUNNING):
            task.state = ScraperState.PAUSED
            return True
        return False
    
    def resume_scraper(self, name: str, source: str) -> bool:
        """Reanuda un scraper pausado."""
        task = self.get_scraper(name, source)
        if task and task.state == ScraperState.PAUSED:
            task.state = ScraperState.IDLE
            return True
        return False
    
    # =========================================================================
    # EJECUCIÓN DE SCRAPERS
    # =========================================================================
    
    async def _execute_scraper(self, task: ScraperTask) -> ScraperResult:
        """Ejecuta un scraper individual con resiliencia."""
        key = f"{task.scraper_name}:{task.source}"
        logger = self._get_logger(task.scraper_name, task.source)
        metrics = self._get_metrics(task.scraper_name, task.source)
        
        result = ScraperResult(
            scraper_name=task.scraper_name,
            source=task.source,
            success=False,
            started_at=datetime.utcnow()
        )
        
        start_time = time.time()
        task.state = ScraperState.RUNNING
        task.total_runs += 1
        task.last_run = datetime.utcnow()
        metrics.record_run()
        
        if hasattr(logger, 'scrape_started'):
            logger.scrape_started()
        
        try:
            # Verificar circuit breaker
            circuit_breaker = self._circuit_breakers.get(key)
            if circuit_breaker and circuit_breaker.is_open:
                task.state = ScraperState.CIRCUIT_OPEN
                metrics.set_circuit_breaker_state("open")
                raise Exception(f"Circuit breaker is open for {task.scraper_name}")
            
            # Adquirir rate limit
            rate_limiter = self._rate_limiters.get(key)
            if rate_limiter:
                await rate_limiter.acquire_async()
            
            # Ejecutar scraper con timeout
            timeout_manager = self._timeout_managers.get(key)
            retry_manager = self._retry_managers.get(key)
            
            async def execute():
                if timeout_manager:
                    async with timeout_manager.timeout_context():
                        return await task.scraper_callable(**task.config.extra_config)
                else:
                    return await task.scraper_callable(**task.config.extra_config)
            
            # Con retry si está habilitado
            if retry_manager:
                scrape_result = await retry_manager.execute_with_retry(execute)
            else:
                scrape_result = await execute()
            
            # Procesar resultado
            items_count = 0
            if isinstance(scrape_result, dict):
                items_count = scrape_result.get('items_count', 0)
                result.metadata = scrape_result
            elif isinstance(scrape_result, (list, tuple)):
                items_count = len(scrape_result)
            elif isinstance(scrape_result, int):
                items_count = scrape_result
            
            result.success = True
            result.items_count = items_count
            task.total_items += items_count
            task.consecutive_failures = 0
            task.last_success = datetime.utcnow()
            task.state = ScraperState.IDLE
            
            # Registrar éxito en circuit breaker
            if circuit_breaker:
                circuit_breaker._record_success()
                metrics.set_circuit_breaker_state("closed")
            
            metrics.record_success()
            metrics.record_items_scraped(items_count, "item")
            
            if hasattr(logger, 'scrape_completed'):
                logger.scrape_completed(success=True, items_count=items_count)
            
        except asyncio.TimeoutError as e:
            result.error = "Timeout"
            result.error_type = "TimeoutError"
            task.consecutive_failures += 1
            task.state = ScraperState.ERROR
            
            if hasattr(logger, 'timeout_occurred'):
                logger.timeout_occurred("scrape", 60.0)
            metrics.record_error("timeout", recoverable=True)
            
        except Exception as e:
            result.error = str(e)
            result.error_type = type(e).__name__
            task.consecutive_failures += 1
            task.state = ScraperState.ERROR
            
            # Registrar falla en circuit breaker
            circuit_breaker = self._circuit_breakers.get(key)
            if circuit_breaker:
                circuit_breaker._record_failure()
                if circuit_breaker.is_open:
                    task.state = ScraperState.CIRCUIT_OPEN
                    metrics.set_circuit_breaker_state("open")
            
            if hasattr(logger, 'error'):
                logger.error(f"Scrape failed: {e}", exc_info=True)
            metrics.record_error(result.error_type, recoverable=True)
            
            if hasattr(logger, 'scrape_completed'):
                logger.scrape_completed(success=False, items_count=0)
        
        finally:
            result.duration_seconds = time.time() - start_time
            result.completed_at = datetime.utcnow()
            
            # Actualizar estadísticas globales
            self._stats.total_runs += 1
            if result.success:
                self._stats.successful_runs += 1
                self._stats.total_items_scraped += result.items_count
            else:
                self._stats.failed_runs += 1
        
        return result
    
    async def run_scraper(self, name: str, source: str) -> Optional[ScraperResult]:
        """Ejecuta un scraper específico."""
        task = self.get_scraper(name, source)
        if not task:
            return None
        
        if task.state == ScraperState.PAUSED:
            return ScraperResult(
                scraper_name=name,
                source=source,
                success=False,
                error="Scraper is paused"
            )
        
        return await self._execute_scraper(task)
    
    async def run_all(
        self,
        filter_func: Optional[Callable[[ScraperTask], bool]] = None
    ) -> List[ScraperResult]:
        """
        Ejecuta todos los scrapers registrados concurrentemente.
        
        Args:
            filter_func: Función opcional para filtrar qué scrapers ejecutar
            
        Returns:
            Lista de resultados
        """
        # Inicializar semáforo si no existe
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.config.max_concurrent_scrapers)
        
        # Filtrar tareas activas
        tasks = [
            task for task in self._tasks.values()
            if task.config.enabled 
            and task.state not in (ScraperState.PAUSED, ScraperState.RUNNING)
            and (filter_func is None or filter_func(task))
        ]
        
        # Ordenar por prioridad
        tasks.sort(key=lambda t: t.config.priority, reverse=True)
        
        # Ejecutar concurrentemente con límite
        async def run_with_semaphore(task: ScraperTask) -> ScraperResult:
            async with self._semaphore:
                return await self._execute_scraper(task)
        
        results = await asyncio.gather(
            *[run_with_semaphore(task) for task in tasks],
            return_exceptions=True
        )
        
        # Procesar excepciones
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(ScraperResult(
                    scraper_name=tasks[i].scraper_name,
                    source=tasks[i].source,
                    success=False,
                    error=str(result),
                    error_type=type(result).__name__
                ))
            else:
                processed_results.append(result)
        
        return processed_results
    
    # =========================================================================
    # EJECUCIÓN CONTINUA
    # =========================================================================
    
    async def start(self):
        """
        Inicia el orquestador en modo continuo.
        
        Ejecuta scrapers según sus intervalos configurados.
        """
        if self._running:
            return
        
        self._running = True
        self._shutdown_event = asyncio.Event()
        self._stats.started_at = datetime.utcnow()
        
        logger = self._get_logger("orchestrator", "system")
        if hasattr(logger, 'info'):
            logger.info("Orchestrator started")
        
        # Crear tareas de ejecución para cada scraper
        scheduler_tasks = []
        for task in self._tasks.values():
            if task.config.enabled:
                scheduler_tasks.append(
                    asyncio.create_task(
                        self._scheduler_loop(task),
                        name=f"scheduler_{task.scraper_name}"
                    )
                )
        
        # Tarea de health check
        health_task = asyncio.create_task(
            self._health_check_loop(),
            name="health_check"
        )
        scheduler_tasks.append(health_task)
        
        try:
            # Esperar shutdown
            await self._shutdown_event.wait()
        finally:
            # Cancelar todas las tareas
            for task in scheduler_tasks:
                task.cancel()
            
            await asyncio.gather(*scheduler_tasks, return_exceptions=True)
            self._running = False
            
            if hasattr(logger, 'info'):
                logger.info("Orchestrator stopped")
    
    async def _scheduler_loop(self, task: ScraperTask):
        """Loop de scheduling para un scraper."""
        while self._running and not self._shutdown_event.is_set():
            try:
                # Verificar si debe ejecutarse
                if task.state == ScraperState.PAUSED:
                    await asyncio.sleep(10)
                    continue
                
                if task.state == ScraperState.CIRCUIT_OPEN:
                    # Esperar timeout del circuit breaker
                    await asyncio.sleep(30)
                    
                    # Verificar si el circuit breaker se ha cerrado
                    key = f"{task.scraper_name}:{task.source}"
                    cb = self._circuit_breakers.get(key)
                    if cb and cb.is_open:
                        continue
                    task.state = ScraperState.IDLE
                
                # Verificar intervalo
                if task.last_run:
                    elapsed = (datetime.utcnow() - task.last_run).total_seconds()
                    if elapsed < task.config.interval_seconds:
                        await asyncio.sleep(min(10, task.config.interval_seconds - elapsed))
                        continue
                
                # Ejecutar scraper
                await self._execute_scraper(task)
                
                # Esperar intervalo
                await asyncio.sleep(task.config.interval_seconds)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger = self._get_logger(task.scraper_name, task.source)
                if hasattr(logger, 'error'):
                    logger.error(f"Scheduler error: {e}", exc_info=True)
                await asyncio.sleep(60)  # Esperar antes de reintentar
    
    async def _health_check_loop(self):
        """Loop de health check del orquestador."""
        while self._running and not self._shutdown_event.is_set():
            try:
                await asyncio.sleep(self.config.health_check_interval)
                
                # Actualizar estadísticas
                self._stats.uptime_seconds = (
                    datetime.utcnow() - self._stats.started_at
                ).total_seconds() if self._stats.started_at else 0
                
                # Contar estados
                self._stats.active_scrapers = sum(
                    1 for t in self._tasks.values() 
                    if t.state == ScraperState.RUNNING
                )
                self._stats.paused_scrapers = sum(
                    1 for t in self._tasks.values() 
                    if t.state == ScraperState.PAUSED
                )
                self._stats.circuit_open_scrapers = sum(
                    1 for t in self._tasks.values() 
                    if t.state == ScraperState.CIRCUIT_OPEN
                )
                
                # Actualizar métricas globales
                if MONITORING_AVAILABLE:
                    MetricsRegistry().set_active_scrapers(self._stats.active_scrapers)
                
            except asyncio.CancelledError:
                break
            except Exception:
                pass
    
    async def stop(self):
        """Detiene el orquestador."""
        if self._shutdown_event:
            self._shutdown_event.set()
        
        # Esperar a que terminen las tareas en ejecución
        await asyncio.sleep(1)
    
    # =========================================================================
    # ESTADÍSTICAS Y ESTADO
    # =========================================================================
    
    def get_stats(self) -> OrchestratorStats:
        """Obtiene estadísticas del orquestador."""
        return self._stats
    
    def get_scraper_status(self, name: str, source: str) -> Optional[Dict[str, Any]]:
        """Obtiene el estado detallado de un scraper."""
        task = self.get_scraper(name, source)
        if not task:
            return None
        
        key = f"{name}:{source}"
        cb = self._circuit_breakers.get(key)
        rl = self._rate_limiters.get(key)
        
        return {
            "name": task.scraper_name,
            "source": task.source,
            "state": task.state.value,
            "enabled": task.config.enabled,
            "last_run": task.last_run.isoformat() if task.last_run else None,
            "last_success": task.last_success.isoformat() if task.last_success else None,
            "consecutive_failures": task.consecutive_failures,
            "total_runs": task.total_runs,
            "total_items": task.total_items,
            "circuit_breaker": {
                "state": cb.get_stats()['state'] if cb else "disabled",
            } if cb else None,
            "rate_limiter": {
                "current_rate": rl.get_stats().current_rpm if rl else None,
            } if rl else None,
        }
    
    def get_all_status(self) -> Dict[str, Any]:
        """Obtiene el estado de todos los scrapers."""
        return {
            "orchestrator": {
                "running": self._running,
                "max_concurrent": self.config.max_concurrent_scrapers,
                "stats": {
                    "total_runs": self._stats.total_runs,
                    "successful_runs": self._stats.successful_runs,
                    "failed_runs": self._stats.failed_runs,
                    "success_rate": (
                        self._stats.successful_runs / self._stats.total_runs * 100
                        if self._stats.total_runs > 0 else 0
                    ),
                    "total_items": self._stats.total_items_scraped,
                    "uptime_seconds": self._stats.uptime_seconds,
                }
            },
            "scrapers": [
                self.get_scraper_status(task.scraper_name, task.source)
                for task in self._tasks.values()
            ]
        }
    
    def is_healthy(self) -> bool:
        """Verifica si el orquestador está saludable."""
        # Verificar que no haya demasiados circuit breakers abiertos
        open_circuits = sum(
            1 for cb in self._circuit_breakers.values() if cb.is_open
        )
        total_scrapers = len(self._tasks)
        
        if total_scrapers > 0 and open_circuits / total_scrapers > 0.5:
            return False
        
        # Verificar tasa de éxito
        if self._stats.total_runs > 10:
            success_rate = self._stats.successful_runs / self._stats.total_runs
            if success_rate < 0.5:
                return False
        
        return True


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================

def create_orchestrator_from_config(config_path: str) -> ScraperOrchestrator:
    """
    Crea un orquestador desde un archivo de configuración YAML.
    
    Args:
        config_path: Ruta al archivo de configuración
        
    Returns:
        ScraperOrchestrator configurado
    """
    config = OrchestratorConfig(config_file=config_path)
    return ScraperOrchestrator(config)


async def run_once(
    scrapers: List[Callable[..., Awaitable[Any]]],
    max_concurrent: int = 5
) -> List[ScraperResult]:
    """
    Ejecuta una lista de scrapers una sola vez.
    
    Función de conveniencia para ejecución simple.
    
    Args:
        scrapers: Lista de funciones async de scraping
        max_concurrent: Máximo de scrapers concurrentes
        
    Returns:
        Lista de resultados
    """
    orchestrator = ScraperOrchestrator(
        OrchestratorConfig(max_concurrent_scrapers=max_concurrent)
    )
    
    for i, scraper in enumerate(scrapers):
        name = getattr(scraper, '__name__', f'scraper_{i}')
        orchestrator.register_scraper(
            name=name,
            source=f"source_{i}",
            scraper_callable=scraper
        )
    
    return await orchestrator.run_all()
