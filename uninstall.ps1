Remove-Item 'HKCU:\Software\Microsoft\Edge\NativeMessagingHosts\com.streamtopc.host' -ErrorAction SilentlyContinue
Remove-Item (Join-Path $env:LOCALAPPDATA 'StreamToPC') -Recurse -Force -ErrorAction SilentlyContinue
Write-Host "Removed."
