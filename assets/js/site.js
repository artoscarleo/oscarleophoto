/* ==========================================================================
   Oscar Leo Photography — site behaviour
   Vanilla JS, no dependencies. ~6KB unminified.

   Deliberately not using GSAP: every animation here is a class toggle driving
   a CSS transition on transform/opacity. A 70KB animation library would cost
   more than the effects are worth on an image-heavy site, and the compositor
   already does this work for free.

   Every feature degrades to plain, fully usable HTML if this file fails.
   ========================================================================== */

(function () {
  'use strict';

  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

  /* Whether the last interaction came from the keyboard. Moving focus is right
     for keyboard and screen-reader users, but doing it after a tap leaves a
     visible outline around the logo or the menu button on iOS, which reads as
     a stray box. */
  var keyboardMode = false;
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Tab' || e.key === 'Enter' || e.key === ' ' || e.key === 'Escape') keyboardMode = true;
  }, true);
  document.addEventListener('pointerdown', function () { keyboardMode = false; }, true);

  /* Both the drawer and the lightbox are hidden with `visibility: hidden`, and
     calling focus() on a still-hidden element is a silent no-op — the browser
     has not applied the style change yet when the click handler runs. Waiting a
     frame lets the visibility flip land first, so focus actually moves into the
     dialog for keyboard and screen-reader users. */
  function focusWhenVisible(el) {
    if (!el) return;
    window.requestAnimationFrame(function () {
      window.requestAnimationFrame(function () { el.focus(); });
    });
  }

  /* ---------- Header condense on scroll ---------------------------------- */
  function initHeader() {
    var header = document.querySelector('[data-header]');
    if (!header) return;
    var ticking = false;

    function update() {
      header.setAttribute('data-scrolled', window.scrollY > 40 ? 'true' : 'false');
      // Drives the floating back-to-top mark: it only earns its place once
      // there is enough page behind you to want the way back.
      document.documentElement.setAttribute(
        'data-past-fold', window.scrollY > window.innerHeight ? 'true' : 'false');
      ticking = false;
    }
    update();

    window.addEventListener('scroll', function () {
      if (!ticking) {
        ticking = true;
        window.requestAnimationFrame(update);
      }
    }, { passive: true });
  }

  /* ---------- Mobile navigation ------------------------------------------ */
  function initMobileNav() {
    var nav = document.querySelector('[data-mobile-nav]');
    var openBtn = document.querySelector('[data-nav-open]');
    var closeBtn = document.querySelector('[data-nav-close]');
    if (!nav || !openBtn) return;

    function setOpen(open) {
      nav.setAttribute('data-open', open ? 'true' : 'false');
      nav.setAttribute('aria-hidden', open ? 'false' : 'true');
      openBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
      document.body.setAttribute('data-scroll-locked', open ? 'true' : 'false');
      if (open) {
        focusWhenVisible(nav);
      } else if (keyboardMode) {
        openBtn.focus();     // only return focus when it was a keyboard journey
      }
    }

    openBtn.addEventListener('click', function () { setOpen(true); });
    if (closeBtn) closeBtn.addEventListener('click', function () { setOpen(false); });

    nav.addEventListener('click', function (e) {
      if (e.target.closest('a')) setOpen(false);
    });

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && nav.getAttribute('data-open') === 'true') setOpen(false);
    });

    // Keep focus inside the drawer while it is open.
    nav.addEventListener('keydown', function (e) {
      if (e.key !== 'Tab') return;
      var items = nav.querySelectorAll('a, button');
      if (!items.length) return;
      var first = items[0];
      var last = items[items.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    });
  }

  /* ---------- Scroll reveals ---------------------------------------------
     One shared observer, unobserved after firing. Elements are revealed
     immediately if IntersectionObserver is missing or motion is reduced,
     so content is never trapped behind an effect that did not run.
     -------------------------------------------------------------------- */
  function initReveals() {
    var targets = document.querySelectorAll('[data-reveal], [data-reveal-img]');
    if (!targets.length) return;

    function showAll() {
      Array.prototype.forEach.call(targets, function (el) {
        el.setAttribute(el.hasAttribute('data-reveal-img') ? 'data-reveal-img' : 'data-reveal', 'is-visible');
      });
    }

    if (reduceMotion.matches || !('IntersectionObserver' in window)) {
      showAll();
      return;
    }

    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        var el = entry.target;
        el.setAttribute(el.hasAttribute('data-reveal-img') ? 'data-reveal-img' : 'data-reveal', 'is-visible');
        observer.unobserve(el);
      });
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.08 });

    Array.prototype.forEach.call(targets, function (el, i) {
      // Stagger within a group, capped so a long gallery never crawls.
      if (!el.style.getPropertyValue('--i')) {
        var group = el.getAttribute('data-reveal-group');
        if (group) el.style.setProperty('--i', String(Math.min(i % 8, 7)));
      }
      observer.observe(el);
    });

    // If the visitor turns reduced-motion on mid-visit, stop hiding things.
    reduceMotion.addEventListener('change', function (e) { if (e.matches) showAll(); });
  }

  /* ---------- Service backdrop -------------------------------------------
     Hovering a service row fades a full-bleed photograph in behind the list.
     Decorative only: the layer is aria-hidden and never interactive, and the
     list is perfectly usable if none of this runs.
     -------------------------------------------------------------------- */
  function initServiceBackdrop() {
    var section = document.querySelector('.services');
    var list = document.querySelector('[data-service-list]');
    var bg = document.querySelector('[data-service-bg]');
    if (!section || !list || !bg) return;

    var images = bg.querySelectorAll('img');
    if (!images.length) return;

    // Checked per event rather than once at load, so a window that starts
    // narrow, or a visitor who turns reduced-motion on mid-visit, behaves.
    var fine = window.matchMedia('(hover: hover) and (pointer: fine)');

    function clear() {
      Array.prototype.forEach.call(images, function (img) {
        img.setAttribute('data-active', 'false');
      });
      Array.prototype.forEach.call(list.querySelectorAll('[data-preview-index]'), function (row) {
        row.setAttribute('data-current', 'false');
      });
      section.setAttribute('data-bg-active', 'false');
    }

    Array.prototype.forEach.call(list.querySelectorAll('[data-preview-index]'), function (row) {
      row.addEventListener('pointerenter', function () {
        if (!fine.matches) return;
        var idx = row.getAttribute('data-preview-index');
        Array.prototype.forEach.call(images, function (img) {
          img.setAttribute('data-active', img.getAttribute('data-bg-index') === idx ? 'true' : 'false');
        });
        section.setAttribute('data-bg-active', 'true');
      });
      // Keyboard users get the same cue when tabbing through the list.
      row.addEventListener('focus', function () {
        var idx = row.getAttribute('data-preview-index');
        Array.prototype.forEach.call(images, function (img) {
          img.setAttribute('data-active', img.getAttribute('data-bg-index') === idx ? 'true' : 'false');
        });
        section.setAttribute('data-bg-active', 'true');
      });
    });

    list.addEventListener('pointerleave', clear);
    list.addEventListener('focusout', function (e) {
      if (!list.contains(e.relatedTarget)) clear();
    });
    fine.addEventListener('change', clear);

    /* ----- Touch devices -------------------------------------------------
       There is no hover on a phone, so the photographs would never appear at
       all. Instead they cycle by themselves. Three seconds, not one: the
       crossfade alone runs 620ms, so a shorter interval never lets an image
       settle and keeps pulling files down.

       The timer only runs while the section is actually on screen and the tab
       is visible, so it costs nothing on the rest of the page and does not sit
       burning battery in a background tab. */
    var coarse = window.matchMedia('(hover: none), (pointer: coarse)');
    var INTERVAL = 3000;
    var timer = null;
    var idx = 0;

    var rows = list.querySelectorAll('[data-preview-index]');

    function show(i) {
      idx = (i + images.length) % images.length;
      Array.prototype.forEach.call(images, function (img, n) {
        img.setAttribute('data-active', n === idx ? 'true' : 'false');
      });
      // Mark the row the photograph belongs to, so the name it matches lifts
      // with it rather than the photograph changing behind an inert list.
      Array.prototype.forEach.call(rows, function (row, n) {
        row.setAttribute('data-current', n === idx ? 'true' : 'false');
      });
      section.setAttribute('data-bg-active', 'true');
    }

    function stop() {
      if (timer) { window.clearInterval(timer); timer = null; }
    }

    function start() {
      if (timer || !coarse.matches) return;
      show(idx);
      // Someone who asked for less motion still gets a photograph — it simply
      // does not move.
      if (reduceMotion.matches) return;
      timer = window.setInterval(function () { show(idx + 1); }, INTERVAL);
    }

    if (coarse.matches && 'IntersectionObserver' in window) {
      new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) start(); else stop();
        });
      }, { threshold: 0.15 }).observe(section);
    } else if (coarse.matches) {
      start();
    }

    document.addEventListener('visibilitychange', function () {
      if (document.hidden) stop(); else if (coarse.matches) start();
    });

    reduceMotion.addEventListener('change', function (e) {
      if (e.matches) stop(); else if (coarse.matches) start();
    });
    coarse.addEventListener('change', function (e) {
      if (!e.matches) { stop(); clear(); } else { start(); }
    });
  }

  /* ---------- Hero slideshow ---------------------------------------------
     Six photographs crossfading behind the headline. Five seconds rather than
     three: these are full-screen images and the crossfade alone runs 1.2s, so
     a shorter interval would never let one settle.

     It runs only while the hero is on screen and the tab is visible, so it
     stops as soon as the visitor scrolls into the page.
     -------------------------------------------------------------------- */
  function initHeroSlides() {
    // Two of these on the homepage — the hero and the photo band further down.
    // Each keeps its own timer, and each only runs while it is on screen.
    var wraps = document.querySelectorAll('[data-hero-slides]');
    Array.prototype.forEach.call(wraps, initOne);
  }

  function initOne(wrap) {
    var slides = wrap.querySelectorAll('img');
    if (slides.length < 2) return;

    var INTERVAL = 5000;
    var timer = null;
    var idx = 0;

    function show(i) {
      idx = (i + slides.length) % slides.length;
      Array.prototype.forEach.call(slides, function (img, n) {
        img.setAttribute('data-active', n === idx ? 'true' : 'false');
      });
    }

    function stop() { if (timer) { window.clearInterval(timer); timer = null; } }

    function start() {
      // Someone who asked for less motion keeps the first photograph, still.
      if (timer || reduceMotion.matches) return;
      timer = window.setInterval(function () { show(idx + 1); }, INTERVAL);
    }

    if ('IntersectionObserver' in window) {
      new IntersectionObserver(function (entries) {
        entries.forEach(function (e) { if (e.isIntersecting) start(); else stop(); });
      }, { threshold: 0.2 }).observe(wrap);
    } else {
      start();
    }

    document.addEventListener('visibilitychange', function () {
      if (document.hidden) stop(); else start();
    });
    reduceMotion.addEventListener('change', function (e) {
      if (e.matches) { stop(); show(0); } else { start(); }
    });
  }

  /* ---------- Parallax ----------------------------------------------------
     The photograph behind a band drifts against the scroll. The CSS owns how
     far it may travel (--parallax-overhang, which also sizes the overhang on
     the media box); this reads that value rather than keeping its own copy, so
     the two cannot drift apart and expose an edge.

     Work happens on a rAF and only while the band is on screen.
     -------------------------------------------------------------------- */
  function initParallax() {
    var boxes = document.querySelectorAll('[data-parallax]');
    if (!boxes.length || reduceMotion.matches) return;
    Array.prototype.forEach.call(boxes, initOneParallax);
  }

  function initOneParallax(box) {
    var img = box.querySelector('img');
    var section = box.parentElement;
    if (!img || !section) return;

    var ticking = false;

    function travel(height) {
      var pct = parseFloat(
        window.getComputedStyle(section).getPropertyValue('--parallax-overhang'));
      return height * (isNaN(pct) ? 0 : pct) / 100;
    }

    function frame() {
      ticking = false;
      var r = section.getBoundingClientRect();
      var vh = window.innerHeight || document.documentElement.clientHeight;
      // Nowhere near the viewport: nothing to move. This is the cheap guard —
      // the effect is never gated on the observer having reported, because a
      // late or undelivered callback would freeze the photograph mid-travel.
      if (r.bottom < -vh || r.top > vh * 2) return;
      // +1 as the band enters from the bottom, 0 dead centre, -1 as it leaves
      var progress = ((r.top + r.height / 2) - vh / 2) / ((vh + r.height) / 2);
      if (progress > 1) progress = 1;
      if (progress < -1) progress = -1;
      img.style.transform =
        'translate3d(0,' + (progress * travel(r.height)).toFixed(2) + 'px,0)';
    }

    function onScroll() {
      if (ticking) return;
      ticking = true;
      window.requestAnimationFrame(frame);
    }

    // The observer's only job is the compositor hint, so nothing about whether
    // the photograph moves depends on when its callback arrives.
    if ('IntersectionObserver' in window) {
      new IntersectionObserver(function (entries) {
        entries.forEach(function (e) {
          box.setAttribute('data-parallax-active', e.isIntersecting ? 'true' : 'false');
        });
      }).observe(section);
    }

    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onScroll, { passive: true });
    frame();
  }

  /* ---------- Lightbox ----------------------------------------------------
     Tiles are real <button>s in the markup, so the gallery is keyboard
     operable whether or not this initialises.
     -------------------------------------------------------------------- */
  function initLightbox() {
    var box = document.querySelector('[data-lightbox]');
    if (!box) return;
    var tiles = Array.prototype.slice.call(document.querySelectorAll('[data-lightbox-item]'));
    if (!tiles.length) return;

    var stage = box.querySelector('[data-lightbox-image]');
    var caption = box.querySelector('[data-lightbox-caption]');
    var counter = box.querySelector('[data-lightbox-count]');
    var closeBtn = box.querySelector('[data-lightbox-close]');
    var prevBtn = box.querySelector('[data-lightbox-prev]');
    var nextBtn = box.querySelector('[data-lightbox-next]');
    var index = 0;
    var lastFocused = null;

    function show(i) {
      index = (i + tiles.length) % tiles.length;
      var tile = tiles[index];
      var img = tile.querySelector('img');
      stage.src = tile.getAttribute('data-full') || img.currentSrc || img.src;
      stage.alt = img.alt || '';
      if (caption) caption.textContent = img.alt || '';
      if (counter) counter.textContent = (index + 1) + ' / ' + tiles.length;
    }

    function open(i) {
      lastFocused = document.activeElement;
      show(i);
      box.setAttribute('data-open', 'true');
      box.setAttribute('aria-hidden', 'false');
      document.body.setAttribute('data-scroll-locked', 'true');
      focusWhenVisible(closeBtn);
    }

    function close() {
      box.setAttribute('data-open', 'false');
      box.setAttribute('aria-hidden', 'true');
      document.body.setAttribute('data-scroll-locked', 'false');
      if (lastFocused) lastFocused.focus();
    }

    tiles.forEach(function (tile, i) {
      tile.addEventListener('click', function () { open(i); });
    });

    if (closeBtn) closeBtn.addEventListener('click', close);
    if (prevBtn) prevBtn.addEventListener('click', function () { show(index - 1); });
    if (nextBtn) nextBtn.addEventListener('click', function () { show(index + 1); });

    /* The image element now fills the whole stage and letterboxes itself, so a
       click in the empty margin beside a portrait still lands on the <img>.
       Work out where the visible picture actually sits and only keep the click
       if it is on the picture itself — otherwise it counts as a backdrop click. */
    function pointIsOnPicture(e) {
      var r = stage.getBoundingClientRect();
      var nW = stage.naturalWidth, nH = stage.naturalHeight;
      if (!nW || !nH) return true;
      var scale = Math.min(r.width / nW, r.height / nH);
      var w = nW * scale, h = nH * scale;
      var left = r.left + (r.width - w) / 2;
      var top = r.top + (r.height - h) / 2;
      return e.clientX >= left && e.clientX <= left + w &&
             e.clientY >= top && e.clientY <= top + h;
    }

    box.addEventListener('click', function (e) {
      if (e.target === box || e.target.classList.contains('lightbox__stage')) { close(); return; }
      if (e.target === stage && !pointIsOnPicture(e)) close();
    });

    document.addEventListener('keydown', function (e) {
      if (box.getAttribute('data-open') !== 'true') return;
      if (e.key === 'Escape') { close(); }
      else if (e.key === 'ArrowLeft') { show(index - 1); }
      else if (e.key === 'ArrowRight') { show(index + 1); }
      else if (e.key === 'Tab') {
        var items = box.querySelectorAll('button');
        if (!items.length) return;
        var first = items[0], last = items[items.length - 1];
        if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
        else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
      }
    });

    // Swipe between images on touch devices.
    var startX = null;
    box.addEventListener('touchstart', function (e) { startX = e.changedTouches[0].clientX; }, { passive: true });
    box.addEventListener('touchend', function (e) {
      if (startX === null) return;
      var dx = e.changedTouches[0].clientX - startX;
      if (Math.abs(dx) > 55) show(index + (dx < 0 ? 1 : -1));
      startX = null;
    }, { passive: true });
  }

  /* ---------- Mark the current page in the nav --------------------------- */
  function initCurrentNav() {
    var path = window.location.pathname.replace(/index\.html$/, '').replace(/\/+$/, '') || '/';
    Array.prototype.forEach.call(document.querySelectorAll('[data-nav-link]'), function (a) {
      // a.pathname, not getAttribute('href') — the markup uses relative links so
      // the browser has to resolve them before they can be compared.
      var href = a.pathname.replace(/index\.html$/, '').replace(/\/+$/, '') || '/';
      if (href === path) a.setAttribute('aria-current', 'page');
    });
  }

  function init() {
    initHeader();
    initMobileNav();
    initReveals();
    initServiceBackdrop();
    initHeroSlides();
    initParallax();
    initLightbox();
    initCurrentNav();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
