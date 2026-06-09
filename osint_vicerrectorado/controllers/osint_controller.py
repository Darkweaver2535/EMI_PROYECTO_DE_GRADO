"""
OSINTController - Controlador principal de recolección OSINT
Sistema de Analítica EMI

Orquesta los collectors de Facebook y TikTok (vía Apify):
- Registro y gestión de múltiples collectors
- Ejecución secuencial de recolección
- Integración con APScheduler para automatización
- Almacenamiento de datos en base de datos

Autor: Sistema OSINT EMI
Fecha: Mayo 2026 (refactorizado para Apify)
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
import pytz

from scrapers.facebook_collector import FacebookCollector
from scrapers.tiktok_collector import TikTokCollector
from database.db_writer import DatabaseWriter


class OSINTController:
    """
    Controlador principal que orquesta todos los collectors OSINT.

    Gestiona la recolección de datos de múltiples fuentes vía Apify,
    el almacenamiento en base de datos y la automatización.

    Attributes:
        config (dict): Configuración del sistema
        db (DatabaseWriter): Gestor de base de datos
        collectors (Dict): Collectors registrados por fuente
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

        # Collectors registrados
        self.collectors: Dict[str, Any] = {}

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

        # Registrar collectors configurados
        self._register_configured_collectors()

        self.logger.info("OSINTController inicializado (Apify mode)")

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
            self.logger.warning(
                "config.json no encontrado, usando configuración por defecto"
            )
            return {}

    def _register_configured_collectors(self) -> None:
        """
        Registra los collectors según la configuración.
        """
        sources = self.config.get('sources', {})

        # Registrar collectors de Facebook
        if sources.get('facebook', {}).get('enabled', True):
            for page in sources['facebook'].get('pages', []):
                collector_id = f"fb_{page['name'].replace(' ', '_').lower()}"
                self.register_facebook_collector(
                    collector_id=collector_id,
                    page_url=page['url'],
                    page_name=page['name']
                )

        # Registrar collectors de TikTok
        if sources.get('tiktok', {}).get('enabled', True):
            for account in sources['tiktok'].get('accounts', []):
                collector_id = f"tt_{account['username']}"
                self.register_tiktok_collector(
                    collector_id=collector_id,
                    profile_url=account['url'],
                    account_name=account['name']
                )

    def register_facebook_collector(
        self,
        collector_id: str,
        page_url: str,
        page_name: str
    ) -> None:
        """
        Registra un collector de Facebook.

        Args:
            collector_id: Identificador único del collector
            page_url: URL de la página de Facebook
            page_name: Nombre descriptivo de la página
        """
        self.collectors[collector_id] = {
            'type': 'facebook',
            'collector_class': FacebookCollector,
            'args': {
                'page_url': page_url,
                'page_name': page_name,
                'config': self.config
            },
            'source_id': None
        }

        self.stats['by_source'][collector_id] = {
            'collections': 0,
            'items': 0,
            'last_run': None
        }

        self.logger.info(f"Collector registrado: {collector_id} ({page_name})")

    def register_tiktok_collector(
        self,
        collector_id: str,
        profile_url: str,
        account_name: str
    ) -> None:
        """
        Registra un collector de TikTok.

        Args:
            collector_id: Identificador único del collector
            profile_url: URL del perfil de TikTok
            account_name: Nombre descriptivo de la cuenta
        """
        self.collectors[collector_id] = {
            'type': 'tiktok',
            'collector_class': TikTokCollector,
            'args': {
                'profile_url': profile_url,
                'account_name': account_name,
                'config': self.config
            },
            'source_id': None
        }

        self.stats['by_source'][collector_id] = {
            'collections': 0,
            'items': 0,
            'last_run': None
        }

        self.logger.info(f"Collector registrado: {collector_id} ({account_name})")

    async def trigger_collection(
        self,
        source: str = 'all',
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Ejecuta la recolección de datos.

        Args:
            source: ID del collector a ejecutar o 'all' para todos
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

        # Determinar qué collectors ejecutar
        collectors_to_run = {}
        if source == 'all':
            collectors_to_run = self.collectors
        elif source in self.collectors:
            collectors_to_run = {source: self.collectors[source]}
        elif source in ['facebook', 'tiktok']:
            collectors_to_run = {
                cid: cinfo for cid, cinfo in self.collectors.items()
                if cinfo.get('type', '').lower() == source.lower()
            }
            if not collectors_to_run:
                error_msg = f"No hay collectors configurados para: {source}"
                self.logger.error(error_msg)
                results['success'] = False
                results['errors'].append(error_msg)
                return results
        else:
            error_msg = f"Collector no encontrado: {source}"
            self.logger.error(error_msg)
            results['success'] = False
            results['errors'].append(error_msg)
            return results

        # Ejecutar cada collector secuencialmente
        for collector_id, collector_info in collectors_to_run.items():
            try:
                self.logger.info(f"Iniciando recolección: {collector_id}")

                source_result = await self._run_single_collector(
                    collector_id, collector_info, limit
                )

                results['by_source'][collector_id] = source_result
                results['total_collected'] += source_result['collected']
                results['total_saved'] += source_result['saved']
                results['total_duplicates'] += source_result['duplicates']

            except Exception as e:
                error_msg = f"Error en {collector_id}: {str(e)}"
                self.logger.error(error_msg)
                results['errors'].append(error_msg)
                results['by_source'][collector_id] = {
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

    async def _run_single_collector(
        self,
        collector_id: str,
        collector_info: dict,
        limit: int
    ) -> Dict[str, Any]:
        """
        Ejecuta un collector individual.

        Args:
            collector_id: ID del collector
            collector_info: Información del collector
            limit: Límite de items

        Returns:
            Dict: Resultado de la recolección
        """
        start_time = datetime.now()

        # Crear instancia del collector
        CollectorClass = collector_info['collector_class']
        collector = CollectorClass(**collector_info['args'])

        # Ejecutar recolección
        collected_data = await collector.run(limit=limit)

        duration = (datetime.now() - start_time).total_seconds()

        # Obtener o crear source_id
        source_type = collector_info['type'].capitalize()
        if collector_info['type'] == 'facebook':
            source_name = collector_info['args']['page_name']
            source_url = collector_info['args']['page_url']
            identificador = collector.page_id
        else:
            source_name = collector_info['args']['account_name']
            source_url = collector_info['args']['profile_url']
            identificador = collector.username

        source_id = self.db.get_or_create_source(
            nombre=source_name,
            tipo=source_type,
            url=source_url,
            identificador=identificador
        )

        # Guardar en base de datos
        saved, duplicates = self.db.save_collected_data(collected_data, source_id)

        # Actualizar estadísticas del collector
        self.stats['by_source'][collector_id]['collections'] += 1
        self.stats['by_source'][collector_id]['items'] += saved
        self.stats['by_source'][collector_id]['last_run'] = (
            datetime.now().isoformat()
        )

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
            'collectors_registered': len(self.collectors),
            'collectors': list(self.collectors.keys()),
            'scheduler_running': self.scheduler_running,
            'global_stats': self.stats,
            'database_stats': db_stats,
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
                f"Recolección programada completada: "
                f"{results['total_saved']} nuevos items"
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
            import asyncio

            etl = ETLController(config=self.config, db=self.db)
            results = etl.run()
            
            nuevos_registros = results.get('loaded', 0)

            self.logger.info(
                f"ETL programado completado: "
                f"{nuevos_registros} registros procesados"
            )
            
            if nuevos_registros > 0:
                self.logger.info("Iniciando análisis IA automático...")
                
                def run_ai():
                    try:
                        import sentiment_analyzer
                        from nlp_pipeline import NLPPipeline
                        
                        # a) Sentiment Analyzer: solo registros sin análisis previo
                        sentiment_analyzer.ejecutar_analisis_completo(force_reanalysis=False)
                        
                        # b) NLP Pipeline: recalcula tópicos y clusters
                        NLPPipeline().ejecutar_pipeline_completo()
                        
                        self.logger.info("Pipeline NLP/ML completado. Dashboard actualizado.")
                    except Exception as ai_e:
                        self.logger.error(f"Error en análisis IA automático: {ai_e}")

                loop = asyncio.get_running_loop()
                # Se ejecuta en un thread separado para NO bloquear el event loop del scheduler
                future = loop.run_in_executor(None, run_ai)
                future.add_done_callback(
                    lambda f: self.logger.error(f"IA thread error: {f.exception()}") 
                    if f.exception() else None
                )
            else:
                self.logger.info("Sin datos nuevos, omitiendo análisis IA")

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
                'next_run': (
                    job.next_run_time.isoformat() if job.next_run_time else None
                ),
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
