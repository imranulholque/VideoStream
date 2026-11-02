// Detects video / subtitle requests per tab and stores them in storage.session
const VIDEO_RE = /\.(m3u8|mpd|mp4|webm|mkv|m4v|mov)(?:$|[?#])/i;
const SUB_RE = /\.(vtt|srt|ass|ssa|ttml|dfxp)(?:$|[?#])/i;
const CT_VIDEO = /mpegurl|dash\+xml|video\/(mp4|webm|x-matroska)/i;
const CT_SUB = /text\/vtt|x-subrip|ttml/i;

let queue = Promise.resolve();

function labelFor(url) {
  try {
    const seg = new URL(url).pathname.split("/").pop() || "sub";
    return decodeURIComponent(seg).replace(/\.[^.]+$/, "").slice(0, 60) || "sub";
  } catch { return "sub"; }
}

function add(tabId, item) {
  if (tabId < 0) return;
  queue = queue.then(async () => {
    const key = "t" + tabId;
    const list = (await chrome.storage.session.get(key))[key] || [];
    if (list.some(x => x.url === item.url)) return;
    list.push(item);
    await chrome.storage.session.set({ [key]: list });
    const n = list.filter(x => x.kind === "video").length;
    chrome.action.setBadgeText({ tabId, text: n ? String(n) : "" });
    chrome.action.setBadgeBackgroundColor({ tabId, color: "#0b7a3b" });
  }).catch(() => {});
}

function kindOf(url) {
  if (SUB_RE.test(url)) return "sub";
  if (VIDEO_RE.test(url)) return "video";
  return null;
}

function pick(headers) {
  const g = n => (headers.find(h => h.name.toLowerCase() === n) || {}).value || "";
  return { referer: g("referer"), origin: g("origin"), ua: g("user-agent"), cookie: g("cookie") };
}

// Real request headers (Referer, Cookie...) for URL-matched requests
chrome.webRequest.onSendHeaders.addListener(d => {
  const kind = kindOf(d.url);
  if (!kind) return;
  add(d.tabId, { url: d.url, kind, label: kind === "sub" ? labelFor(d.url) : "", headers: pick(d.requestHeaders || []), t: Date.now() });
}, { urls: ["<all_urls>"] }, ["requestHeaders", "extraHeaders"]);

// URLs without extension: detect by Content-Type
chrome.webRequest.onHeadersReceived.addListener(async d => {
  if (kindOf(d.url)) return;
  const ct = ((d.responseHeaders || []).find(h => h.name.toLowerCase() === "content-type") || {}).value || "";
  const kind = CT_SUB.test(ct) ? "sub" : CT_VIDEO.test(ct) ? "video" : null;
  if (!kind || d.tabId < 0) return;
  let tab; try { tab = await chrome.tabs.get(d.tabId); } catch { return; }
  add(d.tabId, { url: d.url, kind, label: kind === "sub" ? labelFor(d.url) : "", headers: { referer: tab.url || "", origin: "", ua: navigator.userAgent, cookie: "" }, t: Date.now() });
}, { urls: ["<all_urls>"] }, ["responseHeaders"]);

chrome.tabs.onUpdated.addListener((tabId, info) => {
  if (info.status === "loading" && info.url) {
    chrome.storage.session.remove("t" + tabId);
    chrome.action.setBadgeText({ tabId, text: "" });
  }
});
chrome.tabs.onRemoved.addListener(tabId => chrome.storage.session.remove("t" + tabId));
