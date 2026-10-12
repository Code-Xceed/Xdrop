const SERVICE_URL = "http://127.0.0.1:8484";

document.addEventListener("DOMContentLoaded", async () => {
  const statusEl = document.getElementById("status");
  const urlEl = document.getElementById("url");
  const sendBtn = document.getElementById("send-btn");
  const feedbackEl = document.getElementById("feedback");
  const formatEl = document.getElementById("format");

  // Check backend health
  try {
    const res = await fetch(`${SERVICE_URL}/api/health`);
    if (res.ok) {
      statusEl.textContent = "Engine Connected";
      statusEl.classList.remove("offline");
    } else {
      throw new Error();
    }
  } catch (_) {
    statusEl.textContent = "Engine Offline";
    statusEl.classList.add("offline");
  }

  // Populate active tab URL if available
  if (chrome.tabs && chrome.tabs.query) {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs && tabs[0] && tabs[0].url && tabs[0].url.startsWith("http")) {
        urlEl.value = tabs[0].url;
      }
    });
  }

  sendBtn.addEventListener("click", async () => {
    const url = urlEl.value.trim();
    if (!url) {
      feedbackEl.textContent = "Please enter a valid URL.";
      feedbackEl.style.color = "#ef4444";
      return;
    }

    sendBtn.disabled = true;
    feedbackEl.textContent = "Sending to editor...";
    feedbackEl.style.color = "#00e5ff";

    const preset = formatEl.value;
    const isAudio = preset.startsWith("audio_");
    const isProres = preset === "prores_master";

    try {
      const res = await fetch(`${SERVICE_URL}/api/download`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url: url,
          quality: isProres ? "best" : "1080p",
          format: isAudio ? (preset === "audio_wav" ? "wav" : "mp3") : (isProres ? "mov" : "mp4"),
          extractAudio: isAudio,
          autoImport: true
        })
      });

      if (res.ok) {
        feedbackEl.textContent = "Sent! Clip importing to active NLE.";
        feedbackEl.style.color = "#22c55e";
        setTimeout(() => window.close(), 1500);
      } else {
        const data = await res.json().catch(() => ({}));
        feedbackEl.textContent = data.detail || "Error queueing download.";
        feedbackEl.style.color = "#ef4444";
        sendBtn.disabled = false;
      }
    } catch (_) {
      feedbackEl.textContent = "Could not contact Xdrop engine (port 8484).";
      feedbackEl.style.color = "#ef4444";
      sendBtn.disabled = false;
    }
  });
});
