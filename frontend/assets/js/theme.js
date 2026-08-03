(function () {
  const SUN = '<svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="4"/><path stroke-linecap="round" d="M12 2v2.2M12 19.8V22M4.2 4.2l1.55 1.55M18.25 18.25l1.55 1.55M2 12h2.2M19.8 12H22M4.2 19.8l1.55-1.55M18.25 5.75l1.55-1.55"/></svg>';
  const MOON = '<svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 1020.354 15.354z"/></svg>';

  function syncThemeIcons() {
    const isDark = (document.documentElement.getAttribute("data-theme") ||
      (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light")) === "dark";
    document.querySelectorAll("[data-theme-icon]").forEach((el) => {
      el.innerHTML = isDark ? SUN : MOON;
    });
  }

  const stored = localStorage.getItem("theme");
  if (stored) document.documentElement.setAttribute("data-theme", stored);
  document.addEventListener("DOMContentLoaded", syncThemeIcons);
  // In case this page injects the icon markup after DOMContentLoaded (e.g.
  // the shared topbar rendered by layout.js), re-sync shortly after too.
  setTimeout(syncThemeIcons, 0);

  window.toggleTheme = function () {
    const current = document.documentElement.getAttribute("data-theme") ||
      (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    const next = current === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("theme", next);

    document.querySelectorAll("[data-theme-icon]").forEach((el) => {
      el.style.transition = "transform .3s ease, opacity .2s ease";
      el.style.transform = "rotate(-90deg) scale(0.5)";
      el.style.opacity = "0";
      setTimeout(() => {
        el.innerHTML = next === "dark" ? SUN : MOON;
        el.style.transform = "rotate(0deg) scale(1)";
        el.style.opacity = "1";
      }, 150);
    });
  };

  window.syncThemeIcons = syncThemeIcons;
})();
