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

        # Add REACH Amplify discovery optimization data (AI + SEO)
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
                'posting_times': discovery_data.get('posting_times', {})
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
