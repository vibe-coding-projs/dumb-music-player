# Dumb Music Player

A lightweight web app optimized for Nokia 215 Opera Mini browser that allows users to browse songs and download MP3s. Features a Hebrew interface for the target audience.

## Features

### Public Interface
- Simple, minimal JavaScript interface optimized for Opera Mini
- Flat list of songs with names as they appear on YouTube
- Thumbnails displayed next to each song
- Download songs as MP3 files
- No login required for end users
- Only admin can add songs

### Admin Backend
- Password-protected admin interface
- Search YouTube with embedded video previews
- Select the correct video from search results
- Automatic download with thumbnail saving
- Edit song names
- Delete songs
- Full Hebrew interface

## Prerequisites

- Python 3.8 or higher
- FFmpeg (required for audio conversion)

### Install FFmpeg

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install ffmpeg
```

**Windows:**
Download from https://ffmpeg.org/download.html

## Installation

1. Clone or download this repository

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Create environment file:
```bash
cp .env.example .env
```

4. Edit `.env` and set your admin password:
```
ADMIN_PASSWORD=your-secure-password
SECRET_KEY=your-secret-key-here
```

## Usage

### Start the server

```bash
python app.py
```

The app will be available at:
- Public interface: http://localhost:5000
- Admin login: http://localhost:5000/admin

### For Production

For production deployment, use a production WSGI server:

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## Admin Workflow

1. Go to `/admin` and log in with your password
2. Click "הוסף שיר חדש" (Add New Song)
3. Enter song name and artist name
4. Click "חפש ביוטיוב" (Search YouTube)
5. See 5 results with embedded YouTube players
6. Watch/preview videos directly in the page
7. Select the correct video with radio button
8. Click "הורד את השיר הנבחר" (Download selected song)
9. Wait for download to complete (shows loading overlay)
10. Song will be added to the list
11. Edit the song name if needed

**Note**: Downloads are synchronous and may take 30-60 seconds. A dismissible loading overlay is shown during the process.

## Project Structure

```
dumb-music-player/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── data.json             # Songs database (auto-created)
├── downloads/            # MP3 files storage (auto-created)
├── static/
│   └── thumbnails/       # YouTube thumbnail images
├── templates/            # HTML templates (Hebrew)
│   ├── base.html
│   ├── index.html
│   ├── admin_login.html
│   ├── admin_dashboard.html
│   ├── admin_add_song.html
│   ├── admin_edit_song.html
│   └── admin_search_results.html
└── .env                  # Environment variables
```

## Data Structure

Each song in `data.json` has:
```json
{
  "display_name": "Song Title as it appears on YouTube",
  "filename": "song-file.mp3",
  "youtube_url": "https://www.youtube.com/watch?v=...",
  "thumbnail": "video_id.jpg"
}
```

No search terms are stored - only the final song information.

## YouTube Authentication (Optional)

The app will attempt to download YouTube videos without authentication first, which works for most public videos. However, some videos may require authentication.

**If downloads fail**, you can provide YouTube cookies:

**Option 1: Export cookies manually (Recommended for production)**
1. Install a browser extension like "Get cookies.txt LOCALLY" for Chrome/Firefox
2. Visit youtube.com and make sure you're logged in
3. Click the extension and export cookies
4. Save as `cookies.txt` in the project root directory

**Option 2: Use browser cookies (automatic - Local development only)**
On your local machine with Chrome installed, the app will try to use cookies from your Chrome browser automatically.

**Download Strategy**:
The app tries multiple strategies in order:
1. cookies.txt file (if exists)
2. Chrome browser cookies (if Chrome is installed)
3. No authentication (works for most public videos)

## Notes

- **Hebrew Interface**: All UI text is in Hebrew with RTL support for optimal viewing on Nokia 215
- **Opera Mini Optimization**: The UI uses minimal CSS, minimal JavaScript, and simple HTML that works well on feature phones
- **YouTube Downloads**: Uses yt-dlp to search and download from YouTube. Make sure this complies with YouTube's Terms of Service in your jurisdiction
- **Storage**: MP3 files are stored in the `downloads/` directory. Make sure you have enough disk space
- **Song Names**: Songs are initially named as they appear on YouTube, but can be edited through the admin interface

## License

MIT License - feel free to modify and use as needed.
# Test PyPI upload א' מרץ 29 16:42:55 IDT 2026
