// Requires the Supabase JS CDN script to be loaded before this file:
// <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2/dist/umd/supabase.min.js"></script>
const { createClient } = supabase;

window.sb = createClient(window.APP_CONFIG.SUPABASE_URL, window.APP_CONFIG.SUPABASE_ANON_KEY, {
  auth: { persistSession: true, autoRefreshToken: true },
});

window.Auth = {
  async getSession() {
    const { data } = await window.sb.auth.getSession();
    return data.session;
  },
  async requireSession(allowedRoles = []) {
    const session = await this.getSession();
    if (!session) {
      window.location.href = "login.html";
      return null;
    }
    const profile = JSON.parse(localStorage.getItem("profile") || "null");
    if (allowedRoles.length && profile && !allowedRoles.includes(profile.role)) {
      window.location.href = "dashboard.html";
      return null;
    }
    return session;
  },
  async signOut() {
    await window.sb.auth.signOut();
    localStorage.removeItem("profile");
    window.location.href = "login.html";
  },
};
