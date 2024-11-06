#!/usr/bin/env python3
import os
import glob

# Create list of all .mp4 files in current working directory.
files = list(filter(os.path.isfile, glob.glob(os.path.join(os.getcwd(), '*.mp4'))))
files.sort(key=lambda x: os.path.getctime(x))

# Write list to text file that ffmpeg reads next.
with open('files.txt', 'w') as output:
    for file in files:
        output.write("file '" + file + "'\n")

# Run ffmpeg to concatenate the .mp4 files.
os.system('ffmpeg -f concat -safe 0 -i files.txt merged.mp4')

# Delete the text file.
os.remove('files.txt')