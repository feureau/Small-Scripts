import json
audio_streams = [{'index': 1, 'tags': {'language': 'ita'}}, {'index': 2, 'tags': {'language': 'eng'}}]
audio_maps_and_metadata = []
english_streams = []
other_streams = []
for s in audio_streams:
    tags = s.get('tags') or {}
    lang = tags.get('language', '').lower()
    if lang in ('eng', 'en', 'english'):
        english_streams.append(s)
    else:
        other_streams.append(s)
sorted_streams = english_streams + other_streams
for i, s in enumerate(sorted_streams):
    audio_maps_and_metadata.extend(['-map', f'0:{s["index"]}'])
    tags = s.get('tags') or {}
    lang = tags.get('language')
    if lang:
        audio_maps_and_metadata.extend([f'-metadata:s:a:{i}', f'language={lang}'])
    title = tags.get('title')
    if title:
        audio_maps_and_metadata.extend([f'-metadata:s:a:{i}', f'title={title}'])
    disp = 'default' if i == 0 else '0'
    audio_maps_and_metadata.extend([f'-disposition:s:a:{i}', disp])
command = ['ffmpeg', '-y', '-i', 'file', '-map', '0:v:0', '-c:v', 'copy'] + audio_maps_and_metadata + ['-c:a', 'aac_mf', '-b:a', '1536k'] + ['-ch_layout', '5.1'] + ['output.mp4']
print(' '.join(command))
