#!/usr/bin/env python3
# Python 3.x torrent creator with dynamic piece size based on total data size
# Compatible with Windows paths
# Now includes -P / --private flag to set torrent as private

import os
import argparse
import hashlib
import math
import bencodepy

def determine_piece_size(total_size):
    """Determine piece size based on file/folder size (in bytes)."""
    mib = total_size / (1024 * 1024)
    if mib < 50:
        return 32 * 1024          # 32 KiB
    elif 50 <= mib <= 150:
        return 64 * 1024          # 64 KiB
    elif 150 < mib <= 512:
        return 256 * 1024         # 256 KiB
    elif 512 < mib <= 1024:
        return 512 * 1024         # 512 KiB
    elif 1024 < mib <= 2048:
        return 1 * 1024 * 1024    # 1 MiB
    elif 2048 < mib <= 5120:
        return 2 * 1024 * 1024    # 2 MiB
    elif 5120 < mib <= 11264:
        return 4 * 1024 * 1024    # 4 MiB
    else:
        return 8 * 1024 * 1024    # 8 MiB for larger

def get_total_size(path):
    """Calculate total size in bytes of a file or directory."""
    if os.path.isfile(path):
        return os.path.getsize(path)
    total = 0
    for root, dirs, files in os.walk(path):
        for f in files:
            total += os.path.getsize(os.path.join(root, f))
    return total

def create_torrent(path, announce_url, output_file, private=False):
    torrent_dict = {b"announce": announce_url.encode(), b"info": {}}

    total_size = get_total_size(path)
    piece_size = determine_piece_size(total_size)
    torrent_dict[b"info"][b"piece length"] = piece_size

    # Add private flag if requested
    if private:
        torrent_dict[b"info"][b"private"] = 1

    if os.path.isfile(path):
        with open(path, "rb") as f:
            data = f.read()
        torrent_dict[b"info"][b"name"] = os.path.basename(path).encode()
        pieces = b""
        for i in range(0, len(data), piece_size):
            piece = data[i:i+piece_size]
            pieces += hashlib.sha1(piece).digest()
        torrent_dict[b"info"][b"pieces"] = pieces
        torrent_dict[b"info"][b"length"] = len(data)
    else:
        torrent_dict[b"info"][b"name"] = os.path.basename(os.path.normpath(path)).encode()
        files_list = []
        for root, dirs, files in os.walk(path):
            for f in files:
                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, path)
                path_parts = [p.encode() for p in rel_path.split(os.sep)]
                files_list.append({b"length": os.path.getsize(full_path), b"path": path_parts})
        torrent_dict[b"info"][b"files"] = files_list

        pieces = b""
        buffer = b""
        for file_entry in files_list:
            file_path = os.path.join(path, *[p.decode() for p in file_entry[b"path"]])
            with open(file_path, "rb") as f:
                while True:
                    read_data = f.read(piece_size - len(buffer))
                    if not read_data:
                        break
                    buffer += read_data
                    while len(buffer) >= piece_size:
                        pieces += hashlib.sha1(buffer[:piece_size]).digest()
                        buffer = buffer[piece_size:]
        if buffer:
            pieces += hashlib.sha1(buffer).digest()
        torrent_dict[b"info"][b"pieces"] = pieces

    # Write torrent file
    with open(output_file, "wb") as f:
        f.write(bencodepy.encode(torrent_dict))

    print(f"✅ Torrent created: {output_file}")
    print(f"Piece size: {piece_size} bytes")
    if private:
        print("🔒 Torrent marked as PRIVATE")

def main():
    parser = argparse.ArgumentParser(description="Create a .torrent file")
    parser.add_argument("--announce", required=True, help="Tracker announce URL")
    parser.add_argument("path", help="Path to file or folder")
    parser.add_argument("--output", required=True, help="Output .torrent file path")
    parser.add_argument("-P", "--private", action="store_true", help="Mark torrent as private")
    args = parser.parse_args()

    create_torrent(args.path, args.announce, args.output, private=args.private)

if __name__ == "__main__":
    main()
