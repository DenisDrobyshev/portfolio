/* Мини-скрипт сайта-визитки: тема, фильтр проектов, reveal, год.
   Никаких зависимостей — чистый vanilla JS. */
(function () {
  "use strict";

  /* ---- Год в подвале ---- */
  var yearEl = document.getElementById("year");
  if (yearEl) yearEl.textContent = new Date().getFullYear();

  /* ---- Переключение темы (с запоминанием) ---- */
  var root = document.documentElement;
  var toggle = document.getElementById("themeToggle");
  var saved = null;
  try { saved = localStorage.getItem("theme"); } catch (e) {}
  if (saved) root.setAttribute("data-theme", saved);
  updateIcon();

  if (toggle) {
    toggle.addEventListener("click", function () {
      var next = root.getAttribute("data-theme") === "light" ? "dark" : "light";
      root.setAttribute("data-theme", next);
      try { localStorage.setItem("theme", next); } catch (e) {}
      updateIcon();
    });
  }

  function updateIcon() {
    var icon = toggle && toggle.querySelector(".theme-icon");
    if (icon) icon.textContent = root.getAttribute("data-theme") === "light" ? "☀" : "☾";
  }

  /* ---- Фильтр проектов ---- */
  var filters = document.querySelectorAll(".filter");
  var projects = document.querySelectorAll(".proj");
  filters.forEach(function (btn) {
    btn.addEventListener("click", function () {
      filters.forEach(function (b) { b.classList.remove("is-active"); });
      btn.classList.add("is-active");
      var cat = btn.getAttribute("data-filter");
      projects.forEach(function (p) {
        var show = cat === "all" || p.getAttribute("data-cat") === cat;
        p.classList.toggle("is-hidden", !show);
      });
    });
  });

  /* ---- Плавное появление при прокрутке ---- */
  var reveals = document.querySelectorAll(".reveal");
  if ("IntersectionObserver" in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add("in");
          io.unobserve(entry.target);
        }
      });
    }, { threshold: 0.12 });
    reveals.forEach(function (el) { io.observe(el); });
  } else {
    reveals.forEach(function (el) { el.classList.add("in"); });
  }
})();
