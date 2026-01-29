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

        self.client = OpenAI(api_key=self.api_key, timeout=OPENAI_TIMEOUT)
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

    def generate_image_prompt(self, topic: str, style_hints: str = "") -> str:
        """
        Generate a DALL-E prompt for image generation.

        Args:
            topic: The topic for the image
            style_hints: Additional style guidance

        Returns:
            Optimized prompt for DALL-E
        """
        self.logger.info(f"Generating image prompt for topic: {topic}")

        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at creating DALL-E prompts that generate "
                                   "authentic, candid-looking photographs that DON'T look AI-generated. "
                                   "Your prompts create images that look like real photos taken by real people - "
                                   "slightly imperfect, natural, with real-world textures and lighting."
                    },
                    {
                        "role": "user",
                        "content": f"Create a DALL-E prompt for an Instagram post about: {topic}\n"
                                   f"Niche: {self.niche}\n"
                                   f"Style hints: {style_hints}\n\n"
                                   "CRITICAL - Make it look REAL, not AI-generated:\n"
                                   "- Documentary/candid photography style, NOT studio perfect\n"
                                   "- Natural imperfections: slightly uneven lighting, real textures\n"
                                   "- Shot on iPhone or mirrorless camera look, not overly polished\n"
                                   "- Real-world environment with authentic details\n"
                                   "- Natural color grading, slight warmth, NOT oversaturated\n"
                                   "- Subtle film grain or slight noise for authenticity\n"
                                   "- Ambient/available light, NOT perfect studio lighting\n"
                                   "- Everyday scenes: coffee shops, parks, home settings, nature\n"
                                   "- Real fabric textures, wood grain, natural surfaces\n"
                                   "- NO faces or identifiable people\n"
                                   "- NO text, words, or letters in the image\n"
                                   "- Symbolic imagery: purple ribbons, candles, flowers, hands, nature\n"
                                   "- Add: 'candid photo, authentic, natural lighting, slight film grain, "
                                   "realistic textures, not AI, shot on iPhone, documentary style'\n\n"
                                   "Return ONLY the prompt, nothing else."
                    }
                ],
                max_tokens=300,
                temperature=0.7
            )

            prompt = response.choices[0].message.content.strip()

            # Add authenticity modifiers to the prompt
            authenticity_suffix = ", candid authentic photo, natural imperfections, realistic textures, not AI generated, documentary photography style, subtle film grain"
            prompt = prompt.rstrip('.') + authenticity_suffix

            self.logger.info("Image prompt generated successfully")

            return prompt

        except Exception as e:
            self.logger.error(f"Error generating image prompt: {e}")
            # Return a simple fallback prompt with authenticity markers
            return f"Candid photograph of {topic}, authentic documentary style, natural ambient lighting, slight film grain, realistic textures, shot on iPhone, warm natural tones, not AI generated, no text, no faces"

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
