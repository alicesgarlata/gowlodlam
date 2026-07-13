(function () {
  function initLightbox() {
    var images = document.querySelectorAll("figure img");
    if (!images.length) return;

    var overlay = document.createElement("div");
    overlay.className = "lightbox-overlay";
    overlay.setAttribute("role", "dialog");
    overlay.setAttribute("aria-modal", "true");
    overlay.setAttribute("aria-label", "Image viewer");
    overlay.innerHTML =
      '<button type="button" class="lightbox-close" aria-label="Close image viewer">&times;</button>' +
      '<img class="lightbox-img" alt="">' +
      '<div class="lightbox-hint">Scroll or pinch to zoom &middot; drag to pan &middot; double-click to reset &middot; Esc to close</div>';
    document.body.appendChild(overlay);

    var img = overlay.querySelector(".lightbox-img");
    var closeBtn = overlay.querySelector(".lightbox-close");

    var scale = 1;
    var originX = 0;
    var originY = 0;
    var isDragging = false;
    var startX = 0;
    var startY = 0;
    var lastTouchDist = null;
    var lastOpener = null;

    function setTransform() {
      img.style.transform =
        "translate(" + originX + "px, " + originY + "px) scale(" + scale + ")";
      img.style.cursor = scale > 1 ? "grab" : "zoom-in";
    }

    function resetTransform() {
      scale = 1;
      originX = 0;
      originY = 0;
      setTransform();
    }

    function openLightbox(src, alt, opener) {
      img.src = src;
      img.alt = alt || "";
      resetTransform();
      overlay.classList.add("open");
      document.body.style.overflow = "hidden";
      lastOpener = opener || null;
      closeBtn.focus();
    }

    function closeLightbox() {
      overlay.classList.remove("open");
      document.body.style.overflow = "";
      if (lastOpener) lastOpener.focus();
    }

    function getTouchDist(touches) {
      var dx = touches[0].clientX - touches[1].clientX;
      var dy = touches[0].clientY - touches[1].clientY;
      return Math.sqrt(dx * dx + dy * dy);
    }

    images.forEach(function (image) {
      image.classList.add("zoomable-img");
      image.tabIndex = 0;
      image.setAttribute("role", "button");
      image.setAttribute(
        "aria-label",
        "Open full-size image: " + (image.alt || "image")
      );

      image.addEventListener("click", function () {
        openLightbox(image.currentSrc || image.src, image.alt, image);
      });

      image.addEventListener("keydown", function (e) {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          openLightbox(image.currentSrc || image.src, image.alt, image);
        }
      });
    });

    closeBtn.addEventListener("click", closeLightbox);

    overlay.addEventListener("click", function (e) {
      if (e.target === overlay) closeLightbox();
    });

    document.addEventListener("keydown", function (e) {
      if (!overlay.classList.contains("open")) return;
      if (e.key === "Escape") closeLightbox();
    });

    overlay.addEventListener(
      "wheel",
      function (e) {
        if (!overlay.classList.contains("open")) return;
        e.preventDefault();
        var delta = e.deltaY < 0 ? 0.18 : -0.18;
        scale = Math.min(6, Math.max(1, scale + delta));
        if (scale === 1) {
          originX = 0;
          originY = 0;
        }
        setTransform();
      },
      { passive: false }
    );

    img.addEventListener("dblclick", function () {
      if (scale > 1) {
        resetTransform();
      } else {
        scale = 2.5;
        setTransform();
      }
    });

    img.addEventListener("mousedown", function (e) {
      if (scale <= 1) return;
      isDragging = true;
      startX = e.clientX - originX;
      startY = e.clientY - originY;
      img.style.cursor = "grabbing";
      e.preventDefault();
    });
    window.addEventListener("mousemove", function (e) {
      if (!isDragging) return;
      originX = e.clientX - startX;
      originY = e.clientY - startY;
      setTransform();
    });
    window.addEventListener("mouseup", function () {
      isDragging = false;
      if (scale > 1) img.style.cursor = "grab";
    });

    img.addEventListener(
      "touchstart",
      function (e) {
        if (e.touches.length === 1 && scale > 1) {
          isDragging = true;
          startX = e.touches[0].clientX - originX;
          startY = e.touches[0].clientY - originY;
        } else if (e.touches.length === 2) {
          lastTouchDist = getTouchDist(e.touches);
        }
      },
      { passive: true }
    );

    img.addEventListener(
      "touchmove",
      function (e) {
        if (e.touches.length === 1 && isDragging) {
          originX = e.touches[0].clientX - startX;
          originY = e.touches[0].clientY - startY;
          setTransform();
        } else if (e.touches.length === 2 && lastTouchDist) {
          var dist = getTouchDist(e.touches);
          var delta = (dist - lastTouchDist) * 0.012;
          scale = Math.min(6, Math.max(1, scale + delta));
          lastTouchDist = dist;
          setTransform();
        }
      },
      { passive: true }
    );

    img.addEventListener("touchend", function (e) {
      isDragging = false;
      if (e.touches.length < 2) lastTouchDist = null;
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initLightbox);
  } else {
    initLightbox();
  }
})();
