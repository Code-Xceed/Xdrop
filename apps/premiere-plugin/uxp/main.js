/**
 * Xdrop UXP panel bootstrap.
 *
 * Keeps the plugin itself as thin as possible: the real interface is the Xdrop frontend
 * served by the local service and rendered inside the `<webview>`. This file only makes sure
 * the webview points at the right host and reports, in plain text, when the engine is not
 * running — because an empty webview with no explanation is the least useful failure mode.
 *
 * Deliberately dependency-free and defensive: UXP's runtime differs from a browser in ways
 * that are easy to get wrong, and the panel must never take the host application down.
 */

(function () {
  var SERVICE_URL = 'http://127.0.0.1:8484';
  var HEALTH_URL = SERVICE_URL + '/api/health';

  function setStatus(text, kind) {
    var status = document.getElementById('status');
    var label = document.getElementById('status-text');
    if (!status || !label) {
      return;
    }
    status.className = 'status status--' + kind;
    label.textContent = text;
  }

  function pointWebviewAtService() {
    var panel = document.getElementById('panel');
    if (!panel) {
      return;
    }
    var url = panel.getAttribute('data-service-url') || SERVICE_URL;
    // index.html already carries the ?host= parameter baked in at package time; only fall
    // back to the bare URL if it is somehow missing.
    panel.setAttribute('src', panel.getAttribute('src') || url);
  }

  function probeEngine() {
    if (typeof fetch !== 'function') {
      setStatus('Xdrop engine status unknown in this runtime.', 'unknown');
      return;
    }

    fetch(HEALTH_URL, { method: 'GET' })
      .then(function (response) {
        if (response && response.ok) {
          setStatus('Connected to the Xdrop engine.', 'online');
        } else {
          setStatus('Xdrop engine answered unexpectedly. Restart it from the desktop app.', 'offline');
        }
      })
      .catch(function () {
        setStatus('Xdrop engine is not running. Start Xdrop, then reopen this panel.', 'offline');
      });
  }

  function ready() {
    pointWebviewAtService();
    probeEngine();
  }

  if (document.readyState === 'complete' || document.readyState === 'interactive') {
    ready();
  } else {
    document.addEventListener('DOMContentLoaded', ready);
  }
})();
