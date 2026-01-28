#!/usr/bin/env python3
"""
DVCCC Instagram Content Manager - Web Interface
"""

import os
import sys
import json
import sqlite3
import threading
import time
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.content import TextGenerator, ImageGenerator
from src.utils.image_hosting import get_uploader
from src.scheduler import start_web_scheduler, stop_web_scheduler

load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Database setup
DB_PATH = 'scheduled_posts.db'


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


# Initialize components
text_gen = TextGenerator(
    niche='domestic violence awareness',
    style='warm, personal, and empowering',
    hashtag_count=10
)
img_gen = ImageGenerator(output_dir='generated_images')

try:
    uploader = get_uploader()
except:
    uploader = None


@app.route('/')
def index():
    """Homepage - Create new content."""
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


@app.route('/generate', methods=['POST'])
def generate():
    """Generate content based on theme."""
    theme = request.form.get('theme', '').strip()

    if not theme:
        return jsonify({'error': 'Please provide a theme'}), 400

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
        return jsonify({'error': str(e)}), 500


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
        return jsonify({'error': str(e)}), 500


# Initialize database on startup
init_db()


if __name__ == '__main__':
    print("\n" + "="*60)
    print("  DVCCC Instagram Content Manager")
    print("="*60)
    print("\n  Open in browser: http://127.0.0.1:5001")
    print("  Background scheduler: ACTIVE")
    print("="*60 + "\n")

    # Start background scheduler
    start_web_scheduler()

    try:
        app.run(host='127.0.0.1', debug=True, port=5001, use_reloader=False)
    finally:
        stop_web_scheduler()
