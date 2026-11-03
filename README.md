# Stream to PC (Microsoft Edge)

Edge-e jekono page-e video play korle extension stream URL (m3u8 / mpd / mp4 / webm) ar subtitle (vtt / srt / ass) detect kore.
Popup theke: **Play** (mpv / VLC) ba **Download** (best resolution + subtitles, yt-dlp diye).

## Install (release zip)
1. GitHub Releases / Actions artifact theke `stream-to-pc-windows.zip` nao, extract koro.
2. `edge://extensions` -> Developer mode ON -> **Load unpacked** -> `extension` folder.
3. Extension-er **ID** copy koro.
4. PowerShell: `.\install.ps1 -ExtensionId <ID> -InstallDeps`  (yt-dlp, ffmpeg, VLC install kore; mpv alada)
5. Edge restart.

## Build from source
Push to GitHub -> Actions `build` workflow `host.py` ke exe banay ar zip toiri kore. Tag `v1.0.0` push korle Release-e upload hoy.
(Exe chara chalate chaile Python install thakle `install.ps1` `host.bat` diye kaj chalabe.)

## Kon site-e kaj kore
- **"This page" (Page URL):** YouTube, Vimeo, X/Twitter, Facebook, Twitch, Dailymotion, Reddit ... 1000+ site. yt-dlp nije video khuje ber kore, tai sniff lage na. Play = mpv, Download = best quality + subtitles (.mkv).
- **"Detected streams":** onno jekono site-er direct m3u8/mpd/mp4 (yt-dlp na bujhle eta kaj kore).
- Login/age-restricted video: Settings-e *Use Edge cookies* ba `cookies.txt` path dao. (Notun Edge-e cookie-DB encrypted/locked thakle `cookies.txt` beshi reliable.)
- Site bodlale: `yt-dlp -U` chalao. YouTube-er jonno Deno lage (`winget install DenoLand.Deno`).

## Notes
- DRM-protected stream (Netflix, Prime, Disney+ etc. - Widevine) kaj korbe na; ei tool DRM bypass kore na.
- Page-er vitore subtitle HLS/DASH manifest-e thakle yt-dlp auto embed kore (mkv). Alada vtt/srt file thakle video-r pashe `.srt` hishebe save hoy.
- Link expire/token thakle download fail korte pare — tokhon page-e video abar play kore try koro.
- Segment (`.mp4` chunk) o kokhono list-e ashte pare; main/lomba URL (`.m3u8`/`.mpd`) ta select koro.
