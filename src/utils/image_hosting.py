"""
Image Hosting Utilities

Instagram Graph API requires publicly accessible image URLs.
This module provides implementations for various hosting services.
"""

import os
import requests
from typing import Optional
from src.utils.logger import setup_logger


logger = setup_logger("ImageHosting")


class CloudinaryUploader:
    """Upload images to Cloudinary (recommended for production)."""

    def __init__(
        self,
        cloud_name: str = None,
        api_key: str = None,
        api_secret: str = None
    ):
        """
        Initialize Cloudinary uploader.

        Args:
            cloud_name: Cloudinary cloud name (or CLOUDINARY_CLOUD_NAME env var)
            api_key: Cloudinary API key (or CLOUDINARY_API_KEY env var)
            api_secret: Cloudinary API secret (or CLOUDINARY_API_SECRET env var)
        """
        self.cloud_name = cloud_name or os.getenv("CLOUDINARY_CLOUD_NAME")
        self.api_key = api_key or os.getenv("CLOUDINARY_API_KEY")
        self.api_secret = api_secret or os.getenv("CLOUDINARY_API_SECRET")

        if not all([self.cloud_name, self.api_key, self.api_secret]):
            raise ValueError(
                "Cloudinary credentials required. Set CLOUDINARY_CLOUD_NAME, "
                "CLOUDINARY_API_KEY, and CLOUDINARY_API_SECRET environment variables."
            )

    def upload(self, image_path: str, public_id: str = None) -> str:
        """
        Upload image to Cloudinary.

        Args:
            image_path: Local path to image
            public_id: Optional custom public ID

        Returns:
            Public URL of uploaded image
        """
        try:
            import cloudinary
            import cloudinary.uploader

            cloudinary.config(
                cloud_name=self.cloud_name,
                api_key=self.api_key,
                api_secret=self.api_secret
            )

            upload_options = {"folder": "instagram-auto-poster"}
            if public_id:
                upload_options["public_id"] = public_id

            result = cloudinary.uploader.upload(image_path, **upload_options)
            logger.info(f"Image uploaded to Cloudinary: {result['secure_url']}")

            return result["secure_url"]

        except ImportError:
            raise ImportError("cloudinary package required. Install with: pip install cloudinary")


class ImgurUploader:
    """Upload images to Imgur (free, good for testing)."""

    def __init__(self, client_id: str = None):
        """
        Initialize Imgur uploader.

        Args:
            client_id: Imgur client ID (or IMGUR_CLIENT_ID env var)
        """
        self.client_id = client_id or os.getenv("IMGUR_CLIENT_ID")

        if not self.client_id:
            raise ValueError(
                "Imgur client ID required. Set IMGUR_CLIENT_ID environment variable. "
                "Get one at: https://api.imgur.com/oauth2/addclient"
            )

    def upload(self, image_path: str) -> str:
        """
        Upload image to Imgur.

        Args:
            image_path: Local path to image

        Returns:
            Public URL of uploaded image
        """
        url = "https://api.imgur.com/3/image"

        with open(image_path, "rb") as f:
            image_data = f.read()

        headers = {"Authorization": f"Client-ID {self.client_id}"}

        response = requests.post(
            url,
            headers=headers,
            files={"image": image_data},
            timeout=60
        )

        response.raise_for_status()
        data = response.json()

        if data["success"]:
            link = data["data"]["link"]
            logger.info(f"Image uploaded to Imgur: {link}")
            return link
        else:
            raise Exception(f"Imgur upload failed: {data}")


class ImgBBUploader:
    """Upload images to ImgBB (free, simple)."""

    def __init__(self, api_key: str = None):
        """
        Initialize ImgBB uploader.

        Args:
            api_key: ImgBB API key (or IMGBB_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("IMGBB_API_KEY")

        if not self.api_key:
            raise ValueError(
                "ImgBB API key required. Set IMGBB_API_KEY environment variable. "
                "Get one at: https://api.imgbb.com/"
            )

    def upload(self, image_path: str) -> str:
        """
        Upload image to ImgBB.

        Args:
            image_path: Local path to image

        Returns:
            Public URL of uploaded image
        """
        import base64

        url = "https://api.imgbb.com/1/upload"

        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")

        response = requests.post(
            url,
            data={
                "key": self.api_key,
                "image": image_data
            },
            timeout=60
        )

        response.raise_for_status()
        data = response.json()

        if data["success"]:
            link = data["data"]["url"]
            logger.info(f"Image uploaded to ImgBB: {link}")
            return link
        else:
            raise Exception(f"ImgBB upload failed: {data}")


def get_uploader(service: str = "auto"):
    """
    Get an image uploader instance based on available credentials.

    Args:
        service: Service name ("cloudinary", "imgur", "imgbb", or "auto")

    Returns:
        Uploader instance
    """
    if service == "cloudinary" or (
        service == "auto" and os.getenv("CLOUDINARY_CLOUD_NAME")
    ):
        return CloudinaryUploader()

    if service == "imgur" or (service == "auto" and os.getenv("IMGUR_CLIENT_ID")):
        return ImgurUploader()

    if service == "imgbb" or (service == "auto" and os.getenv("IMGBB_API_KEY")):
        return ImgBBUploader()

    raise ValueError(
        "No image hosting service configured. Please set one of:\n"
        "- Cloudinary: CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET\n"
        "- Imgur: IMGUR_CLIENT_ID\n"
        "- ImgBB: IMGBB_API_KEY"
    )
