(function () {
  const stored = localStorage.getItem("theme");
  if (stored) document.documentElement.setAttribute("data-theme", stored);

  window.toggleTheme = function () {
    const current = document.documentElement.getAttribute("data-theme") ||
      (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    const next = current === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("theme", next);
    document.querySelectorAll("[data-theme-icon]").forEach((el) => {
      el.textContent = next === "dark" ? "☀️" : "🌙";
    });
  };
})();
