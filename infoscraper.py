# Media Info BBCode Generator for Uploads
# Gathers info from TMDb and Mediainfo, and uploads screenshots to Imgur before generating final BBCode
# Written by dcquence 2024

import ctypes
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

import requests
from imgurpython import ImgurClient
import subprocess
import tkinter as tk
from tkinter import filedialog
import os
import re
import sys

template = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'template_mediainfo.txt')

def upload_image_to_imgur(image_path, client_id, client_secret):
    client = ImgurClient(client_id, client_secret)
    image = client.upload_from_path(image_path, anon=True)
    return image['link']

def get_movie_info(tmdb_id, api_key):
    url = f"https://api.themoviedb.org/3/movie/{tmdb_id}?api_key={api_key}"
    response = requests.get(url)
    data = response.json()

    title = data.get('title', 'Title not available')
    plot_summary = data.get('overview', 'Plot summary not available')

    credits_url = f"https://api.themoviedb.org/3/movie/{tmdb_id}/credits?api_key={api_key}"
    credits_response = requests.get(credits_url)
    credits_data = credits_response.json()

    director = next((member['name'] for member in credits_data['crew'] if member['job'] == 'Director'), 'Director information not available')
    writers = [member['name'] for member in credits_data['crew'] if member['department'] == 'Writing']
    cast = [actor['name'] for actor in credits_data['cast'][:5]]  # Get top 5 cast members

    poster_path = data.get('poster_path')
    poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else None

    imdb_id = data.get('imdb_id')

    return title, plot_summary, director, writers, cast, poster_url, imdb_id

def get_tv_series_info(tmdb_id, api_key, season=None, episode=None):
    url = f"https://api.themoviedb.org/3/tv/{tmdb_id}?api_key={api_key}"
    response = requests.get(url)
    data = response.json()

    title = data.get('name', 'Title not available')
    plot_summary = data.get('overview', 'Plot summary not available')

    credits_url = f"https://api.themoviedb.org/3/tv/{tmdb_id}/credits?api_key={api_key}"
    credits_response = requests.get(credits_url)
    credits_data = credits_response.json()

    creators = [creator['name'] for creator in data.get('created_by', [])]
    cast = [actor['name'] for actor in credits_data['cast'][:5]]

    poster_path = data.get('poster_path')
    poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else None

    episode_info = None
    if season is not None and episode is not None:
        episode_url = f"https://api.themoviedb.org/3/tv/{tmdb_id}/season/{season}/episode/{episode}?api_key={api_key}"
        episode_response = requests.get(episode_url)
        if episode_response.status_code == 200:
            episode_data = episode_response.json()
            episode_info = {
                'title': episode_data.get('name', 'Episode title not available'),
                'plot': episode_data.get('overview', 'Episode plot not available')
            }

    return title, plot_summary, creators, cast, poster_url, episode_info

def format_bbcode(title, plot_summary, creators_or_director, writers, cast, imgur_link, mediainfo_output, screenshot_links, is_movie, episode_info=None):
    bbcode = f"[center][img]{imgur_link}[/img]\n\n" if imgur_link else ""
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

    for link in screenshot_links:
        bbcode += f"[img]{link}[/img]\n"

    return bbcode

def select_video_file():
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename()
    return file_path

def read_template_file(file_path):
    with open(file_path, 'r') as f:
        return f.read()

def create_screenshots(video_path):
    screenshots_folder = os.path.join(os.path.dirname(__file__), 'screenshots')
    os.makedirs(screenshots_folder, exist_ok=True)

    result = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', video_path],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    duration = float(result.stdout)

    start_time = 5 * 60

    screenshot_interval = 5 * 60
    max_screenshots = 4
    for i in range(start_time, min(int(duration), start_time + screenshot_interval * max_screenshots), screenshot_interval):
        screenshot_path = os.path.join(screenshots_folder, f'screenshot_{i//screenshot_interval + 1}.jpg')
        subprocess.run(['ffmpeg', '-ss', str(i), '-i', video_path, '-vframes', '1', '-q:v', '2', screenshot_path],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    return screenshots_folder

def upload_screenshots(screenshots_folder, client_id, client_secret):
    imgur_links = []
    for screenshot in os.listdir(screenshots_folder):
        screenshot_path = os.path.join(screenshots_folder, screenshot)
        link = upload_image_to_imgur(screenshot_path, client_id, client_secret)
        imgur_links.append(link)
        os.remove(screenshot_path)
    return imgur_links

def sanitize_filename(filename):
    sanitized = re.sub(r'[\\/:*?"<>|]', '', filename)
    sanitized = "_".join(sanitized.split())
    return sanitized

import re

def extract_season_episode(filename):
    filename = re.sub(r'(1080p|720p)', '', filename, flags=re.IGNORECASE)
    print(f"Extracting season and episode from filename: {filename}")

    match = re.search(r'(\d{4})', filename)
    if match:
        episode_str = match.group(1)
        if len(episode_str) == 4:
            season = int(episode_str[:2])
            episode = int(episode_str[2:])
            print(f"Matched 4-digit format: Season {season}, Episode {episode}")
            return season, episode

    match = re.search(r'(s?(\d{1,2})[x|e](\d{2}))|(\d{3})|(\d{4})', filename, re.IGNORECASE)
    if match:
        print(f"Regex match: {match.groups()}") 
        if match.group(2) and match.group(3):
            season = int(match.group(2))
            episode = int(match.group(3))
            return season, episode
        
        elif match.group(4):
            episode_str = match.group(4)
            if len(episode_str) == 3:
                season = int(episode_str[0])
                episode = int(episode_str[1:])
                return season, episode

        elif match.group(5):
            episode_str = match.group(5)
            if len(episode_str) == 4:
                season = int(episode_str[:2])
                episode = int(episode_str[2:])
                return season, episode

    return None, None

def main():
    try:
        print("Starting Media Info BBCode Generator...")
        media_type = input("Is this for a movie or TV show? (movie/tv): ").strip().lower()
        if media_type not in ['movie', 'tv']:
            print("Invalid choice. Please enter 'movie' or 'tv'.")
            input("Press Enter to exit.")
            return

        tmdb_id = input("Enter TMDB ID: ")
        api_key = "<YOUR_TMDB_API_KEY"  # Replace with your actual TMDB API key
        imgur_client_id = "<YOUR_IMGUR_CLIENT_ID>"  # Replace with your actual Imgur client ID
        imgur_client_secret = "<YOUR_IMGUR_CLIENT_SECRET>"  # Replace with your actual Imgur client secret

        video_path = select_video_file()

        if media_type == 'movie':
            print("Fetching movie info...")
            title, plot_summary, director, writers, cast, poster_url, tmdb_id = get_movie_info(tmdb_id, api_key)
            creators_or_director = director
            episode_info = None
        else:
            tv_scope = input("Is this for the entire series or a single episode? (series/episode): ").strip().lower()
            if tv_scope not in ['series', 'episode']:
                print("Invalid choice. Please enter 'series' or 'episode'.")
                input("Press Enter to exit.")
                return

            if tv_scope == 'episode':
                season, episode = extract_season_episode(os.path.basename(video_path))
                if not season or not episode:
                    print("Failed to extract season and episode from filename.")
                    input("Press Enter to exit.")
                    return
            else:
                season, episode = None, None

            print("Fetching TV series info...")
            title, plot_summary, creators, cast, poster_url, episode_info = get_tv_series_info(tmdb_id, api_key, season, episode)
            creators_or_director = creators
            writers = None
            tmdb_id = None

        if poster_url:
            print("Downloading poster...")
            image_path = "poster.jpg"
            with open(image_path, 'wb') as f:
                f.write(requests.get(poster_url).content)
            imgur_link = upload_image_to_imgur(image_path, imgur_client_id, imgur_client_secret)
            os.remove(image_path)
        else:
            imgur_link = None

        print("Creating screenshots...")
        screenshots_folder = create_screenshots(video_path)
        print("Uploading screenshots to Imgur...")
        screenshot_links = upload_screenshots(screenshots_folder, imgur_client_id, imgur_client_secret)

        print("Fetching MediaInfo...")
        mediainfo_output = subprocess.check_output(['mediainfo', '--Inform=file://' + template, video_path], text=True)

        print("Formatting BBCode...")
        bbcode = format_bbcode(title, plot_summary, creators_or_director, writers, cast, imgur_link, mediainfo_output, screenshot_links, media_type == 'movie', episode_info)

        output_filename = sanitize_filename(title) + ".txt"
        with open(output_filename, 'w', encoding='utf-8') as f:
            f.write(bbcode)

        print(f"BBCode saved to {output_filename}")
    except Exception as e:
        print(f"An error occurred: {e}")
        input("Press Enter to exit.")

if __name__ == "__main__":
    main()
