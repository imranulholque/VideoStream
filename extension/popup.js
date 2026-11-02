const HOST = "com.streamtopc.host";
const defaults = { player: "mpv", playerPath: "", downloadDir: "" };
const $ = s => document.querySelector(s);
const status = t => { $("#status").textContent = t; };
let tab, vids = [], subs = [];

const getSettings = async () => ({ ...defaults, ...(await chrome.storage.local.get(defaults)) });

function typeOf(url) {
  const m = url.match(/\.(m3u8|mpd|mp4|webm|mkv|m4v|mov)(?:$|[?#])/i);
  return m ? m[1].toLowerCase() : "stream";
}

async function send(action, video) {
  const s = await getSettings();
  const chosen = [...document.querySelectorAll(".subchk:checked")].map(c => subs[+c.dataset.i]);
  const msg = {
    action, url: video.url, title: tab.title || "video", pageUrl: tab.url, headers: video.headers,
    subs: chosen.map(x => ({ url: x.url, label: x.label, headers: x.headers })),
    player: s.player, playerPath: s.playerPath, downloadDir: s.downloadDir
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

async function init() {
  [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  const key = "t" + tab.id;
  const items = (await chrome.storage.session.get(key))[key] || [];
  vids = items.filter(i => i.kind === "video");
  subs = items.filter(i => i.kind === "sub");

  const vbox = $("#videos");
  if (!vids.length) { vbox.innerHTML = '<div class="empty">Kichu paoa jai nai. Video play kore abar dekho.</div>'; }
  vids.forEach(v => {
    const d = document.createElement("div"); d.className = "item";
    const t = document.createElement("span"); t.className = "type"; t.textContent = typeOf(v.url);
    const u = document.createElement("div"); u.className = "url"; u.textContent = v.url; u.title = v.url;
    d.append(t, u,
      btn("▶ Play", "", () => send("play", v)),
      btn("⬇ Download (best + subs)", "dl", () => send("download", v)),
      btn("Copy URL", "cp", () => navigator.clipboard.writeText(v.url).then(() => status("Copied"))));
    vbox.append(d);
  });

  const sbox = $("#subs");
  if (!subs.length) sbox.innerHTML = '<div class="empty">Alada subtitle file paoa jai nai (HLS-er vitore thakle download e auto ashbe).</div>';
  subs.forEach((s, i) => {
    const l = document.createElement("label"); l.className = "item";
    const c = document.createElement("input"); c.type = "checkbox"; c.className = "subchk"; c.dataset.i = i; c.checked = true;
    c.style.width = "auto";
    l.append(c, " " + s.label);
    sbox.append(l);
  });

  const s = await getSettings();
  for (const k of Object.keys(defaults)) {
    const el = $("#" + k); el.value = s[k];
    el.onchange = () => chrome.storage.local.set({ [k]: el.value });
  }
}
init();
