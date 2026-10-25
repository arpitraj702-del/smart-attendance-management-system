/* Shared helpers: CSRF-aware JSON posts, camera access, mobile nav. */
function csrfToken() { return document.querySelector('meta[name="csrf-token"]').content; }

async function postJSON(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken() },
    body: JSON.stringify(body),
  });
  let data = {};
  try { data = await res.json(); } catch (e) { /* non-JSON error page */ }
  return { ok: res.ok, status: res.status, data };
}

const Cam = {
  stream: null,
  async start(video) {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      throw new Error("Camera is unavailable. Open the app at http://localhost:5000 (not a network IP address).");
    }
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 960 }, height: { ideal: 720 }, facingMode: "user" }, audio: false,
      });
    } catch (e) {
      throw new Error("Camera blocked or not found. Allow camera access in the browser address bar and close other apps using it.");
    }
    video.srcObject = this.stream;
    await video.play();
  },
  stop(video) {
    if (this.stream) this.stream.getTracks().forEach(t => t.stop());
    this.stream = null;
    video.srcObject = null;
  },
  grab(video, maxWidth = 640, quality = 0.85) {
    const w = video.videoWidth, h = video.videoHeight;
    if (!w || !h) return null;
    const scale = Math.min(1, maxWidth / w);
    const c = document.createElement("canvas");
    c.width = Math.round(w * scale); c.height = Math.round(h * scale);
    c.getContext("2d").drawImage(video, 0, 0, c.width, c.height);
    return { dataUrl: c.toDataURL("image/jpeg", quality), width: c.width, height: c.height };
  },
};

document.addEventListener("DOMContentLoaded", () => {
  const t = document.getElementById("navToggle"), s = document.getElementById("sidebar");
  if (t && s) t.addEventListener("click", () => s.classList.toggle("open"));
});
