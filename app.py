import os
import json
import re
import requests
import yt_dlp
import sys
import time
from flask import Flask, render_template, request, redirect, url_for, session, send_file, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from dotenv import load_dotenv
from pathlib import Path

# Force unbuffered output for real-time logging
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin')

# Log EVERY request before it reaches any route
@app.before_request
def log_request():
    print(f"\n>>> [MIDDLEWARE] Request received: {request.method} {request.path}", flush=True)
    print(f">>> [MIDDLEWARE] Time: {time.time()}", flush=True)
    sys.stdout.flush()

# Add ngrok skip warning header to all responses
@app.after_request
def add_ngrok_header(response):
    response.headers['ngrok-skip-browser-warning'] = 'true'
    return response

# Persistent Data Directory
# This folder will be mounted as a persistent disk in Render
PERSISTENT_DATA_DIR = Path(os.getenv('PERSISTENT_DATA_PATH', 'persistent_data'))
PERSISTENT_DATA_DIR.mkdir(exist_ok=True)

# Subdirectories for different types of data
DOWNLOADS_DIR = PERSISTENT_DATA_DIR / 'downloads'
DOWNLOADS_DIR.mkdir(exist_ok=True)

THUMBNAILS_DIR = PERSISTENT_DATA_DIR / 'thumbnails'
THUMBNAILS_DIR.mkdir(exist_ok=True)

DATA_FILE = PERSISTENT_DATA_DIR / 'data.json'

# Initialize data file
if not DATA_FILE.exists():
    DATA_FILE.write_text(json.dumps({'songs': []}, indent=2))

# Cookies file path (also in persistent storage)
COOKIES_FILE = PERSISTENT_DATA_DIR / 'cookies.txt'

print(f"[INIT] Persistent data directory: {PERSISTENT_DATA_DIR.absolute()}", flush=True)
print(f"[INIT] Downloads directory: {DOWNLOADS_DIR.absolute()}", flush=True)
print(f"[INIT] Thumbnails directory: {THUMBNAILS_DIR.absolute()}", flush=True)
print(f"[INIT] Data file: {DATA_FILE.absolute()}", flush=True)
print(f"[INIT] Cookies file: {COOKIES_FILE.absolute()}", flush=True)


def load_data():
    """Load songs data from JSON file."""
    with open(DATA_FILE, 'r') as f:
        return json.load(f)


def save_data(data):
    """Save songs data to JSON file."""
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def search_youtube(query, num_results=5):
    """Search YouTube for a song and return top results with metadata."""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(f"ytsearch{num_results}:{query}", download=False)
            if result and 'entries' in result and len(result['entries']) > 0:
                videos = []
                for video in result['entries']:
                    videos.append({
                        'id': video['id'],
                        'url': f"https://www.youtube.com/watch?v={video['id']}",
                        'title': video.get('title', ''),
                        'thumbnail': video.get('thumbnail', ''),
                        'duration': video.get('duration', 0),
                        'channel': video.get('channel', video.get('uploader', ''))
                    })
                return videos
    except Exception as e:
        print(f"Error searching YouTube: {e}")

    return []


def download_from_youtube(youtube_url, output_path, thumbnail_path=None):
    """Download audio from YouTube as MP3 and optionally save thumbnail.
    Returns True on success, False if all strategies fail."""
    print(f"  [download_from_youtube] Starting download for: {youtube_url}", flush=True)

    # Check if cookies file exists
    print(f"  [download_from_youtube] Checking for cookies.txt at {COOKIES_FILE}... {'FOUND' if COOKIES_FILE.exists() else 'NOT FOUND'}", flush=True)

    ydl_opts = {
        'format': 'bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': str(output_path.with_suffix('')),
        'quiet': False,
        'no_warnings': False,
        'writethumbnail': True if thumbnail_path else False,
        'extract_audio': True,
        'extractor_args': {'youtube': {'player_client': ['ios', 'android', 'web']}},
        'js_runtimes': ['node', 'deno'],
    }

    # Try multiple strategies for cookie authentication
    strategies = []

    # Strategy 1: Use cookies.txt if it exists
    if COOKIES_FILE.exists():
        strategy_opts = ydl_opts.copy()
        strategy_opts['cookiefile'] = str(COOKIES_FILE)
        strategies.append(("cookies.txt file", strategy_opts))

    # Strategy 2: Try Chrome browser cookies (only works locally)
    # DISABLED: Chrome cookie extraction hangs on macOS due to Keychain issues
    # chrome_check = Path.home() / '.config' / 'google-chrome'
    # if chrome_check.exists() or Path('/Applications/Google Chrome.app').exists():
    #     strategy_opts = ydl_opts.copy()
    #     strategy_opts['cookiesfrombrowser'] = ('chrome',)
    #     strategies.append(("Chrome browser cookies", strategy_opts))

    # Strategy 3: Try without cookies (fallback)
    strategies.append(("no authentication", ydl_opts.copy()))

    print(f"  [download_from_youtube] Will try {len(strategies)} strategies", flush=True)

    # Try each strategy until one works
    for strategy_index, (strategy_name, opts) in enumerate(strategies, 1):
        try:
            print(f"\n  [download_from_youtube] === STRATEGY {strategy_index}/{len(strategies)}: {strategy_name} ===", flush=True)
            print(f"  [download_from_youtube] Downloading from: {youtube_url}", flush=True)
            print(f"  [download_from_youtube] Output path: {output_path}", flush=True)

            import time
            strategy_start = time.time()

            print(f"  [download_from_youtube] Creating YoutubeDL instance...", flush=True)
            with yt_dlp.YoutubeDL(opts) as ydl:
                print(f"  [download_from_youtube] Calling extract_info()...", flush=True)
                info = ydl.extract_info(youtube_url, download=True)
                print(f"  [download_from_youtube] extract_info() completed", flush=True)

            strategy_elapsed = time.time() - strategy_start
            print(f"  [download_from_youtube] Strategy took {strategy_elapsed:.2f} seconds", flush=True)

            # Check if the mp3 file was created
            print(f"  [download_from_youtube] Checking if file exists at: {output_path}", flush=True)
            if output_path.exists():
                print(f"  [download_from_youtube] ✓ File created successfully: {output_path}", flush=True)
                file_size = output_path.stat().st_size / (1024 * 1024)  # MB
                print(f"  [download_from_youtube] File size: {file_size:.2f} MB", flush=True)

                # Handle thumbnail if requested
                if thumbnail_path:
                    print(f"  [download_from_youtube] Processing thumbnail...", flush=True)
                    # yt-dlp saves thumbnail with same basename as audio file
                    possible_thumb_exts = ['.jpg', '.png', '.webp']
                    base_path = output_path.with_suffix('')
                    for ext in possible_thumb_exts:
                        thumb_file = base_path.with_suffix(ext)
                        if thumb_file.exists():
                            # Move thumbnail to desired location
                            import shutil
                            shutil.move(str(thumb_file), str(thumbnail_path))
                            print(f"  [download_from_youtube] ✓ Thumbnail saved: {thumbnail_path}", flush=True)
                            break
                    else:
                        print(f"  [download_from_youtube] ⚠ No thumbnail found", flush=True)

                print(f"  [download_from_youtube] === SUCCESS ===", flush=True)
                return True
            else:
                print(f"  [download_from_youtube] ✗ File not created at expected path: {output_path}", flush=True)
                # Check if file exists without extension
                base_path = output_path.with_suffix('')
                if base_path.exists():
                    print(f"  [download_from_youtube] Found file without .mp3 extension, renaming...", flush=True)
                    base_path.rename(output_path)
                    print(f"  [download_from_youtube] === SUCCESS (after rename) ===", flush=True)
                    return True
                else:
                    print(f"  [download_from_youtube] File not found even without extension", flush=True)
        except Exception as e:
            import traceback
            print(f"  [download_from_youtube] ✗ Strategy '{strategy_name}' FAILED", flush=True)
            print(f"  [download_from_youtube] Error: {e}", flush=True)
            print(f"  [download_from_youtube] Traceback:", flush=True)
            traceback.print_exc()
            sys.stdout.flush()
            sys.stderr.flush()
            # Continue to next strategy
            continue

    # All strategies failed
    print(f"  [download_from_youtube] === ALL STRATEGIES FAILED ===", flush=True)
    print(f"  [download_from_youtube] Error: All download strategies failed for {youtube_url}", flush=True)
    print("  [download_from_youtube] Tip: For better reliability, export YouTube cookies to cookies.txt file", flush=True)
    return False


# ============ PUBLIC ROUTES ============

@app.route('/')
def index():
    """Public homepage showing all songs."""
    data = load_data()
    return render_template('index.html', songs=data['songs'])


@app.route('/download/<int:song_id>')
def download_song(song_id):
    """Download a specific song as MP3."""
    data = load_data()

    if song_id >= len(data['songs']):
        return "שיר לא נמצא", 404

    song = data['songs'][song_id]
    file_path = DOWNLOADS_DIR / song['filename']

    if not file_path.exists():
        return "קובץ לא נמצא", 404

    return send_file(
        file_path,
        as_attachment=True,
        download_name=song['filename'],
        mimetype='audio/mpeg'
    )


@app.route('/thumbnails/<path:filename>')
def serve_thumbnail(filename):
    """Serve thumbnail images from persistent storage."""
    thumbnail_path = THUMBNAILS_DIR / filename

    if not thumbnail_path.exists():
        return "תמונה לא נמצאה", 404

    return send_file(
        thumbnail_path,
        mimetype='image/jpeg'
    )


# ============ ADMIN ROUTES ============

@app.route('/admin')
def admin_login():
    """Admin login page."""
    if 'admin' in session:
        return redirect(url_for('admin_dashboard'))
    return render_template('admin_login.html')


@app.route('/admin/login', methods=['POST'])
def admin_login_post():
    """Handle admin login."""
    password = request.form.get('password')

    if password == ADMIN_PASSWORD:
        session['admin'] = True
        return redirect(url_for('admin_dashboard'))

    return render_template('admin_login.html', error='סיסמה שגויה')


@app.route('/admin/logout')
def admin_logout():
    """Admin logout."""
    session.pop('admin', None)
    return redirect(url_for('index'))


@app.route('/admin/dashboard')
def admin_dashboard():
    """Admin dashboard showing all songs."""
    if 'admin' not in session:
        return redirect(url_for('admin_login'))

    data = load_data()
    return render_template('admin_dashboard.html', songs=data['songs'])


@app.route('/admin/add-song', methods=['GET', 'POST'])
def admin_add_song():
    """Search for a song on YouTube."""
    if 'admin' not in session:
        return redirect(url_for('admin_login'))

    if request.method == 'POST':
        print("\n" + "="*80, flush=True)
        print("SEARCH REQUEST STARTED", flush=True)
        print("="*80, flush=True)

        search_query = request.form.get('search_query', '').strip()

        print(f"Search Query: {search_query}", flush=True)

        if not search_query:
            print("ERROR: Missing search_query", flush=True)
            return render_template('admin_add_song.html', error='נא למלא שדה חיפוש')

        # Search YouTube
        print("\n>>> CALLING search_youtube()...", flush=True)
        import time
        start_time = time.time()
        search_results = search_youtube(search_query)
        elapsed_time = time.time() - start_time
        print(f"<<< search_youtube() COMPLETED in {elapsed_time:.2f} seconds", flush=True)
        print(f"Found {len(search_results)} results", flush=True)

        if not search_results:
            print("ERROR: No search results found", flush=True)
            return render_template('admin_add_song.html', error='לא נמצא שיר ביוטיוב')

        # Show search results
        # For backward compatibility with the template, we'll pass the query as both song_name and artist_name
        print("\n>>> Rendering search results page...", flush=True)
        print("="*80, flush=True)
        print("SEARCH REQUEST COMPLETED", flush=True)
        print("="*80 + "\n", flush=True)
        return render_template('admin_search_results.html',
                             results=search_results,
                             song_name=search_query,
                             artist_name='')

    return render_template('admin_add_song.html')


@app.route('/admin/ping', methods=['GET', 'POST'])
def admin_ping():
    """Simple test endpoint to verify requests reach the server."""
    print("!!! PING ENDPOINT HIT !!!", flush=True)
    print(f"Method: {request.method}", flush=True)
    print(f"Form data: {dict(request.form)}", flush=True)
    return jsonify({'status': 'ok', 'message': 'Server is reachable'})


@app.route('/admin/download-song', methods=['POST'])
def admin_download_song():
    """Download selected song from YouTube."""
    import sys
    sys.stdout.flush()
    sys.stderr.flush()
    print("\n" + "="*80, flush=True)
    print("!!! DOWNLOAD ROUTE HIT !!!", flush=True)
    print("DOWNLOAD REQUEST STARTED", flush=True)
    print(f"Request method: {request.method}", flush=True)
    print(f"Request path: {request.path}", flush=True)
    print(f"Request form keys: {list(request.form.keys())}", flush=True)
    print("="*80, flush=True)

    if 'admin' not in session:
        print("ERROR: User not authenticated", flush=True)
        return redirect(url_for('admin_login'))

    youtube_url = request.form.get('youtube_url')
    youtube_title = request.form.get('youtube_title')
    youtube_thumbnail = request.form.get('youtube_thumbnail')
    song_name = request.form.get('song_name', '')
    artist_name = request.form.get('artist_name', '')

    # Combine song_name and artist_name if both exist, otherwise use just song_name
    search_query = f"{song_name} {artist_name}".strip() if artist_name else song_name

    print(f"Search Query: {search_query}", flush=True)
    print(f"YouTube URL: {youtube_url}", flush=True)
    print(f"YouTube Title: {youtube_title}", flush=True)

    if not youtube_url or not youtube_title:
        print("ERROR: Missing youtube_url or youtube_title", flush=True)
        return redirect(url_for('admin_add_song'))

    # Generate filename from search query
    safe_name = re.sub(r'[^\w\s-]', '', search_query)
    safe_name = re.sub(r'[-\s]+', '-', safe_name)
    filename = f"{safe_name}.mp3"

    # Generate thumbnail filename
    video_id = youtube_url.split('watch?v=')[-1]
    thumbnail_filename = f"{video_id}.jpg"
    thumbnail_path = THUMBNAILS_DIR / thumbnail_filename

    print(f"Output filename: {filename}", flush=True)
    print(f"Thumbnail filename: {thumbnail_filename}", flush=True)
    print("\n>>> CALLING download_from_youtube()...", flush=True)

    # Download from YouTube
    output_path = DOWNLOADS_DIR / filename

    import time
    start_time = time.time()
    success = download_from_youtube(youtube_url, output_path, thumbnail_path)
    elapsed_time = time.time() - start_time

    print(f"<<< download_from_youtube() COMPLETED in {elapsed_time:.2f} seconds", flush=True)
    print(f"Success: {success}", flush=True)

    if not success:
        print("ERROR: Download failed, re-rendering search results", flush=True)
        search_results = search_youtube(search_query)
        return render_template('admin_search_results.html',
                             results=search_results,
                             song_name=search_query,
                             artist_name='',
                             error='שגיאה בהורדה מיוטיוב. אולי צריך לעדכן cookies?')

    print("\n>>> Adding song to database...", flush=True)
    # Add to songs list
    data = load_data()
    data['songs'].append({
        'display_name': youtube_title,
        'filename': filename,
        'youtube_url': youtube_url,
        'thumbnail': thumbnail_filename if thumbnail_path.exists() else None
    })
    save_data(data)
    print("<<< Song added to database successfully", flush=True)

    print("\n>>> Redirecting to admin dashboard...", flush=True)
    print("="*80, flush=True)
    print("DOWNLOAD REQUEST COMPLETED", flush=True)
    print("="*80 + "\n", flush=True)

    return redirect(url_for('admin_dashboard'))


@app.route('/admin/song/<int:song_id>/edit', methods=['GET', 'POST'])
def admin_edit_song(song_id):
    """Edit a song's display name."""
    if 'admin' not in session:
        return redirect(url_for('admin_login'))

    data = load_data()

    if song_id >= len(data['songs']):
        return "שיר לא נמצא", 404

    song = data['songs'][song_id]

    if request.method == 'POST':
        new_name = request.form.get('display_name')

        if not new_name:
            return render_template('admin_edit_song.html', song=song, song_id=song_id, error='נא למלא שם')

        # Update song name
        data['songs'][song_id]['display_name'] = new_name
        save_data(data)

        return redirect(url_for('admin_dashboard'))

    return render_template('admin_edit_song.html', song=song, song_id=song_id)


@app.route('/admin/song/<int:song_id>/delete', methods=['POST'])
def admin_delete_song(song_id):
    """Delete a song."""
    if 'admin' not in session:
        return redirect(url_for('admin_login'))

    data = load_data()

    if song_id >= len(data['songs']):
        return "שיר לא נמצא", 404

    song = data['songs'][song_id]

    # Delete file
    file_path = DOWNLOADS_DIR / song['filename']
    if file_path.exists():
        file_path.unlink()

    # Remove from data
    data['songs'].pop(song_id)
    save_data(data)

    return redirect(url_for('admin_dashboard'))


@app.route('/admin/cookies', methods=['GET', 'POST'])
def admin_cookies():
    """Manage cookies.txt file for YouTube authentication."""
    if 'admin' not in session:
        return redirect(url_for('admin_login'))

    current_cookies = None
    cookies_exist = COOKIES_FILE.exists()

    if cookies_exist:
        try:
            current_cookies = COOKIES_FILE.read_text()
            # Only show first 500 chars for preview
            if len(current_cookies) > 500:
                current_cookies = current_cookies[:500] + '\n... (truncated)'
        except Exception as e:
            print(f"Error reading cookies.txt: {e}", flush=True)

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'update':
            cookies_content = request.form.get('cookies_content', '').strip()

            if not cookies_content:
                return render_template('admin_cookies.html',
                                     error='תוכן ה-cookies ריק',
                                     current_cookies=current_cookies,
                                     cookies_exist=cookies_exist)

            # Basic validation - check if it looks like Netscape cookie format
            lines = [line.strip() for line in cookies_content.split('\n') if line.strip()]
            if not any(line.startswith('#') or '\t' in line for line in lines):
                return render_template('admin_cookies.html',
                                     error='הפורמט של ה-cookies נראה לא תקין. צריך להיות בפורמט Netscape',
                                     current_cookies=current_cookies,
                                     cookies_exist=cookies_exist)

            # Save cookies.txt
            try:
                COOKIES_FILE.write_text(cookies_content)
                print(f"✓ cookies.txt updated successfully ({len(cookies_content)} bytes)", flush=True)
                return render_template('admin_cookies.html',
                                     success='קובץ cookies.txt עודכן בהצלחה!',
                                     current_cookies=cookies_content[:500] + '\n... (truncated)' if len(cookies_content) > 500 else cookies_content,
                                     cookies_exist=True)
            except Exception as e:
                print(f"Error writing cookies.txt: {e}", flush=True)
                return render_template('admin_cookies.html',
                                     error=f'שגיאה בשמירת הקובץ: {str(e)}',
                                     current_cookies=current_cookies,
                                     cookies_exist=cookies_exist)

        elif action == 'delete':
            if COOKIES_FILE.exists():
                try:
                    COOKIES_FILE.unlink()
                    print("✓ cookies.txt deleted", flush=True)
                    return render_template('admin_cookies.html',
                                         success='קובץ cookies.txt נמחק בהצלחה',
                                         current_cookies=None,
                                         cookies_exist=False)
                except Exception as e:
                    print(f"Error deleting cookies.txt: {e}", flush=True)
                    return render_template('admin_cookies.html',
                                         error=f'שגיאה במחיקת הקובץ: {str(e)}',
                                         current_cookies=current_cookies,
                                         cookies_exist=cookies_exist)

    return render_template('admin_cookies.html',
                         current_cookies=current_cookies,
                         cookies_exist=cookies_exist)


if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    app.run(debug=True, host='0.0.0.0', port=port)
