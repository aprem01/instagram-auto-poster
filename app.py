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
    language = request.form.get('language', 'en').strip()

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

        # Translate to Spanish if requested
        spanish_caption = None
        if language == 'es' and reach_amplify:
            try:
                translation = reach_amplify.translate_caption(caption, 'es')
                if translation.get('translated'):
                    spanish_caption = translation['translated']
                    caption = spanish_caption  # Use Spanish as main caption
                    logger.info("Caption translated to Spanish successfully")
            except Exception as e:
                logger.warning(f"Spanish translation failed: {e}")

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
            'caption_en': result['caption'],  # Always include English
            'caption_es': spanish_caption,     # Spanish if translated
            'language': language,
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
    language = data.get('language', 'en')

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
        caption = result['caption']
        spanish_caption = None

        # Translate to Spanish if requested
        if language == 'es' and reach_amplify:
            try:
                translation = reach_amplify.translate_caption(caption, 'es')
                if translation.get('translated'):
                    spanish_caption = translation['translated']
                    caption = spanish_caption
            except Exception as e:
                logger.warning(f"Spanish translation failed: {e}")

        return jsonify({
            'success': True,
            'caption': caption,
            'caption_en': result['caption'],
            'caption_es': spanish_caption,
            'language': language
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


# ============== DISCOVERY OPTIMIZER ==============

@app.route('/discovery')
def discovery_optimizer():
    """Discovery Optimizer page - optimize existing captions for discoverability."""
    return render_template('discovery.html')


@app.route('/api/discovery/analyze', methods=['POST'])
def api_discovery_analyze():
    """
    Analyze a caption for social media discoverability.

    Request body:
        - caption: str (required) - The caption to analyze
        - platform: str (optional) - Target platform (instagram, facebook, tiktok, linkedin)
        - target_audience: str (optional) - Target audience (general, youth, donors, event)
        - campaign_type: str (optional) - Campaign type (awareness, fundraising, events, youth, volunteer)

    Returns:
        Comprehensive discoverability analysis with recommendations
    """
    data = request.json or {}
    caption = data.get('caption', '').strip()
    platform = data.get('platform', 'instagram').lower()
    target_audience = data.get('target_audience', 'general').lower()
    campaign_type = data.get('campaign_type', 'awareness').lower()

    if not caption:
        return jsonify({
            'success': False,
            'error': 'Please provide a caption to analyze'
        }), 400

    if not reach_amplify:
        return jsonify({
            'success': False,
            'error': 'Discovery Optimizer requires OPENAI_API_KEY to be configured'
        }), 503

    try:
        # Get base hashtags
        base_hashtags = reach_amplify.generate_hashtags(
            topic=campaign_type,
            caption=caption,
            count=15
        )

        # Get audience-specific hashtags
        audience_hashtags = get_audience_hashtags(target_audience, campaign_type)

        # Combine and deduplicate hashtags
        all_hashtags = list(dict.fromkeys(audience_hashtags + base_hashtags))[:20]

        # Get SEO keywords
        keywords = extract_seo_keywords(caption, target_audience)

        # Get SEO analysis
        seo_analysis = reach_amplify.get_seo_analysis(caption, keywords)

        # Calculate discovery score
        discovery_score = calculate_discovery_score(caption, all_hashtags, keywords, platform)

        # Get posting time recommendations
        posting_times = get_audience_posting_times(target_audience, platform)

        # Get platform-specific tips
        platform_tips = reach_amplify.get_platform_tips(platform) if hasattr(reach_amplify, 'get_platform_tips') else {}

        # Get improvement suggestions
        improvements = generate_improvement_suggestions(caption, discovery_score, target_audience, platform)

        # Get engagement tips
        engagement_tips = reach_amplify.get_engagement_tips(campaign_type)

        return jsonify({
            'success': True,
            'analysis': {
                'discovery_score': discovery_score,
                'hashtags': all_hashtags,
                'hashtag_string': ' '.join(['#' + h.lstrip('#') for h in all_hashtags]),
                'keywords': keywords,
                'seo_analysis': seo_analysis,
                'posting_times': posting_times,
                'platform_tips': platform_tips,
                'improvements': improvements,
                'engagement_tips': engagement_tips,
                'caption_length': len(caption),
                'platform': platform,
                'target_audience': target_audience
            }
        })

    except Exception as e:
        logger.error(f"Discovery analysis failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


def get_audience_hashtags(audience: str, campaign_type: str) -> list:
    """Get hashtags optimized for specific target audiences."""

    # Youth-focused hashtags (Under 24)
    youth_hashtags = [
        'GenZ', 'TeenDatingViolence', 'TDVAM', 'HealthyRelationships',
        'KnowTheSigns', 'LoveIsRespect', 'TeenSafety', 'YouthAdvocacy',
        'BreakTheCycle', 'SpeakUp', 'TeenVoices', 'YouMatter',
        'MentalHealthMatters', 'SafeRelationships', 'RedFlags'
    ]

    # Donor/Fundraising hashtags
    donor_hashtags = [
        'GiveHope', 'SupportSurvivors', 'NonprofitLove', 'ChesterCountyGives',
        'DonateForChange', 'GivingTuesday', 'PhilanthropyMatters',
        'MakeADifference', 'CharityTuesday', 'GiveBack', 'ImpactGiving'
    ]

    # Event attendee hashtags
    event_hashtags = [
        'DVCCCEvents', 'ChesterCountyEvents', 'CommunityEvent',
        'JoinUs', 'LocalEvents', 'NonprofitEvent', 'AwarenessEvent',
        'WalkForSurvivors', 'PurpleThursday', 'CandlelightVigil'
    ]

    # General awareness hashtags
    general_hashtags = [
        'DomesticViolenceAwareness', 'DVCCC', 'ChesterCounty',
        'EndDomesticViolence', 'SurvivorSupport', 'YouAreNotAlone',
        'HopeAndHealing', 'BreakTheSilence', 'DVAwareness', 'SafeSpace'
    ]

    # Survivor-focused hashtags
    survivor_hashtags = [
        'SurvivorStrong', 'YouAreNotAlone', 'HopeAndHealing', 'SafeSpace',
        'BreakTheSilence', 'SurvivorSupport', 'HelpIsAvailable', 'DVCCC',
        'ChesterCounty', 'FreeSupport', 'ConfidentialHelp', 'NewBeginnings'
    ]

    # Professional hashtags
    professional_hashtags = [
        'DVAwareness', 'SocialWork', 'TraumaInformed', 'HealthcareProvider',
        'DVAdvocacy', 'ProfessionalDevelopment', 'DVTraining', 'CommunityPartners',
        'ReferralResources', 'DVPrevention', 'ChesterCounty', 'DVCCC'
    ]

    # Spanish/Bilingual hashtags
    spanish_hashtags = [
        'ViolenciaDomestica', 'AyudaGratuita', 'Confidencial', 'ChesterCounty',
        'DVCCC', 'ApoyoEnEspanol', 'ComunidadLatina', 'SomosFamilia',
        'NoEstásSola', 'HelpIsAvailable', 'BilingualServices', 'ServiciosEnEspanol'
    ]

    # Volunteer hashtags
    volunteer_hashtags = [
        'VolunteerWithUs', 'MakeADifference', 'BeTheChange', 'DVCCCVolunteers',
        'CommunityService', 'GiveBack', 'VolunteerOpportunity', 'ChesterCounty',
        'NonprofitVolunteer', 'HelpingSurvivors', 'VolunteerAppreciation'
    ]

    # Campaign-specific additions
    campaign_additions = {
        'awareness': ['DVAwareness', 'EndDV', 'BreakTheSilence'],
        'fundraising': ['GiveHope', 'SupportSurvivors', 'DonateForChange'],
        'events': ['DVCCCEvents', 'JoinUs', 'CommunityMatters'],
        'youth': ['TeenDatingViolence', 'HealthyRelationships', 'YouthVoices'],
        'volunteer': ['VolunteerWithUs', 'MakeADifference', 'BeTheChange']
    }

    # Select base hashtags by audience
    audience_map = {
        'youth': youth_hashtags,
        'donors': donor_hashtags,
        'event': event_hashtags,
        'survivors': survivor_hashtags,
        'professionals': professional_hashtags,
        'spanish': spanish_hashtags,
        'volunteers': volunteer_hashtags,
        'general': general_hashtags
    }

    hashtags = audience_map.get(audience, general_hashtags).copy()

    # Add campaign-specific hashtags
    hashtags.extend(campaign_additions.get(campaign_type, []))

    return hashtags


def extract_seo_keywords(caption: str, audience: str) -> list:
    """Extract SEO-friendly keywords from caption."""
    import re

    # Base keywords that should always be present
    base_keywords = ['domestic violence', 'Chester County', 'support', 'help', 'free', 'confidential']

    # Audience-specific keywords
    audience_keywords = {
        'youth': ['teen', 'dating violence', 'healthy relationships', 'warning signs', 'young people'],
        'donors': ['donate', 'give', 'support', 'impact', 'change lives', 'gift'],
        'event': ['event', 'join', 'attend', 'register', 'community'],
        'general': ['survivor', 'awareness', 'hope', 'healing', 'safety']
    }

    # Extract potential keywords from caption
    words = re.findall(r'\b[a-zA-Z]{4,}\b', caption.lower())
    word_freq = {}
    for word in words:
        if word not in ['that', 'this', 'with', 'from', 'have', 'been', 'were', 'they', 'their', 'your', 'will']:
            word_freq[word] = word_freq.get(word, 0) + 1

    # Get top words from caption
    caption_keywords = sorted(word_freq.keys(), key=lambda x: word_freq[x], reverse=True)[:5]

    # Combine all keywords
    all_keywords = base_keywords + audience_keywords.get(audience, []) + caption_keywords

    # Deduplicate while preserving order
    seen = set()
    unique_keywords = []
    for kw in all_keywords:
        if kw.lower() not in seen:
            seen.add(kw.lower())
            unique_keywords.append(kw)

    return unique_keywords[:12]


def calculate_discovery_score(caption: str, hashtags: list, keywords: list, platform: str) -> dict:
    """Calculate a discovery score for the content."""
    score = 0
    max_score = 100
    breakdown = []

    # Caption length scoring (15 points)
    caption_len = len(caption)
    if platform == 'instagram':
        if 150 <= caption_len <= 2200:
            score += 15
            breakdown.append({'item': 'Caption length', 'points': 15, 'max': 15, 'status': 'good'})
        elif caption_len < 150:
            score += 8
            breakdown.append({'item': 'Caption length', 'points': 8, 'max': 15, 'status': 'short', 'tip': 'Add more context to improve engagement'})
        else:
            score += 10
            breakdown.append({'item': 'Caption length', 'points': 10, 'max': 15, 'status': 'ok'})
    elif platform == 'tiktok':
        if caption_len <= 150:
            score += 15
            breakdown.append({'item': 'Caption length', 'points': 15, 'max': 15, 'status': 'good'})
        else:
            score += 5
            breakdown.append({'item': 'Caption length', 'points': 5, 'max': 15, 'status': 'long', 'tip': 'Shorten for TikTok (max 150 chars)'})
    else:
        score += 12
        breakdown.append({'item': 'Caption length', 'points': 12, 'max': 15, 'status': 'ok'})

    # Hashtag scoring (20 points)
    hashtag_count = len(hashtags)
    if platform == 'instagram':
        if 8 <= hashtag_count <= 15:
            score += 20
            breakdown.append({'item': 'Hashtag count', 'points': 20, 'max': 20, 'status': 'good'})
        elif hashtag_count < 8:
            score += 10
            breakdown.append({'item': 'Hashtag count', 'points': 10, 'max': 20, 'status': 'low', 'tip': 'Add more hashtags for better reach'})
        else:
            score += 15
            breakdown.append({'item': 'Hashtag count', 'points': 15, 'max': 20, 'status': 'ok'})
    elif platform in ['facebook', 'linkedin']:
        if 2 <= hashtag_count <= 5:
            score += 20
            breakdown.append({'item': 'Hashtag count', 'points': 20, 'max': 20, 'status': 'good'})
        else:
            score += 10
            breakdown.append({'item': 'Hashtag count', 'points': 10, 'max': 20, 'status': 'adjust', 'tip': f'Use 2-5 hashtags for {platform}'})
    else:
        score += 15
        breakdown.append({'item': 'Hashtag count', 'points': 15, 'max': 20, 'status': 'ok'})

    # Keyword presence (20 points)
    caption_lower = caption.lower()
    keywords_found = sum(1 for kw in keywords if kw.lower() in caption_lower)
    keyword_score = min(20, int((keywords_found / max(len(keywords), 1)) * 20))
    score += keyword_score
    if keyword_score >= 15:
        breakdown.append({'item': 'Keywords', 'points': keyword_score, 'max': 20, 'status': 'good'})
    else:
        breakdown.append({'item': 'Keywords', 'points': keyword_score, 'max': 20, 'status': 'improve', 'tip': 'Include more searchable keywords'})

    # Call to action (15 points)
    cta_phrases = ['visit', 'call', 'click', 'learn more', 'link in bio', 'dm', 'contact', 'reach out', 'sign up', 'register', 'donate', 'join']
    has_cta = any(cta in caption_lower for cta in cta_phrases)
    if has_cta:
        score += 15
        breakdown.append({'item': 'Call to action', 'points': 15, 'max': 15, 'status': 'good'})
    else:
        score += 0
        breakdown.append({'item': 'Call to action', 'points': 0, 'max': 15, 'status': 'missing', 'tip': 'Add a call to action (visit, call, learn more)'})

    # Emoji usage (10 points)
    import re
    emoji_pattern = re.compile("["
        u"\U0001F600-\U0001F64F"
        u"\U0001F300-\U0001F5FF"
        u"\U0001F680-\U0001F6FF"
        u"\U0001F1E0-\U0001F1FF"
        u"\U00002702-\U000027B0"
        u"\U0001F900-\U0001F9FF"
        "]+", flags=re.UNICODE)
    emoji_count = len(emoji_pattern.findall(caption))
    if 1 <= emoji_count <= 5:
        score += 10
        breakdown.append({'item': 'Emoji usage', 'points': 10, 'max': 10, 'status': 'good'})
    elif emoji_count == 0:
        score += 3
        breakdown.append({'item': 'Emoji usage', 'points': 3, 'max': 10, 'status': 'none', 'tip': 'Add 1-3 emojis for visual appeal'})
    else:
        score += 7
        breakdown.append({'item': 'Emoji usage', 'points': 7, 'max': 10, 'status': 'many'})

    # Location/Community mention (10 points)
    location_terms = ['chester county', 'pennsylvania', 'pa', 'local', 'community', 'dvccc']
    has_location = any(term in caption_lower for term in location_terms)
    if has_location:
        score += 10
        breakdown.append({'item': 'Local relevance', 'points': 10, 'max': 10, 'status': 'good'})
    else:
        score += 0
        breakdown.append({'item': 'Local relevance', 'points': 0, 'max': 10, 'status': 'missing', 'tip': 'Mention Chester County or DVCCC for local reach'})

    # Question/Engagement prompt (10 points)
    has_question = '?' in caption
    engagement_prompts = ['share', 'comment', 'tag', 'tell us', 'what do you think', 'have you']
    has_engagement = any(prompt in caption_lower for prompt in engagement_prompts)
    if has_question or has_engagement:
        score += 10
        breakdown.append({'item': 'Engagement prompt', 'points': 10, 'max': 10, 'status': 'good'})
    else:
        score += 0
        breakdown.append({'item': 'Engagement prompt', 'points': 0, 'max': 10, 'status': 'missing', 'tip': 'Add a question or engagement prompt'})

    # Calculate grade
    percentage = (score / max_score) * 100
    if percentage >= 90:
        grade = 'A'
        color = '#22c55e'
    elif percentage >= 80:
        grade = 'B'
        color = '#84cc16'
    elif percentage >= 70:
        grade = 'C'
        color = '#eab308'
    elif percentage >= 60:
        grade = 'D'
        color = '#f97316'
    else:
        grade = 'F'
        color = '#ef4444'

    return {
        'score': score,
        'max_score': max_score,
        'percentage': round(percentage),
        'grade': grade,
        'color': color,
        'breakdown': breakdown
    }


def get_audience_posting_times(audience: str, platform: str) -> dict:
    """Get optimal posting times for target audience."""

    # Youth (Under 24) - typically more active in evening/night
    youth_times = {
        'instagram': {'best': ['7:00 PM', '9:00 PM'], 'good': ['3:00 PM', '8:00 PM', '10:00 PM'], 'days': ['Tuesday', 'Thursday', 'Saturday']},
        'tiktok': {'best': ['7:00 PM', '10:00 PM'], 'good': ['4:00 PM', '8:00 PM', '11:00 PM'], 'days': ['Tuesday', 'Thursday', 'Friday']},
        'facebook': {'best': ['8:00 PM', '9:00 PM'], 'good': ['12:00 PM', '7:00 PM'], 'days': ['Wednesday', 'Friday']},
        'linkedin': {'best': ['5:00 PM', '6:00 PM'], 'good': ['12:00 PM', '4:00 PM'], 'days': ['Tuesday', 'Wednesday']}
    }

    # Donors - typically professionals, active during work hours and early evening
    donor_times = {
        'instagram': {'best': ['12:00 PM', '6:00 PM'], 'good': ['8:00 AM', '5:00 PM', '7:00 PM'], 'days': ['Tuesday', 'Wednesday', 'Thursday']},
        'facebook': {'best': ['9:00 AM', '1:00 PM'], 'good': ['11:00 AM', '3:00 PM', '7:00 PM'], 'days': ['Tuesday', 'Wednesday', 'Thursday']},
        'linkedin': {'best': ['10:00 AM', '12:00 PM'], 'good': ['8:00 AM', '5:00 PM'], 'days': ['Tuesday', 'Wednesday', 'Thursday']},
        'tiktok': {'best': ['6:00 PM', '8:00 PM'], 'good': ['12:00 PM', '7:00 PM'], 'days': ['Tuesday', 'Thursday']}
    }

    # Event - depends on event timing, generally afternoon/evening
    event_times = {
        'instagram': {'best': ['5:00 PM', '7:00 PM'], 'good': ['12:00 PM', '3:00 PM', '8:00 PM'], 'days': ['Monday', 'Wednesday', 'Friday']},
        'facebook': {'best': ['1:00 PM', '4:00 PM'], 'good': ['10:00 AM', '6:00 PM'], 'days': ['Wednesday', 'Thursday', 'Friday']},
        'linkedin': {'best': ['10:00 AM', '2:00 PM'], 'good': ['9:00 AM', '4:00 PM'], 'days': ['Tuesday', 'Wednesday']},
        'tiktok': {'best': ['6:00 PM', '8:00 PM'], 'good': ['3:00 PM', '9:00 PM'], 'days': ['Thursday', 'Friday', 'Saturday']}
    }

    # General audience
    general_times = {
        'instagram': {'best': ['11:00 AM', '7:00 PM'], 'good': ['9:00 AM', '12:00 PM', '5:00 PM'], 'days': ['Tuesday', 'Wednesday', 'Friday']},
        'facebook': {'best': ['9:00 AM', '1:00 PM'], 'good': ['11:00 AM', '4:00 PM', '7:00 PM'], 'days': ['Wednesday', 'Thursday', 'Friday']},
        'linkedin': {'best': ['10:00 AM', '12:00 PM'], 'good': ['8:00 AM', '2:00 PM', '5:00 PM'], 'days': ['Tuesday', 'Wednesday', 'Thursday']},
        'tiktok': {'best': ['7:00 PM', '9:00 PM'], 'good': ['12:00 PM', '3:00 PM', '8:00 PM'], 'days': ['Tuesday', 'Thursday', 'Friday']},
        'twitter': {'best': ['9:00 AM', '12:00 PM'], 'good': ['8:00 AM', '5:00 PM', '6:00 PM'], 'days': ['Tuesday', 'Wednesday', 'Thursday']}
    }

    # Survivors - late evening/night when they have privacy
    survivor_times = {
        'instagram': {'best': ['9:00 PM', '10:00 PM'], 'good': ['7:00 PM', '8:00 PM', '11:00 PM'], 'days': ['Monday', 'Wednesday', 'Sunday']},
        'facebook': {'best': ['8:00 PM', '10:00 PM'], 'good': ['6:00 PM', '9:00 PM'], 'days': ['Monday', 'Tuesday', 'Sunday']},
        'tiktok': {'best': ['9:00 PM', '11:00 PM'], 'good': ['7:00 PM', '10:00 PM'], 'days': ['Monday', 'Wednesday', 'Friday']},
        'linkedin': {'best': ['12:00 PM', '5:00 PM'], 'good': ['10:00 AM', '2:00 PM'], 'days': ['Monday', 'Wednesday']},
        'twitter': {'best': ['9:00 PM', '10:00 PM'], 'good': ['7:00 PM', '11:00 PM'], 'days': ['Monday', 'Tuesday', 'Wednesday']}
    }

    # Professionals (social workers, healthcare, educators) - work hours
    professional_times = {
        'instagram': {'best': ['12:00 PM', '5:00 PM'], 'good': ['8:00 AM', '1:00 PM', '6:00 PM'], 'days': ['Tuesday', 'Wednesday', 'Thursday']},
        'facebook': {'best': ['10:00 AM', '2:00 PM'], 'good': ['9:00 AM', '12:00 PM', '4:00 PM'], 'days': ['Tuesday', 'Wednesday', 'Thursday']},
        'linkedin': {'best': ['8:00 AM', '10:00 AM'], 'good': ['12:00 PM', '5:00 PM'], 'days': ['Tuesday', 'Wednesday', 'Thursday']},
        'tiktok': {'best': ['5:00 PM', '7:00 PM'], 'good': ['12:00 PM', '6:00 PM'], 'days': ['Wednesday', 'Thursday']},
        'twitter': {'best': ['9:00 AM', '11:00 AM'], 'good': ['8:00 AM', '1:00 PM', '5:00 PM'], 'days': ['Tuesday', 'Wednesday', 'Thursday']}
    }

    # Spanish-speaking community
    spanish_times = {
        'instagram': {'best': ['7:00 PM', '9:00 PM'], 'good': ['12:00 PM', '6:00 PM', '8:00 PM'], 'days': ['Tuesday', 'Thursday', 'Saturday']},
        'facebook': {'best': ['8:00 PM', '9:00 PM'], 'good': ['12:00 PM', '7:00 PM'], 'days': ['Wednesday', 'Friday', 'Saturday']},
        'tiktok': {'best': ['8:00 PM', '10:00 PM'], 'good': ['6:00 PM', '9:00 PM'], 'days': ['Thursday', 'Friday', 'Saturday']},
        'linkedin': {'best': ['10:00 AM', '1:00 PM'], 'good': ['9:00 AM', '5:00 PM'], 'days': ['Tuesday', 'Wednesday']},
        'twitter': {'best': ['7:00 PM', '9:00 PM'], 'good': ['12:00 PM', '8:00 PM'], 'days': ['Tuesday', 'Thursday', 'Saturday']}
    }

    # Volunteers - evening and weekends
    volunteer_times = {
        'instagram': {'best': ['6:00 PM', '8:00 PM'], 'good': ['12:00 PM', '5:00 PM', '7:00 PM'], 'days': ['Monday', 'Wednesday', 'Saturday']},
        'facebook': {'best': ['7:00 PM', '8:00 PM'], 'good': ['10:00 AM', '5:00 PM', '6:00 PM'], 'days': ['Tuesday', 'Thursday', 'Saturday']},
        'linkedin': {'best': ['9:00 AM', '12:00 PM'], 'good': ['8:00 AM', '5:00 PM'], 'days': ['Tuesday', 'Wednesday']},
        'tiktok': {'best': ['7:00 PM', '9:00 PM'], 'good': ['5:00 PM', '8:00 PM'], 'days': ['Thursday', 'Friday', 'Saturday']},
        'twitter': {'best': ['6:00 PM', '8:00 PM'], 'good': ['12:00 PM', '5:00 PM', '7:00 PM'], 'days': ['Monday', 'Wednesday', 'Saturday']}
    }

    audience_map = {
        'youth': youth_times,
        'donors': donor_times,
        'event': event_times,
        'general': general_times,
        'survivors': survivor_times,
        'professionals': professional_times,
        'spanish': spanish_times,
        'volunteers': volunteer_times
    }

    times = audience_map.get(audience, general_times).get(platform, general_times['instagram'])
    times['audience'] = audience
    times['platform'] = platform

    return times


def generate_improvement_suggestions(caption: str, score: dict, audience: str, platform: str) -> list:
    """Generate specific improvement suggestions based on analysis."""
    suggestions = []

    # Check score breakdown for issues
    for item in score.get('breakdown', []):
        if item.get('tip'):
            suggestions.append({
                'category': item['item'],
                'suggestion': item['tip'],
                'priority': 'high' if item['points'] < item['max'] / 2 else 'medium'
            })

    # Audience-specific suggestions
    if audience == 'youth':
        if 'tiktok' not in caption.lower() and platform != 'tiktok':
            suggestions.append({
                'category': 'Youth Reach',
                'suggestion': 'Consider creating a TikTok version - 60% of users are under 24',
                'priority': 'medium'
            })
        if not any(word in caption.lower() for word in ['dating', 'relationship', 'teen', 'young']):
            suggestions.append({
                'category': 'Youth Keywords',
                'suggestion': 'Add youth-relevant terms like "dating", "relationship", or "teen" for better youth discovery',
                'priority': 'high'
            })

    elif audience == 'donors':
        if not any(word in caption.lower() for word in ['impact', 'difference', 'change', 'support', 'help']):
            suggestions.append({
                'category': 'Donor Appeal',
                'suggestion': 'Add impact language like "make a difference" or "your support helps"',
                'priority': 'high'
            })

    # Platform-specific suggestions
    if platform == 'instagram' and len(caption) < 100:
        suggestions.append({
            'category': 'Instagram Optimization',
            'suggestion': 'Instagram captions can be up to 2,200 characters - add more storytelling for engagement',
            'priority': 'medium'
        })

    if platform == 'tiktok' and len(caption) > 150:
        suggestions.append({
            'category': 'TikTok Optimization',
            'suggestion': 'TikTok captions should be under 150 characters - focus on the hook',
            'priority': 'high'
        })

    return suggestions


# ============== DISCOVERY OPTIMIZER - CAPTION GENERATION & MULTI-OPTIMIZATION ==============

@app.route('/api/discovery/generate-caption', methods=['POST'])
def api_generate_discovery_caption():
    """
    Generate an optimized caption based on topic/theme with SEO/AIO/GEO/AEO optimization.

    Request body:
        - topic: str (required) - Topic or theme for the caption
        - target_audience: str (optional) - Target audience
        - platform: str (optional) - Target platform
        - campaign_type: str (optional) - Campaign type
        - optimization_focus: str (optional) - Focus area (seo, aio, geo, aeo, balanced)

    Returns:
        Generated caption with optimization data
    """
    data = request.json or {}
    topic = data.get('topic', '').strip()
    target_audience = data.get('target_audience', 'general')
    platform = data.get('platform', 'instagram')
    campaign_type = data.get('campaign_type', 'awareness')
    optimization_focus = data.get('optimization_focus', 'balanced')
    enhance = data.get('enhance', False)  # Flag for improved regeneration

    if not topic:
        return jsonify({'success': False, 'error': 'Please provide a topic'}), 400

    if not reach_amplify:
        return jsonify({'success': False, 'error': 'Caption generation requires OPENAI_API_KEY'}), 503

    try:
        # Generate optimized caption using AI
        generated = generate_optimized_caption(topic, target_audience, platform, campaign_type, optimization_focus, enhance)

        # Get multi-optimization scores
        multi_opt = get_multi_optimization_scores(generated['caption'], topic, platform)

        # Get posting times for target audience
        posting_times = get_audience_posting_times(target_audience, platform)

        # Check if score is low and provide improvement suggestions
        overall_score = multi_opt.get('overall_score', 0)
        improvement_suggestions = []
        if overall_score < 70:
            improvement_suggestions = [
                'Consider adding more searchable keywords',
                'Include a direct call-to-action',
                'Mention Chester County for local relevance',
                'Add a question to boost engagement'
            ]

        return jsonify({
            'success': True,
            'caption': generated['caption'],
            'topic': topic,
            'optimization_focus': optimization_focus,
            'seo_optimized': generated.get('seo_elements', []),
            'aio_optimized': generated.get('aio_elements', []),
            'geo_optimized': generated.get('geo_elements', []),
            'aeo_optimized': generated.get('aeo_elements', []),
            'multi_optimization': multi_opt,
            'hashtags': generated.get('hashtags', []),
            'posting_times': posting_times,
            'overall_score': overall_score,
            'needs_improvement': overall_score < 70,
            'improvement_suggestions': improvement_suggestions
        })

    except Exception as e:
        logger.error(f"Caption generation failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/discovery/trending')
def api_discovery_trending():
    """
    Get trending topics for DV awareness content.

    Uses real-time data from:
    - Google Trends (search interest)
    - NewsAPI (current news)
    - Awareness Calendar (timely events)

    Returns:
        List of trending topics with optimization potential
    """
    try:
        # Try to use real-time trends service
        try:
            from src.trends.realtime_trends import get_trends_service
            trends_service = get_trends_service(os.getenv('NEWS_API_KEY'))
            trending_topics = trends_service.get_all_trends()

            # Add source indicator
            for topic in trending_topics:
                topic['realtime'] = topic.get('source') in ['google_trends', 'news', 'google_daily_trends']

            logger.info(f"Fetched {len(trending_topics)} real-time trends")

        except Exception as e:
            logger.warning(f"Real-time trends unavailable, using fallback: {e}")
            # Fallback to static trends
            trending_topics = _get_fallback_trends()

        # Sort by trending score
        trending_topics.sort(key=lambda x: x.get('trending_score', 0), reverse=True)

        return jsonify({
            'success': True,
            'trending': trending_topics[:10],
            'updated_at': datetime.now().isoformat(),
            'sources': list(set(t.get('source', 'static') for t in trending_topics))
        })

    except Exception as e:
        logger.error(f"Trending topics failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


def _get_fallback_trends() -> list:
    """Return fallback trending topics when real-time data is unavailable."""
    return [
        {
            'topic': 'Teen Dating Violence Awareness',
            'hashtag': '#TDVAM',
            'audience': 'youth',
            'trending_score': 95,
            'reason': 'February awareness month',
            'source': 'static'
        },
        {
            'topic': 'Financial Abuse Warning Signs',
            'hashtag': '#FinancialAbuse',
            'audience': 'general',
            'trending_score': 88,
            'reason': 'Often overlooked form of abuse',
            'source': 'static'
        },
        {
            'topic': 'Healthy Relationship Education',
            'hashtag': '#HealthyRelationships',
            'audience': 'youth',
            'trending_score': 92,
            'reason': 'High engagement topic',
            'source': 'static'
        },
        {
            'topic': 'Survivor Stories of Strength',
            'hashtag': '#SurvivorStrong',
            'audience': 'survivors',
            'trending_score': 85,
            'reason': 'Personal narratives drive engagement',
            'source': 'static'
        },
        {
            'topic': 'Digital Safety & Technology Abuse',
            'hashtag': '#DigitalSafety',
            'audience': 'youth',
            'trending_score': 90,
            'reason': 'Rising concern for young people',
            'source': 'static'
        },
        {
            'topic': 'Purple Thursday Community Support',
            'hashtag': '#PurpleThursday',
            'audience': 'general',
            'trending_score': 82,
            'reason': 'Weekly awareness momentum',
            'source': 'static'
        }
    ]


@app.route('/api/discovery/multi-optimize', methods=['POST'])
def api_multi_optimize():
    """
    Analyze caption with comprehensive SEO/AIO/GEO/AEO optimization.

    Request body:
        - caption: str (required) - Caption to analyze
        - topic: str (optional) - Topic for context
        - platform: str (optional) - Target platform

    Returns:
        Detailed optimization scores and recommendations for each channel
    """
    data = request.json or {}
    caption = data.get('caption', '').strip()
    topic = data.get('topic', 'domestic violence awareness')
    platform = data.get('platform', 'instagram')

    if not caption:
        return jsonify({'success': False, 'error': 'Caption is required'}), 400

    try:
        multi_opt = get_multi_optimization_scores(caption, topic, platform)
        return jsonify({
            'success': True,
            'optimization': multi_opt
        })
    except Exception as e:
        logger.error(f"Multi-optimization failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


def generate_optimized_caption(topic: str, audience: str, platform: str, campaign: str, focus: str, enhance: bool = False) -> dict:
    """Generate an AI-optimized caption with SEO/AIO/GEO/AEO elements."""

    # Build optimization prompt based on focus
    focus_instructions = {
        'seo': 'Include searchable keywords, clear topic mentions, and link-worthy phrases.',
        'aio': 'Structure with clear headings, bullet-point friendly format, and comprehensive coverage.',
        'geo': 'Include authoritative statements, citable facts, and brand-building language.',
        'aeo': 'Include direct answers to common questions, voice-friendly phrasing, and concise facts.',
        'balanced': 'Balance all optimization types: searchable keywords, clear structure, authoritative tone, and direct answers.'
    }

    audience_context = {
        'youth': 'Target audience is young people under 24. Use relatable language, mention dating relationships, peer support, and social media friendly phrases.',
        'donors': 'Target audience is potential donors. Emphasize impact, community investment, measurable outcomes, and how donations save lives.',
        'event': 'Target audience is event attendees. Include event details, registration info, and community gathering.',
        'general': 'Target audience is general community. Balance awareness, support resources, and hope.',
        'survivors': 'Target audience is survivors of domestic violence. Use empathetic, empowering language. Emphasize safety, confidentiality, and that help is available without judgment. Avoid triggering language.',
        'professionals': 'Target audience is professionals (social workers, healthcare providers, educators). Use professional terminology, mention referral resources, training opportunities, and partnership possibilities.',
        'spanish': 'Target audience is Spanish-speaking community. Write in BOTH English and Spanish (bilingual caption). Use culturally appropriate messaging. Include "Servicios GRATUITOS y CONFIDENCIALES".',
        'volunteers': 'Target audience is potential and current volunteers. Emphasize making a difference, training provided, flexible schedules, and community impact.'
    }

    campaign_tone = {
        'awareness': 'Educational and empowering tone focused on awareness and prevention.',
        'fundraising': 'Inspiring tone emphasizing impact and the difference donations make.',
        'events': 'Inviting and energetic tone promoting community participation.',
        'youth': 'Relatable and direct tone speaking to young people about healthy relationships.',
        'volunteer': 'Appreciative and welcoming tone celebrating volunteer contributions.'
    }

    # Enhanced optimization instructions for improved regeneration
    enhance_instructions = ""
    if enhance:
        enhance_instructions = """
ENHANCED OPTIMIZATION MODE - Generate a significantly improved version:
- Use MORE searchable keywords (domestic violence, Chester County PA, free help, confidential support)
- Include a COMPELLING question to drive engagement
- Add a STRONGER call-to-action with urgency
- Include a STATISTIC or fact that makes the message memorable
- Make the hook STRONGER and more attention-grabbing
- Ensure the caption is HIGHLY shareable
"""

    if reach_amplify and hasattr(reach_amplify, 'client'):
        try:
            response = reach_amplify.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": f"""You are a social media expert for the Domestic Violence Center of Chester County (DVCCC).
Create an Instagram caption optimized for maximum discoverability and engagement.

REQUIRED ELEMENTS FOR HIGH SCORE:
1. KEYWORDS: Include "Chester County", "domestic violence", "free", "confidential", "support", "safe"
2. BRAND: Mention "DVCCC" or "Domestic Violence Center" and use "we provide", "we offer", or "we help"
3. LOCAL: Emphasize Chester County, PA location and community
4. ACTION: Include clear CTA like "Call", "Visit", "Reach out", "Get help"
5. QUESTION: Include an engaging question to drive interaction
6. STRUCTURE: Use 2-3 short paragraphs with line breaks

Organization context:
- DVCCC provides FREE, CONFIDENTIAL services to survivors in Chester County, PA
- 24-hour hotline available
- Services include shelter, counseling, advocacy, support groups

{focus_instructions.get(focus, focus_instructions['balanced'])}
{audience_context.get(audience, audience_context['general'])}
{campaign_tone.get(campaign, campaign_tone['awareness'])}
{enhance_instructions}

Platform: {platform}

Structure the caption with:
1. Hook with a question or powerful statement (first line)
2. Key message with required keywords
3. "We provide/offer/help" statement with specific services
4. Strong call to action (call, visit, reach out)
5. 2-4 relevant emojis

Example format:
"[Question or powerful hook] 💜

[Key message with keywords: domestic violence, Chester County, free, confidential, support, safe]

We provide/help/offer [specific services]. [Call to action - call, visit dvcccpa.org, reach out]

You're not alone. 💪"

Do NOT include hashtags - those will be added separately."""
                    },
                    {
                        "role": "user",
                        "content": f"Create an optimized caption about: {topic}"
                    }
                ],
                max_tokens=500,
                temperature=0.8 if enhance else 0.7  # Slightly higher creativity for enhanced mode
            )
            caption = response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"AI caption generation failed: {e}")
            caption = generate_fallback_caption(topic, audience)
    else:
        caption = generate_fallback_caption(topic, audience)

    # Extract optimization elements
    seo_elements = extract_seo_elements(caption)
    aio_elements = extract_aio_elements(caption)
    geo_elements = extract_geo_elements(caption)
    aeo_elements = extract_aeo_elements(caption)

    # Generate hashtags
    hashtags = get_audience_hashtags(audience, campaign)[:15]

    return {
        'caption': caption,
        'seo_elements': seo_elements,
        'aio_elements': aio_elements,
        'geo_elements': geo_elements,
        'aeo_elements': aeo_elements,
        'hashtags': hashtags
    }


def generate_fallback_caption(topic: str, audience: str) -> str:
    """Generate a fallback caption without AI."""
    templates = {
        'youth': f"""Your relationships should make you feel safe and respected. 💜

{topic}

At DVCCC, we're here for young people in Chester County with FREE, CONFIDENTIAL support. You deserve healthy relationships.

Learn more at dvcccpa.org or reach out anytime. You're not alone. 💪""",

        'donors': f"""Your support changes lives in Chester County. 💜

{topic}

Every gift to DVCCC provides FREE, CONFIDENTIAL services to survivors of domestic violence. Together, we're building a safer community.

Make an impact today at dvcccpa.org/give 🌟""",

        'general': f"""You are not alone. 💜

{topic}

DVCCC provides FREE, CONFIDENTIAL services to anyone in Chester County experiencing domestic violence. Our doors are always open.

Reach out today at dvcccpa.org or call our 24-hour hotline. Hope lives here. 💪🌟"""
    }
    return templates.get(audience, templates['general'])


def extract_seo_elements(caption: str) -> list:
    """Extract SEO-friendly elements from caption."""
    elements = []
    caption_lower = caption.lower()

    # Check for key SEO elements
    seo_keywords = ['domestic violence', 'chester county', 'free', 'confidential', 'support', 'help', 'services', 'survivor']
    for kw in seo_keywords:
        if kw in caption_lower:
            elements.append({'type': 'keyword', 'value': kw, 'found': True})

    # Check for URL/link mention
    if 'dvcccpa.org' in caption_lower or 'link in bio' in caption_lower:
        elements.append({'type': 'link', 'value': 'Website reference', 'found': True})

    # Check for location
    if 'chester county' in caption_lower or 'pennsylvania' in caption_lower:
        elements.append({'type': 'location', 'value': 'Local targeting', 'found': True})

    return elements


def extract_aio_elements(caption: str) -> list:
    """Extract AI Overview optimization elements."""
    elements = []

    # Check for clear structure
    if '\n\n' in caption:
        elements.append({'type': 'structure', 'value': 'Paragraph breaks', 'found': True})

    # Check for clarity indicators
    sentences = caption.split('.')
    avg_sentence_length = sum(len(s.split()) for s in sentences) / max(len(sentences), 1)
    if avg_sentence_length < 20:
        elements.append({'type': 'clarity', 'value': 'Readable sentence length', 'found': True})

    # Check for comprehensive coverage
    if len(caption) > 200:
        elements.append({'type': 'depth', 'value': 'Comprehensive content', 'found': True})

    return elements


def extract_geo_elements(caption: str) -> list:
    """Extract Generative Engine Optimization elements."""
    elements = []
    caption_lower = caption.lower()

    # Check for authoritative language
    authority_phrases = ['we provide', 'our services', 'dvccc', 'at dvccc', 'we offer', 'our team']
    for phrase in authority_phrases:
        if phrase in caption_lower:
            elements.append({'type': 'authority', 'value': f'Brand voice: "{phrase}"', 'found': True})
            break

    # Check for citable facts
    if any(char.isdigit() for char in caption):
        elements.append({'type': 'citation', 'value': 'Contains statistics/numbers', 'found': True})

    # Check for reputation indicators
    reputation_words = ['free', 'confidential', '24-hour', 'professional', 'trained']
    found_rep = [w for w in reputation_words if w in caption_lower]
    if found_rep:
        elements.append({'type': 'reputation', 'value': f'Trust signals: {", ".join(found_rep[:3])}', 'found': True})

    return elements


def extract_aeo_elements(caption: str) -> list:
    """Extract Answer Engine Optimization elements (voice search)."""
    elements = []
    caption_lower = caption.lower()

    # Check for question-answer format
    if '?' in caption:
        elements.append({'type': 'question', 'value': 'Contains question format', 'found': True})

    # Check for direct answer phrases
    direct_phrases = ['you can', 'we offer', 'call', 'visit', 'reach out', 'contact']
    for phrase in direct_phrases:
        if phrase in caption_lower:
            elements.append({'type': 'direct_answer', 'value': f'Action phrase: "{phrase}"', 'found': True})
            break

    # Check for voice-friendly snippets (short, clear statements)
    sentences = [s.strip() for s in caption.split('.') if s.strip()]
    short_clear = [s for s in sentences if 5 <= len(s.split()) <= 15]
    if short_clear:
        elements.append({'type': 'voice_snippet', 'value': 'Voice-ready sentences', 'found': True})

    # Check for local intent (important for voice search)
    if 'chester county' in caption_lower:
        elements.append({'type': 'local', 'value': 'Local search optimized', 'found': True})

    return elements


def get_multi_optimization_scores(caption: str, topic: str, platform: str) -> dict:
    """Calculate comprehensive optimization scores for SEO, AIO, GEO, AEO."""

    seo_score = calculate_seo_score(caption, topic)
    aio_score = calculate_aio_score(caption)
    geo_score = calculate_geo_score(caption)
    aeo_score = calculate_aeo_score(caption)

    # Calculate overall score
    overall = int((seo_score['score'] + aio_score['score'] + geo_score['score'] + aeo_score['score']) / 4)

    return {
        'overall_score': overall,
        'overall_grade': score_to_grade(overall),
        'seo': seo_score,
        'aio': aio_score,
        'geo': geo_score,
        'aeo': aeo_score
    }


def calculate_seo_score(caption: str, topic: str) -> dict:
    """Calculate SEO optimization score."""
    score = 0
    max_score = 100
    tips = []
    caption_lower = caption.lower()

    # Keyword presence (35 points) - More generous scoring
    keywords = ['domestic violence', 'chester county', 'support', 'help', 'free', 'confidential',
                'survivor', 'safety', 'abuse', 'resources', 'services', 'hotline', 'crisis']
    keywords_found = sum(1 for kw in keywords if kw in caption_lower)
    keyword_score = min(35, keywords_found * 7)
    score += keyword_score
    if keyword_score < 21:
        tips.append('Add searchable keywords (domestic violence, Chester County, support, safety)')

    # Link/URL or website reference (15 points) - More flexible
    url_patterns = ['dvcccpa.org', 'website', 'online', 'learn more', 'find out', 'visit us']
    if any(p in caption_lower for p in url_patterns):
        score += 15
    else:
        tips.append('Mention website or include dvcccpa.org')

    # Topic relevance (25 points) - More flexible matching
    topic_words = [w for w in topic.lower().split() if len(w) > 3]
    topic_matches = sum(1 for word in topic_words if word in caption_lower)
    topic_score = min(25, max(10, topic_matches * 8))  # Base 10 points for any caption
    score += topic_score
    if topic_score < 17:
        tips.append(f'Include more topic keywords')

    # Length optimization (15 points)
    if len(caption) >= 100:
        score += 15
    elif len(caption) >= 50:
        score += 10
        tips.append('Expand caption slightly for better SEO')
    else:
        tips.append('Expand caption for better SEO (aim for 100+ characters)')
        score += 5

    # Call to action (10 points) - More CTA options
    cta_words = ['visit', 'call', 'learn', 'contact', 'reach out', 'connect', 'get help', 'find', 'discover', 'explore', 'dm', 'message']
    if any(cta in caption_lower for cta in cta_words):
        score += 10
    else:
        tips.append('Add a call to action')

    return {
        'score': score,
        'max_score': max_score,
        'grade': score_to_grade(score),
        'focus': 'Keywords & Links',
        'platform': 'Google / Bing',
        'metric': 'Website Traffic',
        'tips': tips
    }


def calculate_aio_score(caption: str) -> dict:
    """Calculate AI Overview optimization score."""
    score = 0
    max_score = 100
    tips = []

    # Clear structure (25 points) - More flexible
    has_structure = '\n\n' in caption or '\n' in caption or len(caption.split('. ')) >= 2
    if has_structure:
        score += 25
    else:
        tips.append('Add paragraph breaks or multiple sentences')
        score += 12

    # Sentence clarity (25 points) - More generous
    sentences = [s.strip() for s in caption.replace('!', '.').replace('?', '.').split('.') if s.strip()]
    if sentences:
        avg_length = sum(len(s.split()) for s in sentences) / len(sentences)
        if avg_length < 30:
            score += 25
        elif avg_length < 40:
            score += 18
        else:
            tips.append('Consider shorter sentences for clarity')
            score += 10

    # Comprehensive coverage (25 points) - Lower threshold
    if len(caption) >= 150:
        score += 25
    elif len(caption) >= 80:
        score += 20
    elif len(caption) >= 50:
        score += 15
    else:
        tips.append('Expand content for better AI summaries')
        score += 8

    # Factual content (25 points) - More indicators
    factual_indicators = ['free', 'confidential', '24', 'chester county', 'dvccc', 'services',
                         'support', 'help', 'available', 'safe', 'trained', 'professional']
    factual_count = sum(1 for fi in factual_indicators if fi in caption.lower())
    factual_score = min(25, factual_count * 5)
    score += factual_score
    if factual_score < 15:
        tips.append('Include factual details (free, confidential, available)')

    return {
        'score': score,
        'max_score': max_score,
        'grade': score_to_grade(score),
        'focus': 'Clarity & Structure',
        'platform': 'Google AI Overviews',
        'metric': 'Summary Presence',
        'tips': tips
    }


def calculate_geo_score(caption: str) -> dict:
    """Calculate Generative Engine Optimization score (ChatGPT/Perplexity)."""
    score = 0
    max_score = 100
    tips = []
    caption_lower = caption.lower()

    # Brand authority (30 points) - More brand signals
    brand_signals = ['dvccc', 'domestic violence center', 'chester county', 'center', 'organization', 'nonprofit']
    brand_found = sum(1 for bs in brand_signals if bs in caption_lower)
    brand_score = min(30, brand_found * 10)
    score += brand_score
    if brand_score < 20:
        tips.append('Mention organization name or Chester County')

    # Reputation indicators (25 points) - More trust words
    trust_words = ['free', 'confidential', 'professional', 'trained', 'certified', 'experienced', '24',
                   'safe', 'trusted', 'support', 'help', 'available', 'caring', 'dedicated']
    trust_found = sum(1 for tw in trust_words if tw in caption_lower)
    trust_score = min(25, trust_found * 5)
    score += trust_score
    if trust_score < 15:
        tips.append('Add trust signals (free, confidential, safe, available)')

    # Citable information (25 points) - More generous
    has_numbers = any(char.isdigit() for char in caption)
    has_specifics = any(w in caption_lower for w in ['services', 'resources', 'hotline', 'shelter', 'counseling', 'advocacy'])
    citable_score = 0
    if has_numbers:
        citable_score += 10
    if has_specifics:
        citable_score += 10
    if len(caption) > 100:
        citable_score += min(10, (len(caption) - 100) // 15)
    score += min(25, max(8, citable_score))  # Minimum 8 points
    if citable_score < 12:
        tips.append('Add specific services or statistics')

    # Expert voice (20 points) - More flexible phrasing
    expert_phrases = ['we provide', 'our services', 'we offer', 'our team', 'we support',
                      'we help', 'are here', 'is here', 'available for', 'reach out']
    if any(ep in caption_lower for ep in expert_phrases):
        score += 20
    else:
        score += 8  # Partial credit
        tips.append('Use "we" voice (we provide, we help, we are here)')

    return {
        'score': score,
        'max_score': max_score,
        'grade': score_to_grade(score),
        'focus': 'Authority & Reputation',
        'platform': 'ChatGPT / Perplexity',
        'metric': 'Brand Citations',
        'tips': tips
    }


def calculate_aeo_score(caption: str) -> dict:
    """Calculate Answer Engine Optimization score (Voice assistants)."""
    score = 0
    max_score = 100
    tips = []
    caption_lower = caption.lower()

    # Direct answers (30 points) - More patterns
    direct_patterns = ['you can', 'call', 'visit', 'contact', 'we offer', 'services include', 'help is available',
                       'reach out', 'get help', 'find support', 'available', 'here for you', 'dm us', 'message']
    direct_found = sum(1 for dp in direct_patterns if dp in caption_lower)
    direct_score = min(30, direct_found * 6)
    score += max(10, direct_score)  # Minimum 10 points
    if direct_score < 18:
        tips.append('Include action phrases (call, visit, reach out)')

    # Voice-friendly length (25 points) - More flexible
    sentences = [s.strip() for s in caption.replace('!', '.').replace('?', '.').split('.') if s.strip()]
    voice_ready = [s for s in sentences if 3 <= len(s.split()) <= 25]
    voice_score = min(25, len(voice_ready) * 7)
    score += max(10, voice_score)  # Minimum 10 points
    if voice_score < 14:
        tips.append('Use short, speakable sentences')

    # Question handling (20 points) - More triggers
    question_indicators = ['what', 'how', 'where', 'when', 'who', 'can i', 'is there', '?',
                          'wondering', 'need help', 'looking for', 'know that']
    handles_questions = any(qi in caption_lower for qi in question_indicators)
    if handles_questions:
        score += 20
    else:
        score += 8  # Partial credit for any caption
        tips.append('Add a question or address common concerns')

    # Local intent (25 points) - More signals
    local_signals = ['chester county', 'local', 'near', 'pennsylvania', 'pa', 'community', 'area', 'region']
    local_found = sum(1 for ls in local_signals if ls in caption_lower)
    local_score = min(25, local_found * 8)
    score += max(8, local_score)  # Minimum 8 points
    if local_score < 16:
        tips.append('Mention Chester County or local community')

    return {
        'score': score,
        'max_score': max_score,
        'grade': score_to_grade(score),
        'focus': 'Direct Answers',
        'platform': 'Siri / Alexa / Snippets',
        'metric': 'Voice Answer',
        'tips': tips
    }


def score_to_grade(score: int) -> str:
    """Convert numeric score to letter grade."""
    if score >= 90:
        return 'A'
    elif score >= 80:
        return 'B'
    elif score >= 70:
        return 'C'
    elif score >= 60:
        return 'D'
    else:
        return 'F'


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
