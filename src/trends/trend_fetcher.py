import random
from typing import List, Dict, Optional
from pytrends.request import TrendReq
from src.utils.logger import setup_logger


class TrendFetcher:
    """Fetches trending topics from various sources."""

    def __init__(self, geo: str = "US", language: str = "en-US", niche: str = None):
        """
        Initialize the trend fetcher.

        Args:
            geo: Geographic region for trends (e.g., "US", "GB", "IN")
            language: Language for trends (e.g., "en-US")
            niche: Optional niche to filter trends
        """
        self.geo = geo
        self.language = language
        self.niche = niche
        self.logger = setup_logger("TrendFetcher")

        # Initialize pytrends
        self.pytrends = TrendReq(hl=language, tz=360)

    def get_trending_topics(self, limit: int = 5) -> List[Dict]:
        """
        Fetch current trending topics from Google Trends.

        Args:
            limit: Maximum number of trends to return

        Returns:
            List of trending topics with metadata
        """
        self.logger.info(f"Fetching trending topics for {self.geo}...")

        try:
            # Get trending searches (daily trends)
            trending_searches = self.pytrends.trending_searches(pn=self.geo.lower())

            if trending_searches.empty:
                self.logger.warning("No trending searches found, using fallback")
                return self._get_fallback_trends(limit)

            # Convert to list of dicts
            trends = []
            for idx, row in trending_searches.head(limit * 2).iterrows():
                topic = row[0] if isinstance(row, tuple) else str(row.values[0])
                trends.append({
                    "topic": topic,
                    "source": "google_trends",
                    "rank": idx + 1
                })

            # Filter by niche if specified
            if self.niche:
                trends = self._filter_by_niche(trends)

            self.logger.info(f"Found {len(trends[:limit])} trending topics")
            return trends[:limit]

        except Exception as e:
            self.logger.error(f"Error fetching trends: {e}")
            return self._get_fallback_trends(limit)

    def get_related_topics(self, keyword: str) -> List[str]:
        """
        Get topics related to a specific keyword.

        Args:
            keyword: The keyword to find related topics for

        Returns:
            List of related topic strings
        """
        try:
            self.pytrends.build_payload([keyword], cat=0, timeframe="now 7-d", geo=self.geo)
            related = self.pytrends.related_topics()

            if keyword in related and "rising" in related[keyword]:
                rising_df = related[keyword]["rising"]
                if rising_df is not None and not rising_df.empty:
                    return rising_df["topic_title"].tolist()[:5]

            return []

        except Exception as e:
            self.logger.error(f"Error fetching related topics: {e}")
            return []

    def get_interest_over_time(self, keywords: List[str]) -> Dict:
        """
        Get interest over time for specific keywords.

        Args:
            keywords: List of keywords to analyze

        Returns:
            Dictionary with interest data
        """
        try:
            self.pytrends.build_payload(keywords[:5], cat=0, timeframe="now 7-d", geo=self.geo)
            interest = self.pytrends.interest_over_time()

            if interest.empty:
                return {}

            return interest.to_dict()

        except Exception as e:
            self.logger.error(f"Error fetching interest data: {e}")
            return {}

    def _filter_by_niche(self, trends: List[Dict]) -> List[Dict]:
        """
        Filter trends to match the channel's niche.
        This is a simple keyword-based filter - can be enhanced with ML.

        Args:
            trends: List of trend dictionaries

        Returns:
            Filtered list of trends
        """
        niche_keywords = {
            "tech": ["ai", "tech", "app", "software", "google", "apple", "microsoft", "crypto", "bitcoin", "startup", "iphone", "android"],
            "fitness": ["fitness", "workout", "gym", "health", "diet", "weight", "muscle", "yoga", "running", "exercise"],
            "travel": ["travel", "vacation", "trip", "destination", "hotel", "flight", "beach", "adventure", "tourism"],
            "business": ["business", "entrepreneur", "startup", "money", "finance", "investment", "stock", "market", "economy"],
            "entertainment": ["movie", "music", "celebrity", "tv", "show", "netflix", "streaming", "concert", "festival"],
            "domestic_violence_awareness": ["domestic violence", "abuse", "survivor", "awareness", "support", "healing", "safety", "family", "women", "children", "mental health", "trauma", "recovery"]
        }

        keywords = niche_keywords.get(self.niche.lower(), [])

        if not keywords:
            return trends

        filtered = []
        for trend in trends:
            topic_lower = trend["topic"].lower()
            if any(kw in topic_lower for kw in keywords):
                filtered.append(trend)

        # If no matches, return original trends (better than nothing)
        return filtered if filtered else trends

    def _get_fallback_trends(self, limit: int) -> List[Dict]:
        """
        Return fallback trends when API fails.

        Args:
            limit: Number of trends to return

        Returns:
            List of fallback trend topics
        """
        fallback_topics = {
            "tech": ["AI innovations", "Tech trends 2024", "Startup success stories", "Future of technology", "Digital transformation"],
            "fitness": ["Home workout tips", "Healthy eating habits", "Fitness motivation", "Wellness trends", "Mental health tips"],
            "travel": ["Hidden travel gems", "Budget travel tips", "Adventure destinations", "Travel photography", "Local experiences"],
            "business": ["Entrepreneurship tips", "Business growth strategies", "Investment insights", "Market analysis", "Leadership skills"],
            "entertainment": ["Trending movies", "Music releases", "Celebrity news", "Streaming picks", "Pop culture moments"],
            "domestic_violence_awareness": [
                "We see you, we believe you, and we are here for you",
                "Free confidential support available in Chester County",
                "Your journey to healing starts with one step",
                "How we help survivors reclaim their happiness",
                "Signs that someone you love may need help",
                "Self-care tips for survivors on the healing journey",
                "Thank you Chester County for supporting our mission",
                "What to expect when you reach out for help",
                "Building healthy relationships after trauma",
                "Our counselors are here to listen without judgment",
                "Financial resources available for survivors",
                "You deserve to feel safe - help is available",
                "Supporting a loved one through domestic violence",
                "Children deserve to grow up in safe homes",
                "Every survivor has a story of strength",
                "Community spotlight - partners making a difference",
                "Your safety matters - creating an exit plan",
                "Hope lives here at DVCCC"
            ]
        }

        topics = fallback_topics.get(self.niche, fallback_topics["tech"]) if self.niche else fallback_topics["tech"]

        return [
            {"topic": topic, "source": "fallback", "rank": idx + 1}
            for idx, topic in enumerate(random.sample(topics, min(limit, len(topics))))
        ]
