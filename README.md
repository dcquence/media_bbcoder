Python script for inputing a movie or tv show's tmdb page number and a video file that outputs bbcode generated for an info page.

**Important to edit these with your key and announce URL.**

    api_key = "<Your API Key>"

    createtorrent_cmd = [
            "python", "createtorrent.py", "-P", "--announce",
    ---->>  "<Tracker Announce URL>",
            video_folder, "--output", output_path
        ]
    
This requires mediainfo.exe, the CLI version, to run which can be grabbed separetly here:
https://mediaarea.net/en/MediaInfo/Download/Windows
Put the .exe in the same folder as the script, along with template_mediainfo.txt before running the script

template_mediainfo.txt is used for formatting the output and can be adjusted to your liking.

imgs.py script must be in the same folder as infoscraper.py along with the cookies.json file containing your info in the format of:
    
    {
      "inSpeed_speedian": "...........",
      "cf_clearance": "..........."
    }

code for imgs.py script is from PhlegethonAcheron's script here https://gist.github.com/PhlegethonAcheron/7e35933adb9a7fbc247c91b8455b59d8
