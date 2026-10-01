/**
 * TimaLove — intention vocale 15 s (texte de secours) + modal destinataire.
 */
(function () {
  const recRoot = document.querySelector("[data-guided-rec]");
  const review = document.getElementById("guided-review-modal");

  function csrf() {
    const m = document.cookie.match(/(?:^|; )csrftoken=([^;]*)/);
    return m ? decodeURIComponent(m[1]) : "";
  }

  function fmt(ms) {
    const n = Math.max(0, Math.round((Number(ms) || 0) / 1000));
    return Math.floor(n / 60) + ":" + String(n % 60).padStart(2, "0");
  }

  if (recRoot) {
    const url = recRoot.getAttribute("data-upload-url") || "";
    const maxSeconds = Number(recRoot.getAttribute("data-max-seconds") || 15);
    const textMax = Number(recRoot.getAttribute("data-text-max") || 400);
    const micBtn = recRoot.querySelector("[data-guided-mic]");
    const micLabel = recRoot.querySelector("[data-guided-mic-label]");
    const timeEl = recRoot.querySelector("[data-guided-time]");
    const statusEl = recRoot.querySelector("[data-guided-status]");
    const actions = recRoot.querySelector("[data-guided-actions]");
    const sendBtn = recRoot.querySelector("[data-guided-send]");
    const redoBtn = recRoot.querySelector("[data-guided-redo]");
    const textToggle = recRoot.querySelector("[data-guided-text-toggle]");
    const textPanel = recRoot.querySelector("[data-guided-text]");
    const textInput = recRoot.querySelector("[data-guided-text-input]");
    const textCount = recRoot.querySelector("[data-guided-text-count]");
    const textSend = recRoot.querySelector("[data-guided-text-send]");
    let recorder = null;
    let recStream = null;
    let chunks = [];
    let recTimer = null;
    let recStarted = 0;
    let blob = null;
    let elapsed = 1;

    function setStatus(text, isError) {
      if (!statusEl) return;
      statusEl.textContent = text || "";
      statusEl.classList.toggle("is-error", !!isError);
      statusEl.hidden = !text;
    }

    function setMicLabel(text) {
      if (micLabel) micLabel.textContent = text;
      else if (micBtn) micBtn.textContent = text;
    }

    function idleMicLabel() {
      return (micBtn && micBtn.getAttribute("data-label-idle")) || "Enregistrer (15 s max)";
    }

    function stopTracks() {
      if (recStream) {
        recStream.getTracks().forEach(function (track) {
          track.stop();
        });
        recStream = null;
      }
    }

    function showTextPanel(open) {
      if (textPanel) textPanel.hidden = !open;
      if (textToggle) textToggle.hidden = !!open;
    }

    function resetPreview() {
      blob = null;
      if (actions) actions.hidden = true;
      if (micBtn) {
        micBtn.hidden = false;
        micBtn.disabled = false;
        micBtn.classList.remove("is-rec");
        setMicLabel(idleMicLabel());
      }
      if (timeEl) timeEl.textContent = "0:00 / 0:" + String(maxSeconds).padStart(2, "0");
    }

    function finishRecord() {
      if (!recorder) return;
      elapsed = Math.max(1, Math.round((Date.now() - recStarted) / 1000));
      const rec = recorder;
      rec.addEventListener("stop", function () {
        stopTracks();
        window.clearInterval(recTimer);
        recTimer = null;
        blob = new Blob(chunks, { type: rec.mimeType || "audio/webm" });
        chunks = [];
        recorder = null;
        if (micBtn) {
          micBtn.classList.remove("is-rec");
          micBtn.hidden = true;
        }
        if (blob.size < 800) {
          setStatus("Enregistrement trop court. Réessayez ou écrivez un message.", true);
          resetPreview();
          showTextPanel(true);
          return;
        }
        setStatus("Écoutez-vous, puis envoyez ou recommencez.", false);
        if (actions) actions.hidden = false;
      });
      if (rec.state !== "inactive") rec.stop();
    }

    function startRecord() {
      if (!navigator.mediaDevices || !window.MediaRecorder) {
        setStatus("Le micro n’est pas disponible. Écrivez votre intention.", true);
        showTextPanel(true);
        return;
      }
      setStatus("", false);
      showTextPanel(false);
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
          recorder.start();
          if (micBtn) {
            micBtn.classList.add("is-rec");
            setMicLabel((micBtn.getAttribute("data-label-stop") || "Arrêter"));
          }
          recTimer = window.setInterval(function () {
            const spent = Date.now() - recStarted;
            if (timeEl) timeEl.textContent = fmt(spent) + " / 0:" + String(maxSeconds).padStart(2, "0");
            if (spent >= maxSeconds * 1000) finishRecord();
          }, 200);
        })
        .catch(function () {
          setStatus("Autorisez le micro, ou écrivez votre intention.", true);
          showTextPanel(true);
        });
    }

    function updateTextCount() {
      if (!textCount || !textInput) return;
      textCount.textContent = String((textInput.value || "").trim().length) + " / " + String(textMax);
    }

    micBtn?.addEventListener("click", function () {
      if (recorder && recorder.state === "recording") {
        finishRecord();
        return;
      }
      startRecord();
    });
    redoBtn?.addEventListener("click", function () {
      resetPreview();
      setStatus("", false);
    });
    textToggle?.addEventListener("click", function () {
      showTextPanel(true);
      textInput?.focus();
    });
    textInput?.addEventListener("input", updateTextCount);
    sendBtn?.addEventListener("click", function () {
      if (!blob || !url) return;
      sendBtn.disabled = true;
      setStatus("Envoi…", false);
      const fd = new FormData();
      fd.append("file", blob, "guided.webm");
      fd.append("duration", String(Math.min(maxSeconds, elapsed)));
      fetch(url, {
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
            sendBtn.disabled = false;
            setStatus(result.data.message || "Envoi impossible.", true);
            return;
          }
          window.location.reload();
        })
        .catch(function () {
          sendBtn.disabled = false;
          setStatus("Envoi impossible.", true);
        });
    });
    textSend?.addEventListener("click", function () {
      if (!url || !textInput) return;
      const content = (textInput.value || "").trim();
      textSend.disabled = true;
      setStatus("Envoi…", false);
      const fd = new FormData();
      fd.append("content", content);
      fetch(url, {
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
            textSend.disabled = false;
            setStatus(result.data.message || "Envoi impossible.", true);
            return;
          }
          window.location.reload();
        })
        .catch(function () {
          textSend.disabled = false;
          setStatus("Envoi impossible.", true);
        });
    });
    updateTextCount();
  }

  if (!review) return;

  const reopen = document.querySelector("[data-guided-reopen]");
  const form = review.querySelector("[data-guided-review-form]");
  const errorEl = review.querySelector("[data-guided-review-error]");

  function openReview() {
    review.hidden = false;
    document.body.style.overflow = "hidden";
    review.querySelector(".guided-review__title")?.focus();
  }

  function closeReview() {
    review.hidden = true;
    document.body.style.overflow = "";
  }

  if (!review.hasAttribute("hidden")) openReview();
  else if (review.getAttribute("data-auto-open") === "1") openReview();

  review.querySelector("[data-guided-close]")?.addEventListener("click", function () {
    closeReview();
  });
  reopen?.addEventListener("click", function () {
    openReview();
  });

  function postIntent(intent, btn) {
    if (!form) return;
    if (btn) btn.disabled = true;
    if (errorEl) {
      errorEl.hidden = true;
      errorEl.textContent = "";
    }
    const fd = new FormData(form);
    fd.set("intent", intent);
    fetch(form.getAttribute("action"), {
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
          if (btn) btn.disabled = false;
          if (errorEl) {
            errorEl.hidden = false;
            errorEl.textContent = result.data.message || "Action impossible.";
          }
          return;
        }
        window.location.href = result.data.redirect || "/messages/";
      })
      .catch(function () {
        if (btn) btn.disabled = false;
        if (errorEl) {
          errorEl.hidden = false;
          errorEl.textContent = "Action impossible.";
        }
      });
  }

  review.querySelector("[data-guided-accept]")?.addEventListener("click", function (event) {
    event.preventDefault();
    postIntent("accept", event.currentTarget);
  });
  review.querySelector("[data-guided-reject]")?.addEventListener("click", function (event) {
    event.preventDefault();
    postIntent("reject", event.currentTarget);
  });
  review.querySelector("[data-guided-block]")?.addEventListener("click", function (event) {
    event.preventDefault();
    postIntent("block", event.currentTarget);
  });
})();
