import logging
import random
from datetime import datetime
from typing import Optional

from .instagram_client import InstagramClient

logger = logging.getLogger(__name__)


class TrendAnalyzer:
    """Analyzes trends and content for the domestic violence awareness niche."""

    def __init__(self, instagram_client: InstagramClient, default_hashtags: list[str]):
        self.client = instagram_client
        self.default_hashtags = default_hashtags

        # Awareness dates for domestic violence
        self.awareness_dates = {
            (10, 1): "Domestic Violence Awareness Month begins",
            (10, 31): "Domestic Violence Awareness Month ends",
            (2, 14): "V-Day / One Billion Rising",
            (3, 8): "International Women's Day",
            (4, 1): "Sexual Assault Awareness Month begins",
            (11, 25): "International Day for the Elimination of Violence Against Women",
        }

        # Content themes with weights (higher = more frequent)
        self.theme_weights = {
            "awareness_statistics": 15,
            "warning_signs": 15,
            "support_resources": 20,
            "survivor_empowerment": 20,
            "healthy_relationships": 10,
            "community_support": 10,
            "self_care_healing": 10,
        }

    def get_trending_topics(self) -> dict:
        """Analyze current trends and return topic suggestions."""
        trends = {
            "hashtags": self._get_relevant_hashtags(),
            "theme": self._select_content_theme(),
            "special_date": self._check_awareness_date(),
            "engagement_insights": self._analyze_engagement(),
        }
        logger.info(f"Trend analysis complete: theme={trends['theme']}")
        return trends

    def _get_relevant_hashtags(self) -> list[str]:
        """Get a mix of default and trending hashtags."""
        hashtags = self.default_hashtags.copy()

        # Try to get trending related hashtags
        seed_tags = ["domesticviolence", "survivorstrong", "endabuse"]
        for tag in random.sample(seed_tags, min(2, len(seed_tags))):
            try:
                related = self.client.get_trending_hashtags(tag, limit=5)
                hashtags.extend(related)
            except Exception as e:
                logger.warning(f"Could not get trending hashtags for {tag}: {e}")

        # Remove duplicates and limit
        unique_hashtags = list(dict.fromkeys(hashtags))
        return unique_hashtags[:20]

    def _select_content_theme(self) -> str:
        """Select a content theme based on weighted probability."""
        themes = list(self.theme_weights.keys())
        weights = list(self.theme_weights.values())
        selected = random.choices(themes, weights=weights, k=1)[0]
        return selected

    def _check_awareness_date(self) -> Optional[str]:
        """Check if today is a special awareness date."""
        today = datetime.now()
        key = (today.month, today.day)
        return self.awareness_dates.get(key)

    def _analyze_engagement(self) -> dict:
        """Analyze engagement from recent account posts."""
        try:
            posts = self.client.get_account_posts(limit=10)
            if not posts:
                return {"avg_likes": 0, "avg_comments": 0, "top_performing": None}

            avg_likes = sum(p["like_count"] for p in posts) / len(posts)
            avg_comments = sum(p["comment_count"] for p in posts) / len(posts)

            # Find top performing post
            top_post = max(posts, key=lambda p: p["like_count"] + p["comment_count"] * 2)

            return {
                "avg_likes": avg_likes,
                "avg_comments": avg_comments,
                "top_performing_caption": top_post["caption"][:200] if top_post else None,
            }
        except Exception as e:
            logger.warning(f"Could not analyze engagement: {e}")
            return {"avg_likes": 0, "avg_comments": 0, "top_performing": None}

    def get_content_prompt_context(self) -> str:
        """Generate context for AI content generation based on trends."""
        trends = self.get_trending_topics()

        context = f"""
Content Theme: {trends['theme']}

Relevant Hashtags to include (pick 5-10):
{', '.join(trends['hashtags'][:15])}
"""

        if trends["special_date"]:
            context += f"\nSpecial Date Today: {trends['special_date']} - Make the content relevant to this occasion.\n"

        if trends["engagement_insights"].get("top_performing_caption"):
            context += f"""
Top Performing Caption Style Reference:
{trends['engagement_insights']['top_performing_caption']}
"""

        return context
