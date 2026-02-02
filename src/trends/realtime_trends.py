"""
Real-Time Trends Service for DVCCC Discovery Optimizer

Fetches trending topics from:
1. Google Trends (pytrends) - Search interest data
2. NewsAPI - Current news headlines
3. Curated DV awareness calendar
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import requests

# Google Trends
try:
    from pytrends.request import TrendReq
    PYTRENDS_AVAILABLE = True
except ImportError:
    PYTRENDS_AVAILABLE = False

logger = logging.getLogger(__name__)


class RealtimeTrends:
    """Fetches real-time trending topics relevant to DV awareness."""

    # DV-related search terms to monitor
    DV_KEYWORDS = [
        'domestic violence help',
        'abusive relationship',
        'teen dating violence',
        'healthy relationships',
        'relationship red flags',
        'emotional abuse signs',
        'leaving abusive relationship',
        'domestic violence hotline',
        'relationship abuse',
        'controlling relationship'
    ]

    # Awareness calendar for timely content
    AWARENESS_CALENDAR = {
        1: {'name': 'Stalking Awareness Month', 'hashtag': '#StalkingAwareness', 'topic': 'Stalking prevention and safety'},
        2: {'name': 'Teen Dating Violence Awareness Month', 'hashtag': '#TDVAM', 'topic': 'Teen dating violence warning signs'},
        4: {'name': 'Sexual Assault Awareness Month', 'hashtag': '#SAAM', 'topic': 'Sexual assault prevention'},
        10: {'name': 'Domestic Violence Awareness Month', 'hashtag': '#DVAM', 'topic': 'Domestic violence awareness'},
    }

    # Special days
    SPECIAL_DAYS = [
        {'month': 3, 'day': 8, 'name': "International Women's Day", 'hashtag': '#IWD'},
        {'month': 10, 'day': 1, 'name': 'Day of Remembrance', 'hashtag': '#RememberDV'},
        {'month': 11, 'day': 25, 'name': 'Int\'l Day for Elimination of Violence Against Women', 'hashtag': '#OrangeTheWorld'},
    ]

    def __init__(self, news_api_key: Optional[str] = None):
        """Initialize trends service."""
        self.news_api_key = news_api_key or os.getenv('NEWS_API_KEY')
        self.pytrends = None
        self._cache = {}
        self._cache_expiry = {}

        if PYTRENDS_AVAILABLE:
            try:
                self.pytrends = TrendReq(hl='en-US', tz=300)
                logger.info("Google Trends initialized successfully")
            except Exception as e:
                logger.warning(f"Could not initialize Google Trends: {e}")

    def get_all_trends(self) -> List[Dict]:
        """Get combined trending topics from all sources."""
        trends = []

        # 1. Get awareness calendar trends (always relevant)
        calendar_trends = self._get_calendar_trends()
        trends.extend(calendar_trends)

        # 2. Get Google Trends data
        google_trends = self._get_google_trends()
        trends.extend(google_trends)

        # 3. Get news trends
        news_trends = self._get_news_trends()
        trends.extend(news_trends)

        # 4. Add evergreen topics if we need more
        if len(trends) < 5:
            evergreen = self._get_evergreen_trends()
            trends.extend(evergreen)

        # Sort by score and deduplicate
        seen_topics = set()
        unique_trends = []
        for trend in sorted(trends, key=lambda x: x.get('trending_score', 0), reverse=True):
            topic_key = trend['topic'].lower()[:30]
            if topic_key not in seen_topics:
                seen_topics.add(topic_key)
                unique_trends.append(trend)

        return unique_trends[:10]

    def _get_calendar_trends(self) -> List[Dict]:
        """Get trends based on awareness calendar."""
        trends = []
        now = datetime.now()
        current_month = now.month
        current_day = now.day

        # Check monthly awareness
        if current_month in self.AWARENESS_CALENDAR:
            awareness = self.AWARENESS_CALENDAR[current_month]
            trends.append({
                'topic': awareness['topic'],
                'hashtag': awareness['hashtag'],
                'source': 'awareness_calendar',
                'reason': f"{awareness['name']} - This month!",
                'trending_score': 98,  # High priority for current awareness months
                'audience': 'general',
                'timely': True
            })

        # Check special days (within 7 days)
        for day in self.SPECIAL_DAYS:
            try:
                special_date = datetime(now.year, day['month'], day['day'])
                days_until = (special_date - now).days
                if -1 <= days_until <= 7:  # Within a week before/after
                    score = 99 if days_until == 0 else max(85, 95 - abs(days_until) * 2)
                    trends.append({
                        'topic': day['name'],
                        'hashtag': day['hashtag'],
                        'source': 'special_day',
                        'reason': 'Today!' if days_until == 0 else f"In {days_until} days" if days_until > 0 else "Yesterday",
                        'trending_score': score,
                        'audience': 'general',
                        'timely': True
                    })
            except ValueError:
                continue

        return trends

    def _get_google_trends(self) -> List[Dict]:
        """Fetch trending searches from Google Trends."""
        cache_key = 'google_trends'

        # Check cache (refresh every 4 hours)
        if self._is_cached(cache_key, hours=4):
            return self._cache.get(cache_key, [])

        if not self.pytrends:
            return []

        trends = []
        try:
            # Get interest over time for DV keywords
            self.pytrends.build_payload(
                self.DV_KEYWORDS[:5],  # API limit
                timeframe='now 7-d',
                geo='US'
            )

            # Get related queries for top keywords
            related = self.pytrends.related_queries()

            for keyword, data in related.items():
                if data and 'rising' in data and data['rising'] is not None:
                    rising = data['rising'].head(3)
                    for _, row in rising.iterrows():
                        query = row.get('query', '')
                        if query and len(query) > 5:
                            trends.append({
                                'topic': query.title(),
                                'hashtag': '#' + ''.join(word.capitalize() for word in query.split()[:3]),
                                'source': 'google_trends',
                                'reason': f"Rising search: +{row.get('value', 'N/A')}%",
                                'trending_score': min(95, 70 + len(trends) * 3),
                                'audience': self._detect_audience(query),
                                'timely': True
                            })

            # Get trending searches in US
            try:
                daily_trends = self.pytrends.trending_searches(pn='united_states')
                # Filter for potentially relevant ones
                dv_related_terms = ['abuse', 'violence', 'relationship', 'safety', 'domestic', 'help']
                for trend in daily_trends[0].head(20).values:
                    if any(term in trend.lower() for term in dv_related_terms):
                        trends.append({
                            'topic': trend,
                            'hashtag': '#' + trend.replace(' ', ''),
                            'source': 'google_daily_trends',
                            'reason': 'Trending today on Google',
                            'trending_score': 90,
                            'audience': 'general',
                            'timely': True
                        })
            except Exception as e:
                logger.debug(f"Could not fetch daily trends: {e}")

            self._set_cache(cache_key, trends)
            logger.info(f"Fetched {len(trends)} trends from Google")

        except Exception as e:
            logger.error(f"Google Trends error: {e}")
            return []

        return trends

    def _get_news_trends(self) -> List[Dict]:
        """Fetch current news about domestic violence."""
        cache_key = 'news_trends'

        # Check cache (refresh every 2 hours)
        if self._is_cached(cache_key, hours=2):
            return self._cache.get(cache_key, [])

        if not self.news_api_key:
            logger.debug("NewsAPI key not configured, skipping news trends")
            return []

        trends = []
        try:
            # Search for DV-related news
            response = requests.get(
                'https://newsapi.org/v2/everything',
                params={
                    'q': '(domestic violence OR dating violence OR relationship abuse) AND (awareness OR help OR support)',
                    'language': 'en',
                    'sortBy': 'publishedAt',
                    'pageSize': 10,
                    'apiKey': self.news_api_key
                },
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                articles = data.get('articles', [])

                for article in articles[:5]:
                    title = article.get('title', '')
                    if title and 'removed' not in title.lower():
                        # Extract key topic from headline
                        topic = self._extract_topic_from_headline(title)
                        if topic:
                            trends.append({
                                'topic': topic,
                                'hashtag': self._generate_hashtag(topic),
                                'source': 'news',
                                'reason': f"In the news: {article.get('source', {}).get('name', 'News')}",
                                'trending_score': 85,
                                'audience': 'general',
                                'timely': True,
                                'url': article.get('url')
                            })

                self._set_cache(cache_key, trends)
                logger.info(f"Fetched {len(trends)} trends from news")

        except Exception as e:
            logger.error(f"News API error: {e}")

        return trends

    def _get_evergreen_trends(self) -> List[Dict]:
        """Return evergreen topics when real-time data is limited."""
        return [
            {
                'topic': 'Healthy Relationship Signs',
                'hashtag': '#HealthyRelationships',
                'source': 'evergreen',
                'reason': 'Always relevant - high engagement',
                'trending_score': 80,
                'audience': 'youth'
            },
            {
                'topic': 'Financial Abuse Awareness',
                'hashtag': '#FinancialAbuse',
                'source': 'evergreen',
                'reason': 'Often overlooked form of abuse',
                'trending_score': 78,
                'audience': 'general'
            },
            {
                'topic': 'Digital Safety Tips',
                'hashtag': '#DigitalSafety',
                'source': 'evergreen',
                'reason': 'Rising concern for young people',
                'trending_score': 82,
                'audience': 'youth'
            },
            {
                'topic': 'Survivor Stories of Strength',
                'hashtag': '#SurvivorStrong',
                'source': 'evergreen',
                'reason': 'High engagement content',
                'trending_score': 75,
                'audience': 'survivors'
            },
            {
                'topic': 'Supporting a Friend in Crisis',
                'hashtag': '#BeThereForThem',
                'source': 'evergreen',
                'reason': 'Helps bystanders take action',
                'trending_score': 77,
                'audience': 'general'
            }
        ]

    def _detect_audience(self, text: str) -> str:
        """Detect target audience from text."""
        text_lower = text.lower()
        if any(w in text_lower for w in ['teen', 'young', 'college', 'student', 'dating']):
            return 'youth'
        if any(w in text_lower for w in ['donate', 'fundrais', 'support', 'give']):
            return 'donors'
        if any(w in text_lower for w in ['survivor', 'victim', 'escape', 'leaving']):
            return 'survivors'
        return 'general'

    def _extract_topic_from_headline(self, headline: str) -> Optional[str]:
        """Extract a usable topic from a news headline."""
        # Skip certain types of headlines
        skip_words = ['murder', 'killed', 'dead', 'death', 'charged', 'arrested', 'court']
        if any(word in headline.lower() for word in skip_words):
            return None

        # Try to extract the key theme
        if 'awareness' in headline.lower():
            return headline.split(':')[0] if ':' in headline else headline[:60]
        if 'support' in headline.lower() or 'help' in headline.lower():
            return headline.split(':')[0] if ':' in headline else headline[:60]

        return None

    def _generate_hashtag(self, topic: str) -> str:
        """Generate a hashtag from a topic."""
        words = topic.replace('-', ' ').replace(':', '').split()
        hashtag = '#' + ''.join(word.capitalize() for word in words[:4] if len(word) > 2)
        return hashtag[:30]  # Limit length

    def _is_cached(self, key: str, hours: int = 1) -> bool:
        """Check if data is cached and not expired."""
        if key not in self._cache_expiry:
            return False
        return datetime.now() < self._cache_expiry[key]

    def _set_cache(self, key: str, data: any, hours: int = 1):
        """Cache data with expiry."""
        self._cache[key] = data
        self._cache_expiry[key] = datetime.now() + timedelta(hours=hours)


# Singleton instance
_trends_service = None


def get_trends_service(news_api_key: Optional[str] = None) -> RealtimeTrends:
    """Get or create trends service singleton."""
    global _trends_service
    if _trends_service is None:
        _trends_service = RealtimeTrends(news_api_key)
    return _trends_service
