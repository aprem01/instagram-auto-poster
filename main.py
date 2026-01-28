#!/usr/bin/env python3
"""
Instagram Auto-Poster for Domestic Violence Center of Chester County

This application automatically:
1. Analyzes trends relevant to domestic violence awareness
2. Generates AI content (images + captions) using OpenAI
3. Posts to Instagram on a scheduled basis

Usage:
    python main.py              # Start the hourly scheduler
    python main.py --test       # Run a single test post
    python main.py --dry-run    # Generate content without posting
"""

import argparse
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config import settings
from src.instagram_client import InstagramClient
from src.trend_analyzer import TrendAnalyzer
from src.content_generator import ContentGenerator
from src.scheduler import PostScheduler, TestScheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("instagram_poster.log"),
    ],
)
logger = logging.getLogger(__name__)


class InstagramAutoPoster:
    """Main application class that orchestrates all components."""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.settings = settings

        # Validate settings
        missing = self.settings.validate()
        if missing:
            logger.error(f"Missing required settings: {', '.join(missing)}")
            logger.error("Please copy .env.example to .env and fill in your credentials")
            sys.exit(1)

        # Initialize components
        logger.info("Initializing Instagram Auto-Poster...")

        self.instagram = InstagramClient(
            username=self.settings.instagram_username,
            password=self.settings.instagram_password,
            session_file=self.settings.session_file,
            proxy_url=self.settings.proxy_url,
        )

        self.trend_analyzer = TrendAnalyzer(
            instagram_client=self.instagram,
            default_hashtags=self.settings.default_hashtags,
        )

        self.content_generator = ContentGenerator(
            api_key=self.settings.openai_api_key,
            organization_name=self.settings.organization_name,
            helpline_number=self.settings.helpline_number,
            local_contact=self.settings.local_contact,
            images_dir=self.settings.images_dir,
        )

        logger.info("All components initialized successfully")

    def login(self) -> bool:
        """Login to Instagram."""
        if self.dry_run:
            logger.info("[DRY RUN] Skipping Instagram login")
            return True

        logger.info("Logging in to Instagram...")
        if not self.instagram.login():
            logger.error("Failed to login to Instagram")
            return False
        logger.info("Instagram login successful")
        return True

    def create_and_post(self) -> bool:
        """Main workflow: analyze trends, generate content, and post."""
        try:
            logger.info("=" * 50)
            logger.info("Starting content generation cycle")
            logger.info("=" * 50)

            # Step 1: Analyze trends
            logger.info("Step 1: Analyzing trends...")
            trend_context = self.trend_analyzer.get_content_prompt_context()
            trends = self.trend_analyzer.get_trending_topics()
            theme = trends["theme"]
            logger.info(f"Selected theme: {theme}")

            # Step 2: Generate content
            logger.info("Step 2: Generating AI content...")
            content = self.content_generator.generate_content(theme, trend_context)

            if not content["success"]:
                logger.error("Failed to generate content")
                return False

            logger.info(f"Content generated successfully")
            logger.info(f"Caption preview: {content['caption'][:100]}...")

            # Step 3: Post to Instagram
            if self.dry_run:
                logger.info("[DRY RUN] Would post the following:")
                logger.info(f"Image: {content['image_path']}")
                logger.info(f"Caption: {content['caption']}")
                return True

            logger.info("Step 3: Posting to Instagram...")
            result = self.instagram.post_image(
                image_path=content["image_path"],
                caption=content["caption"],
            )

            if result:
                logger.info(f"Successfully posted! Media ID: {result.pk}")
                return True
            else:
                logger.error("Failed to post to Instagram")
                return False

        except Exception as e:
            logger.error(f"Error in create_and_post: {e}", exc_info=True)
            return False

    def run_scheduler(self, run_immediately: bool = False):
        """Start the hourly posting scheduler."""
        if not self.login():
            sys.exit(1)

        scheduler = PostScheduler(
            post_callback=self.create_and_post,
            interval_hours=self.settings.posting_interval_hours,
            jitter_minutes=15,
        )

        logger.info(f"Starting scheduler (interval: {self.settings.posting_interval_hours}h)")
        scheduler.start(run_immediately=run_immediately)

    def run_test(self):
        """Run a single test post."""
        if not self.login():
            sys.exit(1)

        test_scheduler = TestScheduler(post_callback=self.create_and_post)
        test_scheduler.run_once()


def main():
    parser = argparse.ArgumentParser(
        description="Instagram Auto-Poster for Domestic Violence Awareness",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                    Start hourly auto-posting
  python main.py --test             Run a single test post
  python main.py --dry-run          Generate content without posting
  python main.py --run-now          Start scheduler and post immediately
        """,
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run a single test post instead of scheduler",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate content but don't post to Instagram",
    )
    parser.add_argument(
        "--run-now",
        action="store_true",
        help="Post immediately when starting scheduler",
    )

    args = parser.parse_args()

    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║     Instagram Auto-Poster                                 ║
    ║     Domestic Violence Center of Chester County            ║
    ╠═══════════════════════════════════════════════════════════╣
    ║  Raising awareness. Supporting survivors. Building hope.  ║
    ╚═══════════════════════════════════════════════════════════╝
    """)

    try:
        poster = InstagramAutoPoster(dry_run=args.dry_run)

        if args.test:
            logger.info("Running in TEST mode")
            poster.run_test()
        else:
            logger.info("Running in SCHEDULER mode")
            poster.run_scheduler(run_immediately=args.run_now)

    except KeyboardInterrupt:
        logger.info("\nShutting down gracefully...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
