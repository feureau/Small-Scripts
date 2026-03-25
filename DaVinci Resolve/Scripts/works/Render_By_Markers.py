####### CUSTOM PARAMETERS ########
marker_filter = 'all'         # 'all' renders all markers regardless of color
render_preset_name = ''       # Optional: Name of your render preset (leave blank to use current Deliver settings)
filename_prefix = ''          # Optional: Add text before each file name (e.g. 'Scene_01_')
#################################

# Access DaVinci Resolve API
resolve = bmd.scriptapp("Resolve")
pm = resolve.GetProjectManager()
project = pm.GetCurrentProject()
timeline = project.GetCurrentTimeline()

if not project or not timeline:
    print("❌ No active project or timeline found. Open a project and timeline first.")
    quit()

# Load preset if specified
if render_preset_name:
    success = project.LoadRenderPreset(render_preset_name)
    if success:
        print(f"✅ Loaded render preset: {render_preset_name}")
    else:
        print(f"⚠️ Could not find render preset '{render_preset_name}'. Using current Deliver settings.")
else:
    print("ℹ️ No render preset specified. Using current Deliver settings.")

# Get timeline markers
markers = timeline.GetMarkers()
if not markers:
    print("❌ No markers found on the current timeline.")
    quit()

# Sort markers by frame position
sorted_marker_frames = sorted(markers.keys())

timeline_start = timeline.GetStartFrame()
timeline_end = timeline.GetEndFrame()
render_count = 0

# Function to create render job
def renderjob_create(vfx_name, start_frame, end_frame):
    render_settings = {
        'CustomName': vfx_name,
        'MarkIn': start_frame,
        'MarkOut': end_frame
    }
    project.SetRenderSettings(render_settings)
    project.AddRenderJob()

# Iterate over markers in order
for i, marker_frame in enumerate(sorted_marker_frames):
    marker_data = markers[marker_frame]
    marker_color = marker_data['color']

    if marker_filter.lower() == 'all' or marker_color.lower() == marker_filter.lower():
        marker_name = marker_data['name'] or f"Marker_{marker_frame}"

        # Start frame = this marker
        start_frame = marker_frame + timeline_start

        # End frame = next marker - 1, or timeline end if this is the last marker
        if i < len(sorted_marker_frames) - 1:
            next_marker_frame = sorted_marker_frames[i + 1] + timeline_start
            end_frame = next_marker_frame - 1
        else:
            end_frame = timeline_end

        job_name = f"{filename_prefix}{marker_name}"
        print(f"🟢 Adding '{job_name}' to Render Queue | Frames: {start_frame}-{end_frame}")
        renderjob_create(job_name, start_frame, end_frame)
        render_count += 1

if render_count == 0:
    print(f"⚠️ No markers matched filter '{marker_filter}'. No jobs added.")
else:
    print(f"✅ {render_count} render jobs added to the Render Queue.")
    print("ℹ️ Rendering NOT started automatically. Start it manually in the Deliver page.")
