import os
from typing import Dict, Optional
import httpx
from openai import OpenAI
from src.utils.logger import setup_logger

# Longer timeout for cloud deployments (Render free tier can be slow)
OPENAI_TIMEOUT = httpx.Timeout(120.0, connect=30.0)  # 120 sec total, 30 sec connect


class TextGenerator:
    """Generates Instagram captions using OpenAI GPT-4."""

    def __init__(
        self,
        api_key: str = None,
        niche: str = "general",
        style: str = "casual",
        hashtag_count: int = 15
    ):
        """
        Initialize the text generator.

        Args:
            api_key: OpenAI API key (or set OPENAI_API_KEY env var)
            niche: Content niche (tech, fitness, travel, etc.)
            style: Writing style (casual, professional, humorous)
            hashtag_count: Number of hashtags to include
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required")

        # Explicitly set base_url to override any OPENAI_BASE_URL env var
        self.client = OpenAI(api_key=self.api_key, base_url="https://api.openai.com/v1", timeout=OPENAI_TIMEOUT)
        self.niche = niche
        self.style = style
        self.hashtag_count = hashtag_count
        self.logger = setup_logger("TextGenerator")

    def generate_caption(
        self,
        topic: str,
        channel_description: str = "",
        max_length: int = 2200,
        include_emojis: bool = True,
        include_cta: bool = True
    ) -> Dict:
        """
        Generate an Instagram caption for a given topic.

        Args:
            topic: The trending topic to write about
            channel_description: Description of the Instagram channel
            max_length: Maximum caption length
            include_emojis: Whether to include emojis
            include_cta: Whether to include call-to-action

        Returns:
            Dictionary with caption and metadata
        """
        self.logger.info(f"Generating caption for topic: {topic}")

        prompt = self._build_caption_prompt(
            topic=topic,
            channel_description=channel_description,
            max_length=max_length,
            include_emojis=include_emojis,
            include_cta=include_cta
        )

        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "You are the social media manager for the Domestic Violence Center of Chester County (DVCCC). "
                                   "Write Instagram captions in FIRST PERSON as the organization ('we', 'our', 'us'). "
                                   f"Your writing style is {self.style}. "
                                   "Create personal, heartfelt captions that connect with survivors and the community. "
                                   "Always remind readers that help is available and they are not alone."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=1000,
                temperature=0.8
            )

            caption = response.choices[0].message.content.strip()

            self.logger.info("Caption generated successfully")

            return {
                "caption": caption,
                "topic": topic,
                "model": "gpt-4",
                "tokens_used": response.usage.total_tokens
            }

        except Exception as e:
            self.logger.error(f"Error generating caption: {e}")
            raise

    def generate_image_prompt(self, topic: str, style_hints: str = "", campaign_mode: str = None) -> str:
        """
        Generate a DALL-E prompt using diverse visual themes.

        Args:
            topic: The topic for the image
            style_hints: Additional style guidance
            campaign_mode: Optional campaign mode for theme matching

        Returns:
            Optimized prompt for DALL-E that looks authentic and varied
        """
        self.logger.info(f"Generating image prompt for topic: {topic}")

        # Try to use the visual themes system for diversity
        try:
            from src.content.visual_themes import get_diverse_prompt, theme_selector

            # Get diverse prompt from theme system
            base_prompt = get_diverse_prompt(topic=topic, campaign_mode=campaign_mode)

            self.logger.info(f"Using visual theme system - theme: {theme_selector.recently_used[-1] if theme_selector.recently_used else 'unknown'}")

            return base_prompt

        except ImportError:
            self.logger.warning("Visual themes module not available, using GPT-4 generation")

        # Fallback: Use GPT-4 with improved prompting
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at creating DALL-E prompts for authentic-looking photographs. "
                                   "Create images that look like real smartphone photos - slightly imperfect, natural lighting, "
                                   "real-world textures. AVOID: trees, forests, nature paths (overused). "
                                   "PREFER: urban scenes, hands/connection, cozy interiors, abstract light, community spaces."
                    },
                    {
                        "role": "user",
                        "content": f"Create a DALL-E prompt for: {topic}\n"
                                   f"Style hints: {style_hints}\n\n"
                                   "Choose a UNIQUE theme (avoid trees/forests):\n"
                                   "- Warm bokeh lights at dusk\n"
                                   "- Hands holding (no faces)\n"
                                   "- Cozy interior with tea/coffee\n"
                                   "- Rain on window glass\n"
                                   "- Empty park bench at dawn\n"
                                   "- Single flower, minimal composition\n"
                                   "- Community garden gate\n"
                                   "- Candle flame in darkness\n"
                                   "- Rolling hills at golden hour\n"
                                   "- Old bridge with character\n\n"
                                   "Make it look REAL: shot on iPhone 14, slight grain, "
                                   "not perfectly centered, natural imperfections.\n"
                                   "NO faces, NO text. Return ONLY the prompt."
                    }
                ],
                max_tokens=250,
                temperature=0.9  # Higher temperature for more variety
            )

            prompt = response.choices[0].message.content.strip()

            # Add varied authenticity modifiers
            import random
            modifiers = random.choice([
                ", shot on iPhone 14, slight film grain, candid moment, not perfectly composed",
                ", smartphone snapshot aesthetic, natural uneven lighting, documentary style",
                ", Fujifilm colors, nostalgic film look, authentic captured moment",
                ", Canon mirrorless, soft natural light, accidentally aesthetic"
            ])

            prompt = prompt.rstrip('.') + modifiers + ", no faces, no text"

            self.logger.info("Image prompt generated successfully via GPT-4")
            return prompt

        except Exception as e:
            self.logger.error(f"Error generating image prompt: {e}")
            # Return diverse fallback
            import random
            fallbacks = [
                "Warm bokeh lights at evening dusk, shallow depth of field, nostalgic film grain, soft focus, cozy atmosphere, no text",
                "Close-up of hands holding warm mug, natural window light, cozy sweater texture, documentary detail, no faces, no text",
                "Rain droplets on window glass, blurred warm interior lights, moody contemplative atmosphere, authentic weather moment, no text",
                "Single candle flame in soft darkness, warm gentle glow, remembrance and hope, low light iPhone photo, no text",
                "Empty park bench at dawn, morning dew, soft pink sky, documentary photography, Chester County park, no text"
            ]
            return random.choice(fallbacks)

    def _build_caption_prompt(
        self,
        topic: str,
        channel_description: str,
        max_length: int,
        include_emojis: bool,
        include_cta: bool
    ) -> str:
        """Build the prompt for caption generation."""

        prompt_parts = [
            f"Create a personal, heartfelt Instagram caption about: {topic}",
            "\nOrganization: Domestic Violence Center of Chester County (DVCCC)",
            "Location: Chester County, Pennsylvania",
            "Tagline: 'Supporting Survivors of Domestic Violence in Chester County'",
            "Services: FREE, CONFIDENTIAL, LIFESAVING services including compassionate support, counseling, and resources",
            "Website: dvcccpa.org",
        ]

        if channel_description:
            prompt_parts.append(f"\nAbout us: {channel_description}")

        prompt_parts.append(f"\nWriting style: {self.style}")
        prompt_parts.append(f"Maximum length: {max_length} characters")
        prompt_parts.append(f"Number of hashtags: {self.hashtag_count}")

        requirements = ["\nCRITICAL Requirements:"]
        requirements.append("- Write in FIRST PERSON as the organization ('We are here for you', 'Our team', 'We believe')")
        requirements.append("- Be PERSONAL and WARM - like talking to a friend who cares")
        requirements.append("- Mention Chester County to connect with local community")
        requirements.append("- Emphasize that services are FREE and CONFIDENTIAL")
        requirements.append("- Always include hope and the message 'You are not alone'")

        if include_emojis:
            requirements.append("- Use tasteful, supportive emojis (💜 purple heart, 🤝 support, 💪 strength, 🌟 hope)")
        else:
            requirements.append("- Do NOT include any emojis")

        if include_cta:
            requirements.append("- End with: encouragement to reach out, visit dvcccpa.org, or reminder that help is available 24/7")

        requirements.extend([
            "- Start with a hook that speaks directly to the reader",
            "- Break up text with line breaks for easy reading",
            "- Keep it authentic - not corporate or clinical",
            "- Include hashtags: #DVCCC #ChesterCounty #DomesticViolenceAwareness #SurvivorSupport #YouAreNotAlone"
        ])

        prompt_parts.extend(requirements)

        return "\n".join(prompt_parts)
