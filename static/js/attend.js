(function () {
  const sessionId = Number(document.getElementById("live-config").dataset.session);
  const video = document.getElementById("video"), overlay = document.getElementById("overlay");
  const ctx = overlay.getContext("2d");
  const statusEl = document.getElementById("status");
  const logEl = document.getElementById("log"), countEl = document.getElementById("presentCount");
  const startBtn = document.getElementById("startBtn"), stopBtn = document.getElementById("stopBtn");
  const INTERVAL_MS = 700;
  let running = false, busy = false, timer = null;
  const logged = new Set([...logEl.querySelectorAll("li")].map(li => li.dataset.id));

  const COLORS = { marked: "#22c55e", already: "#22c55e", confirming: "#f59e0b", not_enrolled: "#f59e0b",
                   rejected: "#ef4444", unknown: "#ef4444" };

  function setStatus(text, bad) { statusEl.textContent = text; statusEl.className = "live-status" + (bad ? " bad" : ""); }

  function draw(faces, frame) {
    overlay.width = video.clientWidth; overlay.height = video.clientHeight;
    ctx.clearRect(0, 0, overlay.width, overlay.height);
    // video uses object-fit: cover, so map frame coordinates the same way
    const s = Math.max(overlay.width / frame.width, overlay.height / frame.height);
    const ox = (overlay.width - frame.width * s) / 2, oy = (overlay.height - frame.height * s) / 2;
    ctx.lineWidth = 3; ctx.font = "600 15px system-ui, sans-serif";
    faces.forEach(f => {
      const [x, y, w, h] = f.box, X = x * s + ox, Y = y * s + oy, W = w * s, H = h * s;
      const color = COLORS[f.status] || COLORS.unknown;
      let label = f.name;
      if (f.status === "marked") label += " ✓ marked";
      else if (f.status === "already") label += " (already marked)";
      else if (f.status === "confirming") label += " …";
      if (f.note) label += " · " + f.note;
      ctx.strokeStyle = color; ctx.strokeRect(X, Y, W, H);
      const tw = ctx.measureText(label).width + 14, ty = Y > 28 ? Y - 26 : Y + H + 2;
      ctx.fillStyle = color; ctx.fillRect(X, ty, tw, 24);
      ctx.fillStyle = "#06120a"; ctx.fillText(label, X + 7, ty + 17);
    });
  }

  function addLog(f) {
    if (logged.has(String(f.student_id))) return;
    logged.add(String(f.student_id));
    const empty = document.getElementById("logEmpty"); if (empty) empty.remove();
    const li = document.createElement("li"); li.dataset.id = f.student_id;
    const a = document.createElement("span"), b = document.createElement("span");
    const strong = document.createElement("strong"); strong.textContent = f.name;
    const roll = document.createElement("span"); roll.className = "muted"; roll.textContent = " " + (f.roll_no || "");
    a.append(strong, roll); b.className = "muted"; b.textContent = new Date().toLocaleTimeString([], { hour12: false });
    li.append(a, b); logEl.prepend(li);
  }

  async function tick() {
    if (!running || busy) return;
    const frame = Cam.grab(video, 640, 0.8);
    if (!frame) { schedule(); return; }
    busy = true;
    try {
      const { ok, status, data } = await postJSON("/api/recognize", { session_id: sessionId, image: frame.dataUrl });
      if (!ok) {
        setStatus(data.error || ("Server error " + status), true);
        if ([401, 409, 503].includes(status)) { stop(); return; }
      } else {
        draw(data.faces, frame);
        countEl.textContent = data.present;
        data.faces.forEach(f => { if (f.status === "marked" || f.status === "already") addLog(f); });
        const marked = data.faces.filter(f => f.status === "marked");
        const unknown = data.faces.filter(f => f.status === "unknown").length;
        if (marked.length) setStatus("Marked present: " + marked.map(f => f.name).join(", "));
        else if (unknown) setStatus("Unknown User detected — not marked.");
        else if (!data.faces.length) setStatus("Looking for faces…");
      }
    } catch (e) { setStatus("Cannot reach the server. Is the app still running?", true); }
    finally { busy = false; schedule(); }
  }
  function schedule() { if (running) timer = setTimeout(tick, INTERVAL_MS); }

  async function start() {
    try { await Cam.start(video); } catch (e) { setStatus(e.message, true); return; }
    document.getElementById("hint").hidden = true;
    running = true; startBtn.disabled = true; stopBtn.disabled = false;
    setStatus("Looking for faces…"); tick();
  }
  function stop() {
    running = false; clearTimeout(timer); Cam.stop(video);
    ctx.clearRect(0, 0, overlay.width, overlay.height);
    startBtn.disabled = false; stopBtn.disabled = true;
    document.getElementById("hint").hidden = false;
  }
  startBtn.onclick = start; stopBtn.onclick = stop;
  window.addEventListener("beforeunload", () => Cam.stop(video));
})();
