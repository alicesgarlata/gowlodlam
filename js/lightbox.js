(function () {
  "use strict";

  function initSlideshow() {
    var root = document.querySelector(".myth-slideshow");
    if (!root) return;

    var track = root.querySelector(".slideshow-track");
    var slides = Array.prototype.slice.call(root.querySelectorAll(".slide"));
    var dots = Array.prototype.slice.call(root.querySelectorAll(".slide-dot"));
    var prevBtn = root.querySelector(".slide-prev");
    var nextBtn = root.querySelector(".slide-next");
    if (!track || !slides.length) return;

    var index = 0;
    var timer = null;
    var AUTO_DELAY = 6500;

    function goTo(i) {
      index = (i + slides.length) % slides.length;
      track.style.transform = "translateX(-" + index * 100 + "%)";
      dots.forEach(function (dot, di) {
        dot.classList.toggle("active", di === index);
      });
    }
    function next() { goTo(index + 1); }
    function prev() { goTo(index - 1); }
    function stopAuto() {
      if (timer) window.clearInterval(timer);
      timer = null;
    }
    function startAuto() {
      stopAuto();
      timer = window.setInterval(next, AUTO_DELAY);
    }

    if (prevBtn) prevBtn.addEventListener("click", function () { prev(); startAuto(); });
    if (nextBtn) nextBtn.addEventListener("click", function () { next(); startAuto(); });
    dots.forEach(function (dot, di) {
      dot.addEventListener("click", function () { goTo(di); startAuto(); });
    });

    root.addEventListener("mouseenter", stopAuto);
    root.addEventListener("mouseleave", startAuto);
    root.addEventListener("focusin", stopAuto);
    root.addEventListener("focusout", function (event) {
      if (!root.contains(event.relatedTarget)) startAuto();
    });
    root.addEventListener("keydown", function (event) {
      if (event.key === "ArrowLeft") { prev(); startAuto(); }
      if (event.key === "ArrowRight") { next(); startAuto(); }
    });

    var touchStartX = null;
    track.addEventListener("touchstart", function (event) {
      touchStartX = event.touches[0].clientX;
      stopAuto();
    }, { passive: true });
    track.addEventListener("touchend", function (event) {
      if (touchStartX === null) return;
      var dx = event.changedTouches[0].clientX - touchStartX;
      if (Math.abs(dx) > 40) dx < 0 ? next() : prev();
      touchStartX = null;
      startAuto();
    }, { passive: true });

    goTo(0);
    startAuto();
  }

  function initLightbox() {
    var images = Array.prototype.slice.call(
      document.querySelectorAll("figure img, .image-slot.filled img")
    );
    if (!images.length) return;

    var overlay = document.createElement("div");
    overlay.className = "lightbox-overlay";
    overlay.setAttribute("role", "dialog");
    overlay.setAttribute("aria-modal", "true");
    overlay.setAttribute("aria-label", "Image viewer");
    overlay.innerHTML =
      '<button type="button" class="lightbox-close" aria-label="Close image viewer">&times;</button>' +
      '<button type="button" class="lightbox-nav lightbox-prev" aria-label="Previous image">&#8249;</button>' +
      '<div class="lightbox-stage"><img class="lightbox-img" alt=""></div>' +
      '<button type="button" class="lightbox-nav lightbox-next" aria-label="Next image">&#8250;</button>' +
      '<div class="lightbox-toolbar" aria-label="Zoom controls">' +
        '<button type="button" class="lightbox-zoom-out" aria-label="Zoom out">&minus;</button>' +
        '<span class="lightbox-zoom-level" aria-live="polite">100%</span>' +
        '<button type="button" class="lightbox-zoom-in" aria-label="Zoom in">+</button>' +
        '<button type="button" class="lightbox-reset" aria-label="Reset zoom">Reset</button>' +
      '</div>' +
      '<p class="lightbox-caption"></p>';
    document.body.appendChild(overlay);

    var viewer = overlay.querySelector(".lightbox-img");
    var stage = overlay.querySelector(".lightbox-stage");
    var closeBtn = overlay.querySelector(".lightbox-close");
    var prevBtn = overlay.querySelector(".lightbox-prev");
    var nextBtn = overlay.querySelector(".lightbox-next");
    var zoomInBtn = overlay.querySelector(".lightbox-zoom-in");
    var zoomOutBtn = overlay.querySelector(".lightbox-zoom-out");
    var resetBtn = overlay.querySelector(".lightbox-reset");
    var zoomLabel = overlay.querySelector(".lightbox-zoom-level");
    var caption = overlay.querySelector(".lightbox-caption");
    var current = 0;
    var scale = 1;
    var x = 0;
    var y = 0;
    var dragging = false;
    var dragStartX = 0;
    var dragStartY = 0;
    var previousFocus = null;

    function applyTransform() {
      viewer.style.transform = "translate(" + x + "px," + y + "px) scale(" + scale + ")";
      viewer.classList.toggle("is-zoomed", scale > 1);
      zoomLabel.textContent = Math.round(scale * 100) + "%";
    }
    function resetZoom() {
      scale = 1;
      x = 0;
      y = 0;
      applyTransform();
    }
    function setZoom(nextScale) {
      scale = Math.max(1, Math.min(4, nextScale));
      if (scale === 1) { x = 0; y = 0; }
      applyTransform();
    }
    function show(index) {
      current = (index + images.length) % images.length;
      var source = images[current];
      viewer.src = source.currentSrc || source.src;
      viewer.alt = source.alt || "Expanded image";
      caption.textContent = source.alt || "";
      resetZoom();
      var multiple = images.length > 1;
      prevBtn.hidden = !multiple;
      nextBtn.hidden = !multiple;
    }
    function open(index) {
      previousFocus = document.activeElement;
      show(index);
      overlay.classList.add("open");
      document.body.classList.add("lightbox-open");
      closeBtn.focus();
    }
    function close() {
      overlay.classList.remove("open");
      document.body.classList.remove("lightbox-open");
      viewer.removeAttribute("src");
      if (previousFocus) previousFocus.focus();
    }

    images.forEach(function (image, index) {
      image.classList.add("zoomable-img");
      image.tabIndex = 0;
      image.setAttribute("role", "button");
      image.setAttribute("aria-label", (image.alt || "Image") + ". Open enlarged view");
      image.addEventListener("click", function () { open(index); });
      image.addEventListener("keydown", function (event) {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          open(index);
        }
      });
    });

    closeBtn.addEventListener("click", close);
    prevBtn.addEventListener("click", function () { show(current - 1); });
    nextBtn.addEventListener("click", function () { show(current + 1); });
    zoomInBtn.addEventListener("click", function () { setZoom(scale + 0.25); });
    zoomOutBtn.addEventListener("click", function () { setZoom(scale - 0.25); });
    resetBtn.addEventListener("click", resetZoom);
    overlay.addEventListener("click", function (event) {
      if (event.target === overlay || event.target === stage) close();
    });
    overlay.addEventListener("wheel", function (event) {
      event.preventDefault();
      setZoom(scale + (event.deltaY < 0 ? 0.25 : -0.25));
    }, { passive: false });
    overlay.addEventListener("keydown", function (event) {
      if (event.key === "Escape") close();
      if (event.key === "ArrowLeft") show(current - 1);
      if (event.key === "ArrowRight") show(current + 1);
      if (event.key === "+" || event.key === "=") setZoom(scale + 0.25);
      if (event.key === "-") setZoom(scale - 0.25);
    });

    viewer.addEventListener("pointerdown", function (event) {
      if (scale <= 1) return;
      dragging = true;
      dragStartX = event.clientX - x;
      dragStartY = event.clientY - y;
      viewer.setPointerCapture(event.pointerId);
    });
    viewer.addEventListener("pointermove", function (event) {
      if (!dragging) return;
      x = event.clientX - dragStartX;
      y = event.clientY - dragStartY;
      applyTransform();
    });
    viewer.addEventListener("pointerup", function () { dragging = false; });
    viewer.addEventListener("pointercancel", function () { dragging = false; });
  }

  function init() {
    initSlideshow();
    initLightbox();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
