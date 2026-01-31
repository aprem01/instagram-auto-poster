#!/usr/bin/env python3
"""
DVCCC Instagram Content Manager - Web Interface
"""

import os
import sys
import json
import sqlite3
import logging
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

# Import components with error handling
TextGenerator = None
ImageGenerator = None
ReachAmplify = None
get_uploader = None
start_web_scheduler = None
stop_web_scheduler = None

try:
    from src.content import TextGenerator, ImageGenerator
    logger.info("Content generators imported successfully")
except ImportError as e:
    logger.warning(f"Could not import content generators: {e}")

try:
    from src.content.reach_amplify import ReachAmplify
    logger.info("REACH Amplify imported successfully")
except ImportError as e:
    logger.warning(f"Could not import REACH Amplify: {e}")

try:
    from src.utils.image_hosting import get_uploader
    logger.info("Image uploader imported successfully")
except ImportError as e:
    logger.warning(f"Could not import image uploader: {e}")

try:
    from src.scheduler import start_web_scheduler, stop_web_scheduler
    logger.info("Scheduler imported successfully")
except ImportError as e:
    logger.warning(f"Could not import scheduler: {e}")

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Database setup
DB_PATH = 'scheduled_posts.db'

# ============== ERROR HANDLING HELPERS ==============

def check_api_keys():
    """Check if required API keys are configured."""
    issues = []
    if not os.getenv('OPENAI_API_KEY'):
        issues.append('OPENAI_API_KEY is not set')
    if not os.getenv('IMGBB_API_KEY'):
        issues.append('IMGBB_API_KEY is not set (image hosting may not work)')
    return issues

def parse_openai_error(error):
    """Parse OpenAI errors into user-friendly messages."""
    error_str = str(error).lower()

    if 'authentication' in error_str or 'api key' in error_str or 'invalid_api_key' in error_str:
        return {
            'title': 'API Key Error',
            'message': 'The OpenAI API key is invalid or not configured. Please check your OPENAI_API_KEY environment variable.',
            'action': 'Go to Render Dashboard → Environment → Add OPENAI_API_KEY'
        }
    elif 'rate_limit' in error_str or 'rate limit' in error_str:
        return {
            'title': 'Rate Limit Reached',
            'message': 'Too many requests to OpenAI. Please wait a moment and try again.',
            'action': 'Wait 30-60 seconds before trying again'
        }
    elif 'insufficient_quota' in error_str or 'quota' in error_str or 'billing' in error_str:
        return {
            'title': 'OpenAI Quota Exceeded',
            'message': 'Your OpenAI account has run out of credits or the billing limit has been reached.',
            'action': 'Check your OpenAI billing at platform.openai.com/account/billing'
        }
    elif 'content_policy' in error_str or 'safety' in error_str:
        return {
            'title': 'Content Policy',
            'message': 'The generated content was flagged by OpenAI\'s safety system. Please try a different theme.',
            'action': 'Try rephrasing your theme or use a suggested theme'
        }
    elif 'timeout' in error_str or 'timed out' in error_str:
        return {
            'title': 'Request Timeout',
            'message': 'The request to OpenAI took too long. This might be due to high demand.',
            'action': 'Please try again in a few moments'
        }
    elif 'connection' in error_str or 'network' in error_str:
        return {
            'title': 'Connection Error',
            'message': 'Could not connect to OpenAI servers. Please check your internet connection.',
            'action': 'Check network connectivity and try again'
        }
    else:
        return {
            'title': 'Generation Error',
            'message': f'An error occurred while generating content: {str(error)[:200]}',
            'action': 'Please try again or contact support if the issue persists'
        }


def init_db():
    """Initialize the database."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Posts table
    c.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            theme TEXT NOT NULL,
            caption TEXT NOT NULL,
            image_url TEXT NOT NULL,
            scheduled_time TEXT,
            status TEXT DEFAULT 'draft',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            schedule_id INTEGER,
            FOREIGN KEY (schedule_id) REFERENCES schedules(id)
        )
    ''')

    # Schedules table for recurring posts
    c.execute('''
        CREATE TABLE IF NOT EXISTS schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            theme_mode TEXT DEFAULT 'same',
            auto_post INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Schedule times (multiple times per schedule)
    c.execute('''
        CREATE TABLE IF NOT EXISTS schedule_times (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            schedule_id INTEGER NOT NULL,
            time_of_day TEXT NOT NULL,
            days_of_week TEXT DEFAULT '0,1,2,3,4,5,6',
            FOREIGN KEY (schedule_id) REFERENCES schedules(id)
        )
    ''')

    # Themes for schedules
    c.execute('''
        CREATE TABLE IF NOT EXISTS schedule_themes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            schedule_id INTEGER NOT NULL,
            theme TEXT NOT NULL,
            use_order INTEGER DEFAULT 0,
            FOREIGN KEY (schedule_id) REFERENCES schedules(id)
        )
    ''')

    # Pending posts awaiting review
    c.execute('''
        CREATE TABLE IF NOT EXISTS pending_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            schedule_id INTEGER,
            theme TEXT NOT NULL,
            caption TEXT NOT NULL,
            image_url TEXT NOT NULL,
            scheduled_for TEXT NOT NULL,
            status TEXT DEFAULT 'pending_review',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (schedule_id) REFERENCES schedules(id)
        )
    ''')

    conn.commit()
    conn.close()


def get_db():
    """Get database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# Initialize components with error handling
text_gen = None
img_gen = None
reach_amplify = None
uploader = None
initialization_errors = []

logger.info("Starting component initialization...")

try:
    if TextGenerator and ImageGenerator and os.getenv('OPENAI_API_KEY'):
        text_gen = TextGenerator(
            niche='domestic violence awareness',
            style='warm, personal, and empowering',
            hashtag_count=10
        )
        img_gen = ImageGenerator(output_dir='generated_images')
        logger.info("AI generators initialized successfully")

        # Initialize REACH Amplify for discovery optimization
        if ReachAmplify:
            reach_amplify = ReachAmplify(os.getenv('OPENAI_API_KEY'))
            logger.info("REACH Amplify initialized successfully")
    elif not os.getenv('OPENAI_API_KEY'):
        initialization_errors.append('OPENAI_API_KEY not configured - content generation disabled')
        logger.warning('OPENAI_API_KEY not configured')
    else:
        initialization_errors.append('Content generator modules not available')
        logger.warning('Content generator modules not available')
except Exception as e:
    initialization_errors.append(f'Failed to initialize AI generators: {str(e)}')
    logger.error(f'Failed to initialize AI generators: {e}')

try:
    if get_uploader:
        uploader = get_uploader()
        logger.info("Image uploader initialized successfully")
except Exception as e:
    initialization_errors.append(f'Image hosting not configured: {str(e)}')
    logger.warning(f'Image hosting not configured: {e}')

logger.info(f"Initialization complete. Errors: {initialization_errors if initialization_errors else 'None'}")


@app.route('/health')
def health():
    """Simple health check for load balancers."""
    return jsonify({'status': 'ok', 'message': 'DVCCC Instagram Manager is running'})


@app.route('/status')
def status():
    """Detailed configuration status."""
    api_issues = check_api_keys()
    return jsonify({
        'status': 'ok' if not api_issues else 'degraded',
        'generators_ready': text_gen is not None and img_gen is not None,
        'uploader_ready': uploader is not None,
        'issues': api_issues + initialization_errors
    })


@app.route('/')
def dashboard():
    """Dashboard - Overview and stats."""
    conn = get_db()
    c = conn.cursor()

    # Get stats
    c.execute('SELECT COUNT(*) as cnt FROM posts')
    total_posts = c.fetchone()['cnt']

    c.execute('SELECT COUNT(*) as cnt FROM posts WHERE status = "scheduled"')
    scheduled_posts = c.fetchone()['cnt']

    c.execute('SELECT COUNT(*) as cnt FROM posts WHERE status = "draft"')
    draft_posts = c.fetchone()['cnt']

    c.execute('SELECT COUNT(*) as cnt FROM pending_posts WHERE status = "pending_review"')
    pending_count = c.fetchone()['cnt']

    c.execute('SELECT COUNT(*) as cnt FROM schedules WHERE is_active = 1')
    active_schedules = c.fetchone()['cnt']

    # Posts this week
    week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    c.execute('SELECT COUNT(*) as cnt FROM posts WHERE created_at >= ?', (week_ago,))
    posts_this_week = c.fetchone()['cnt']

    # Recent posts
    c.execute('SELECT * FROM posts ORDER BY created_at DESC LIMIT 5')
    recent_posts = c.fetchall()

    # Upcoming scheduled posts
    c.execute('''
        SELECT * FROM posts
        WHERE status = 'scheduled' AND scheduled_time >= datetime('now')
        ORDER BY scheduled_time ASC LIMIT 5
    ''')
    upcoming = c.fetchall()

    conn.close()

    # Check configuration status
    config_issues = check_api_keys() + initialization_errors
    generators_ready = text_gen is not None and img_gen is not None

    return render_template('dashboard.html',
        total_posts=total_posts,
        scheduled_posts=scheduled_posts,
        draft_posts=draft_posts,
        pending_count=pending_count,
        active_schedules=active_schedules,
        posts_this_week=posts_this_week,
        recent_posts=recent_posts,
        upcoming=upcoming,
        config_issues=config_issues,
        generators_ready=generators_ready
    )


@app.route('/create')
def create_post():
    """Create new content page."""
    # Suggested themes
    themes = [
        "We see you, we believe you, and we are here for you",
        "Free confidential support available in Chester County",
        "Your journey to healing starts with one step",
        "You deserve to feel safe - help is available",
        "Hope lives here at DVCCC",
        "Our counselors are here to listen without judgment",
        "Every survivor has a story of strength",
        "Building healthy relationships after trauma"
    ]
    return render_template('index.html', themes=themes)


@app.route('/calendar')
def calendar():
    """Calendar view of scheduled posts."""
    conn = get_db()
    c = conn.cursor()

    # Get all scheduled and posted items for calendar
    c.execute('''
        SELECT id, theme, caption, image_url, scheduled_time, status, 'post' as type
        FROM posts
        WHERE scheduled_time IS NOT NULL AND scheduled_time != ''
        UNION ALL
        SELECT id, theme, caption, image_url, scheduled_for as scheduled_time, status, 'pending' as type
        FROM pending_posts
        WHERE status = 'pending_review'
        ORDER BY scheduled_time
    ''')
    events = c.fetchall()

    conn.close()

    # Convert to calendar format
    calendar_events = []
    for event in events:
        calendar_events.append({
            'id': event['id'],
            'title': event['theme'][:30] + '...' if len(event['theme']) > 30 else event['theme'],
            'start': event['scheduled_time'],
            'status': event['status'],
            'type': event['type'],
            'image_url': event['image_url']
        })

    return render_template('calendar.html', events=json.dumps(calendar_events))


@app.route('/generate', methods=['POST'])
def generate():
    """Generate content based on theme."""
    theme = request.form.get('theme', '').strip()

    if not theme:
        return jsonify({'error': 'Please provide a theme', 'title': 'Missing Theme'}), 400

    # Check if generators are available
    if not text_gen or not img_gen:
        api_issues = check_api_keys()
        return jsonify({
            'error': 'Content generation is not available.',
            'title': 'Configuration Required',
            'details': api_issues if api_issues else ['AI generators failed to initialize'],
            'action': 'Please configure the OPENAI_API_KEY environment variable in your deployment settings.'
        }), 503

    try:
        # Generate caption
        channel_desc = '''We are the Domestic Violence Center of Chester County (DVCCC),
        providing FREE, CONFIDENTIAL, LIFESAVING services to survivors of domestic violence
        in Chester County, PA.'''

        result = text_gen.generate_caption(theme, channel_description=channel_desc)
        caption = result['caption']

        # Generate image
        prompt = text_gen.generate_image_prompt(theme)
        img_result = img_gen.generate_image(prompt, size='1024x1024', style='natural')
        optimized = img_gen.optimize_for_instagram(img_result['image_path'])

        # Upload to hosting
        if uploader:
            image_url = uploader.upload(optimized)
        else:
            image_url = img_result['image_url']

        # REACH Amplify - AI-powered discovery & SEO optimization
        discovery_data = None
        if reach_amplify:
            try:
                discovery_data = reach_amplify.optimize_content(caption, prompt, theme)
                logger.info(f"REACH Amplify score: {discovery_data.get('discovery_score', {}).get('grade', 'N/A')}")
            except Exception as e:
                logger.warning(f"REACH Amplify optimization failed: {e}")

        response_data = {
            'success': True,
            'theme': theme,
            'caption': caption,
            'image_url': image_url
        }

        # Add REACH Amplify discovery optimization data (AI + SEO + AIO/GEO/AEO)
        if discovery_data:
            response_data['reach_amplify'] = {
                'hashtags': discovery_data.get('hashtags', []),
                'hashtag_string': discovery_data.get('hashtag_string', ''),
                'alt_text': discovery_data.get('alt_text', ''),
                'optimized_caption': discovery_data.get('optimized_caption', caption),
                'keywords': discovery_data.get('keywords', []),
                'discovery_score': discovery_data.get('discovery_score', {}),
                'tips': discovery_data.get('tips', []),
                'seo_analysis': discovery_data.get('seo_analysis', {}),
                'posting_times': discovery_data.get('posting_times', {}),
                'aio_optimization': discovery_data.get('aio_optimization', {})
            }

        return jsonify(response_data)

    except Exception as e:
        error_info = parse_openai_error(e)
        return jsonify({
            'error': error_info['message'],
            'title': error_info['title'],
            'action': error_info['action']
        }), 500


@app.route('/save', methods=['POST'])
def save_post():
    """Save post as draft or schedule it."""
    data = request.json

    theme = data.get('theme', '')
    caption = data.get('caption', '')
    image_url = data.get('image_url', '')
    scheduled_time = data.get('scheduled_time', '')
    status = 'scheduled' if scheduled_time else 'draft'

    conn = get_db()
    c = conn.cursor()
    c.execute('''
        INSERT INTO posts (theme, caption, image_url, scheduled_time, status)
        VALUES (?, ?, ?, ?, ?)
    ''', (theme, caption, image_url, scheduled_time, status))
    conn.commit()
    post_id = c.lastrowid
    conn.close()

    return jsonify({'success': True, 'post_id': post_id, 'status': status})


@app.route('/posts')
def posts():
    """View all posts."""
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM posts ORDER BY created_at DESC')
    all_posts = c.fetchall()
    conn.close()

    return render_template('posts.html', posts=all_posts)


@app.route('/post/<int:post_id>')
def view_post(post_id):
    """View a single post."""
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM posts WHERE id = ?', (post_id,))
    post = c.fetchone()
    conn.close()

    if not post:
        return "Post not found", 404

    return render_template('view_post.html', post=post)


@app.route('/post/<int:post_id>/delete', methods=['POST'])
def delete_post(post_id):
    """Delete a post."""
    conn = get_db()
    c = conn.cursor()
    c.execute('DELETE FROM posts WHERE id = ?', (post_id,))
    conn.commit()
    conn.close()

    return redirect(url_for('posts'))


@app.route('/post/<int:post_id>/copy')
def copy_post(post_id):
    """Get post data for copying."""
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM posts WHERE id = ?', (post_id,))
    post = c.fetchone()
    conn.close()

    if not post:
        return jsonify({'error': 'Post not found'}), 404

    return jsonify({
        'caption': post['caption'],
        'image_url': post['image_url']
    })


# ============== SCHEDULE MANAGEMENT ==============

@app.route('/schedules')
def schedules():
    """View all schedules."""
    conn = get_db()
    c = conn.cursor()

    # Get all schedules with their times and themes
    c.execute('SELECT * FROM schedules ORDER BY created_at DESC')
    all_schedules = c.fetchall()

    schedules_data = []
    for schedule in all_schedules:
        # Get times for this schedule
        c.execute('SELECT * FROM schedule_times WHERE schedule_id = ?', (schedule['id'],))
        times = c.fetchall()

        # Get themes for this schedule
        c.execute('SELECT * FROM schedule_themes WHERE schedule_id = ? ORDER BY use_order', (schedule['id'],))
        themes = c.fetchall()

        schedules_data.append({
            'schedule': schedule,
            'times': times,
            'themes': themes
        })

    conn.close()
    return render_template('schedules.html', schedules=schedules_data)


@app.route('/schedule/new')
def new_schedule():
    """Create a new schedule page."""
    # Suggested themes
    suggested_themes = [
        "We see you, we believe you, and we are here for you",
        "Free confidential support available in Chester County",
        "Your journey to healing starts with one step",
        "You deserve to feel safe - help is available",
        "Hope lives here at DVCCC",
        "Our counselors are here to listen without judgment",
        "Every survivor has a story of strength",
        "Building healthy relationships after trauma"
    ]
    return render_template('schedule_form.html', schedule=None, suggested_themes=suggested_themes)


@app.route('/schedule/create', methods=['POST'])
def create_schedule():
    """Create a new schedule."""
    data = request.json

    name = data.get('name', 'My Schedule')
    theme_mode = data.get('theme_mode', 'same')  # same, different, mixed
    auto_post = 1 if data.get('auto_post', False) else 0
    times = data.get('times', [])  # List of {time, days}
    themes = data.get('themes', [])  # List of theme strings

    conn = get_db()
    c = conn.cursor()

    # Create schedule
    c.execute('''
        INSERT INTO schedules (name, theme_mode, auto_post)
        VALUES (?, ?, ?)
    ''', (name, theme_mode, auto_post))
    schedule_id = c.lastrowid

    # Add times
    for t in times:
        time_of_day = t.get('time', '09:00')
        days = t.get('days', '0,1,2,3,4,5,6')
        c.execute('''
            INSERT INTO schedule_times (schedule_id, time_of_day, days_of_week)
            VALUES (?, ?, ?)
        ''', (schedule_id, time_of_day, days))

    # Add themes
    for i, theme in enumerate(themes):
        c.execute('''
            INSERT INTO schedule_themes (schedule_id, theme, use_order)
            VALUES (?, ?, ?)
        ''', (schedule_id, theme, i))

    conn.commit()
    conn.close()

    return jsonify({'success': True, 'schedule_id': schedule_id})


@app.route('/schedule/<int:schedule_id>')
def view_schedule(schedule_id):
    """View a single schedule."""
    conn = get_db()
    c = conn.cursor()

    c.execute('SELECT * FROM schedules WHERE id = ?', (schedule_id,))
    schedule = c.fetchone()

    if not schedule:
        return "Schedule not found", 404

    c.execute('SELECT * FROM schedule_times WHERE schedule_id = ?', (schedule_id,))
    times = c.fetchall()

    c.execute('SELECT * FROM schedule_themes WHERE schedule_id = ? ORDER BY use_order', (schedule_id,))
    themes = c.fetchall()

    conn.close()

    suggested_themes = [
        "We see you, we believe you, and we are here for you",
        "Free confidential support available in Chester County",
        "Your journey to healing starts with one step",
        "You deserve to feel safe - help is available",
        "Hope lives here at DVCCC",
        "Our counselors are here to listen without judgment",
        "Every survivor has a story of strength",
        "Building healthy relationships after trauma"
    ]

    return render_template('schedule_form.html',
                         schedule=schedule,
                         times=times,
                         themes=themes,
                         suggested_themes=suggested_themes)


@app.route('/schedule/<int:schedule_id>/update', methods=['POST'])
def update_schedule(schedule_id):
    """Update an existing schedule."""
    data = request.json

    name = data.get('name', 'My Schedule')
    theme_mode = data.get('theme_mode', 'same')
    auto_post = 1 if data.get('auto_post', False) else 0
    is_active = 1 if data.get('is_active', True) else 0
    times = data.get('times', [])
    themes = data.get('themes', [])

    conn = get_db()
    c = conn.cursor()

    # Update schedule
    c.execute('''
        UPDATE schedules SET name=?, theme_mode=?, auto_post=?, is_active=?
        WHERE id=?
    ''', (name, theme_mode, auto_post, is_active, schedule_id))

    # Delete old times and themes
    c.execute('DELETE FROM schedule_times WHERE schedule_id = ?', (schedule_id,))
    c.execute('DELETE FROM schedule_themes WHERE schedule_id = ?', (schedule_id,))

    # Add new times
    for t in times:
        time_of_day = t.get('time', '09:00')
        days = t.get('days', '0,1,2,3,4,5,6')
        c.execute('''
            INSERT INTO schedule_times (schedule_id, time_of_day, days_of_week)
            VALUES (?, ?, ?)
        ''', (schedule_id, time_of_day, days))

    # Add new themes
    for i, theme in enumerate(themes):
        c.execute('''
            INSERT INTO schedule_themes (schedule_id, theme, use_order)
            VALUES (?, ?, ?)
        ''', (schedule_id, theme, i))

    conn.commit()
    conn.close()

    return jsonify({'success': True})


@app.route('/schedule/<int:schedule_id>/delete', methods=['POST'])
def delete_schedule(schedule_id):
    """Delete a schedule."""
    conn = get_db()
    c = conn.cursor()
    c.execute('DELETE FROM schedule_times WHERE schedule_id = ?', (schedule_id,))
    c.execute('DELETE FROM schedule_themes WHERE schedule_id = ?', (schedule_id,))
    c.execute('DELETE FROM schedules WHERE id = ?', (schedule_id,))
    conn.commit()
    conn.close()

    return redirect(url_for('schedules'))


@app.route('/schedule/<int:schedule_id>/toggle', methods=['POST'])
def toggle_schedule(schedule_id):
    """Toggle a schedule active/inactive."""
    conn = get_db()
    c = conn.cursor()
    c.execute('UPDATE schedules SET is_active = NOT is_active WHERE id = ?', (schedule_id,))
    conn.commit()
    conn.close()

    return jsonify({'success': True})


# ============== PENDING POSTS (for review) ==============

@app.route('/pending')
def pending_posts():
    """View posts pending review."""
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT p.*, s.name as schedule_name
        FROM pending_posts p
        LEFT JOIN schedules s ON p.schedule_id = s.id
        WHERE p.status = 'pending_review'
        ORDER BY p.scheduled_for ASC
    ''')
    posts = c.fetchall()
    conn.close()

    return render_template('pending.html', posts=posts)


@app.route('/pending/<int:post_id>/approve', methods=['POST'])
def approve_pending(post_id):
    """Approve a pending post."""
    conn = get_db()
    c = conn.cursor()

    # Get the pending post
    c.execute('SELECT * FROM pending_posts WHERE id = ?', (post_id,))
    pending = c.fetchone()

    if pending:
        # Move to main posts table
        c.execute('''
            INSERT INTO posts (theme, caption, image_url, scheduled_time, status, schedule_id)
            VALUES (?, ?, ?, ?, 'scheduled', ?)
        ''', (pending['theme'], pending['caption'], pending['image_url'],
              pending['scheduled_for'], pending['schedule_id']))

        # Update pending status
        c.execute('UPDATE pending_posts SET status = "approved" WHERE id = ?', (post_id,))
        conn.commit()

    conn.close()
    return jsonify({'success': True})


@app.route('/pending/<int:post_id>/reject', methods=['POST'])
def reject_pending(post_id):
    """Reject a pending post."""
    conn = get_db()
    c = conn.cursor()
    c.execute('UPDATE pending_posts SET status = "rejected" WHERE id = ?', (post_id,))
    conn.commit()
    conn.close()

    return jsonify({'success': True})


@app.route('/pending/<int:post_id>/edit', methods=['POST'])
def edit_pending(post_id):
    """Edit a pending post."""
    data = request.json
    caption = data.get('caption', '')

    conn = get_db()
    c = conn.cursor()
    c.execute('UPDATE pending_posts SET caption = ? WHERE id = ?', (caption, post_id))
    conn.commit()
    conn.close()

    return jsonify({'success': True})


# ============== MANUAL GENERATE FOR SCHEDULE ==============

@app.route('/schedule/<int:schedule_id>/generate', methods=['POST'])
def generate_for_schedule(schedule_id):
    """Generate content for a schedule (manual trigger)."""
    conn = get_db()
    c = conn.cursor()

    c.execute('SELECT * FROM schedules WHERE id = ?', (schedule_id,))
    schedule = c.fetchone()

    if not schedule:
        return jsonify({'error': 'Schedule not found'}), 404

    c.execute('SELECT theme FROM schedule_themes WHERE schedule_id = ? ORDER BY use_order', (schedule_id,))
    themes = [row['theme'] for row in c.fetchall()]

    if not themes:
        return jsonify({'error': 'No themes configured for this schedule'}), 400

    # Pick theme based on mode
    import random
    theme_mode = schedule['theme_mode']
    if theme_mode == 'same':
        theme = themes[0]
    elif theme_mode == 'different':
        # Rotate through themes sequentially
        c.execute('SELECT COUNT(*) as cnt FROM posts WHERE schedule_id = ?', (schedule_id,))
        count = c.fetchone()['cnt']
        theme = themes[count % len(themes)]
    else:  # mixed
        theme = random.choice(themes)

    conn.close()

    # Check if generators are available
    if not text_gen or not img_gen:
        api_issues = check_api_keys()
        return jsonify({
            'error': 'Content generation is not available.',
            'title': 'Configuration Required',
            'details': api_issues,
            'action': 'Please configure the OPENAI_API_KEY environment variable.'
        }), 503

    try:
        # Generate caption
        channel_desc = '''We are the Domestic Violence Center of Chester County (DVCCC),
        providing FREE, CONFIDENTIAL, LIFESAVING services to survivors of domestic violence
        in Chester County, PA.'''

        result = text_gen.generate_caption(theme, channel_description=channel_desc)
        caption = result['caption']

        # Generate image
        prompt = text_gen.generate_image_prompt(theme)
        img_result = img_gen.generate_image(prompt, size='1024x1024', style='natural')
        optimized = img_gen.optimize_for_instagram(img_result['image_path'])

        # Upload to hosting
        if uploader:
            image_url = uploader.upload(optimized)
        else:
            image_url = img_result['image_url']

        return jsonify({
            'success': True,
            'theme': theme,
            'caption': caption,
            'image_url': image_url
        })

    except Exception as e:
        error_info = parse_openai_error(e)
        return jsonify({
            'error': error_info['message'],
            'title': error_info['title'],
            'action': error_info['action']
        }), 500


# ============== REGENERATE OPTIONS ==============

@app.route('/regenerate/caption', methods=['POST'])
def regenerate_caption():
    """Regenerate only the caption for a theme."""
    data = request.json
    theme = data.get('theme', '').strip()

    if not theme:
        return jsonify({'error': 'Please provide a theme', 'title': 'Missing Theme'}), 400

    if not text_gen:
        return jsonify({
            'error': 'Caption generation is not available.',
            'title': 'Configuration Required',
            'action': 'Please configure the OPENAI_API_KEY environment variable.'
        }), 503

    try:
        channel_desc = '''We are the Domestic Violence Center of Chester County (DVCCC),
        providing FREE, CONFIDENTIAL, LIFESAVING services to survivors of domestic violence
        in Chester County, PA.'''

        result = text_gen.generate_caption(theme, channel_description=channel_desc)
        return jsonify({
            'success': True,
            'caption': result['caption']
        })

    except Exception as e:
        error_info = parse_openai_error(e)
        return jsonify({
            'error': error_info['message'],
            'title': error_info['title'],
            'action': error_info['action']
        }), 500


@app.route('/regenerate/image', methods=['POST'])
def regenerate_image():
    """Regenerate only the image for a theme."""
    data = request.json
    theme = data.get('theme', '').strip()

    if not theme:
        return jsonify({'error': 'Please provide a theme', 'title': 'Missing Theme'}), 400

    if not text_gen or not img_gen:
        return jsonify({
            'error': 'Image generation is not available.',
            'title': 'Configuration Required',
            'action': 'Please configure the OPENAI_API_KEY environment variable.'
        }), 503

    try:
        prompt = text_gen.generate_image_prompt(theme)
        img_result = img_gen.generate_image(prompt, size='1024x1024', style='natural')
        optimized = img_gen.optimize_for_instagram(img_result['image_path'])

        if uploader:
            image_url = uploader.upload(optimized)
        else:
            image_url = img_result['image_url']

        return jsonify({
            'success': True,
            'image_url': image_url
        })

    except Exception as e:
        error_info = parse_openai_error(e)
        return jsonify({
            'error': error_info['message'],
            'title': error_info['title'],
            'action': error_info['action']
        }), 500


# ============== VIDEO GENERATION ==============

@app.route('/video')
def video_page():
    """Video generation page."""
    themes = [
        "We see you, we believe you, and we are here for you",
        "Free confidential support available in Chester County",
        "Your journey to healing starts with one step",
        "You deserve to feel safe - help is available",
        "Hope lives here at DVCCC"
    ]
    return render_template('video.html', themes=themes)


@app.route('/generate/video', methods=['POST'])
def generate_video():
    """Generate a video using AI."""
    data = request.json
    theme = data.get('theme', '').strip()
    video_type = data.get('video_type', 'slideshow')  # slideshow, animation, or ai_generated

    if not theme:
        return jsonify({'error': 'Please provide a theme', 'title': 'Missing Theme'}), 400

    if not text_gen or not img_gen:
        return jsonify({
            'error': 'Content generation is not available.',
            'title': 'Configuration Required',
            'action': 'Please configure the OPENAI_API_KEY environment variable.'
        }), 503

    try:
        # Generate caption for the video
        channel_desc = '''We are the Domestic Violence Center of Chester County (DVCCC),
        providing FREE, CONFIDENTIAL, LIFESAVING services to survivors of domestic violence
        in Chester County, PA.'''

        result = text_gen.generate_caption(theme, channel_description=channel_desc)
        caption = result['caption']

        if video_type == 'slideshow':
            # Generate multiple images for slideshow
            images = []
            for i in range(3):  # Generate 3 images
                prompt = text_gen.generate_image_prompt(theme)
                img_result = img_gen.generate_image(prompt, size='1024x1024', style='natural')
                optimized = img_gen.optimize_for_instagram(img_result['image_path'])

                if uploader:
                    image_url = uploader.upload(optimized)
                else:
                    image_url = img_result['image_url']
                images.append(image_url)

            return jsonify({
                'success': True,
                'video_type': 'slideshow',
                'theme': theme,
                'caption': caption,
                'images': images,
                'message': 'Slideshow images generated! Use these in Instagram Reels or a video editor.'
            })

        elif video_type == 'ai_generated':
            # For AI video generation, we'd use a service like Runway, Pika, or similar
            # For now, return info about the feature
            return jsonify({
                'success': True,
                'video_type': 'ai_generated',
                'theme': theme,
                'caption': caption,
                'message': 'AI video generation requires additional API setup (Runway ML, Pika Labs, etc.)',
                'prompt': text_gen.generate_image_prompt(theme)
            })

        else:
            return jsonify({'error': 'Invalid video type', 'title': 'Invalid Option'}), 400

    except Exception as e:
        error_info = parse_openai_error(e)
        return jsonify({
            'error': error_info['message'],
            'title': error_info['title'],
            'action': error_info['action']
        }), 500


# ============== API ENDPOINTS ==============

@app.route('/api/calendar/events')
def api_calendar_events():
    """API endpoint for calendar events."""
    conn = get_db()
    c = conn.cursor()

    c.execute('''
        SELECT id, theme, scheduled_time, status, 'post' as type
        FROM posts
        WHERE scheduled_time IS NOT NULL AND scheduled_time != ''
        UNION ALL
        SELECT id, theme, scheduled_for as scheduled_time, status, 'pending' as type
        FROM pending_posts
        WHERE status = 'pending_review'
    ''')
    events = c.fetchall()
    conn.close()

    return jsonify([dict(e) for e in events])


@app.route('/api/smart-themes')
def api_smart_themes():
    """API endpoint for AI-generated smart theme ideas with optional preference filtering."""
    preference = request.args.get('preference', None)

    # Static fallback themes with full SEO/AIO data
    static_themes = [
        {
            "theme": "We see you, we believe you, and we are here for you",
            "type": "supportive",
            "priority": "high",
            "seo_keywords": ["domestic violence support", "DV help", "believe survivors"],
            "aio_query": "where can i get help for domestic violence"
        },
        {
            "theme": "Free confidential support in Chester County",
            "type": "resource",
            "priority": "high",
            "seo_keywords": ["free DV services", "Chester County help", "confidential support"],
            "aio_query": "free domestic violence help near me"
        },
        {
            "theme": "Your journey to healing starts with one step",
            "type": "empowerment",
            "priority": "medium",
            "seo_keywords": ["healing from abuse", "trauma recovery", "survivor healing"],
            "aio_query": "how do i start healing from abuse"
        },
        {
            "theme": "You deserve to feel safe - help is available",
            "type": "supportive",
            "priority": "high",
            "seo_keywords": ["feel safe", "abuse help", "safety resources"],
            "aio_query": "i dont feel safe at home what do i do"
        },
        {
            "theme": "Recognizing warning signs in relationships",
            "type": "educational",
            "priority": "high",
            "seo_keywords": ["red flags relationship", "abuse signs", "unhealthy relationship"],
            "aio_query": "is my relationship abusive"
        },
        {
            "theme": "Our counselors listen without judgment",
            "type": "resource",
            "priority": "medium",
            "seo_keywords": ["DV counseling", "free counseling", "support services"],
            "aio_query": "where can i talk to someone about abuse"
        },
        {
            "theme": "Every survivor has a story of strength",
            "type": "empowerment",
            "priority": "medium",
            "seo_keywords": ["survivor stories", "abuse survivor", "strength"],
            "aio_query": "am i strong enough to leave"
        },
        {
            "theme": "Building healthy relationships after trauma",
            "type": "educational",
            "priority": "medium",
            "seo_keywords": ["healthy relationships", "dating after abuse", "trust again"],
            "aio_query": "can i have a healthy relationship after abuse"
        }
    ]

    if not reach_amplify:
        # Filter by preference if specified
        themes = static_themes
        if preference and preference != 'all':
            if preference == 'trending':
                themes = [t for t in static_themes if t['priority'] in ['trending', 'high']]
            else:
                themes = [t for t in static_themes if t['type'] == preference]

        return jsonify({
            'success': True,
            'source': 'static',
            'themes': themes
        })

    try:
        themes = reach_amplify.generate_smart_themes(count=8)

        # Filter by preference if specified
        if preference and preference != 'all':
            if preference == 'trending':
                themes = [t for t in themes if t.get('priority') in ['trending', 'high']]
            else:
                themes = [t for t in themes if t.get('type') == preference]

        return jsonify({
            'success': True,
            'source': 'ai',
            'themes': themes
        })
    except Exception as e:
        logger.error(f"Smart themes generation failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'themes': []
        }), 500


@app.route('/api/optimize-content', methods=['POST'])
def api_optimize_content():
    """API endpoint to optimize manual content with REACH Amplify."""
    data = request.json
    caption = data.get('caption', '').strip()
    topic = data.get('topic', 'domestic violence awareness').strip()

    if not caption:
        return jsonify({'success': False, 'error': 'Caption is required'}), 400

    if not reach_amplify:
        return jsonify({
            'success': False,
            'error': 'REACH Amplify not available. Please configure OPENAI_API_KEY.'
        }), 503

    try:
        # Generate a simple image prompt for alt text generation
        image_prompt = f"Supportive image for: {topic}"
        discovery_data = reach_amplify.optimize_content(caption, image_prompt, topic)

        return jsonify({
            'success': True,
            'reach_amplify': {
                'hashtags': discovery_data.get('hashtags', []),
                'hashtag_string': discovery_data.get('hashtag_string', ''),
                'alt_text': discovery_data.get('alt_text', ''),
                'keywords': discovery_data.get('keywords', []),
                'discovery_score': discovery_data.get('discovery_score', {}),
                'tips': discovery_data.get('tips', []),
                'seo_analysis': discovery_data.get('seo_analysis', {})
            }
        })
    except Exception as e:
        logger.error(f"Content optimization failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/keyword-trends', methods=['POST'])
def api_keyword_trends():
    """API endpoint to find trends based on user keywords using SEO/AIO analysis."""
    data = request.json
    keywords = data.get('keywords', [])

    if not keywords or not isinstance(keywords, list):
        return jsonify({'success': False, 'error': 'Keywords array is required'}), 400

    if len(keywords) > 10:
        keywords = keywords[:10]  # Limit to 10 keywords

    if not reach_amplify:
        return jsonify({
            'success': False,
            'error': 'REACH Amplify not available. Please configure OPENAI_API_KEY.'
        }), 503

    try:
        # Generate keyword-based trends using REACH Amplify
        trend_data = reach_amplify.analyze_keywords_for_trends(keywords)

        return jsonify({
            'success': True,
            'keywords': keywords,
            'seo_insights': trend_data.get('seo_insights', {}),
            'aio_queries': trend_data.get('aio_queries', []),
            'themes': trend_data.get('themes', []),
            'hashtags': trend_data.get('hashtags', [])
        })
    except Exception as e:
        logger.error(f"Keyword trend analysis failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/campaign-modes')
def api_campaign_modes():
    """Get all available campaign modes."""
    if not reach_amplify:
        # Return static config if REACH Amplify not available
        return jsonify({
            'success': True,
            'modes': {
                "awareness": {"name": "Awareness", "icon": "📢", "description": "General DV awareness"},
                "fundraising": {"name": "Fundraising", "icon": "💝", "description": "Donor engagement"},
                "events": {"name": "Events", "icon": "📅", "description": "Event promotion"},
                "youth": {"name": "Youth Outreach", "icon": "🎯", "description": "Teen outreach"}
            }
        })

    return jsonify({
        'success': True,
        'modes': reach_amplify.get_campaign_modes()
    })


@app.route('/api/campaign-optimize', methods=['POST'])
def api_campaign_optimize():
    """Optimize content for a specific campaign mode."""
    data = request.json
    caption = data.get('caption', '')
    topic = data.get('topic', '')
    campaign_mode = data.get('campaign_mode', 'awareness')

    if not reach_amplify:
        return jsonify({'success': False, 'error': 'REACH Amplify not available'}), 503

    try:
        result = reach_amplify.optimize_for_campaign(caption, topic, campaign_mode)
        return jsonify({'success': True, **result})
    except Exception as e:
        logger.error(f"Campaign optimization failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/platforms')
def api_platforms():
    """Get all platform configurations."""
    if not reach_amplify:
        return jsonify({
            'success': True,
            'platforms': {
                "facebook": {"name": "Facebook", "icon": "📘", "tips": ["Use 1-3 hashtags"]},
                "linkedin": {"name": "LinkedIn", "icon": "💼", "tips": ["Professional tone"]},
                "tiktok": {"name": "TikTok", "icon": "🎵", "tips": ["Short captions"]}
            }
        })

    return jsonify({
        'success': True,
        'platforms': reach_amplify.get_all_platforms()
    })


@app.route('/api/platform-tips/<platform>')
def api_platform_tips(platform):
    """Get tips for a specific platform."""
    if not reach_amplify:
        return jsonify({'success': False, 'error': 'Not available'}), 503

    tips = reach_amplify.get_platform_tips(platform)
    if not tips:
        return jsonify({'success': False, 'error': 'Platform not found'}), 404

    return jsonify({'success': True, 'platform': platform, **tips})


@app.route('/api/adapt-for-platform', methods=['POST'])
def api_adapt_for_platform():
    """
    Adapt Instagram caption for a specific platform.

    Request body:
        - caption: str (required) - Original Instagram caption
        - platform: str (required) - Target platform (facebook, linkedin, tiktok)
        - topic: str (optional) - Topic for context-aware adaptation
        - campaign_mode: str (optional) - Campaign mode for tone adjustment

    Returns:
        Adapted caption with platform-specific optimizations
    """
    import re

    data = request.json or {}
    caption = data.get('caption', '').strip()
    platform = data.get('platform', '').lower()
    topic = data.get('topic', '')
    campaign_mode = data.get('campaign_mode', 'awareness')

    if not caption:
        return jsonify({'success': False, 'error': 'Caption is required'}), 400

    if platform not in ['facebook', 'linkedin', 'tiktok']:
        return jsonify({'success': False, 'error': 'Invalid platform. Use: facebook, linkedin, tiktok'}), 400

    # Platform character limits and hashtag counts
    platform_config = {
        'facebook': {'char_limit': 500, 'hashtag_count': 3, 'tone': 'conversational'},
        'linkedin': {'char_limit': 1300, 'hashtag_count': 5, 'tone': 'professional'},
        'tiktok': {'char_limit': 150, 'hashtag_count': 5, 'tone': 'casual'}
    }

    config = platform_config[platform]

    if not reach_amplify:
        # Fallback: basic adaptation without AI
        hashtags = re.findall(r'#\w+', caption)
        clean_caption = re.sub(r'#\w+\s*', '', caption).strip()

        # Truncate if needed
        char_limit = config['char_limit']
        if len(clean_caption) > char_limit - 50:
            clean_caption = clean_caption[:char_limit-53] + '...'

        # Add limited hashtags
        selected_hashtags = hashtags[:config['hashtag_count']]
        if selected_hashtags:
            adapted = clean_caption + '\n\n' + ' '.join(selected_hashtags)
        else:
            adapted = clean_caption

        return jsonify({
            'success': True,
            'source': 'fallback',
            'platform': platform,
            'adapted_caption': adapted,
            'hashtags': selected_hashtags,
            'char_count': len(adapted),
            'char_limit': config['char_limit'],
            'within_limit': len(adapted) <= config['char_limit'],
            'tips': []
        })

    try:
        result = reach_amplify.adapt_for_platform(caption, platform, topic, campaign_mode)
        return jsonify({
            'success': True,
            **result
        })
    except Exception as e:
        logger.error(f"Platform adaptation failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/event-optimize', methods=['POST'])
def api_event_optimize():
    """Optimize content for an event."""
    data = request.json
    event_name = data.get('event_name', '')
    event_type = data.get('event_type', 'community')
    event_date = data.get('event_date', '')
    location = data.get('location', 'Chester County')

    if not event_name:
        return jsonify({'success': False, 'error': 'Event name required'}), 400

    if not reach_amplify:
        return jsonify({'success': False, 'error': 'Not available'}), 503

    try:
        result = reach_amplify.optimize_for_event(event_name, event_type, event_date, location)
        return jsonify({'success': True, **result})
    except Exception as e:
        logger.error(f"Event optimization failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/fundraising')
def api_fundraising():
    """Get fundraising optimization data."""
    if not reach_amplify:
        return jsonify({
            'success': True,
            'donor_hashtags': ["#GivingTuesday", "#NonprofitLove"],
            'tips': ["Share impact metrics"]
        })

    return jsonify({
        'success': True,
        **reach_amplify.get_fundraising_optimization()
    })


@app.route('/api/instagram-status')
def api_instagram_status():
    """Check if Instagram API is configured."""
    # Check for required Instagram API environment variables
    access_token = os.getenv('INSTAGRAM_ACCESS_TOKEN')
    account_id = os.getenv('INSTAGRAM_ACCOUNT_ID')

    configured = bool(access_token and account_id)

    return jsonify({
        'configured': configured,
        'has_token': bool(access_token),
        'has_account_id': bool(account_id)
    })


@app.route('/api/post-to-instagram', methods=['POST'])
def api_post_to_instagram():
    """Post content directly to Instagram using Graph API."""
    access_token = os.getenv('INSTAGRAM_ACCESS_TOKEN')
    account_id = os.getenv('INSTAGRAM_ACCOUNT_ID')

    if not access_token or not account_id:
        return jsonify({
            'success': False,
            'error': 'Instagram API not configured. Please set INSTAGRAM_ACCESS_TOKEN and INSTAGRAM_ACCOUNT_ID environment variables.'
        }), 503

    data = request.json
    caption = data.get('caption', '').strip()
    image_url = data.get('image_url', '').strip()

    if not caption or not image_url:
        return jsonify({'success': False, 'error': 'Caption and image URL are required'}), 400

    # Instagram Graph API requires a publicly accessible image URL
    if image_url.startswith('data:'):
        return jsonify({
            'success': False,
            'error': 'Instagram requires a public image URL. Please use AI-generated content or upload to a hosting service first.'
        }), 400

    try:
        import requests

        # Step 1: Create media container
        container_url = f"https://graph.facebook.com/v18.0/{account_id}/media"
        container_response = requests.post(container_url, data={
            'image_url': image_url,
            'caption': caption,
            'access_token': access_token
        })
        container_data = container_response.json()

        if 'error' in container_data:
            logger.error(f"Instagram container error: {container_data['error']}")
            return jsonify({
                'success': False,
                'error': container_data['error'].get('message', 'Failed to create media container')
            }), 400

        container_id = container_data.get('id')
        if not container_id:
            return jsonify({'success': False, 'error': 'Failed to get container ID'}), 500

        # Step 2: Publish the media
        publish_url = f"https://graph.facebook.com/v18.0/{account_id}/media_publish"
        publish_response = requests.post(publish_url, data={
            'creation_id': container_id,
            'access_token': access_token
        })
        publish_data = publish_response.json()

        if 'error' in publish_data:
            logger.error(f"Instagram publish error: {publish_data['error']}")
            return jsonify({
                'success': False,
                'error': publish_data['error'].get('message', 'Failed to publish media')
            }), 400

        post_id = publish_data.get('id')
        logger.info(f"Successfully posted to Instagram: {post_id}")

        return jsonify({
            'success': True,
            'post_id': post_id,
            'message': 'Successfully posted to Instagram!'
        })

    except Exception as e:
        logger.error(f"Instagram posting failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/debug-config')
def debug_config():
    """Debug endpoint to check API key configuration."""
    api_key = os.getenv('OPENAI_API_KEY', '')
    return jsonify({
        'openai_key_set': bool(api_key),
        'openai_key_length': len(api_key) if api_key else 0,
        'openai_key_prefix': api_key[:10] + '...' if api_key and len(api_key) > 10 else 'NOT SET',
        'text_gen_initialized': text_gen is not None,
        'img_gen_initialized': img_gen is not None,
        'reach_amplify_initialized': reach_amplify is not None,
        'initialization_errors': initialization_errors
    })


# ============== FUNDRAISING IMPACT CALCULATOR ==============

@app.route('/api/fundraising/impact-calculator', methods=['POST'])
def api_impact_calculator():
    """
    Calculate the real-world impact of a donation amount.

    Request body:
        - amount: int (required) - Donation amount in dollars
        - impact_type: str (optional) - Specific impact type to calculate

    Returns:
        Impact breakdown with messaging suggestions
    """
    data = request.json or {}
    amount = data.get('amount')
    impact_type = data.get('impact_type')

    if not amount or not isinstance(amount, (int, float)) or amount <= 0:
        return jsonify({
            'success': False,
            'error': 'A positive donation amount is required'
        }), 400

    if not reach_amplify:
        # Use static calculation if REACH Amplify not available
        presets = [25, 50, 100, 250, 500, 1000]
        return jsonify({
            'success': True,
            'amount': int(amount),
            'formatted_amount': f"${int(amount):,}",
            'presets': presets,
            'message': f"Your gift of ${int(amount)} makes a difference in survivors' lives.",
            'source': 'static'
        })

    try:
        result = reach_amplify.calculate_donation_impact(int(amount), impact_type)
        result['success'] = True
        result['presets'] = reach_amplify.get_impact_presets()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Impact calculator failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============== AWARENESS CALENDAR ==============

@app.route('/api/awareness/calendar')
def api_awareness_calendar():
    """
    Get awareness calendar information.

    Query params:
        - month: int (optional) - Specific month (1-12)
        - year: int (optional) - Specific year

    Returns:
        Awareness months and special days
    """
    month = request.args.get('month', type=int)
    year = request.args.get('year', type=int)

    if not reach_amplify:
        # Return static calendar data
        return jsonify({
            'success': True,
            'source': 'static',
            'months': {
                10: {'name': 'Domestic Violence Awareness Month', 'short': 'DVAM'},
                2: {'name': 'Teen Dating Violence Awareness Month', 'short': 'TDVAM'}
            },
            'special_days': []
        })

    try:
        result = reach_amplify.get_awareness_calendar(month, year)
        result['success'] = True
        return jsonify(result)
    except Exception as e:
        logger.error(f"Awareness calendar failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/awareness/upcoming')
def api_upcoming_awareness():
    """
    Get upcoming awareness days.

    Query params:
        - days: int (optional) - Number of days to look ahead (default 30)

    Returns:
        List of upcoming awareness events
    """
    days_ahead = request.args.get('days', 30, type=int)

    if not reach_amplify:
        return jsonify({
            'success': True,
            'source': 'static',
            'upcoming': []
        })

    try:
        upcoming = reach_amplify.get_upcoming_awareness_days(days_ahead)
        return jsonify({
            'success': True,
            'days_ahead': days_ahead,
            'upcoming': upcoming
        })
    except Exception as e:
        logger.error(f"Upcoming awareness failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/awareness-calendar')
def api_awareness_calendar_frontend():
    """
    Get awareness calendar for frontend display.
    This endpoint is specifically formatted for the frontend JavaScript.

    Query params:
        - days: int (optional) - Number of days to look ahead (default 90)

    Returns:
        {success: true, days: [...]} format for frontend consumption
    """
    days_ahead = request.args.get('days', 90, type=int)

    # Static fallback data with proper future date calculations
    def get_static_awareness_days():
        from datetime import datetime, timedelta
        import calendar

        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        days = []

        # Define awareness months with their details
        awareness_months = {
            1: {"name": "Human Trafficking Awareness Month", "category": "Human Trafficking"},
            2: {"name": "Teen Dating Violence Awareness Month", "category": "Youth"},
            4: {"name": "Sexual Assault Awareness Month", "category": "Sexual Assault"},
            10: {"name": "Domestic Violence Awareness Month", "category": "DV Related"}
        }

        # Check current and upcoming months
        for month_num, info in awareness_months.items():
            # Calculate the start of this awareness month
            year = today.year
            if month_num < today.month:
                year += 1  # Next year

            month_start = datetime(year, month_num, 1)
            last_day = calendar.monthrange(year, month_num)[1]
            month_end = datetime(year, month_num, last_day)

            # Check if we're currently IN this month (active) or if it's upcoming
            is_active = month_start <= today <= month_end

            if is_active:
                days_away = 0
                days.append({
                    "date": today.strftime("%Y-%m-%d"),
                    "name": info["name"],
                    "type": "Month",
                    "days_away": days_away,
                    "is_active": True,
                    "category": info["category"]
                })
            elif month_start > today:
                days_away = (month_start - today).days
                if days_away <= days_ahead:
                    days.append({
                        "date": month_start.strftime("%Y-%m-%d"),
                        "name": info["name"],
                        "type": "Month",
                        "days_away": days_away,
                        "is_active": False,
                        "category": info["category"]
                    })

        # Add some special days
        special_days = [
            {"month": 2, "day": 14, "name": "V-Day / One Billion Rising", "category": "Women's Issues"},
            {"month": 3, "day": 8, "name": "International Women's Day", "category": "Women's Issues"},
            {"month": 11, "day": 25, "name": "International Day for the Elimination of Violence Against Women", "category": "DV Related"}
        ]

        for special in special_days:
            year = today.year
            special_date = datetime(year, special["month"], special["day"])

            # If the date has passed this year, use next year
            if special_date <= today:
                year += 1
                special_date = datetime(year, special["month"], special["day"])

            days_away = (special_date - today).days
            if days_away > 0 and days_away <= days_ahead:
                days.append({
                    "date": special_date.strftime("%Y-%m-%d"),
                    "name": special["name"],
                    "type": "Day",
                    "days_away": days_away,
                    "is_active": False,
                    "category": special["category"]
                })

        # Sort by days_away (nearest first)
        days.sort(key=lambda x: x["days_away"])

        return days[:6]  # Return top 6

    if not reach_amplify:
        return jsonify({
            'success': True,
            'source': 'static',
            'days': get_static_awareness_days()
        })

    try:
        upcoming = reach_amplify.get_upcoming_awareness_days(days_ahead)

        # Transform the data to match frontend expectations
        days = []
        for item in upcoming:
            day_data = {
                "date": item.get("date", item.get("start_date", "")),
                "name": item.get("name", ""),
                "type": "Month" if item.get("type") == "month" else "Day",
                "days_away": item.get("days_away", 0),
                "is_active": item.get("is_active", False),
                "category": item.get("category", "Community")
            }
            days.append(day_data)

        return jsonify({
            'success': True,
            'days': days[:6]  # Return top 6 items
        })
    except Exception as e:
        logger.error(f"Awareness calendar failed: {e}")
        # Fall back to static data on error
        return jsonify({
            'success': True,
            'source': 'static_fallback',
            'days': get_static_awareness_days()
        })


@app.route('/api/awareness/generate', methods=['POST'])
def api_generate_awareness_post():
    """
    Generate a post for an awareness period or special day.

    Request body:
        - awareness_type: str (required) - Type of awareness (e.g., 'october', 'purple_thursday')
        - date: str (optional) - Date for context

    Returns:
        Post content and suggestions
    """
    data = request.json or {}
    awareness_type = data.get('awareness_type')
    date = data.get('date')

    if not awareness_type:
        return jsonify({
            'success': False,
            'error': 'awareness_type is required'
        }), 400

    if not reach_amplify:
        return jsonify({
            'success': False,
            'error': 'REACH Amplify not available'
        }), 503

    try:
        result = reach_amplify.generate_awareness_post(awareness_type, date)
        if 'error' in result:
            return jsonify({'success': False, **result}), 400
        result['success'] = True
        return jsonify(result)
    except Exception as e:
        logger.error(f"Awareness post generation failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============== VOLUNTEER RECRUITMENT ==============

@app.route('/api/volunteer/roles')
def api_volunteer_roles():
    """
    Get all available volunteer roles.

    Returns:
        Dict of volunteer roles with requirements
    """
    if not reach_amplify:
        # Return static volunteer roles
        return jsonify({
            'success': True,
            'source': 'static',
            'roles': {
                'hotline': {'title': 'Crisis Hotline Volunteer', 'commitment': '4 hrs/week'},
                'shelter': {'title': 'Shelter Support', 'commitment': 'Flexible'},
                'children': {'title': "Children's Program", 'commitment': '2-4 hrs/week'},
                'admin': {'title': 'Administrative', 'commitment': 'Remote OK'},
                'event': {'title': 'Event Support', 'commitment': 'As needed'}
            }
        })

    try:
        roles = reach_amplify.get_volunteer_roles()
        return jsonify({
            'success': True,
            'roles': roles
        })
    except Exception as e:
        logger.error(f"Volunteer roles failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/volunteer/generate', methods=['POST'])
def api_generate_volunteer_post():
    """
    Generate a volunteer recruitment post.

    Request body:
        - role: str (optional) - Specific volunteer role
        - urgency: str (optional) - Urgency level (ongoing, urgent, immediate)

    Returns:
        Volunteer recruitment post content
    """
    data = request.json or {}
    role = data.get('role')
    urgency = data.get('urgency', 'ongoing')

    if not reach_amplify:
        return jsonify({
            'success': False,
            'error': 'REACH Amplify not available'
        }), 503

    try:
        result = reach_amplify.generate_volunteer_post(role, urgency)
        result['success'] = True
        return jsonify(result)
    except Exception as e:
        logger.error(f"Volunteer post generation failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============== GIVING TUESDAY ==============

@app.route('/api/giving-tuesday/<int:year>')
def api_giving_tuesday(year):
    """
    Get Giving Tuesday information for a specific year.

    Path params:
        - year: int - Year to get Giving Tuesday date for

    Query params:
        - goal: int (optional) - Fundraising goal for campaign generation
        - matching: bool (optional) - Whether matching gifts are available

    Returns:
        Giving Tuesday date and optional campaign content
    """
    goal = request.args.get('goal', type=int)
    matching = request.args.get('matching', 'false').lower() == 'true'

    if not reach_amplify:
        # Calculate date without REACH Amplify
        from datetime import datetime, timedelta
        import calendar

        november = calendar.Calendar().itermonthdays2(year, 11)
        thursdays = [day for day, weekday in november if day != 0 and weekday == 3]

        if len(thursdays) >= 4:
            thanksgiving_day = thursdays[3]
            thanksgiving = datetime(year, 11, thanksgiving_day)
            giving_tuesday = thanksgiving + timedelta(days=5)
            date_str = giving_tuesday.strftime("%Y-%m-%d")
        else:
            date_str = ""

        return jsonify({
            'success': True,
            'year': year,
            'date': date_str,
            'source': 'static'
        })

    try:
        date = reach_amplify.get_giving_tuesday_date(year)
        result = {
            'success': True,
            'year': year,
            'date': date
        }

        # Generate full campaign if goal is provided
        if goal and goal > 0:
            campaign = reach_amplify.generate_giving_tuesday_campaign(goal, matching)
            result['campaign'] = campaign

        return jsonify(result)
    except Exception as e:
        logger.error(f"Giving Tuesday failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============== TRANSLATION / MULTI-LANGUAGE ==============

@app.route('/api/translate', methods=['POST'])
def api_translate():
    """
    Translate a caption to another language.

    Request body:
        - caption: str (required) - Text to translate
        - target_lang: str (optional) - Target language code (default: 'es')

    Returns:
        Translated text with language-specific hashtags
    """
    data = request.json or {}
    caption = data.get('caption', '').strip()
    target_lang = data.get('target_lang', 'es')

    if not caption:
        return jsonify({
            'success': False,
            'error': 'Caption text is required'
        }), 400

    if not reach_amplify:
        return jsonify({
            'success': False,
            'error': 'REACH Amplify not available for translation'
        }), 503

    try:
        result = reach_amplify.translate_caption(caption, target_lang)
        if 'error' in result and not result.get('translated'):
            return jsonify({'success': False, 'error': result['error']}), 500
        result['success'] = True
        return jsonify(result)
    except Exception as e:
        logger.error(f"Translation failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/languages')
def api_languages():
    """
    Get available languages and their hashtags.

    Returns:
        List of supported languages with hashtag sets
    """
    if not reach_amplify:
        return jsonify({
            'success': True,
            'source': 'static',
            'languages': {
                'en': {'name': 'English', 'hashtags': ['#DomesticViolenceAwareness']},
                'es': {'name': 'Spanish', 'hashtags': ['#ViolenciaDomestica', '#NoEstasSola']}
            }
        })

    try:
        languages = {
            'en': {
                'name': 'English',
                'native_name': 'English',
                'hashtags': reach_amplify.get_language_hashtags('en')
            },
            'es': {
                'name': 'Spanish',
                'native_name': 'Espanol',
                'hashtags': reach_amplify.get_language_hashtags('es')
            },
            'fr': {
                'name': 'French',
                'native_name': 'Francais',
                'hashtags': reach_amplify.get_language_hashtags('fr')
            },
            'pt': {
                'name': 'Portuguese',
                'native_name': 'Portugues',
                'hashtags': reach_amplify.get_language_hashtags('pt')
            }
        }

        # Add common translations
        if hasattr(reach_amplify, 'TRANSLATIONS'):
            for lang_code, translations in reach_amplify.TRANSLATIONS.items():
                if lang_code in languages:
                    languages[lang_code]['common_phrases'] = translations

        return jsonify({
            'success': True,
            'languages': languages
        })
    except Exception as e:
        logger.error(f"Languages endpoint failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============== BUSINESS CHALLENGE ==============

@app.route('/api/business-challenge/generate', methods=['POST'])
def api_generate_business_challenge():
    """
    Generate a business challenge post or spotlight.

    Request body:
        - type: str (required) - 'challenge' or 'spotlight'
        - challenge_name: str (for challenge) - Name of the challenge
        - business_count: int (for challenge) - Number of participating businesses
        - business_name: str (for spotlight) - Name of business to spotlight
        - custom_message: str (for spotlight, optional) - Custom thank you message

    Returns:
        Business-focused post content
    """
    data = request.json or {}
    post_type = data.get('type')

    if post_type not in ['challenge', 'spotlight']:
        return jsonify({
            'success': False,
            'error': 'type must be either "challenge" or "spotlight"'
        }), 400

    if not reach_amplify:
        return jsonify({
            'success': False,
            'error': 'REACH Amplify not available'
        }), 503

    try:
        if post_type == 'challenge':
            challenge_name = data.get('challenge_name')
            if not challenge_name:
                return jsonify({
                    'success': False,
                    'error': 'challenge_name is required for challenge posts'
                }), 400

            business_count = data.get('business_count', 0)
            result = reach_amplify.generate_business_challenge_post(challenge_name, business_count)

        else:  # spotlight
            business_name = data.get('business_name')
            if not business_name:
                return jsonify({
                    'success': False,
                    'error': 'business_name is required for spotlight posts'
                }), 400

            custom_message = data.get('custom_message', '')
            result = reach_amplify.generate_business_spotlight(business_name, custom_message)

        result['success'] = True
        result['type'] = post_type
        return jsonify(result)

    except Exception as e:
        logger.error(f"Business challenge generation failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/settings')
def settings_page():
    """Settings page for API configuration."""
    # Check current configuration status
    config_status = {
        'openai': bool(os.getenv('OPENAI_API_KEY')),
        'imgbb': bool(os.getenv('IMGBB_API_KEY')),
        'instagram_token': bool(os.getenv('INSTAGRAM_ACCESS_TOKEN')),
        'instagram_account': bool(os.getenv('INSTAGRAM_ACCOUNT_ID'))
    }
    return render_template('settings.html', config_status=config_status)


# Initialize database on startup
try:
    init_db()
    logger.info("Database initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize database: {e}")

logger.info("DVCCC Instagram Content Manager - Ready")


if __name__ == '__main__':
    # Get port from environment variable (for deployment) or use 5001
    port = int(os.environ.get('PORT', 5001))

    print("\n" + "="*60)
    print("  DVCCC Instagram Content Manager")
    print("="*60)
    print(f"\n  Open in browser: http://127.0.0.1:{port}")
    print("  Background scheduler: " + ("ACTIVE" if start_web_scheduler else "DISABLED"))
    print("="*60 + "\n")

    # Start background scheduler if available
    if start_web_scheduler:
        start_web_scheduler()

    try:
        app.run(host='0.0.0.0', debug=False, port=port, use_reloader=False)
    finally:
        if stop_web_scheduler:
            stop_web_scheduler()
