const HOST = "com.streamtopc.host";
const defaults = { player: "mpv", playerPath: "", downloadDir: "", cookiesBrowser: false, cookiesFile: "" };
const $ = s => document.querySelector(s);
const status = t => { $("#status").textContent = t; };
let tab, vids = [], subs = [];

const getSettings = async () => ({ ...defaults, ...(await chrome.storage.local.get(defaults)) });

function typeOf(url) {
  const m = url.match(/\.(m3u8|mpd|mp4|webm|mkv|m4v|mov)(?:$|[?#])/i);
  return m ? m[1].toLowerCase() : "stream";
}

// mode: "stream" (sniffed URL, direct) or "page" (page URL, yt-dlp extracts everything)
async function send(action, mode, url, headers) {
  const s = await getSettings();
  const chosen = mode === "stream"
    ? [...document.querySelectorAll(".subchk:checked")].map(c => subs[+c.dataset.i]) : [];
  const msg = {
    action, mode, url, title: tab.title || "video", pageUrl: tab.url, headers: headers || {},
    subs: chosen.map(x => ({ url: x.url, label: x.label, headers: x.headers })),
    player: s.player, playerPath: s.playerPath, downloadDir: s.downloadDir,
    cookiesBrowser: s.cookiesBrowser, cookiesFile: s.cookiesFile
  };
  status("Sending...");
  chrome.runtime.sendNativeMessage(HOST, msg, r => {
    if (chrome.runtime.lastError) status("Helper not installed? " + chrome.runtime.lastError.message);
    else status(r && r.message ? r.message : "Done");
  });
}

function btn(text, cls, fn) {
  const b = document.createElement("button");
  b.textContent = text; if (cls) b.className = cls; b.onclick = fn; return b;
}

function card(label, url, mode, headers) {
  const d = document.createElement("div"); d.className = "item";
  const t = document.createElement("span"); t.className = "type"; t.textContent = label;
  const u = document.createElement("div"); u.className = "url"; u.textContent = url; u.title = url;
  d.append(t, u,
    btn("▶ Play", "", () => send("play", mode, url, headers)),
    btn("⬇ Download (best + subs)", "dl", () => send("download", mode, url, headers)),
    btn("Copy URL", "cp", () => navigator.clipboard.writeText(url).then(() => status("Copied"))));
  return d;
}

async function init() {
  [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  const key = "t" + tab.id;
  const items = (await chrome.storage.session.get(key))[key] || [];
  vids = items.filter(i => i.kind === "video");
  subs = items.filter(i => i.kind === "sub");

  if (/^https?:/i.test(tab.url || "")) $("#page").append(card("page", tab.url, "page"));
  else $("#page").innerHTML = '<div class="empty">Ei tab-e page URL nei.</div>';

  const vbox = $("#videos");
  if (!vids.length) vbox.innerHTML = '<div class="empty">Kichu detect hoy nai (page URL option byabohar korte paro).</div>';
  vids.forEach(v => vbox.append(card(typeOf(v.url), v.url, "stream", v.headers)));

  const sbox = $("#subs");
  if (!subs.length) sbox.innerHTML = '<div class="empty">Alada subtitle file paoa jai nai.</div>';
  subs.forEach((s, i) => {
    const l = document.createElement("label"); l.className = "item";
    const c = document.createElement("input"); c.type = "checkbox"; c.className = "subchk"; c.dataset.i = i; c.checked = true;
    c.style.width = "auto";
    l.append(c, " " + s.label);
    sbox.append(l);
  });

  const s = await getSettings();
  for (const k of Object.keys(defaults)) {
    const el = $("#" + k);
    if (el.type === "checkbox") { el.checked = !!s[k]; el.onchange = () => chrome.storage.local.set({ [k]: el.checked }); }
    else { el.value = s[k]; el.onchange = () => chrome.storage.local.set({ [k]: el.value }); }
  }
}
init();
