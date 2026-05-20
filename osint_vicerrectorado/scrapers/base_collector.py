"""
BaseCollector - Clase base para recolectores de datos OSINT
Sistema de Analítica EMI

Define la interfaz común que todos los collectors deben implementar.
Cada collector (Facebook, TikTok, etc.) hereda de esta clase.

La recolección se realiza a través de la API de Apify, que maneja
proxies, CAPTCHAs y anti-detección de forma transparente.

Autor: Sistema OSINT EMI
Fecha: Mayo 2026
"""

import logging
import hashlib
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict, Any, Optional


class BaseCollector(ABC):
    """
    Clase base abstracta para todos los collectors de datos OSINT.

    Define la interfaz estándar que cada collector debe implementar.
    Los datos recolectados se normalizan a un formato común antes
    de pasarlos al pipeline ETL.

    Attributes:
        source_name (str): Nombre de la plataforma (ej: 'Facebook', 'TikTok')
        source_url (str): URL de la fuente de datos
        logger (logging.Logger): Logger del collector

    Formato de salida estándar (cada item):
        {
            'id_externo': str,           # ID único generado
            'contenido_original': str,   # Texto del post/video
            'fecha_publicacion': datetime,
            'autor': str,
            'engagement_likes': int,
            'engagement_comments': int,
            'engagement_shares': int,
            'engagement_views': int,     # Solo para videos
            'tipo_contenido': str,       # 'texto', 'imagen', 'video'
            'url_publicacion': str,
            'metadata_json': dict        # Datos adicionales específicos
        }
    """

    def __init__(
        self,
        source_name: str,
        source_url: str,
        config: dict = None
    ):
        """
        Inicializa el collector base.

        Args:
            source_name: Nombre de la plataforma
            source_url: URL de la fuente de datos
            config: Configuración del sistema
        """
        self.source_name = source_name
        self.source_url = source_url
        self.config = config or {}
        self.logger = logging.getLogger(f"OSINT.Collector.{source_name}")

    @abstractmethod
    async def collect_data(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Recolecta datos de la fuente.

        Cada implementación debe llamar a la API de Apify con el
        actor correspondiente y normalizar los resultados.

        Args:
            limit: Número máximo de items a recolectar

        Returns:
            Lista de dicts con el formato estándar definido arriba
        """
        pass

    async def run(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Ejecuta el proceso completo de recolección.

        Args:
            limit: Número máximo de items a recolectar

        Returns:
            Lista de datos recolectados normalizados
        """
        self.logger.info(
            f"Iniciando recolección de {self.source_name}: {self.source_url}"
        )

        try:
            data = await self.collect_data(limit=limit)
            self.logger.info(
                f"Recolección completada: {len(data)} items de {self.source_name}"
            )
            return data
        except Exception as e:
            self.logger.error(
                f"Error en recolección de {self.source_name}: {e}"
            )
            raise

    @staticmethod
    def generate_external_id(platform: str, unique_key: str) -> str:
        """
        Genera un ID externo único y determinista.

        Args:
            platform: Prefijo de plataforma (ej: 'fb', 'tt')
            unique_key: Clave única del item (ej: post_id, video_id)

        Returns:
            ID externo con formato '{platform}_{hash}'
        """
        hash_val = hashlib.md5(
            f"{platform}_{unique_key}".encode()
        ).hexdigest()[:16]
        return f"{platform}_{hash_val}"

    @staticmethod
    def normalize_engagement(value: Any) -> int:
        """
        Normaliza un valor de engagement a entero.

        Args:
            value: Valor de engagement (puede ser int, str, None)

        Returns:
            Valor normalizado como entero
        """
        if value is None:
            return 0
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str):
            # Manejar notación K/M
            value = value.strip().upper()
            try:
                if 'K' in value:
                    return int(float(value.replace('K', '')) * 1_000)
                elif 'M' in value:
                    return int(float(value.replace('M', '')) * 1_000_000)
                return int(float(value))
            except ValueError:
                return 0
        return 0
