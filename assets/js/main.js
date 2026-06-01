/* ============================================================================
   POBŘEŽNÍ 22 — interaktivita
============================================================================ */
(function () {
  "use strict";
  var $  = function (s, c) { return (c || document).querySelector(s); };
  var $$ = function (s, c) { return Array.prototype.slice.call((c || document).querySelectorAll(s)); };

  /* ---------- jazyk / i18n ---------- */
  var lang = (localStorage.getItem("p22_lang") || (navigator.language || "cs").slice(0, 2)) === "en" ? "en" : "cs";

  function t(key) {
    var e = I18N[key];
    return e ? (e[lang] || e.cs) : key;
  }
  function applyI18n() {
    document.documentElement.lang = lang;
    $$("[data-i18n]").forEach(function (el) {
      el.textContent = t(el.getAttribute("data-i18n"));
    });
    $$("[data-i18n-ph]").forEach(function (el) {
      el.setAttribute("placeholder", t(el.getAttribute("data-i18n-ph")));
    });
    $$(".lang__btn").forEach(function (b) {
      b.classList.toggle("is-active", b.getAttribute("data-lang") === lang);
    });
  }
  function setLang(l) {
    lang = l; localStorage.setItem("p22_lang", l);
    applyI18n();
    renderAll(); // překreslit dynamický obsah ve správném jazyce
  }

  /* ---------- formátování ---------- */
  var loc = function () { return lang === "en" ? "en-US" : "cs-CZ"; };
  function fmtPrice(n) {
    if (n == null) return "—";
    return lang === "en" ? "CZK " + n.toLocaleString("en-US") : n.toLocaleString("cs-CZ") + " Kč";
  }
  function fmtArea(n) { return n.toLocaleString(loc()) + " m²"; }
  function floorLabel(f) { return f + ". " + (lang === "en" ? "floor" : "NP"); }
  function statusLabel(s) { return t("status." + s); }
  var extraLabel = {
    balkon: { cs: "Balkon", en: "Balcony" },
    terasa: { cs: "Terasa", en: "Terrace" },
    pavlač: { cs: "Pavlač", en: "Gallery" },
    dvorek: { cs: "Dvorek", en: "Courtyard" }
  };

  /* ---------- SVG ikony (standardy) ---------- */
  var ICONS = {
    parquet: '<svg viewBox="0 0 32 32"><rect x="3" y="6" width="11" height="8"/><rect x="18" y="6" width="11" height="8"/><rect x="3" y="18" width="11" height="8"/><rect x="18" y="18" width="11" height="8"/></svg>',
    door:    '<svg viewBox="0 0 32 32"><rect x="8" y="3" width="16" height="26"/><circle cx="20" cy="16" r="1.2" fill="currentColor" stroke="none"/></svg>',
    tile:    '<svg viewBox="0 0 32 32"><rect x="4" y="4" width="10" height="10"/><rect x="18" y="4" width="10" height="10"/><rect x="4" y="18" width="10" height="10"/><rect x="18" y="18" width="10" height="10"/></svg>',
    bath:    '<svg viewBox="0 0 32 32"><path d="M5 16h22v4a5 5 0 0 1-5 5H10a5 5 0 0 1-5-5z"/><path d="M9 16V8a3 3 0 0 1 6 0"/><line x1="5" y1="25" x2="7" y2="28"/><line x1="27" y1="25" x2="25" y2="28"/></svg>',
    switch:  '<svg viewBox="0 0 32 32"><rect x="9" y="3" width="14" height="26" rx="2"/><rect x="13" y="9" width="6" height="9" rx="1"/></svg>',
    window:  '<svg viewBox="0 0 32 32"><path d="M6 14a10 10 0 0 1 20 0v15H6z"/><line x1="16" y1="4" x2="16" y2="29"/><line x1="6" y1="14" x2="26" y2="14"/></svg>'
  };

  /* ---------- render: seznam dostupností + reálná Leaflet mapa ---------- */
  var locMap = null, locMarkers = [];
  function renderLocation() {
    var ul = $("#locationPoints");
    if (!ul) return;
    ul.innerHTML = LOCATION_POINTS.map(function (p, i) {
      return '<li class="locitem" data-i="' + i + '" tabindex="0">' +
        '<span class="locitem__min">' + p.min + '<small>min</small></span>' +
        '<span class="locitem__txt">' + p.t[lang] + '</span>' +
        '<span class="locitem__dot"></span></li>';
    }).join("");

    function hot(i, on) {
      var it = $('.locitem[data-i="' + i + '"]');
      if (it) it.classList.toggle("is-hot", on);
      var m = locMarkers[i];
      if (m && m._icon) m._icon.classList.toggle("is-hot", on);
      if (on && locMap && m) locMap.panTo(m.getLatLng(), { animate: true, duration: 0.5 });
    }
    $$(".locitem", ul).forEach(function (it) {
      var i = +it.getAttribute("data-i");
      it.addEventListener("mouseenter", function () { hot(i, true); });
      it.addEventListener("mouseleave", function () { hot(i, false); });
      it.addEventListener("focus", function () { hot(i, true); });
      it.addEventListener("blur", function () { hot(i, false); });
    });

    // mapa se inicializuje až když je sekce v dohledu (výkon + stabilita)
    var el = $("#locMap");
    if (!el) return;
    if (locMap) { initLeaflet(hot); return; }
    if ("IntersectionObserver" in window) {
      var io = new IntersectionObserver(function (en) {
        en.forEach(function (x) { if (x.isIntersecting) { io.disconnect(); initLeaflet(hot); } });
      }, { rootMargin: "200px" });
      io.observe(el);
    } else { initLeaflet(hot); }
  }

  function initLeaflet(hot) {
    var el = $("#locMap");
    if (!el || typeof L === "undefined") return;
    if (locMap) { locMap.remove(); locMap = null; locMarkers = []; }

    locMap = L.map(el, {
      center: [PROJECT_GEO.lat, PROJECT_GEO.lng], zoom: 15,
      scrollWheelZoom: false, zoomControl: true, attributionControl: true,
      fadeAnimation: false
    });
    L.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", {
      attribution: '&copy; OpenStreetMap &copy; CARTO', maxZoom: 19
    }).addTo(locMap);

    // marker domu — zlatý, s popiskem
    var home = L.divIcon({ className: "lmark lmark--home", html: '<span class="lmark__pulse"></span><span class="lmark__pin"></span><b class="lmark__name">Pobřežní 22</b>', iconSize: [18, 18], iconAnchor: [9, 9] });
    L.marker([PROJECT_GEO.lat, PROJECT_GEO.lng], { icon: home, zIndexOffset: 1000, interactive: false }).addTo(locMap);

    // body zájmu
    locMarkers = LOCATION_POINTS.map(function (p, i) {
      var icon = L.divIcon({ className: "lmark lmark--poi", html: '<span class="lmark__dot"></span><span class="lmark__tip"><b>' + p.min + ' min</b> ' + p.t[lang] + '</span>', iconSize: [14, 14], iconAnchor: [7, 7] });
      var m = L.marker([p.lat, p.lng], { icon: icon }).addTo(locMap);
      m.on("mouseover", function () { hot(i, true); });
      m.on("mouseout", function () { hot(i, false); });
      return m;
    });

    // fit na všechny body
    var pts = LOCATION_POINTS.map(function (p) { return [p.lat, p.lng]; });
    pts.push([PROJECT_GEO.lat, PROJECT_GEO.lng]);
    locMap.fitBounds(pts, { padding: [42, 42] });

    // dorenderovat po viditelnosti (kvůli velikosti kontejneru)
    setTimeout(function () { if (locMap) locMap.invalidateSize(); }, 300);
    if ("IntersectionObserver" in window) {
      var io = new IntersectionObserver(function (en) {
        en.forEach(function (x) { if (x.isIntersecting && locMap) { locMap.invalidateSize(); io.disconnect(); } });
      });
      io.observe(el);
    }
  }

  /* ---------- 3D COVERFLOW CAROUSEL (interiéry) ---------- */
  var carActive = 0, carTimer = null;
  function pad(n) { return (n < 10 ? "0" : "") + n; }

  function renderCarousel() {
    var stage = $("#carouselStage"); if (!stage) return;
    stage.innerHTML = GALLERY.map(function (it, i) {
      return '<figure class="cslide" data-i="' + i + '"><img src="' + it.src + '" alt="' + it.cap[lang] + '" loading="lazy" /><span class="cslide__zoom" aria-hidden="true">⤢</span></figure>';
    }).join("");
    $("#carTotal").textContent = pad(GALLERY.length);
    if (carActive > GALLERY.length - 1) carActive = 0;
    var dots = $("#carDots");
    dots.innerHTML = GALLERY.map(function (_, i) { return '<button class="cdot" data-i="' + i + '" aria-label="' + (i + 1) + '"></button>'; }).join("");
    layoutCarousel();
    bindCarousel();
    startAuto();
  }

  function layoutCarousel() {
    var slides = $$(".cslide", $("#carouselStage"));
    slides.forEach(function (s, i) {
      var off = i - carActive, abs = Math.abs(off);
      if (abs > 2) {
        s.style.opacity = 0; s.style.pointerEvents = "none"; s.style.zIndex = 0;
        s.style.transform = "translate(-50%,-50%) translateX(" + (off * 62) + "%) scale(.45)";
        s.classList.remove("is-active"); return;
      }
      var tx = off * 56, rot = off * -27, sc = off === 0 ? 1 : 0.78, tz = off === 0 ? 0 : -180 * abs;
      s.style.opacity = off === 0 ? 1 : (abs === 1 ? 0.6 : 0.3);
      s.style.pointerEvents = "auto";
      s.style.transform = "translate(-50%,-50%) translateX(" + tx + "%) translateZ(" + tz + "px) rotateY(" + rot + "deg) scale(" + sc + ")";
      s.style.zIndex = 10 - abs;
      s.classList.toggle("is-active", off === 0);
    });
    $("#carIndex").textContent = pad(carActive + 1);
    $("#carCap").textContent = GALLERY[carActive].cap[lang];
    $("#carBar").style.width = ((carActive + 1) / GALLERY.length * 100) + "%";
    $$("#carDots .cdot").forEach(function (d, i) { d.classList.toggle("is-active", i === carActive); });
  }

  function carGo(n) { carActive = (n + GALLERY.length) % GALLERY.length; layoutCarousel(); }
  function startAuto() { stopAuto(); carTimer = setInterval(function () { carGo(carActive + 1); }, 4500); }
  function stopAuto() { if (carTimer) { clearInterval(carTimer); carTimer = null; } }
  function restartAuto() { startAuto(); }

  function bindCarousel() {
    var car = $("#carousel"), stage = $("#carouselStage");
    $("#carPrev").onclick = function () { carGo(carActive - 1); restartAuto(); };
    $("#carNext").onclick = function () { carGo(carActive + 1); restartAuto(); };
    $$("#carDots .cdot").forEach(function (d) { d.onclick = function () { carGo(+d.getAttribute("data-i")); restartAuto(); }; });
    $$(".cslide", stage).forEach(function (s) {
      s.onclick = function () { var i = +s.getAttribute("data-i"); if (i === carActive) openLightbox(i); else { carGo(i); restartAuto(); } };
    });
    car.onmouseenter = stopAuto; car.onmouseleave = startAuto;
    var x0 = null;
    stage.onpointerdown = function (e) { x0 = e.clientX; stopAuto(); };
    stage.onpointerup = function (e) { if (x0 === null) return; var dx = e.clientX - x0; if (dx > 45) carGo(carActive - 1); else if (dx < -45) carGo(carActive + 1); x0 = null; startAuto(); };
    stage.onpointercancel = function () { x0 = null; };
  }

  /* ---------- render: standardy ---------- */
  function renderStandards() {
    var grid = $("#standardsGrid"); if (!grid) return;
    grid.innerHTML = STANDARDS.map(function (s) {
      return '<article class="std reveal"><div class="std__icon">' + (ICONS[s.icon] || "") + '</div>' +
             '<h3>' + s.t[lang] + '</h3><p>' + s.d[lang] + '</p></article>';
    }).join("");
    observeReveal(grid);
  }

  /* ---------- PRŮZKUMNÍK DOMU (výběr bytů) ---------- */
  var expFloor = 2, expLayout = "all", expOnlyAvail = false, bld3dDragged = false;
  function clamp(v, a, b) { return v < a ? a : v > b ? b : v; }

  function flatTags(a) {
    var tags = [];
    if (a.extra) tags.push(extraLabel[a.extra.t][lang] + " " + fmtArea(a.extra.m).replace(" m²", " m²"));
    if (a.cellar) tags.push((lang === "en" ? "Cellar" : "Sklep"));
    if (a.mezonet) tags.push(lang === "en" ? "Maisonette" : "Mezonet");
    return tags;
  }

  function unitMatches(a) {
    return (expLayout === "all" || a.layout === expLayout) && (!expOnlyAvail || a.status === "available");
  }
  function floorAvail(f) {
    return APARTMENTS.filter(function (a) { return a.floor === f && a.status === "available" && unitMatches(a); }).length;
  }
  function floorInfo(f) { return FLOORS.filter(function (x) { return x.n === f; })[0]; }

  function renderBuilding() {
    var box = $("#bldFloors"); if (!box) return;
    box.innerHTML = FLOORS.map(function (fl) {
      var avail = floorAvail(fl.n);
      return '<button class="bfloor" data-floor="' + fl.n + '" style="top:' + fl.top + '%;height:' + fl.h + '%" aria-label="' + fl.label[lang] + '">' +
        '<span class="bfloor__tag"><b>' + fl.n + '.</b>&nbsp;NP' +
        (avail ? '<i class="bfloor__dot"></i>' + avail : '') + '</span></button>';
    }).join("");
    $$(".bfloor", box).forEach(function (b) {
      b.addEventListener("click", function () { if (bld3dDragged) return; selectFloor(+b.getAttribute("data-floor")); });
    });
  }

  /* dům je nyní statický výkres — žádné 3D otáčení (čistší, elegantnější) */
  function initBuilding3D() { bld3dDragged = false; }

  function renderFloorPicker() {
    var p = $("#floorPicker"); if (!p) return;
    p.innerHTML = FLOORS.map(function (fl) {
      var avail = floorAvail(fl.n);
      return '<button class="fpill' + (avail ? "" : " is-out") + '" data-floor="' + fl.n + '">' +
        '<span class="fpill__n">' + fl.n + '<i>. NP</i></span>' +
        '<span class="fpill__c">' + (avail ? avail + " " + t("exp.floorAvail") : t("exp.soldout")) + '</span></button>';
    }).join("");
    $$(".fpill", p).forEach(function (b) {
      b.addEventListener("click", function () { selectFloor(+b.getAttribute("data-floor")); });
    });
  }

  function selectFloor(f) {
    expFloor = f;
    var fl = floorInfo(f);
    var spot = $("#bldSpot");
    if (spot && fl) { spot.hidden = false; spot.style.top = fl.top + "%"; spot.style.height = fl.h + "%"; }
    $$(".bfloor").forEach(function (b) { b.classList.toggle("is-active", +b.getAttribute("data-floor") === f); });
    $$(".fpill").forEach(function (b) { b.classList.toggle("is-active", +b.getAttribute("data-floor") === f); });
    var tt = $("#floorTitle"); if (tt) tt.textContent = fl ? fl.label[lang] : "";
    var av = floorAvail(f), tot = APARTMENTS.filter(function (a) { return a.floor === f; }).length;
    var mt = $("#floorMeta"); if (mt) mt.textContent = tot + (lang === "en" ? " residences on this floor" : " bytů na podlaží");
    var bd = $("#floorBadge");
    if (bd) { bd.textContent = av + " " + t("exp.floorAvail"); bd.className = "floorhead__badge" + (av ? "" : " is-out"); }
    renderUnits(f);
  }

  function renderUnits(f) {
    var list = $("#unitList"); if (!list) return;
    var units = APARTMENTS.filter(function (a) { return a.floor === f; });
    var shown = units.filter(unitMatches);
    var emptyEl = $("#unitEmpty"); if (emptyEl) emptyEl.hidden = shown.length !== 0;
    list.innerHTML = shown.map(function (a, i) {
      var gone = a.status !== "available";
      var specs = [fmtArea(a.area)];
      if (a.extra) specs.push(extraLabel[a.extra.t][lang] + " " + fmtArea(a.extra.m));
      if (a.mezonet) specs.push(lang === "en" ? "Maisonette" : "Mezonet");
      var specHtml = specs.map(function (s) { return '<span>' + s + '</span>'; }).join('<em>·</em>');
      return '<article class="unit' + (gone ? " is-gone" : "") + '" data-id="' + a.id + '" tabindex="0" style="--d:' + (i * 60) + 'ms">' +
        '<div class="unit__media"><img src="' + a.img + '" alt="" loading="lazy"/>' +
          '<span class="unit__badge badge--' + a.status + '">' + statusLabel(a.status) + '</span></div>' +
        '<div class="unit__body">' +
          '<div class="unit__head"><span class="unit__no">' + (lang === "en" ? "Unit" : "Byt") + ' ' + (a.id < 10 ? "0" + a.id : a.id) + '</span>' +
            '<span class="unit__disp">' + a.layout + '</span></div>' +
          '<div class="unit__specs">' + specHtml + '</div>' +
          '<div class="unit__foot"><span class="unit__price">' + fmtPrice(a.price) + '</span>' +
            '<span class="unit__cta">' + t("exp.detail") + ' <i>&rarr;</i></span></div>' +
        '</div></article>';
    }).join("");
    $$(".unit", list).forEach(function (el) {
      el.addEventListener("click", function () { openModal(+el.getAttribute("data-id")); });
      el.addEventListener("keydown", function (e) { if (e.key === "Enter") openModal(+el.getAttribute("data-id")); });
    });
  }

  function renderExplorer() {
    renderBuilding();
    renderFloorPicker();
    selectFloor(expFloor);
  }

  function renderCommercial() {
    var box = $("#commercialList"); if (!box) return;
    box.innerHTML = COMMERCIAL.map(function (c) {
      return '<div class="com">' +
        '<span class="com__floor">' + c.floor + '</span>' +
        '<span class="com__area">' + fmtArea(c.area) + '</span>' +
        '<span class="com__code">' + c.code + '</span>' +
        '<span class="com__price">' + fmtPrice(c.price) + '</span></div>';
    }).join("");
  }

  /* ---------- modal: detail bytu ---------- */
  var modal = $("#modal");
  function openModal(id) {
    var a = APARTMENTS.find(function (x) { return x.id === id; });
    if (!a) return;
    // Půdorysy: karta bytu vždy; mezonet (14) navíc 3D dollhouse se schodištěm
    var views = [{ src: "assets/img/floorplans/" + a.plan + ".jpg", tag: t("modal.plan") }];
    if (a.mezonet) views.push({ src: "assets/img/floorplans/byt14-3d.webp", tag: t("modal.plan3d") });
    var planHtml = '<span class="plan3d__tag">' + views[0].tag + '</span>' +
      '<div class="plan3d__inner"><img id="modalPlanImg" src="' + views[0].src + '" alt="' + views[0].tag + '" ' +
      'onerror="this.onerror=null;this.src=\'assets/img/floorplans/plan-3d.webp\'"/></div>' +
      (views.length > 1 ? '<div class="plan3d__switch" id="planSwitch">' +
        views.map(function (v, i) { return '<button data-vi="' + i + '"' + (i === 0 ? ' class="is-active"' : '') + '>' + v.tag + '</button>'; }).join("") +
      '</div>' : '');

    var rows = "";
    rows += mrow(t("modal.layout"), a.layout);
    rows += mrow(t("modal.floor"), floorLabel(a.floor));
    rows += mrow(t("modal.interior"), fmtArea(a.area));
    if (a.extra) rows += mrow(t("modal.outdoor"), extraLabel[a.extra.t][lang] + " · " + fmtArea(a.extra.m));
    if (a.cellar) rows += mrow(t("modal.cellar"), fmtArea(a.cellar));
    rows += mrow("<b>" + t("modal.total") + "</b>", "<b>" + fmtArea(a.total) + "</b>");

    var reserveBtn = a.status === "available"
      ? '<button class="btn btn--gold btn--full" id="modalReserve">' + t("modal.reserve") + '</button>'
      : '<div style="text-align:center;color:var(--muted);font-size:.9rem">' + statusLabel(a.status) + '</div>';

    $("#modalContent").innerHTML =
      '<div class="mflat__plan plan3d">' + planHtml + '</div>' +
      '<div class="mflat__body">' +
        '<span class="badge badge--' + a.status + ' mflat__badge">' + statusLabel(a.status) + '</span>' +
        '<h3 class="mflat__title">' + (lang === "en" ? "Residence" : "Byt") + " " + a.id + '</h3>' +
        '<p class="mflat__sub">' + a.layout + " · " + floorLabel(a.floor) + '</p>' +
        '<div class="mflat__rows">' + rows + '</div>' +
        '<div class="mflat__price"><small>' + t("modal.price") + '</small>' + fmtPrice(a.price) + '</div>' +
        reserveBtn +
      '</div>';

    if (a.status === "available") {
      $("#modalReserve").addEventListener("click", function () {
        closeModal();
        var sel = $("#fUnit");
        if (sel) sel.value = String(a.id);
        document.getElementById("reserve").scrollIntoView({ behavior: "smooth" });
        setTimeout(function () { var n = $("#fName"); if (n) n.focus(); }, 600);
      });
    }
    var sw = $("#planSwitch");
    if (sw) {
      $$("button", sw).forEach(function (b) {
        b.addEventListener("click", function () {
          var v = views[+b.getAttribute("data-vi")];
          $("#modalPlanImg").src = v.src;
          $(".plan3d__tag", modal).textContent = v.tag;
          $$("button", sw).forEach(function (x) { x.classList.remove("is-active"); });
          b.classList.add("is-active");
        });
      });
    }
    modal.classList.add("is-open");
    modal.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden";
  }
  function mrow(a, b) { return '<div class="mrow"><span>' + a + '</span><span>' + b + '</span></div>'; }
  function closeModal() {
    modal.classList.remove("is-open");
    modal.setAttribute("aria-hidden", "true");
    document.body.style.overflow = "";
  }
  $$("[data-close]", modal).forEach(function (el) { el.addEventListener("click", closeModal); });

  /* ---------- lightbox ---------- */
  var lb = $("#lightbox"), lbImg = $("#lightboxImg"), lbCap = $("#lightboxCap"), lbIndex = 0;
  function openLightbox(i) {
    lbIndex = i; updateLightbox();
    lb.classList.add("is-open"); lb.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden";
  }
  function updateLightbox() {
    var item = GALLERY[lbIndex];
    lbImg.src = item.src; lbImg.alt = item.cap[lang]; lbCap.textContent = item.cap[lang];
  }
  function lbStep(d) { lbIndex = (lbIndex + d + GALLERY.length) % GALLERY.length; updateLightbox(); }
  function closeLightbox() { lb.classList.remove("is-open"); lb.setAttribute("aria-hidden", "true"); document.body.style.overflow = ""; }
  $("[data-lbclose]").addEventListener("click", closeLightbox);
  $("[data-lbprev]").addEventListener("click", function () { lbStep(-1); });
  $("[data-lbnext]").addEventListener("click", function () { lbStep(1); });
  lb.addEventListener("click", function (e) { if (e.target === lb) closeLightbox(); });

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") { closeModal(); closeLightbox(); }
    if (lb.classList.contains("is-open")) {
      if (e.key === "ArrowLeft") lbStep(-1);
      if (e.key === "ArrowRight") lbStep(1);
    }
  });

  /* ---------- select bytu ve formuláři ---------- */
  function populateUnitSelect() {
    var sel = $("#fUnit"); if (!sel) return;
    var cur = sel.value;
    var opts = '<option value="">' + t("form.unitAny") + '</option>';
    APARTMENTS.filter(function (a) { return a.status === "available"; }).forEach(function (a) {
      opts += '<option value="' + a.id + '">' + (lang === "en" ? "Unit" : "Byt") + " " + a.id +
              " — " + a.layout + ", " + floorLabel(a.floor) + ", " + fmtArea(a.total) + '</option>';
    });
    sel.innerHTML = opts;
    if (cur) sel.value = cur;
  }

  /* ---------- formulář ---------- */
  function initForm() {
    var form = $("#reserveForm"); if (!form) return;
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var name = $("#fName"), email = $("#fEmail"), gdpr = $("#fGdpr"), msg = $("#formMsg");
      [name, email].forEach(function (f) { f.classList.remove("invalid"); });
      var ok = true;
      if (!name.value.trim()) { name.classList.add("invalid"); ok = false; }
      if (!email.value.trim() || !/^\S+@\S+\.\S+$/.test(email.value)) { email.classList.add("invalid"); ok = false; }
      if (!gdpr.checked) ok = false;
      if (!ok) { msg.textContent = t("form.required"); msg.className = "form__msg is-err"; return; }

      var unitSel = $("#fUnit");
      var unitTxt = unitSel.value ? unitSel.options[unitSel.selectedIndex].text : t("form.unitAny");
      var data = {
        name: name.value.trim(),
        email: email.value.trim(),
        phone: $("#fPhone").value.trim(),
        unit: unitTxt,
        message: $("#fMsg").value.trim(),
        subject: "Pobřežní 22 — rezervace prohlídky: " + unitTxt
      };

      var btn = $("#formSubmit");
      btn.textContent = t("form.sending"); btn.disabled = true;

      send(data).then(function () {
        msg.textContent = t("form.success"); msg.className = "form__msg is-ok";
        form.reset(); populateUnitSelect();
      }).catch(function () {
        msg.textContent = t("form.error"); msg.className = "form__msg is-err";
      }).then(function () {
        btn.textContent = t("form.submit"); btn.disabled = false;
      });
    });
  }

  function send(data) {
    // 1) bez endpointu -> mailto (funguje ihned)
    if (!SITE.FORM_ENDPOINT) {
      var body = encodeURIComponent(
        "Jméno: " + data.name + "\nE-mail: " + data.email + "\nTelefon: " + data.phone +
        "\nByt: " + data.unit + "\n\n" + data.message
      );
      window.location.href = "mailto:" + SITE.email + "?subject=" + encodeURIComponent(data.subject) + "&body=" + body;
      return Promise.resolve();
    }
    // 2) Web3Forms (JSON + access_key)
    if (SITE.WEB3FORMS_KEY) {
      return fetch(SITE.FORM_ENDPOINT, {
        method: "POST", headers: { "Content-Type": "application/json", "Accept": "application/json" },
        body: JSON.stringify(Object.assign({ access_key: SITE.WEB3FORMS_KEY }, data))
      }).then(function (r) { if (!r.ok) throw new Error(); });
    }
    // 3) generický endpoint (Formspree apod.) — FormData
    var fd = new FormData();
    Object.keys(data).forEach(function (k) { fd.append(k, data[k]); });
    return fetch(SITE.FORM_ENDPOINT, { method: "POST", body: fd, headers: { "Accept": "application/json" } })
      .then(function (r) { if (!r.ok) throw new Error(); });
  }

  /* ---------- populace kontaktů z konfigurace ---------- */
  function fillContacts() {
    var tel = "tel:" + SITE.phoneHref, mail = "mailto:" + SITE.email;
    function set(id, attr, val, txt) { var e = $(id); if (!e) return; if (attr) e.setAttribute(attr, val); if (txt != null) e.textContent = txt; }

    // reserve
    set("#reserveTel", "href", tel, SITE.phone);
    set("#reserveMail", "href", mail, SITE.email);
    // contact
    set("#cPhone", "href", tel); var cp = $("#cPhone .cinfo__val"); if (cp) cp.textContent = SITE.phone;
    set("#cMail", "href", mail); var cm = $("#cMail .cinfo__val"); if (cm) cm.textContent = SITE.email;
    set("#cAddr", null, null, SITE.address);
    // footer
    set("#fTel", "href", tel, SITE.phone);
    set("#fMail", "href", mail, SITE.email);
    set("#fAddr", null, null, SITE.address);
    set("#fCompany", null, null, SITE.company + " · " + SITE.companyId);
    set("#fCompany2", null, null, SITE.company);
    set("#year", null, null, String(new Date().getFullYear()));

    // makléř + firma
    var a = SITE.agent;
    var ph = a.photo ? '<img class="agent__photo" src="' + a.photo + '" alt="' + a.name + '" onerror="this.outerHTML=\'<div class=&quot;agent__ph&quot;>' + (a.name[0] || "P") + '</div>\'"/>' : '<div class="agent__ph">' + (a.name[0] || "P") + '</div>';
    $("#contactAgent").innerHTML = ph +
      '<div class="agent__info"><div class="agent__name">' + a.name + '</div>' +
      '<div class="agent__role">' + t("contact.agentRole") + '</div>' +
      '<div class="agent__contact">' +
        '<a href="tel:' + a.phoneHref + '">' + a.phone + '</a>' +
        '<a href="mailto:' + a.email + '">' + a.email + '</a>' +
        '<span style="color:var(--muted)">' + SITE.company + '</span>' +
      '</div></div>';
  }

  /* ---------- hero stat (počet volných) ---------- */
  function fillHeroStat() {
    var n = APARTMENTS.filter(function (a) { return a.status === "available"; }).length;
    var el = $("#statAvail"); if (el) { el.setAttribute("data-count", n); el.textContent = n; }
  }

  /* ---------- nav: scroll, burger, smooth ---------- */
  function initNav() {
    var nav = $("#nav");
    var onScroll = function () { nav.classList.toggle("is-scrolled", window.scrollY > 40); };
    onScroll(); window.addEventListener("scroll", onScroll, { passive: true });

    var burger = $("#navBurger"), links = $("#navLinks");
    burger.addEventListener("click", function () {
      var open = links.classList.toggle("is-open");
      burger.setAttribute("aria-expanded", open ? "true" : "false");
    });
    $$("#navLinks a, .nav__cta").forEach(function (a) {
      a.addEventListener("click", function () {
        links.classList.remove("is-open");
        burger.setAttribute("aria-expanded", "false");
      });
    });
  }

  /* ---------- reveal animace ---------- */
  var io;
  function observeReveal(scope) {
    if (!("IntersectionObserver" in window)) { $$(".reveal", scope).forEach(function (e) { e.classList.add("is-visible"); }); return; }
    if (!io) io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) { if (en.isIntersecting) { en.target.classList.add("is-visible"); io.unobserve(en.target); } });
    }, { threshold: 0.12, rootMargin: "0px 0px -8% 0px" });
    $$(".reveal", scope || document).forEach(function (e) { if (!e.classList.contains("is-visible")) io.observe(e); });
  }

  /* ---------- jazykové přepínače ---------- */
  $$(".lang__btn").forEach(function (b) {
    b.addEventListener("click", function () { if (b.getAttribute("data-lang") !== lang) setLang(b.getAttribute("data-lang")); });
  });

  /* ---------- filtry ---------- */
  function initFilters() {
    var lay = $('#expFilter .chips[data-filter="layout"]');
    if (lay) lay.addEventListener("click", function (e) {
      var btn = e.target.closest(".chip"); if (!btn) return;
      $$(".chip", lay).forEach(function (c) { c.classList.remove("is-active"); });
      btn.classList.add("is-active");
      expLayout = btn.getAttribute("data-val");
      renderExplorer();
    });
    var oa = $("#onlyAvail");
    if (oa) oa.addEventListener("change", function () { expOnlyAvail = oa.checked; renderExplorer(); });
  }

  /* ---------- render vše (po změně jazyka) ---------- */
  function renderAll() {
    renderLocation(); renderCarousel(); renderStandards();
    renderExplorer(); renderCommercial(); populateUnitSelect();
    fillContacts(); fillHeroStat();
  }

  /* ---------- hero video: přepínač zvuku ---------- */
  function initReel() {
    var v = $("#heroVideo"), b = $("#heroSound");
    if (!v || !b) return;
    b.addEventListener("click", function () {
      if (v.muted) {
        v.muted = false; try { v.volume = 1; } catch (e) {}
        var p = v.play(); if (p && p.catch) p.catch(function () {});
        b.classList.add("is-on");
      } else { v.muted = true; b.classList.remove("is-on"); }
    });
  }

  /* ---------- init ---------- */
  document.addEventListener("DOMContentLoaded", function () {
    applyI18n();
    renderAll();
    initNav(); initFilters(); initForm(); initReel(); initBuilding3D();
    observeReveal(document);
  });
})();
