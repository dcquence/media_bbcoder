# Media Info BBCode Generator for Uploads
# Gathers info from TMDb and Mediainfo, and calls imgs.py to upload screenshots and poster
# Written by dcquence 2024, modified to use imgs.py from PhlegethonAcheron

import ctypes
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

import requests
import subprocess
import tkinter as tk
from tkinter import filedialog
import os
import re
import sys
import json

template = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'template_mediainfo.txt')

def upload_images_via_imgs_py(image_paths, cookies_file="cookies.json"):
    import subprocess

    cmd = ["python", "imgs.py", "-c", cookies_file] + image_paths
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        output_lines = result.stdout.strip().splitlines()
        
        urls = []
        for line in output_lines:
            if ": " in line:
                urls.append(line.split(": ", 1)[1].strip())
        
        if len(urls) != len(image_paths):
            print(f"Warning: number of returned URLs ({len(urls)}) does not match number of images ({len(image_paths)})")
            urls.extend([None] * (len(image_paths) - len(urls)))

        return urls
    except Exception as e:
        print(f"Error uploading images via imgs.py: {e}")
        return [None] * len(image_paths)

def get_movie_info(tmdb_id, api_key):
    url = f"https://api.themoviedb.org/3/movie/{tmdb_id}?api_key={api_key}"
    data = requests.get(url).json()

    title = data.get('title', 'Title not available')
    plot_summary = data.get('overview', 'Plot summary not available')

    credits_data = requests.get(f"https://api.themoviedb.org/3/movie/{tmdb_id}/credits?api_key={api_key}").json()
    director = next((member['name'] for member in credits_data['crew'] if member['job'] == 'Director'), 'Director information not available')
    writers = [member['name'] for member in credits_data['crew'] if member['department'] == 'Writing']
    cast = [actor['name'] for actor in credits_data['cast'][:5]]

    poster_path = data.get('poster_path')
    poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else None

    imdb_id = data.get('imdb_id')
    return title, plot_summary, director, writers, cast, poster_url, imdb_id

def get_tv_series_info(tmdb_id, api_key, season=None, episode=None):
    data = requests.get(f"https://api.themoviedb.org/3/tv/{tmdb_id}?api_key={api_key}").json()
    title = data.get('name', 'Title not available')
    plot_summary = data.get('overview', 'Plot summary not available')

    credits_data = requests.get(f"https://api.themoviedb.org/3/tv/{tmdb_id}/credits?api_key={api_key}").json()
    creators = [creator['name'] for creator in data.get('created_by', [])]
    cast = [actor['name'] for actor in credits_data['cast'][:5]]

    poster_path = data.get('poster_path')
    poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else None

    episode_info = None
    if season is not None and episode is not None:
        episode_data = requests.get(f"https://api.themoviedb.org/3/tv/{tmdb_id}/season/{season}/episode/{episode}?api_key={api_key}").json()
        episode_info = {
            'title': episode_data.get('name', 'Episode title not available'),
            'plot': episode_data.get('overview', 'Episode plot not available')
        }

    return title, plot_summary, creators, cast, poster_url, episode_info

def format_bbcode(title, plot_summary, creators_or_director, writers, cast, poster_link, mediainfo_output, screenshot_links, is_movie, episode_info=None):
    bbcode = f"[center][img]{poster_link}[/img]\n\n" if poster_link else ""
    bbcode += f"[b]Title:[/b] {title}\n\n"
    if episode_info:
        bbcode += f"[b]Episode Title:[/b] {episode_info['title']}\n\n"
        bbcode += f"[b]Episode Plot:[/b] {episode_info['plot']}\n\n"
    bbcode += f"[icon=plot]\n[b]Plot:[/b] {plot_summary}\n\n"
    if is_movie:
        bbcode += f"[b]Director:[/b] {creators_or_director}\n\n"
        bbcode += f"[b]Writers:[/b] {', '.join(writers) if writers else 'Writers information not available'}\n\n"
    else:
        bbcode += f"[b]Creators:[/b] {', '.join(creators_or_director) if creators_or_director else 'Creators information not available'}\n\n"
    bbcode += f"[icon=cast]\n[b]Cast:[/b] {', '.join(cast) if cast else 'Cast information not available'}\n\n"
    bbcode += f"[icon=info][/center]\n\n"
    bbcode += f"[code]{mediainfo_output}[/code]\n\n"

    if screenshot_links:
        bbcode += "[center]\n"
        for link in screenshot_links:
            bbcode += f"[img]{link}[/img]\n"
        bbcode += "[/center]\n"

    return bbcode

def select_video_file():
    root = tk.Tk()
    root.withdraw()
    return filedialog.askopenfilename()

def create_screenshots(video_path):
    screenshots_folder = os.path.join(os.path.dirname(__file__), 'screenshots')
    os.makedirs(screenshots_folder, exist_ok=True)

    duration = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                                     '-of', 'default=noprint_wrappers=1:nokey=1', video_path],
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout)

    start_time = 5 * 60
    screenshot_interval = 5 * 60
    max_screenshots = 4

    screenshot_paths = []
    for i in range(start_time, min(int(duration), start_time + screenshot_interval * max_screenshots), screenshot_interval):
        screenshot_path = os.path.join(screenshots_folder, f'screenshot_{i//screenshot_interval + 1}.jpg')
        subprocess.run(['ffmpeg', '-ss', str(i), '-i', video_path, '-vframes', '1', '-q:v', '2', screenshot_path],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        screenshot_paths.append(screenshot_path)

    return screenshot_paths

def sanitize_filename(filename):
    sanitized = re.sub(r'[\\/:*?"<>|]', '', filename)
    return "_".join(sanitized.split())

def extract_season_episode(filename):
    filename = re.sub(r'(1080p|720p)', '', filename, flags=re.IGNORECASE)
    match = re.search(r'(\d{4})', filename)
    if match:
        episode_str = match.group(1)
        if len(episode_str) == 4:
            return int(episode_str[:2]), int(episode_str[2:])
    match = re.search(r'(s?(\d{1,2})[x|e](\d{2}))|(\d{3})|(\d{4})', filename, re.IGNORECASE)
    if match:
        if match.group(2) and match.group(3):
            return int(match.group(2)), int(match.group(3))
        elif match.group(4):
            ep = match.group(4)
            if len(ep) == 3:
                return int(ep[0]), int(ep[1:])
        elif match.group(5):
            ep = match.group(5)
            if len(ep) == 4:
                return int(ep[:2]), int(ep[2:])
    return None, None

def main():
    try:
        print("Starting Media Info BBCode Generator...")
        media_type = input("Is this for a movie or TV show? (movie/tv): ").strip().lower()
        if media_type not in ['movie', 'tv']:
            print("Invalid choice. Please enter 'movie' or 'tv'.")
            return

        tmdb_id = input("Enter TMDB ID: ")
        api_key = "<Your API Key>"

        video_path = select_video_file()

        if media_type == 'movie':
            title, plot_summary, director, writers, cast, poster_url, _ = get_movie_info(tmdb_id, api_key)
            creators_or_director = director
            episode_info = None
        else:
            tv_scope = input("Is this for the entire series or a single episode? (series/episode): ").strip().lower()
            if tv_scope == 'episode':
                season, episode = extract_season_episode(os.path.basename(video_path))
                if not season or not episode:
                    print("Failed to extract season and episode from filename.")
                    return
            else:
                season, episode = None, None
            title, plot_summary, creators, cast, poster_url, episode_info = get_tv_series_info(tmdb_id, api_key, season, episode)
            creators_or_director = creators
            writers = None

        # Collect images to upload
        image_paths = []
        if poster_url:
            poster_path = "poster.jpg"
            with open(poster_path, 'wb') as f:
                f.write(requests.get(poster_url).content)
            image_paths.append(poster_path)

        screenshot_paths = create_screenshots(video_path)
        image_paths.extend(screenshot_paths)

        # Upload images via imgs.py
        print("Uploading images via imgs.py...")
        image_urls = upload_images_via_imgs_py(image_paths)
        poster_link = image_urls[0] if poster_url else None
        screenshot_links = image_urls[1:] if poster_url else image_urls

        # Cleanup local images
        for path in image_paths:
            if os.path.exists(path):
                os.remove(path)

        # Fetch MediaInfo
        mediainfo_output = subprocess.check_output(['mediainfo', '--Inform=file://' + template, video_path], text=True)

        bbcode = format_bbcode(title, plot_summary, creators_or_director, writers, cast, poster_link, mediainfo_output, screenshot_links, media_type=='movie', episode_info)

        output_filename = sanitize_filename(title) + ".txt"
        with open(output_filename, 'w', encoding='utf-8') as f:
            f.write(bbcode)

        print(f"BBCode saved to {output_filename}")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()

