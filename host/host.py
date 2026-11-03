"""Stream to PC - native messaging host + download worker (Windows).
Modes:
  (no args)            -> native messaging host, talks to the Edge extension
  --download job.json  -> download worker (runs in its own console window)
"""
import sys, os, json, struct, subprocess, shutil, tempfile, re, urllib.request, uuid

DEFAULT_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36 Edg/124.0"
EXTRA = {
    "mpv": [r"C:\Program Files\mpv\mpv.exe", r"C:\Program Files (x86)\mpv\mpv.exe", os.path.expandvars(r"%LOCALAPPDATA%\Programs\mpv\mpv.exe")],
    "vlc": [r"C:\Program Files\VideoLAN\VLC\vlc.exe", r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe"],
    "yt-dlp": [os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Links\yt-dlp.exe")],
    "ffmpeg": [os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Links\ffmpeg.exe")],
}

def find_tool(name):
    p = shutil.which(name)
    if p: return p
    for c in EXTRA.get(name, []):
        if os.path.isfile(c): return c
    return None

def sanitize(s):
    s = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", s or "video").strip(" .")
    return s[:120] or "video"

def req_headers(m, h):
    out = {"User-Agent": h.get("ua") or DEFAULT_UA}
    ref = h.get("referer") or m.get("pageUrl")
    if ref: out["Referer"] = ref
    if h.get("origin"): out["Origin"] = h["origin"]
    if h.get("cookie"): out["Cookie"] = h["cookie"]
    return out

def fetch(url, headers, dest):
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r, open(dest, "wb") as f:
        shutil.copyfileobj(r, f)

# ---------- native messaging io ----------
def read_msg():
    raw = sys.stdin.buffer.read(4)
    if len(raw) < 4: return None
    n = struct.unpack("<I", raw)[0]
    return json.loads(sys.stdin.buffer.read(n).decode("utf-8"))

def send_msg(obj):
    data = json.dumps(obj).encode("utf-8")
    sys.stdout.buffer.write(struct.pack("<I", len(data)) + data)
    sys.stdout.buffer.flush()

def spawn_detached(cmd, console=False):
    flags = 0x00000010 if console else (0x00000008 | 0x00000200)  # NEW_CONSOLE | DETACHED+NEW_GROUP
    subprocess.Popen(cmd, creationflags=flags, stdin=subprocess.DEVNULL,
                     stdout=None if console else subprocess.DEVNULL,
                     stderr=None if console else subprocess.DEVNULL, close_fds=True)

# ---------- play ----------
def cookie_opts(m):
    """yt-dlp option list for cookies (login / age-restricted)."""
    if m.get("cookiesFile") and os.path.isfile(m["cookiesFile"]):
        return ["--cookies", m["cookiesFile"]]
    if m.get("cookiesBrowser"):
        return ["--cookies-from-browser", "edge"]
    return []

def play_page(m):
    exe = m.get("playerPath") if (m.get("player") or "mpv") == "mpv" and m.get("playerPath") else find_tool("mpv")
    if (m.get("player") or "mpv") != "mpv":
        return {"ok": False, "message": "Page URL play-er jonno Settings-e player 'mpv' select koro (VLC page URL bujhe na)."}
    if not exe or not os.path.isfile(exe):
        return {"ok": False, "message": "mpv not found. Install mpv or set the path in Settings."}
    raw = ["write-subs=", "sub-langs=all"]
    if m.get("cookiesFile") and os.path.isfile(m["cookiesFile"]):
        raw.append("cookies=" + m["cookiesFile"])
    elif m.get("cookiesBrowser"):
        raw.append("cookies-from-browser=edge")
    cmd = [exe, "--ytdl=yes", "--ytdl-format=bestvideo+bestaudio/best", "--ytdl-raw-options=" + ",".join(raw)]
    yt = find_tool("yt-dlp")
    if yt: cmd.append("--script-opts=ytdl_hook-ytdl_path=" + yt)
    cmd += ["--", m["url"]]
    spawn_detached(cmd)
    return {"ok": True, "message": "Opened in mpv (yt-dlp diye extract hocche, ektu soman lagte pare)"}

def play(m):
    if m.get("mode") == "page":
        return play_page(m)
    h = m.get("headers") or {}
    hd = req_headers(m, h)
    title = m.get("title") or "video"
    player = (m.get("player") or "mpv").lower()
    exe = m.get("playerPath") or (find_tool("vlc") if player == "vlc" else find_tool("mpv"))
    if not exe or not os.path.isfile(exe):
        return {"ok": False, "message": "Player not found. Install mpv/VLC or set the path in Settings."}
    if player == "vlc":
        cmd = [exe, "--http-user-agent=" + hd["User-Agent"]]
        if "Referer" in hd: cmd.append("--http-referrer=" + hd["Referer"])
        subs = m.get("subs") or []
        if subs:
            tmp = os.path.join(tempfile.gettempdir(), "stp_" + uuid.uuid4().hex[:6])
            os.makedirs(tmp, exist_ok=True)
            s = subs[0]
            ext = os.path.splitext(s["url"].split("?")[0])[1] or ".vtt"
            dest = os.path.join(tmp, sanitize(s.get("label", "sub")) + ext)
            try:
                fetch(s["url"], {**hd, **req_headers(m, s.get("headers") or {})}, dest)
                cmd.append("--sub-file=" + dest)
            except Exception: pass
        cmd.append(m["url"])
    elif player == "custom":
        cmd = [exe, m["url"]]
    else:
        cmd = [exe, "--ytdl=no", "--force-media-title=" + title, "--user-agent=" + hd["User-Agent"]]
        if "Referer" in hd: cmd.append("--referrer=" + hd["Referer"])
        for k in ("Origin", "Cookie"):
            if k in hd: cmd.append("--http-header-fields-append=%s: %s" % (k, hd[k]))
        for s in m.get("subs") or []:
            cmd.append("--sub-file=" + s["url"])
        cmd += ["--", m["url"]]
    spawn_detached(cmd)
    return {"ok": True, "message": "Opened in " + player}

# ---------- download ----------
def download(m):
    job = os.path.join(tempfile.gettempdir(), "stp_job_%s.json" % uuid.uuid4().hex[:8])
    with open(job, "w", encoding="utf-8") as f: json.dump(m, f)
    me = [sys.executable] if getattr(sys, "frozen", False) else [sys.executable, os.path.abspath(__file__)]
    spawn_detached(me + ["--download", job], console=True)
    return {"ok": True, "message": "Download started (console window dekho)"}

def worker(jobfile):
    m = json.load(open(jobfile, encoding="utf-8"))
    h = m.get("headers") or {}
    hd = req_headers(m, h)
    ytdlp, ffmpeg = find_tool("yt-dlp"), find_tool("ffmpeg")
    if not ytdlp:
        print("yt-dlp not found. Install: winget install yt-dlp.yt-dlp"); os.system("pause"); return
    if not ffmpeg:
        print("WARNING: ffmpeg not found (needed to merge video+audio). Install: winget install Gyan.FFmpeg")
    outdir = m.get("downloadDir") or os.path.join(os.path.expanduser("~"), "Videos", "StreamToPC")
    os.makedirs(outdir, exist_ok=True)
    page = m.get("mode") == "page"
    title = sanitize(m.get("title"))
    pathfile = os.path.join(tempfile.gettempdir(), "stp_path_%s.txt" % uuid.uuid4().hex[:6])
    cmd = [ytdlp, m["url"], "--no-playlist", "-f", "bv*+ba/b", "--merge-output-format", "mkv",
           "--write-subs", "--sub-langs", "all,-live_chat", "--embed-subs",
           "--concurrent-fragments", "8", "--user-agent", hd["User-Agent"],
           "-o", os.path.join(outdir, ("%(title).150B [%(id)s]" if page else title) + ".%(ext)s"),
           "--print-to-file", "after_move:filepath", pathfile]
    if not page:
        if "Referer" in hd: cmd += ["--referer", hd["Referer"]]
        for k in ("Origin", "Cookie"):
            if k in hd: cmd += ["--add-header", "%s:%s" % (k, hd[k])]
    cmd += cookie_opts(m)
    if ffmpeg: cmd += ["--ffmpeg-location", ffmpeg]
    print("Downloading best quality:", m["url"], "\n")
    rc = subprocess.call(cmd)
    # external subtitle files found on the page -> saved next to the video as .srt
    for i, s in enumerate([] if page else (m.get("subs") or [])):
        try:
            ext = os.path.splitext(s["url"].split("?")[0])[1] or ".vtt"
            base = os.path.join(outdir, "%s.%s" % (title, sanitize(s.get("label") or "sub%d" % (i + 1))))
            raw = base + ext
            fetch(s["url"], {**hd, **req_headers(m, s.get("headers") or {})}, raw)
            if ffmpeg and ext.lower() != ".srt":
                if subprocess.call([ffmpeg, "-y", "-loglevel", "error", "-i", raw, base + ".srt"]) == 0:
                    os.remove(raw)
            print("Subtitle saved:", base)
        except Exception as e:
            print("Subtitle failed:", e)
    print("\nDONE" if rc == 0 else "\nyt-dlp exit code %d (DRM / expired link / login lagte pare). Try: yt-dlp -U  ar  winget install DenoLand.Deno (YouTube-er jonno)" % rc)
    print("Folder:", outdir)
    os.system("pause")

def main():
    if len(sys.argv) > 2 and sys.argv[1] == "--download":
        return worker(sys.argv[2])
    if os.name == "nt":
        import msvcrt
        msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY); msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    m = read_msg()
    if not m: return
    try:
        r = play(m) if m.get("action") == "play" else download(m) if m.get("action") == "download" else {"ok": False, "message": "unknown action"}
    except Exception as e:
        r = {"ok": False, "message": "Error: %s" % e}
    send_msg(r)

if __name__ == "__main__":
    main()
