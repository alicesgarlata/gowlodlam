(function () {
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
    var AUTO_DELAY = 6500;
    var timer = null;

    function goTo(i) {
      index = (i + slides.length) % slides.length;
      track.style.transform = "translateX(-" + index * 100 + "%)";
      dots.forEach(function (dot, di) {
        dot.classList.toggle("active", di === index);
      });
    }

    function next() { goTo(index + 1); }
    function prev() { goTo(index - 1); }

    function startAuto() {
      stopAuto();
      timer = window.setInterval(next, AUTO_DELAY);
    }
    function stopAuto() {
      if (timer) {
        window.clearInterval(timer);
        timer = null;
      }
    }
    function restartAuto() {
      // called after manual interaction, so the next auto-advance
      // waits a full interval rather than firing immediately
      startAuto();
    }

    if (prevBtn) {
      prevBtn.addEventListener("click", function () {
        prev();
        restartAuto();
      });
    }
    if (nextBtn) {
      nextBtn.addEventListener("click", function () {
        next();
        restartAuto();
      });
    }
    dots.forEach(function (dot, di) {
      dot.addEventListener("click", function () {
        goTo(di);
        restartAuto();
      });
    });

    root.addEventListener("mouseenter", stopAuto);
    root.addEventListener("mouseleave", startAuto);
    root.addEventListener("focusin", stopAuto);
    root.addEventListener("focusout", function (e) {
      if (!root.contains(e.relatedTarget)) startAuto();
    });

    root.tabIndex = -1;
    root.addEventListener("keydown", function (e) {
      if (e.key === "ArrowLeft") {
        prev();
        restartAuto();
      } else if (e.key === "ArrowRight") {
        next();
        restartAuto();
      }
    });

    // basic touch swipe
    var touchStartX = null;
    track.addEventListener(
      "touchstart",
      function (e) {
        touchStartX = e.touches[0].clientX;
        stopAuto();
      },
      { passive: true }
    );
    track.addEventListener(
      "touchend",
      function (e) {
        if (touchStartX === null) return;
        var dx = e.changedTouches[0].clientX - touchStartX;
        if (Math.abs(dx) > 40) {
          if (dx < 0) next();
          else prev();
        }
        touchStartX = null;
        startAuto();
      },
      { passive: true }
    );

    goTo(0);
    startAuto();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initSlideshow);
  } else {
    initSlideshow();
  }
})();
