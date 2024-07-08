import requests
from imgurpython import ImgurClient
import subprocess
import tkinter as tk
from tkinter import filedialog

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

def format_bbcode(title, plot_summary, director, writers, cast, imgur_link, imdb_id, mediainfo_output):
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
    bbcode += f"[code]{mediainfo_output}[/code]"
    return bbcode

def select_video_file():
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename()
    return file_path

def read_template_file(file_path):
    with open(file_path, 'r') as f:
        return f.read()

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
    else:
        imgur_link = None

    # Select video file and extract information using mediainfo
    video_path = select_video_file()
    if not video_path:
        print("No file selected. Exiting.")
        return

    # Read mediainfo template file
    # mediainfo_template = read_template_file("template_mediainfo.txt")
    mediainfo_output = subprocess.check_output(['mediainfo', '--Inform=file://template_mediainfo.txt', video_path]).decode('utf-8')

    bbcode = format_bbcode(title, plot_summary, director, writers, cast, imgur_link, imdb_id, mediainfo_output)
    print(bbcode)

if __name__ == "__main__":
    main()

    import os; os.remove("poster.jpg")

input("Press enter to exit;")
