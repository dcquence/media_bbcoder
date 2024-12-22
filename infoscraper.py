# Media Info BBCode Generator for Uploads
# Gathers info from TMDb and Mediainfo, and uploads screenshots to Imgur before generating final BBCode
# Written by dcquence 2024

# Fixes blurriness in the WPF window opened to select the video file
import ctypes
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)  # Set DPI awareness to Per Monitor
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

def upload_image_to_imgur(image_path, client_id, client_secret):
    client = ImgurClient(client_id, client_secret)
    image = client.upload_from_path(image_path, anon=True)
    return image['link']

def get_movie_info(tmdb_id, api_key):
    # Fetch basic movie info
    url = f"https://api.themoviedb.org/3/movie/{tmdb_id}?api_key={api_key}"
    response = requests.get(url)
    data = response.json()

    title = data.get('title', 'Title not available')
    plot_summary = data.get('overview', 'Plot summary not available')

    # Fetch credits (cast and crew) for the movie
    credits_url = f"https://api.themoviedb.org/3/movie/{tmdb_id}/credits?api_key={api_key}"
    credits_response = requests.get(credits_url)
    credits_data = credits_response.json()

    # Extract director, writers, and cast from the credits data
    director = next((member['name'] for member in credits_data['crew'] if member['job'] == 'Director'), 'Director information not available')
    writers = [member['name'] for member in credits_data['crew'] if member['department'] == 'Writing']
    cast = [actor['name'] for actor in credits_data['cast'][:5]]  # Get top 5 cast members

    # Fetch the poster image path
    poster_path = data.get('poster_path')
    poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else None

    # Fetch the IMDb ID
    imdb_id = data.get('imdb_id')

    return title, plot_summary, director, writers, cast, poster_url, imdb_id

def get_tv_series_info(tmdb_id, api_key):
    # Fetch basic TV series info
    url = f"https://api.themoviedb.org/3/tv/{tmdb_id}?api_key={api_key}"
    response = requests.get(url)
    data = response.json()

    title = data.get('name', 'Title not available')
    plot_summary = data.get('overview', 'Plot summary not available')

    # Fetch credits (cast and crew) for the TV series
    credits_url = f"https://api.themoviedb.org/3/tv/{tmdb_id}/credits?api_key={api_key}"
    credits_response = requests.get(credits_url)
    credits_data = credits_response.json()

    # Extract creators and cast from the credits data
    creators = [creator['name'] for creator in data.get('created_by', [])]
    cast = [actor['name'] for actor in credits_data['cast'][:5]]  # Get top 5 cast members

    # Fetch the poster image path
    poster_path = data.get('poster_path')
    poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else None

    return title, plot_summary, creators, cast, poster_url

def format_bbcode(title, plot_summary, creators_or_director, writers, cast, imgur_link, mediainfo_output, screenshot_links, is_movie):
    bbcode = f"[center][img]{imgur_link}[/img]\n\n" if imgur_link else ""
    bbcode += f"[b]Title:[/b] {title}\n\n"
    bbcode += f"[icon=plot]\n[b]Plot:[/b] {plot_summary}\n\n"
    if is_movie:
        bbcode += f"[b]Director:[/b] {creators_or_director}\n\n"
        bbcode += f"[b]Writers:[/b] {', '.join(writers) if writers else 'Writers information not available'}\n\n"
    else:
        bbcode += f"[b]Creators:[/b] {', '.join(creators_or_director) if creators_or_director else 'Creators information not available'}\n\n"
    bbcode += f"[icon=cast]\n[b]Cast:[/b] {', '.join(cast) if cast else 'Cast information not available'}\n\n"
    bbcode += f"[icon=info][/center]\n\n"
    bbcode += f"[code]{mediainfo_output}[/code]\n\n"

    # Add screenshot links
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
    # Create screenshots folder
    screenshots_folder = os.path.join(os.path.dirname(__file__), 'screenshots')
    os.makedirs(screenshots_folder, exist_ok=True)

    # Get the duration of the video in seconds
    result = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', video_path],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    duration = float(result.stdout)

    # Start taking screenshots from the 5-minute mark
    start_time = 5 * 60  # 5 minutes in seconds

    # Create screenshots every 15 minutes, maximum of 4 screenshots
    screenshot_interval = 15 * 60  # 15 minutes in seconds
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
        os.remove(screenshot_path)  # Delete the screenshot file after uploading
    return imgur_links

def sanitize_filename(filename):
    # Remove or replace invalid characters
    sanitized = re.sub(r'[\\/:*?"<>|]', '', filename)
    # Replace spaces with underscores
    sanitized = "_".join(sanitized.split())
    return sanitized

def main():
    try:
        print("Starting Media Info BBCode Generator...")
        media_type = input("Is this for a movie or TV show? (movie/tv): ").strip().lower()
        if media_type not in ['movie', 'tv']:
            print("Invalid choice. Please enter 'movie' or 'tv'.")
            input("Press Enter to exit.")
            return

        tmdb_id = input("Enter TMDB ID: ")
        api_key = "<YourAPIKey"  # Replace with your actual TMDB API key
        imgur_client_id = "<YourAPIKey>"  # Replace with your actual Imgur client ID
        imgur_client_secret = "<YourAPIKey>"  # Replace with your actual Imgur client secret

        if media_type == 'movie':
            print("Fetching movie info...")
            title, plot_summary, director, writers, cast, poster_url, imdb_id = get_movie_info(tmdb_id, api_key)
            creators_or_director = director
        else:
            print("Fetching TV series info...")
            title, plot_summary, creators, cast, poster_url = get_tv_series_info(tmdb_id, api_key)
            creators_or_director = creators
            writers = None
            imdb_id = None

        if poster_url:
            print("Downloading poster...")
            image_path = "poster.jpg"
            with open(image_path, 'wb') as f:
                f.write(requests.get(poster_url).content)
            imgur_link = upload_image_to_imgur(image_path, imgur_client_id, imgur_client_secret)
            os.remove(image_path)  # Delete the poster image file after uploading
        else:
            imgur_link = None

        video_path = select_video_file()
        print("Creating screenshots...")
        screenshots_folder = create_screenshots(video_path)
        print("Uploading screenshots to Imgur...")
        screenshot_links = upload_screenshots(screenshots_folder, imgur_client_id, imgur_client_secret)

        print("Fetching MediaInfo...")
        mediainfo_output = subprocess.check_output(['mediainfo', video_path], text=True)

        print("Formatting BBCode...")
        bbcode = format_bbcode(title, plot_summary, creators_or_director, writers, cast, imgur_link, mediainfo_output, screenshot_links, media_type == 'movie')

        output_filename = sanitize_filename(title) + ".txt"
        with open(output_filename, 'w') as f:
            f.write(bbcode)

        print(f"BBCode saved to {output_filename}")
    except Exception as e:
        print(f"An error occurred: {e}")
        input("Press Enter to exit.")

if __name__ == "__main__":
    main()
