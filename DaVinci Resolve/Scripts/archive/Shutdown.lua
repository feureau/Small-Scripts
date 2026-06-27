manager = resolve:GetProjectManager()
manager:SaveProject()
strProgram = '"C:\\Windows\\System32\\shutdown.exe" /s /t 00'
os.execute(strProgram)