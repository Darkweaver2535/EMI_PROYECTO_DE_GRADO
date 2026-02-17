#!/usr/bin/env python3
"""
Script de Anotación Manual de Sentimientos
Sistema de Analítica EMI - Sprint 3

Este script permite anotar manualmente textos con su sentimiento
para generar datos de entrenamiento para el modelo BETO.

Uso:
    python annotate_sentiments.py [--limit N] [--output FILE] [--resume]

Autor: Sistema OSINT EMI
Fecha: Enero 2025
"""

import os
import sys
import json
import sqlite3
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

# Añadir directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

console = Console() if RICH_AVAILABLE else None


class SentimentAnnotator:
    """
    Herramienta interactiva para anotar sentimientos en textos.
    
    Permite a un anotador humano clasificar textos como:
    - Positivo (p)
    - Negativo (n)
    - Neutral (u)
    
    Los resultados se guardan en la base de datos y/o en archivo JSON.
    """
    
    SENTIMENT_MAP = {
        'p': 'Positivo',
        'positivo': 'Positivo',
        '1': 'Positivo',
        '+': 'Positivo',
        'n': 'Negativo',
        'negativo': 'Negativo',
        '0': 'Negativo',
        '-': 'Negativo',
        'u': 'Neutral',
        'neutral': 'Neutral',
        '2': 'Neutral',
        '=': 'Neutral',
    }
    
    def __init__(
        self,
        db_path: str = None,
        output_file: str = None,
        annotator_name: str = None
    ):
        """
        Inicializa el anotador.
        
        Args:
            db_path: Ruta a la base de datos SQLite
            output_file: Archivo JSON para exportar anotaciones
            annotator_name: Nombre del anotador
        """
        self.db_path = db_path or 'data/osint_emi.db'
        self.output_file = output_file or f'data/annotations_{datetime.now().strftime("%Y%m%d")}.json'
        self.annotator = annotator_name or 'anonimo'
        
        self.annotations: List[Dict[str, Any]] = []
        self.session_stats = {
            'total': 0,
            'positivo': 0,
            'negativo': 0,
            'neutral': 0,
            'skipped': 0
        }
    
    def connect_db(self) -> sqlite3.Connection:
        """Conecta a la base de datos."""
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Base de datos no encontrada: {self.db_path}")
        return sqlite3.connect(self.db_path)
    
    def get_unannotated_texts(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Obtiene textos no anotados de la base de datos.
        
        Args:
            limit: Número máximo de textos a obtener
            
        Returns:
            Lista de textos con sus metadatos
        """
        conn = self.connect_db()
        cursor = conn.cursor()
        
        # Obtener textos procesados que no tienen anotación manual
        query = """
            SELECT 
                dp.id_dato_procesado,
                dp.contenido_limpio,
                dr.contenido_original,
                f.tipo_fuente,
                f.nombre_fuente,
                dp.engagement_total,
                dp.sentimiento_basico
            FROM dato_procesado dp
            JOIN dato_recolectado dr ON dp.id_dato_original = dr.id_dato
            JOIN fuente_osint f ON dr.id_fuente = f.id_fuente
            LEFT JOIN anotacion_manual am ON dp.id_dato_procesado = am.id_dato_procesado
            WHERE am.id_anotacion IS NULL
            AND dp.contenido_limpio IS NOT NULL
            AND LENGTH(dp.contenido_limpio) > 20
            ORDER BY RANDOM()
            LIMIT ?
        """
        
        try:
            cursor.execute(query, (limit,))
            rows = cursor.fetchall()
        except sqlite3.OperationalError:
            # Si la tabla anotacion_manual no existe, crear y reintentar
            self._create_annotation_table(conn)
            cursor.execute(query, (limit,))
            rows = cursor.fetchall()
        
        conn.close()
        
        texts = []
        for row in rows:
            texts.append({
                'id': row[0],
                'texto_limpio': row[1],
                'texto_original': row[2],
                'fuente': row[3],
                'nombre_fuente': row[4],
                'engagement': row[5],
                'sentimiento_basico': row[6]
            })
        
        return texts
    
    def _create_annotation_table(self, conn: sqlite3.Connection):
        """Crea la tabla de anotaciones si no existe."""
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS anotacion_manual (
                id_anotacion INTEGER PRIMARY KEY AUTOINCREMENT,
                id_dato_procesado INTEGER NOT NULL,
                texto_original TEXT NOT NULL,
                sentimiento_anotado VARCHAR(20) NOT NULL,
                confianza_anotacion VARCHAR(20),
                anotador VARCHAR(100),
                fecha_anotacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notas TEXT,
                usado_entrenamiento BOOLEAN DEFAULT 0,
                FOREIGN KEY (id_dato_procesado) REFERENCES dato_procesado(id_dato_procesado)
            )
        """)
        conn.commit()
    
    def save_annotation(
        self,
        text_id: int,
        text: str,
        sentiment: str,
        confidence: str = 'alta',
        notes: str = None
    ) -> bool:
        """
        Guarda una anotación en la base de datos.
        
        Args:
            text_id: ID del dato procesado
            text: Texto anotado
            sentiment: Sentimiento asignado
            confidence: Confianza de la anotación
            notes: Notas adicionales
            
        Returns:
            True si se guardó correctamente
        """
        try:
            conn = self.connect_db()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO anotacion_manual 
                (id_dato_procesado, texto_original, sentimiento_anotado, 
                 confianza_anotacion, anotador, notas)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (text_id, text, sentiment, confidence, self.annotator, notes))
            
            conn.commit()
            conn.close()
            
            # También guardar en memoria
            self.annotations.append({
                'id': text_id,
                'text': text,
                'label': sentiment,
                'confidence': confidence,
                'annotator': self.annotator,
                'timestamp': datetime.now().isoformat(),
                'notes': notes
            })
            
            return True
            
        except Exception as e:
            print(f"Error guardando anotación: {e}")
            return False
    
    def display_text(self, text_data: Dict[str, Any], index: int, total: int):
        """Muestra un texto para anotar."""
        if RICH_AVAILABLE:
            console.clear()
            console.print(Panel(
                f"[bold]Anotación de Sentimientos[/bold]\n"
                f"Progreso: {index}/{total}",
                title="Sistema OSINT EMI"
            ))
            
            # Info de la fuente
            table = Table(show_header=False, box=None)
            table.add_column("Campo", style="cyan")
            table.add_column("Valor")
            table.add_row("Fuente:", f"{text_data['fuente']} - {text_data['nombre_fuente']}")
            table.add_row("Engagement:", str(text_data['engagement'] or 'N/A'))
            table.add_row("Sent. básico:", text_data['sentimiento_basico'] or 'N/A')
            console.print(table)
            
            console.print("\n[bold yellow]TEXTO A ANOTAR:[/bold yellow]")
            console.print(Panel(
                text_data['texto_original'] or text_data['texto_limpio'],
                border_style="yellow"
            ))
            
            console.print("\n[bold]Opciones:[/bold]")
            console.print("  [green]p[/green] = Positivo  |  [red]n[/red] = Negativo  |  [blue]u[/blue] = Neutral")
            console.print("  [dim]s = Saltar  |  q = Salir  |  h = Ayuda[/dim]")
        else:
            print("\n" + "=" * 60)
            print(f"ANOTACIÓN {index}/{total}")
            print("=" * 60)
            print(f"Fuente: {text_data['fuente']} - {text_data['nombre_fuente']}")
            print(f"Engagement: {text_data['engagement'] or 'N/A'}")
            print(f"Sentimiento básico: {text_data['sentimiento_basico'] or 'N/A'}")
            print("-" * 60)
            print("TEXTO:")
            print(text_data['texto_original'] or text_data['texto_limpio'])
            print("-" * 60)
            print("Opciones: (p)ositivo | (n)egativo | n(u)tral | (s)altar | (q)uit")
    
    def get_user_input(self) -> str:
        """Obtiene la entrada del usuario."""
        if RICH_AVAILABLE:
            response = Prompt.ask("\n[bold]Tu anotación[/bold]").lower().strip()
        else:
            response = input("\nTu anotación: ").lower().strip()
        return response
    
    def show_help(self):
        """Muestra ayuda sobre las categorías."""
        help_text = """
        [bold]Guía de Anotación de Sentimientos[/bold]
        
        [green]POSITIVO (p)[/green]: El texto expresa una opinión favorable, 
        satisfacción, agradecimiento, o emociones positivas.
        Ejemplos: "Excelente servicio", "Me encanta la EMI", "Muy buenos profesores"
        
        [red]NEGATIVO (n)[/red]: El texto expresa quejas, insatisfacción, 
        críticas, o emociones negativas.
        Ejemplos: "Pésima atención", "No recomiendo", "Mal servicio"
        
        [blue]NEUTRAL (u)[/blue]: El texto es informativo, neutral, 
        o no expresa una opinión clara.
        Ejemplos: "La biblioteca abre a las 8am", "Información de inscripciones"
        
        [dim]SALTAR (s)[/dim]: Si no estás seguro o el texto es ambiguo.
        [dim]SALIR (q)[/dim]: Guardar y terminar la sesión.
        """
        
        if RICH_AVAILABLE:
            console.print(Panel(help_text, title="Ayuda"))
            input("\nPresiona Enter para continuar...")
        else:
            print(help_text)
            input("\nPresiona Enter para continuar...")
    
    def show_stats(self):
        """Muestra estadísticas de la sesión."""
        stats = self.session_stats
        total_annotated = stats['positivo'] + stats['negativo'] + stats['neutral']
        
        if RICH_AVAILABLE:
            table = Table(title="Estadísticas de la Sesión")
            table.add_column("Categoría", style="cyan")
            table.add_column("Cantidad", justify="right")
            table.add_column("Porcentaje", justify="right")
            
            if total_annotated > 0:
                table.add_row("Positivo", str(stats['positivo']), 
                             f"{stats['positivo']/total_annotated*100:.1f}%")
                table.add_row("Negativo", str(stats['negativo']),
                             f"{stats['negativo']/total_annotated*100:.1f}%")
                table.add_row("Neutral", str(stats['neutral']),
                             f"{stats['neutral']/total_annotated*100:.1f}%")
                table.add_row("Saltados", str(stats['skipped']), "-")
                table.add_row("[bold]Total[/bold]", f"[bold]{total_annotated}[/bold]", "100%")
            
            console.print(table)
        else:
            print("\n--- Estadísticas de la Sesión ---")
            print(f"Positivo: {stats['positivo']}")
            print(f"Negativo: {stats['negativo']}")
            print(f"Neutral: {stats['neutral']}")
            print(f"Saltados: {stats['skipped']}")
            print(f"Total anotados: {total_annotated}")
    
    def export_annotations(self) -> str:
        """
        Exporta anotaciones a archivo JSON.
        
        Returns:
            Ruta del archivo exportado
        """
        output_path = Path(self.output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Cargar anotaciones existentes si el archivo existe
        existing = []
        if output_path.exists():
            with open(output_path, 'r', encoding='utf-8') as f:
                existing = json.load(f)
        
        # Combinar con nuevas
        all_annotations = existing + self.annotations
        
        # Guardar
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(all_annotations, f, indent=2, ensure_ascii=False)
        
        return str(output_path)
    
    def run_interactive(self, limit: int = 100, resume: bool = False):
        """
        Ejecuta la sesión interactiva de anotación.
        
        Args:
            limit: Número máximo de textos a anotar
            resume: Si continuar desde anotaciones anteriores
        """
        if RICH_AVAILABLE:
            console.print(Panel(
                "[bold]Bienvenido al Sistema de Anotación de Sentimientos[/bold]\n\n"
                "Este sistema te permitirá clasificar textos para entrenar\n"
                "el modelo de análisis de sentimientos BETO.\n\n"
                "[dim]Presiona 'h' en cualquier momento para ver ayuda.[/dim]",
                title="Sistema OSINT EMI"
            ))
        else:
            print("\n=== Sistema de Anotación de Sentimientos ===")
            print("Clasifica textos para entrenar el modelo BETO.")
        
        # Obtener nombre del anotador
        if RICH_AVAILABLE:
            self.annotator = Prompt.ask("Tu nombre", default=self.annotator)
        else:
            name = input(f"Tu nombre [{self.annotator}]: ").strip()
            if name:
                self.annotator = name
        
        # Obtener textos
        if RICH_AVAILABLE:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                progress.add_task("Cargando textos...", total=None)
                texts = self.get_unannotated_texts(limit)
        else:
            print("Cargando textos...")
            texts = self.get_unannotated_texts(limit)
        
        if not texts:
            print("\n¡No hay textos pendientes de anotar!")
            return
        
        print(f"\nSe encontraron {len(texts)} textos para anotar.")
        
        # Proceso de anotación
        for i, text_data in enumerate(texts, 1):
            self.display_text(text_data, i, len(texts))
            
            while True:
                response = self.get_user_input()
                
                if response == 'q':
                    print("\nGuardando y saliendo...")
                    break
                
                if response == 'h':
                    self.show_help()
                    self.display_text(text_data, i, len(texts))
                    continue
                
                if response == 's':
                    self.session_stats['skipped'] += 1
                    break
                
                if response in self.SENTIMENT_MAP:
                    sentiment = self.SENTIMENT_MAP[response]
                    
                    # Pedir confianza (opcional)
                    confidence = 'alta'
                    
                    # Guardar
                    self.save_annotation(
                        text_data['id'],
                        text_data['texto_original'] or text_data['texto_limpio'],
                        sentiment,
                        confidence
                    )
                    
                    # Actualizar stats
                    self.session_stats['total'] += 1
                    self.session_stats[sentiment.lower()] += 1
                    
                    if RICH_AVAILABLE:
                        console.print(f"[green]✓ Guardado como {sentiment}[/green]")
                    else:
                        print(f"✓ Guardado como {sentiment}")
                    
                    break
                else:
                    if RICH_AVAILABLE:
                        console.print("[red]Opción no válida. Usa p/n/u/s/q/h[/red]")
                    else:
                        print("Opción no válida. Usa p/n/u/s/q/h")
            
            if response == 'q':
                break
        
        # Mostrar estadísticas
        self.show_stats()
        
        # Exportar
        if self.annotations:
            export_path = self.export_annotations()
            if RICH_AVAILABLE:
                console.print(f"\n[green]Anotaciones exportadas a: {export_path}[/green]")
            else:
                print(f"\nAnotaciones exportadas a: {export_path}")
        
        print("\n¡Gracias por tu contribución!")


def main():
    """Punto de entrada principal."""
    parser = argparse.ArgumentParser(
        description='Herramienta de anotación de sentimientos para OSINT EMI'
    )
    parser.add_argument(
        '--limit', '-l',
        type=int,
        default=100,
        help='Número máximo de textos a anotar (default: 100)'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        help='Archivo de salida para exportar anotaciones'
    )
    parser.add_argument(
        '--db', '-d',
        type=str,
        default='data/osint_emi.db',
        help='Ruta a la base de datos'
    )
    parser.add_argument(
        '--annotator', '-a',
        type=str,
        help='Nombre del anotador'
    )
    parser.add_argument(
        '--resume', '-r',
        action='store_true',
        help='Continuar desde sesión anterior'
    )
    parser.add_argument(
        '--export-format',
        type=str,
        choices=['json', 'csv'],
        default='json',
        help='Formato de exportación'
    )
    
    args = parser.parse_args()
    
    # Crear anotador
    annotator = SentimentAnnotator(
        db_path=args.db,
        output_file=args.output,
        annotator_name=args.annotator
    )
    
    # Ejecutar
    try:
        annotator.run_interactive(
            limit=args.limit,
            resume=args.resume
        )
    except KeyboardInterrupt:
        print("\n\nSesión interrumpida por el usuario.")
        annotator.show_stats()
        if annotator.annotations:
            annotator.export_annotations()


if __name__ == '__main__':
    main()
