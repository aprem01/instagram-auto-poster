import os
import requests
from typing import Optional
import httpx
from openai import OpenAI
from PIL import Image
from io import BytesIO
from src.utils.logger import setup_logger

# Longer timeout for DALL-E (image generation takes longer)
OPENAI_TIMEOUT = httpx.Timeout(180.0, connect=30.0)  # 180 sec total, 30 sec connect


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

        # Explicitly set base_url to override any OPENAI_BASE_URL env var
        self.client = OpenAI(api_key=self.api_key, base_url="https://api.openai.com/v1", timeout=OPENAI_TIMEOUT)
        self.output_dir = output_dir
        self.logger = setup_logger("ImageGenerator")

        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

    # Fallback prompts - 25+ diverse themes (not just trees/nature)
    SAFE_FALLBACK_PROMPTS = [
        # ABSTRACT HOPE/LIGHT
        "Soft golden light rays filtering through morning mist, warm atmosphere, shot on iPhone 14, slight lens flare, natural overexposure, grainy film texture, no people, no text",
        "Out-of-focus warm evening lights creating gentle bokeh, golden hour fading to dusk, shallow depth of field, nostalgic film grain, accidentally aesthetic, no text",

        # URBAN/COMMUNITY
        "Empty Chester County main street at first light, small town morning, puddles from overnight rain, documentary photography, authentic local scene, no people visible, no text",
        "Local community garden gate slightly ajar, morning light on weathered wood, authentic neighborhood vibe, iPhone candid style, earth tones, no text",
        "Empty farmers market stall at dawn with morning setup, authentic vendor tables, documentary moment, Chester County community space, no faces, no text",

        # HANDS/CONNECTION
        "Close-up of two hands holding gently in natural window light, real skin texture, warm supportive moment, iPhone photo, slight motion blur, no faces visible, no text",
        "Hands wrapped around warm ceramic mug, natural indoor light, cozy sweater sleeve visible, documentary detail shot, comfort and care, no text",

        # COZY COMFORT
        "Steaming cup of tea on rainy windowsill, condensation on glass, soft grey outdoor light, cozy indoor atmosphere, authentic home moment, no text",
        "Rain droplets on window glass with blurred warm interior lights, moody contemplative atmosphere, authentic weather moment, soft focus, no text",
        "Soft knit blanket draped over chair arm, afternoon window light, cozy texture detail, warm neutral tones, hygge aesthetic, no text",

        # STRENGTH SYMBOLS
        "Chester County rolling hills at golden hour, grounding earth tones, morning mist in valleys, documentary landscape, natural colors not oversaturated, no text",
        "Old covered bridge in Chester County, weathered wood textures, afternoon light, authentic Pennsylvania landmark, sturdy structure, no people, no text",
        "Large boulder in meadow with wildflowers around base, grounding presence, morning light, stability symbol, documentary style, no text",

        # GROWTH/RENEWAL
        "Small green seedling pushing through soil, natural garden light, macro detail, real dirt textures, new growth symbol, slightly imperfect framing, no text",
        "Open blank journal on wooden desk with morning light, pen beside it, new beginnings symbol, cozy workspace, minimal composition, no visible writing, no text",
        "Early crocuses emerging through last snow, hopeful spring moment, natural garden setting, candid outdoor photo, film grain, no text",

        # MOVEMENT/FREEDOM
        "Single bird silhouette against soft morning sky, not perfectly centered, motion blur on wings, documentary wildlife, freedom symbol, muted colors, no text",
        "Country road stretching through Chester County farmland, morning mist, journey ahead, documentary landscape, authentic rural scene, no text",
        "Monarch butterfly on wildflower, natural meadow setting, slightly imperfect focus, transformation symbol, Pennsylvania garden, no text",

        # SEASONAL VARIETY
        "Fallen autumn leaves on wet pavement after rain, rich orange and brown tones, Chester County fall, iPhone snapshot aesthetic, no text",
        "Frosted window with warm interior light glowing through, winter morning, cozy inside, authentic home moment, no text",
        "Sunflowers in Chester County field, natural afternoon light, not perfectly arranged, authentic farm aesthetic, summer warmth, no text",

        # PEACE/HEALING
        "Still pond reflecting sky at dawn, mist on water surface, peaceful Chester County scene, calm and healing, soft natural colors, no text",
        "Single candle flame in soft dark background, warm gentle glow, remembrance and hope, not perfectly centered, authentic low light, no text",

        # MINIMALIST/TRENDING
        "Single purple flower against simple background, natural windowsill placement, minimalist hope symbol, candid still life, soft light, no text",
        "Smooth river stone on weathered driftwood, simple grounding moment, natural textures, minimal composition, calming simplicity, no text",
        "Soft focus morning through sheer curtains, ethereal diffused light, dreamy sanctuary atmosphere, gentle bokeh, film grain, no text"
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
        # Generate filename if not provided
        if not filename:
            import uuid
            filename = f"generated_{uuid.uuid4().hex[:8]}"

        # Save as JPEG directly (less memory than PNG compression)
        image_path = os.path.join(self.output_dir, f"{filename}.jpg")

        # Stream download to reduce memory usage
        with requests.get(url, timeout=60, stream=True) as response:
            response.raise_for_status()

            # Download in chunks to temp file
            temp_path = image_path + ".tmp"
            with open(temp_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

        # Verify and convert to JPEG (more memory efficient than PNG)
        try:
            image = Image.open(temp_path)
            if image.mode in ("RGBA", "P"):
                image = image.convert("RGB")
            image.save(image_path, "JPEG", quality=95)
            image.close()
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)

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

    def optimize_for_instagram(self, image_path: str, add_authenticity: bool = True) -> str:
        """
        Optimize image for Instagram posting with authenticity effects.

        Args:
            image_path: Path to source image
            add_authenticity: Add subtle effects to make image look less AI-generated

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

        # Add authenticity effects to reduce AI look
        if add_authenticity:
            image = self._add_authenticity_effects(image)

        # Save as JPEG with optimal quality for Instagram
        base, _ = os.path.splitext(image_path)
        output_path = f"{base}_instagram.jpg"

        image.save(output_path, "JPEG", quality=92, optimize=True)
        self.logger.info(f"Optimized image saved to: {output_path}")

        return output_path

    def _add_authenticity_effects(self, image: Image.Image) -> Image.Image:
        """
        Add stronger effects to make AI images look more authentic/real.

        Args:
            image: PIL Image object

        Returns:
            Modified image with authenticity effects
        """
        import random
        from PIL import ImageEnhance, ImageFilter
        import numpy as np

        # Choose a random "camera style" for consistent effects
        camera_style = random.choice(['iphone', 'film', 'mirrorless', 'vintage'])

        img_array = np.array(image)

        # 1. Add realistic film grain/noise (stronger than before)
        if camera_style == 'film':
            noise_intensity = random.uniform(8, 14)  # Stronger for film look
        elif camera_style == 'vintage':
            noise_intensity = random.uniform(10, 16)  # Even stronger for vintage
        else:
            noise_intensity = random.uniform(5, 10)  # Moderate for digital

        noise = np.random.normal(0, noise_intensity, img_array.shape).astype(np.int16)
        img_array = np.clip(img_array.astype(np.int16) + noise, 0, 255).astype(np.uint8)

        image = Image.fromarray(img_array)

        # 2. Reduce saturation more noticeably (AI images are often oversaturated)
        enhancer = ImageEnhance.Color(image)
        if camera_style == 'vintage':
            saturation = random.uniform(0.80, 0.88)  # More faded
        elif camera_style == 'film':
            saturation = random.uniform(0.85, 0.92)  # Film-like
        else:
            saturation = random.uniform(0.88, 0.95)  # Subtle

        image = enhancer.enhance(saturation)

        # 3. Color temperature shift (warmer or cooler based on style)
        r, g, b = image.split()
        if camera_style in ['film', 'vintage']:
            # Warm vintage look
            r = r.point(lambda x: min(255, int(x * random.uniform(1.03, 1.07))))
            b = b.point(lambda x: int(x * random.uniform(0.93, 0.97)))
        elif random.random() > 0.5:
            # Slight warmth
            r = r.point(lambda x: min(255, int(x * random.uniform(1.01, 1.04))))
            b = b.point(lambda x: int(x * random.uniform(0.96, 0.99)))

        image = Image.merge('RGB', (r, g, b))

        # 4. Reduce sharpness (AI images are unnaturally sharp)
        if camera_style == 'iphone':
            # iPhones have some processing but not razor sharp
            if random.random() > 0.3:
                image = image.filter(ImageFilter.GaussianBlur(radius=random.uniform(0.3, 0.6)))
        else:
            # Film/vintage have softer look
            image = image.filter(ImageFilter.GaussianBlur(radius=random.uniform(0.4, 0.8)))

        # 5. Contrast adjustment (often slightly lower in real photos)
        enhancer = ImageEnhance.Contrast(image)
        if camera_style == 'vintage':
            contrast = random.uniform(0.90, 0.96)  # Lower contrast for vintage
        else:
            contrast = random.uniform(0.94, 1.02)

        image = enhancer.enhance(contrast)

        # 6. Brightness variation (real photos often slightly over/under exposed)
        enhancer = ImageEnhance.Brightness(image)
        brightness = random.uniform(0.97, 1.05)
        image = enhancer.enhance(brightness)

        # 7. Add vignette (more noticeable for vintage/film)
        if camera_style in ['vintage', 'film']:
            vignette_intensity = random.uniform(0.10, 0.18)
        else:
            vignette_intensity = random.uniform(0.05, 0.10)

        image = self._add_vignette(image, intensity=vignette_intensity)

        # 8. Add subtle color cast (photos often have slight color biases)
        if random.random() > 0.6:
            image = self._add_color_cast(image)

        return image

    def _add_color_cast(self, image: Image.Image) -> Image.Image:
        """Add subtle color cast like real photos often have."""
        import random
        import numpy as np

        img_array = np.array(image).astype(np.float32)

        # Choose a subtle color cast
        cast_type = random.choice(['warm', 'cool', 'green', 'magenta'])

        if cast_type == 'warm':
            img_array[:, :, 0] *= random.uniform(1.01, 1.03)  # More red
            img_array[:, :, 2] *= random.uniform(0.97, 0.99)  # Less blue
        elif cast_type == 'cool':
            img_array[:, :, 0] *= random.uniform(0.97, 0.99)  # Less red
            img_array[:, :, 2] *= random.uniform(1.01, 1.03)  # More blue
        elif cast_type == 'green':
            img_array[:, :, 1] *= random.uniform(1.01, 1.02)  # Slight green
        elif cast_type == 'magenta':
            img_array[:, :, 0] *= random.uniform(1.01, 1.02)  # Slight red
            img_array[:, :, 2] *= random.uniform(1.01, 1.02)  # Slight blue

        img_array = np.clip(img_array, 0, 255).astype(np.uint8)
        return Image.fromarray(img_array)

        return image

    def _add_vignette(self, image: Image.Image, intensity: float = 0.1) -> Image.Image:
        """
        Add a subtle vignette effect like real camera lenses produce.

        Args:
            image: PIL Image object
            intensity: How strong the vignette should be (0-1)

        Returns:
            Image with vignette effect
        """
        import numpy as np

        width, height = image.size
        img_array = np.array(image).astype(np.float32)

        # Create vignette mask
        x = np.linspace(-1, 1, width)
        y = np.linspace(-1, 1, height)
        X, Y = np.meshgrid(x, y)
        distance = np.sqrt(X**2 + Y**2)

        # Smooth falloff from center
        vignette = 1 - (distance * intensity)
        vignette = np.clip(vignette, 0.7, 1)

        # Apply to all channels
        for i in range(3):
            img_array[:, :, i] = img_array[:, :, i] * vignette

        img_array = np.clip(img_array, 0, 255).astype(np.uint8)
        return Image.fromarray(img_array)
