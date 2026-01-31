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
        # Explicitly set base_url to override any OPENAI_BASE_URL env var
        self.client = OpenAI(api_key=api_key, base_url="https://api.openai.com/v1", timeout=OPENAI_TIMEOUT)
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

    def generate_smart_themes(self, count: int = 8) -> List[Dict]:
        """
        Generate smart theme ideas based on trends, SEO, and AIO/GEO/AEO.
        These are AI-powered suggestions that are optimized for discoverability.
        """
        self.logger.info("Generating smart theme ideas...")

        # Get current trending topics as context
        trending = self.get_trending_topics()
        trending_context = ", ".join([t["topic"] for t in trending[:5]])

        from datetime import datetime
        current_month = datetime.now().strftime("%B")
        current_year = datetime.now().year

        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": """You are a social media strategist for DVCCC (Domestic Violence Center of Chester County).
Generate theme ideas that are:
1. SEO-optimized: Include searchable keywords people use
2. AIO-optimized: Match how people ask AI assistants questions
3. Emotionally resonant: Connect with survivors and supporters
4. Action-oriented: Encourage engagement and help-seeking
5. Varied: Mix educational, supportive, empowering, and awareness themes

Each theme should be a complete message/concept that can inspire an Instagram post.
Keep themes concise (under 60 characters when possible) but meaningful."""
                    },
                    {
                        "role": "user",
                        "content": f"""Generate {count} smart theme ideas for DVCCC Instagram posts.

Current month: {current_month} {current_year}
Current trending topics in DV space: {trending_context}

For each theme, provide:
- theme: The actual theme text (concise, inspiring)
- type: One of [awareness, educational, supportive, empowerment, resource, seasonal]
- seo_keywords: 2-3 SEO keywords this targets
- aio_query: What question might someone ask an AI that this content answers?
- priority: high, medium, or trending

Format as JSON array. Make themes varied and emotionally authentic."""
                    }
                ],
                max_tokens=800,
                temperature=0.8
            )

            content = response.choices[0].message.content.strip()
            import re
            import json
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if json_match:
                themes = json.loads(json_match.group())
                self.logger.info(f"Generated {len(themes)} smart themes")
                return themes

            return self._get_fallback_smart_themes()

        except Exception as e:
            self.logger.error(f"Smart theme generation failed: {e}")
            return self._get_fallback_smart_themes()

    def _get_fallback_smart_themes(self) -> List[Dict]:
        """Fallback themes when AI generation fails."""
        from datetime import datetime
        month = datetime.now().month

        themes = [
            {
                "theme": "You are not alone - help is one call away",
                "type": "supportive",
                "seo_keywords": ["domestic violence help", "DV hotline"],
                "aio_query": "where can i get help for domestic violence",
                "priority": "high"
            },
            {
                "theme": "Recognizing the signs of an unhealthy relationship",
                "type": "educational",
                "seo_keywords": ["abuse signs", "unhealthy relationship"],
                "aio_query": "is my relationship abusive",
                "priority": "high"
            },
            {
                "theme": "Your healing journey is valid, no matter how long it takes",
                "type": "empowerment",
                "seo_keywords": ["healing from abuse", "trauma recovery"],
                "aio_query": "how long does it take to heal from abuse",
                "priority": "medium"
            },
            {
                "theme": "Free confidential services for Chester County survivors",
                "type": "resource",
                "seo_keywords": ["Chester County DV services", "free abuse help"],
                "aio_query": "free domestic violence help near me",
                "priority": "high"
            },
            {
                "theme": "How to support a loved one experiencing abuse",
                "type": "educational",
                "seo_keywords": ["help abuse victim", "support friend abuse"],
                "aio_query": "how do i help someone in an abusive relationship",
                "priority": "medium"
            },
            {
                "theme": "Building healthy relationships after trauma",
                "type": "empowerment",
                "seo_keywords": ["healthy relationships", "dating after abuse"],
                "aio_query": "can i have a healthy relationship after abuse",
                "priority": "medium"
            },
            {
                "theme": "Safety planning: preparing for your next steps",
                "type": "resource",
                "seo_keywords": ["safety plan", "leaving abusive relationship"],
                "aio_query": "how to leave an abusive relationship safely",
                "priority": "high"
            },
            {
                "theme": "Every survivor has a story of incredible strength",
                "type": "empowerment",
                "seo_keywords": ["survivor stories", "DV awareness"],
                "aio_query": "am i strong enough to leave",
                "priority": "medium"
            }
        ]

        # Add seasonal theme
        if month == 10:  # October - DV Awareness Month
            themes.insert(0, {
                "theme": "October is Domestic Violence Awareness Month - we stand with survivors",
                "type": "seasonal",
                "seo_keywords": ["DVAM", "domestic violence awareness month"],
                "aio_query": "what is domestic violence awareness month",
                "priority": "trending"
            })
        elif month == 2:  # February - Teen Dating Violence
            themes.insert(0, {
                "theme": "Teen Dating Violence Awareness: Teaching healthy love early",
                "type": "seasonal",
                "seo_keywords": ["teen dating violence", "TDVAM"],
                "aio_query": "signs of teen dating abuse",
                "priority": "trending"
            })

        return themes[:8]


    def analyze_keywords_for_trends(self, keywords: List[str]) -> Dict:
        """
        Analyze user-provided keywords to find related trends, SEO insights, and AIO queries.
        This is the core method for keyword-based trend discovery.

        Args:
            keywords: List of user-provided keywords (e.g., ["healing", "teen", "safety"])

        Returns:
            Dict with:
            - seo_insights: SEO analysis for the keywords
            - aio_queries: AI search queries people might use
            - themes: Suggested content themes based on keywords
            - hashtags: Relevant hashtags for the keywords
        """
        self.logger.info(f"Analyzing keywords for trends: {keywords}")

        keywords_str = ", ".join(keywords)

        # Generate all components
        seo_insights = self._get_keyword_seo_insights(keywords)
        aio_queries = self._generate_keyword_aio_queries(keywords)
        themes = self._generate_keyword_themes(keywords)
        hashtags = self._generate_keyword_hashtags(keywords)

        return {
            "seo_insights": seo_insights,
            "aio_queries": aio_queries,
            "themes": themes,
            "hashtags": hashtags
        }

    def _get_keyword_seo_insights(self, keywords: List[str]) -> Dict:
        """Generate SEO insights for the given keywords."""
        self.logger.info("Generating SEO insights for keywords")

        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": """You are an SEO expert for nonprofit domestic violence support organizations.
Analyze keywords and provide insights about their search potential, competition, and related terms.
Focus on how these keywords can help reach people who need help - especially teens and young adults."""
                    },
                    {
                        "role": "user",
                        "content": f"""Analyze these keywords for DVCCC (Domestic Violence Center of Chester County):
Keywords: {', '.join(keywords)}

Return JSON:
{{
    "search_potential": "High/Medium/Low - based on likely search volume for DV-related queries",
    "competition": "High/Medium/Low - how competitive these terms are",
    "related_keywords": ["5-8 related keywords that expand on these topics"],
    "long_tail_suggestions": ["3-5 longer, more specific keyword phrases"],
    "optimization_tips": ["2-3 tips for using these keywords effectively"]
}}"""
                    }
                ],
                max_tokens=400,
                temperature=0.6
            )

            content = response.choices[0].message.content.strip()
            import re
            import json
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())

            return self._get_fallback_seo_insights(keywords)

        except Exception as e:
            self.logger.error(f"SEO insights generation failed: {e}")
            return self._get_fallback_seo_insights(keywords)

    def _get_fallback_seo_insights(self, keywords: List[str]) -> Dict:
        """Fallback SEO insights if AI generation fails."""
        # Map common keywords to related terms
        keyword_expansions = {
            "healing": ["trauma recovery", "abuse recovery", "emotional healing", "survivor healing"],
            "safety": ["safety planning", "safe relationships", "domestic safety", "feeling safe"],
            "teen": ["teen dating violence", "teen relationships", "youth help", "young adult support"],
            "support": ["survivor support", "emotional support", "crisis support", "help services"],
            "awareness": ["DV awareness", "abuse awareness", "education", "prevention"],
            "hope": ["hope after abuse", "new beginnings", "future hope", "recovery hope"],
            "help": ["get help", "crisis help", "free help", "confidential help"],
            "self-care": ["survivor self-care", "mental health", "wellness", "coping strategies"]
        }

        related = []
        for kw in keywords:
            kw_lower = kw.lower()
            if kw_lower in keyword_expansions:
                related.extend(keyword_expansions[kw_lower])
            else:
                related.append(f"{kw_lower} support")
                related.append(f"domestic violence {kw_lower}")

        return {
            "search_potential": "Medium",
            "competition": "Medium",
            "related_keywords": list(set(related))[:8],
            "long_tail_suggestions": [
                f"how to {keywords[0]} after abuse" if keywords else "how to heal after abuse",
                "domestic violence support near me",
                "free confidential help for abuse"
            ],
            "optimization_tips": [
                "Include location (Chester County) for local SEO",
                "Use natural language that survivors might search for"
            ]
        }

    def _generate_keyword_aio_queries(self, keywords: List[str]) -> List[Dict]:
        """Generate AI search queries based on keywords."""
        self.logger.info("Generating AIO queries for keywords")

        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": """Generate conversational search queries that people (especially teens/young adults)
might ask AI assistants about domestic violence topics. These should sound like natural questions
someone might type into ChatGPT, Google, or Perplexity when looking for help or information."""
                    },
                    {
                        "role": "user",
                        "content": f"""Based on these keywords: {', '.join(keywords)}

Generate 5 conversational AI queries that someone might ask about these topics in relation to
domestic violence, abusive relationships, or seeking help.

Return as JSON array:
[
    {{"query": "natural conversational question", "intent": "help-seeking/educational/crisis/support", "theme_suggestion": "content theme idea based on this query"}}
]

Make queries sound like real people talking - informal, emotional, personal."""
                    }
                ],
                max_tokens=400,
                temperature=0.8
            )

            content = response.choices[0].message.content.strip()
            import re
            import json
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())

            return self._get_fallback_aio_queries(keywords)

        except Exception as e:
            self.logger.error(f"AIO queries generation failed: {e}")
            return self._get_fallback_aio_queries(keywords)

    def _get_fallback_aio_queries(self, keywords: List[str]) -> List[Dict]:
        """Fallback AIO queries if AI generation fails."""
        base_queries = [
            {"query": "is my relationship healthy or abusive", "intent": "educational", "theme_suggestion": "Signs of healthy vs unhealthy relationships"},
            {"query": "where can i get help for domestic violence near me", "intent": "help-seeking", "theme_suggestion": "Free confidential support in Chester County"},
            {"query": "how do i know if i should leave my partner", "intent": "support", "theme_suggestion": "Trusting your instincts about your safety"},
            {"query": "im scared to ask for help what do i do", "intent": "crisis", "theme_suggestion": "It's okay to reach out - you're not alone"},
            {"query": "can i heal from an abusive relationship", "intent": "support", "theme_suggestion": "Your journey to healing starts with one step"}
        ]

        # Customize based on keywords
        for kw in keywords:
            kw_lower = kw.lower()
            if "teen" in kw_lower:
                base_queries.insert(0, {
                    "query": "is my boyfriend being controlling or is this normal",
                    "intent": "educational",
                    "theme_suggestion": "Understanding healthy boundaries in teen relationships"
                })
            elif "healing" in kw_lower:
                base_queries.insert(0, {
                    "query": "how long does it take to recover from an abusive relationship",
                    "intent": "support",
                    "theme_suggestion": "Healing takes time - be patient with yourself"
                })
            elif "safety" in kw_lower:
                base_queries.insert(0, {
                    "query": "how do i make a safety plan to leave",
                    "intent": "crisis",
                    "theme_suggestion": "Safety planning: your first step to freedom"
                })

        return base_queries[:5]

    def _generate_keyword_themes(self, keywords: List[str]) -> List[Dict]:
        """Generate content themes based on keywords."""
        self.logger.info("Generating themes for keywords")

        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": """You are a content strategist for DVCCC (Domestic Violence Center of Chester County).
Generate Instagram post theme ideas that incorporate the given keywords while being:
- SEO optimized (searchable)
- AIO optimized (answers questions people ask AI)
- Emotionally resonant for survivors
- Appropriate for a support organization's voice"""
                    },
                    {
                        "role": "user",
                        "content": f"""Create 5 Instagram post theme ideas based on these keywords: {', '.join(keywords)}

Return as JSON array:
[
    {{
        "theme": "concise theme text (under 60 chars)",
        "type": "supportive/educational/empowerment/resource/awareness",
        "priority": "high/medium/trending",
        "seo_keywords": ["2-3 SEO keywords this targets"],
        "aio_query": "question this content answers"
    }}
]

Make themes varied, authentic, and actionable."""
                    }
                ],
                max_tokens=600,
                temperature=0.8
            )

            content = response.choices[0].message.content.strip()
            import re
            import json
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())

            return self._get_fallback_keyword_themes(keywords)

        except Exception as e:
            self.logger.error(f"Keyword themes generation failed: {e}")
            return self._get_fallback_keyword_themes(keywords)

    def _get_fallback_keyword_themes(self, keywords: List[str]) -> List[Dict]:
        """Fallback themes if AI generation fails."""
        themes = []

        # Generate themes based on keyword combinations
        keyword_themes = {
            "healing": {
                "theme": "Your healing journey is valid, no matter how long",
                "type": "empowerment",
                "priority": "high",
                "seo_keywords": ["healing from abuse", "trauma recovery"],
                "aio_query": "how do i heal from abuse"
            },
            "safety": {
                "theme": "You deserve to feel safe - help is available",
                "type": "supportive",
                "priority": "high",
                "seo_keywords": ["safety planning", "feel safe"],
                "aio_query": "how to feel safe again"
            },
            "teen": {
                "theme": "Healthy relationships start with respect",
                "type": "educational",
                "priority": "high",
                "seo_keywords": ["teen dating", "healthy relationships"],
                "aio_query": "signs of unhealthy teen relationship"
            },
            "support": {
                "theme": "We're here for you - free confidential support",
                "type": "resource",
                "priority": "high",
                "seo_keywords": ["DV support", "confidential help"],
                "aio_query": "where can i get support for abuse"
            },
            "hope": {
                "theme": "There is hope - a new chapter awaits you",
                "type": "empowerment",
                "priority": "medium",
                "seo_keywords": ["hope after abuse", "new beginning"],
                "aio_query": "is there hope after abusive relationship"
            },
            "awareness": {
                "theme": "Knowledge is power - recognize the signs",
                "type": "educational",
                "priority": "medium",
                "seo_keywords": ["DV awareness", "abuse signs"],
                "aio_query": "what are signs of domestic abuse"
            }
        }

        for kw in keywords:
            kw_lower = kw.lower()
            if kw_lower in keyword_themes:
                themes.append(keyword_themes[kw_lower])

        # Add default themes if not enough
        if len(themes) < 3:
            default_themes = [
                {
                    "theme": "You are not alone - we believe you",
                    "type": "supportive",
                    "priority": "high",
                    "seo_keywords": ["DV help", "believe survivors"],
                    "aio_query": "where can i get help"
                },
                {
                    "theme": "Free confidential services in Chester County",
                    "type": "resource",
                    "priority": "high",
                    "seo_keywords": ["free DV services", "Chester County"],
                    "aio_query": "free domestic violence help near me"
                },
                {
                    "theme": "Every survivor has a story of incredible strength",
                    "type": "empowerment",
                    "priority": "medium",
                    "seo_keywords": ["survivor strength", "resilience"],
                    "aio_query": "am i strong enough to leave"
                }
            ]
            for t in default_themes:
                if len(themes) < 5:
                    themes.append(t)

        return themes[:5]

    def _generate_keyword_hashtags(self, keywords: List[str]) -> List[str]:
        """Generate relevant hashtags for the keywords."""
        self.logger.info("Generating hashtags for keywords")

        hashtags = []

        # Add core hashtags
        hashtags.extend([
            "#DomesticViolenceAwareness", "#DVCCC", "#ChesterCounty",
            "#YouAreNotAlone", "#SurvivorSupport"
        ])

        # Add keyword-specific hashtags
        keyword_hashtags = {
            "healing": ["#HealingJourney", "#TraumaRecovery", "#HopeAndHealing"],
            "safety": ["#SafetyFirst", "#SafetyPlanning", "#FeelSafe"],
            "teen": ["#TeenDatingViolence", "#HealthyRelationships", "#TeenSafety"],
            "support": ["#SupportSurvivors", "#HelpIsAvailable", "#ReachOut"],
            "hope": ["#ThereIsHope", "#NewBeginnings", "#Strength"],
            "awareness": ["#DVAwareness", "#BreakTheSilence", "#SpeakOut"],
            "help": ["#GetHelp", "#CrisisHelp", "#HelpLine"],
            "self-care": ["#SelfCare", "#MentalHealth", "#Wellness"],
            "empowerment": ["#Empowerment", "#SurvivorStrong", "#ReclaimYourLife"]
        }

        for kw in keywords:
            kw_lower = kw.lower()
            if kw_lower in keyword_hashtags:
                hashtags.extend(keyword_hashtags[kw_lower])
            else:
                # Create custom hashtag from keyword
                clean_kw = kw.replace(" ", "").replace("-", "")
                hashtags.append(f"#{clean_kw.title()}")

        # Remove duplicates while preserving order
        seen = set()
        unique_hashtags = []
        for tag in hashtags:
            tag_lower = tag.lower()
            if tag_lower not in seen:
                seen.add(tag_lower)
                unique_hashtags.append(tag)

        return unique_hashtags[:15]


# Convenience function for quick optimization
def optimize_post(api_key: str, caption: str, image_prompt: str, topic: str) -> Dict:
    """Quick function to optimize a post."""
    amplifier = ReachAmplify(api_key)
    return amplifier.optimize_content(caption, image_prompt, topic)
