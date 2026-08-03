// Toasts, modals, skeleton helpers shared across all pages.
window.UI = (() => {
  function ensureToastContainer() {
    let el = document.getElementById("toast-container");
    if (!el) {
      el = document.createElement("div");
      el.id = "toast-container";
      el.className = "fixed top-5 right-5 z-[9999] flex flex-col gap-3";
      document.body.appendChild(el);
    }
    return el;
  }

  const ICONS = {
    success: '<svg class="w-5 h-5 text-emerald-500 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>',
    error: '<svg class="w-5 h-5 text-red-500 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg>',
    warning: '<svg class="w-5 h-5 text-amber-500 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01M10.29 3.86l-8.18 14.14A1 1 0 003 19.5h18a1 1 0 00.89-1.5L13.71 3.86a1 1 0 00-1.72 0z"/></svg>',
    info: '<svg class="w-5 h-5 text-blue-500 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>',
  };

  // FastAPI error `detail` can be a string, a validation-error array of
  // {msg, loc, ...} objects, or a nested object — normalize all of them
  // to a readable string instead of letting them stringify to "[object Object]".
  function formatError(detail, fallback = "Something went wrong") {
    if (!detail) return fallback;
    if (typeof detail === "string") return detail;
    if (detail instanceof Error) return detail.message || fallback;
    if (Array.isArray(detail)) {
      const msgs = detail.map((d) => (d && typeof d === "object" ? d.msg || JSON.stringify(d) : String(d)));
      return msgs.join("; ") || fallback;
    }
    if (typeof detail === "object") return detail.msg || detail.message || fallback;
    return String(detail);
  }

  function toast(message, type = "info", duration = 4000) {
    const container = ensureToastContainer();
    const el = document.createElement("div");
    el.className = "toast glass";
    const safeMessage = formatError(message, typeof message === "string" ? message : "Something went wrong");
    el.innerHTML = `${ICONS[type] || ICONS.info}<p class="text-sm font-medium" style="color:var(--text)">${safeMessage}</p>`;
    container.appendChild(el);
    setTimeout(() => {
      el.style.opacity = "0";
      el.style.transform = "translateX(24px)";
      el.style.transition = "all .25s ease";
      setTimeout(() => el.remove(), 250);
    }, duration);
  }

  function openModal(id) {
    document.getElementById(id)?.classList.remove("hidden");
  }
  function closeModal(id) {
    document.getElementById(id)?.classList.add("hidden");
  }

  function skeletonRows(count, cols) {
    return Array.from({ length: count })
      .map(
        () =>
          `<tr>${Array.from({ length: cols })
            .map(() => `<td class="py-3 px-4"><div class="skeleton h-4 w-full"></div></td>`)
            .join("")}</tr>`
      )
      .join("");
  }

  function statusBadge(status) {
    const map = {
      present: "badge-present", absent: "badge-absent", late: "badge-late",
      leave: "badge-leave", pending: "badge-pending", approved: "badge-approved", rejected: "badge-rejected",
    };
    return `<span class="badge ${map[status] || "badge-pending"}">${status}</span>`;
  }

  function formatDate(iso) {
    if (!iso) return "-";
    return new Date(iso).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
  }

  function formatTime(iso) {
    if (!iso) return "-";
    return new Date(iso).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
  }

  return { toast, openModal, closeModal, skeletonRows, statusBadge, formatDate, formatTime, formatError };
})();
