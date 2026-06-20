// inject.js — běží v KONTEXTU STRÁNKY (world: MAIN), document_start.
// Zaháčkuje fetch i XMLHttpRequest a každou JSON odpověď pošle přes
// window.postMessage do content scriptu (ten ji předá do dashboardu).
(function () {
  "use strict";
  function emit(url, text) {
    try { window.postMessage({ __livetimeArb: 1, url: String(url || ""), text: text }, "*"); } catch (e) {}
  }
  // fetch
  const _f = window.fetch;
  if (_f) {
    window.fetch = function () {
      const args = arguments;
      const p = _f.apply(this, args);
      try {
        p.then(res => {
          try { res.clone().text().then(t => emit(res.url || args[0], t)).catch(() => {}); } catch (e) {}
        }).catch(() => {});
      } catch (e) {}
      return p;
    };
  }
  // XHR
  const _open = XMLHttpRequest.prototype.open, _send = XMLHttpRequest.prototype.send;
  XMLHttpRequest.prototype.open = function (m, url) { this.__laUrl = url; return _open.apply(this, arguments); };
  XMLHttpRequest.prototype.send = function () {
    this.addEventListener("load", function () {
      try {
        const ct = this.getResponseHeader && (this.getResponseHeader("content-type") || "");
        if (this.responseType === "json") emit(this.__laUrl, JSON.stringify(this.response));
        else if (!this.responseType || this.responseType === "text") {
          if (/json/i.test(ct) || /^\s*[\[{]/.test(this.responseText || "")) emit(this.__laUrl, this.responseText);
        }
      } catch (e) {}
    });
    return _send.apply(this, arguments);
  };
})();
