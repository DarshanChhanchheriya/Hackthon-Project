// Adds a show/hide eye button to every password field on the page,
// automatically — no per-page wiring needed. Just include this script.
(function () {
  const EYE = '<svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/><path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/></svg>';
  const EYE_OFF = '<svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.542-7a9.97 9.97 0 011.563-3.029m3.29-2.317A9.958 9.958 0 0112 5c4.478 0 8.268 2.943 9.542 7a9.973 9.973 0 01-1.622 3.056M9.879 9.879a3 3 0 104.242 4.242M3 3l18 18"/></svg>';

  function wrap(input) {
    if (input.dataset.toggleWrapped) return;
    input.dataset.toggleWrapped = "1";

    const wrapper = document.createElement("div");
    wrapper.style.position = "relative";
    input.parentNode.insertBefore(wrapper, input);
    wrapper.appendChild(input);
    input.style.paddingRight = "2.75rem";

    const btn = document.createElement("button");
    btn.type = "button";
    btn.setAttribute("aria-label", "Show password");
    btn.tabIndex = -1;
    btn.style.cssText =
      "position:absolute; right:0.75rem; top:0; bottom:0; margin:0; background:none; border:none; padding:0; cursor:pointer; color:var(--text-muted); display:flex; align-items:center; justify-content:center; line-height:0;";
    btn.innerHTML = EYE;
    btn.addEventListener("click", () => {
      const show = input.type === "password";
      input.type = show ? "text" : "password";
      btn.innerHTML = show ? EYE_OFF : EYE;
      btn.setAttribute("aria-label", show ? "Hide password" : "Show password");
    });
    wrapper.appendChild(btn);
  }

  function init() {
    document.querySelectorAll('input[type="password"]:not([aria-hidden="true"])').forEach(wrap);
  }

  document.addEventListener("DOMContentLoaded", init);
  setTimeout(init, 0); // catch fields present before DOMContentLoaded fires
})();
