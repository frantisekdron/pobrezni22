/* ============================================================================
   POBŘEŽNÍ 22 — motion engine
   Parallax · 3D tilt · Ken Burns (CSS) · count-up · den→noc scrub · video v dohledu
   Respektuje prefers-reduced-motion.
============================================================================ */
(function () {
  "use strict";
  var $$ = function (s, c) { return Array.prototype.slice.call((c || document).querySelectorAll(s)); };
  var mq = function (q) { return window.matchMedia && window.matchMedia(q).matches; };
  var reduce = mq("(prefers-reduced-motion: reduce)");
  var isTouch = mq("(hover: none)");

  var vh = window.innerHeight;
  var parallaxEls = [], scrubEls = [], ticking = false;

  /* ---- curtain loader (s bezpečným fallbackem) ---- */
  function initCurtain() {
    var c = document.getElementById("curtain");
    if (!c) return;
    var done = false;
    var hide = function () { if (done) return; done = true; c.classList.add("is-done"); };
    if (document.readyState === "complete") setTimeout(hide, 250);
    else window.addEventListener("load", function () { setTimeout(hide, 250); });
    // fallback — opona se zvedne nejpozději po 1,2 s, ať nikdy nevisí
    setTimeout(hide, 1200);
  }
  initCurtain();

  /* ---- scroll progress ---- */
  function initScrollbar() {
    var bar = document.getElementById("scrollbar");
    if (!bar) return;
    var upd = function () {
      var h = document.documentElement.scrollHeight - window.innerHeight;
      var p = h > 0 ? window.scrollY / h : 0;
      bar.style.transform = "scaleX(" + p.toFixed(4) + ")";
    };
    upd(); window.addEventListener("scroll", upd, { passive: true });
    window.addEventListener("resize", upd, { passive: true });
  }
  initScrollbar();

  function collect() {
    parallaxEls = $$("[data-parallax]").map(function (el) {
      return {
        el: el,
        target: el.querySelector("[data-parallax-target]") || el.querySelector("img,video") || el,
        speed: parseFloat(el.getAttribute("data-parallax")) || 0.3
      };
    });
    scrubEls = $$("[data-scrub]");
  }

  function tick() {
    ticking = false;
    var mid = vh / 2;
    var i, r;
    for (i = 0; i < parallaxEls.length; i++) {
      var p = parallaxEls[i];
      r = p.el.getBoundingClientRect();
      if (r.bottom < -150 || r.top > vh + 150) continue;
      var center = r.top + r.height / 2;
      var prog = (center - mid) / (mid + r.height / 2); // ~ -1..1
      var ty = (-prog * p.speed * 100).toFixed(1);
      p.target.style.transform = "translate3d(0," + ty + "px,0)";
    }
    for (i = 0; i < scrubEls.length; i++) {
      var s = scrubEls[i];
      r = s.getBoundingClientRect();
      var pr = 1 - (r.top + r.height * 0.2) / (vh + r.height * 0.4);
      pr = pr < 0 ? 0 : pr > 1 ? 1 : pr;
      s.style.setProperty("--np", pr.toFixed(3));
      var lbl = s.querySelector("[data-scrub-label]");
      if (lbl) lbl.setAttribute("data-state", pr > 0.5 ? "night" : "day");
    }
  }
  function onScroll() { if (!ticking) { ticking = true; requestAnimationFrame(tick); } }

  /* ---- 3D tilt (myš) ---- */
  function initTilt() {
    if (isTouch) return;
    $$("[data-tilt]").forEach(function (el) {
      var max = parseFloat(el.getAttribute("data-tilt")) || 6;
      el.style.transformStyle = "preserve-3d";
      el.addEventListener("mousemove", function (e) {
        var r = el.getBoundingClientRect();
        var px = (e.clientX - r.left) / r.width - 0.5;
        var py = (e.clientY - r.top) / r.height - 0.5;
        el.style.transform = "perspective(1000px) rotateY(" + (px * max).toFixed(2) + "deg) rotateX(" + (-py * max).toFixed(2) + "deg)";
      });
      el.addEventListener("mouseleave", function () { el.style.transform = ""; });
    });
  }

  /* ---- count-up ---- */
  function initCount() {
    var els = $$("[data-count]");
    if (!("IntersectionObserver" in window) || reduce) {
      els.forEach(function (e) { e.textContent = e.getAttribute("data-count"); });
      return;
    }
    var io = new IntersectionObserver(function (en) {
      en.forEach(function (x) { if (x.isIntersecting) { countTo(x.target); io.unobserve(x.target); } });
    }, { threshold: 0.6 });
    els.forEach(function (e) { io.observe(e); });
  }
  function countTo(el) {
    var end = parseFloat(el.getAttribute("data-count")) || 0, dur = 1300, start = null;
    function step(ts) {
      if (!start) start = ts;
      var p = Math.min(1, (ts - start) / dur);
      var e = 1 - Math.pow(1 - p, 3);
      el.textContent = Math.round(end * e);
      if (p < 1) requestAnimationFrame(step); else el.textContent = end;
    }
    requestAnimationFrame(step);
  }

  /* ---- video: přehrát v dohledu, jinak pauza ---- */
  function initVideo() {
    var v = document.querySelector("video[data-autoview]");
    if (!v) return;
    var play = function () { var pr = v.play(); if (pr && pr.catch) pr.catch(function () {}); };
    if (!("IntersectionObserver" in window)) { play(); return; }
    var io = new IntersectionObserver(function (en) {
      en.forEach(function (x) {
        if (x.isIntersecting) { if (v.preload === "none") v.preload = "auto"; play(); }
        else v.pause();
      });
    }, { threshold: 0.25 });
    io.observe(v);
  }

  /* ---- jemný 3D tilt galerie (delegovaně — přežije re-render) ---- */
  function initGalleryTilt() {
    if (isTouch) return;
    var g = document.getElementById("gallery");
    if (!g) return;
    g.addEventListener("mousemove", function (e) {
      var it = e.target.closest(".gallery__item");
      if (!it) return;
      var r = it.getBoundingClientRect();
      var px = (e.clientX - r.left) / r.width - 0.5;
      var py = (e.clientY - r.top) / r.height - 0.5;
      it.style.transform = "perspective(1100px) rotateY(" + (px * 5).toFixed(2) + "deg) rotateX(" + (-py * 5).toFixed(2) + "deg)";
    });
    g.addEventListener("mouseout", function (e) {
      var it = e.target.closest(".gallery__item");
      if (it) it.style.transform = "";
    });
  }

  /* ---- magnetická tlačítka ---- */
  function initMagnetic() {
    if (isTouch) return;
    $$("[data-mag]").forEach(function (btn) {
      btn.style.transition = "transform .25s cubic-bezier(.22,.61,.36,1)";
      btn.addEventListener("mousemove", function (e) {
        var r = btn.getBoundingClientRect();
        var x = (e.clientX - r.left - r.width / 2) * 0.3;
        var y = (e.clientY - r.top - r.height / 2) * 0.4;
        btn.style.transform = "translate(" + x.toFixed(1) + "px," + y.toFixed(1) + "px)";
      });
      btn.addEventListener("mouseleave", function () { btn.style.transform = ""; });
    });
  }

  function init() {
    initCount();
    initVideo();
    if (reduce) return; // bez parallaxu/tiltu/scrubu
    collect();
    tick();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", function () { vh = window.innerHeight; collect(); onScroll(); }, { passive: true });
    initTilt();
    initGalleryTilt();
    initMagnetic();
  }

  if (document.readyState !== "loading") init();
  else document.addEventListener("DOMContentLoaded", init);
})();
