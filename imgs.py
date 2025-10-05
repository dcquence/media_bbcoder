import argparse
import glob
import sys
import json
import os
import requests
import datetime
from requests_toolbelt import MultipartEncoder
import re

ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'gif', 'png', 'bmp', 'ico', 'svg', 'svgz', 'tif', 'tiff', 'raw', 'webp', 'heic'}

def upload_img(image_path, speed_cookies: dict, bound='pyuploaded', logfile=None):
    multipart_boundary_separator = bound

    multipartdata = MultipartEncoder(
        fields={
            'MAX_FILE_SIZE': '2000000',
            'jxt': '5',
            'jxw': 'img',
            'a': '1',
            'file': ((os.path.basename(image_path)), open(image_path, 'rb'), 'image/jpeg')
        },
        boundary=multipart_boundary_separator
    )

    myheaders = {
        'Host': 'speed.cd',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/png,image/svg+xml,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Referer': 'https://speed.cd/user/Activity',
        'Content-Type': multipartdata.content_type,
        'Content-Length': str(multipartdata.len),
        'Origin': 'https://speed.cd',
        'Connection': 'keep-alive',
        'Sec-Fetch-Dest': 'iframe',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-User': '?1',
        'Priority': 'u=4'
    }

    response = requests.post(url='https://speed.cd/API', data=multipartdata, cookies=speed_cookies, headers=myheaders)

    pattern = r"https://cdn\.speed\.cd/u/i/\d+/[\w-]+\.[a-z]+"
    match = re.search(pattern, str(response.content).replace("\\", ""))

    if (logfile is not None):
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open('response_details.txt', 'a') as fileout:
            fileout.write(f'\n\n--- Response at {current_time} ---\n')
            fileout.write(f'File Info:\n')
            fileout.write(f'\tFile Name: {image_path}\n')
            fileout.write(f'\tFile Size: {str(multipartdata.len)}\n')
            fileout.write(f'\tFile Type: {multipartdata.content_type}\n')
            fileout.write("Request:\n")
            fileout.write(f"\tRequest Headers: \n\t\t{response.request.headers}\n")
            fileout.write(f"\tRequest Body: \n\t\t{response.request.body}\n")
            fileout.write("Response:\n")
            fileout.write(f"\tStatus Code: {response.status_code}\n")
            fileout.write(f"\tHeaders: {response.headers}\n")
            fileout.write(f"\tContent: {response.content}\n")
            fileout.write(f"\tText: {response.text}\n")
            fileout.write(f"\tRaw: {response.raw}\n")
            fileout.write(f"\tCookies: {str(response.cookies.values())}\n")
        fileout.close()

    if match:
        return (match.group())
    else:
        if response.status_code != 200:
            print(
                f"Error: \n\tServer returned code {response.status_code}\n\t{response.reason}\n\t{str(response.content)}",
                file=sys.stderr)
            return -1
        else:
            print(
                f"Unspecified Error (Server returned OK):\n\t{str(response.content)}\n\t{str(response.reason)}\n\t{response.raw}",
                file=sys.stderr)
            return -1

def load_cookies(cookie_path: str):
    with open(cookie_path) as json_file:
        cookies = json.load(json_file)
        json_file.close()
    return cookies

def is_file_valid(f):
    if not os.path.exists(f):
        print(f"Warning: {f} does not exist and will be ignored.", file=sys.stderr)
        return False
    if f.split('.')[-1].lower() not in ALLOWED_EXTENSIONS:
        print(f"Warning: {f} has an invalid extension and will be ignored.\n\t"
              f"Valid extensions are: {str(ALLOWED_EXTENSIONS)}", file=sys.stderr)
        return False
    if os.path.getsize(f) > 2000000:
        sub = re.sub(r'\.\w+$', '.jpeg', os.path.basename(f))
        print(f"Warning - Max Image Size Exceeded - Ignoring file:\n\t"
              f"{os.path.basename(f)} is {os.path.getsize(f) / 1000} KB. Max allowed size is 2000 KB.\n\t"
              f"Run the following command to reencode the image to an allowed size:\n"
              f"magick '{f}' -define jpeg:extent=2048kb -strip '{os.path.dirname(f)}/resized_{sub}'",
              file=sys.stderr)
        return False
    return True

def process_files(file_list, args):
    urls = []
    print(f"Starting upload of {len(file_list)} files:") if args.verbose and len(file_list) > 1 else None
    cookies_from_file = load_cookies(args.cookies)

    urls = []
    for f in file_list:
        print(f"Uploading {f}...") if args.verbose else None
        new_url = f"https://speed.cd/u/i/testing/{os.path.basename(f)}" if args.testing else upload_img(f, speed_cookies=cookies_from_file, bound=args.separator, logfile=args.logfile)
        if(type(new_url)==str):
            urls.append([new_url, f])
            print(f"{f} successfuly uploaded to {new_url}")  if args.verbose else None
        else:
            print(f"{f} failed to upload") if args.verbose else None

    if args.bbcode:
        [print(f"[img={os.path.basename(uf[1])}]{uf[0]}[/img]") for uf in urls]
    else:
        [print(f"{uf[1]}: {uf[0]}") for uf in urls]

def main():
    # region parser_setup
    parser = argparse.ArgumentParser(description="Upload images to speed.cd\nWildcards and multiple")
    parser.add_argument('-c', '--cookies', type=str, help='path to the cookies file', required=True)
    parser.add_argument('-l', '--logfile', type=str, default=None, help='path to the output log file')
    parser.add_argument('-t', '--testing', action='store_true', default=False,
                        help='preview the files to be uploaded without actually uploading')
    parser.add_argument('-s', '--separator', type=str, default='pyuploader',
                        help="Multipart form separator, no real reason to use this option")
    parser.add_argument('-v', '--verbose', action='store_true', default=False, help='increase output verbosity')
    parser.add_argument('-b', '--bbcode', action='store_true', default=False,
                        help='output urls formatted as bbcode (useful for integrating into bash scripts)')
    parser.add_argument('files', nargs='+', help='file paths or patterns to process')

    args = parser.parse_args()
    # endregion

    if args.verbose:
        print("Verbose mode is enabled")
        print(f"Using cookies file: {args.cookies}")
        print(f"Logging output to {args.logfile}") if args.logfile else print(f"Logging disabled")
        print(f"Testing mode: {'TRUE' if args.testing else 'FALSE'}")
        print(f"BBCODE mode: {'TRUE' if args.bbcode else 'FALSE'}\n")

    possible_files = []
    for file_pattern in args.files:
        if '*' in file_pattern or '?' in file_pattern or '[' in file_pattern:
            # Use globbing for patterns
            expanded_files = glob.glob(file_pattern)
            possible_files.extend(expanded_files)
        else:
            possible_files.append(file_pattern) # Individual file

    possible_files = list(dict.fromkeys(possible_files))
    valid_files = [file for file in possible_files if is_file_valid(file)]

    if (len(valid_files) == 0):
        print("Error - No valid files to process!", file=sys.stderr)
        exit(1)

    if args.verbose:
        print("Files to process:", file=sys.stdout)
        for file in valid_files:
            print(file, file=sys.stdout)

    process_files(valid_files, args)

if __name__ == '__main__':
    main()
