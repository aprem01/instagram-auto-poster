import logging
import random
from datetime import datetime
from typing import Callable, Optional

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED

logger = logging.getLogger(__name__)


class PostScheduler:
    """Handles scheduling of automated posts."""

    def __init__(
        self,
        post_callback: Callable,
        interval_hours: int = 1,
        jitter_minutes: int = 15,
    ):
        """
        Initialize the scheduler.

        Args:
            post_callback: Function to call when it's time to post
            interval_hours: Hours between posts
            jitter_minutes: Random jitter to add (helps avoid detection)
        """
        self.post_callback = post_callback
        self.interval_hours = interval_hours
        self.jitter_minutes = jitter_minutes
        self.scheduler = BlockingScheduler()
        self.post_count = 0
        self.error_count = 0

        # Add event listeners
        self.scheduler.add_listener(self._job_executed, EVENT_JOB_EXECUTED)
        self.scheduler.add_listener(self._job_error, EVENT_JOB_ERROR)

    def _job_executed(self, event):
        """Called when a job executes successfully."""
        self.post_count += 1
        logger.info(f"Post #{self.post_count} completed successfully")

    def _job_error(self, event):
        """Called when a job encounters an error."""
        self.error_count += 1
        logger.error(f"Post job failed. Total errors: {self.error_count}")
        logger.error(f"Exception: {event.exception}")

    def _execute_with_jitter(self):
        """Execute the post callback with random jitter."""
        # Add random delay (jitter) to seem more human
        jitter_seconds = random.randint(0, self.jitter_minutes * 60)
        logger.info(f"Adding {jitter_seconds}s jitter before posting...")

        import time
        time.sleep(jitter_seconds)

        try:
            self.post_callback()
        except Exception as e:
            logger.error(f"Error during post execution: {e}")
            raise

    def start(self, run_immediately: bool = False):
        """
        Start the scheduler.

        Args:
            run_immediately: If True, run one post immediately before starting schedule
        """
        logger.info(f"Starting scheduler - posting every {self.interval_hours} hour(s)")
        logger.info(f"Jitter: up to {self.jitter_minutes} minutes")

        if run_immediately:
            logger.info("Running initial post immediately...")
            try:
                self._execute_with_jitter()
            except Exception as e:
                logger.error(f"Initial post failed: {e}")

        # Add the scheduled job
        self.scheduler.add_job(
            self._execute_with_jitter,
            trigger=IntervalTrigger(hours=self.interval_hours),
            id="instagram_post",
            name="Instagram Auto Post",
            replace_existing=True,
        )

        logger.info("Scheduler started. Press Ctrl+C to stop.")
        try:
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Scheduler stopped by user")
            self.stop()

    def stop(self):
        """Stop the scheduler gracefully."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info(f"Scheduler stopped. Total posts: {self.post_count}, Errors: {self.error_count}")

    def get_stats(self) -> dict:
        """Get scheduler statistics."""
        return {
            "total_posts": self.post_count,
            "total_errors": self.error_count,
            "interval_hours": self.interval_hours,
            "is_running": self.scheduler.running if hasattr(self.scheduler, 'running') else False,
        }


class TestScheduler:
    """A simple test scheduler for development/testing."""

    def __init__(self, post_callback: Callable):
        self.post_callback = post_callback

    def run_once(self):
        """Run a single post for testing."""
        logger.info("Running single test post...")
        try:
            result = self.post_callback()
            logger.info("Test post completed")
            return result
        except Exception as e:
            logger.error(f"Test post failed: {e}")
            raise


# ============== WEB-BASED SCHEDULER ==============

import os
import sys
import sqlite3
import threading
import time as time_module

DB_PATH = 'scheduled_posts.db'


class WebContentScheduler:
    """Manages scheduled content generation for the web interface."""

    def __init__(self):
        self.running = False
        self.thread = None
        self._text_gen = None
        self._img_gen = None
        self._uploader = None

    @property
    def text_gen(self):
        """Lazy load text generator."""
        if self._text_gen is None:
            from src.content import TextGenerator
            self._text_gen = TextGenerator(
                niche='domestic violence awareness',
                style='warm, personal, and empowering',
                hashtag_count=10
            )
        return self._text_gen

    @property
    def img_gen(self):
        """Lazy load image generator."""
        if self._img_gen is None:
            from src.content import ImageGenerator
            self._img_gen = ImageGenerator(output_dir='generated_images')
        return self._img_gen

    @property
    def uploader(self):
        """Lazy load uploader."""
        if self._uploader is None:
            try:
                from src.utils.image_hosting import get_uploader
                self._uploader = get_uploader()
            except:
                self._uploader = False  # Use False to indicate failed, None for not loaded
        return self._uploader if self._uploader else None

    def get_db(self):
        """Get database connection."""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    def get_due_schedules(self):
        """Get schedules that are due to run now."""
        now = datetime.now()
        current_time = now.strftime('%H:%M')

        # Convert Python weekday (0=Monday) to our format (0=Sunday)
        day_map = {0: 1, 1: 2, 2: 3, 3: 4, 4: 5, 5: 6, 6: 0}
        current_day = str(day_map[now.weekday()])

        conn = self.get_db()
        c = conn.cursor()

        # Find active schedules with matching times
        c.execute('''
            SELECT s.*, st.time_of_day, st.days_of_week
            FROM schedules s
            JOIN schedule_times st ON s.id = st.schedule_id
            WHERE s.is_active = 1
            AND st.time_of_day = ?
            AND st.days_of_week LIKE ?
        ''', (current_time, f'%{current_day}%'))

        due_schedules = c.fetchall()
        conn.close()

        return due_schedules

    def pick_theme(self, schedule_id, theme_mode):
        """Pick a theme based on the schedule's mode."""
        conn = self.get_db()
        c = conn.cursor()

        c.execute('SELECT theme FROM schedule_themes WHERE schedule_id = ? ORDER BY use_order', (schedule_id,))
        themes = [row['theme'] for row in c.fetchall()]

        if not themes:
            conn.close()
            return None

        if theme_mode == 'same':
            theme = themes[0]
        elif theme_mode == 'different':
            # Count posts made for this schedule to rotate
            c.execute('SELECT COUNT(*) as cnt FROM posts WHERE schedule_id = ?', (schedule_id,))
            count = c.fetchone()['cnt']
            c.execute('SELECT COUNT(*) as cnt FROM pending_posts WHERE schedule_id = ?', (schedule_id,))
            count += c.fetchone()['cnt']
            theme = themes[count % len(themes)]
        else:  # mixed
            theme = random.choice(themes)

        conn.close()
        return theme

    def generate_content(self, theme):
        """Generate caption and image for a theme."""
        channel_desc = '''We are the Domestic Violence Center of Chester County (DVCCC),
        providing FREE, CONFIDENTIAL, LIFESAVING services to survivors of domestic violence
        in Chester County, PA.'''

        # Generate caption
        result = self.text_gen.generate_caption(theme, channel_description=channel_desc)
        caption = result['caption']

        # Generate image
        prompt = self.text_gen.generate_image_prompt(theme)
        img_result = self.img_gen.generate_image(prompt, size='1024x1024', style='natural')
        optimized = self.img_gen.optimize_for_instagram(img_result['image_path'])

        # Upload to hosting
        if self.uploader:
            image_url = self.uploader.upload(optimized)
        else:
            image_url = img_result['image_url']

        return caption, image_url

    def process_schedule(self, schedule):
        """Process a single schedule."""
        schedule_id = schedule['id']
        schedule_name = schedule['name']
        theme_mode = schedule['theme_mode']
        auto_post = schedule['auto_post']

        logger.info(f"Processing schedule: {schedule_name} (ID: {schedule_id})")

        # Pick theme
        theme = self.pick_theme(schedule_id, theme_mode)
        if not theme:
            logger.warning(f"No themes configured for schedule {schedule_id}")
            return

        logger.info(f"Theme: {theme[:50]}...")

        try:
            # Generate content
            caption, image_url = self.generate_content(theme)
            logger.info("Content generated successfully")

            conn = self.get_db()
            c = conn.cursor()

            scheduled_for = datetime.now().strftime('%Y-%m-%d %H:%M')

            if auto_post:
                # TODO: Actually post to Instagram here
                # For now, save as "posted"
                c.execute('''
                    INSERT INTO posts (theme, caption, image_url, scheduled_time, status, schedule_id)
                    VALUES (?, ?, ?, ?, 'posted', ?)
                ''', (theme, caption, image_url, scheduled_for, schedule_id))
                logger.info("Auto-posted (saved as posted)")
            else:
                # Add to pending review
                c.execute('''
                    INSERT INTO pending_posts (schedule_id, theme, caption, image_url, scheduled_for)
                    VALUES (?, ?, ?, ?, ?)
                ''', (schedule_id, theme, caption, image_url, scheduled_for))
                logger.info("Added to pending review queue")

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"Error generating content: {e}")

    def check_schedules(self):
        """Check and process due schedules."""
        due = self.get_due_schedules()
        if due:
            logger.info(f"Found {len(due)} schedule(s) to process")
            for schedule in due:
                self.process_schedule(dict(schedule))

    def run_loop(self):
        """Main scheduler loop."""
        logger.info("Web scheduler started")
        last_check = None

        while self.running:
            now = datetime.now()
            current_minute = now.strftime('%Y-%m-%d %H:%M')

            # Only check once per minute
            if current_minute != last_check:
                self.check_schedules()
                last_check = current_minute

            # Sleep for a short time before checking again
            time_module.sleep(10)

        logger.info("Web scheduler stopped")

    def start(self):
        """Start the scheduler in a background thread."""
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self.run_loop, daemon=True)
        self.thread.start()
        logger.info("Background web scheduler started")

    def stop(self):
        """Stop the scheduler."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Background web scheduler stopped")


# Global web scheduler instance
web_scheduler = WebContentScheduler()


def start_web_scheduler():
    """Start the background web scheduler."""
    web_scheduler.start()


def stop_web_scheduler():
    """Stop the background web scheduler."""
    web_scheduler.stop()
