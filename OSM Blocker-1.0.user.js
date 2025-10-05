// ==UserScript==
// @name         OSM Blocker
// @namespace    http://tampermonkey.net/
// @version      1.0
// @description  Replace transparency in numeric tiles with white on wplace.live
// @match        https://wplace.live/*
// @grant        none
// @run-at       document-start
// ==/UserScript==

(function () {
  'use strict';

  const tileRegex = /\/(\d{1,4})(?:\.png)(?:$|\?)/i;
  const PROCESSED_MARKER = 'bm_processed=1';
  const PLACEHOLDER_1PX = 'data:image/gif;base64,R0lGODlhAQABAIABAP///wAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==';

  function isTileUrl(url) {
    if (!url || typeof url !== 'string') return false;
    if (url.startsWith('data:') || url.startsWith('blob:')) return false;
    if (url.includes(PROCESSED_MARKER)) return false;
    return tileRegex.test(url);
  }

  async function fetchAndReplaceTransparentWithWhite(url) {
    try {
      const resp = await fetch(url, { mode: 'cors', credentials: 'include' });
      if (!resp.ok) throw new Error('fetch failed: ' + resp.status);
      const blob = await resp.blob();
      const bitmap = await createImageBitmap(blob);
      const canvas = document.createElement('canvas');
      canvas.width = bitmap.width;
      canvas.height = bitmap.height;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(bitmap, 0, 0);
      const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
      const data = imageData.data;
      for (let i = 0; i < data.length; i += 4) {
        if (data[i+3] === 0) { data[i]=255; data[i+1]=255; data[i+2]=255; data[i+3]=255; }
      }
      ctx.putImageData(imageData, 0, 0);
      const modifiedBlob = await new Promise(resolve => canvas.toBlob(resolve, 'image/png'));
      return { url: URL.createObjectURL(modifiedBlob), width: canvas.width, height: canvas.height };
    } catch {
      return null;
    }
  }

  (function interceptImageSrcSetter() {
    const proto = HTMLImageElement.prototype;
    const desc = Object.getOwnPropertyDescriptor(proto, 'src');
    if (!desc || !desc.configurable) return;
    Object.defineProperty(proto, 'src', {
      get: function () { return desc.get.call(this); },
      set: function (value) {
        try {
          const url = String(value || '');
          if (isTileUrl(url)) {
            const imgEl = this;
            if (imgEl.dataset && imgEl.dataset.bmProcessing === '1') return desc.set.call(imgEl, value);
            imgEl.dataset.bmProcessing = '1';
            desc.set.call(imgEl, PLACEHOLDER_1PX);
            (async () => {
              const result = await fetchAndReplaceTransparentWithWhite(url);
              if (result && imgEl) {
                imgEl.dataset.bmProcessed = '1';
                desc.set.call(imgEl, result.url);
                const cleanup = () => { try { URL.revokeObjectURL(result.url); } catch {} };
                const mo = new MutationObserver((_, observer) => { if (!document.contains(imgEl)) { cleanup(); observer.disconnect(); }});
                mo.observe(document, { childList: true, subtree: true });
              } else { try { desc.set.call(imgEl, url); } catch {} }
              if (imgEl && imgEl.dataset) delete imgEl.dataset.bmProcessing;
            })();
            return;
          }
        } catch {}
        return desc.set.call(this, value);
      },
      configurable: true,
      enumerable: true
    });
  })();

  const imgObserver = new MutationObserver(mutations => {
    for (const m of mutations) {
      if (m.type === 'childList') {
        m.addedNodes.forEach(node => {
          if (!(node instanceof HTMLElement)) return;
          if (node.tagName === 'IMG') handleImgElement(node);
          node.querySelectorAll && node.querySelectorAll('img').forEach(img => handleImgElement(img));
        });
      }
    }
  });
  imgObserver.observe(document, { childList: true, subtree: true });

  function scanExistingImages() {
    document.querySelectorAll('img').forEach(img => handleImgElement(img));
  }

  function handleImgElement(imgEl) {
    try {
      const src = imgEl.getAttribute('src') || imgEl.src;
      if (!src) return;
      if (isTileUrl(src) && imgEl.dataset?.bmProcessed !== '1') imgEl.src = src;
    } catch {}
  }

  setTimeout(scanExistingImages, 50);

  (function interceptFetchForTiles() {
    const origFetch = window.fetch;
    window.fetch = async function (input, init) {
      try {
        const reqUrl = (typeof input === 'string') ? input : (input && input.url);
        if (isTileUrl(reqUrl)) {
          try {
            const resp = await origFetch(input, init);
            if (!resp.ok) return resp;
            const blob = await resp.blob();
            try {
              const bitmap = await createImageBitmap(blob);
              const canvas = document.createElement('canvas');
              canvas.width = bitmap.width;
              canvas.height = bitmap.height;
              const ctx = canvas.getContext('2d');
              ctx.drawImage(bitmap, 0, 0);
              const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
              const data = imageData.data;
              for (let i = 0; i < data.length; i += 4) if (data[i+3]===0) {data[i]=255;data[i+1]=255;data[i+2]=255;data[i+3]=255;}
              ctx.putImageData(imageData, 0, 0);
              const newBlob = await new Promise(res => canvas.toBlob(res, 'image/png'));
              const headers = new Headers(resp.headers);
              headers.set('Content-Type', 'image/png');
              return new Response(newBlob, { status: resp.status, statusText: resp.statusText, headers });
            } catch { return resp; }
          } catch { return origFetch(input, init); }
        }
      } catch {}
      return origFetch(input, init);
    };
  })();

})();