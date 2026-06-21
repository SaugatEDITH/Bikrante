(function () {
  const TRACK_URL = "/activity/track/";
  const PATH = window.location && window.location.pathname ? window.location.pathname : "";
  const PAGE = PATH === "/" ? "home" : "shop";
  const MAX_QUEUE_SIZE = 25;
  const FLUSH_INTERVAL_MS = 5000;

  function getCookie(name) {
    const m = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
    return m ? decodeURIComponent(m[2]) : "";
  }

  function setCookie(name, value, maxAgeSeconds) {
    document.cookie =
      encodeURIComponent(name) +
      "=" +
      encodeURIComponent(value) +
      "; path=/; max-age=" +
      String(maxAgeSeconds) +
      "; samesite=Lax";
  }

  function uuidv4() {
    if (window.crypto && crypto.randomUUID) return crypto.randomUUID();
    const buf = new Uint8Array(16);
    crypto.getRandomValues(buf);
    buf[6] = (buf[6] & 0x0f) | 0x40;
    buf[8] = (buf[8] & 0x3f) | 0x80;
    const hex = Array.from(buf).map((b) => b.toString(16).padStart(2, "0")).join("");
    return (
      hex.slice(0, 8) +
      "-" +
      hex.slice(8, 12) +
      "-" +
      hex.slice(12, 16) +
      "-" +
      hex.slice(16, 20) +
      "-" +
      hex.slice(20)
    );
  }

  async function sha256Hex(str) {
    const data = new TextEncoder().encode(str);
    const hash = await crypto.subtle.digest("SHA-256", data);
    const bytes = new Uint8Array(hash);
    return Array.from(bytes).map((b) => b.toString(16).padStart(2, "0")).join("");
  }

  async function generateFingerprint() {
    try {
      const canvas = document.createElement("canvas");
      const ctx = canvas.getContext("2d");
      canvas.width = 240;
      canvas.height = 80;
      ctx.textBaseline = "top";
      ctx.font = "16px Arial";
      ctx.fillText("bikrante-fp", 10, 10);
      ctx.fillStyle = "#f60";
      ctx.fillRect(100, 20, 80, 30);
      const canvasData = canvas.toDataURL();

      const raw = [
        navigator.userAgent,
        navigator.language,
        String(screen.width),
        String(screen.height),
        String(screen.colorDepth),
        String(new Date().getTimezoneOffset()),
        String(navigator.hardwareConcurrency || ""),
        String(navigator.deviceMemory || ""),
        canvasData,
      ].join("|");

      return await sha256Hex(raw);
    } catch (_e) {
      return "";
    }
  }

  function ensureIds() {
    let anon = getCookie("anon_id");
    if (!anon) {
      anon = uuidv4();
      setCookie("anon_id", anon, 60 * 60 * 24 * 365);
    }
    return anon;
  }

  const state = {
    anon_id: "",
    fingerprint: "",
    queue: [],
    hoverStart: new Map(),
    visibleSince: new Map(),
    dwellAccum: new Map(),
    impressed: new Set(),
    flushTimer: null,
  };

  function enqueue(ev) {
    if (!ev || !ev.product_id || !ev.event_type) return;
    state.queue.push(ev);
    if (state.queue.length >= MAX_QUEUE_SIZE) flush();
  }

  function productElFromEventTarget(target) {
    return target && target.closest ? target.closest(".js-track-product") : null;
  }

  function getProductId(el) {
    if (!el) return null;
    const v = el.getAttribute("data-product-id");
    if (!v) return null;
    const n = Number(v);
    return Number.isFinite(n) ? n : null;
  }

  function baseMeta(el) {
    const meta = {};
    if (el && el.getAttribute) {
      const pos = el.getAttribute("data-position");
      if (pos) {
        const n = Number(pos);
        if (Number.isFinite(n)) meta.position = n;
      }
      const section =
        el.getAttribute("data-section") || el.getAttribute("data-track-section");
      if (section) {
        meta.section = section;
      }
    }
    meta.ts = now();
    return meta;
  }

  function now() {
    return Date.now();
  }

  function safeSend(body) {
    const data = JSON.stringify(body);
    if (navigator.sendBeacon) {
      try {
        const blob = new Blob([data], { type: "application/json" });
        navigator.sendBeacon(TRACK_URL, blob);
        return true;
      } catch (_e) {}
    }
    fetch(TRACK_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: data,
      keepalive: true,
      credentials: "same-origin",
    }).catch(function () {});
    return true;
  }

  function flush() {
    if (!state.queue.length) return;
    const events = state.queue.splice(0, state.queue.length);
    safeSend({
      anon_id: state.anon_id,
      fingerprint: state.fingerprint,
      page: PAGE,
      events: events,
    });
  }

  function attachHoverTracking(root) {
    root.addEventListener(
      "mouseenter",
      function (e) {
        const el = productElFromEventTarget(e.target);
        const pid = getProductId(el);
        if (!pid) return;
        state.hoverStart.set(pid, now());
      },
      true
    );

    root.addEventListener(
      "mouseleave",
      function (e) {
        const el = productElFromEventTarget(e.target);
        const pid = getProductId(el);
        if (!pid) return;
        const start = state.hoverStart.get(pid);
        if (!start) return;
        const dur = now() - start;
        state.hoverStart.delete(pid);
        if (dur >= 150) {
          enqueue({
            product_id: pid,
            event_type: "hover",
            duration_ms: dur,
            meta: baseMeta(el),
          });
        }
      },
      true
    );
  }

  function attachClickTracking(root) {
    root.addEventListener(
      "click",
      function (e) {
        const el = productElFromEventTarget(e.target);
        const pid = getProductId(el);
        if (!pid) return;

        const t = e.target;
        const actionBtn = t.closest && t.closest(".action__btn");
        const cartBtn = t.closest && t.closest(".cart__btn");

        let eventType = "click";

        if (actionBtn) {
          const aria = (actionBtn.getAttribute("aria-label") || "").toLowerCase();
          if (aria.includes("quick view")) eventType = "quick_view";
          if (aria.includes("wishlist")) eventType = "wishlist";
        }

        if (cartBtn && !cartBtn.classList.contains("disabled")) {
          eventType = "add_to_cart";
        }

        if (t.closest && t.closest("a") && t.closest("a").classList.contains("product__images")) {
          eventType = "click";
        }

        enqueue({
          product_id: pid,
          event_type: eventType,
          duration_ms: null,
          meta: baseMeta(el),
        });
      },
      true
    );
  }

  function attachImpressionAndDwellTracking() {
    const items = document.querySelectorAll(".js-track-product");
    if (!items.length) return;

    const io = new IntersectionObserver(
      function (entries) {
        const ts = now();
        entries.forEach(function (entry) {
          const el = entry.target;
          const pid = getProductId(el);
          if (!pid) return;

          if (entry.isIntersecting && entry.intersectionRatio >= 0.35) {
            if (!state.impressed.has(pid)) {
              state.impressed.add(pid);
              enqueue({
                product_id: pid,
                event_type: "impression",
                duration_ms: null,
                meta: baseMeta(el),
              });
            }
            state.visibleSince.set(pid, ts);
          } else {
            const start = state.visibleSince.get(pid);
            if (start) {
              const dur = ts - start;
              state.visibleSince.delete(pid);
              const prev = state.dwellAccum.get(pid) || 0;
              state.dwellAccum.set(pid, prev + dur);
              if (dur >= 300) {
                enqueue({
                  product_id: pid,
                  event_type: "dwell",
                  duration_ms: dur,
                  meta: baseMeta(el),
                });
              }
            }
          }
        });
      },
      { threshold: [0, 0.35, 0.75] }
    );

    items.forEach(function (el) {
      io.observe(el);
    });
  }

  function init() {
    state.anon_id = ensureIds();

    generateFingerprint().then(function (fp) {
      state.fingerprint = fp || "";
      if (state.fingerprint) {
        setCookie("fp", state.fingerprint, 60 * 60 * 24 * 365);
      }
    });

    const root = document.getElementById("shop-results") || document.body;
    attachHoverTracking(root);
    attachClickTracking(root);

    function rebind() {
      attachImpressionAndDwellTracking();
    }

    rebind();

    document.body.addEventListener("htmx:afterSwap", function (evt) {
      if (evt.detail && evt.detail.target && evt.detail.target.id === "shop-results") {
        rebind();
      }
    });

    state.flushTimer = setInterval(flush, FLUSH_INTERVAL_MS);

    document.addEventListener("visibilitychange", function () {
      if (document.visibilityState === "hidden") {
        flush();
      }
    });

    window.addEventListener("beforeunload", function () {
      flush();
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
