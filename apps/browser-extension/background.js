/**
 * Xdrop Browser Companion Extension — Background Service Worker
 * Listens for context menu events and sends media directly to Xdrop engine.
 */

const SERVICE_URL = "http://127.0.0.1:8484";

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "xdrop-send-media",
    title: "Send to Xdrop (Active Editor)",
    contexts: ["page", "link", "video", "audio"]
  });
});

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId !== "xdrop-send-media") return;

  const targetUrl = info.linkUrl || info.srcUrl || info.pageUrl || (tab && tab.url);
  if (!targetUrl) return;

  try {
    const res = await fetch(`${SERVICE_URL}/api/download`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        url: targetUrl,
        quality: "best",
        format: "mp4",
        extractAudio: false,
        autoImport: true
      })
    });

    if (res.ok) {
      chrome.action.setBadgeText({ text: "OK", tabId: tab?.id });
      chrome.action.setBadgeBackgroundColor({ color: "#22c55e" });
      setTimeout(() => chrome.action.setBadgeText({ text: "", tabId: tab?.id }), 3000);
    } else {
      chrome.action.setBadgeText({ text: "ERR", tabId: tab?.id });
      chrome.action.setBadgeBackgroundColor({ color: "#ef4444" });
      setTimeout(() => chrome.action.setBadgeText({ text: "", tabId: tab?.id }), 4000);
    }
  } catch (err) {
    chrome.action.setBadgeText({ text: "OFF", tabId: tab?.id });
    chrome.action.setBadgeBackgroundColor({ color: "#71717a" });
    setTimeout(() => chrome.action.setBadgeText({ text: "", tabId: tab?.id }), 4000);
  }
});
