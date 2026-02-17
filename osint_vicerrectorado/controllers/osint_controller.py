"""
OSINTController - Controlador principal de recolección OSINT
Sistema de Analítica EMI

Orquesta los scrapers de Facebook y TikTok:
- Registro y gestión de múltiples scrapers
- Ejecución secuencial o paralela de recolección
- Integración con APScheduler para automatización
- Almacenamiento de datos en base de datos

Autor: Sistema OSINT EMI
Fecha: Diciembre 2024
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
import pytz

from scrapers.facebook_scraper import FacebookScraper
from scrapers.tiktok_scraper import TikTokScraper
from database.db_writer import DatabaseWriter
from utils.rate_limiter import RateLimiter, create_facebook_limiter, create_tiktok_limiter
from utils.logger import setup_logger, log_collection


class OSINTController:
    """
    Controlador principal que orquesta todos los scrapers OSINT.
    
    Gestiona la recolección de datos de múltiples fuentes,
    el almacenamiento en base de datos y la automatización.
    
    Attributes:
        config (dict): Configuración del sistema
        db (DatabaseWriter): Gestor de base de datos
        scrapers (Dict): Scrapers registrados por fuente
        rate_limiters (Dict): Rate limiters por plataforma
        scheduler (AsyncIOScheduler): Scheduler para automatización
        logger (logging.Logger): Logger para registrar operaciones
    """
    
    def __init__(self, config: dict = None, db: DatabaseWriter = None):
        """
        Inicializa el controlador OSINT.
        
        Args:
            config: Diccionario de configuración
            db: Instancia de DatabaseWriter (opcional)
        """
        self.config = config or self._load_config()
        self.logger = logging.getLogger("OSINT.Controller")
        
        # Inicializar base de datos
        self.db = db or DatabaseWriter(config=self.config)
        
        # Scrapers registrados
        self.scrapers: Dict[str, Any] = {}
        
        # Rate limiters por plataforma
        self.rate_limiters: Dict[str, RateLimiter] = {
            'facebook': create_facebook_limiter(),
            'tiktok': create_tiktok_limiter()
        }
        
        # Scheduler
        timezone = self.config.get('scheduler', {}).get('timezone', 'America/La_Paz')
        self.scheduler = AsyncIOScheduler(timezone=pytz.timezone(timezone))
        self.scheduler_running = False
        
        # Estadísticas globales
        self.stats = {
            'total_collections': 0,
            'total_items_collected': 0,
            'last_collection': None,
            'by_source': {}
        }
        
        # Registrar scrapers configurados
        self._register_configured_scrapers()
        
        self.logger.info("OSINTController inicializado")
    
    def _load_config(self) -> dict:
        """
        Carga la configuración desde el archivo config.json.
        
        Returns:
            dict: Configuración del sistema
        """
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            self.logger.warning("config.json no encontrado, usando configuración por defecto")
            return {}
    
    def _register_configured_scrapers(self) -> None:
        """
        Registra los scrapers según la configuración.
        """
        sources = self.config.get('sources', {})
        
        # Registrar scrapers de Facebook
        if sources.get('facebook', {}).get('enabled', True):
            for page in sources['facebook'].get('pages', []):
                scraper_id = f"fb_{page['name'].replace(' ', '_').lower()}"
                self.register_facebook_scraper(
                    scraper_id=scraper_id,
                    page_url=page['url'],
                    page_name=page['name']
                )
        
        # Registrar scrapers de TikTok
        if sources.get('tiktok', {}).get('enabled', True):
            for account in sources['tiktok'].get('accounts', []):
                scraper_id = f"tt_{account['username']}"
                self.register_tiktok_scraper(
                    scraper_id=scraper_id,
                    profile_url=account['url'],
                    account_name=account['name']
                )
    
    def register_facebook_scraper(self, scraper_id: str, 
                                   page_url: str, page_name: str) -> None:
        """
        Registra un scraper de Facebook.
        
        Args:
            scraper_id: Identificador único del scraper
            page_url: URL de la página de Facebook
            page_name: Nombre descriptivo de la página
        """
        self.scrapers[scraper_id] = {
            'type': 'facebook',
            'scraper_class': FacebookScraper,
            'args': {
                'page_url': page_url,
                'page_name': page_name,
                'config': self.config
            },
            'source_id': None  # Se obtiene de la BD al ejecutar
        }
        
        self.stats['by_source'][scraper_id] = {
            'collections': 0,
            'items': 0,
            'last_run': None
        }
        
        self.logger.info(f"Scraper registrado: {scraper_id} ({page_name})")
    
    def register_tiktok_scraper(self, scraper_id: str,
                                 profile_url: str, account_name: str) -> None:
        """
        Registra un scraper de TikTok.
        
        Args:
            scraper_id: Identificador único del scraper
            profile_url: URL del perfil de TikTok
            account_name: Nombre descriptivo de la cuenta
        """
        self.scrapers[scraper_id] = {
            'type': 'tiktok',
            'scraper_class': TikTokScraper,
            'args': {
                'profile_url': profile_url,
                'account_name': account_name,
                'config': self.config
            },
            'source_id': None
        }
        
        self.stats['by_source'][scraper_id] = {
            'collections': 0,
            'items': 0,
            'last_run': None
        }
        
        self.logger.info(f"Scraper registrado: {scraper_id} ({account_name})")
    
    async def trigger_collection(self, source: str = 'all', 
                                  limit: int = 100) -> Dict[str, Any]:
        """
        Ejecuta la recolección de datos.
        
        Args:
            source: ID del scraper a ejecutar o 'all' para todos
            limit: Número máximo de items a recolectar por fuente
            
        Returns:
            Dict: Resultados de la recolección
        """
        start_time = datetime.now()
        log_id = self.db.log_execution('recoleccion', source)
        
        results = {
            'success': True,
            'total_collected': 0,
            'total_saved': 0,
            'total_duplicates': 0,
            'by_source': {},
            'errors': []
        }
        
        # Determinar qué scrapers ejecutar
        scrapers_to_run = {}
        if source == 'all':
            scrapers_to_run = self.scrapers
        elif source in self.scrapers:
            scrapers_to_run = {source: self.scrapers[source]}
        elif source in ['facebook', 'tiktok']:
            # Filtrar por tipo de plataforma
            scrapers_to_run = {
                sid: sinfo for sid, sinfo in self.scrapers.items()
                if sinfo.get('type', '').lower() == source.lower()
            }
            if not scrapers_to_run:
                error_msg = f"No hay scrapers configurados para: {source}"
                self.logger.error(error_msg)
                results['success'] = False
                results['errors'].append(error_msg)
                return results
        else:
            error_msg = f"Scraper no encontrado: {source}"
            self.logger.error(error_msg)
            results['success'] = False
            results['errors'].append(error_msg)
            return results
        
        # Ejecutar cada scraper secuencialmente
        for scraper_id, scraper_info in scrapers_to_run.items():
            try:
                self.logger.info(f"Iniciando recolección: {scraper_id}")
                
                source_result = await self._run_single_scraper(
                    scraper_id, scraper_info, limit
                )
                
                results['by_source'][scraper_id] = source_result
                results['total_collected'] += source_result['collected']
                results['total_saved'] += source_result['saved']
                results['total_duplicates'] += source_result['duplicates']
                
                # Log de recolección
                log_collection(
                    source=scraper_info['type'],
                    items=source_result['collected'],
                    duration=source_result['duration'],
                    status='success' if source_result['collected'] > 0 else 'partial'
                )
                
            except Exception as e:
                error_msg = f"Error en {scraper_id}: {str(e)}"
                self.logger.error(error_msg)
                results['errors'].append(error_msg)
                results['by_source'][scraper_id] = {
                    'collected': 0,
                    'saved': 0,
                    'duplicates': 0,
                    'error': str(e)
                }
        
        # Actualizar estadísticas globales
        self.stats['total_collections'] += 1
        self.stats['total_items_collected'] += results['total_collected']
        self.stats['last_collection'] = datetime.now().isoformat()
        
        # Completar log
        duration = (datetime.now() - start_time).total_seconds()
        self.db.complete_execution_log(
            log_id,
            success=len(results['errors']) == 0,
            processed=results['total_collected'],
            successful=results['total_saved'],
            failed=len(results['errors']),
            details={'results': results, 'duration': duration}
        )
        
        self.logger.info(
            f"Recolección completada: {results['total_saved']} nuevos, "
            f"{results['total_duplicates']} duplicados, "
            f"{len(results['errors'])} errores"
        )
        
        return results
    
    async def _run_single_scraper(self, scraper_id: str, 
                                   scraper_info: dict, 
                                   limit: int) -> Dict[str, Any]:
        """
        Ejecuta un scraper individual.
        
        Args:
            scraper_id: ID del scraper
            scraper_info: Información del scraper
            limit: Límite de items
            
        Returns:
            Dict: Resultado de la recolección
        """
        start_time = datetime.now()
        
        # Crear instancia del scraper
        ScraperClass = scraper_info['scraper_class']
        scraper = ScraperClass(**scraper_info['args'])
        
        # Ejecutar recolección
        collected_data = await scraper.run(limit=limit)
        
        duration = (datetime.now() - start_time).total_seconds()
        
        # Obtener o crear source_id
        source_type = scraper_info['type'].capitalize()
        if scraper_info['type'] == 'facebook':
            source_name = scraper_info['args']['page_name']
            source_url = scraper_info['args']['page_url']
            identificador = scraper._extract_page_id(source_url) if hasattr(scraper, '_extract_page_id') else scraper_id
        else:
            source_name = scraper_info['args']['account_name']
            source_url = scraper_info['args']['profile_url']
            identificador = scraper.username if hasattr(scraper, 'username') else scraper_id
        
        source_id = self.db.get_or_create_source(
            nombre=source_name,
            tipo=source_type,
            url=source_url,
            identificador=identificador
        )
        
        # Guardar en base de datos
        saved, duplicates = self.db.save_collected_data(collected_data, source_id)
        
        # Actualizar estadísticas del scraper
        self.stats['by_source'][scraper_id]['collections'] += 1
        self.stats['by_source'][scraper_id]['items'] += saved
        self.stats['by_source'][scraper_id]['last_run'] = datetime.now().isoformat()
        
        return {
            'collected': len(collected_data),
            'saved': saved,
            'duplicates': duplicates,
            'duration': duration
        }
    
    def get_collection_status(self) -> Dict[str, Any]:
        """
        Obtiene el estado actual de la recolección.
        
        Returns:
            Dict: Estado y estadísticas del sistema
        """
        db_stats = self.db.get_statistics()
        
        return {
            'scrapers_registered': len(self.scrapers),
            'scrapers': list(self.scrapers.keys()),
            'scheduler_running': self.scheduler_running,
            'global_stats': self.stats,
            'database_stats': db_stats,
            'rate_limiters': {
                name: limiter.get_stats() 
                for name, limiter in self.rate_limiters.items()
            }
        }
    
    def get_engagement_stats(self) -> List[Dict[str, Any]]:
        """
        Obtiene estadísticas de engagement por fuente.
        
        Returns:
            List[Dict]: Estadísticas de engagement
        """
        return self.db.get_engagement_stats_by_source()
    
    # =========================================================
    # Métodos de Scheduler (APScheduler)
    # =========================================================
    
    def start_scheduler(self) -> None:
        """
        Inicia el scheduler para recolección automática.
        """
        if self.scheduler_running:
            self.logger.warning("Scheduler ya está corriendo")
            return
        
        scheduler_config = self.config.get('scheduler', {})
        interval_hours = scheduler_config.get('collection_interval_hours', 12)
        
        # Agregar job de recolección
        self.scheduler.add_job(
            self._scheduled_collection,
            trigger=IntervalTrigger(hours=interval_hours),
            id='osint_collection',
            name='Recolección OSINT programada',
            replace_existing=True
        )
        
        # Agregar job de ETL
        etl_interval = scheduler_config.get('etl_interval_hours', 6)
        self.scheduler.add_job(
            self._scheduled_etl,
            trigger=IntervalTrigger(hours=etl_interval),
            id='osint_etl',
            name='Procesamiento ETL programado',
            replace_existing=True
        )
        
        self.scheduler.start()
        self.scheduler_running = True
        
        self.logger.info(
            f"Scheduler iniciado: recolección cada {interval_hours}h, "
            f"ETL cada {etl_interval}h"
        )
    
    def stop_scheduler(self) -> None:
        """
        Detiene el scheduler.
        """
        if not self.scheduler_running:
            self.logger.warning("Scheduler no está corriendo")
            return
        
        self.scheduler.shutdown(wait=True)
        self.scheduler_running = False
        self.logger.info("Scheduler detenido")
    
    async def _scheduled_collection(self) -> None:
        """
        Ejecuta recolección programada (llamada por scheduler).
        """
        self.logger.info("Iniciando recolección programada...")
        
        try:
            results = await self.trigger_collection(source='all', limit=50)
            self.logger.info(
                f"Recolección programada completada: {results['total_saved']} nuevos items"
            )
        except Exception as e:
            self.logger.error(f"Error en recolección programada: {e}")
    
    async def _scheduled_etl(self) -> None:
        """
        Ejecuta ETL programado (llamada por scheduler).
        """
        self.logger.info("Iniciando ETL programado...")
        
        try:
            from etl.etl_controller import ETLController
            
            etl = ETLController(config=self.config, db=self.db)
            results = etl.run()
            
            self.logger.info(
                f"ETL programado completado: {results.get('loaded', 0)} registros procesados"
            )
        except Exception as e:
            self.logger.error(f"Error en ETL programado: {e}")
    
    def get_scheduled_jobs(self) -> List[Dict[str, Any]]:
        """
        Obtiene información de los jobs programados.
        
        Returns:
            List[Dict]: Lista de jobs con su información
        """
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
                'trigger': str(job.trigger)
            })
        return jobs
    
    def close(self) -> None:
        """
        Cierra el controlador y libera recursos.
        """
        if self.scheduler_running:
            self.stop_scheduler()
        
        if self.db:
            self.db.close()
        
        self.logger.info("OSINTController cerrado")


async def main():
    """Función de prueba para el controlador OSINT."""
    import json
    
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Cargar configuración
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        config = {}
    
    print("=== Test de OSINTController ===\n")
    
    controller = OSINTController(config)
    
    # Mostrar estado
    status = controller.get_collection_status()
    print(f"Scrapers registrados: {status['scrapers_registered']}")
    for scraper in status['scrapers']:
        print(f"  - {scraper}")
    
    # Ejecutar recolección de prueba (límite pequeño)
    print("\nEjecutando recolección de prueba...")
    results = await controller.trigger_collection(source='all', limit=5)
    
    print("\n=== Resultados ===")
    print(f"Total recolectados: {results['total_collected']}")
    print(f"Total guardados: {results['total_saved']}")
    print(f"Duplicados: {results['total_duplicates']}")
    
    if results['errors']:
        print(f"Errores: {results['errors']}")
    
    controller.close()


if __name__ == "__main__":
    asyncio.run(main())
