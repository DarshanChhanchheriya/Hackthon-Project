// Thin fetch wrapper around the FastAPI backend, auto-attaches the
// Supabase access token and surfaces errors as toasts.
window.api = {
  async _headers(hasBody) {
    const session = await window.sb.auth.getSession();
    const token = session.data.session?.access_token;
    const headers = {};
    if (hasBody) headers["Content-Type"] = "application/json";
    if (token) headers["Authorization"] = `Bearer ${token}`;
    return headers;
  },

  async request(method, path, body) {
    const headers = await this._headers(!!body);
    const res = await fetch(`${window.APP_CONFIG.API_BASE_URL}${path}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });

    if (res.status === 401) {
      window.Auth.signOut();
      throw new Error("Session expired. Please log in again.");
    }

    const contentType = res.headers.get("content-type") || "";
    if (!res.ok) {
      let detail = `Request failed (${res.status})`;
      if (contentType.includes("application/json")) {
        const errBody = await res.json().catch(() => null);
        detail = errBody?.detail || detail;
      }
      window.UI?.toast(detail, "error");
      throw new Error(detail);
    }

    if (contentType.includes("application/json")) return res.json();
    return res.blob();
  },

  get(path) { return this.request("GET", path); },
  post(path, body) { return this.request("POST", path, body); },
  put(path, body) { return this.request("PUT", path, body); },
  del(path) { return this.request("DELETE", path); },

  async downloadFile(path, body, filename) {
    const blob = await this.request("POST", path, body);
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  },
};
