manager = resolve:GetProjectManager()
project = manager:GetCurrentProject()
timeline = project:GetCurrentTimeline()
markers = timeline:GetMarkers()
firstFrame = timeline:GetStartFrame()

mf = {}
for frame, marker in pairs(markers) do
    table.insert(mf, {frame, marker['name']})
end
table.insert(mf, {timeline:GetEndFrame(), "end"})

table.sort(mf, function (k1, k2) return k1[1] < k2[1] end)

for i = 1, #mf - 1 do
    startFrame = firstFrame + mf[i][1]
    endFrame = firstFrame + mf[i + 1][1] - 1

    isLastMarker = i == #mf - 1

    if isLastMarker then endFrame = mf[i + 1][1] end

    fileName = string.format("%02d-", i) .. mf[i][2]
    project:SetRenderSettings({
        ["SelectAllFrames"] = false,
        ["MarkIn"] = startFrame,
        ["MarkOut"] = endFrame,
        ["CustomName"] = fileName
    })
    print(string.format("Adding render job %s '%s' start frame %s end frame %s", i, fileName, startFrame, endFrame))
    project:AddRenderJob()
end