(function () {
  const $ = id => document.getElementById(id);
  const video = $("video"), photos = [];
  const MAX = 10;

  function msg(text, kind) {
    const m = $("msg"); m.hidden = !text; m.textContent = text || ""; m.className = "flash " + (kind || "error");
  }
  function refresh() {
    $("count").textContent = "(" + photos.length + ")";
    $("submitBtn").disabled = photos.length === 0;
    const t = $("thumbs"); t.innerHTML = "";
    photos.forEach((src, i) => {
      const d = document.createElement("div"), img = document.createElement("img"), b = document.createElement("button");
      img.src = src; img.alt = "Captured photo " + (i + 1);
      b.type = "button"; b.textContent = "×"; b.setAttribute("aria-label", "Remove photo " + (i + 1));
      b.onclick = () => { photos.splice(i, 1); refresh(); };
      d.append(img, b); t.append(d);
    });
  }
  function add(src) { if (photos.length >= MAX) { msg("Maximum " + MAX + " photos."); return false; } photos.push(src); refresh(); return true; }
  const sleep = ms => new Promise(r => setTimeout(r, ms));

  $("startBtn").onclick = async () => {
    try {
      await Cam.start(video);
      $("hint").hidden = true; $("captureBtn").disabled = false; $("burstBtn").disabled = false; msg("");
    } catch (e) { msg(e.message); }
  };
  $("captureBtn").onclick = () => { const f = Cam.grab(video, 800, 0.9); if (f) add(f.dataUrl); };
  $("burstBtn").onclick = async () => {
    $("burstBtn").disabled = true;
    for (let i = 1; i <= 5; i++) {
      msg("Capturing " + i + " of 5 — look at the camera and turn your head slightly.", "ok");
      await sleep(900);
      const f = Cam.grab(video, 800, 0.9); if (f && !add(f.dataUrl)) break;
    }
    msg(""); $("burstBtn").disabled = false;
  };
  $("file").onchange = e => {
    [...e.target.files].forEach(file => {
      const r = new FileReader(); r.onload = () => add(r.result); r.readAsDataURL(file);
    });
    e.target.value = "";
  };

  $("regForm").onsubmit = async e => {
    e.preventDefault();
    const btn = $("submitBtn"); btn.disabled = true; btn.textContent = "Checking faces…"; msg("");
    const { ok, data } = await postJSON("/api/students/register", {
      name: $("name").value, roll_no: $("roll_no").value, email: $("email").value,
      department_id: $("department_id").value, semester: $("semester").value,
      auto_enroll: $("auto_enroll").checked, images: photos,
    });
    if (ok) { Cam.stop(video); window.location = data.redirect; return; }
    msg(data.error || "Registration failed.");
    btn.textContent = "Save student"; btn.disabled = photos.length === 0;
  };
  refresh();
})();
