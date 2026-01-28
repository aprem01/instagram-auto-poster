#!/usr/bin/env python3
"""
Instagram Auto-Poster Application

Automatically fetches trends, generates AI content, and posts to Instagram.
"""

import os
import sys
import yaml
import signal
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.trends import TrendFetcher
from src.content import TextGenerator, ImageGenerator
from src.instagram import InstagramPoster
from src.utils import setup_logger


class InstagramAutoPostingApp:
    """Main application class for automated Instagram posting."""

    def __init__(self, config_path: str = "config/config.yaml"):
        """
        Initialize the application.

        Args:
            config_path: Path to configuration file
        """
        # Load environment variables
        load_dotenv()

        # Load configuration
        self.config = self._load_config(config_path)

        # Setup logging
        log_config = self.config.get("logging", {})
        self.logger = setup_logger(
            "InstagramAutoPostingApp",
            log_level=log_config.get("level", "INFO"),
            log_file=log_config.get("file")
        )

        self.logger.info("Initializing Instagram Auto-Posting App...")

        # Initialize components
        self._init_components()

        # Setup scheduler
        self.scheduler = BlockingScheduler()

        self.logger.info("App initialized successfully!")

    def _load_config(self, config_path: str) -> dict:
        """Load configuration from YAML file."""
        config_file = Path(config_path)

        if not config_file.exists():
            # Try relative to script location
            config_file = Path(__file__).parent.parent / config_path

        if not config_file.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_file, "r") as f:
            return yaml.safe_load(f)

    def _init_components(self):
        """Initialize all application components."""
        channel_config = self.config.get("channel", {})
        trends_config = self.config.get("trends", {})
        content_config = self.config.get("content", {})

        # Trend fetcher
        self.trend_fetcher = TrendFetcher(
            geo=trends_config.get("geo", "US"),
            language=trends_config.get("language", "en-US"),
            niche=channel_config.get("niche")
        )

        # Text generator
        self.text_generator = TextGenerator(
            niche=channel_config.get("niche", "general"),
            style=channel_config.get("style", "casual"),
            hashtag_count=channel_config.get("hashtag_count", 15)
        )

        # Image generator
        image_config = content_config.get("image", {})
        self.image_generator = ImageGenerator(
            output_dir="generated_images"
        )
        self.image_size = f"{image_config.get('width', 1024)}x{image_config.get('height', 1024)}"
        self.image_quality = image_config.get("quality", "standard")
        self.image_style = image_config.get("style", "vivid")

        # Instagram poster
        self.instagram_poster = InstagramPoster()

        # Store caption config
        self.caption_config = content_config.get("caption", {})
        self.channel_description = channel_config.get("description", "")

    def create_and_post_content(self):
        """Main job: fetch trends, generate content, and post to Instagram."""
        self.logger.info("=" * 50)
        self.logger.info(f"Starting content creation job at {datetime.now()}")
        self.logger.info("=" * 50)

        try:
            # Step 1: Fetch trending topics
            self.logger.info("Step 1: Fetching trending topics...")
            trends = self.trend_fetcher.get_trending_topics(limit=3)

            if not trends:
                self.logger.warning("No trends found, skipping this cycle")
                return

            # Select a random trend
            import random
            selected_trend = random.choice(trends)
            topic = selected_trend["topic"]
            self.logger.info(f"Selected topic: {topic}")

            # Step 2: Generate caption
            self.logger.info("Step 2: Generating caption...")
            caption_result = self.text_generator.generate_caption(
                topic=topic,
                channel_description=self.channel_description,
                max_length=self.caption_config.get("max_length", 2200),
                include_emojis=self.caption_config.get("include_emojis", True),
                include_cta=self.caption_config.get("include_cta", True)
            )
            caption = caption_result["caption"]
            self.logger.info(f"Caption generated ({len(caption)} chars)")

            # Step 3: Generate image prompt
            self.logger.info("Step 3: Generating image prompt...")
            image_prompt = self.text_generator.generate_image_prompt(topic)
            self.logger.info(f"Image prompt: {image_prompt[:100]}...")

            # Step 4: Generate image
            self.logger.info("Step 4: Generating image...")
            image_result = self.image_generator.generate_image(
                prompt=image_prompt,
                size=self.image_size,
                quality=self.image_quality,
                style=self.image_style
            )
            image_path = image_result["image_path"]
            self.logger.info(f"Image saved to: {image_path}")

            # Step 5: Optimize image for Instagram
            self.logger.info("Step 5: Optimizing image for Instagram...")
            optimized_path = self.image_generator.optimize_for_instagram(image_path)

            # Step 6: Upload to hosting and get public URL
            self.logger.info("Step 6: Uploading image to hosting service...")
            image_url = self.instagram_poster.upload_image_to_hosting(optimized_path)
            self.logger.info(f"Image uploaded: {image_url}")

            # Step 7: Post to Instagram
            self.logger.info("Step 7: Posting to Instagram...")
            post_result = self.instagram_poster.post_image(
                image_url=image_url,
                caption=caption
            )

            self.logger.info("=" * 50)
            self.logger.info(f"SUCCESS! Post published with ID: {post_result.get('id')}")
            self.logger.info("=" * 50)

        except NotImplementedError as e:
            self.logger.error(f"Configuration required: {e}")
            self.logger.info("Please configure image hosting in src/instagram/poster.py")
        except Exception as e:
            self.logger.error(f"Error in content creation job: {e}")
            import traceback
            self.logger.error(traceback.format_exc())

    def run_once(self):
        """Run a single content creation and posting cycle."""
        self.logger.info("Running single post cycle...")
        self.create_and_post_content()

    def start(self):
        """Start the scheduler for hourly posting."""
        schedule_config = self.config.get("schedule", {})
        interval_hours = schedule_config.get("interval_hours", 1)

        self.logger.info(f"Starting scheduler with {interval_hours} hour interval...")

        # Schedule the job
        self.scheduler.add_job(
            self.create_and_post_content,
            trigger=IntervalTrigger(hours=interval_hours),
            id="content_posting_job",
            name="Create and post content to Instagram",
            next_run_time=datetime.now()  # Run immediately on start
        )

        # Handle graceful shutdown
        def shutdown(signum, frame):
            self.logger.info("Shutdown signal received, stopping scheduler...")
            self.scheduler.shutdown()
            sys.exit(0)

        signal.signal(signal.SIGINT, shutdown)
        signal.signal(signal.SIGTERM, shutdown)

        self.logger.info("Scheduler started! Press Ctrl+C to stop.")

        try:
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            self.logger.info("Scheduler stopped.")

    def test_components(self):
        """Test individual components without posting."""
        self.logger.info("Testing components...")

        # Test trend fetcher
        self.logger.info("\n--- Testing Trend Fetcher ---")
        trends = self.trend_fetcher.get_trending_topics(limit=3)
        for trend in trends:
            self.logger.info(f"  - {trend['topic']} (source: {trend['source']})")

        if trends:
            topic = trends[0]["topic"]

            # Test text generator
            self.logger.info("\n--- Testing Text Generator ---")
            caption_result = self.text_generator.generate_caption(topic)
            self.logger.info(f"  Caption preview: {caption_result['caption'][:200]}...")

            # Test image prompt generation
            self.logger.info("\n--- Testing Image Prompt Generator ---")
            image_prompt = self.text_generator.generate_image_prompt(topic)
            self.logger.info(f"  Image prompt: {image_prompt[:200]}...")

        # Test Instagram connection
        self.logger.info("\n--- Testing Instagram Connection ---")
        try:
            account_info = self.instagram_poster.get_account_info()
            self.logger.info(f"  Connected to: @{account_info.get('username')}")
            self.logger.info(f"  Followers: {account_info.get('followers_count')}")
        except Exception as e:
            self.logger.error(f"  Instagram connection failed: {e}")

        self.logger.info("\nComponent testing complete!")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Instagram Auto-Poster")
    parser.add_argument(
        "--config",
        default="config/config.yaml",
        help="Path to configuration file"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Test components without posting"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run single post cycle and exit"
    )

    args = parser.parse_args()

    # Change to script directory
    os.chdir(Path(__file__).parent.parent)

    app = InstagramAutoPostingApp(config_path=args.config)

    if args.test:
        app.test_components()
    elif args.once:
        app.run_once()
    else:
        app.start()


if __name__ == "__main__":
    main()
