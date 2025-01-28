import yt_dlp
import os
import sys

# Folder where videos & subtitles will be saved
OUTPUT_FOLDER = "TikTok_Downloads"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def download_videos(urls):
    """Downloads TikTok videos along with subtitles using yt-dlp."""
    ydl_opts = {
        'outtmpl': f'{OUTPUT_FOLDER}/%(uploader)s - %(title)s.%(ext)s',  # Filename format
        'format': 'mp4',  # Best video quality
        'quiet': False,  # Show progress
        'noplaylist': True,  # Download single videos
        'postprocessors': [{'key': 'FFmpegVideoConvertor', 'preferedformat': 'mp4'}],
        
        # Subtitle options
        'writesubtitles': True,         # Download subtitles
        'subtitleslangs': ['en'],       # English subtitles (modify for other languages)
        'subtitlesformat': 'srt',       # Save subtitles as .srt
        'outtmpl_subtitles': f'{OUTPUT_FOLDER}/%(uploader)s - %(title)s.%(ext)s'  # Keep subs next to video
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for url in urls:
            try:
                print(f"📥 Downloading: {url}")
                ydl.download([url])
            except Exception as e:
                print(f"❌ Error downloading {url}: {e}")

def get_urls_from_txt(file_path):
    """Reads URLs from a text file."""
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return [line.strip() for line in file if line.strip()]
    except Exception as e:
        print(f"⚠️ Error reading file: {e}")
        return []

def main():
    urls = []

    # Check if script was called with arguments
    if len(sys.argv) > 1:
        arg = sys.argv[1]

        # If argument is a text file, read URLs from it
        if os.path.isfile(arg) and arg.endswith(".txt"):
            print(f"📂 Reading URLs from file: {arg}")
            urls = get_urls_from_txt(arg)

        # If argument is a single URL, use it
        elif arg.startswith("http"):
            urls = sys.argv[1:]

    # If no arguments, ask for input
    if not urls:
        print("\n✏️  Enter TikTok URLs (one per line). Press ENTER twice to finish:\n")
        while True:
            url = input().strip()
            if not url:
                break
            urls.append(url)

    # Download videos and subtitles
    if urls:
        download_videos(urls)
    else:
        print("⚠️ No valid URLs provided!")

if __name__ == "__main__":
    main()
