// Real-time "attendance session started" alerts for students, with a
// one-tap face self-check-in modal. Subscribes to Supabase Realtime on the
// notifications table (no polling) and only initializes for student role.
// If the student never enrolled a face, the same modal seamlessly switches
// into a 5-photo registration flow, then retries check-in automatically.
window.SessionAlerts = (() => {
  let stream, mode, captures, mySessionId;

  function ensureModal() {
    if (document.getElementById("checkin-modal")) return;
    const el = document.createElement("div");
    el.id = "checkin-modal";
    el.className = "hidden fixed inset-0 z-[200] flex items-center justify-center px-4";
    el.innerHTML = `
      <div class="modal-backdrop absolute inset-0" onclick="SessionAlerts.closeModal()"></div>
      <div class="card glass relative z-10 w-full max-w-md p-6 text-center">
        <h3 id="checkin-title" class="font-bold text-lg mb-1">Face Check-in</h3>
        <p id="checkin-subtitle" class="text-sm mb-4" style="color:var(--text-muted)">Look at the camera to mark yourself present.</p>
        <div class="relative rounded-2xl overflow-hidden bg-black aspect-square">
          <video id="checkin-video" autoplay playsinline class="w-full h-full object-cover"></video>
          <div class="face-reticle">
            <span class="corner tl"></span><span class="corner tr"></span><span class="corner bl"></span><span class="corner br"></span>
            <div class="scan-line"></div>
          </div>
        </div>
        <canvas id="checkin-canvas" class="hidden"></canvas>
        <div id="checkin-dots" class="hidden flex justify-center gap-2 mt-3">
          <div class="w-3 h-3 rounded-full" style="background:var(--border)"></div>
          <div class="w-3 h-3 rounded-full" style="background:var(--border)"></div>
          <div class="w-3 h-3 rounded-full" style="background:var(--border)"></div>
          <div class="w-3 h-3 rounded-full" style="background:var(--border)"></div>
          <div class="w-3 h-3 rounded-full" style="background:var(--border)"></div>
        </div>
        <p id="checkin-result" class="text-sm font-medium mt-4 min-h-[1.5em]"></p>
        <div class="flex gap-3 mt-4">
          <button class="btn btn-secondary flex-1" onclick="SessionAlerts.closeModal()">Cancel</button>
          <button id="checkin-capture-btn" class="btn btn-primary flex-1">Capture &amp; Check In</button>
        </div>
      </div>`;
    document.body.appendChild(el);
    document.getElementById("checkin-capture-btn").addEventListener("click", onCaptureClick);
  }

  function resetToCheckinMode() {
    mode = "checkin";
    captures = [];
    document.getElementById("checkin-title").textContent = "Face Check-in";
    document.getElementById("checkin-subtitle").textContent = "Look at the camera to mark yourself present.";
    document.getElementById("checkin-capture-btn").textContent = "Capture & Check In";
    document.getElementById("checkin-dots").classList.add("hidden");
    document.querySelectorAll("#checkin-dots > div").forEach((d) => (d.style.background = "var(--border)"));
  }

  async function openModal(sessionId) {
    ensureModal();
    mySessionId = sessionId;
    resetToCheckinMode();
    document.getElementById("checkin-result").textContent = "";
    document.getElementById("checkin-modal").classList.remove("hidden");
    try {
      stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "user" } });
      document.getElementById("checkin-video").srcObject = stream;
    } catch (_) {
      UI.toast("Camera access denied", "error");
    }
  }

  function closeModal() {
    stream?.getTracks().forEach((t) => t.stop());
    stream = null;
    document.getElementById("checkin-modal")?.classList.add("hidden");
  }

  function captureFrame() {
    const video = document.getElementById("checkin-video");
    const canvas = document.getElementById("checkin-canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext("2d").drawImage(video, 0, 0);
    return canvas.toDataURL("image/jpeg", 0.85);
  }

  function switchToEnrollMode() {
    mode = "enroll";
    captures = [];
    document.getElementById("checkin-title").textContent = "Register Your Face First";
    document.getElementById("checkin-subtitle").textContent = "No face on file yet — capture 5 photos, then we'll check you in automatically.";
    document.getElementById("checkin-capture-btn").textContent = "Capture (0/5)";
    document.getElementById("checkin-dots").classList.remove("hidden");
    document.getElementById("checkin-result").textContent = "";
  }

  async function onCaptureClick() {
    const resultEl = document.getElementById("checkin-result");
    const profile = JSON.parse(localStorage.getItem("profile") || "null");

    if (mode === "enroll") {
      captures.push(captureFrame());
      const dots = document.querySelectorAll("#checkin-dots > div");
      dots[captures.length - 1].style.background = "var(--accent)";
      document.getElementById("checkin-capture-btn").textContent = `Capture (${captures.length}/5)`;

      if (captures.length >= 5) {
        resultEl.textContent = "Registering your face...";
        document.getElementById("checkin-capture-btn").disabled = true;
        try {
          await api.post("/face/enroll", { owner_id: profile.id, images_base64: captures });
          UI.toast("Face registered! Checking you in...", "success");
          resetToCheckinMode();
          await performCheckin();
        } catch (_) {
          resultEl.textContent = "Registration failed — try capturing again.";
          captures = [];
          dots.forEach((d) => (d.style.background = "var(--border)"));
          document.getElementById("checkin-capture-btn").textContent = "Capture (0/5)";
        } finally {
          document.getElementById("checkin-capture-btn").disabled = false;
        }
      }
      return;
    }

    await performCheckin();
  }

  async function performCheckin() {
    const resultEl = document.getElementById("checkin-result");
    const frame = captureFrame();
    resultEl.textContent = "Verifying...";
    try {
      const res = await api.post("/face/self-checkin", { session_id: mySessionId, image_base64: frame });
      if (res.status === "rejected" && /no face enrolled/i.test(res.message || "")) {
        switchToEnrollMode();
        return;
      }
      resultEl.textContent = res.message;
      if (res.status === "marked") {
        UI.toast("Attendance marked — you're present!", "success");
        setTimeout(closeModal, 1200);
      } else {
        UI.toast(res.message, res.status === "late" ? "warning" : "error");
      }
    } catch (_) {
      resultEl.textContent = "Check-in failed. Try again.";
    }
  }

  function showBanner(sessionSubject) {
    let banner = document.getElementById("session-banner");
    if (banner) banner.remove();
    banner = document.createElement("div");
    banner.id = "session-banner";
    banner.className = "fixed bottom-5 left-1/2 -translate-x-1/2 z-[150] card glass px-5 py-4 flex items-center gap-4 shadow-lg fade-in";
    banner.innerHTML = `
      <span class="pulse-dot"></span>
      <div>
        <p class="font-semibold text-sm">Attendance session started${sessionSubject ? " — " + sessionSubject : ""}</p>
        <p class="text-xs" style="color:var(--text-muted)">Check in now with your face before the window closes.</p>
      </div>
      <button class="btn btn-primary !py-1.5" id="session-banner-checkin">Check In</button>
      <button class="btn btn-secondary !p-2" onclick="document.getElementById('session-banner').remove()">✕</button>`;
    document.body.appendChild(banner);
    document.getElementById("session-banner-checkin").addEventListener("click", async () => {
      const session = await findActiveSessionForMe();
      banner.remove();
      if (session) openModal(session.id);
      else UI.toast("That session isn't active anymore", "warning");
    });
  }

  async function findActiveSessionForMe() {
    const profile = JSON.parse(localStorage.getItem("profile") || "null");
    if (!profile) return null;
    const student = await api.get(`/students/${profile.id}`).catch(() => null);
    const departmentId = student?.department_id;
    const sessions = await api.get(`/sessions/active${departmentId ? `?department_id=${departmentId}` : ""}`).catch(() => []);
    return sessions?.[0] || null;
  }

  function init(profile) {
    if (!profile || profile.role !== "student") return;
    window.sb
      .channel("session-alerts")
      .on(
        "postgres_changes",
        { event: "INSERT", schema: "public", table: "notifications", filter: `user_id=eq.${profile.id}` },
        (payload) => {
          const n = payload.new;
          if (n.title === "Attendance session started") {
            const match = n.message.match(/session (?:for )?(.*?)\./i);
            showBanner(match ? match[1] : "");
          }
        }
      )
      .subscribe();
  }

  return { init, openModal, closeModal, findActiveSessionForMe };
})();
