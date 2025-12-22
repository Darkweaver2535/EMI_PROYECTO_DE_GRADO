#!/usr/bin/env python3
"""
Sistema OSINT - Vicerrectorado EMI Bolivia
==========================================

Herramienta de línea de comandos para recolección y procesamiento
de datos de fuentes abiertas (Facebook, TikTok).

Uso:
    python main.py --collect              # Ejecutar recolección manual
    python main.py --process              # Ejecutar ETL manual
    python main.py --stats                # Mostrar estadísticas
    python main.py --schedule-start       # Iniciar scheduler automático

Autor: Sistema OSINT EMI
Fecha: Diciembre 2024
"""

import argparse
import asyncio
import json
import sys
import os
from datetime import datetime
from typing import Optional

# Agregar el directorio actual al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from controllers.osint_controller import OSINTController
from etl.etl_controller import ETLController
from database.db_writer import DatabaseWriter
from utils.logger import setup_logger


def load_config() -> dict:
    """
    Carga la configuración desde config.json.
    
    Returns:
        dict: Configuración del sistema
    """
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print("[ERROR] Archivo config.json no encontrado")
        print("Ejecute: cp config.json.example config.json")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"[ERROR] Error al parsear config.json: {e}")
        sys.exit(1)


def initialize_database(config: dict) -> DatabaseWriter:
    """
    Inicializa la base de datos.
    
    Args:
        config: Configuración del sistema
        
    Returns:
        DatabaseWriter: Instancia del gestor de base de datos
    """
    db = DatabaseWriter(config=config)
    db.initialize_schema()
    return db


def print_banner():
    """Imprime el banner del sistema."""
    banner = """
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║   ███████╗███╗   ███╗██╗     ██████╗ ███████╗██╗███╗   ██╗████████╗  ║
║   ██╔════╝████╗ ████║██║    ██╔═══██╗██╔════╝██║████╗  ██║╚══██╔══╝  ║
║   █████╗  ██╔████╔██║██║    ██║   ██║███████╗██║██╔██╗ ██║   ██║     ║
║   ██╔══╝  ██║╚██╔╝██║██║    ██║   ██║╚════██║██║██║╚██╗██║   ██║     ║
║   ███████╗██║ ╚═╝ ██║██║    ╚██████╔╝███████║██║██║ ╚████║   ██║     ║
║   ╚══════╝╚═╝     ╚═╝╚═╝     ╚═════╝ ╚══════╝╚═╝╚═╝  ╚═══╝   ╚═╝     ║
║                                                                      ║
║          Sistema OSINT - Vicerrectorado EMI Bolivia                  ║
║            Recolección y Análisis de Datos Abiertos                  ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
"""
    print(banner)


def print_section(title: str):
    """Imprime un separador de sección."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


async def cmd_collect(args, config: dict):
    """
    Ejecuta la recolección de datos OSINT.
    
    Args:
        args: Argumentos de línea de comandos
        config: Configuración del sistema
    """
    print_section("RECOLECCIÓN DE DATOS OSINT")
    
    source = args.source if hasattr(args, 'source') and args.source else 'all'
    limit = args.limit if hasattr(args, 'limit') and args.limit else 100
    
    print(f"\n[*] Fuente: {source}")
    print(f"[*] Límite por fuente: {limit}")
    print(f"[*] Hora de inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n[+] Iniciando scrapers...\n")
    
    controller = OSINTController(config)
    
    try:
        results = await controller.trigger_collection(source=source, limit=limit)
        
        print("\n" + "-"*50)
        print("  RESULTADOS DE RECOLECCIÓN")
        print("-"*50)
        
        if results['success']:
            print(f"\n  ✓ Recolección completada exitosamente")
        else:
            print(f"\n  ⚠ Recolección completada con errores")
        
        print(f"\n  Total recolectados: {results['total_collected']}")
        print(f"  Nuevos guardados:   {results['total_saved']}")
        print(f"  Duplicados:         {results['total_duplicates']}")
        
        if results['by_source']:
            print("\n  Por fuente:")
            for source_id, data in results['by_source'].items():
                status = "✓" if data.get('collected', 0) > 0 else "✗"
                print(f"    {status} {source_id}: {data.get('collected', 0)} items "
                      f"({data.get('saved', 0)} nuevos)")
        
        if results['errors']:
            print("\n  Errores:")
            for error in results['errors']:
                print(f"    ✗ {error}")
        
    except Exception as e:
        print(f"\n[ERROR] Error durante la recolección: {e}")
        raise
    finally:
        controller.close()
    
    print("\n" + "="*50)


async def cmd_process(args, config: dict):
    """
    Ejecuta el procesamiento ETL.
    
    Args:
        args: Argumentos de línea de comandos
        config: Configuración del sistema
    """
    print_section("PROCESAMIENTO ETL")
    
    print(f"\n[*] Hora de inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n[+] Iniciando pipeline ETL...\n")
    
    db = initialize_database(config)
    
    try:
        etl = ETLController(config=config, db=db)
        results = etl.run()
        
        print("\n" + "-"*50)
        print("  RESULTADOS DE ETL")
        print("-"*50)
        
        print(f"\n  Registros extraídos:     {results.get('extracted', 0)}")
        print(f"  Registros limpiados:     {results.get('cleaned', 0)}")
        print(f"  Registros transformados: {results.get('transformed', 0)}")
        print(f"  Registros validados:     {results.get('validated', 0)}")
        print(f"  Registros cargados:      {results.get('loaded', 0)}")
        print(f"  Registros inválidos:     {results.get('invalid', 0)}")
        
        if results.get('errors'):
            print("\n  Errores:")
            for error in results['errors'][:5]:  # Solo primeros 5
                print(f"    ✗ {error}")
        
    except Exception as e:
        print(f"\n[ERROR] Error durante ETL: {e}")
        raise
    finally:
        db.close()
    
    print("\n" + "="*50)


def cmd_stats(args, config: dict):
    """
    Muestra estadísticas del sistema.
    
    Args:
        args: Argumentos de línea de comandos
        config: Configuración del sistema
    """
    print_section("ESTADÍSTICAS DEL SISTEMA")
    
    db = initialize_database(config)
    
    try:
        stats = db.get_statistics()
        
        print("\n  📊 DATOS RECOLECTADOS")
        print("  " + "-"*40)
        print(f"  Total registros raw:       {stats.get('total_raw', 0)}")
        print(f"  Total registros procesados: {stats.get('total_processed', 0)}")
        print(f"  Registros pendientes ETL:   {stats.get('pending_etl', 0)}")
        
        print("\n  📱 POR FUENTE")
        print("  " + "-"*40)
        by_source = stats.get('by_source', {})
        for source, count in by_source.items():
            print(f"  {source}: {count} registros")
        
        print("\n  📅 ÚLTIMAS EJECUCIONES")
        print("  " + "-"*40)
        last_collection = stats.get('last_collection')
        last_etl = stats.get('last_etl')
        print(f"  Última recolección: {last_collection or 'Nunca'}")
        print(f"  Último ETL:         {last_etl or 'Nunca'}")
        
        # Estadísticas de engagement
        print("\n  📈 ENGAGEMENT POR FUENTE")
        print("  " + "-"*40)
        engagement = db.get_engagement_stats_by_source()
        for source_stats in engagement:
            print(f"  {source_stats['nombre']}:")
            print(f"    Publicaciones: {source_stats['total_posts']}")
            print(f"    Likes promedio: {source_stats['avg_likes']:.1f}")
            print(f"    Comentarios promedio: {source_stats['avg_comments']:.1f}")
        
        # Mostrar configuración
        print("\n  ⚙️ CONFIGURACIÓN ACTUAL")
        print("  " + "-"*40)
        sources = config.get('sources', {})
        
        print("  Facebook:")
        for page in sources.get('facebook', {}).get('pages', []):
            print(f"    - {page['name']}: {page['url']}")
        
        print("  TikTok:")
        for account in sources.get('tiktok', {}).get('accounts', []):
            print(f"    - {account['name']}: {account['url']}")
        
        scheduler = config.get('scheduler', {})
        print(f"\n  Intervalo de recolección: {scheduler.get('collection_interval_hours', 12)}h")
        print(f"  Intervalo de ETL:         {scheduler.get('etl_interval_hours', 6)}h")
        
    finally:
        db.close()
    
    print("\n" + "="*50)


async def cmd_schedule_start(args, config: dict):
    """
    Inicia el scheduler para ejecución automática.
    
    Args:
        args: Argumentos de línea de comandos
        config: Configuración del sistema
    """
    print_section("SCHEDULER AUTOMÁTICO")
    
    scheduler_config = config.get('scheduler', {})
    collection_interval = scheduler_config.get('collection_interval_hours', 12)
    etl_interval = scheduler_config.get('etl_interval_hours', 6)
    
    print(f"\n[*] Intervalo de recolección: {collection_interval} horas")
    print(f"[*] Intervalo de ETL: {etl_interval} horas")
    print(f"[*] Zona horaria: {scheduler_config.get('timezone', 'America/La_Paz')}")
    
    print("\n[+] Iniciando scheduler...")
    print("[+] Presione Ctrl+C para detener\n")
    
    controller = OSINTController(config)
    
    try:
        controller.start_scheduler()
        
        # Mostrar jobs programados
        jobs = controller.get_scheduled_jobs()
        print("Jobs programados:")
        for job in jobs:
            print(f"  - {job['name']}: próxima ejecución {job['next_run']}")
        
        print("\n[*] Scheduler corriendo. Esperando primera ejecución...")
        
        # Mantener el programa corriendo
        while True:
            await asyncio.sleep(60)
            
            # Mostrar estado cada minuto
            status = controller.get_collection_status()
            print(f"[{datetime.now().strftime('%H:%M:%S')}] "
                  f"Colecciones: {status['global_stats']['total_collections']}, "
                  f"Items: {status['global_stats']['total_items_collected']}")
            
    except KeyboardInterrupt:
        print("\n\n[*] Recibida señal de interrupción...")
    except Exception as e:
        print(f"\n[ERROR] Error en scheduler: {e}")
        raise
    finally:
        print("[+] Deteniendo scheduler...")
        controller.close()
        print("[+] Scheduler detenido correctamente")


def cmd_init_db(args, config: dict):
    """
    Inicializa la base de datos.
    
    Args:
        args: Argumentos de línea de comandos
        config: Configuración del sistema
    """
    print_section("INICIALIZACIÓN DE BASE DE DATOS")
    
    db_config = config.get('database', {})
    db_path = db_config.get('path', 'data/osint_emi.db')
    
    print(f"\n[*] Base de datos: {db_path}")
    
    db = DatabaseWriter(config=config)
    
    try:
        db.initialize_schema()
        print("\n[+] Esquema creado/verificado correctamente")
        
        # Mostrar tablas creadas
        stats = db.get_statistics()
        print(f"\n[+] Fuentes configuradas: {stats.get('total_sources', 0)}")
        
    finally:
        db.close()
    
    print("\n[+] Base de datos lista para usar")
    print("="*50)


def cmd_export(args, config: dict):
    """
    Exporta datos a CSV.
    
    Args:
        args: Argumentos de línea de comandos
        config: Configuración del sistema
    """
    import csv
    from datetime import datetime
    
    print_section("EXPORTACIÓN DE DATOS")
    
    output_file = args.output if hasattr(args, 'output') and args.output else \
                  f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    print(f"\n[*] Archivo de salida: {output_file}")
    
    db = initialize_database(config)
    
    try:
        # Obtener datos procesados
        processed_data = db.get_all_processed_data()
        
        if not processed_data:
            print("\n[!] No hay datos procesados para exportar")
            return
        
        # Exportar a CSV
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            if processed_data:
                writer = csv.DictWriter(f, fieldnames=processed_data[0].keys())
                writer.writeheader()
                writer.writerows(processed_data)
        
        print(f"\n[+] Exportados {len(processed_data)} registros")
        print(f"[+] Archivo guardado: {output_file}")
        
    finally:
        db.close()
    
    print("="*50)


def create_parser() -> argparse.ArgumentParser:
    """
    Crea el parser de argumentos.
    
    Returns:
        ArgumentParser: Parser configurado
    """
    parser = argparse.ArgumentParser(
        prog='osint_emi',
        description='Sistema OSINT para Vicerrectorado EMI Bolivia',
        epilog='Ejemplo: python main.py --collect --source all --limit 50',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Argumentos globales
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Modo verbose (más información de debug)'
    )
    
    parser.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='Modo silencioso (solo errores)'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        default='config.json',
        help='Ruta al archivo de configuración'
    )
    
    # Subcomandos usando argumentos mutuamente exclusivos
    group = parser.add_mutually_exclusive_group(required=True)
    
    group.add_argument(
        '--collect',
        action='store_true',
        help='Ejecutar recolección de datos OSINT'
    )
    
    group.add_argument(
        '--process',
        action='store_true',
        help='Ejecutar procesamiento ETL'
    )
    
    group.add_argument(
        '--stats',
        action='store_true',
        help='Mostrar estadísticas del sistema'
    )
    
    group.add_argument(
        '--schedule-start',
        action='store_true',
        help='Iniciar scheduler para ejecución automática'
    )
    
    group.add_argument(
        '--init-db',
        action='store_true',
        help='Inicializar base de datos'
    )
    
    group.add_argument(
        '--export',
        action='store_true',
        help='Exportar datos procesados a CSV'
    )
    
    # Argumentos específicos de collect
    parser.add_argument(
        '--source',
        type=str,
        choices=['all', 'facebook', 'tiktok'],
        default='all',
        help='Fuente de datos a recolectar (default: all)'
    )
    
    parser.add_argument(
        '--limit',
        type=int,
        default=100,
        help='Límite de items por fuente (default: 100)'
    )
    
    # Argumentos específicos de export
    parser.add_argument(
        '--output',
        type=str,
        help='Archivo de salida para exportación'
    )
    
    return parser


def setup_logging(args) -> None:
    """
    Configura el logging según los argumentos.
    
    Args:
        args: Argumentos de línea de comandos
    """
    import logging
    
    if args.verbose:
        level = logging.DEBUG
    elif args.quiet:
        level = logging.ERROR
    else:
        level = logging.INFO
    
    # Usar nuestro logger personalizado
    setup_logger(
        name='OSINT',
        log_file='data/logs/osint.log',
        level=level
    )


async def async_main():
    """Punto de entrada asíncrono principal."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Cargar configuración
    config = load_config()
    
    # Configurar logging
    setup_logging(args)
    
    # Imprimir banner (excepto en modo quiet)
    if not args.quiet:
        print_banner()
    
    # Ejecutar comando correspondiente
    try:
        if args.collect:
            await cmd_collect(args, config)
        elif args.process:
            await cmd_process(args, config)
        elif args.stats:
            cmd_stats(args, config)
        elif args.schedule_start:
            await cmd_schedule_start(args, config)
        elif args.init_db:
            cmd_init_db(args, config)
        elif args.export:
            cmd_export(args, config)
            
    except KeyboardInterrupt:
        print("\n\n[!] Operación cancelada por el usuario")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] Error fatal: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def main():
    """Punto de entrada principal."""
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
