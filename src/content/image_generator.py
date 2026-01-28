import os
import requests
from typing import Optional
from openai import OpenAI
from PIL import Image
from io import BytesIO
from src.utils.logger import setup_logger


class ImageGenerator:
    """Generates images using OpenAI DALL-E."""

    def __init__(
        self,
        api_key: str = None,
        output_dir: str = "generated_images"
    ):
        """
        Initialize the image generator.

        Args:
            api_key: OpenAI API key (or set OPENAI_API_KEY env var)
            output_dir: Directory to save generated images
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required")

        self.client = OpenAI(api_key=self.api_key)
        self.output_dir = output_dir
        self.logger = setup_logger("ImageGenerator")

        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

    # Fallback prompts for when DALL-E safety filter blocks content (photorealistic style)
    SAFE_FALLBACK_PROMPTS = [
        "Photorealistic photograph of a purple awareness ribbon lying on a wooden table next to a lit candle, soft natural window lighting, DSLR camera quality, shallow depth of field, warm and hopeful mood",
        "Professional photograph of two hands gently holding each other in a supportive gesture, soft golden hour lighting, no faces visible, DSLR quality, warm skin tones, symbol of support and unity",
        "Photorealistic image of purple lavender flowers in a sunlit garden with morning dew, professional nature photography, soft bokeh background, peaceful and healing atmosphere, DSLR quality",
        "Professional photograph of a single lit candle with purple flowers beside it on a peaceful table setting, soft natural lighting, shallow depth of field, symbol of hope, DSLR camera quality",
        "Photorealistic photograph of a butterfly resting on purple flowers in a garden, golden hour sunlight, professional macro photography style, symbol of transformation and hope, sharp detail"
    ]

    def generate_image(
        self,
        prompt: str,
        size: str = "1024x1024",
        quality: str = "standard",
        style: str = "vivid",
        filename: str = None,
        max_retries: int = 3
    ) -> dict:
        """
        Generate an image using DALL-E 3.

        Args:
            prompt: The image generation prompt
            size: Image size (1024x1024, 1792x1024, or 1024x1792)
            quality: Image quality (standard or hd)
            style: Image style (vivid or natural)
            filename: Custom filename (without extension)
            max_retries: Number of retries with fallback prompts

        Returns:
            Dictionary with image path and metadata
        """
        self.logger.info(f"Generating image with prompt: {prompt[:100]}...")

        current_prompt = prompt

        for attempt in range(max_retries):
            try:
                response = self.client.images.generate(
                    model="dall-e-3",
                    prompt=current_prompt,
                    size=size,
                    quality=quality,
                    style=style,
                    n=1
                )

                image_url = response.data[0].url
                revised_prompt = response.data[0].revised_prompt

                # Download and save the image
                image_path = self._download_image(image_url, filename)

                self.logger.info(f"Image generated and saved to: {image_path}")

                return {
                    "image_path": image_path,
                    "image_url": image_url,
                    "original_prompt": prompt,
                    "revised_prompt": revised_prompt,
                    "size": size,
                    "quality": quality,
                    "style": style
                }

            except Exception as e:
                error_str = str(e)
                if "content_policy_violation" in error_str or "safety system" in error_str:
                    if attempt < max_retries - 1:
                        import random
                        current_prompt = random.choice(self.SAFE_FALLBACK_PROMPTS)
                        self.logger.warning(f"Safety filter triggered, trying fallback prompt (attempt {attempt + 2}/{max_retries})")
                        continue
                self.logger.error(f"Error generating image: {e}")
                raise

    def _download_image(self, url: str, filename: str = None) -> str:
        """
        Download image from URL and save locally.

        Args:
            url: Image URL
            filename: Custom filename (without extension)

        Returns:
            Path to saved image
        """
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        # Generate filename if not provided
        if not filename:
            import uuid
            filename = f"generated_{uuid.uuid4().hex[:8]}"

        # Save as PNG
        image_path = os.path.join(self.output_dir, f"{filename}.png")

        # Open with PIL to ensure valid image and save
        image = Image.open(BytesIO(response.content))
        image.save(image_path, "PNG")

        return image_path

    def resize_image(
        self,
        image_path: str,
        target_size: tuple = (1080, 1080),
        output_path: str = None
    ) -> str:
        """
        Resize an image to target dimensions.

        Args:
            image_path: Path to source image
            target_size: Target (width, height)
            output_path: Path for resized image (optional)

        Returns:
            Path to resized image
        """
        self.logger.info(f"Resizing image to {target_size}")

        image = Image.open(image_path)

        # Use high-quality resampling
        resized = image.resize(target_size, Image.Resampling.LANCZOS)

        if not output_path:
            base, ext = os.path.splitext(image_path)
            output_path = f"{base}_resized{ext}"

        resized.save(output_path)
        self.logger.info(f"Resized image saved to: {output_path}")

        return output_path

    def optimize_for_instagram(self, image_path: str) -> str:
        """
        Optimize image for Instagram posting.

        Args:
            image_path: Path to source image

        Returns:
            Path to optimized image
        """
        self.logger.info("Optimizing image for Instagram")

        image = Image.open(image_path)

        # Convert to RGB if necessary (Instagram doesn't support RGBA)
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")

        # Instagram optimal size for feed posts
        target_size = (1080, 1080)

        # Resize if needed
        if image.size != target_size:
            image = image.resize(target_size, Image.Resampling.LANCZOS)

        # Save as JPEG with optimal quality for Instagram
        base, _ = os.path.splitext(image_path)
        output_path = f"{base}_instagram.jpg"

        image.save(output_path, "JPEG", quality=95, optimize=True)
        self.logger.info(f"Optimized image saved to: {output_path}")

        return output_path
