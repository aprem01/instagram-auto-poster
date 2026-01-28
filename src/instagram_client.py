import json
import logging
import random
import time
from pathlib import Path
from typing import Optional

from instagrapi import Client
from instagrapi.exceptions import LoginRequired, ChallengeRequired
from instagrapi.types import Media

logger = logging.getLogger(__name__)


class InstagramClient:
    """Handles Instagram API interactions using instagrapi."""

    def __init__(
        self,
        username: str,
        password: str,
        session_file: Path,
        proxy_url: Optional[str] = None,
    ):
        self.username = username
        self.password = password
        self.session_file = session_file
        self.proxy_url = proxy_url
        self.client = Client()

        if proxy_url:
            self.client.set_proxy(proxy_url)

        # Set realistic device settings
        self.client.set_device(
            {
                "app_version": "269.0.0.18.75",
                "android_version": 31,
                "android_release": "12.0",
                "dpi": "480dpi",
                "resolution": "1080x2400",
                "manufacturer": "Google",
                "device": "Pixel 6",
                "model": "Pixel 6",
                "cpu": "arm64-v8a",
                "version_code": "314665256",
            }
        )

        # Add delays to mimic human behavior
        self.client.delay_range = [2, 5]

    def login(self) -> bool:
        """Login to Instagram with session persistence."""
        try:
            # Try to load existing session
            if self.session_file.exists():
                logger.info("Loading existing session...")
                session_data = json.loads(self.session_file.read_text())
                self.client.set_settings(session_data)

                try:
                    self.client.login(self.username, self.password)
                    logger.info("Logged in using saved session")
                    return True
                except LoginRequired:
                    logger.warning("Session expired, performing fresh login...")

            # Fresh login
            logger.info("Performing fresh login...")
            self.client.login(self.username, self.password)

            # Save session for future use
            self._save_session()
            logger.info("Login successful, session saved")
            return True

        except ChallengeRequired as e:
            logger.error(f"Instagram challenge required: {e}")
            logger.error("Please complete the challenge manually in a browser")
            return False
        except Exception as e:
            logger.error(f"Login failed: {e}")
            return False

    def _save_session(self):
        """Save current session to file."""
        session_data = self.client.get_settings()
        self.session_file.write_text(json.dumps(session_data, indent=2))

    def _random_delay(self, min_sec: int = 2, max_sec: int = 5):
        """Add random delay to mimic human behavior."""
        delay = random.uniform(min_sec, max_sec)
        time.sleep(delay)

    def post_image(self, image_path: Path, caption: str) -> Optional[Media]:
        """Post a single image with caption."""
        try:
            self._random_delay()
            logger.info(f"Posting image: {image_path}")
            media = self.client.photo_upload(str(image_path), caption)
            logger.info(f"Successfully posted image. Media ID: {media.pk}")
            self._save_session()
            return media
        except Exception as e:
            logger.error(f"Failed to post image: {e}")
            return None

    def post_carousel(
        self, image_paths: list[Path], caption: str
    ) -> Optional[Media]:
        """Post multiple images as a carousel."""
        try:
            self._random_delay()
            logger.info(f"Posting carousel with {len(image_paths)} images")
            paths = [str(p) for p in image_paths]
            media = self.client.album_upload(paths, caption)
            logger.info(f"Successfully posted carousel. Media ID: {media.pk}")
            self._save_session()
            return media
        except Exception as e:
            logger.error(f"Failed to post carousel: {e}")
            return None

    def post_reel(
        self, video_path: Path, caption: str, thumbnail_path: Optional[Path] = None
    ) -> Optional[Media]:
        """Post a video as a reel."""
        try:
            self._random_delay()
            logger.info(f"Posting reel: {video_path}")
            thumbnail = str(thumbnail_path) if thumbnail_path else None
            media = self.client.clip_upload(str(video_path), caption, thumbnail)
            logger.info(f"Successfully posted reel. Media ID: {media.pk}")
            self._save_session()
            return media
        except Exception as e:
            logger.error(f"Failed to post reel: {e}")
            return None

    def get_trending_hashtags(self, seed_hashtag: str, limit: int = 10) -> list[str]:
        """Get related/trending hashtags based on a seed hashtag."""
        try:
            self._random_delay()
            hashtag_info = self.client.hashtag_info(seed_hashtag.lstrip("#"))
            related = self.client.hashtag_related_hashtags(seed_hashtag.lstrip("#"))
            trending = [f"#{h.name}" for h in related[:limit]]
            logger.info(f"Found {len(trending)} related hashtags for {seed_hashtag}")
            return trending
        except Exception as e:
            logger.error(f"Failed to get trending hashtags: {e}")
            return []

    def get_account_posts(self, limit: int = 10) -> list[dict]:
        """Get recent posts from own account for style analysis."""
        try:
            self._random_delay()
            user_id = self.client.user_id
            medias = self.client.user_medias(user_id, limit)
            posts = []
            for media in medias:
                posts.append(
                    {
                        "caption": media.caption_text or "",
                        "media_type": media.media_type,
                        "like_count": media.like_count,
                        "comment_count": media.comment_count,
                        "taken_at": media.taken_at,
                    }
                )
            logger.info(f"Retrieved {len(posts)} recent posts for style analysis")
            return posts
        except Exception as e:
            logger.error(f"Failed to get account posts: {e}")
            return []

    def get_niche_content(self, hashtag: str, limit: int = 20) -> list[dict]:
        """Get recent posts from a hashtag for trend analysis."""
        try:
            self._random_delay()
            medias = self.client.hashtag_medias_recent(hashtag.lstrip("#"), limit)
            content = []
            for media in medias:
                content.append(
                    {
                        "caption": media.caption_text or "",
                        "like_count": media.like_count,
                        "comment_count": media.comment_count,
                    }
                )
            return content
        except Exception as e:
            logger.error(f"Failed to get niche content: {e}")
            return []
