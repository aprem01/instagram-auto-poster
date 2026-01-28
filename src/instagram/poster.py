import os
import time
import requests
from typing import Dict, Optional
from src.utils.logger import setup_logger


class InstagramPoster:
    """Posts content to Instagram using the Meta Graph API."""

    BASE_URL = "https://graph.facebook.com/v18.0"

    def __init__(
        self,
        access_token: str = None,
        instagram_account_id: str = None
    ):
        """
        Initialize the Instagram poster.

        Args:
            access_token: Meta API access token (or set META_ACCESS_TOKEN env var)
            instagram_account_id: Instagram Business Account ID
        """
        self.access_token = access_token or os.getenv("META_ACCESS_TOKEN")
        self.instagram_account_id = instagram_account_id or os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID")

        if not self.access_token:
            raise ValueError("Meta access token is required")
        if not self.instagram_account_id:
            raise ValueError("Instagram Business Account ID is required")

        self.logger = setup_logger("InstagramPoster")

    def post_image(
        self,
        image_url: str,
        caption: str,
        location_id: str = None
    ) -> Dict:
        """
        Post an image to Instagram.

        Instagram Graph API requires a 2-step process:
        1. Create a media container
        2. Publish the container

        Args:
            image_url: Public URL of the image to post
            caption: Post caption
            location_id: Optional location ID

        Returns:
            Dictionary with post details
        """
        self.logger.info("Starting Instagram post process...")

        # Step 1: Create media container
        container_id = self._create_media_container(image_url, caption, location_id)

        if not container_id:
            raise Exception("Failed to create media container")

        # Wait for container to be ready
        self._wait_for_container(container_id)

        # Step 2: Publish the container
        result = self._publish_media(container_id)

        self.logger.info(f"Post published successfully! ID: {result.get('id')}")

        return result

    def _create_media_container(
        self,
        image_url: str,
        caption: str,
        location_id: str = None
    ) -> Optional[str]:
        """
        Create a media container for the post.

        Args:
            image_url: Public URL of the image
            caption: Post caption
            location_id: Optional location ID

        Returns:
            Container ID or None
        """
        self.logger.info("Creating media container...")

        url = f"{self.BASE_URL}/{self.instagram_account_id}/media"

        params = {
            "image_url": image_url,
            "caption": caption,
            "access_token": self.access_token
        }

        if location_id:
            params["location_id"] = location_id

        try:
            response = requests.post(url, data=params, timeout=30)
            response.raise_for_status()

            data = response.json()

            if "id" in data:
                self.logger.info(f"Container created: {data['id']}")
                return data["id"]
            else:
                self.logger.error(f"Unexpected response: {data}")
                return None

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error creating container: {e}")
            if hasattr(e, 'response') and e.response is not None:
                self.logger.error(f"Response: {e.response.text}")
            raise

    def _wait_for_container(self, container_id: str, max_attempts: int = 10) -> bool:
        """
        Wait for the media container to be ready for publishing.

        Args:
            container_id: The container ID to check
            max_attempts: Maximum polling attempts

        Returns:
            True if ready, raises exception otherwise
        """
        self.logger.info("Waiting for container to be ready...")

        url = f"{self.BASE_URL}/{container_id}"
        params = {
            "fields": "status_code",
            "access_token": self.access_token
        }

        for attempt in range(max_attempts):
            try:
                response = requests.get(url, params=params, timeout=30)
                response.raise_for_status()

                data = response.json()
                status = data.get("status_code")

                if status == "FINISHED":
                    self.logger.info("Container is ready!")
                    return True
                elif status == "ERROR":
                    raise Exception(f"Container processing failed: {data}")
                else:
                    self.logger.info(f"Status: {status}, waiting... (attempt {attempt + 1}/{max_attempts})")
                    time.sleep(3)

            except requests.exceptions.RequestException as e:
                self.logger.error(f"Error checking container status: {e}")
                time.sleep(3)

        raise Exception("Container processing timed out")

    def _publish_media(self, container_id: str) -> Dict:
        """
        Publish the media container to Instagram.

        Args:
            container_id: The container ID to publish

        Returns:
            Response data with published post ID
        """
        self.logger.info("Publishing media to Instagram...")

        url = f"{self.BASE_URL}/{self.instagram_account_id}/media_publish"

        params = {
            "creation_id": container_id,
            "access_token": self.access_token
        }

        try:
            response = requests.post(url, data=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            return data

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error publishing media: {e}")
            if hasattr(e, 'response') and e.response is not None:
                self.logger.error(f"Response: {e.response.text}")
            raise

    def get_account_info(self) -> Dict:
        """
        Get Instagram account information.

        Returns:
            Account details
        """
        url = f"{self.BASE_URL}/{self.instagram_account_id}"

        params = {
            "fields": "id,username,name,profile_picture_url,followers_count,media_count",
            "access_token": self.access_token
        }

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error getting account info: {e}")
            raise

    def upload_image_to_hosting(self, image_path: str) -> str:
        """
        Upload image to a public hosting service.

        Note: Instagram Graph API requires publicly accessible image URLs.
        Automatically detects and uses available hosting service based on
        environment variables.

        Args:
            image_path: Local path to the image

        Returns:
            Public URL of the uploaded image
        """
        from src.utils.image_hosting import get_uploader

        uploader = get_uploader()
        return uploader.upload(image_path)
