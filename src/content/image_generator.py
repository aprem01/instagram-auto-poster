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

        # Support Cloudflare Worker proxy for API calls
        base_url = os.getenv("OPENAI_BASE_URL")
        if base_url:
            self.client = OpenAI(api_key=self.api_key, base_url=base_url, timeout=OPENAI_TIMEOUT)
        else:
            self.client = OpenAI(api_key=self.api_key, timeout=OPENAI_TIMEOUT)
        self.output_dir = output_dir
        self.logger = setup_logger("ImageGenerator")

        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

    # Fallback prompts - varied themes for DVCCC (not always purple ribbons)
    SAFE_FALLBACK_PROMPTS = [
        "Candid photograph of golden sunrise breaking through clouds over a peaceful meadow, natural morning light, hope and new beginnings, shot on iPhone, authentic landscape, slight film grain, warm tones, documentary style",
        "Authentic photo of two hands gently holding in supportive gesture, natural daylight from window, no faces, real skin texture, candid moment of connection, warm supportive atmosphere, documentary photography",
        "Real photograph of a single oak tree standing strong in a Chester County field, morning golden hour light, symbol of strength and resilience, shot on smartphone, natural colors, slight bokeh, authentic nature",
        "Candid photo of birds taking flight at sunrise, silhouetted against warm sky, freedom and hope, natural outdoor lighting, documentary wildlife photography, slight motion blur, authentic moment",
        "Peaceful photograph of a winding forest path with dappled sunlight, journey forward, natural woodland setting, shot on mirrorless camera, soft morning light, authentic nature scene, warm earth tones",
        "Cozy candid photo of warm cup of tea on a windowsill with rain outside, comfort and healing, natural ambient light, authentic home setting, soft focus background, warm inviting atmosphere",
        "Documentary style photo of spring flowers pushing through soil, new growth and resilience, natural garden setting, morning dew, authentic macro photography, soft natural lighting"
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
        Add subtle effects to make AI images look more authentic/real.

        Args:
            image: PIL Image object

        Returns:
            Modified image with authenticity effects
        """
        import random
        from PIL import ImageEnhance, ImageFilter
        import numpy as np

        # Convert to numpy for grain
        img_array = np.array(image)

        # 1. Add subtle film grain/noise
        noise_intensity = random.uniform(3, 8)
        noise = np.random.normal(0, noise_intensity, img_array.shape).astype(np.int16)
        img_array = np.clip(img_array.astype(np.int16) + noise, 0, 255).astype(np.uint8)

        image = Image.fromarray(img_array)

        # 2. Slightly reduce saturation (AI images are often oversaturated)
        enhancer = ImageEnhance.Color(image)
        saturation = random.uniform(0.92, 0.98)
        image = enhancer.enhance(saturation)

        # 3. Add very subtle warmth by adjusting color balance
        r, g, b = image.split()
        r = r.point(lambda x: min(255, int(x * random.uniform(1.01, 1.03))))
        b = b.point(lambda x: int(x * random.uniform(0.97, 0.99)))
        image = Image.merge('RGB', (r, g, b))

        # 4. Very slight blur to reduce AI sharpness
        if random.random() > 0.5:
            image = image.filter(ImageFilter.GaussianBlur(radius=0.3))

        # 5. Subtle contrast adjustment
        enhancer = ImageEnhance.Contrast(image)
        contrast = random.uniform(0.97, 1.03)
        image = enhancer.enhance(contrast)

        # 6. Very slight vignette effect (darker corners like real cameras)
        image = self._add_vignette(image, intensity=random.uniform(0.05, 0.12))

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
