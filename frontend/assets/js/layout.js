// Renders the shared sidebar + topbar shell for all authenticated pages.
// Usage: call renderLayout("dashboard") from each page after DOM ready.
const NAV_ITEMS = [
  { key: "dashboard", href: "dashboard.html", label: "Dashboard", icon: "M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6", roles: ["student", "teacher", "admin"] },
  { key: "attendance", href: "attendance.html", label: "Attendance Session", icon: "M15 17h5l-1.4-1.4A2 2 0 0118 14.2V11a6 6 0 10-12 0v3.2c0 .53-.21 1.04-.6 1.4L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9", roles: ["teacher", "admin"] },
  { key: "qr", href: "qr.html", label: "QR Attendance", icon: "M12 4v1m6 11h2m-6 0h-2v4m0-11v3m0 0h.01M4 4h4v4H4V4zm0 12h4v4H4v-4zm12-12h4v4h-4V4z", roles: ["student", "teacher", "admin"] },
  { key: "students", href: "students.html", label: "Students", icon: "M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z", roles: ["teacher", "admin"] },
  { key: "teachers", href: "teachers.html", label: "Teachers", icon: "M17 20h5v-2a4 4 0 00-3-3.87M9 20H4v-2a4 4 0 013-3.87m6-2a4 4 0 10-4-4 4 4 0 004 4zm6 0a4 4 0 10-4-4", roles: ["admin"] },
  { key: "leave", href: "leave.html", label: "Leave Management", icon: "M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z", roles: ["student", "teacher", "admin"] },
  { key: "analytics", href: "analytics.html", label: "Analytics", icon: "M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z", roles: ["teacher", "admin"] },
  { key: "reports", href: "reports.html", label: "Reports", icon: "M9 17v-2a4 4 0 014-4h4M9 17H7a2 2 0 01-2-2V5a2 2 0 012-2h6l4 4v2M9 17h6a2 2 0 002-2v-3", roles: ["teacher", "admin"] },
  { key: "notifications", href: "notifications.html", label: "Notifications", icon: "M15 17h5l-1.4-1.4A2 2 0 0118 14.2V11a6 6 0 10-12 0v3.2c0 .53-.21 1.04-.6 1.4L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9", roles: ["student", "teacher", "admin"] },
  { key: "settings", href: "settings.html", label: "Settings", icon: "M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z", roles: ["student", "teacher", "admin"] },
];

async function renderLayout(activeKey) {
  const session = await window.Auth.requireSession();
  if (!session) return;

  let profile = JSON.parse(localStorage.getItem("profile") || "null");
  if (!profile) {
    profile = await window.api.get("/auth/me").catch(() => null);
    if (profile) localStorage.setItem("profile", JSON.stringify(profile));
  }
  const role = profile?.role || "student";

  const items = NAV_ITEMS.filter((i) => i.roles.includes(role));
  const sidebarHtml = `
    <aside class="hidden lg:flex flex-col w-64 shrink-0 h-screen sticky top-0 glass border-r px-4 py-6" style="border-color:var(--border)">
      <a href="dashboard.html" class="flex items-center gap-2 px-2 mb-8">
        <div class="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-600 to-blue-400 flex items-center justify-center text-white font-bold"><svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M16 21v-2a4 4 0 00-4-4H6a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path stroke-linecap="round" stroke-linejoin="round" d="M17 11l2 2 4-4"/></svg></div>
        <span class="font-extrabold text-lg tracking-tight"><span class="gradient-text">Attendify</span></span>
      </a>
      <nav class="flex flex-col gap-1 flex-1">
        ${items
          .map(
            (i) => `
          <a href="${i.href}" class="sidebar-link ${i.key === activeKey ? "active" : ""}">
            <svg class="w-5 h-5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="${i.icon}"/></svg>
            <span class="text-sm">${i.label}</span>
          </a>`
          )
          .join("")}
      </nav>
      <button onclick="window.Auth.signOut()" class="sidebar-link w-full text-left">
        <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"/></svg>
        <span class="text-sm">Sign Out</span>
      </button>
    </aside>`;

  const topbarHtml = `
    <header class="sticky top-0 z-40 glass border-b px-4 sm:px-6 py-3 flex items-center justify-between" style="border-color:var(--border)">
      <div class="flex items-center gap-3">
        <button onclick="document.getElementById('mobile-sidebar').classList.remove('hidden')" class="lg:hidden btn btn-secondary !p-2">
          <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 6h16M4 12h16M4 18h16"/></svg>
        </button>
        <h1 class="text-lg font-bold capitalize">${activeKey.replace("-", " ")}</h1>
      </div>
      <div class="flex items-center gap-3">
        <button onclick="toggleTheme()" class="btn btn-secondary !p-2" title="Toggle theme"><span data-theme-icon class="inline-flex"></span></button>
        <a href="notifications.html" class="btn btn-secondary !p-2" title="Notifications">
          <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="M15 17h5l-1.4-1.4A2 2 0 0118 14.2V11a6 6 0 10-12 0v3.2c0 .53-.21 1.04-.6 1.4L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"/></svg>
        </a>
        <a href="profile.html" class="flex items-center gap-2 pl-2">
          <div class="w-9 h-9 rounded-full bg-gradient-to-br from-blue-500 to-blue-300 flex items-center justify-center text-white font-bold text-sm">
            ${(profile?.full_name || "U")[0].toUpperCase()}
          </div>
          <span class="hidden sm:block text-sm font-semibold">${profile?.full_name || "User"}</span>
        </a>
      </div>
    </header>`;

  const mobileSidebar = `
    <div id="mobile-sidebar" class="hidden fixed inset-0 z-50 lg:hidden">
      <div class="modal-backdrop absolute inset-0" onclick="document.getElementById('mobile-sidebar').classList.add('hidden')"></div>
      <div class="absolute left-0 top-0 h-full w-72 glass p-4">${sidebarHtml.replace('class="hidden lg:flex', 'class="flex')}</div>
    </div>`;

  document.getElementById("app-sidebar").outerHTML = sidebarHtml;
  document.getElementById("app-topbar").outerHTML = topbarHtml;
  document.body.insertAdjacentHTML("beforeend", mobileSidebar);

  window.syncThemeIcons?.();

  window.SessionAlerts?.init(profile);

  return { profile, role };
}
