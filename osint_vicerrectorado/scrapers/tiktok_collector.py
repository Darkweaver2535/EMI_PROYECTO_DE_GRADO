"""
TikTokCollector - Recolector de datos de TikTok vía Apify
Sistema de Analítica EMI

Proceso de 2 fases:
  Fase 1: Extraer videos del perfil (clockworks/tiktok-scraper)
  Fase 2: Extraer TODOS los comentarios de cada video
          (clockworks/tiktok-comments-scraper)

Perfil objetivo:
- https://www.tiktok.com/@emilapazoficial

Autor: Sistema OSINT EMI
Fecha: Mayo 2026
"""

import re
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from scrapers.base_collector import BaseCollector


class TikTokCollector(BaseCollector):
    """
    Collector de TikTok que usa Apify para recolectar videos y comentarios.

    Attributes:
        account_name (str): Nombre descriptivo de la cuenta
        username (str): Nombre de usuario de TikTok (sin @)
    """

    def __init__(self, profile_url: str, account_name: str, config: dict = None):
        """
        Inicializa el collector de TikTok.

        Args:
            profile_url: URL del perfil de TikTok
            account_name: Nombre descriptivo de la cuenta
            config: Configuración del sistema
        """
        super().__init__(
            source_name='TikTok',
            source_url=profile_url,
            config=config or {}
        )
        self.account_name = account_name
        self.username = self._extract_username(profile_url)

        self.logger.info(
            f"TikTokCollector inicializado para: @{self.username}"
        )

    def _extract_username(self, url: str) -> str:
        """
        Extrae el nombre de usuario desde la URL de TikTok.

        Args:
            url: URL del perfil de TikTok

        Returns:
            Nombre de usuario (sin @)
        """
        match = re.search(r'tiktok\.com/@([^/?]+)', url)
        if match:
            return match.group(1)
        return 'unknown'

    def collect_data(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Recolecta videos de TikTok con TODOS sus comentarios.

        Proceso:
          1. Extrae hasta `limit` videos del perfil
          2. Para cada video que tenga comentarios, extrae los comentarios
             usando clockworks/tiktok-comments-scraper

        Args:
            limit: Número máximo de videos a recolectar

        Returns:
            Lista de videos normalizados con comentarios incluidos
        """
        from scrapers.apify_keys import (
            create_client_with_fallback, create_fallback_client,
            is_quota_error
        )

        try:
            client, api_key = create_client_with_fallback(
                self.config, 'tiktok'
            )
        except ValueError as e:
            self.logger.warning(str(e))
            return []

        # ===== FASE 1: Extraer videos =====
        self.logger.info(
            f"[Fase 1/2] Extrayendo hasta {limit} videos de '@{self.username}'..."
        )

        try:
            run = client.actor("clockworks/tiktok-scraper").call(run_input={
                "profiles": [self.username],
                "resultsPerPage": limit,
                "shouldDownloadVideos": False,
                "shouldDownloadCovers": False,
            })

            if run.get('status') != 'SUCCEEDED':
                error_msg = run.get('statusMessage', '')
                self.logger.error(
                    f"Apify Videos run falló: {run.get('status')} - {error_msg}"
                )
                
                # Intentar con fallback si es error de cuota/memoria
                if is_quota_error(Exception(error_msg)):
                    self.logger.info("Intentando con API key de fallback...")
                    fallback = create_fallback_client(self.config, 'tiktok')
                    if fallback:
                        client, _ = fallback
                        run = client.actor("clockworks/tiktok-scraper").call(
                            run_input={
                                "profiles": [self.username],
                                "resultsPerPage": limit,
                                "shouldDownloadVideos": False,
                                "shouldDownloadCovers": False,
                            }
                        )
                        if run.get('status') != 'SUCCEEDED':
                            return []
                    else:
                        return []
                else:
                    return []

            raw_videos = client.dataset(run["defaultDatasetId"]).list_items().items
            self.logger.info(f"Fase 1 completada: {len(raw_videos)} videos extraídos")

        except Exception as e:
            self.logger.error(f"Error en Fase 1 (videos): {e}")
            
            # Intentar con fallback
            if is_quota_error(e):
                self.logger.info("Intentando con API key de fallback...")
                fallback = create_fallback_client(self.config, 'tiktok')
                if fallback:
                    client, _ = fallback
                    try:
                        run = client.actor("clockworks/tiktok-scraper").call(
                            run_input={
                                "profiles": [self.username],
                                "resultsPerPage": limit,
                                "shouldDownloadVideos": False,
                                "shouldDownloadCovers": False,
                            }
                        )
                        if run.get('status') != 'SUCCEEDED':
                            return []
                        raw_videos = client.dataset(
                            run["defaultDatasetId"]
                        ).list_items().items
                        self.logger.info(
                            f"Fase 1 completada (fallback): "
                            f"{len(raw_videos)} videos"
                        )
                    except Exception as e2:
                        self.logger.error(f"Fallback también falló: {e2}")
                        return []
                else:
                    return []
            else:
                return []

        # ===== FASE 2: Extraer comentarios de cada video =====
        video_urls_with_comments = []
        for video in raw_videos:
            comment_count = video.get('commentCount', 0)
            video_url = video.get('webVideoUrl', '')
            if comment_count and comment_count > 0 and video_url:
                video_urls_with_comments.append(video_url)

        all_comments = {}  # Mapa: video_url -> lista de comentarios

        if video_urls_with_comments:
            self.logger.info(
                f"[Fase 2/2] Extrayendo comentarios de "
                f"{len(video_urls_with_comments)} videos..."
            )
            try:
                all_comments = self._extract_comments_batch(
                    client, video_urls_with_comments
                )
                total_comments = sum(len(c) for c in all_comments.values())
                self.logger.info(
                    f"Fase 2 completada: {total_comments} comentarios extraídos "
                    f"de {len(all_comments)} videos"
                )
            except Exception as e:
                self.logger.warning(
                    f"Fase 2 (comentarios) falló parcialmente: {e}. "
                    f"Videos se guardan sin comentarios."
                )
        else:
            self.logger.info(
                "[Fase 2/2] Ningún video tiene comentarios, saltando fase 2"
            )

        # ===== Normalizar todo =====
        normalized = []
        for video in raw_videos:
            video_url = video.get('webVideoUrl', '')
            video_comments = all_comments.get(video_url, [])
            normalized.append(self._normalize_apify_video(video, video_comments))

        return normalized

    def _extract_comments_batch(
        self, client, video_urls: List[str]
    ) -> Dict[str, List[Dict]]:
        """
        Extrae comentarios de múltiples videos usando
        clockworks/tiktok-comments-scraper.

        Envía todas las URLs en una sola ejecución del actor.

        Args:
            client: ApifyClient configurado
            video_urls: Lista de URLs de videos de TikTok

        Returns:
            Dict mapeando URL del video -> lista de comentarios crudos
        """
        self.logger.info(
            f"Ejecutando tiktok-comments-scraper para "
            f"{len(video_urls)} videos..."
        )

        run = client.actor("clockworks/tiktok-comments-scraper").call(
            run_input={
                "postURLs": video_urls,
                "commentsPerPost": 200,   # Hasta 200 comentarios por video
                "maxRepliesPerComment": 3, # Incluir respuestas
            }
        )

        if run.get('status') != 'SUCCEEDED':
            self.logger.error(
                f"Comments scraper falló: {run.get('status')}"
            )
            return {}

        raw_comments = client.dataset(
            run["defaultDatasetId"]
        ).list_items().items

        # Agrupar comentarios por video URL
        comments_by_video = {}
        for comment in raw_comments:
            # El scraper devuelve la URL del video en cada comentario
            video_url = (
                comment.get('videoWebUrl') or
                comment.get('postUrl') or
                comment.get('videoUrl') or
                ''
            )

            # Intentar matchear con nuestras URLs
            matched_url = None
            for url in video_urls:
                if video_url and (url in video_url or video_url in url):
                    matched_url = url
                    break
                # Comparar por video ID
                vid_id_1 = self._extract_video_id(url)
                vid_id_2 = self._extract_video_id(video_url)
                if vid_id_1 and vid_id_2 and vid_id_1 == vid_id_2:
                    matched_url = url
                    break

            if not matched_url and video_url:
                matched_url = video_url

            if matched_url:
                if matched_url not in comments_by_video:
                    comments_by_video[matched_url] = []
                comments_by_video[matched_url].append(comment)

        return comments_by_video

    @staticmethod
    def _extract_video_id(url: str) -> str:
        """Extrae el ID del video de una URL de TikTok."""
        match = re.search(r'/video/(\d+)', url)
        return match.group(1) if match else ''

    def _normalize_apify_video(
        self, raw: Dict, comments: List[Dict] = None
    ) -> Dict[str, Any]:
        """
        Normaliza un video de Apify al formato estándar del sistema.

        Args:
            raw: Datos crudos del actor de Apify
            comments: Lista de comentarios crudos del comments-scraper

        Returns:
            Dict normalizado con el formato estándar
        """
        video_id = raw.get('id', '') or raw.get('videoId', '')
        comments = comments or []

        # Extraer fecha
        timestamp = raw.get('createTime') or raw.get('createTimeISO')
        if isinstance(timestamp, (int, float)):
            fecha = datetime.fromtimestamp(timestamp)
        elif isinstance(timestamp, str):
            try:
                fecha = datetime.fromisoformat(timestamp)
            except (ValueError, TypeError):
                fecha = datetime.now()
        else:
            fecha = datetime.now()

        # Normalizar comentarios
        comentarios_normalizados = []
        for c in comments:
            # El TikTok comments scraper devuelve campos como:
            # text, uniqueId, nickname, createTime, diggCount, etc.
            autor = (
                c.get('uniqueId') or
                c.get('nickname') or
                c.get('userName') or
                c.get('user', {}).get('uniqueId', '') if isinstance(c.get('user'), dict) else '' or
                'Anónimo'
            )
            texto = c.get('text', '') or c.get('comment', '') or ''
            
            # Fecha del comentario
            c_time = c.get('createTime')
            if isinstance(c_time, (int, float)):
                c_fecha = datetime.fromtimestamp(c_time).isoformat()
            elif isinstance(c_time, str):
                c_fecha = c_time
            else:
                c_fecha = ''

            likes_count = (
                c.get('diggCount') or
                c.get('likesCount') or
                c.get('likes') or
                0
            )

            comentarios_normalizados.append({
                'autor': autor,
                'texto': texto,
                'fecha': c_fecha,
                'likes': likes_count,
                'is_reply': bool(
                    c.get('replyCommentId') or c.get('parentCommentId')
                ),
            })

        # Descripción del video
        descripcion = (
            raw.get('text', '') or
            raw.get('desc', '') or
            raw.get('description', '') or
            f"Video de @{self.username}"
        )

        return {
            'id_externo': self.generate_external_id('tt', video_id),
            'contenido_original': descripcion[:2000],
            'fecha_publicacion': fecha,
            'autor': raw.get('authorMeta', {}).get('name', self.username),
            'engagement_likes': self.normalize_engagement(
                raw.get('diggCount', 0) or raw.get('likesCount', 0)
            ),
            'engagement_comments': self.normalize_engagement(
                raw.get('commentCount', 0) or raw.get('commentsCount', 0)
            ),
            'engagement_shares': self.normalize_engagement(
                raw.get('shareCount', 0) or raw.get('sharesCount', 0)
            ),
            'engagement_views': self.normalize_engagement(
                raw.get('playCount', 0) or raw.get('viewsCount', 0)
            ),
            'tipo_contenido': 'video',
            'url_publicacion': (
                raw.get('webVideoUrl', '') or
                raw.get('url', '') or
                f"https://www.tiktok.com/@{self.username}/video/{video_id}"
            ),
            'metadata_json': {
                'platform': 'tiktok',
                'username': self.username,
                'account_name': self.account_name,
                'video_id': video_id,
                'duration': raw.get('videoMeta', {}).get('duration', 0),
                'views': self.normalize_engagement(
                    raw.get('playCount', 0)
                ),
                'music': raw.get('musicMeta', {}).get('musicName', ''),
                'hashtags': [
                    t.get('name', '') for t in (raw.get('hashtags') or [])
                ],
                'comentarios': comentarios_normalizados,
                'num_comentarios_extraidos': len(comentarios_normalizados),
                'scrape_method': 'apify',
                'scrape_timestamp': datetime.now().isoformat()
            }
        }
