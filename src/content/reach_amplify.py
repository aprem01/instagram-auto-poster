"""
REACH Amplify - Social Media Discovery Optimizer for DVCCC

Helps maximize discoverability to reach young people in crisis
through optimized hashtags, keywords, alt text, and engagement signals.
"""

import logging
import os
import random
from typing import Dict, List, Optional
from openai import OpenAI
import httpx

# Timeout configuration for OpenAI
OPENAI_TIMEOUT = httpx.Timeout(120.0, connect=30.0)


class ReachAmplify:
    """
    Social media discovery optimizer for DVCCC Instagram content.
    Optimizes hashtags, keywords, alt text, and discoverability signals.
    """

    def __init__(self, api_key: str):
        """Initialize with OpenAI API key."""
        # Support Cloudflare Worker proxy for API calls
        base_url = os.getenv("OPENAI_BASE_URL")
        if base_url:
            self.client = OpenAI(api_key=api_key, base_url=base_url, timeout=OPENAI_TIMEOUT)
        else:
            self.client = OpenAI(api_key=api_key, timeout=OPENAI_TIMEOUT)
        self.logger = logging.getLogger("ReachAmplify")

        # Core hashtag categories for domestic violence awareness
        self.core_hashtags = {
            "awareness": [
                "#DomesticViolenceAwareness", "#DVAwareness", "#EndDomesticViolence",
                "#BreakTheSilence", "#SpeakOut", "#NoMoreSilence", "#DomesticAbuse",
                "#AbuseAwareness", "#StopDomesticViolence", "#PurpleRibbon"
            ],
            "support": [
                "#YouAreNotAlone", "#SurvivorSupport", "#HelpIsAvailable",
                "#SafeSpace", "#SupportSurvivors", "#BelieveSurvivors",
                "#HopeAndHealing", "#BreakTheCycle", "#SeekHelp", "#ThereIsHope"
            ],
            "empowerment": [
                "#SurvivorStrong", "#Empowerment", "#Strength", "#Resilience",
                "#CourageToLeave", "#NewBeginnings", "#HealingJourney",
                "#ReclaimYourLife", "#YouMatter", "#SelfLove"
            ],
            "youth_focused": [
                "#TeenDatingViolence", "#HealthyRelationships", "#RedFlags",
                "#LoveIsRespect", "#DatingAbuse", "#TeenSafety", "#KnowTheSigns",
                "#ToxicRelationships", "#SafeRelationships", "#TeenHelp"
            ],
            "local": [
                "#ChesterCounty", "#ChesterCountyPA", "#DVCCC", "#Pennsylvania",
                "#PAstrong", "#ChesterCountySupport", "#LocalHelp"
            ],
            "mental_health": [
                "#MentalHealth", "#Trauma", "#PTSD", "#Healing", "#Anxiety",
                "#Recovery", "#SelfCare", "#MentalHealthMatters", "#TraumaRecovery"
            ],
            "crisis": [
                "#CrisisHelp", "#GetHelp", "#HotlineHelp", "#EmergencyHelp",
                "#SafetyPlanning", "#ReachOut", "#AskForHelp"
            ]
        }

        # Time-sensitive hashtags (for specific months/days)
        self.special_hashtags = {
            "october": ["#DomesticViolenceAwarenessMonth", "#DVAM", "#PurpleThursday", "#WearPurple"],
            "february": ["#TeenDatingViolenceAwarenessMonth", "#TDVAM", "#LoveIsRespect"],
            "april": ["#SexualAssaultAwarenessMonth", "#SAAM", "#BelieveSurvivors"]
        }

    def optimize_content(self, caption: str, image_prompt: str, topic: str) -> Dict:
        """
        Full discovery optimization for a post with AI & SEO analysis.

        Returns dict with:
        - optimized_caption: Caption with keywords
        - hashtags: Optimized hashtag set
        - alt_text: Accessible image description
        - discovery_score: Estimated reach potential
        - tips: Engagement tips
        - seo_analysis: SEO optimization insights
        - ai_insights: AI-powered content analysis
        - posting_times: Best times to post
        """
        self.logger.info(f"Optimizing content for topic: {topic}")

        # Generate all optimizations
        hashtags = self.generate_hashtags(topic, caption)
        alt_text = self.generate_alt_text(image_prompt)
        keywords = self.extract_keywords(topic)
        optimized_caption = self.optimize_caption(caption, keywords)
        tips = self.get_engagement_tips(topic)
        discovery_score = self._calculate_discovery_score(hashtags, alt_text, optimized_caption)

        # AI & SEO Analysis
        seo_analysis = self.get_seo_analysis(optimized_caption, keywords)
        posting_times = self.get_best_posting_times()

        # AIO/GEO/AEO Optimization
        aio_data = self.get_aio_optimization(optimized_caption, topic)

        return {
            "optimized_caption": optimized_caption,
            "hashtags": hashtags,
            "hashtag_string": " ".join(hashtags),
            "alt_text": alt_text,
            "keywords": keywords,
            "discovery_score": discovery_score,
            "tips": tips,
            "seo_analysis": seo_analysis,
            "posting_times": posting_times,
            "aio_optimization": aio_data
        }

    def generate_hashtags(self, topic: str, caption: str = "", count: int = 20) -> List[str]:
        """
        Generate optimized hashtag mix for maximum discoverability.

        Strategy:
        - 5-7 high-volume awareness hashtags
        - 5-7 niche/specific hashtags
        - 3-5 local Chester County hashtags
        - 3-5 trending/contextual hashtags
        """
        self.logger.info("Generating optimized hashtags")

        try:
            # Use AI to generate contextual hashtags
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": """You are a social media expert for a domestic violence support center.
Generate hashtags that help reach people in need - especially young people searching for help.
Focus on terms a teen or young adult might search when:
- Questioning if their relationship is healthy
- Looking for help or resources
- Feeling scared or trapped
- Seeking support or validation"""
                    },
                    {
                        "role": "user",
                        "content": f"""Generate 10 unique Instagram hashtags for this DVCCC post:
Topic: {topic}
Caption: {caption[:200] if caption else 'N/A'}

Return ONLY hashtags, one per line, including the # symbol.
Mix of:
- Terms young people actually search
- Relationship advice hashtags they might follow
- Mental health hashtags
- Support/help hashtags
Avoid: overly clinical terms, hashtags with low engagement"""
                    }
                ],
                max_tokens=200,
                temperature=0.8
            )

            ai_hashtags = [
                tag.strip() for tag in response.choices[0].message.content.strip().split('\n')
                if tag.strip().startswith('#')
            ][:10]

        except Exception as e:
            self.logger.error(f"Error generating AI hashtags: {e}")
            ai_hashtags = []

        # Build final hashtag set
        final_hashtags = []

        # Add core awareness hashtags (3-4)
        final_hashtags.extend(random.sample(self.core_hashtags["awareness"], min(4, len(self.core_hashtags["awareness"]))))

        # Add support hashtags (3-4)
        final_hashtags.extend(random.sample(self.core_hashtags["support"], min(4, len(self.core_hashtags["support"]))))

        # Add youth-focused hashtags (important for reaching young people)
        final_hashtags.extend(random.sample(self.core_hashtags["youth_focused"], min(3, len(self.core_hashtags["youth_focused"]))))

        # Add local hashtags (2-3)
        final_hashtags.extend(random.sample(self.core_hashtags["local"], min(3, len(self.core_hashtags["local"]))))

        # Add AI-generated contextual hashtags
        final_hashtags.extend(ai_hashtags)

        # Remove duplicates while preserving order
        seen = set()
        unique_hashtags = []
        for tag in final_hashtags:
            tag_lower = tag.lower()
            if tag_lower not in seen:
                seen.add(tag_lower)
                unique_hashtags.append(tag)

        # Limit to count
        return unique_hashtags[:count]

    def generate_alt_text(self, image_prompt: str) -> str:
        """
        Generate accessible alt text for the image.
        Important for:
        - Accessibility (screen readers)
        - SEO/discoverability
        - Instagram's search algorithm
        """
        self.logger.info("Generating alt text for image")

        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": """You write concise, descriptive alt text for images.
Alt text should:
- Describe what's visually in the image (under 125 characters ideal)
- Be helpful for screen reader users
- Include relevant keywords naturally
- NOT start with "Image of" or "Photo of"
- NOT include hashtags or promotional text"""
                    },
                    {
                        "role": "user",
                        "content": f"""Write alt text for an Instagram image.
The image shows: {image_prompt}

Keep it under 125 characters. Be descriptive and accessible."""
                    }
                ],
                max_tokens=60,
                temperature=0.5
            )

            alt_text = response.choices[0].message.content.strip()
            # Clean up any quotes
            alt_text = alt_text.strip('"\'')
            return alt_text[:150]  # Instagram limit is around 100-125 but we allow slightly more

        except Exception as e:
            self.logger.error(f"Error generating alt text: {e}")
            # Fallback: create simple alt text from prompt
            return self._create_fallback_alt_text(image_prompt)

    def _create_fallback_alt_text(self, image_prompt: str) -> str:
        """Create simple alt text from image prompt."""
        # Extract key elements
        prompt_lower = image_prompt.lower()

        if "sunrise" in prompt_lower or "sunset" in prompt_lower:
            return "Warm sunrise over a peaceful landscape symbolizing hope and new beginnings"
        elif "hands" in prompt_lower:
            return "Two hands joined together in a supportive, caring gesture"
        elif "bird" in prompt_lower or "flight" in prompt_lower:
            return "Birds soaring freely against a warm sky, symbolizing freedom"
        elif "tree" in prompt_lower:
            return "Strong oak tree standing resilient, symbolizing strength and growth"
        elif "path" in prompt_lower or "road" in prompt_lower:
            return "A winding path through nature, representing the journey forward"
        elif "candle" in prompt_lower:
            return "Soft candlelight creating a warm, peaceful atmosphere"
        elif "flower" in prompt_lower or "garden" in prompt_lower:
            return "Flowers blooming in natural light, symbolizing growth and renewal"
        else:
            return "Peaceful image representing hope, healing, and support"

    def extract_keywords(self, topic: str) -> List[str]:
        """Extract searchable keywords from topic for caption optimization."""
        self.logger.info("Extracting keywords")

        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": """Extract keywords that someone in need might search for.
Think about what a young person might type into Instagram search when:
- They're in an unhealthy relationship
- They need help but don't know where to start
- They're looking for support or validation"""
                    },
                    {
                        "role": "user",
                        "content": f"""Extract 5-7 searchable keywords from this topic: {topic}

Return only keywords, comma-separated.
Focus on terms young people would actually search."""
                    }
                ],
                max_tokens=50,
                temperature=0.5
            )

            keywords = [k.strip() for k in response.choices[0].message.content.split(',')]
            return keywords[:7]

        except Exception as e:
            self.logger.error(f"Error extracting keywords: {e}")
            return ["support", "help", "healing", "strength", "hope"]

    def optimize_caption(self, caption: str, keywords: List[str]) -> str:
        """
        Optimize caption for discoverability while keeping it authentic.
        Ensures key searchable terms are naturally included.
        """
        # Don't over-optimize - just ensure basic discoverability
        # The caption should remain authentic and emotional

        # Add a call-to-action if not present
        cta_phrases = [
            "\n\n💜 Help is available. You are not alone.",
            "\n\n💜 If you or someone you know needs help, reach out.",
            "\n\n💜 DVCCC is here for you. You matter.",
            "\n\n💜 Support is just a call away. You deserve safety.",
            "\n\n💜 You are stronger than you know. Help is here."
        ]

        # Check if caption already has a CTA
        has_cta = any(phrase in caption.lower() for phrase in ["help is", "reach out", "you are not alone", "call", "here for you"])

        if not has_cta:
            caption = caption.rstrip() + random.choice(cta_phrases)

        return caption

    def get_engagement_tips(self, topic: str) -> List[str]:
        """Get engagement tips for the post."""
        tips = [
            "Post between 11am-1pm or 7pm-9pm for best engagement",
            "Reply to comments within the first hour to boost visibility",
            "Share to Stories with a 'Swipe Up' or link sticker",
            "Use the question sticker in Stories to encourage engagement",
            "Pin supportive/helpful comments to the top"
        ]

        # Add topic-specific tips
        topic_lower = topic.lower()
        if "teen" in topic_lower or "young" in topic_lower:
            tips.append("Consider Reels format - higher reach with younger audiences")
        if "awareness" in topic_lower:
            tips.append("Tag relevant awareness accounts for potential reshares")

        return tips[:5]

    def _calculate_discovery_score(self, hashtags: List[str], alt_text: str, caption: str) -> Dict:
        """Calculate estimated discovery score."""
        score = 0
        breakdown = {}

        # Hashtag score (max 40)
        hashtag_score = min(len(hashtags) * 2, 40)
        breakdown["hashtags"] = hashtag_score
        score += hashtag_score

        # Alt text score (max 20)
        if alt_text and len(alt_text) > 20:
            alt_score = 20
        elif alt_text:
            alt_score = 10
        else:
            alt_score = 0
        breakdown["alt_text"] = alt_score
        score += alt_score

        # Caption score (max 40)
        caption_score = 0
        if len(caption) > 100:
            caption_score += 15
        if "help" in caption.lower() or "support" in caption.lower():
            caption_score += 10
        if "💜" in caption or "❤️" in caption:
            caption_score += 5
        if any(cta in caption.lower() for cta in ["reach out", "call", "here for you"]):
            caption_score += 10
        breakdown["caption"] = min(caption_score, 40)
        score += breakdown["caption"]

        return {
            "total": score,
            "max": 100,
            "grade": self._score_to_grade(score),
            "breakdown": breakdown
        }

    def _score_to_grade(self, score: int) -> str:
        """Convert score to letter grade."""
        if score >= 90:
            return "A+"
        elif score >= 80:
            return "A"
        elif score >= 70:
            return "B"
        elif score >= 60:
            return "C"
        else:
            return "D"

    # ============== AI OPTIMIZATION FEATURES ==============

    def analyze_content_ai(self, caption: str, topic: str) -> Dict:
        """
        AI-powered content analysis for maximum engagement.
        Returns insights on tone, emotional impact, and improvements.
        """
        self.logger.info("Running AI content analysis")

        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": """You are a social media content analyst specializing in
nonprofit and support organization content. Analyze posts for emotional impact,
clarity, and ability to reach people who need help."""
                    },
                    {
                        "role": "user",
                        "content": f"""Analyze this DVCCC Instagram post:

Topic: {topic}
Caption: {caption}

Provide a brief JSON response with:
{{
    "emotional_tone": "hopeful/supportive/urgent/empowering",
    "clarity_score": 1-10,
    "reach_potential": "low/medium/high",
    "strengths": ["strength1", "strength2"],
    "improvements": ["improvement1", "improvement2"],
    "target_audience_fit": "how well it reaches people in need"
}}"""
                    }
                ],
                max_tokens=300,
                temperature=0.5
            )

            content = response.choices[0].message.content.strip()
            # Try to parse as JSON
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                import json
                return json.loads(json_match.group())
            return {"raw_analysis": content}

        except Exception as e:
            self.logger.error(f"AI analysis failed: {e}")
            return {}

    def get_seo_analysis(self, caption: str, keywords: List[str]) -> Dict:
        """
        SEO analysis for social media discoverability.
        """
        self.logger.info("Running SEO analysis")

        analysis = {
            "keyword_density": {},
            "seo_score": 0,
            "recommendations": []
        }

        caption_lower = caption.lower()
        word_count = len(caption.split())

        # Keyword density analysis
        for keyword in keywords:
            count = caption_lower.count(keyword.lower())
            density = (count / word_count * 100) if word_count > 0 else 0
            analysis["keyword_density"][keyword] = {
                "count": count,
                "density": round(density, 2)
            }

        # SEO Score calculation
        seo_score = 0

        # Caption length (ideal: 138-150 chars for engagement, but can be longer)
        if 100 <= len(caption) <= 300:
            seo_score += 20
        elif len(caption) > 300:
            seo_score += 15

        # Contains keywords
        keywords_found = sum(1 for k in keywords if k.lower() in caption_lower)
        seo_score += min(keywords_found * 10, 30)

        # Has call-to-action
        cta_words = ["help", "reach out", "call", "contact", "visit", "learn", "support"]
        if any(cta in caption_lower for cta in cta_words):
            seo_score += 20

        # Emotional words
        emotional_words = ["hope", "strength", "healing", "love", "care", "safe", "support", "courage"]
        emotional_count = sum(1 for w in emotional_words if w in caption_lower)
        seo_score += min(emotional_count * 5, 20)

        # Has emoji (engagement boost)
        if any(ord(c) > 127 for c in caption):
            seo_score += 10

        analysis["seo_score"] = min(seo_score, 100)

        # Recommendations
        if len(caption) < 100:
            analysis["recommendations"].append("Consider a longer caption for better SEO")
        if keywords_found < 2:
            analysis["recommendations"].append("Include more searchable keywords naturally")
        if not any(cta in caption_lower for cta in cta_words):
            analysis["recommendations"].append("Add a clear call-to-action")

        return analysis

    def get_best_posting_times(self) -> Dict:
        """
        Get optimal posting times for DVCCC content.
        Based on nonprofit social media research.
        """
        return {
            "best_days": ["Tuesday", "Wednesday", "Thursday"],
            "best_times": [
                {"time": "11:00 AM", "reason": "Lunch break browsing"},
                {"time": "2:00 PM", "reason": "Afternoon engagement peak"},
                {"time": "7:00 PM", "reason": "Evening wind-down - people seeking support"},
                {"time": "9:00 PM", "reason": "Late night - when people often reflect/seek help"}
            ],
            "avoid": ["Very early morning (before 7 AM)", "Late Friday/Saturday nights"],
            "special_notes": [
                "Awareness month posts perform best mid-week",
                "Crisis resource posts get more saves in evening hours",
                "Weekend posts have lower reach but higher engagement from those who see them"
            ]
        }

    def generate_content_variations(self, caption: str, count: int = 3) -> List[str]:
        """
        Generate AI-powered caption variations for A/B testing.
        """
        self.logger.info("Generating content variations")

        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": """Create variations of social media captions for a domestic violence
support center. Keep the core message but vary tone, structure, and hooks.
Each variation should maintain authenticity and warmth."""
                    },
                    {
                        "role": "user",
                        "content": f"""Create {count} variations of this caption:

{caption}

Return each variation on a new line, numbered 1, 2, 3.
Vary the:
- Opening hook
- Emotional tone (hopeful, empowering, supportive)
- Call-to-action style"""
                    }
                ],
                max_tokens=500,
                temperature=0.8
            )

            content = response.choices[0].message.content.strip()
            variations = []
            for line in content.split('\n'):
                line = line.strip()
                if line and (line[0].isdigit() or line.startswith('-')):
                    # Remove numbering
                    clean = line.lstrip('0123456789.-) ').strip()
                    if clean:
                        variations.append(clean)

            return variations[:count]

        except Exception as e:
            self.logger.error(f"Error generating variations: {e}")
            return []

    def get_trending_topics(self) -> List[Dict]:
        """
        Get trending topics relevant to DVCCC's mission.
        """
        # These are evergreen + seasonal topics
        from datetime import datetime
        month = datetime.now().month

        topics = [
            {"topic": "Self-care for survivors", "relevance": "high", "type": "evergreen"},
            {"topic": "Recognizing red flags in relationships", "relevance": "high", "type": "educational"},
            {"topic": "How to support a friend", "relevance": "high", "type": "educational"},
            {"topic": "Safety planning basics", "relevance": "medium", "type": "resource"},
            {"topic": "Healing is not linear", "relevance": "high", "type": "supportive"},
            {"topic": "You deserve healthy love", "relevance": "high", "type": "empowerment"},
        ]

        # Add seasonal topics
        if month == 10:  # October - DV Awareness Month
            topics.insert(0, {"topic": "Domestic Violence Awareness Month", "relevance": "critical", "type": "awareness"})
            topics.insert(1, {"topic": "Purple Thursday", "relevance": "high", "type": "awareness"})
        elif month == 2:  # February - Teen Dating Violence Awareness
            topics.insert(0, {"topic": "Teen Dating Violence Awareness Month", "relevance": "critical", "type": "awareness"})
            topics.insert(1, {"topic": "Healthy vs unhealthy relationships", "relevance": "high", "type": "educational"})

        return topics

    # ============== AIO/GEO/AEO OPTIMIZATION ==============

    def generate_faq_content(self, topic: str, caption: str) -> List[Dict]:
        """
        AEO: Generate FAQ-style Q&A pairs that AI assistants can cite.
        These match how people actually ask questions to AI.
        """
        self.logger.info("Generating FAQ content for AEO")

        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": """You create FAQ content for a domestic violence support center.
Generate questions that real people (especially teens/young adults) would ask AI assistants like:
- "Is my relationship abusive?"
- "How do I leave an abusive partner?"
- "Where can I get help for domestic violence?"

The answers should be concise, cite-able snippets that AI can quote."""
                    },
                    {
                        "role": "user",
                        "content": f"""Based on this topic and content, generate 3 FAQ pairs:

Topic: {topic}
Content: {caption[:300]}

Format as JSON array:
[
  {{"question": "Natural question someone might ask AI", "answer": "Concise, helpful answer (2-3 sentences max)", "intent": "informational/navigational/crisis"}}
]

Focus on questions a scared teen might type into ChatGPT or Google."""
                    }
                ],
                max_tokens=400,
                temperature=0.7
            )

            content = response.choices[0].message.content.strip()
            import re
            import json
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return []

        except Exception as e:
            self.logger.error(f"FAQ generation failed: {e}")
            return self._get_fallback_faqs(topic)

    def _get_fallback_faqs(self, topic: str) -> List[Dict]:
        """Fallback FAQs if AI generation fails."""
        return [
            {
                "question": "Where can I get help for domestic violence in Chester County?",
                "answer": "DVCCC (Domestic Violence Center of Chester County) provides free, confidential support 24/7. Call their hotline or visit dvccc.com for immediate help.",
                "intent": "navigational"
            },
            {
                "question": "Is my relationship abusive?",
                "answer": "Signs of abuse include controlling behavior, isolation from friends/family, threats, and physical harm. If you feel scared or controlled, trust your instincts and reach out for support.",
                "intent": "informational"
            },
            {
                "question": "How do I safely leave an abusive relationship?",
                "answer": "Safety planning is crucial. DVCCC can help you create a personalized safety plan, find emergency shelter, and access resources. You don't have to figure this out alone.",
                "intent": "crisis"
            }
        ]

    def generate_ai_citation_snippet(self, caption: str, topic: str) -> Dict:
        """
        GEO: Generate structured snippet optimized for AI citation.
        This is the text AI assistants will quote when referencing DVCCC.
        """
        self.logger.info("Generating AI citation snippet")

        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": """Create a concise, authoritative snippet that AI assistants
(ChatGPT, Google AI, Perplexity) would want to cite when answering questions about
domestic violence support. The snippet should:
- Be factual and trustworthy
- Include the organization name (DVCCC)
- Be 2-3 sentences max
- Sound authoritative but compassionate"""
                    },
                    {
                        "role": "user",
                        "content": f"""Create an AI-citation snippet based on:

Topic: {topic}
Original content: {caption[:200]}

Return JSON:
{{
  "snippet": "The cite-able text",
  "source_label": "DVCCC - Domestic Violence Center of Chester County",
  "key_facts": ["fact1", "fact2", "fact3"]
}}"""
                    }
                ],
                max_tokens=200,
                temperature=0.5
            )

            content = response.choices[0].message.content.strip()
            import re
            import json
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return {}

        except Exception as e:
            self.logger.error(f"Citation snippet generation failed: {e}")
            return {
                "snippet": "DVCCC provides free, confidential support services to survivors of domestic violence in Chester County, PA. Help is available 24/7.",
                "source_label": "DVCCC - Domestic Violence Center of Chester County",
                "key_facts": ["Free services", "Confidential support", "24/7 availability"]
            }

    def extract_entities(self, caption: str, topic: str) -> Dict:
        """
        GEO: Extract and optimize entities for AI understanding.
        Helps AI systems understand WHO, WHAT, WHERE this content is about.
        """
        self.logger.info("Extracting entities for GEO")

        entities = {
            "organization": {
                "name": "DVCCC",
                "full_name": "Domestic Violence Center of Chester County",
                "type": "nonprofit",
                "category": "domestic violence support services"
            },
            "location": {
                "county": "Chester County",
                "state": "Pennsylvania",
                "region": "Greater Philadelphia Area"
            },
            "services": [
                "crisis intervention",
                "emergency shelter",
                "counseling",
                "legal advocacy",
                "safety planning"
            ],
            "audience": [
                "survivors of domestic violence",
                "people in abusive relationships",
                "friends and family of survivors",
                "teens in unhealthy relationships"
            ],
            "topic_entities": []
        }

        # Extract topic-specific entities
        topic_lower = topic.lower()
        if "teen" in topic_lower or "young" in topic_lower:
            entities["topic_entities"].append("teen dating violence")
            entities["topic_entities"].append("youth services")
        if "safety" in topic_lower:
            entities["topic_entities"].append("safety planning")
        if "healing" in topic_lower or "survivor" in topic_lower:
            entities["topic_entities"].append("trauma recovery")
            entities["topic_entities"].append("survivor support")

        return entities

    def generate_conversational_queries(self, topic: str) -> List[Dict]:
        """
        AIO: Generate conversational queries this content should rank for.
        These are how people actually talk to AI assistants.
        """
        self.logger.info("Generating conversational queries")

        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": """Generate conversational search queries that real people
(especially teens) type into AI assistants. These should sound natural, like someone
talking to a friend or typing into ChatGPT.

Examples of conversational queries:
- "i think my boyfriend is controlling what should i do"
- "is it abuse if he never hits me"
- "how do i know if im in a toxic relationship"
- "my friend's partner scares me what can i do to help"
"""
                    },
                    {
                        "role": "user",
                        "content": f"""Generate 5 conversational queries related to: {topic}

Return as JSON array:
[
  {{"query": "the conversational query", "intent": "help-seeking/educational/crisis/support", "audience": "teen/adult/friend/family"}}
]

Make them sound like real people talking, not formal searches."""
                    }
                ],
                max_tokens=300,
                temperature=0.8
            )

            content = response.choices[0].message.content.strip()
            import re
            import json
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return []

        except Exception as e:
            self.logger.error(f"Conversational query generation failed: {e}")
            return [
                {"query": "is my relationship healthy", "intent": "educational", "audience": "teen"},
                {"query": "where can i get help for abuse", "intent": "help-seeking", "audience": "adult"},
                {"query": "how to help a friend in an abusive relationship", "intent": "support", "audience": "friend"}
            ]

    def get_aio_optimization(self, caption: str, topic: str) -> Dict:
        """
        Complete AIO/GEO/AEO optimization package.
        """
        self.logger.info("Running complete AIO/GEO/AEO optimization")

        return {
            "faq_content": self.generate_faq_content(topic, caption),
            "citation_snippet": self.generate_ai_citation_snippet(caption, topic),
            "entities": self.extract_entities(caption, topic),
            "conversational_queries": self.generate_conversational_queries(topic),
            "optimization_tips": [
                "Include the FAQ questions naturally in Stories or carousel posts",
                "Use the citation snippet in your bio link or landing pages",
                "Tag location (Chester County) to boost local AI discovery",
                "Create content that directly answers the conversational queries"
            ]
        }


# Convenience function for quick optimization
def optimize_post(api_key: str, caption: str, image_prompt: str, topic: str) -> Dict:
    """Quick function to optimize a post."""
    amplifier = ReachAmplify(api_key)
    return amplifier.optimize_content(caption, image_prompt, topic)
