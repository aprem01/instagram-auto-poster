import logging
import random
import requests
from pathlib import Path
from typing import Optional

from openai import OpenAI

logger = logging.getLogger(__name__)


class ContentGenerator:
    """Generates content using OpenAI GPT-4 and DALL-E 3."""

    def __init__(
        self,
        api_key: str,
        organization_name: str,
        helpline_number: str,
        local_contact: str,
        images_dir: Path,
    ):
        self.client = OpenAI(api_key=api_key)
        self.organization_name = organization_name
        self.helpline_number = helpline_number
        self.local_contact = local_contact
        self.images_dir = images_dir

        # System prompt for trauma-informed content
        self.system_prompt = f"""You are a social media content creator for {organization_name},
a domestic violence support organization.

IMPORTANT GUIDELINES:
- Use trauma-informed, sensitive language
- Focus on empowerment, hope, and healing
- Never use victim-blaming language
- Include support resources when appropriate
- Use inclusive language
- Content should be supportive, not sensational
- Avoid graphic descriptions of violence
- Emphasize that help is available and recovery is possible

National Domestic Violence Hotline: {helpline_number}
Local Contact: {local_contact if local_contact else 'Contact us for local resources'}

Your content should raise awareness, support survivors, and educate the community."""

    def generate_caption(self, theme: str, trend_context: str) -> str:
        """Generate an Instagram caption using GPT-4."""
        theme_prompts = {
            "awareness_statistics": "Create a post sharing an important statistic about domestic violence. Make it impactful but not overwhelming. End with a message of hope.",
            "warning_signs": "Create a post educating about warning signs of an abusive relationship. Be informative and supportive, not alarming.",
            "support_resources": "Create a post highlighting available support resources. Emphasize that help is available and reaching out is a sign of strength.",
            "survivor_empowerment": "Create an empowering post celebrating survivor strength and resilience. Focus on hope, healing, and the possibility of a better future.",
            "healthy_relationships": "Create a post about what healthy relationships look like. Focus on positive traits like respect, communication, and boundaries.",
            "community_support": "Create a post about how the community can support survivors. Include ways people can help and get involved.",
            "breaking_the_cycle": "Create a post about breaking the cycle of violence. Focus on education, awareness, and available support.",
            "self_care_healing": "Create a post about self-care and healing for survivors. Emphasize that healing is a journey and it's okay to take it one day at a time.",
        }

        prompt = theme_prompts.get(theme, theme_prompts["support_resources"])

        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {
                        "role": "user",
                        "content": f"""{prompt}

{trend_context}

Requirements:
- Keep the caption under 2000 characters
- Include 5-10 relevant hashtags from the provided list
- Include a call to action
- Include the helpline number: {self.helpline_number}
- Make it engaging and shareable
- Use appropriate emojis sparingly

Write the caption now:""",
                    },
                ],
                max_tokens=1000,
                temperature=0.7,
            )

            caption = response.choices[0].message.content.strip()
            logger.info(f"Generated caption for theme: {theme}")
            return caption

        except Exception as e:
            logger.error(f"Failed to generate caption: {e}")
            return self._get_fallback_caption(theme)

    def _get_fallback_caption(self, theme: str) -> str:
        """Return a fallback caption if AI generation fails."""
        fallbacks = [
            f"You are not alone. Help is available 24/7.\n\nNational Domestic Violence Hotline: {self.helpline_number}\n\n#DomesticViolenceAwareness #YouAreNotAlone #SurvivorStrong",
            f"Healing is possible. Support is available.\n\nReach out to the National Domestic Violence Hotline: {self.helpline_number}\n\n#BreakTheSilence #EndDomesticViolence #SupportSurvivors",
            f"Every person deserves to feel safe. If you or someone you know needs help, resources are available.\n\nCall: {self.helpline_number}\n\n#DomesticViolenceAwareness #SafeRelationships",
        ]
        return random.choice(fallbacks)

    def generate_image(self, theme: str, caption: str) -> Optional[Path]:
        """Generate an image using DALL-E 3."""
        # Image style guidelines for sensitive content
        image_prompts = {
            "awareness_statistics": "A hopeful sunrise over a peaceful landscape, symbolizing new beginnings and awareness. Soft purple and teal colors representing domestic violence awareness. No people, abstract and uplifting.",
            "warning_signs": "An abstract image of hands gently holding a glowing heart, symbolizing protection and care. Warm, comforting colors. Artistic and supportive mood.",
            "support_resources": "A welcoming open door with warm light streaming through, symbolizing help and support being available. Peaceful, hopeful atmosphere. Purple awareness ribbon subtly included.",
            "survivor_empowerment": "A powerful abstract image of a butterfly emerging from a cocoon, symbolizing transformation and strength. Vibrant colors representing hope and new life.",
            "healthy_relationships": "Two abstract figures standing together as equals, represented by balanced geometric shapes. Warm, harmonious colors conveying mutual respect and partnership.",
            "community_support": "Many hands coming together in unity, forming a supportive circle. Diverse, abstract representation. Warm community colors.",
            "breaking_the_cycle": "An abstract chain transforming into birds flying free, symbolizing breaking free and new possibilities. Uplifting sky colors.",
            "self_care_healing": "A serene garden scene with gentle flowers blooming, representing growth and healing. Soft, calming colors. Peaceful and nurturing atmosphere.",
        }

        style_suffix = " Professional Instagram post style. High quality, visually striking. No text in image. Safe for all audiences. Photorealistic or artistic illustration style."

        prompt = image_prompts.get(theme, image_prompts["support_resources"]) + style_suffix

        try:
            response = self.client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1024x1024",
                quality="standard",
                n=1,
            )

            image_url = response.data[0].url

            # Download and save the image
            image_response = requests.get(image_url)
            image_response.raise_for_status()

            # Generate unique filename
            import time
            filename = f"post_{theme}_{int(time.time())}.png"
            image_path = self.images_dir / filename

            with open(image_path, "wb") as f:
                f.write(image_response.content)

            logger.info(f"Generated and saved image: {image_path}")
            return image_path

        except Exception as e:
            logger.error(f"Failed to generate image: {e}")
            return None

    def generate_content(self, theme: str, trend_context: str) -> dict:
        """Generate complete content (caption + image) for a post."""
        caption = self.generate_caption(theme, trend_context)
        image_path = self.generate_image(theme, caption)

        return {
            "caption": caption,
            "image_path": image_path,
            "theme": theme,
            "success": image_path is not None,
        }

    def generate_reel_concept(self, theme: str, trend_context: str) -> dict:
        """Generate a concept/script for a reel (requires manual video creation)."""
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {
                        "role": "user",
                        "content": f"""Create a short video/reel concept for Instagram about: {theme}

{trend_context}

Provide:
1. A 15-30 second script or narration
2. Visual suggestions (what to show on screen)
3. Suggested background music mood
4. Caption for the reel
5. Relevant hashtags

Keep it engaging, educational, and trauma-informed.""",
                    },
                ],
                max_tokens=1500,
                temperature=0.7,
            )

            concept = response.choices[0].message.content.strip()
            logger.info(f"Generated reel concept for theme: {theme}")

            return {
                "concept": concept,
                "theme": theme,
                "note": "Video creation requires manual effort or integration with video generation APIs",
            }

        except Exception as e:
            logger.error(f"Failed to generate reel concept: {e}")
            return {"concept": None, "theme": theme, "error": str(e)}
