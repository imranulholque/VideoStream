# Usage: .\install.ps1 -ExtensionId <id from edge://extensions> [-InstallDeps]
param([Parameter(Mandatory=$true)][string]$ExtensionId, [switch]$InstallDeps)
$ErrorActionPreference = 'Stop'
$src  = $PSScriptRoot
$dest = Join-Path $env:LOCALAPPDATA 'StreamToPC'
New-Item -ItemType Directory -Force $dest | Out-Null

$exe = Join-Path $src 'streamtopc-host.exe'
if (Test-Path $exe) {
  Copy-Item $exe $dest -Force
  $hostPath = Join-Path $dest 'streamtopc-host.exe'
} else {
  $py = Join-Path $src 'host\host.py'
  if (-not (Test-Path $py)) { throw 'host.py / streamtopc-host.exe not found' }
  Copy-Item $py $dest -Force
  Set-Content (Join-Path $dest 'host.bat') "@echo off`r`npython `"%~dp0host.py`" %*" -Encoding ASCII
  $hostPath = Join-Path $dest 'host.bat'
}

$manifest = [ordered]@{
  name = 'com.streamtopc.host'; description = 'Stream to PC helper'
  path = $hostPath; type = 'stdio'
  allowed_origins = @("chrome-extension://$ExtensionId/")
}
$mf = Join-Path $dest 'com.streamtopc.host.json'
$manifest | ConvertTo-Json | Set-Content $mf -Encoding ASCII
New-Item -Path 'HKCU:\Software\Microsoft\Edge\NativeMessagingHosts\com.streamtopc.host' -Value $mf -Force | Out-Null
Write-Host "Installed. Edge restart koro."

if ($InstallDeps) {
  foreach ($id in 'yt-dlp.yt-dlp','Gyan.FFmpeg','VideoLAN.VLC') { winget install --id $id -e --accept-package-agreements --accept-source-agreements }
  Write-Host "mpv chaile manually nao: https://mpv.io/installation/ (ba: winget search mpv)"
}
