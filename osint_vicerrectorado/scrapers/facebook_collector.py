"""
FacebookCollector - Recolector de datos de Facebook vía Apify
Sistema de Analítica EMI

Proceso de 2 fases:
  Fase 1: Extraer posts de la página (apify/facebook-posts-scraper)
  Fase 2: Extraer TODOS los comentarios de cada post (apify/facebook-comments-scraper)

Páginas objetivo:
- https://www.facebook.com/profile.php?id=61574626396439 (EMI Oficial)
- https://www.facebook.com/EMI.UALP (EMI UALP)

Autor: Sistema OSINT EMI
Fecha: Mayo 2026
"""

import re
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from scrapers.base_collector import BaseCollector


class FacebookCollector(BaseCollector):
    """
    Collector de Facebook que usa Apify para recolectar posts y comentarios.

    Attributes:
        page_name (str): Nombre descriptivo de la página
        page_id (str): ID o nombre de la página de Facebook
    """

    def __init__(self, page_url: str, page_name: str, config: dict = None):
        """
        Inicializa el collector de Facebook.

        Args:
            page_url: URL de la página de Facebook
            page_name: Nombre descriptivo de la página
            config: Configuración del sistema
        """
        super().__init__(
            source_name='Facebook',
            source_url=page_url,
            config=config or {}
        )
        self.page_name = page_name
        self.page_id = self._extract_page_id(page_url)

        self.logger.info(
            f"FacebookCollector inicializado para: {page_name} (ID: {self.page_id})"
        )

    def _extract_page_id(self, url: str) -> str:
        """
        Extrae el ID o nombre de la página desde la URL.

        Args:
            url: URL de la página de Facebook

        Returns:
            ID o nombre de la página
        """
        # Patrón para profile.php?id=XXXXX
        id_match = re.search(r'profile\.php\?id=(\d+)', url)
        if id_match:
            return id_match.group(1)

        # Patrón para facebook.com/PAGENAME
        name_match = re.search(r'facebook\.com/([^/?]+)', url)
        if name_match:
            return name_match.group(1)

        return 'unknown'

    def collect_data(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Recolecta posts de Facebook con TODOS sus comentarios.

        Proceso:
          1. Extrae hasta `limit` posts de la página
          2. Para cada post que tenga comentarios, extrae los comentarios
             usando el actor facebook-comments-scraper

        Args:
            limit: Número máximo de posts a recolectar

        Returns:
            Lista de posts normalizados con comentarios incluidos
        """
        from scrapers.apify_keys import (
            create_client_with_fallback, create_fallback_client,
            is_quota_error
        )

        try:
            client, api_key = create_client_with_fallback(
                self.config, 'facebook'
            )
        except ValueError as e:
            self.logger.warning(str(e))
            return []

        # ===== FASE 1: Extraer posts =====
        self.logger.info(
            f"[Fase 1/2] Extrayendo hasta {limit} posts de '{self.page_name}'..."
        )

        try:
            run = client.actor("apify/facebook-posts-scraper").call(run_input={
                "startUrls": [{"url": self.source_url}],
                "resultsLimit": limit,
            })

            if run.get('status') != 'SUCCEEDED':
                error_msg = run.get('statusMessage', '')
                self.logger.error(
                    f"Apify Posts run falló: {run.get('status')} - {error_msg}"
                )
                
                # Intentar con fallback si es error de cuota/memoria
                if is_quota_error(Exception(error_msg)):
                    self.logger.info("Intentando con API key de fallback...")
                    fallback = create_fallback_client(self.config, 'facebook')
                    if fallback:
                        client, _ = fallback
                        run = client.actor("apify/facebook-posts-scraper").call(
                            run_input={
                                "startUrls": [{"url": self.source_url}],
                                "resultsLimit": limit,
                            }
                        )
                        if run.get('status') != 'SUCCEEDED':
                            return []
                    else:
                        return []
                else:
                    return []

            raw_posts = client.dataset(run["defaultDatasetId"]).list_items().items
            self.logger.info(f"Fase 1 completada: {len(raw_posts)} posts extraídos")

        except Exception as e:
            self.logger.error(f"Error en Fase 1 (posts): {e}")
            
            # Intentar con fallback
            if is_quota_error(e):
                self.logger.info("Intentando con API key de fallback...")
                fallback = create_fallback_client(self.config, 'facebook')
                if fallback:
                    client, _ = fallback
                    try:
                        run = client.actor("apify/facebook-posts-scraper").call(
                            run_input={
                                "startUrls": [{"url": self.source_url}],
                                "resultsLimit": limit,
                            }
                        )
                        if run.get('status') != 'SUCCEEDED':
                            return []
                        raw_posts = client.dataset(
                            run["defaultDatasetId"]
                        ).list_items().items
                        self.logger.info(
                            f"Fase 1 completada (fallback): "
                            f"{len(raw_posts)} posts"
                        )
                    except Exception as e2:
                        self.logger.error(f"Fallback también falló: {e2}")
                        return []
                else:
                    return []
            else:
                return []

        # ===== FASE 2: Extraer comentarios de cada post =====
        # Recolectar URLs de posts que tienen comentarios
        post_urls_with_comments = []
        for post in raw_posts:
            comment_count = post.get('comments', 0)
            post_url = post.get('url') or post.get('topLevelUrl', '')
            if comment_count and comment_count > 0 and post_url:
                post_urls_with_comments.append(post_url)

        all_comments = {}  # Mapa: post_url -> lista de comentarios

        if post_urls_with_comments:
            self.logger.info(
                f"[Fase 2/2] Extrayendo comentarios de {len(post_urls_with_comments)} posts..."
            )
            try:
                all_comments = self._extract_comments_batch(
                    client, post_urls_with_comments
                )
                total_comments = sum(len(c) for c in all_comments.values())
                self.logger.info(
                    f"Fase 2 completada: {total_comments} comentarios extraídos "
                    f"de {len(all_comments)} posts"
                )
            except Exception as e:
                self.logger.warning(
                    f"Fase 2 (comentarios) falló parcialmente: {e}. "
                    f"Posts se guardan sin comentarios."
                )
        else:
            self.logger.info(
                "[Fase 2/2] Ningún post tiene comentarios, saltando fase 2"
            )

        # ===== Normalizar todo =====
        normalized = []
        for post in raw_posts:
            post_url = post.get('url') or post.get('topLevelUrl', '')
            post_comments = all_comments.get(post_url, [])
            normalized.append(self._normalize_apify_post(post, post_comments))

        return normalized

    def _extract_comments_batch(
        self, client, post_urls: List[str]
    ) -> Dict[str, List[Dict]]:
        """
        Extrae comentarios de múltiples posts usando facebook-comments-scraper.
        
        Envía todas las URLs en una sola ejecución del actor para eficiencia.

        Args:
            client: ApifyClient configurado
            post_urls: Lista de URLs de posts

        Returns:
            Dict mapeando URL del post -> lista de comentarios crudos
        """
        self.logger.info(
            f"Ejecutando facebook-comments-scraper para {len(post_urls)} posts..."
        )

        run = client.actor("apify/facebook-comments-scraper").call(run_input={
            "startUrls": [{"url": url} for url in post_urls],
            "resultsLimit": 200,  # Max comentarios por post
            "includeNestedComments": True,
        })

        if run.get('status') != 'SUCCEEDED':
            self.logger.error(
                f"Comments scraper falló: {run.get('status')}"
            )
            return {}

        raw_comments = client.dataset(run["defaultDatasetId"]).list_items().items

        # Agrupar comentarios por post URL
        comments_by_post = {}
        for comment in raw_comments:
            # El scraper incluye la URL del post en cada comentario
            post_url = comment.get('postUrl', '') or comment.get('facebookUrl', '')
            
            # Intentar matchear con nuestras URLs
            matched_url = None
            for url in post_urls:
                if post_url and (
                    url in post_url or post_url in url or
                    self._urls_match(url, post_url)
                ):
                    matched_url = url
                    break
            
            if not matched_url and post_urls:
                # Si no podemos matchear, asignar al primer post como fallback
                # (en caso de que el scraper no devuelva URLs exactas)
                matched_url = post_url or post_urls[0]

            if matched_url:
                if matched_url not in comments_by_post:
                    comments_by_post[matched_url] = []
                comments_by_post[matched_url].append(comment)

        return comments_by_post

    @staticmethod
    def _urls_match(url1: str, url2: str) -> bool:
        """Compara dos URLs de Facebook de forma flexible."""
        # Extraer el identificador del post de cada URL
        def extract_id(url):
            # pfbid... format
            match = re.search(r'(pfbid\w+)', url)
            if match:
                return match.group(1)
            # /posts/XXXX format
            match = re.search(r'/posts/(\d+)', url)
            if match:
                return match.group(1)
            # /reel/XXXX format
            match = re.search(r'/reel/(\d+)', url)
            if match:
                return match.group(1)
            return url

        return extract_id(url1) == extract_id(url2)

    def _normalize_apify_post(
        self, raw: Dict, comments: List[Dict] = None
    ) -> Dict[str, Any]:
        """
        Normaliza un post de Apify al formato estándar del sistema.

        Field mapping (verified from live Apify output):
            text         -> contenido_original
            likes        -> engagement_likes
            comments     -> engagement_comments (int, not list)
            shares       -> engagement_shares
            viewsCount   -> engagement_views
            time         -> fecha_publicacion
            postId       -> id_externo
            user.name    -> autor
            isVideo      -> tipo_contenido
            url          -> url_publicacion
        """
        post_id = str(raw.get('postId', '') or raw.get('id', ''))
        comments = comments or []

        # Extraer fecha
        fecha = raw.get('time')
        if isinstance(fecha, str):
            try:
                fecha = datetime.fromisoformat(fecha.replace('Z', '+00:00'))
            except (ValueError, TypeError):
                fecha = datetime.now()
        elif not fecha:
            fecha = datetime.now()

        # Normalizar comentarios
        comentarios_normalizados = []
        for c in comments:
            comentarios_normalizados.append({
                'autor': (
                    c.get('profileName') or
                    c.get('name') or
                    c.get('authorName') or
                    'Anónimo'
                ),
                'texto': c.get('text', '') or c.get('comment', '') or '',
                'fecha': str(
                    c.get('date') or
                    c.get('timestamp') or
                    c.get('time') or
                    ''
                ),
                'likes': (
                    c.get('likesCount') or
                    c.get('reactionsCount') or
                    c.get('likes') or
                    0
                ),
                'is_reply': bool(c.get('parentCommentId')),
            })

        return {
            'id_externo': self.generate_external_id('fb', post_id),
            'contenido_original': (raw.get('text', '') or '')[:5000],
            'fecha_publicacion': fecha,
            'autor': raw.get('user', {}).get('name', self.page_name),
            'engagement_likes': self.normalize_engagement(
                raw.get('likes', 0)
            ),
            'engagement_comments': self.normalize_engagement(
                raw.get('comments', 0)
            ),
            'engagement_shares': self.normalize_engagement(
                raw.get('shares', 0)
            ),
            'engagement_views': self.normalize_engagement(
                raw.get('viewsCount', 0)
            ),
            'tipo_contenido': self._detect_content_type(raw),
            'url_publicacion': raw.get('url', '') or raw.get('topLevelUrl', self.source_url),
            'metadata_json': {
                'platform': 'facebook',
                'page_id': self.page_id,
                'page_name': self.page_name,
                'post_id': post_id,
                'facebook_id': raw.get('facebookId', ''),
                'has_media': bool(raw.get('media')),
                'is_video': raw.get('isVideo', False),
                'reaction_like': raw.get('reactionLikeCount', 0),
                'reaction_love': raw.get('reactionLoveCount', 0),
                'reaction_care': raw.get('reactionCareCount', 0),
                'comentarios': comentarios_normalizados,
                'num_comentarios_extraidos': len(comentarios_normalizados),
                'scrape_method': 'apify',
                'scrape_timestamp': datetime.now().isoformat()
            }
        }

    @staticmethod
    def _detect_content_type(raw: Dict) -> str:
        """Detecta el tipo de contenido del post."""
        if raw.get('isVideo'):
            return 'video'
        if raw.get('media'):
            return 'imagen'
        return 'texto'
