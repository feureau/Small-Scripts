#!/usr/bin/env python3

r"""
# Hybrid Downloader & Extractor: A Robust Parallel Tool for Media and Text

A powerful, multi-purpose wrapper for 'yt-dlp' and 'gallery-dl'. This script operates
in one of two modes: Download or Text Extraction. It can also update its own dependencies.

1.  **Download Mode (Default):** Intelligently detects if a URL is video or an image
    gallery and uses the appropriate tool to download the media files in parallel.
    This mode now automatically detects if an input is a text file and treats it as a
    batch file of URLs. By default, it also saves the full, raw metadata to a .json file.
2.  **Text Extraction Mode (`--extract-text`):** Extracts and saves the clean text
    (descriptions, captions, tweets) associated with a URL to a `.txt` file.
3.  **Update Mode (`--update`):** Updates `yt-dlp` and `gallery-dl` to their latest
    versions to ensure all website extractors are current.

This script is highly optimized for performance, using a "Streaming Worker" model where
each URL is processed from start to finish in a single parallel task. Any URLs that
fail during processing are logged to a specified error file for easy retries.

---
## Developer and Maintenance Note

**Directive for Future Iterations:** For every modification or iteration of this script, the full, unabridged, and most up-to-date help documentation for both `yt-dlp` and `gallery-dl` MUST be included directly within this docstring.

**Reasoning:** The primary goal is to maintain this script as a completely self-contained and portable tool. A user must be able to understand the full capabilities of the script and its underlying dependencies (`yt-dlp`, `gallery-dl`) simply by reading its source code. This eliminates the need for external `... --help` commands, making the script's functionality transparent and accessible in any environment, even offline.

**Version History:**
- **v1.0 (Initial):** Base script provided by the user.
- **v2.0 (Batch Processing):** Added `--batch-file` (`-a`).
- **v3.0 (gallery-dl Integration):** Integrated `gallery-dl` as a fallback.
- **v4.0 (Exposed gallery-dl Options):** Added specific flags like `--g-directory`.
- **v5.0 (Full Documentation):** Re-integrated the complete help texts.
- **v6.0 (Text Extraction Mode):** Added the `--extract-text` (`-E`) flag.
- **v7.0 (Single-Letter Aliases):** Added a unique alias for every flag.
- **v8.0 (Parallel Discovery):** Re-architected into a two-phase parallel model.
- **v8.1 (Default Text Save):** Default download now also saves metadata.
- **v9.0 (Error Logging):** Added `--output-errors` (`-oE`).
- **v10.0 (Self-Updating):** Added the `--update` (`-U`) flag.
- **v11.0 (Streaming Worker Architecture):** Re-architected to a "Streaming Worker" model for higher throughput and implemented an enhanced two-file logging system.
- **v12.0 (Intuitive CLI):** Re-assigned `-a` to audio and implemented automatic batch file detection.

---
## Usage

**To Update Dependencies:**
    python3 downloader.py -U

**To Download Media Files (and Text Metadata) from a single URL:**
    python3 downloader.py <URL> [OPTIONS]

**To Download Audio from a single URL:**
    python3 downloader.py -a <URL>

**To Batch Download from a file:**
    python3 downloader.py my_urls.txt

**To Extract Only Clean Text:**
    python3 downloader.py <URL> -E

### URL Input (Required unless updating)
    INPUT...                One or more URLs or file paths. The script automatically
                            detects if an input is a file and reads URLs from it.

### General Options
| Flag | Short | Description |
| :--- | :--- | :--- |
| `--update`      | `-U` | **Switches to Update Mode.** Updates dependencies and exits. |
| `--extract-text`| `-E` | **Switches to Text Extraction Mode.** Extracts only the clean text to a `.txt` file. |
| `--log` / `--log-file` | `-L` | Enable verbose, timestamped logging (default: disabled; logs to `processing_log.txt` or a specified file). |
| `--output-errors`| `-oE` | File to save the clean list of URLs that failed (default: `errors.txt`). |
| `--verbose` | `-V` | Debug Mode: Prints all output from the underlying process. |

### yt-dlp Options (for video content in Download Mode)
| Flag | Short | Description |
| :--- | :--- | :--- |
| `--video` | `-v` | Download video (best quality MP4 + metadata, desc, comments). |
| `--audio-only`| `-a` | Download audio-only (best quality, MP3). |
| `--srt` | `-s` | Download subtitles (SRT format). |
| `--thumbnail` | `-t` | Download video thumbnail image. |
| `--metadata` | `-m` | Download video metadata to a `.json` file (default). |
| `--description` | `-d` | Download video description to a `.description` file (default). |
| `--comments`    | `-C` | Download video comments into the metadata file (default). |
| `--language`| `-l` | Language code for audio/subs (e.g., 'id', 'es'). |
| `--combine-transcripts`| `-c` | Combine all downloaded transcripts into a single `.md` file. |

### gallery-dl Options (for image content in Download Mode)
| Flag | Short | Description |
| :--- | :--- | :--- |
| `--g-directory`| `-gD` | Output directory for downloaded images. |
| `--g-archive`| `-gA` | Record downloads in an archive file to skip them later. |
| `--g-no-skip` | `-gN` | Do not skip downloads; re-download everything. |
| `--g-write-metadata`| `-gM` | Write metadata to a separate `.json` file for each post (this is now the default behavior). |
| `--g-options` | `-gO` | Raw string of additional options to pass to gallery-dl (e.g., "--zip"). |

---
## Full yt-dlp Help Reference

Usage: yt-dlp [OPTIONS] URL [URL...]

Options:
  General Options:
    -h, --help                                        Print this help text and exit
    --version                                         Print program version and exit
    -U, --update                                      Check if updates are available. You installed yt-dlp with pip or
                                                      using the wheel from PyPi; Use that to update
    --no-update                                       Do not check for updates (default)
    --update-to [CHANNEL]@[TAG]                       Upgrade/downgrade to a specific version. CHANNEL can be a
                                                      repository as well. CHANNEL and TAG default to "stable" and
                                                      "latest" respectively if omitted; See "UPDATE" for details.
                                                      Supported channels: stable, nightly, master
    -i, --ignore-errors                               Ignore download and postprocessing errors. The download will be
                                                      considered successful even if the postprocessing fails
    --no-abort-on-error                               Continue with next video on download errors; e.g. to skip
                                                      unavailable videos in a playlist (default)
    --abort-on-error                                  Abort downloading of further videos if an error occurs (Alias:
                                                      --no-ignore-errors)
    --dump-user-agent                                 Display the current user-agent and exit
    --list-extractors                                 List all supported extractors and exit
    --extractor-descriptions                          Output descriptions of all supported extractors and exit
    --use-extractors NAMES                            Extractor names to use separated by commas. You can also use
                                                      regexes, "all", "default" and "end" (end URL matching); e.g. --ies
                                                      "holodex.*,end,youtube". Prefix the name with a "-" to exclude it,
                                                      e.g. --ies default,-generic. Use --list-extractors for a list of
                                                      extractor names. (Alias: --ies)
    --default-search PREFIX                           Use this prefix for unqualified URLs. E.g. "gvsearch2:python"
                                                      downloads two videos from google videos for the search term
                                                      "python". Use the value "auto" to let yt-dlp guess ("auto_warning"
                                                      to emit a warning when guessing). "error" just throws an error.
                                                      The default value "fixup_error" repairs broken URLs, but emits an
                                                      error if this is not possible instead of searching
    --ignore-config                                   Don't load any more configuration files except those given to
                                                      --config-locations. For backward compatibility, if this option is
                                                      found inside the system configuration file, the user configuration
                                                      is not loaded. (Alias: --no-config)
    --no-config-locations                             Do not load any custom configuration files (default). When given
                                                      inside a configuration file, ignore all previous --config-
                                                      locations defined in the current file
    --config-locations PATH                           Location of the main configuration file; either the path to the
                                                      config or its containing directory ("-" for stdin). Can be used
                                                      multiple times and inside other configuration files
    --plugin-dirs PATH                                Path to an additional directory to search for plugins. This option
                                                      can be used multiple times to add multiple directories. Use
                                                      "default" to search the default plugin directories (default)
    --no-plugin-dirs                                  Clear plugin directories to search, including defaults and those
                                                      provided by previous --plugin-dirs
    --flat-playlist                                   Do not extract a playlist's URL result entries; some entry
                                                      metadata may be missing and downloading may be bypassed
    --no-flat-playlist                                Fully extract the videos of a playlist (default)
    --live-from-start                                 Download livestreams from the start. Currently experimental and
                                                      only supported for YouTube and Twitch
    --no-live-from-start                              Download livestreams from the current time (default)
    --wait-for-video MIN[-MAX]                        Wait for scheduled streams to become available. Pass the minimum
                                                      number of seconds (or range) to wait between retries
    --no-wait-for-video                               Do not wait for scheduled streams (default)
    --mark-watched                                    Mark videos watched (even with --simulate)
    --no-mark-watched                                 Do not mark videos watched (default)
    --color [STREAM:]POLICY                           Whether to emit color codes in output, optionally prefixed by the
                                                      STREAM (stdout or stderr) to apply the setting to. Can be one of
                                                      "always", "auto" (default), "never", or "no_color" (use non color
                                                      terminal sequences). Use "auto-tty" or "no_color-tty" to decide
                                                      based on terminal support only. Can be used multiple times
    --compat-options OPTS                             Options that can help keep compatibility with youtube-dl or
                                                      youtube-dlc configurations by reverting some of the changes made
                                                      in yt-dlp. See "Differences in default behavior" for details
    --alias ALIASES OPTIONS                           Create aliases for an option string. Unless an alias starts with a
                                                      dash "-", it is prefixed with "--". Arguments are parsed according
                                                      to the Python string formatting mini-language. E.g. --alias get-
                                                      audio,-X "-S aext:{0},abr -x --audio-format {0}" creates options "
                                                      --get-audio" and "-X" that takes an argument (ARG0) and expands to
                                                      "-S aext:ARG0,abr -x --audio-format ARG0". All defined aliases are
                                                      listed in the --help output. Alias options can trigger more
                                                      aliases; so be careful to avoid defining recursive options. As a
                                                      safety measure, each alias may be triggered a maximum of 100
                                                      times. This option can be used multiple times
    -t, --preset-alias PRESET                         Applies a predefined set of options. e.g. --preset-alias mp3. The
                                                      following presets are available: mp3, aac, mp4, mkv, sleep. See
                                                      the "Preset Aliases" section at the end for more info. This option
                                                      can be used multiple times

  Network Options:
    --proxy URL                                       Use the specified HTTP/HTTPS/SOCKS proxy. To enable SOCKS proxy,
                                                      specify a proper scheme, e.g. socks5://user:pass@127.0.0.1:1080/.
                                                      Pass in an empty string (--proxy "") for direct connection
    --socket-timeout SECONDS                          Time to wait before giving up, in seconds
    --source-address IP                               Client-side IP address to bind to
    --impersonate CLIENT[:OS]                         Client to impersonate for requests. E.g. chrome, chrome-110,
                                                      chrome:windows-10. Pass --impersonate="" to impersonate any
                                                      client. Note that forcing impersonation for all requests may have
                                                      a detrimental impact on download speed and stability
    --list-impersonate-targets                        List available clients to impersonate.
    -4, --force-ipv4                                  Make all connections via IPv4
    -6, --force-ipv6                                  Make all connections via IPv6
    --enable-file-urls                                Enable file:// URLs. This is disabled by default for security
                                                      reasons.

  Geo-restriction:
    --geo-verification-proxy URL                      Use this proxy to verify the IP address for some geo-restricted
                                                      sites. The default proxy specified by --proxy (or none, if the
                                                      option is not present) is used for the actual downloading
    --xff VALUE                                       How to fake X-Forwarded-For HTTP header to try bypassing
                                                      geographic restriction. One of "default" (only when known to be
                                                      useful), "never", an IP block in CIDR notation, or a two-letter
                                                      ISO 3166-2 country code

  Video Selection:
    -I, --playlist-items ITEM_SPEC                    Comma separated playlist_index of the items to download. You can
                                                      specify a range using "[START]:[STOP][:STEP]". For backward
                                                      compatibility, START-STOP is also supported. Use negative indices
                                                      to count from the right and negative STEP to download in reverse
                                                      order. E.g. "-I 1:3,7,-5::2" used on a playlist of size 15 will
                                                      download the items at index 1,2,3,7,11,13,15
    --min-filesize SIZE                               Abort download if filesize is smaller than SIZE, e.g. 50k or 44.6M
    --max-filesize SIZE                               Abort download if filesize is larger than SIZE, e.g. 50k or 44.6M
    --date DATE                                       Download only videos uploaded on this date. The date can be
                                                      "YYYYMMDD" or in the format
                                                      [now|today|yesterday][-N[day|week|month|year]]. E.g. "--date
                                                      today-2weeks" downloads only videos uploaded on the same day two
                                                      weeks ago
    --datebefore DATE                                 Download only videos uploaded on or before this date. The date
                                                      formats accepted are the same as --date
    --dateafter DATE                                  Download only videos uploaded on or after this date. The date
                                                      formats accepted are the same as --date
    --match-filters FILTER                            Generic video filter. Any "OUTPUT TEMPLATE" field can be compared
                                                      with a number or a string using the operators defined in
                                                      "Filtering Formats". You can also simply specify a field to match
                                                      if the field is present, use "!field" to check if the field is not
                                                      present, and "&" to check multiple conditions. Use a "\" to escape
                                                      "&" or quotes if needed. If used multiple times, the filter
                                                      matches if at least one of the conditions is met. E.g. --match-
                                                      filters !is_live --match-filters "like_count>?100 &
                                                      description~='(?i)\bcats \& dogs\b'" matches only videos that are
                                                      not live OR those that have a like count more than 100 (or the
                                                      like field is not available) and also has a description that
                                                      contains the phrase "cats & dogs" (caseless). Use "--match-filters
                                                      -" to interactively ask whether to download each video
    --no-match-filters                                Do not use any --match-filters (default)
    --break-match-filters FILTER                      Same as "--match-filters" but stops the download process when a
                                                      video is rejected
    --no-break-match-filters                          Do not use any --break-match-filters (default)
    --no-playlist                                     Download only the video, if the URL refers to a video and a
                                                      playlist
    --yes-playlist                                    Download the playlist, if the URL refers to a video and a playlist
    --age-limit YEARS                                 Download only videos suitable for the given age
    --download-archive FILE                           Download only videos not listed in the archive file. Record the
                                                      IDs of all downloaded videos in it
    --no-download-archive                             Do not use archive file (default)
    --max-downloads NUMBER                            Abort after downloading NUMBER files
    --break-on-existing                               Stop the download process when encountering a file that is in the
                                                      archive supplied with the --download-archive option
    --no-break-on-existing                            Do not stop the download process when encountering a file that is
                                                      in the archive (default)
    --break-per-input                                 Alters --max-downloads, --break-on-existing, --break-match-
                                                      filters, and autonumber to reset per input URL
    --no-break-per-input                              --break-on-existing and similar options terminates the entire
                                                      download queue
    --skip-playlist-after-errors N                    Number of allowed failures until the rest of the playlist is
                                                      skipped

  Download Options:
    -N, --concurrent-fragments N                      Number of fragments of a dash/hlsnative video that should be
                                                      downloaded concurrently (default is 1)
    -r, --limit-rate RATE                             Maximum download rate in bytes per second, e.g. 50K or 4.2M
    --throttled-rate RATE                             Minimum download rate in bytes per second below which throttling
                                                      is assumed and the video data is re-extracted, e.g. 100K
    -R, --retries RETRIES                             Number of retries (default is 10), or "infinite"
    --file-access-retries RETRIES                     Number of times to retry on file access error (default is 3), or
                                                      "infinite"
    --fragment-retries RETRIES                        Number of retries for a fragment (default is 10), or "infinite"
                                                      (DASH, hlsnative and ISM)
    --retry-sleep [TYPE:]EXPR                         Time to sleep between retries in seconds (optionally) prefixed by
                                                      the type of retry (http (default), fragment, file_access,
                                                      extractor) to apply the sleep to. EXPR can be a number,
                                                      linear=START[:END[:STEP=1]] or exp=START[:END[:BASE=2]]. This
                                                      option can be used multiple times to set the sleep for the
                                                      different retry types, e.g. --retry-sleep linear=1::2 --retry-
                                                      sleep fragment:exp=1:20
    --skip-unavailable-fragments                      Skip unavailable fragments for DASH, hlsnative and ISM downloads
                                                      (default) (Alias: --no-abort-on-unavailable-fragments)
    --abort-on-unavailable-fragments                  Abort download if a fragment is unavailable (Alias: --no-skip-
                                                      unavailable-fragments)
    --keep-fragments                                  Keep downloaded fragments on disk after downloading is finished
    --no-keep-fragments                               Delete downloaded fragments after downloading is finished
                                                      (default)
    --buffer-size SIZE                                Size of download buffer, e.g. 1024 or 16K (default is 1024)
    --resize-buffer                                   The buffer size is automatically resized from an initial value of
                                                      --buffer-size (default)
    --no-resize-buffer                                Do not automatically adjust the buffer size
    --http-chunk-size SIZE                            Size of a chunk for chunk-based HTTP downloading, e.g. 10485760 or
                                                      10M (default is disabled). May be useful for bypassing bandwidth
                                                      throttling imposed by a webserver (experimental)
    --playlist-random                                 Download playlist videos in random order
    --lazy-playlist                                   Process entries in the playlist as they are received. This
                                                      disables n_entries, --playlist-random and --playlist-reverse
    --no-lazy-playlist                                Process videos in the playlist only after the entire playlist is
                                                      parsed (default)
    --xattr-set-filesize                              Set file xattribute ytdl.filesize with expected file size
    --hls-use-mpegts                                  Use the mpegts container for HLS videos; allowing some players to
                                                      play the video while downloading, and reducing the chance of file
                                                      corruption if download is interrupted. This is enabled by default
                                                      for live streams
    --no-hls-use-mpegts                               Do not use the mpegts container for HLS videos. This is default
                                                      when not downloading live streams
    --download-sections REGEX                         Download only chapters that match the regular expression. A "*"
                                                      prefix denotes time-range instead of chapter. Negative timestamps
                                                      are calculated from the end. "*from-url" can be used to download
                                                      between the "start_time" and "end_time" extracted from the URL.
                                                      Needs ffmpeg. This option can be used multiple times to download
                                                      multiple sections, e.g. --download-sections "*10:15-inf"
                                                      --download-sections "intro"
    --downloader [PROTO:]NAME                         Name or path of the external downloader to use (optionally)
                                                      prefixed by the protocols (http, ftp, m3u8, dash, rstp, rtmp, mms)
                                                      to use it for. Currently supports native, aria2c, avconv, axel,
                                                      curl, ffmpeg, httpie, wget. You can use this option multiple times
                                                      to set different downloaders for different protocols. E.g.
                                                      --downloader aria2c --downloader "dash,m3u8:native" will use
                                                      aria2c for http/ftp downloads, and the native downloader for
                                                      dash/m3u8 downloads (Alias: --external-downloader)
    --downloader-args NAME:ARGS                       Give these arguments to the external downloader. Specify the
                                                      downloader name and the arguments separated by a colon ":". For
                                                      ffmpeg, arguments can be passed to different positions using the
                                                      same syntax as --postprocessor-args. You can use this option
                                                      multiple times to give different arguments to different
                                                      downloaders (Alias: --external-downloader-args)

  Filesystem Options:
    -a, --batch-file FILE                             File containing URLs to download ("-" for stdin), one URL per
                                                      line. Lines starting with "#", ";" or "]" are considered as
                                                      comments and ignored
    --no-batch-file                                   Do not read URLs from batch file (default)
    -P, --paths [TYPES:]PATH                          The paths where the files should be downloaded. Specify the type
                                                      of file and the path separated by a colon ":". All the same TYPES
                                                      as --output are supported. Additionally, you can also provide
                                                      "home" (default) and "temp" paths. All intermediary files are
                                                      first downloaded to the temp path and then the final files are
                                                      moved over to the home path after download is finished. This
                                                      option is ignored if --output is an absolute path
    -o, --output [TYPES:]TEMPLATE                     Output filename template; see "OUTPUT TEMPLATE" for details
    --output-na-placeholder TEXT                      Placeholder for unavailable fields in --output (default: "NA")
    --restrict-filenames                              Restrict filenames to only ASCII characters, and avoid "&" and
                                                      spaces in filenames
    --no-restrict-filenames                           Allow Unicode characters, "&" and spaces in filenames (default)
    --windows-filenames                               Force filenames to be Windows-compatible
    --no-windows-filenames                            Sanitize filenames only minimally
    --trim-filenames LENGTH                           Limit the filename length (excluding extension) to the specified
                                                      number of characters
    -w, --no-overwrites                               Do not overwrite any files
    --force-overwrites                                Overwrite all video and metadata files. This option includes --no-
                                                      continue
    --no-force-overwrites                             Do not overwrite the video, but overwrite related files (default)
    -c, --continue                                    Resume partially downloaded files/fragments (default)
    --no-continue                                     Do not resume partially downloaded fragments. If the file is not
                                                      fragmented, restart download of the entire file
    --part                                            Use .part files instead of writing directly into output file
                                                      (default)
    --no-part                                         Do not use .part files - write directly into output file
    --mtime                                           Use the Last-modified header to set the file modification time
    --no-mtime                                        Do not use the Last-modified header to set the file modification
                                                      time (default)
    --write-description                               Write video description to a .description file
    --no-write-description                            Do not write video description (default)
    --write-info-json                                 Write video metadata to a .info.json file (this may contain
                                                      personal information)
    --no-write-info-json                              Do not write video metadata (default)
    --write-playlist-metafiles                        Write playlist metadata in addition to the video metadata when
                                                      using --write-info-json, --write-description etc. (default)
    --no-write-playlist-metafiles                     Do not write playlist metadata when using --write-info-json,
                                                      --write-description etc.
    --clean-info-json                                 Remove some internal metadata such as filenames from the infojson
                                                      (default)
    --no-clean-info-json                              Write all fields to the infojson
    --write-comments                                  Retrieve video comments to be placed in the infojson. The comments
                                                      are fetched even without this option if the extraction is known to
                                                      be quick (Alias: --get-comments)
    --no-write-comments                               Do not retrieve video comments unless the extraction is known to
                                                      be quick (Alias: --no-get-comments)
    --load-info-json FILE                             JSON file containing the video information (created with the "--
                                                      write-info-json" option)
    --cookies FILE                                    Netscape formatted file to read cookies from and dump cookie jar
                                                      in
    --no-cookies                                      Do not read/dump cookies from/to file (default)
    --cookies-from-browser BROWSER[+KEYRING][:PROFILE][::CONTAINER]
                                                      The name of the browser to load cookies from. Currently supported
                                                      browsers are: brave, chrome, chromium, edge, firefox, opera,
                                                      safari, vivaldi, whale. Optionally, the KEYRING used for
                                                      decrypting Chromium cookies on Linux, the name/path of the PROFILE
                                                      to load cookies from, and the CONTAINER name (if Firefox) ("none"
                                                      for no container) can be given with their respective separators.
                                                      By default, all containers of the most recently accessed profile
                                                      are used. Currently supported keyrings are: basictext,
                                                      gnomekeyring, kwallet, kwallet5, kwallet6
    --no-cookies-from-browser                         Do not load cookies from browser (default)
    --cache-dir DIR                                   Location in the filesystem where yt-dlp can store some downloaded
                                                      information (such as client ids and signatures) permanently. By
                                                      default ${XDG_CACHE_HOME}/yt-dlp
    --no-cache-dir                                    Disable filesystem caching
    --rm-cache-dir                                    Delete all filesystem cache files

  Thumbnail Options:
    --write-thumbnail                                 Write thumbnail image to disk
    --no-write-thumbnail                              Do not write thumbnail image to disk (default)
    --write-all-thumbnails                            Write all thumbnail image formats to disk
    --list-thumbnails                                 List available thumbnails of each video. Simulate unless --no-
                                                      simulate is used

  Internet Shortcut Options:
    --write-link                                      Write an internet shortcut file, depending on the current platform
                                                      (.url, .webloc or .desktop). The URL may be cached by the OS
    --write-url-link                                  Write a .url Windows internet shortcut. The OS caches the URL
                                                      based on the file path
    --write-webloc-link                               Write a .webloc macOS internet shortcut
    --write-desktop-link                              Write a .desktop Linux internet shortcut

  Verbosity and Simulation Options:
    -q, --quiet                                       Activate quiet mode. If used with --verbose, print the log to
                                                      stderr
    --no-quiet                                        Deactivate quiet mode. (Default)
    --no-warnings                                     Ignore warnings
    -s, --simulate                                    Do not download the video and do not write anything to disk
    --no-simulate                                     Download the video even if printing/listing options are used
    --ignore-no-formats-error                         Ignore "No video formats" error. Useful for extracting metadata
                                                      even if the videos are not actually available for download
                                                      (experimental)
    --no-ignore-no-formats-error                      Throw error when no downloadable video formats are found (default)
    --skip-download                                   Do not download the video but write all related files (Alias:
                                                      --no-download)
    -O, --print [WHEN:]TEMPLATE                       Field name or output template to print to screen, optionally
                                                      prefixed with when to print it, separated by a ":". Supported
                                                      values of "WHEN" are the same as that of --use-postprocessor
                                                      (default: video). Implies --quiet. Implies --simulate unless --no-
                                                      simulate or later stages of WHEN are used. This option can be used
                                                      multiple times
    --print-to-file [WHEN:]TEMPLATE FILE              Append given template to the file. The values of WHEN and TEMPLATE
                                                      are the same as that of --print. FILE uses the same syntax as the
                                                      output template. This option can be used multiple times
    -j, --dump-json                                   Quiet, but print JSON information for each video. Simulate unless
                                                      --no-simulate is used. See "OUTPUT TEMPLATE" for a description of
                                                      available keys
    -J, --dump-single-json                            Quiet, but print JSON information for each URL or infojson passed.
                                                      Simulate unless --no-simulate is used. If the URL refers to a
                                                      playlist, the whole playlist information is dumped in a single
                                                      line
    --force-write-archive                             Force download archive entries to be written as far as no errors
                                                      occur, even if -s or another simulation option is used (Alias:
                                                      --force-download-archive)
    --newline                                         Output progress bar as new lines
    --no-progress                                     Do not print progress bar
    --progress                                        Show progress bar, even if in quiet mode
    --console-title                                   Display progress in console titlebar
    --progress-template [TYPES:]TEMPLATE              Template for progress outputs, optionally prefixed with one of
                                                      "download:" (default), "download-title:" (the console title),
                                                      "postprocess:",  or "postprocess-title:". The video's fields are
                                                      accessible under the "info" key and the progress attributes are
                                                      accessible under "progress" key. E.g. --console-title --progress-
                                                      template "download-title:%(info.id)s-%(progress.eta)s"
    --progress-delta SECONDS                          Time between progress output (default: 0)
    -v, --verbose                                     Print various debugging information
    --dump-pages                                      Print downloaded pages encoded using base64 to debug problems
                                                      (very verbose)
    --write-pages                                     Write downloaded intermediary pages to files in the current
                                                      directory to debug problems
    --print-traffic                                   Display sent and read HTTP traffic

  Workarounds:
    --encoding ENCODING                               Force the specified encoding (experimental)
    --legacy-server-connect                           Explicitly allow HTTPS connection to servers that do not support
                                                      RFC 5746 secure renegotiation
    --no-check-certificates                           Suppress HTTPS certificate validation
    --prefer-insecure                                 Use an unencrypted connection to retrieve information about the
                                                      video (Currently supported only for YouTube)
    --add-headers FIELD:VALUE                         Specify a custom HTTP header and its value, separated by a colon
                                                      ":". You can use this option multiple times
    --bidi-workaround                                 Work around terminals that lack bidirectional text support.
                                                      Requires bidiv or fribidi executable in PATH
    --sleep-requests SECONDS                          Number of seconds to sleep between requests during data extraction
    --sleep-interval SECONDS                          Number of seconds to sleep before each download. This is the
                                                      minimum time to sleep when used along with --max-sleep-interval
                                                      (Alias: --min-sleep-interval)
    --max-sleep-interval SECONDS                      Maximum number of seconds to sleep. Can only be used along with
                                                      --min-sleep-interval
    --sleep-subtitles SECONDS                         Number of seconds to sleep before each subtitle download

  Video Format Options:
    -f, --format FORMAT                               Video format code, see "FORMAT SELECTION" for more details
    -S, --format-sort SORTORDER                       Sort the formats by the fields given, see "Sorting Formats" for
                                                      more details
    --format-sort-force                               Force user specified sort order to have precedence over all
                                                      fields, see "Sorting Formats" for more details (Alias: --S-force)
    --no-format-sort-force                            Some fields have precedence over the user specified sort order
                                                      (default)
    --video-multistreams                              Allow multiple video streams to be merged into a single file
    --no-video-multistreams                           Only one video stream is downloaded for each output file (default)
    --audio-multistreams                              Allow multiple audio streams to be merged into a single file
    --no-audio-multistreams                           Only one audio stream is downloaded for each output file (default)
    --prefer-free-formats                             Prefer video formats with free containers over non-free ones of
                                                      the same quality. Use with "-S ext" to strictly prefer free
                                                      containers irrespective of quality
    --no-prefer-free-formats                          Don't give any special preference to free containers (default)
    --check-formats                                   Make sure formats are selected only from those that are actually
                                                      downloadable
    --check-all-formats                               Check all formats for whether they are actually downloadable
    --no-check-formats                                Do not check that the formats are actually downloadable
    -F, --list-formats                                List available formats of each video. Simulate unless --no-
                                                      simulate is used
    --merge-output-format FORMAT                      Containers that may be used when merging formats, separated by
                                                      "/", e.g. "mp4/mkv". Ignored if no merge is required. (currently
                                                      supported: avi, flv, mkv, mov, mp4, webm)

  Subtitle Options:
    --write-subs                                      Write subtitle file
    --no-write-subs                                   Do not write subtitle file (default)
    --write-auto-subs                                 Write automatically generated subtitle file (Alias: --write-
                                                      automatic-subs)
    --no-write-auto-subs                              Do not write auto-generated subtitles (default) (Alias: --no-
                                                      write-automatic-subs)
    --list-subs                                       List available subtitles of each video. Simulate unless --no-
                                                      simulate is used
    --sub-format FORMAT                               Subtitle format; accepts formats preference separated by "/", e.g.
                                                      "srt" or "ass/srt/best"
    --sub-langs LANGS                                 Languages of the subtitles to download (can be regex) or "all"
                                                      separated by commas, e.g. --sub-langs "en.*,ja" (where "en.*" is a
                                                      regex pattern that matches "en" followed by 0 or more of any
                                                      character). You can prefix the language code with a "-" to exclude
                                                      it from the requested languages, e.g. --sub-langs all,-live_chat.
                                                      Use --list-subs for a list of available language tags

  Authentication Options:
    -u, --username USERNAME                           Login with this account ID
    -p, --password PASSWORD                           Account password. If this option is left out, yt-dlp will ask
                                                      interactively
    -2, --twofactor TWOFACTOR                         Two-factor authentication code
    -n, --netrc                                       Use .netrc authentication data
    --netrc-location PATH                             Location of .netrc authentication data; either the path or its
                                                      containing directory. Defaults to ~/.netrc
    --netrc-cmd NETRC_CMD                             Command to execute to get the credentials for an extractor.
    --video-password PASSWORD                         Video-specific password
    --ap-mso MSO                                      Adobe Pass multiple-system operator (TV provider) identifier, use
                                                      --ap-list-mso for a list of available MSOs
    --ap-username USERNAME                            Multiple-system operator account login
    --ap-password PASSWORD                            Multiple-system operator account password. If this option is left
                                                      out, yt-dlp will ask interactively
    --ap-list-mso                                     List all supported multiple-system operators
    --client-certificate CERTFILE                     Path to client certificate file in PEM format. May include the
                                                      private key
    --client-certificate-key KEYFILE                  Path to private key file for client certificate
    --client-certificate-password PASSWORD            Password for client certificate private key, if encrypted. If not
                                                      provided, and the key is encrypted, yt-dlp will ask interactively

  Post-Processing Options:
    -x, --extract-audio                               Convert video files to audio-only files (requires ffmpeg and
                                                      ffprobe)
    --audio-format FORMAT                             Format to convert the audio to when -x is used. (currently
                                                      supported: best (default), aac, alac, flac, m4a, mp3, opus,
                                                      vorbis, wav). You can specify multiple rules using similar syntax
                                                      as --remux-video
    --audio-quality QUALITY                           Specify ffmpeg audio quality to use when converting the audio with
                                                      -x. Insert a value between 0 (best) and 10 (worst) for VBR or a
                                                      specific bitrate like 128K (default 5)
    --remux-video FORMAT                              Remux the video into another container if necessary (currently
                                                      supported: avi, flv, gif, mkv, mov, mp4, webm, aac, aiff, alac,
                                                      flac, m4a, mka, mp3, ogg, opus, vorbis, wav). If the target
                                                      container does not support the video/audio codec, remuxing will
                                                      fail. You can specify multiple rules; e.g. "aac>m4a/mov>mp4/mkv"
                                                      will remux aac to m4a, mov to mp4 and anything else to mkv
    --recode-video FORMAT                             Re-encode the video into another format if necessary. The syntax
                                                      and supported formats are the same as --remux-video
    --postprocessor-args NAME:ARGS                    Give these arguments to the postprocessors. Specify the
                                                      postprocessor/executable name and the arguments separated by a
                                                      colon ":" to give the argument to the specified
                                                      postprocessor/executable. Supported PP are: Merger,
                                                      ModifyChapters, SplitChapters, ExtractAudio, VideoRemuxer,
                                                      VideoConvertor, Metadata, EmbedSubtitle, EmbedThumbnail,
                                                      SubtitlesConvertor, ThumbnailsConvertor, FixupStretched, FixupM4a,
                                                      FixupM3u8, FixupTimestamp and FixupDuration. The supported
                                                      executables are: AtomicParsley, FFmpeg and FFprobe. You can also
                                                      specify "PP+EXE:ARGS" to give the arguments to the specified
                                                      executable only when being used by the specified postprocessor.
                                                      Additionally, for ffmpeg/ffprobe, "_i"/"_o" can be appended to the
                                                      prefix optionally followed by a number to pass the argument before
                                                      the specified input/output file, e.g. --ppa "Merger+ffmpeg_i1:-v
                                                      quiet". You can use this option multiple times to give different
                                                      arguments to different postprocessors. (Alias: --ppa)
    -k, --keep-video                                  Keep the intermediate video file on disk after post-processing
    --no-keep-video                                   Delete the intermediate video file after post-processing (default)
    --post-overwrites                                 Overwrite post-processed files (default)
    --no-post-overwrites                              Do not overwrite post-processed files
    --embed-subs                                      Embed subtitles in the video (only for mp4, webm and mkv videos)
    --no-embed-subs                                   Do not embed subtitles (default)
    --embed-thumbnail                                 Embed thumbnail in the video as cover art
    --no-embed-thumbnail                              Do not embed thumbnail (default)
    --embed-metadata                                  Embed metadata to the video file. Also embeds chapters/infojson if
                                                      present unless --no-embed-chapters/--no-embed-info-json are used
                                                      (Alias: --add-metadata)
    --no-embed-metadata                               Do not add metadata to file (default) (Alias: --no-add-metadata)
    --embed-chapters                                  Add chapter markers to the video file (Alias: --add-chapters)
    --no-embed-chapters                               Do not add chapter markers (default) (Alias: --no-add-chapters)
    --embed-info-json                                 Embed the infojson as an attachment to mkv/mka video files
    --no-embed-info-json                              Do not embed the infojson as an attachment to the video file
    --parse-metadata [WHEN:]FROM:TO                   Parse additional metadata like title/artist from other fields; see
                                                      "MODIFYING METADATA" for details. Supported values of "WHEN" are
                                                      the same as that of --use-postprocessor (default: pre_process)
    --replace-in-metadata [WHEN:]FIELDS REGEX REPLACE
                                                      Replace text in a metadata field using the given regex. This
                                                      option can be used multiple times. Supported values of "WHEN" are
                                                      the same as that of --use-postprocessor (default: pre_process)
    --xattrs                                          Write metadata to the video file's xattrs (using Dublin Core and
                                                      XDG standards)
    --concat-playlist POLICY                          Concatenate videos in a playlist. One of "never", "always", or
                                                      "multi_video" (default; only when the videos form a single show).
                                                      All the video files must have the same codecs and number of
                                                      streams to be concatenable. The "pl_video:" prefix can be used
                                                      with "--paths" and "--output" to set the output filename for the
                                                      concatenated files. See "OUTPUT TEMPLATE" for details
    --fixup POLICY                                    Automatically correct known faults of the file. One of never (do
                                                      nothing), warn (only emit a warning), detect_or_warn (the default;
                                                      fix the file if we can, warn otherwise), force (try fixing even if
                                                      the file already exists)
    --ffmpeg-location PATH                            Location of the ffmpeg binary; either the path to the binary or
                                                      its containing directory
    --exec [WHEN:]CMD                                 Execute a command, optionally prefixed with when to execute it,
                                                      separated by a ":". Supported values of "WHEN" are the same as
                                                      that of --use-postprocessor (default: after_move). The same syntax
                                                      as the output template can be used to pass any field as arguments
                                                      to the command. If no fields are passed, %(filepath,_filename|)q
                                                      is appended to the end of the command. This option can be used
                                                      multiple times
    --no-exec                                         Remove any previously defined --exec
    --convert-subs FORMAT                             Convert the subtitles to another format (currently supported: ass,
                                                      lrc, srt, vtt). Use "--convert-subs none" to disable conversion
                                                      (default) (Alias: --convert-subtitles)
    --convert-thumbnails FORMAT                       Convert the thumbnails to another format (currently supported:
                                                      jpg, png, webp). You can specify multiple rules using similar
                                                      syntax as "--remux-video". Use "--convert-thumbnails none" to
                                                      disable conversion (default)
    --split-chapters                                  Split video into multiple files based on internal chapters. The
                                                      "chapter:" prefix can be used with "--paths" and "--output" to set
                                                      the output filename for the split files. See "OUTPUT TEMPLATE" for
                                                      details
    --no-split-chapters                               Do not split video based on chapters (default)
    --remove-chapters REGEX                           Remove chapters whose title matches the given regular expression.
                                                      The syntax is the same as --download-sections. This option can be
                                                      used multiple times
    --no-remove-chapters                              Do not remove any chapters from the file (default)
    --force-keyframes-at-cuts                         Force keyframes at cuts when downloading/splitting/removing
                                                      sections. This is slow due to needing a re-encode, but the
                                                      resulting video may have fewer artifacts around the cuts
    --no-force-keyframes-at-cuts                      Do not force keyframes around the chapters when cutting/splitting
                                                      (default)
    --use-postprocessor NAME[:ARGS]                   The (case-sensitive) name of plugin postprocessors to be enabled,
                                                      and (optionally) arguments to be passed to it, separated by a
                                                      colon ":". ARGS are a semicolon ";" delimited list of NAME=VALUE.
                                                      The "when" argument determines when the postprocessor is invoked.
                                                      It can be one of "pre_process" (after video extraction),
                                                      "after_filter" (after video passes filter), "video" (after
                                                      --format; before --print/--output), "before_dl" (before each video
                                                      download), "post_process" (after each video download; default),
                                                      "after_move" (after moving the video file to its final location),
                                                      "after_video" (after downloading and processing all formats of a
                                                      video), or "playlist" (at end of playlist). This option can be
                                                      used multiple times

  SponsorBlock Options:
    Make chapter entries for, or remove various segments (sponsor, introductions, etc.) from downloaded YouTube
    videos using the SponsorBlock API (https://sponsor.ajay.app)

    --sponsorblock-mark CATS                          SponsorBlock categories to create chapters for, separated by
                                                      commas. Available categories are sponsor, intro, outro, selfpromo,
                                                      preview, filler, interaction, music_offtopic, poi_highlight,
                                                      chapter, all and default (=all). You can prefix the category with
                                                      a "-" to exclude it. See [1] for descriptions of the categories.
                                                      E.g. --sponsorblock-mark all,-preview [1]
                                                      https://wiki.sponsor.ajay.app/w/Segment_Categories
    --sponsorblock-remove CATS                        SponsorBlock categories to be removed from the video file,
                                                      separated by commas. If a category is present in both mark and
                                                      remove, remove takes precedence. The syntax and available
                                                      categories are the same as for --sponsorblock-mark except that
                                                      "default" refers to "all,-filler" and poi_highlight, chapter are
                                                      not available
    --sponsorblock-chapter-title TEMPLATE             An output template for the title of the SponsorBlock chapters
                                                      created by --sponsorblock-mark. The only available fields are
                                                      start_time, end_time, category, categories, name, category_names.
                                                      Defaults to "[SponsorBlock]: %(category_names)l"
    --no-sponsorblock                                 Disable both --sponsorblock-mark and --sponsorblock-remove
    --sponsorblock-api URL                            SponsorBlock API location, defaults to https://sponsor.ajay.app

  Extractor Options:
    --extractor-retries RETRIES                       Number of retries for known extractor errors (default is 3), or
                                                      "infinite"
    --allow-dynamic-mpd                               Process dynamic DASH manifests (default) (Alias: --no-ignore-
                                                      dynamic-mpd)
    --ignore-dynamic-mpd                              Do not process dynamic DASH manifests (Alias: --no-allow-dynamic-
                                                      mpd)
    --hls-split-discontinuity                         Split HLS playlists to different formats at discontinuities such
                                                      as ad breaks
    --no-hls-split-discontinuity                      Do not split HLS playlists into different formats at
                                                      discontinuities such as ad breaks (default)
    --extractor-args IE_KEY:ARGS                      Pass ARGS arguments to the IE_KEY extractor. See "EXTRACTOR
                                                      ARGUMENTS" for details. You can use this option multiple times to
                                                      give arguments for different extractors

  Preset Aliases:
    Predefined aliases for convenience and ease of use. Note that future versions of yt-dlp may add or adjust
    presets, but the existing preset names will not be changed or removed

    -t mp3                                            -f 'ba[acodec^=mp3]/ba/b' -x --audio-format mp3

    -t aac                                            -f 'ba[acodec^=aac]/ba[acodec^=mp4a.40.]/ba/b' -x --audio-format
                                                      aac

    -t mp4                                            --merge-output-format mp4 --remux-video mp4 -S
                                                      vcodec:h264,lang,quality,res,fps,hdr:12,acodec:aac

    -t mkv                                            --merge-output-format mkv --remux-video mkv

    -t sleep                                          --sleep-subtitles 5 --sleep-requests 0.75 --sleep-interval 10
                                                      --max-sleep-interval 20

---
## Full gallery-dl Help Reference

usage: gallery-dl [OPTION]... URL...

Options:
  -h, --help                  show this help message and exit
  --version                   show program's version number and exit
  -c, --config FILE           load a custom configuration file (defaults to
                              ~/.config/gallery-dl/config.json)
  -d, --dest DIRECTORY        set the destination directory
  -D, --directory DIRECTORY   set the destination directory; each subdirectory
                              gets its own number
  -i, --input-file FILE       download URLs from a text file
  -q, --quiet                 activate quiet mode
  -v, --verbose               print more debugging information
  -g, --get-urls              print URLs instead of downloading
  -G, --resolve-urls          print URLs instead of downloading; resolve redirects
  -j, --dump-json             print JSON information for each URL
  -s, --simulate              simulate a download
  -E, --extractor-info        print extractor information in JSON format
  --list-extractors           list all supported extractors
  -A, --archive FILE          path to an archive file
  --clear-archive             remove all entries from the archive file
  -K, --cookies FILE          path to a cookies file
  --cookies-from-browser BROWSER
                              load cookies from a browser
  --proxy PROXY               use the specified proxy
  --proxy-env [VAR]           use proxy settings from environment variables
  --user-agent USER_AGENT     use a custom User-Agent string
  --referer REFERER           use a custom Referer string
  --source-address IP_ADDRESS
                              client-side IP address to bind to
  --filter EXPRESSION         Python expression to filter files to download
  -o, --option OPTION         set a custom option (KEY=VALUE)
  -u, --username USERNAME     username to use for authentication
  -p, --password PASSWORD     password to use for authentication
  -P, --prompt-password       prompt for password
  -2, --netrc                 use .netrc file for authentication
  -I, --items ITEM_INDICES    specify which gallery items to download
  --zip                       store downloaded files in a ZIP archive
  --zip-comment COMMENT       comment for the ZIP archive
  --ugoira-conv               convert Pixiv Ugoira to WebM
  --ugoira-conv-lossless      convert Pixiv Ugoira to WebM (lossless)
  --write-metadata            write metadata to a .json file
  --write-tags                write tags to a .txt file
  --write-infojson            write ytdl-like .info.json file
  --mtime-from-date           set file modification time from 'date' metadata
  --mtime-from-iso-date       set file modification time from ISO 8601 date
                              metadata
  --no-download               do not download any files
  --no-part                   do not use .part files
  --no-skip                   do not skip downloads
  --no-mtime                  do not set file modification time
  --no-check-certificate      suppress HTTPS certificate validation
  --no-verify                 suppress HTTPS certificate validation
  --terminate-on-error        terminate on any error
  --limit-rate RATE           maximum download rate (e.g. 50K or 4.2M)
  --retries RETRIES           number of retries (default: 4)
  --sleep SECONDS             number of seconds to sleep before each download
  --filesize-min BYTES        do not download files smaller than this
  --filesize-max BYTES        do not download files larger than this
  --imgur-client-id CLIENT_ID
                              Imgur API client ID
  --deviantart-mature         enable content for mature audiences
  --deviantart-oauth          use OAuth for authentication
  --ehentai-cookies           use browser cookies for e-hentai.org
  --ehentai-eh-member-id MEMBER_ID
                              e-hentai.org member ID
  --ehentai-ipb-pass-hash PASS_HASH
                              e-hentai.org pass hash
  --flickr-api-key API_KEY    Flickr API key
  --flickr-api-secret API_SECRET
                              Flickr API secret
  --flickr-oauth              use OAuth for authentication
  --instagram-stories         download stories
  --instagram-highlights      download story highlights
  --instagram-tagged          download tagged posts
  --instagram-igtv            download IGTV posts
  --mastodon-oauth            use OAuth for authentication
  --pixiv-oauth               use OAuth for authentication
  --reddit-subreddit-mode MODE
                              subreddit parsing mode (hot, new, top, ...)
  --reddit-oauth              use OAuth for authentication
  --smugmug-api-key API_KEY   SmugMug API key
  --smugmug-oauth             use OAuth for authentication
  --tumblr-api-key API_KEY    Tumblr API key
  --twitter-retweets          include retweets (default: true)
  --twitter-replies           include replies (default: true)
  --twitter-videos            include videos (default: true)
  --twitter-images            include images (default: true)
  --twitter-text              include tweet text (default: false)
  --vk-oauth                  use OAuth for authentication

"""

import subprocess
import sys
import json
import os
import signal
import threading
import argparse
import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import shlex
import re
import queue
import time
from collections import deque

# ================== USER CONFIGURABLE VARIABLES ==================
YTDLP_PATH = [sys.executable, "-m", "yt_dlp"]
GALLERYDL_PATH = "gallery-dl"
FOLDER_TEMPLATE = "%(channel)s - %(upload_date)s - %(title)s [%(id)s]"
OUTPUT_TEMPLATE = os.path.join(os.getcwd(), f"{FOLDER_TEMPLATE}.%(ext)s")
OUTPUT_TEMPLATE_FOLDER = os.path.join(os.getcwd(), FOLDER_TEMPLATE, f"{FOLDER_TEMPLATE}.%(ext)s")
PARALLEL_DOWNLOADS = 6
# ================================================================

# --- Globals for State Management and Shutdown ---
running_processes = set()
process_lock = threading.Lock()
print_lock = threading.Lock()
log_lock = threading.Lock()
failed_urls = []
failed_urls_lock = threading.Lock()
success_urls = []
success_urls_lock = threading.Lock()

YTDLP_TASK = "yt-dlp"
GALLERYDL_TASK = "gallery-dl"
HEARTBEAT_SECONDS = 20

# --- Live UI state ---
task_status_lock = threading.Lock()
task_statuses = {}
ui_events = deque(maxlen=60)
ui_stop_event = threading.Event()
ui_render_thread = None
ui_enabled = False
ui_dirty_event = threading.Event()
executor = None

def emit_message(message):
    """Prints normally, or appends to live UI event stream."""
    if ui_enabled:
        with task_status_lock:
            timestamp = datetime.datetime.now().strftime('%H:%M:%S')
            ui_events.append(f"[{timestamp}] {message}")
        ui_dirty_event.set()
        return
    with print_lock:
        try:
            print(message, flush=True)
        except UnicodeEncodeError:
            # Fallback: Strip non-ASCII characters if printing fails
            print(message.encode('ascii', 'ignore').decode('ascii'), flush=True)

def update_task_status(task_id, **updates):
    """Thread-safe task status update for live UI."""
    if not task_id:
        return
    with task_status_lock:
        current = task_statuses.get(task_id, {})
        current.update(updates)
        if 'last_update' not in current:
            current['last_update'] = time.monotonic()
        current['last_update'] = time.monotonic()
        task_statuses[task_id] = current
    ui_dirty_event.set()

def parse_progress_line(line):
    """Parses yt-dlp [download] progress lines."""
    pattern = (
        r'^\[download\]\s+'
        r'(?P<pct>\d+(?:\.\d+)?)%\s+of\s+'
        r'(?P<size>.+?)\s+at\s+'
        r'(?P<speed>.+?)\s+ETA\s+'
        r'(?P<eta>.+)$'
    )
    match = re.search(pattern, line.strip())
    if not match:
        return None
    return {
        'percent': match.group('pct'),
        'size': match.group('size'),
        'speed': match.group('speed'),
        'eta': match.group('eta'),
    }

def supports_live_ui(args):
    # Always use plain scrolling console output (no dynamic screen redraw UI).
    return False

def render_live_ui(total_urls):
    """Continuously renders live task status."""
    spinner = ['|', '/', '-', '\\']
    spin_index = 0

    while not ui_stop_event.is_set():
        ui_dirty_event.wait(timeout=0.35)
        ui_dirty_event.clear()
        spin_index = (spin_index + 1) % len(spinner)

        with task_status_lock:
            statuses = list(task_statuses.items())
            events = list(ui_events)[-12:]

        total_tasks = len(statuses)
        done = sum(1 for _, s in statuses if s.get('state') == 'SUCCESS')
        failed = sum(1 for _, s in statuses if s.get('state') == 'FAILURE')
        active = [s for _, s in statuses if s.get('state') not in ('SUCCESS', 'FAILURE')]
        recent_done = [s for _, s in statuses if s.get('state') in ('SUCCESS', 'FAILURE')]
        recent_done.sort(key=lambda s: s.get('last_update', 0), reverse=True)
        recent_done = recent_done[:4]

        lines = []
        lines.append(f"{spinner[spin_index]} URLs: {total_urls} | Tasks: {total_tasks} | Done: {done} | Failed: {failed} | Active: {len(active)}")
        lines.append("-" * 110)
        lines.append("Active Downloads")

        if active:
            for s in active[:8]:
                slot = s.get('slot', '--/--')
                title = (s.get('title', 'Untitled') or 'Untitled').replace('\n', ' ')
                title = title[:56]
                phase = s.get('phase', 'working')
                pct = s.get('percent', '--')
                speed = s.get('speed', '--')
                eta = s.get('eta', '--')
                lines.append(f"[{slot}] {pct:>6}% | {speed:>12} | ETA {eta:>8} | {phase:<12} | {title}")
        else:
            lines.append("(no active tasks)")

        lines.append("-" * 110)
        lines.append("Recent Results")
        if recent_done:
            for s in recent_done:
                slot = s.get('slot', '--/--')
                state = s.get('state', 'UNKNOWN')
                title = (s.get('title', 'Untitled') or 'Untitled').replace('\n', ' ')[:80]
                lines.append(f"[{slot}] {state:<7} {title}")
        else:
            lines.append("(no finished tasks yet)")

        lines.append("-" * 110)
        lines.append("Recent Logs")
        lines.extend(events if events else ["(no log lines yet)"])

        with print_lock:
            sys.stdout.write("\x1b[H\x1b[J")
            sys.stdout.write("\n".join(lines) + "\n")
            sys.stdout.flush()

def start_live_ui(total_urls, args):
    global ui_enabled, ui_render_thread
    ui_enabled = supports_live_ui(args)
    if not ui_enabled:
        return
    ui_stop_event.clear()
    ui_dirty_event.set()
    ui_render_thread = threading.Thread(target=render_live_ui, args=(total_urls,), daemon=True)
    ui_render_thread.start()

def stop_live_ui(immediate=False):
    global ui_render_thread, ui_enabled
    if not ui_enabled:
        return
    ui_stop_event.set()
    ui_dirty_event.set()
    if ui_render_thread:
        # If immediate, don't wait for the thread to join
        if not immediate:
            ui_render_thread.join(timeout=0.5)
    with print_lock:
        # Move cursor to end and clear
        sys.stdout.write("\x1b[?25h") # Show cursor
        sys.stdout.flush()
    ui_enabled = False
    ui_render_thread = None

def should_echo_live_line(line, args):
    """Controls how much child-process output is shown in real time."""
    if getattr(args, 'verbose', False):
        return True
    
    lowered = line.strip().lower()
    # Show lines starting with a tag like [youtube], [info], [download], [merger], [ffmpeg], etc.
    if lowered.startswith("["):
        return True
    
    return (
        "error:" in lowered
        or "warning:" in lowered
        or "retrying" in lowered
        or "destination:" in lowered
        or "already been downloaded" in lowered
    )

def ms_to_srt_time(ms):
    """Converts milliseconds to SRT timestamp format (HH:MM:SS,mmm)."""
    seconds, milliseconds = divmod(ms, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d},{int(milliseconds):03d}"

def process_json3_subtitle(json3_path):
    """Parses a JSON3 subtitle file and extracts plaintext and word-level SRT."""
    try:
        with open(json3_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        events = data.get('events', [])
        if not events:
            return "No events found in JSON3 file."

        base_name = os.path.splitext(json3_path)[0]
        txt_path = f"{base_name}.txt"
        srt_path = f"{base_name}.srt"
        
        full_text_parts = []
        srt_entries = []
        srt_index = 1
        last_event_end_ms = -1

        for event in events:
            start_ms = event.get('tStartMs', 0)
            duration = event.get('dDurationMs', 0)
            segments = event.get('segs', [])
            
            if not segments:
                continue

            # --- Plaintext Extraction (Readability Focus) ---
            event_text = "".join([s.get('utf8', '') for s in segments]).replace('\n', ' ').strip()
            if event_text:
                # Use a threshold (1.5s) to detect a natural break or paragraph
                if last_event_end_ms != -1 and (start_ms - last_event_end_ms) > 1500:
                    full_text_parts.append("\n\n")
                elif full_text_parts and not full_text_parts[-1].endswith("\n\n"):
                    full_text_parts.append(" ")
                
                full_text_parts.append(event_text)
                last_event_end_ms = start_ms + duration

            # --- SRT Extraction (Word/Segment Level) ---
            for i, seg in enumerate(segments):
                text = seg.get('utf8', '').strip()
                if not text:
                    continue
                
                offset = seg.get('tOffsetMs', 0)
                seg_start_ms = start_ms + offset
                
                if i < len(segments) - 1:
                    next_offset = segments[i+1].get('tOffsetMs', 0)
                    if next_offset > offset:
                         seg_end_ms = start_ms + next_offset
                    else:
                         seg_end_ms = seg_start_ms + 100
                else:
                    seg_end_ms = start_ms + duration
                
                if seg_end_ms <= seg_start_ms:
                     seg_end_ms = seg_start_ms + 100

                srt_entries.append(f"{srt_index}\n{ms_to_srt_time(seg_start_ms)} --> {ms_to_srt_time(seg_end_ms)}\n{text}\n")
                srt_index += 1

        # Write Plaintext (Joined parts)
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write("".join(full_text_parts).strip())

        # Write SRT
        with open(srt_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(srt_entries))
            
        return f"Created {os.path.basename(txt_path)} and {os.path.basename(srt_path)}", txt_path

    except Exception as e:
        return f"Error processing JSON3: {e}"

def extract_subtitle_paths_from_output(output_text):
    """Extract subtitle file paths and metadata from yt-dlp output."""
    subtitle_exts = ('.json3', '.srt', '.vtt', '.ass', '.lrc')
    results = []
    current_is_auto = False
    
    # ANSI escape code stripper
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    
    for raw_line in output_text.splitlines():
        # Strip ANSI codes and whitespace
        line = ansi_escape.sub('', raw_line).strip()
        
        # Check if this line indicates the start of a subtitle block
        if "Writing video subtitles to:" in line:
            current_is_auto = False
        elif "Writing auto-generated subtitles to:" in line:
            current_is_auto = True
            
        # Match destinations
        # We look for "to: " or "Destination: " followed by the path
        patterns = [
            r'(?:Writing (?:video|auto-generated) subtitles to:|Destination:)\s*(.+)$',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, line)
            if match:
                path = match.group(1).strip().strip('"').strip("'")
                if path.lower().endswith(subtitle_exts):
                    results.append({
                        'path': path,
                        'is_auto': current_is_auto,
                        'ext': os.path.splitext(path)[1].lower()
                    })
    
    # Remove duplicates
    seen = set()
    unique_results = []
    for r in results:
        if r['path'] not in seen:
            unique_results.append(r)
            seen.add(r['path'])
            
    return unique_results

def process_text_subtitle(subtitle_path):
    """Converts SRT/VTT/ASS/LRC subtitle files to plaintext .txt."""
    ext = os.path.splitext(subtitle_path)[1].lower()
    if ext == '.json3':
        return process_json3_subtitle(subtitle_path)

    if not os.path.exists(subtitle_path):
        return f"Subtitle file not found: {os.path.basename(subtitle_path)}"

    try:
        with open(subtitle_path, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()

        chunks = []
        current_chunk = []
        skip_prefixes = ('WEBVTT', 'NOTE', 'STYLE', 'REGION', 'Kind:', 'Language:')

        for raw_line in lines:
            line = raw_line.strip()
            if not line:
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
                    current_chunk = []
                continue

            if line.startswith(skip_prefixes):
                continue
            if re.fullmatch(r'\d+', line):
                continue
            if '-->' in line:
                continue

            # Strip lightweight subtitle markup tags.
            clean = re.sub(r'<[^>]+>', '', line)
            clean = re.sub(r'{\\[^}]+}', '', clean)
            clean = re.sub(r'\s+', ' ', clean).strip()
            if clean:
                current_chunk.append(clean)

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        # Create a readable continuous transcript instead of one paragraph per subtitle cue.
        text = " ".join(chunks).strip()
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\s+([,.;:!?])', r'\1', text)
        text = re.sub(r'([,.;:!?])([^\s])', r'\1 \2', text)

        txt_path = f"{os.path.splitext(subtitle_path)[0]}.txt"
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(text)

        return f"Created {os.path.basename(txt_path)}", txt_path
    except Exception as e:
        return f"Error converting subtitle to plaintext ({os.path.basename(subtitle_path)}): {e}"

def log_message(log_file, status, url, message=""):
    """Thread-safe function to write a formatted message to the log file."""
    if not log_file:
        return
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with log_lock:
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"[{timestamp}] :: {status.upper()} :: {url} :: {message}\n")

def sanitize_filename(name):
    """Sanitizes a string to be a valid and readable filename."""
    if not isinstance(name, str):
        name = str(name)
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    name = "".join(c for c in name if c.isprintable())
    if len(name) > 150:
        name = name[:150].rsplit(' ', 1)[0]
    return name.strip('. ')

def terminate_running_processes():
    """Best-effort termination for every active child process."""
    with process_lock:
        processes = list(running_processes)

    for proc in processes:
        try:
            if proc.poll() is None:
                proc.kill()
        except Exception:
            pass

def request_global_shutdown(reason=None):
    """Signal all workers to stop and terminate active subprocesses."""
    ui_stop_event.set()
    terminate_running_processes()
    if reason:
        log_message(None, "CANCELLED", "", reason)

def run_updates():
    """Updates the core dependencies, yt-dlp and gallery-dl."""
    print("--- ⬆️  Updating Dependencies ---")
    
    print("\n[1/2] Updating yt-dlp...")
    try:
        update_command_ytdlp = [*YTDLP_PATH, "-U"]
        subprocess.run(update_command_ytdlp, check=True)
    except Exception as e:
        print(f"  ❌ An error occurred during yt-dlp update: {e}")

    print("\n[2/2] Updating gallery-dl...")
    try:
        update_command_gallerydl = [sys.executable, "-m", "pip", "install", "--upgrade", "gallery-dl"]
        subprocess.run(update_command_gallerydl, check=True)
    except Exception as e:
        print(f"  ❌ An error occurred during gallery-dl update: {e}")

    print("\n--- ✅ Update process finished ---")
    sys.exit(0)

def run_download_task(task_type, identifier, title, args, original_url, task_id=None, slot_label=None, channel=None, upload_date=None, video_lang=None):
    """Dispatches and runs a single media download task."""
    command_list, display_title, tool_name = None, "", ""
    
    if task_type == YTDLP_TASK:
        tool_name = "yt-dlp"
        command_list = build_ytdlp_command(identifier, args, video_lang=video_lang)
        display_title = (title[:50] + '...') if len(title) > 50 else title
    elif task_type == GALLERYDL_TASK:
        tool_name = "gallery-dl"
        command_list = build_gallerydl_command(identifier, args, title)
        display_title = (identifier[:60] + '...') if len(identifier) > 60 else identifier
    else:
        return ("FAILURE", f"Unknown task type '{task_type}'")

    if args.verbose:
        emit_message(f"[DEBUG] Executing {tool_name} command: {' '.join(shlex.quote(c) for c in command_list)}")
    
    process = None
    try:
        update_task_status(task_id, slot=slot_label or "--/--", title=display_title, tool=tool_name, state="STARTING", phase="starting")

        popen_kwargs = {}
        if os.name == 'nt':
            popen_kwargs['creationflags'] = getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0)

        process = subprocess.Popen(
            command_list,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True, encoding='utf-8', errors='replace', bufsize=1,
            **popen_kwargs
        )
        with process_lock:
            running_processes.add(process)

        stdout_chunks = []
        stderr_chunks = []
        output_queue = queue.Queue()

        def reader_thread(stream, stream_name):
            try:
                for raw_line in iter(stream.readline, ''):
                    output_queue.put((stream_name, raw_line.rstrip('\r\n')))
            finally:
                stream.close()
                output_queue.put((stream_name, None))

        out_t = threading.Thread(target=reader_thread, args=(process.stdout, "stdout"), daemon=True)
        err_t = threading.Thread(target=reader_thread, args=(process.stderr, "stderr"), daemon=True)
        out_t.start()
        err_t.start()

        finished_streams = set()
        last_output_ts = time.monotonic()
        start_ts = last_output_ts

        while len(finished_streams) < 2:
            if ui_stop_event.is_set():
                if process and process.poll() is None:
                    try:
                        process.kill()
                    except:
                        pass
                update_task_status(task_id, state="CANCELLED", phase="cancelled", speed="--", eta="--")
                return ("FAILURE", f"Cancelled {tool_name}: {display_title}", [])
                
            try:
                stream_name, line = output_queue.get(timeout=0.1) # Shorter timeout
            except queue.Empty:
                if process.poll() is not None and out_t.is_alive() is False and err_t.is_alive() is False:
                    break
                now = time.monotonic()
                if now - last_output_ts >= HEARTBEAT_SECONDS:
                    elapsed = int(now - start_ts)
                    update_task_status(task_id, phase=f"idle {elapsed}s")
                    emit_message(f"[DEBUG] {tool_name} still running for {elapsed}s (title: {display_title})")
                    last_output_ts = now
                continue

            if line is None:
                finished_streams.add(stream_name)
                continue

            last_output_ts = time.monotonic()
            if stream_name == "stdout":
                stdout_chunks.append(line)
            else:
                stderr_chunks.append(line)

            if task_type == YTDLP_TASK:
                prog = parse_progress_line(line)
                if prog:
                    update_task_status(
                        task_id,
                        state="RUNNING",
                        phase="downloading",
                        percent=prog['percent'],
                        speed=prog['speed'],
                        eta=prog['eta'],
                    )
                elif "[Merger]" in line:
                    update_task_status(task_id, state="RUNNING", phase="merging")
                elif "[ExtractAudio]" in line:
                    update_task_status(task_id, state="RUNNING", phase="audio")
                elif "[download] Destination:" in line:
                    update_task_status(task_id, state="RUNNING", phase="fetching", percent="0.0", speed="--", eta="--")
                elif "[info] Downloading subtitles" in line:
                    update_task_status(task_id, state="RUNNING", phase="subtitles")

            if should_echo_live_line(line, args):
                is_progress_spam = line.startswith("[download]") and parse_progress_line(line) is not None
                if not (ui_enabled and not args.verbose and is_progress_spam):
                    emit_message(f"[{tool_name}] {line}")

        process.wait()
        out_t.join(timeout=1)
        err_t.join(timeout=1)
        stdout = "\n".join(stdout_chunks)
        stderr = "\n".join(stderr_chunks)

        interrupted_by_user = any(
            marker in f"{stdout}\n{stderr}"
            for marker in ("Interrupted by user", "KeyboardInterrupt")
        )
        if interrupted_by_user or ui_stop_event.is_set():
            request_global_shutdown("Child process was interrupted; stopping all queued work.")
            update_task_status(task_id, state="CANCELLED", phase="cancelled", speed="--", eta="--")
            return ("FAILURE", f"Cancelled {tool_name}: {display_title}", [])
        
        if process.returncode == 0:
            update_task_status(task_id, state="POST", phase="post-processing", percent="100.0", eta="00:00")
            subtitle_mode = getattr(args, 'default_download', False) or args.srt or args.json3
            subtitle_msgs = []
            if task_type == YTDLP_TASK and subtitle_mode:
                full_output = f"{stdout}\n{stderr}"
                subtitle_candidates_detected = extract_subtitle_paths_from_output(full_output)
                subtitle_paths = []

                # --- Always log subtitle debug info to the log file ---
                sub_keywords = ('subtitle', 'writing video sub', 'writing auto-generated sub',
                                'subtitlesconvert', '.srt', '.vtt', '.json3', '.ass', '.lrc')
                sub_lines = [l.strip() for l in full_output.splitlines()
                             if any(kw in l.lower() for kw in sub_keywords)]
                log_message(args.log_file, "SUB-DEBUG", original_url,
                    f"yt-dlp subtitle-related output ({len(sub_lines)} lines): " +
                    (" | ".join(sub_lines[:30]) if sub_lines else "(none)"))
                log_message(args.log_file, "SUB-DEBUG", original_url,
                    f"Regex detected {len(subtitle_candidates_detected)} path(s) from output: " +
                    (", ".join(f"[{s['path']}] auto={s['is_auto']} ext={s['ext']}" for s in subtitle_candidates_detected)
                     if subtitle_candidates_detected else "(none)"))

                subtitle_candidates = []

                if subtitle_candidates_detected:
                    # Filter for only those that actually exist on disk now
                    existing = [s for s in subtitle_candidates_detected if os.path.exists(s['path'])]
                    missing  = [s for s in subtitle_candidates_detected if not os.path.exists(s['path'])]

                    if missing:
                        log_message(args.log_file, "SUB-DEBUG", original_url,
                            f"Detected but NOT found on disk: {', '.join(s['path'] for s in missing)}")

                        # Fallback: --convert-subs srt renames e.g. .vtt -> .srt after conversion,
                        # so the logged path no longer exists.  Try common subtitle extensions.
                        for s in missing:
                            base_no_ext = os.path.splitext(s['path'])[0]
                            for try_ext in ('.srt', '.vtt', '.json3', '.ass', '.lrc'):
                                alt_path = base_no_ext + try_ext
                                if alt_path != s['path'] and os.path.exists(alt_path):
                                    existing.append({'path': alt_path, 'is_auto': s['is_auto'], 'ext': try_ext})
                                    log_message(args.log_file, "SUB-DEBUG", original_url,
                                        f"Extension substitution hit: {os.path.basename(s['path'])} -> {os.path.basename(alt_path)}")
                                    break

                    subtitle_candidates = existing
                    if existing:
                        log_message(args.log_file, "SUB-DEBUG", original_url,
                            f"Candidates after existence/substitution check: {', '.join(s['path'] for s in existing)}")

                # Filesystem fallback: scan for subtitle files by video ID if still empty
                if not subtitle_candidates:
                    video_id_match = re.search(r'(?:v=|youtu\.be/|shorts/)([a-zA-Z0-9_-]{11})', identifier)
                    if video_id_match:
                        video_id = video_id_match.group(1)
                        sub_exts = {'.srt', '.vtt', '.json3', '.ass', '.lrc'}
                        search_dirs = [os.getcwd()]
                        if getattr(args, 'individual_folder', False):
                            try:
                                for entry in os.scandir(os.getcwd()):
                                    if entry.is_dir() and video_id in entry.name:
                                        search_dirs.append(entry.path)
                            except Exception:
                                pass

                        for sdir in search_dirs:
                            try:
                                for entry in os.scandir(sdir):
                                    if entry.is_file() and video_id in entry.name:
                                        ext = os.path.splitext(entry.name)[1].lower()
                                        if ext in sub_exts:
                                            subtitle_candidates.append({
                                                'path': entry.path,
                                                'is_auto': 'auto' in entry.name.lower(),
                                                'ext': ext,
                                            })
                            except Exception:
                                pass

                        if subtitle_candidates:
                            log_message(args.log_file, "SUB-DEBUG", original_url,
                                f"Filesystem fallback found {len(subtitle_candidates)} file(s): " +
                                ", ".join(s['path'] for s in subtitle_candidates))
                        else:
                            log_message(args.log_file, "SUB-DEBUG", original_url,
                                f"Filesystem fallback: no subtitle files for video ID '{video_id}' in {search_dirs}")
                    else:
                        log_message(args.log_file, "SUB-DEBUG", original_url,
                            "Filesystem fallback skipped: could not extract video ID from URL")

                if subtitle_candidates:
                    # 1. Prioritize: Manual > Auto, Lang match > other, SRT > others
                    target_langs = []
                    if args.language:
                        target_langs.append(args.language.lower())
                    if video_lang:
                        lang_base = video_lang.split('-')[0].lower()
                        if lang_base not in target_langs:
                            target_langs.append(lang_base)
                    # Ensure English is always a fallback target language
                    if 'en' not in target_langs:
                        target_langs.append('en')

                    def score_subtitle(sub):
                        score = 0
                        if not sub['is_auto']: score += 1000

                        path_lower = sub['path'].lower()
                        for i, lang in enumerate(target_langs):
                            if f".{lang}." in path_lower or path_lower.endswith(f".{lang}"):
                                 score += (500 - i * 50)
                                 break

                        if sub['ext'] == '.srt': score += 100
                        if sub['ext'] == '.json3' and args.json3: score += 200

                        return score

                    subtitle_candidates.sort(key=score_subtitle, reverse=True)

                    best_sub = subtitle_candidates[0]
                    other_subs = subtitle_candidates[1:]
                    log_message(args.log_file, "SUB-DEBUG", original_url,
                        f"Best subtitle chosen: {best_sub['path']} (score={score_subtitle(best_sub)})")

                    # 2. Process the best one -> generate cleaned-up .txt
                    res = process_text_subtitle(best_sub['path'])
                    if isinstance(res, tuple):
                        msg, txt_path = res
                        subtitle_paths.append(txt_path)
                        subtitle_msgs.append(msg)
                        log_message(args.log_file, "SUB-DEBUG", original_url,
                            f"Plaintext generated: {txt_path}")
                    else:
                        subtitle_msgs.append(res)
                        log_message(args.log_file, "SUB-DEBUG", original_url,
                            f"Plaintext generation FAILED: {res}")

                    # 3. Cleanup: Delete all other subtitle candidates from disk
                    for other in other_subs:
                        try:
                            if os.path.exists(other['path']):
                                os.remove(other['path'])
                        except Exception:
                            pass
                else:
                    log_message(args.log_file, "SUB-DEBUG", original_url,
                        "No subtitle candidates found after all detection methods")

                # Always show subtitle processing results
                for msg in subtitle_msgs:
                    emit_message(f"[SUBTITLE] {msg}")

                # Make subtitle-only runs explicit when no subtitle files are produced.
                requested_sub_only = (args.srt or args.json3) and not (
                    getattr(args, 'default_download', False) or args.video or args.audio_only
                )
                if requested_sub_only and not subtitle_candidates:
                    update_task_status(task_id, state="FAILURE", phase="no-subtitles", speed="--", eta="--")
                    return ("FAILURE", f"Finished {tool_name}: {display_title} (no subtitle files available/saved)", [])

            # Extract downloaded filetypes from stdout
            downloaded_exts = set()
            for line in stdout.splitlines() + stderr.splitlines():
                # Extract extensions from various yt-dlp successful lines
                # Examples:
                # [info] Writing video description to: NA - NA - #peteknows ... [7434960151893200896].description
                # [info] Writing video metadata as JSON to: NA - NA ... [7434960151893200896].info.json
                # [info] Writing video thumbnail 56 to: NA - NA - ... [7434960151893200896].webp
                # [download] Destination: NA - NA - #peteknows ... [7434960151893200896].mp4
                # [download] NA - NA... [7434960151893200896].mp4 has already been downloaded
                # [Merger] Merging formats into "NA - NA... [7434960151893200896].mkv"
                # [info] Writing video subtitles to: NA - NA... [7434960151893200896].en.srt
                match = re.search(r'(?:into "|Destination: |to: |(?:has already been downloaded).*\.\s*)(.+?\.)([a-zA-Z0-9.]+)(?:"|$)', line)
                if match:
                    ext = match.group(2).lower()
                    if '.' in ext: # e.g. info.json or en.srt
                        ext = ext.split('.')[-1]
                    downloaded_exts.add(ext)

                match = re.search(r'has already been downloaded(?:.*?\.([a-zA-Z0-9]+))?', line)
                if match and match.group(1): downloaded_exts.add(match.group(1).lower())
                
                # gallery-dl specific lines
                match = re.search(r'^# .+\.([a-zA-Z0-9]+)$', line)
                if match: downloaded_exts.add(match.group(1).lower())

            ext_str = ""
            if downloaded_exts:
                ext_str = f" [{', '.join(sorted(downloaded_exts))}]"

            if subtitle_msgs:
                update_task_status(task_id, state="SUCCESS", phase="done", percent="100.0", speed="--", eta="00:00")
                return ("SUCCESS", f"Finished {tool_name}: {display_title}{ext_str} ({len(subtitle_msgs)} subtitle text file(s) created)", subtitle_paths)
            
            update_task_status(task_id, state="SUCCESS", phase="done", percent="100.0", speed="--", eta="00:00")
            return ("SUCCESS", f"Finished {tool_name}: {display_title}{ext_str}", [])
        else:
            error_message = stderr.strip().replace('\n', ' ')
            
            # Check for indicators of a successful file save in stdout
            download_successful = "[Merger] Merging formats into" in stdout or \
                                  "[download] Destination:" in stdout or \
                                  "has already been downloaded" in stdout
            
            non_fatal_patterns = [
                "HTTP Error 429",
                "Too Many Requests",
                "Unable to download video subtitles",
                "Postprocessing: Supported filetypes for thumbnail embedding",
                "Supported filetypes for thumbnail embedding",
            ]
            
            is_non_fatal_error = any(p.lower() in error_message.lower() for p in non_fatal_patterns)
            
            # A non-fatal error is only a "SUCCESS with warnings" if a file was actually created.
            if is_non_fatal_error and download_successful:
                update_task_status(task_id, state="SUCCESS", phase="done-with-warnings", percent="100.0", speed="--", eta="00:00")
                return ("SUCCESS", f"Completed {tool_name} with warnings: {display_title} :: {error_message}", [])
            else:
                update_task_status(task_id, state="FAILURE", phase="failed", speed="--", eta="--")
                return ("FAILURE", f"Failed {tool_name}: {display_title} :: {error_message}", [])

    except Exception as e:
        update_task_status(task_id, state="FAILURE", phase="exception", speed="--", eta="--")
        return ("FAILURE", f"Error running {tool_name} for {display_title}: {e}", [])
    finally:
        if process:
            with process_lock:
                running_processes.discard(process)

def run_text_extraction_task(url):
    """Extracts text metadata from a URL using yt-dlp or gallery-dl."""
    TITLE_KEYS = ['title', 'fullname', 'username']
    CONTENT_KEYS = ['description', 'content', 'caption', 'tweet-text']
    data = None

    try:
        command = [*YTDLP_PATH, '--ignore-config', '--dump-json', '--skip-download', '--ignore-no-formats-error', url]
        result = subprocess.run(command, capture_output=True, text=True, check=True, encoding='utf-8', errors='replace')
        data = result.stdout
    except subprocess.CalledProcessError:
        pass

    entries = []
    if data:
        for line in data.strip().splitlines():
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    if not entries:
        try:
            command = [GALLERYDL_PATH, '--dump-json', '--no-download', url]
            result = subprocess.run(command, capture_output=True, text=True, check=True, encoding='utf-8', errors='replace')
            first_line = result.stdout.strip().splitlines()[0]
            entries = [json.loads(first_line)]
        except (subprocess.CalledProcessError, json.JSONDecodeError, IndexError):
            return ("FAILURE", "Could not extract metadata from either yt-dlp or gallery-dl.")

    primary = entries[0]
    title = next((primary.get(key) for key in TITLE_KEYS if primary.get(key)), "Untitled")

    # If this looks like a thread (multiple tweet entries), stitch them together.
    stitched = []
    thread_entries = primary.get('entries') if isinstance(primary, dict) else None
    if thread_entries and isinstance(thread_entries, list):
        for entry in thread_entries:
            if not isinstance(entry, dict):
                continue
            text = next((entry.get(key) for key in CONTENT_KEYS if entry.get(key)), "")
            if text:
                stitched.append(text.strip())
    else:
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            text = next((entry.get(key) for key in CONTENT_KEYS if entry.get(key)), "")
            if text:
                stitched.append(text.strip())

    if not stitched:
        if title != "Untitled" and isinstance(primary, dict) and title in primary.values():
            stitched = [title]
        else:
            return ("FAILURE", "No text content found in metadata.")

    content = "\n\n---\n\n".join(stitched)
    final_text = f"Title: {title}\nURL: {url}\n\n---\n\n{content}"
    filename = sanitize_filename(title)

    try:
        with open(f"{filename}.txt", "w", encoding="utf-8") as f:
            f.write(final_text)
        return ("SUCCESS", f"Saved text to: {filename}.txt")
    except Exception as e:
        return ("FAILURE", f"Error saving file: {e}")

def normalize_url(url):
    """Normalizes YouTube IDs (video or playlist) into full URLs."""
    url = url.strip()
    if '://' in url:
        return url
        
    # YouTube Playlist ID: Usually 34 chars starting with PL, but can be other 2-letter prefixes like RD (Mixes).
    if re.match(r'^[A-Z]{2}[a-zA-Z0-9_-]{12,}$', url):
        return f"https://www.youtube.com/playlist?list={url}"
        
    # YouTube Video ID: Exactly 11 characters.
    if re.match(r'^[a-zA-Z0-9_-]{11}$', url):
        return f"https://www.youtube.com/watch?v={url}"
        
    return url

def get_tasks_from_url(url):
    """Determines if a URL is for yt-dlp or gallery-dl and returns (tasks, collection_title)."""
    url = normalize_url(url)
    is_youtube = 'youtube.com' in url.lower() or 'youtu.be' in url.lower()
    
    # Use --flat-playlist only for actual playlists or channels to ensure single videos get full metadata (like language).
    command = [*YTDLP_PATH, '--ignore-config', '--dump-json', '--ignore-no-formats-error', url]
    if any(p in url.lower() for p in ['playlist', 'list=', '/c/', '/user/', '/@']):
        command.append('--flat-playlist')
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True, encoding='utf-8', errors='replace')
        ytdlp_tasks = []
        collection_title = None
        
        for line in result.stdout.strip().splitlines():
            try:
                data = json.loads(line)
                
                # Capture the playlist/collection title if this is the top-level entry
                if not collection_title:
                    collection_title = data.get('title') or data.get('playlist_title') or data.get('uploader')

                # Helper to process a single entry
                def add_ytdlp_task(entry, original_url):
                    entry_url = entry.get('webpage_url') or entry.get('url')
                    if not entry_url and entry.get('ie_key') == 'Youtube':
                         entry_url = f"https://www.youtube.com/watch?v={entry['id']}"
                    title = entry.get("title") or f"Media_{entry.get('id', 'unknown')}"
                    channel = entry.get("channel") or entry.get("uploader") or "Unknown Channel"
                    upload_date = entry.get("upload_date") or "00000000"
                    language = entry.get("language")
                    ytdlp_tasks.append((YTDLP_TASK, entry_url or original_url, title, original_url, channel, upload_date, language))

                if data.get('_type') == 'playlist' and 'entries' in data:
                    for entry in data['entries']:
                        if entry and entry.get('id'):
                            add_ytdlp_task(entry, url)
                elif data.get('entries'): # Generic entries list
                    for entry in data['entries']:
                        if entry and entry.get('id'):
                            add_ytdlp_task(entry, url)
                elif data.get('id'): # Single item
                    add_ytdlp_task(data, url)

            except json.JSONDecodeError:
                continue
        
        # If discovery found nothing but it's YouTube, force use of yt-dlp
        if not ytdlp_tasks and is_youtube:
            ytdlp_tasks.append((YTDLP_TASK, url, "YouTube Content", url, "YouTube", "00000000", None))

        if ytdlp_tasks:
            return ytdlp_tasks, (collection_title or "Links")
        else:
            return [(GALLERYDL_TASK, url, url, url, "Gallery", "00000000", None)], "Links"

    except subprocess.CalledProcessError as e:
        if is_youtube:
            return [(YTDLP_TASK, url, "YouTube Content", url, "YouTube", "00000000", None)], "YouTube Content"
        
        stderr_lower = e.stderr.lower()
        if "no video formats found" in stderr_lower or "unsupported url" in stderr_lower or "no media found" in stderr_lower:
            return [(GALLERYDL_TASK, url, url, url, "Gallery", "00000000", None)], "Gallery"
        else:
            raise Exception(f"yt-dlp failed to fetch info: {e.stderr.strip()}")
    except FileNotFoundError:
        raise Exception(f"Critical Error: yt-dlp executable not found at '{YTDLP_PATH}'.")

def build_ytdlp_command(target_url, args, video_lang=None):
    video_url = target_url
    output_tmpl = OUTPUT_TEMPLATE_FOLDER if getattr(args, 'individual_folder', False) else OUTPUT_TEMPLATE
    
    # Base command: ignore config files and explicitly disable sidecar files by default
    command_list = [
        *YTDLP_PATH, 
        '--ignore-config',
        '--no-warnings', 
        '--no-colors', 
        '--newline', 
        '--progress-delta', '2', 
        '-o', output_tmpl,
        '--no-write-thumbnail',
        '--no-write-info-json',
        '--no-write-description'
    ]

    if args.verbose:
        command_list.append('-v')

    wants_video = getattr(args, 'default_download', False) or args.video
    wants_audio_only = args.audio_only
    wants_subtitles = getattr(args, 'default_download', False) or args.srt or args.json3
    wants_metadata = getattr(args, 'default_download', False) or args.metadata
    wants_description = getattr(args, 'default_download', False) or args.description
    wants_thumbnail = args.thumbnail
    wants_comments = args.comments

    if wants_video:
        # Keep a broad but compatibility-first format strategy.
        custom_format_string = "bv*[vcodec^=avc1]+ba[acodec^=mp4a]/b[vcodec^=avc1] / bv*+ba/b"
        command_list.extend([
            '-f', custom_format_string,
            '--merge-output-format', 'mp4',
            '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
            '--extractor-args', 'tiktok:api_hostname=api16-normal-c-useast1a.tiktokv.com',
            '--progress',
            '--retries', '10',
            '--fragment-retries', '10',
            '--continue',
            '--compat-options', 'no-youtube-unavailable-videos',
        ])

    if wants_audio_only:
        lang_code = args.language if args.language else ''
        command_list.extend(['-f', f'ba[language={lang_code}]/ba' if lang_code else 'ba', '--extract-audio', '--audio-format', 'mp3', '--audio-quality', '0'])

    if wants_thumbnail:
        # Re-enable if explicitly requested
        command_list.extend(["--write-thumbnail", "--convert-thumbnails", "webp"])

    if wants_metadata:
        command_list.append("--write-info-json")

    if wants_description:
        command_list.append("--write-description")

    if wants_comments:
        command_list.extend(["--write-comments", "--write-info-json"])

    if wants_subtitles:
        if args.language:
            lang_base = args.language.split('-')[0].lower()
            sub_lang = f"{args.language},{lang_base}.*,{lang_base}"
        elif video_lang:
            # Request only the video's language and English to avoid downloading 100+ auto-translated tracks.
            # We use base language codes with a wildcard (e.g., 'en.*') to catch regional variants.
            v_base = video_lang.split('-')[0].lower()
            if v_base != 'en':
                sub_lang = f"{video_lang},{v_base}.*,{v_base},en.*,en"
            else:
                sub_lang = 'en.*,en'
        elif getattr(args, 'default_download', False):
            # Default download mode with no detected language: conservative English fallback.
            # We avoid 'all' because it downloads 100+ auto-translated languages on YouTube.
            sub_lang = 'en.*,en'
        else:
            # Explicit subtitle mode with unknown language metadata:
            # prefer English manual/auto captions instead of "all", which can fetch
            # huge auto-translation sets on YouTube.
            sub_lang = 'en.*,en'

        command_list.append('--write-subs')
        command_list.append('--write-auto-subs')
        command_list.extend(['--sub-langs', sub_lang, '--ignore-errors'])
        if args.json3:
            command_list.extend(['--sub-format', 'json3'])
        else:
            command_list.extend(['--sub-format', 'srt/best', '--convert-subs', 'srt'])

    if not wants_video and not wants_audio_only:
        command_list.append("--skip-download")

    command_list.append(video_url)
    return command_list

def build_gallerydl_command(url, args, title=None):
    command_list = [GALLERYDL_PATH]
    
    # Base behavior: use internal config isolation
    # Note: gallery-dl uses -c for config, but no direct --ignore-config. 
    # We use -c /dev/null if we wanted to truly ignore, but better to just be explicit.
    
    if args.verbose: command_list.append("--verbose")
    
    # If no media is requested, add --no-download
    wants_media = getattr(args, 'default_download', False) or args.video or args.audio_only or args.thumbnail
    if not wants_media:
        command_list.append("--no-download")

    if getattr(args, 'individual_folder', False) and title:
        safe_title = sanitize_filename(title)
        command_list.extend(["-d", os.path.join(os.getcwd(), safe_title)])
    elif args.g_directory: 
        command_list.extend(["-D", args.g_directory])
    
    if args.g_archive: command_list.extend(["-A", args.g_archive])
    if args.g_no_skip: command_list.append("--no-skip")
    
    if args.g_write_metadata or getattr(args, 'default_download', False):
        command_list.append("--write-metadata")
    
    if args.g_options: command_list.extend(shlex.split(args.g_options))
    command_list.append(url)
    return command_list

def process_url(url, index, total_urls, args):
    """Encapsulates the entire workflow for a single URL."""
    url = normalize_url(url)
    slot_label = f"{index:>{len(str(total_urls))}}/{total_urls}"
    emit_message(f"[{slot_label}]▶️ Starting processing for: {url}")
    
    try:
        if args.extract_text:
            status, message = run_text_extraction_task(url)
            log_message(args.log_file, status, url, message)
            if status == "FAILURE":
                with failed_urls_lock:
                    failed_urls.append({'original_url': url, 'target_url': url, 'title': url, 'message': message})
            elif status == "SUCCESS":
                with success_urls_lock:
                    success_urls.append({'original_url': url, 'target_url': url, 'title': url, 'message': message})
            emit_message(f"[{slot_label}] {'✅' if status == 'SUCCESS' else '❌'} Finished: {url} :: {message}")
        else: # Download Mode
            tasks, collection_title = get_tasks_from_url(url)
            if not tasks:
                log_message(args.log_file, "SKIPPED", url, "No downloadable content found during discovery.")
                emit_message(f"[{slot_label}] ⏩ Skipped: {url} (No content found)")
                return

            is_playlist = len(tasks) > 1
            if is_playlist or args.get_links:
                # Save links to a file
                safe_title = sanitize_filename(collection_title or "Links")
                links_filename = f"{safe_title} - Links.txt"
                try:
                    with open(links_filename, "w", encoding="utf-8") as f:
                        for t in tasks:
                            f.write(f"{t[1]}\n") # t[1] is the target_url
                    emit_message(f"[{slot_label}] ✅ Saved {len(tasks)} link(s) to: {links_filename}")
                except Exception as e:
                    emit_message(f"[{slot_label}] ❌ Error saving links file: {e}")

            if args.get_links:
                emit_message(f"[{slot_label}] ℹ️ Link extraction mode: skipping downloads for {url}")
                return

            emit_message(f"[{slot_label}] Found {len(tasks)} item(s) to download.")

            for i, task in enumerate(tasks, 1):
                if ui_stop_event.is_set():
                    emit_message(f"[{slot_label}] ⚠️ Cancelled; skipping remaining items.")
                    return

                task_type, target_url, title, original_url, channel, upload_date, video_lang = task
                task_id = f"{index}:{i}:{int(time.time() * 1000)}"
                status, message, t_paths = run_download_task(task_type, target_url, title, args, original_url, task_id=task_id, slot_label=slot_label, channel=channel, upload_date=upload_date, video_lang=video_lang)
                log_message(args.log_file, status, original_url, message)
                if status == "FAILURE":
                    with failed_urls_lock:
                        failed_urls.append({'original_url': original_url, 'target_url': target_url, 'title': title, 'message': message})
                elif status == "SUCCESS":
                    with success_urls_lock:
                        success_urls.append({'original_url': original_url, 'target_url': target_url, 'title': title, 'message': message, 'transcript_paths': t_paths, 'channel': channel, 'upload_date': upload_date})
                emit_message(f"[{slot_label} #{i}/{len(tasks)}] {'✅' if status == 'SUCCESS' else '❌'} {message}")
            
            emit_message(f"[{slot_label}] ✅ Finished processing URL: {url}")
            
    except Exception as e:
        message = f"An unexpected error occurred: {e}"
        log_message(args.log_file, "CRITICAL FAILURE", url, message)
        with failed_urls_lock:
            failed_urls.append({'original_url': url, 'target_url': url, 'title': url, 'message': message})
        emit_message(f"[{slot_label}] ❌ CRITICAL FAILURE for {url} :: {message}")

def combine_all_transcripts(success_list):
    """Combines all downloaded transcripts into a single Markdown file."""
    # Determine dynamic filename based on channel and latest date
    channels = [item.get('channel') for item in success_list if item.get('transcript_paths') and item.get('channel')]
    dates = [item.get('upload_date') for item in success_list if item.get('transcript_paths') and item.get('upload_date')]
    
    main_channel = "Combined"
    if channels:
        # Use the most frequent channel name
        main_channel = max(set(channels), key=channels.count)
    
    latest_date = ""
    if dates:
        latest_date = max(dates)
        if latest_date == "00000000":
            latest_date = datetime.datetime.now().strftime('%Y%m%d')
    else:
        latest_date = datetime.datetime.now().strftime('%Y%m%d')
        
    safe_channel = sanitize_filename(main_channel)
    output_file = f"{safe_channel} - {latest_date}.md"
    
    emit_message(f"--- 📝 Combining transcripts into {output_file} ---")
    
    combined_content = ["# Combined Transcripts\n"]
    found_any = False
    
    for item in success_list:
        paths = item.get('transcript_paths', [])
        if not paths:
            continue
        
        title = item.get('title', 'Untitled')
        url = item.get('target_url', 'Unknown URL')
        
        for path in paths:
            if not os.path.exists(path):
                continue
            
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                
                if content:
                    combined_content.append(f"## [{title}]({url})\n")
                    combined_content.append(f"File: `{os.path.basename(path)}`\n\n")
                    combined_content.append(content)
                    combined_content.append("\n\n---\n")
                    found_any = True
            except Exception as e:
                emit_message(f"  ❌ Error reading {path}: {e}")
                
    if not found_any:
        emit_message("  ⚠️ No transcript content found to combine.")
        return

    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("\n".join(combined_content))
        emit_message(f"  ✅ Successfully created {output_file}")
    except Exception as e:
        emit_message(f"  ❌ Error writing {output_file}: {e}")

def signal_handler(sig, frame):
    """Handles Ctrl-C by immediately terminating all child processes and exiting."""
    # Set the stop event first to stop any new tasks
    ui_stop_event.set()
    if 'executor' in globals() and executor:
        executor.shutdown(wait=False, cancel_futures=True)

    # Immediately signal the UI to stop without waiting
    stop_live_ui(immediate=True)
    
    try:
        print("\n\n⚠️ Ctrl-C detected! Terminating all processes...", flush=True)
    except Exception:
        pass
    
    # Kill all running child processes immediately
    terminate_running_processes()
    
    # Exit immediately to avoid hanging on thread joins or other locks
    os._exit(1)

def main():
    global executor
    parser = argparse.ArgumentParser(
        description="A robust, parallel tool for downloading media or extracting text using yt-dlp and gallery-dl.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    
    mode_group = parser.add_argument_group('Script Mode')
    mode_group.add_argument("-U", "--update", action="store_true", help="Switches to Update Mode. Updates dependencies and exits.")
    mode_group.add_argument("-E", "--extract-text", action="store_true", help="Switches to Text Extraction Mode. Extracts text to a .txt file.")
    
    input_group = parser.add_argument_group('URL Input (Required unless updating)')
    input_group.add_argument("inputs", nargs='*', default=[], help="One or more URLs or paths to text files containing URLs.")
    
    general_group = parser.add_argument_group('General Options')
    general_group.add_argument("-L", "--log", action="store_true", help="Enable saving a verbose, timestamped log to processing_log.txt.")
    general_group.add_argument("--log-file", type=str, default=None, help="File to save a verbose, timestamped log (implies --log).")
    general_group.add_argument("-oE", "--output-errors", type=str, default="errors.txt", help="File to save the clean list of URLs that failed (default: errors.txt).")
    general_group.add_argument("-gl", "--get-links", action="store_true", help="Extract and save all video links to a text file and exit (skip download).")
    general_group.add_argument("-V", "--verbose", action="store_true", help="Show all underlying output for debugging.")
    general_group.add_argument("--no-live-ui", action="store_true", help="Disable dynamic terminal status UI and use plain scrolling logs.")
    general_group.add_argument("-F", "--individual-folder", action="store_true", help="Download each item into its own individual folder.")
    
    ytdlp_group = parser.add_argument_group('yt-dlp Options (for video content in Download Mode)')
    ytdlp_group.add_argument("-v", "--video", action="store_true", help="Download video (MP4).")
    ytdlp_group.add_argument("-a", "--audio-only", dest="audio_only", action="store_true", help="Download audio-only (MP3).")
    ytdlp_group.add_argument("-s", "--srt", action="store_true", help="Download subtitles and generate plaintext transcript files.")
    ytdlp_group.add_argument("-t", "--thumbnail", action="store_true", help="Download video thumbnail.")
    ytdlp_group.add_argument("-d", "--description", action="store_true", help="Download video description (.description).")
    ytdlp_group.add_argument("-m", "--metadata", action="store_true", help="Download video metadata (.json).")
    ytdlp_group.add_argument("-C", "--comments", action="store_true", help="Download video comments into the metadata file.")
    ytdlp_group.add_argument("-l", "--language", type=str, help="Language code for audio/subs (e.g., 'id', 'es').")
    ytdlp_group.add_argument("-j", "--json3", action="store_true", help="Download json3 subtitles (word-level timing).")
    ytdlp_group.add_argument("-c", "--combine-transcripts", action="store_true", help="Combine all downloaded transcripts into a single .md file.")
    
    gallerydl_group = parser.add_argument_group('gallery-dl Options (for image content in Download Mode)')
    gallerydl_group.add_argument("-gD", "--g-directory", type=str, help="Output directory for downloaded images.")
    gallerydl_group.add_argument("-gA", "--g-archive", type=str, help="Record downloads in an archive file to skip them later.")
    gallerydl_group.add_argument("-gN", "--g-no-skip", action="store_true", help="Do not skip downloads; re-download everything.")
    gallerydl_group.add_argument("-gM", "--g-write-metadata", action="store_true", help="Write metadata to a .json file (default).")
    gallerydl_group.add_argument("-gO", "--g-options", type=str, help="Raw string of additional options for gallery-dl (e.g., \"--zip\").")
    
    args = parser.parse_args()

    # Resolve log_file path: --log-file takes precedence, otherwise if -L/--log is specified, use processing_log.txt
    if args.log_file:
        pass
    elif args.log:
        args.log_file = "processing_log.txt"
    else:
        args.log_file = None

    if args.update:
        run_updates()

    if not args.inputs:
        parser.error("At least one input (URL or file path) is required for this mode.")

    signal.signal(signal.SIGINT, signal_handler)

    urls_to_process = []
    for item in args.inputs:
        if os.path.isfile(item):
            try:
                with open(item, 'r', encoding='utf-8') as f:
                    urls_to_process.extend([line.strip() for line in f if line.strip() and not line.strip().startswith(('#', ';', ']'))])
            except Exception as e:
                emit_message(f"❌ Error reading batch file '{item}': {e}")
        else:
            urls_to_process.append(item)
    
    if not urls_to_process:
        emit_message("❌ No valid URLs were found from the provided inputs. Exiting.")
        sys.exit(1)
    
    is_any_specific_flag = any([
        args.video, args.audio_only, args.srt, args.thumbnail, args.description,
        args.metadata, args.comments, args.g_write_metadata, args.json3,
        args.combine_transcripts
    ])
    args.default_download = not is_any_specific_flag
    
    # If combine-transcripts is set, implicitly enable srt/subtitles if no other mode is set
    if args.combine_transcripts and not any([args.video, args.audio_only, args.srt, args.json3]):
        args.srt = True
    
    start_live_ui(len(urls_to_process), args)
    emit_message(f"✅ Starting processing for {len(urls_to_process)} URLs with {PARALLEL_DOWNLOADS} parallel workers...")

    with ThreadPoolExecutor(max_workers=PARALLEL_DOWNLOADS) as exec:
        executor = exec
        future_to_url = {exec.submit(process_url, url, i, len(urls_to_process), args): url 
                         for i, url in enumerate(urls_to_process, 1)}

        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                future.result()
            except KeyboardInterrupt:
                signal_handler(None, None)
            except Exception as exc:
                message = f"A critical error occurred while processing {url}: {exc}"
                log_message(args.log_file, "CRITICAL FAILURE", url, message)
                with failed_urls_lock:
                    failed_urls.append({'original_url': url, 'target_url': url, 'title': url, 'message': message})
                emit_message(message)

    stop_live_ui()
    
    if args.combine_transcripts:
        combine_all_transcripts(success_urls)
        
    print("--- All tasks completed ---")
    
    if success_urls:
        with print_lock:
            print("\n" + "="*80)
            print("[SUCCESS] SUCCESSFUL TASKS SUMMARY")
            print("="*80)
            for succ in success_urls:
                print(f"- Title: {succ.get('title', 'Unknown')}")
                print(f"  URL:   {succ.get('target_url', 'Unknown')}")
                msg = succ.get('message', 'Completed')
                print(f"  Info:  {msg}\n")
            print("="*80 + "\n")
            
        if args.log_file:
            try:
                with open(args.log_file, "a", encoding="utf-8") as f:
                    f.write("\n" + "="*80 + "\n")
                    f.write("[SUCCESS] SUCCESSFUL TASKS SUMMARY\n")
                    f.write("="*80 + "\n")
                    for succ in success_urls:
                        f.write(f"- Title: {succ.get('title', 'Unknown')}\n")
                        f.write(f"  URL:   {succ.get('target_url', 'Unknown')}\n")
                        msg = succ.get('message', 'Completed')
                        f.write(f"  Info:  {msg}\n\n")
                    f.write("="*80 + "\n\n")
            except Exception as e:
                pass
    elif not failed_urls:
        with print_lock:
            print("\n" + "="*80)
            print(f"[SUCCESS] ALL {len(urls_to_process)} TASKS COMPLETED SUCCESSFULLY (No items processed)")
            print("="*80 + "\n")

    if failed_urls:
        with print_lock:
            print("\n" + "="*80)
            print("[FAILURE] FAILED TASKS SUMMARY")
            print("="*80)
            for fail in failed_urls:
                print(f"- Title: {fail.get('title', 'Unknown')}")
                print(f"  URL:   {fail.get('target_url', 'Unknown')}")
                print(f"  Error: {fail.get('message', 'Unknown Error')}\n")
            print("="*80 + "\n")
            
        if args.log_file:
            try:
                with open(args.log_file, "a", encoding="utf-8") as f:
                    f.write("\n" + "="*80 + "\n")
                    f.write("[FAILURE] FAILED TASKS SUMMARY\n")
                    f.write("="*80 + "\n")
                    for fail in failed_urls:
                        f.write(f"- Title: {fail.get('title', 'Unknown')}\n")
                        f.write(f"  URL:   {fail.get('target_url', 'Unknown')}\n")
                        f.write(f"  Error: {fail.get('message', 'Unknown Error')}\n\n")
                    f.write("="*80 + "\n\n")
            except Exception as e:
                pass

        unique_failed_target_urls = sorted(list(set(f.get('target_url', '') for f in failed_urls if f.get('target_url'))))
        print(f"- Writing {len(unique_failed_target_urls)} unique failed target URL(s) to '{args.output_errors}'...")
        with open(args.output_errors, "w", encoding="utf-8") as f:
            for u in unique_failed_target_urls:
                f.write(u + "\n")

if __name__ == "__main__":
    main()
