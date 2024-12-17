#Movie info bbcode generator for uploads
#Gathers info from tmdb and mediainfo, and uploads screenshots to imgur before generating final bbcode

#Fixes blurriness in the WPF window opened to select the video file
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

def format_bbcode(title, plot_summary, director, writers, cast, imgur_link, imdb_id, mediainfo_output, screenshot_links):
    bbcode = f"[center][img]{imgur_link}[/img]\n\n" if imgur_link else ""
    if imdb_id:
        imdb_link = f"https://www.imdb.com/title/{imdb_id}/"
        bbcode += f"[b]IMDb Link:[/b] {imdb_link}\n\n"
    bbcode += f"[b]Title:[/b] {title}\n\n"
    bbcode += f"[icon=plot]\n[b]Plot:[/b] {plot_summary}\n\n"
    bbcode += f"[b]Director:[/b] {director}\n\n"
    bbcode += f"[b]Writers:[/b] {', '.join(writers) if writers else 'Writers information not available'}\n\n"
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
    tmdb_id = input("Enter TMDB movie ID (e.g., 693134): ")
    api_key = "YOUR_TMDB_API_KEY"  # Replace "YOUR_TMDB_API_KEY" with your actual TMDB API key
    imgur_client_id = "YOUR_IMGUR_CLIENT_ID"  # Replace "YOUR_IMGUR_CLIENT_ID" with your actual Imgur client ID
    imgur_client_secret = "YOUR_IMGUR_CLIENT_SECRET"  # Replace "YOUR_IMGUR_CLIENT_SECRET" with your actual Imgur client secret

    title, plot_summary, director, writers, cast, poster_url, imdb_id = get_movie_info(tmdb_id, api_key)

    if poster_url:
        image_path = "poster.jpg"
        with open(image_path, 'wb') as f:
            f.write(requests.get(poster_url).content)
        imgur_link = upload_image_to_imgur(image_path, imgur_client_id, imgur_client_secret)
        os.remove(image_path)  # Delete the poster image file after uploading
    else:
        imgur_link = None

    # Select video file and extract information using mediainfo
    video_path = select_video_file()
    if not video_path:
        print("No file selected. Exiting.")
        return

    # Create screenshots and upload them to Imgur
    screenshots_folder = create_screenshots(video_path)
    screenshot_links = upload_screenshots(screenshots_folder, imgur_client_id, imgur_client_secret)

    # Read mediainfo template file
    mediainfo_output = subprocess.check_output(['mediainfo', '--Inform=file://template_mediainfo.txt', video_path]).decode('utf-8')

    bbcode = format_bbcode(title, plot_summary, director, writers, cast, imgur_link, imdb_id, mediainfo_output, screenshot_links)

    # Sanitize title for filename
    sanitized_title = sanitize_filename(title)
    output_file = os.path.join(os.path.dirname(__file__), f"{sanitized_title}.txt")
    
    # Save BBCode to a text file named using the sanitized movie title
    with open(output_file, 'w') as f:
        f.write(bbcode)

    print(f"BBCode saved to {output_file}")

if __name__ == "__main__":
    main()

input("Press enter to exit;")
