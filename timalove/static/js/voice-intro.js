/**
 * TimaLove — Présentation vocale : lecture, enregistrement, signalement.
 */
(function () {
  const MAX_MS = 30000;
  let sharedAudio = null;
  let activePlay = null;
  let recorder = null;
  let recStream = null;
  let chunks = [];
  let recTimer = null;
  let recStarted = 0;

  function csrf() {
    const m = document.cookie.match(/(?:^|; )csrftoken=([^;]*)/);
    return m ? decodeURIComponent(m[1]) : "";
  }

  function fmt(seconds) {
    const n = Math.max(0, Math.round(Number(seconds) || 0));
    return Math.floor(n / 60) + ":" + String(n % 60).padStart(2, "0");
  }

  function stopShared() {
    if (sharedAudio) {
      sharedAudio.pause();
      sharedAudio.removeAttribute("src");
      sharedAudio.load();
    }
    if (activePlay) {
      setPlaying(activePlay, false);
      const time = activePlay.querySelector("[data-voice-intro-time]");
      if (time) time.textContent = fmt(activePlay.getAttribute("data-duration") || 0);
      activePlay = null;
    }
  }

  function setPlaying(root, on) {
    const btn = root.querySelector("[data-voice-intro-play]");
    const playIco = root.querySelector(".voice-intro__ico--play");
    const pauseIco = root.querySelector(".voice-intro__ico--pause");
    if (btn) btn.setAttribute("aria-pressed", on ? "true" : "false");
    if (playIco) playIco.hidden = !!on;
    if (pauseIco) pauseIco.hidden = !on;
  }

  function playRoot(root) {
    const src = root.getAttribute("data-src") || "";
    if (!src) return;
    if (activePlay === root && sharedAudio && !sharedAudio.paused) {
      stopShared();
      return;
    }
    stopShared();
    if (!sharedAudio) sharedAudio = new Audio();
    sharedAudio.src = src;
    const time = root.querySelector("[data-voice-intro-time]");
    const duration = Number(root.getAttribute("data-duration") || 0);
    sharedAudio.ontimeupdate = function () {
      if (time) time.textContent = fmt(sharedAudio.currentTime);
    };
    sharedAudio.onended = function () {
      setPlaying(root, false);
      if (time) time.textContent = fmt(duration);
      if (activePlay === root) activePlay = null;
    };
    sharedAudio.play().then(function () {
      activePlay = root;
      setPlaying(root, true);
    }).catch(function () {
      stopShared();
    });
  }

  function bindPlayer(root) {
    if (!root || root.dataset.voiceBound === "1") return;
    root.dataset.voiceBound = "1";
    root.querySelector("[data-voice-intro-play]")?.addEventListener("click", function (event) {
      event.preventDefault();
      event.stopPropagation();
      playRoot(root);
    });
    const form = root.querySelector("[data-voice-intro-report-form]");
    if (form) {
      form.addEventListener("submit", function (event) {
        event.preventDefault();
        const status = root.querySelector("[data-voice-intro-report-status]");
        const message = (form.querySelector("textarea")?.value || "").trim();
        const profileId = root.getAttribute("data-profile-id") || "";
        if (message.length < 10) {
          if (status) {
            status.hidden = false;
            status.textContent = "Décrivez le motif en quelques mots.";
          }
          return;
        }
        fetch("/api/reports/", {
          method: "POST",
          credentials: "same-origin",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrf(),
            "X-Requested-With": "XMLHttpRequest",
          },
          body: JSON.stringify({
            reported_profile_id: profileId,
            reason: "inappropriate_voice",
            report_kind: "voice",
            message: message,
          }),
        })
          .then(function (res) {
            return res.json().then(function (data) {
              return { ok: res.ok, data: data };
            });
          })
          .then(function (result) {
            if (status) {
              status.hidden = false;
              status.textContent = result.data.message || (result.ok ? "Signalement envoyé." : "Impossible d’envoyer.");
            }
            if (result.ok) form.reset();
          })
          .catch(function () {
            if (status) {
              status.hidden = false;
              status.textContent = "Impossible d’envoyer le signalement.";
            }
          });
      });
    }
  }

  function playerMarkup(url, duration, name) {
    const label = fmt(duration);
    const safeName = name || "";
    return (
      '<div class="voice-intro" data-voice-intro data-src="' +
      url +
      '" data-duration="' +
      duration +
      '"><button type="button" class="voice-intro__play" data-voice-intro-play aria-label="Écouter ' +
      safeName +
      '"><svg class="voice-intro__ico voice-intro__ico--play" viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><path fill="currentColor" d="M8 5.5v13l11-6.5L8 5.5z"/></svg><svg class="voice-intro__ico voice-intro__ico--pause" viewBox="0 0 24 24" width="16" height="16" hidden aria-hidden="true"><path fill="currentColor" d="M7 5h4v14H7V5zm6 0h4v14h-4V5z"/></svg><span>Écouter</span></button><span class="voice-intro__time" data-voice-intro-time>' +
      label +
      "</span></div>"
    );
  }

  function setStatus(root, text, isError) {
    const el = root.querySelector("[data-voice-intro-status]");
    if (!el) return;
    el.hidden = !text;
    el.textContent = text || "";
    el.classList.toggle("is-error", !!isError);
  }

  function stopTracks() {
    if (recStream) {
      recStream.getTracks().forEach(function (t) {
        t.stop();
      });
      recStream = null;
    }
  }

  function setRecordingUi(root, on) {
    const recBtn = root.querySelector("[data-voice-intro-record]");
    const stopBtn = root.querySelector("[data-voice-intro-stop]");
    const timer = root.querySelector("[data-voice-intro-timer]");
    if (recBtn) recBtn.hidden = !!on;
    if (stopBtn) stopBtn.hidden = !on;
    if (timer) timer.hidden = !on;
  }

  function applySaved(root, data) {
    const slot = root.querySelector("[data-voice-intro-slot]");
    const empty = root.querySelector("[data-voice-intro-empty]");
    const delBtn = root.querySelector("[data-voice-intro-delete]");
    const url = data.voice_intro_url || "";
    const duration = data.voice_intro_duration || 0;
    root.setAttribute("data-src", url);
    root.setAttribute("data-duration", String(duration));
    if (slot) {
      slot.hidden = !url;
      slot.innerHTML = url ? playerMarkup(url, duration, "") : "";
      const player = slot.querySelector("[data-voice-intro]");
      if (player) bindPlayer(player);
    }
    if (empty) empty.hidden = !!url;
    if (delBtn) delBtn.hidden = !url;
  }

  function finishRecord(root) {
    if (!recorder) return;
    const elapsed = Math.max(1, Math.round((Date.now() - recStarted) / 1000));
    const rec = recorder;
    rec.addEventListener("stop", function () {
      stopTracks();
      window.clearInterval(recTimer);
      recTimer = null;
      setRecordingUi(root, false);
      const blob = new Blob(chunks, { type: rec.mimeType || "audio/webm" });
      chunks = [];
      recorder = null;
      if (blob.size < 800) {
        setStatus(root, "Enregistrement trop court.", true);
        return;
      }
      const fd = new FormData();
      fd.append("file", blob, "intro.webm");
      fd.append("duration", String(Math.min(30, elapsed)));
      setStatus(root, "Envoi…", false);
      fetch("/api/profile/voice/", {
        method: "POST",
        credentials: "same-origin",
        headers: { "X-CSRFToken": csrf(), "X-Requested-With": "XMLHttpRequest" },
        body: fd,
      })
        .then(function (res) {
          return res.json().then(function (data) {
            return { ok: res.ok, data: data };
          });
        })
        .then(function (result) {
          if (!result.ok) {
            setStatus(root, result.data.message || "Enregistrement impossible.", true);
            return;
          }
          applySaved(root, result.data);
          setStatus(root, "Présentation vocale enregistrée.", false);
        })
        .catch(function () {
          setStatus(root, "Enregistrement impossible.", true);
        });
    });
    if (rec.state !== "inactive") rec.stop();
  }

  function startRecord(root) {
    if (!navigator.mediaDevices || !window.MediaRecorder) {
      setStatus(root, "Le micro n’est pas disponible sur cet appareil.", true);
      return;
    }
    navigator.mediaDevices
      .getUserMedia({ audio: true })
      .then(function (stream) {
        recStream = stream;
        chunks = [];
        const mime = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
          ? "audio/webm;codecs=opus"
          : MediaRecorder.isTypeSupported("audio/webm")
            ? "audio/webm"
            : "";
        recorder = mime
          ? new MediaRecorder(stream, { mimeType: mime, audioBitsPerSecond: 24000 })
          : new MediaRecorder(stream, { audioBitsPerSecond: 24000 });
        recorder.addEventListener("dataavailable", function (event) {
          if (event.data && event.data.size) chunks.push(event.data);
        });
        recStarted = Date.now();
        const timer = root.querySelector("[data-voice-intro-timer]");
        recTimer = window.setInterval(function () {
          const elapsed = Date.now() - recStarted;
          if (timer) timer.textContent = fmt(elapsed / 1000) + " / 0:30";
          if (elapsed >= MAX_MS) finishRecord(root);
        }, 200);
        recorder.start();
        setRecordingUi(root, true);
        if (timer) timer.textContent = "0:00 / 0:30";
        setStatus(root, "", false);
      })
      .catch(function () {
        setStatus(root, "Autorisez le micro pour enregistrer votre voix.", true);
      });
  }

  function bindRecorder(root) {
    if (!root || root.dataset.voiceRecBound === "1") return;
    root.dataset.voiceRecBound = "1";
    root.querySelector("[data-voice-intro-record]")?.addEventListener("click", function (event) {
      event.preventDefault();
      startRecord(root);
    });
    root.querySelector("[data-voice-intro-stop]")?.addEventListener("click", function (event) {
      event.preventDefault();
      finishRecord(root);
    });
    root.querySelector("[data-voice-intro-delete]")?.addEventListener("click", function (event) {
      event.preventDefault();
      if (!window.confirm("Supprimer votre présentation vocale ?")) return;
      fetch("/api/profile/voice/delete/", {
        method: "POST",
        credentials: "same-origin",
        headers: { "X-CSRFToken": csrf(), "X-Requested-With": "XMLHttpRequest" },
      })
        .then(function (res) {
          return res.json().then(function (data) {
            return { ok: res.ok, data: data };
          });
        })
        .then(function (result) {
          if (!result.ok) {
            setStatus(root, result.data.message || "Suppression impossible.", true);
            return;
          }
          stopShared();
          applySaved(root, result.data);
          setStatus(root, "Présentation vocale supprimée.", false);
        })
        .catch(function () {
          setStatus(root, "Suppression impossible.", true);
        });
    });
  }

  function scan() {
    document.querySelectorAll("[data-voice-intro]").forEach(bindPlayer);
    document.querySelectorAll("[data-voice-intro-recorder]").forEach(bindRecorder);
  }

  document.addEventListener("click", function (event) {
    const btn = event.target.closest("[data-voice-intro-play]");
    if (!btn) return;
    const root = btn.closest("[data-voice-intro]");
    if (!root || root.dataset.voiceBound === "1") return;
    bindPlayer(root);
    playRoot(root);
  });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", scan);
  } else {
    scan();
  }
  document.addEventListener("htmx:afterSwap", scan);
})();
