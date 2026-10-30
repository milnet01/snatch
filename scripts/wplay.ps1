$ErrorActionPreference = "Continue"
Set-Location C:\snatch-test
Get-Process snatch,mpv -ErrorAction SilentlyContinue | Stop-Process -Force
Get-ChildItem $env:TEMP -Filter _MEI* -Directory -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Start-Sleep 2

$p = Start-Process -FilePath .\snatch.exe -PassThru
Start-Sleep -Seconds 30
if ($p.HasExited) { Write-Output ("EXITED code=" + $p.ExitCode); exit }
Write-Output "STARTUP: OK"

$mei = Get-ChildItem $env:TEMP -Filter _MEI* -Directory -ErrorAction SilentlyContinue |
       Sort-Object LastWriteTime -Descending | Select-Object -First 1
$bin = Join-Path $mei.FullName "bin"
Write-Output "--- bundled tools ---"
foreach ($rel in @("mpv\mpv.exe","qjs.exe","yt-dlp.exe","ffmpeg.exe")) {
  $path = Join-Path $bin $rel
  if (-not (Test-Path $path)) { Write-Output ("{0,-14} MISSING" -f $rel); continue }
  if ($rel -like "*yt-dlp*") { $a="--version" } elseif ($rel -like "*mpv*") { $a="--version" } else { $a="-version" }
  Write-Output ("{0,-14} -> {1}" -f $rel, (& $path $a 2>&1 | Select-Object -First 1))
}

Write-Output "--- REAL PLAYBACK TEST: bundled mpv + bundled yt-dlp ---"
$mpv = Join-Path $bin "mpv\mpv.exe"
$ytdlp = Join-Path $bin "yt-dlp.exe"
$out = & $mpv --no-config --vo=null --ao=null --frames=1 "--script-opts=ytdl_hook-ytdl_path=$ytdlp" -- "https://www.youtube.com/watch?v=CwI42wfyvw8" 2>&1 | Out-String
if ($out -match "Errors when loading file") { Write-Output "PLAYBACK: FAILED" ; ($out -split "`n" | Select-String -Pattern "error|403" | Select-Object -First 3) }
elseif ($out -match "AV: ") { Write-Output "PLAYBACK: PLAYS" }
else { Write-Output "PLAYBACK: unclear"; ($out -split "`n" | Select-Object -Last 4) }

Get-Process snatch,mpv -ErrorAction SilentlyContinue | Stop-Process -Force
