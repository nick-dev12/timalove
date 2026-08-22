/**
 * TimaLove — fil de discussion : texte, vocal, photos.
 */
(function () {
  const MAX_VOICE_MS = 60000;
  const thread = document.querySelector("[data-msg-thread]");
  const form = document.querySelector(".msg__composer");
  const input = document.querySelector("[data-msg-input]");
  const compose = document.querySelector("[data-msg-compose]");
  const recordBar = document.querySelector("[data-msg-record]");
  const photoInput = document.querySelector("[data-msg-photo-input]");
  const mediaUrl = form && form.getAttribute("data-media-url");

  function csrf() {
    const m = document.cookie.match(/(?:^|; )csrftoken=([^;]*)/);
    if (m) return decodeURIComponent(m[1]);
    const field = document.querySelector("[name=csrfmiddlewaretoken]");
    return field ? field.value : "";
  }

  function fmtTime(seconds) {
    const s = Math.max(0, Math.round(Number(seconds) || 0));
    return Math.floor(s / 60) + ":" + String(s % 60).padStart(2, "0");
  }

  function scrollThread() {
    if (!thread) return;
    const last = thread.querySelector(".msg__row:last-of-type");
    if (last) {
      last.scrollIntoView({ block: "end", inline: "nearest", behavior: "auto" });
      return;
    }
    thread.scrollTop = thread.scrollHeight;
  }

  function pinToLatest() {
    scrollThread();
    requestAnimationFrame(function () {
      scrollThread();
      window.setTimeout(scrollThread, 60);
      window.setTimeout(scrollThread, 220);
    });
    if (!thread) return;
    thread.querySelectorAll("img").forEach(function (img) {
      if (img.complete) return;
      img.addEventListener("load", scrollThread, { once: true });
    });
  }

  function toast(message) {
    let el = document.getElementById("swipe-toast");
    if (!el) {
      el = document.createElement("div");
      el.id = "swipe-toast";
      el.className = "swipe-toast";
      el.setAttribute("role", "status");
      document.body.appendChild(el);
    }
    el.textContent = message;
    el.hidden = false;
    window.clearTimeout(toast._t);
    toast._t = window.setTimeout(function () {
      el.hidden = true;
    }, 3200);
  }

  function fillWave(wave, seed) {
    if (!wave || wave.childElementCount) return;
    let n = Number(seed) || 12;
    for (let i = 0; i < 22; i += 1) {
      const bar = document.createElement("i");
      const h = 28 + ((n * (i + 3) * 13) % 72);
      bar.style.height = h + "%";
      wave.appendChild(bar);
    }
  }

  let currentAudio = null;
  let currentCard = null;

  function stopVoice() {
    if (currentAudio) {
      currentAudio.pause();
      currentAudio.currentTime = 0;
    }
    if (currentCard) {
      currentCard.classList.remove("is-playing");
      const pause = currentCard.querySelector(".msg__voice-ico--pause");
      const play = currentCard.querySelector(".msg__voice-ico--play");
      if (pause) pause.hidden = true;
      if (play) play.hidden = false;
      const time = currentCard.querySelector("[data-voice-time]");
      if (time) time.textContent = fmtTime(currentCard.getAttribute("data-duration"));
      currentCard.style.removeProperty("--voice-progress");
    }
    currentAudio = null;
    currentCard = null;
  }

  function bindVoice(card) {
    const wave = card.querySelector("[data-voice-wave]");
    fillWave(wave, card.getAttribute("data-duration"));
    const btn = card.querySelector("[data-voice-play]");
    if (!btn) return;
    btn.addEventListener("click", function () {
      const src = card.getAttribute("data-src");
      if (!src) return;
      if (currentCard === card && currentAudio) {
        if (currentAudio.paused) currentAudio.play();
        else currentAudio.pause();
        return;
      }
      stopVoice();
      const audio = new Audio(src);
      currentAudio = audio;
      currentCard = card;
      const pauseIco = card.querySelector(".msg__voice-ico--pause");
      const playIco = card.querySelector(".msg__voice-ico--play");
      const time = card.querySelector("[data-voice-time]");
      audio.addEventListener("play", function () {
        card.classList.add("is-playing");
        if (pauseIco) pauseIco.hidden = false;
        if (playIco) playIco.hidden = true;
      });
      audio.addEventListener("pause", function () {
        if (currentCard !== card) return;
        card.classList.remove("is-playing");
        if (pauseIco) pauseIco.hidden = true;
        if (playIco) playIco.hidden = false;
      });
      audio.addEventListener("timeupdate", function () {
        if (!audio.duration) return;
        card.style.setProperty("--voice-progress", String(audio.currentTime / audio.duration));
        if (time) time.textContent = fmtTime(audio.duration - audio.currentTime);
      });
      audio.addEventListener("ended", stopVoice);
      audio.play().catch(function () {
        toast("Impossible de lire ce vocal.");
        stopVoice();
      });
    });
  }

  function bindLightbox() {
    const box = document.getElementById("photo-lightbox");
    if (!box) return;
    const img = box.querySelector(".photo-lightbox__img");
    function close() {
      box.hidden = true;
      if (img) {
        img.removeAttribute("src");
        img.alt = "";
      }
      document.body.classList.remove("is-lightbox");
    }
    function open(src) {
      if (!src || !img) return;
      img.src = src;
      img.alt = "Photo";
      box.hidden = false;
      document.body.classList.add("is-lightbox");
    }
    document.addEventListener("click", function (event) {
      const trigger = event.target.closest("[data-msg-photo]");
      if (trigger) {
        event.preventDefault();
        open(trigger.getAttribute("data-msg-photo"));
        return;
      }
      if (event.target.closest("[data-lightbox-close]") || event.target === box) close();
    });
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && !box.hidden) close();
    });
  }

  function checksHtml(read) {
    const cls = read ? "msg__checks is-read" : "msg__checks";
    const label = read ? "Lu" : "Envoyé";
    return (
      '<span class="' +
      cls +
      '" aria-hidden="true" aria-label="' +
      label +
      '"><svg viewBox="0 0 16 12" width="16" height="12">' +
      '<path class="msg__check msg__check--1" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" d="M1 6.2 4.2 9.5 10.8 2.2"/>' +
      '<path class="msg__check msg__check--2" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" d="M5.2 6.2 8.4 9.5 15 2.2"/>' +
      "</svg></span>"
    );
  }

  function applyReadReceipts(readIds) {
    if (!thread || !readIds || !readIds.length) return;
    const readSet = new Set(readIds);
    thread.querySelectorAll(".msg__row.is-mine[data-msg-id]").forEach(function (row) {
      const id = row.getAttribute("data-msg-id");
      if (!id || !readSet.has(id)) return;
      const checks = row.querySelector(".msg__checks");
      if (!checks || checks.classList.contains("is-read")) return;
      checks.classList.add("is-read");
      checks.setAttribute("aria-label", "Lu");
    });
  }

  function syncReadReceipts(partnerId) {
    if (!partnerId || !thread) return;
    fetch("/api/messages/read-receipts/?partner_id=" + encodeURIComponent(partnerId), {
      credentials: "same-origin",
      headers: { "X-Requested-With": "XMLHttpRequest" },
    })
      .then(function (res) {
        return res.json();
      })
      .then(function (data) {
        applyReadReceipts(data.read_ids || []);
      })
      .catch(function () { });
  }

  let markReadTimer = null;

  function isFromPartner(raw) {
    if (!raw || !meId || !raw.sender_id) return false;
    return String(raw.sender_id) !== String(meId);
  }

  function markPartnerMessagesRead(partnerId) {
    if (!partnerId || !thread) return;
    window.clearTimeout(markReadTimer);
    markReadTimer = window.setTimeout(function () {
      fetch("/api/messages/mark-read/?partner_id=" + encodeURIComponent(partnerId), {
        credentials: "same-origin",
        headers: { "X-Requested-With": "XMLHttpRequest" },
      })
        .then(function () {
          if (typeof window.timaloveRefreshUnreadBadge === "function") {
            window.timaloveRefreshUnreadBadge();
          }
        })
        .catch(function () { });
    }, 80);
  }

  function deleteButtonHtml() {
    return (
      '<button type="button" class="msg__delete" data-msg-delete aria-label="Supprimer le message">' +
      '<svg viewBox="0 0 24 24" width="15" height="15" aria-hidden="true"><path fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" d="M4 7h16M9 7V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2m-1 12H8a2 2 0 0 1-2-2V7h12v10a2 2 0 0 1-2 2h-4z"/></svg></button>'
    );
  }

  function appendBubble(item) {
    if (!thread) return;
    if (item.id && thread.querySelector('.msg__row[data-msg-id="' + item.id + '"]')) return;
    const empty = thread.querySelector(".msg__empty");
    if (empty) empty.remove();
    const mine = item.mine !== false;
    const row = document.createElement("article");
    row.className = "msg__row" + (mine ? " is-mine" : "");
    if (item.id) row.setAttribute("data-msg-id", item.id);
    const mePhoto = thread.getAttribute("data-me-photo") || "";
    const meInitial = thread.getAttribute("data-me-initial") || "M";
    const partnerPhoto = thread.getAttribute("data-partner-photo") || "";
    const partnerInitial = thread.getAttribute("data-partner-initial") || "?";
    const avatarPhoto = mine ? mePhoto : item.photo_url || partnerPhoto;
    const avatarInitial = mine ? meInitial : item.initial || partnerInitial;
    const avatarInner = avatarPhoto
      ? '<img src="' + avatarPhoto + '" alt="">'
      : "<span>" + avatarInitial + "</span>";
    let body = "";
    if (item.is_image && item.image_url) {
      body =
        '<button type="button" class="msg__photo-btn" data-msg-photo="' +
        item.image_url +
        '"><img class="msg__photo" src="' +
        item.image_url +
        '" alt="Photo"></button>';
    } else if (item.is_voice) {
      body =
        '<div class="msg__voice-card" data-voice-player data-src="' +
        (item.voice_url || "") +
        '" data-duration="' +
        (item.voice_duration || 0) +
        '"><button type="button" class="msg__voice-play" data-voice-play aria-label="Lire le vocal"><svg class="msg__voice-ico msg__voice-ico--play" viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><path fill="currentColor" d="M8 5.5v13l11-6.5L8 5.5z"/></svg><svg class="msg__voice-ico msg__voice-ico--pause" viewBox="0 0 24 24" width="16" height="16" hidden aria-hidden="true"><path fill="currentColor" d="M7 5h4v14H7V5zm6 0h4v14h-4V5z"/></svg></button><span class="msg__voice-wave" data-voice-wave aria-hidden="true"></span><span class="msg__voice-time" data-voice-time">' +
        (item.voice_label || fmtTime(item.voice_duration)) +
        "</span></div>";
    } else {
      body = "<p></p>";
    }
    row.innerHTML =
      '<span class="msg__bubble-avatar" aria-hidden="true">' +
      avatarInner +
      '</span><div class="msg__bubble' +
      (item.is_image ? " is-photo" : item.is_voice ? " is-voice" : "") +
      '">' +
      body +
      "<footer><time>" +
      (item.time || "") +
      "</time>" +
      (mine ? checksHtml(Boolean(item.read)) : "") +
      (mine && item.id ? deleteButtonHtml() : "") +
      "</footer></div>";
    if (!item.is_image && !item.is_voice) {
      row.querySelector("p").textContent = item.content || "";
    }
    thread.appendChild(row);
    const voiceCard = row.querySelector("[data-voice-player]");
    if (voiceCard) bindVoice(voiceCard);
    scrollThread();
  }

  function uploadMedia(kind, blob, filename, duration) {
    if (!mediaUrl || !blob) return Promise.reject(new Error("Envoi impossible."));
    const data = new FormData();
    data.append("kind", kind);
    data.append("file", blob, filename);
    if (duration) data.append("duration", String(duration));
    return fetch(mediaUrl, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "X-CSRFToken": csrf(),
        "X-Requested-With": "XMLHttpRequest",
      },
      body: data,
    }).then(function (res) {
      return res.json().then(function (payload) {
        if (!res.ok || !payload.ok) {
          throw failFromPayload(payload, "Envoi impossible.");
        }
        return payload.item;
      });
    });
  }

  function compressImage(file) {
    return new Promise(function (resolve, reject) {
      const img = new Image();
      const url = URL.createObjectURL(file);
      img.onload = function () {
        const max = 1280;
        let w = img.width;
        let h = img.height;
        const scale = Math.min(1, max / Math.max(w, h));
        w = Math.max(1, Math.round(w * scale));
        h = Math.max(1, Math.round(h * scale));
        const canvas = document.createElement("canvas");
        canvas.width = w;
        canvas.height = h;
        canvas.getContext("2d").drawImage(img, 0, 0, w, h);
        URL.revokeObjectURL(url);
        canvas.toBlob(
          function (blob) {
            if (!blob) reject(new Error("Compression impossible."));
            else resolve(blob);
          },
          "image/jpeg",
          0.72
        );
      };
      img.onerror = function () {
        URL.revokeObjectURL(url);
        reject(new Error("Image illisible."));
      };
      img.src = url;
    });
  }

  let recorder = null;
  let chunks = [];
  let recTimer = null;
  let recStarted = 0;
  let recStream = null;

  function setRecording(on) {
    if (recordBar) recordBar.hidden = !on;
    if (compose) compose.hidden = on;
  }

  function stopTracks() {
    if (recStream) {
      recStream.getTracks().forEach(function (t) {
        t.stop();
      });
      recStream = null;
    }
  }

  function cancelRecord() {
    if (recorder && recorder.state !== "inactive") recorder.stop();
    recorder = null;
    chunks = [];
    window.clearInterval(recTimer);
    recTimer = null;
    stopTracks();
    setRecording(false);
  }

  function startRecord() {
    if (!navigator.mediaDevices || !window.MediaRecorder) {
      toast("Le vocal n’est pas disponible sur cet appareil.");
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
        const timeEl = document.querySelector("[data-msg-record-time]");
        recTimer = window.setInterval(function () {
          const elapsed = Date.now() - recStarted;
          if (timeEl) timeEl.textContent = fmtTime(elapsed / 1000);
          if (elapsed >= MAX_VOICE_MS) sendRecord();
        }, 200);
        recorder.start();
        setRecording(true);
        if (timeEl) timeEl.textContent = "0:00";
      })
      .catch(function () {
        toast("Autorisez le micro pour envoyer un vocal.");
      });
  }

  function sendRecord() {
    if (!recorder) return;
    const elapsed = Math.max(1, Math.round((Date.now() - recStarted) / 1000));
    const rec = recorder;
    rec.addEventListener("stop", function () {
      stopTracks();
      window.clearInterval(recTimer);
      setRecording(false);
      const blob = new Blob(chunks, { type: rec.mimeType || "audio/webm" });
      chunks = [];
      recorder = null;
      if (blob.size < 800) {
        toast("Vocal trop court.");
        return;
      }
      uploadMedia("voice", blob, "vocal.webm", elapsed)
        .then(function (item) {
          appendBubble(normalizeChatItem(item));
        })
        .catch(function (err) {
          if (!handleLimitFailure(err)) toast(err.message || "Envoi du vocal impossible.");
        });
    });
    if (rec.state !== "inactive") rec.stop();
  }

  if (thread) {
    thread.querySelectorAll("[data-voice-player]").forEach(bindVoice);
    pinToLatest();
  }

  const msgSection = document.querySelector(".msg[data-partner-id]");
  const partnerId = msgSection && msgSection.getAttribute("data-partner-id");
  const meId = thread && thread.getAttribute("data-me-id");
  let chatWs = null;
  let chatWsConnected = false;
  let chatWsRetryTimer = null;
  let chatWsRetryDelay = 3000;
  let chatWsHideTimer = null;

  function normalizeChatItem(raw) {
    if (!raw) return null;
    const item = Object.assign({}, raw);
    if (meId && raw.sender_id) {
      item.mine = String(raw.sender_id) === String(meId);
    }
    return item;
  }

  function handleChatPayload(data) {
    if (!data || !data.event) return;
    if (data.event === "message" && data.item) {
      const item = normalizeChatItem(data.item);
      appendBubble(item);
      if (isFromPartner(data.item)) {
        markPartnerMessagesRead(partnerId);
      }
      return;
    }
    if (data.event === "error") {
      if (!handleLimitFailure({ code: data.code, message: data.message || "" })) {
        toast(data.message || "Envoi impossible.");
      }
      return;
    }
    if (data.event === "read_receipts") {
      applyReadReceipts(data.read_ids || []);
    }
  }

  function connectChatWebSocket() {
    if (!partnerId || !thread) return;
    if (chatWs && (chatWs.readyState === WebSocket.OPEN || chatWs.readyState === WebSocket.CONNECTING)) {
      return;
    }
    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    const url = proto + "//" + window.location.host + "/ws/chat/" + partnerId + "/";
    console.info("[TimaLove chat WS] connexion", url);
    chatWs = new WebSocket(url);

    chatWs.onopen = function () {
      chatWsConnected = true;
      chatWsRetryDelay = 3000;
      console.log("[TimaLove chat WS] connecté");
      markPartnerMessagesRead(partnerId);
    };

    chatWs.onmessage = function (event) {
      try {
        const data = JSON.parse(event.data);
        console.log("[TimaLove chat WS] event", data.event || data);
        handleChatPayload(data);
      } catch (err) {
        console.warn("[TimaLove chat WS] payload invalide", err);
      }
    };

    chatWs.onclose = function (event) {
      chatWsConnected = false;
      chatWs = null;
      console.log("[TimaLove chat WS] fermé", event.code);
      window.clearTimeout(chatWsRetryTimer);
      if (!document.hidden) {
        const delay = event.code === 1000 ? 1000 : chatWsRetryDelay;
        chatWsRetryTimer = window.setTimeout(connectChatWebSocket, delay);
        if (event.code !== 1000) {
          chatWsRetryDelay = Math.min(chatWsRetryDelay * 2, 30000);
        }
      }
    };

    chatWs.onerror = function () {
      console.error("[TimaLove chat WS] erreur");
    };
  }

  function failFromPayload(payload, fallback) {
    const err = new Error((payload && (payload.message || payload.error)) || fallback);
    if (payload && payload.code) err.code = payload.code;
    if (!err.code && /limite/i.test(err.message || "")) err.code = "message_limit";
    return err;
  }

  function isLimitError(err) {
    if (!err) return false;
    if (err.code === "message_limit") return true;
    return /limite/i.test(err.message || "");
  }

  const limitPopup = document.getElementById("upgrade-limit-popup");
  const plansModal = document.getElementById("upgrade-plans-modal");
  const plansStatus = document.querySelector("[data-upgrade-plans-status]");

  function setQuotaLocked(locked) {
    if (!form) return;
    form.setAttribute("data-quota-locked", locked ? "1" : "0");
  }

  function showLimitPopup() {
    if (!limitPopup) {
      toast("Votre limite a été atteinte. Passez au plan supérieur.");
      return;
    }
    setQuotaLocked(true);
    limitPopup.hidden = false;
    document.body.classList.add("is-upgrade-popup");
    const focusBtn = limitPopup.querySelector("[data-upgrade-open-plans]");
    if (focusBtn) focusBtn.focus();
  }

  function hideLimitPopup() {
    if (!limitPopup) return;
    limitPopup.hidden = true;
    if (!plansModal || plansModal.hidden) {
      document.body.classList.remove("is-upgrade-popup");
    }
  }

  function showPlansModal() {
    if (!plansModal) return;
    hideLimitPopup();
    plansModal.hidden = false;
    document.body.classList.add("is-upgrade-popup");
    const closeBtn = plansModal.querySelector("[data-upgrade-plans-close]");
    if (closeBtn) closeBtn.focus();
  }

  function hidePlansModal() {
    if (!plansModal) return;
    plansModal.hidden = true;
    document.body.classList.remove("is-upgrade-popup");
  }

  function handleLimitFailure(err) {
    if (isLimitError(err)) {
      showLimitPopup();
      return true;
    }
    return false;
  }

  if (limitPopup) {
    limitPopup.querySelectorAll("[data-upgrade-limit-close]").forEach(function (el) {
      el.addEventListener("click", hideLimitPopup);
    });
    const openPlans = limitPopup.querySelector("[data-upgrade-open-plans]");
    if (openPlans) {
      openPlans.addEventListener("click", showPlansModal);
    }
  }

  if (plansModal) {
    plansModal.querySelectorAll("[data-upgrade-plans-close]").forEach(function (el) {
      el.addEventListener("click", hidePlansModal);
    });
    plansModal.addEventListener("click", function (event) {
      const btn = event.target.closest("[data-checkout]");
      if (!btn || btn.disabled) return;
      event.preventDefault();
      const original = btn.textContent;
      btn.disabled = true;
      btn.textContent = "Ouverture du paiement…";
      if (plansStatus) {
        plansStatus.hidden = true;
        plansStatus.textContent = "";
      }
      fetch("/api/payments/checkout/", {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrf(),
          "X-Requested-With": "XMLHttpRequest",
        },
        body: JSON.stringify({ tier: btn.getAttribute("data-checkout") }),
      })
        .then(function (res) {
          return res.json().then(function (payload) {
            if (!res.ok || !payload.ok) {
              throw new Error((payload && payload.message) || "Lien de paiement indisponible.");
            }
            return payload;
          });
        })
        .then(function (data) {
          if (!data.checkout_url) throw new Error("Lien de paiement indisponible.");
          window.location.href = data.checkout_url;
        })
        .catch(function (err) {
          if (plansStatus) {
            plansStatus.hidden = false;
            plansStatus.textContent = err.message || "Paiement indisponible pour le moment.";
          } else {
            toast(err.message || "Paiement indisponible pour le moment.");
          }
        })
        .finally(function () {
          btn.disabled = false;
          btn.textContent = original;
        });
    });
  }

  document.addEventListener("keydown", function (event) {
    if (event.key !== "Escape") return;
    if (plansModal && !plansModal.hidden) {
      hidePlansModal();
      return;
    }
    if (limitPopup && !limitPopup.hidden) hideLimitPopup();
  });

  function sendTextMessage(content) {
    return fetch("/api/messages/", {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrf(),
        "X-Requested-With": "XMLHttpRequest",
      },
      body: JSON.stringify({ partner_id: partnerId, content: content }),
    }).then(function (res) {
      return res.json().then(function (payload) {
        if (!res.ok || !payload.ok) {
          throw failFromPayload(payload, "Envoi impossible.");
        }
        return payload;
      });
    });
  }

  if (partnerId && thread) {
    connectChatWebSocket();
    markPartnerMessagesRead(partnerId);
    syncReadReceipts(partnerId);
    pinToLatest();
    document.addEventListener("visibilitychange", function () {
      window.clearTimeout(chatWsHideTimer);
      if (document.hidden) {
        chatWsHideTimer = window.setTimeout(function () {
          if (document.hidden && chatWs) chatWs.close();
        }, 45000);
      } else {
        connectChatWebSocket();
        markPartnerMessagesRead(partnerId);
      }
    });
  }

  if (input) {
    const maxPx = 7.5 * 16;
    function resize() {
      input.style.height = "auto";
      input.style.height = Math.min(input.scrollHeight, maxPx) + "px";
      input.style.overflowY = input.scrollHeight > maxPx ? "auto" : "hidden";
    }
    input.addEventListener("input", resize);
    resize();
    input.addEventListener("keydown", function (event) {
      if (event.key !== "Enter" || event.shiftKey) return;
      event.preventDefault();
      if (form && input.value.trim()) form.requestSubmit();
    });
  }

  if (form) {
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      if (!input || !input.value.trim() || !partnerId) return;
      if (form.getAttribute("data-quota-locked") === "1") {
        showLimitPopup();
        return;
      }
      const content = input.value.trim();
      const sendBtn = form.querySelector(".msg__send");
      if (sendBtn) sendBtn.disabled = true;
      sendTextMessage(content)
        .then(function (payload) {
          input.value = "";
          input.dispatchEvent(new Event("input"));
          if (payload.item) {
            appendBubble(normalizeChatItem(payload.item));
          }
          syncReadReceipts(partnerId);
        })
        .catch(function (err) {
          if (!handleLimitFailure(err)) toast(err.message || "Envoi impossible.");
        })
        .finally(function () {
          if (sendBtn) sendBtn.disabled = false;
          input.focus();
        });
    });
  }

  document.addEventListener("click", function (event) {
    const deleteBtn = event.target.closest("[data-msg-delete]");
    if (deleteBtn) {
      event.preventDefault();
      const row = deleteBtn.closest(".msg__row");
      const messageId = row && row.getAttribute("data-msg-id");
      if (!messageId) return;
      openDeleteModal(row, messageId, deleteBtn);
      return;
    }

    const voiceBtn = event.target.closest('[data-msg-tool="voice"]');
    if (voiceBtn) {
      event.preventDefault();
      if (form && form.getAttribute("data-quota-locked") === "1") {
        showLimitPopup();
        return;
      }
      startRecord();
      return;
    }
    const photoBtn = event.target.closest('[data-msg-tool="photos"]');
    if (photoBtn && photoInput) {
      event.preventDefault();
      if (form && form.getAttribute("data-quota-locked") === "1") {
        showLimitPopup();
        return;
      }
      photoInput.click();
      return;
    }
    if (event.target.closest("[data-msg-record-cancel]")) {
      event.preventDefault();
      cancelRecord();
      return;
    }
    if (event.target.closest("[data-msg-record-send]")) {
      event.preventDefault();
      sendRecord();
    }
  });

  if (photoInput) {
    photoInput.addEventListener("change", function () {
      const file = photoInput.files && photoInput.files[0];
      photoInput.value = "";
      if (!file) return;
      compressImage(file)
        .then(function (blob) {
          return uploadMedia("photo", blob, "photo.jpg");
        })
        .then(function (item) {
          appendBubble(normalizeChatItem(item));
        })
        .catch(function (err) {
          if (!handleLimitFailure(err)) toast(err.message || "Envoi de la photo impossible.");
        });
    });
  }

  bindLightbox();

  /* — Suppression message — */
  const deleteModal = document.getElementById("msg-delete-modal");
  const deleteConfirmBtn = document.querySelector("[data-msg-delete-confirm]");
  let pendingDelete = { row: null, messageId: "", trigger: null };

  function closeDeleteModal() {
    if (!deleteModal) return;
    deleteModal.hidden = true;
    document.body.classList.remove("is-msg-delete");
    pendingDelete = { row: null, messageId: "", trigger: null };
    if (deleteConfirmBtn) deleteConfirmBtn.disabled = false;
  }

  function openDeleteModal(row, messageId, trigger) {
    if (!deleteModal || !messageId) return;
    pendingDelete = { row: row, messageId: messageId, trigger: trigger };
    deleteModal.hidden = false;
    document.body.classList.add("is-msg-delete");
    if (deleteConfirmBtn) deleteConfirmBtn.focus();
  }

  function executeDelete() {
    const row = pendingDelete.row;
    const messageId = pendingDelete.messageId;
    const trigger = pendingDelete.trigger;
    if (!messageId) return;
    if (deleteConfirmBtn) deleteConfirmBtn.disabled = true;
    if (trigger) trigger.disabled = true;
    fetch("/api/messages/" + messageId + "/", {
      method: "DELETE",
      credentials: "same-origin",
      headers: {
        "X-CSRFToken": csrf(),
        "X-Requested-With": "XMLHttpRequest",
      },
    })
      .then(function (res) {
        return res.json().then(function (data) {
          return { ok: res.ok, data: data };
        });
      })
      .then(function (result) {
        if (!result.ok || !result.data.ok) {
          throw new Error((result.data && result.data.message) || "Suppression impossible.");
        }
        closeDeleteModal();
        if (row) row.remove();
        if (thread && !thread.querySelector(".msg__row")) {
          const empty = document.createElement("p");
          empty.className = "msg__empty";
          empty.textContent = "Dites bonjour, avec douceur.";
          thread.appendChild(empty);
        }
        toast("Message supprimé.");
      })
      .catch(function (err) {
        toast(err.message || "Suppression impossible.");
        if (deleteConfirmBtn) deleteConfirmBtn.disabled = false;
        if (trigger) trigger.disabled = false;
      });
  }

  if (deleteModal) {
    deleteModal.querySelectorAll("[data-msg-delete-close]").forEach(function (btn) {
      btn.addEventListener("click", closeDeleteModal);
    });
    deleteConfirmBtn?.addEventListener("click", executeDelete);
    document.addEventListener("keydown", function (event) {
      if (deleteModal.hidden) return;
      if (event.key === "Escape") {
        event.preventDefault();
        closeDeleteModal();
      }
    });
  }

  /* — Options : bloquer / signaler — */
  const moreBtn = document.querySelector("[data-msg-more]");
  const moreMenu = document.querySelector("[data-msg-more-menu]");
  const reportModal = document.getElementById("msg-report-modal");
  const reportForm = document.querySelector("[data-msg-report-form]");
  const reportError = document.querySelector("[data-msg-report-error]");

  function apiJSON(url, method, body) {
    return fetch(url, {
      method: method || "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrf(),
      },
      body: body ? JSON.stringify(body) : undefined,
    }).then(function (res) {
      return res.json().then(function (data) {
        if (!res.ok || !data.ok) throw new Error(data.message || "Action impossible.");
        return data;
      });
    });
  }

  function closeMoreMenu() {
    if (!moreMenu || !moreBtn) return;
    moreMenu.hidden = true;
    moreBtn.setAttribute("aria-expanded", "false");
  }

  function openReportModal() {
    closeMoreMenu();
    if (!reportModal) return;
    reportModal.hidden = false;
    document.body.classList.add("is-msg-report");
    reportForm && reportForm.reset();
    if (reportError) reportError.hidden = true;
    reportForm && reportForm.querySelector("[data-msg-report-message]")?.focus();
  }

  function closeReportModal() {
    if (!reportModal) return;
    reportModal.hidden = true;
    document.body.classList.remove("is-msg-report");
  }

  if (moreBtn && moreMenu) {
    moreBtn.addEventListener("click", function (event) {
      event.stopPropagation();
      const open = moreMenu.hidden;
      closeMoreMenu();
      if (open) {
        moreMenu.hidden = false;
        moreBtn.setAttribute("aria-expanded", "true");
      }
    });
    document.addEventListener("click", function (event) {
      if (!event.target.closest(".msg__more-wrap")) closeMoreMenu();
    });
  }

  document.querySelector("[data-msg-block]")?.addEventListener("click", function () {
    if (!partnerId) return;
    if (!window.confirm("Bloquer ce profil ? Vous ne recevrez plus ses messages.")) return;
    closeMoreMenu();
    apiJSON("/api/blocked-users/", "POST", { blocked_id: partnerId })
      .then(function () {
        toast("Profil bloqué.");
        window.setTimeout(function () {
          window.location.reload();
        }, 600);
      })
      .catch(function (err) {
        toast(err.message);
      });
  });

  document.querySelector("[data-msg-unblock]")?.addEventListener("click", function () {
    if (!partnerId) return;
    closeMoreMenu();
    apiJSON("/api/blocked-users/", "DELETE", { blocked_id: partnerId })
      .then(function () {
        toast("Profil débloqué.");
        window.setTimeout(function () {
          window.location.reload();
        }, 600);
      })
      .catch(function (err) {
        toast(err.message);
      });
  });

  document.querySelector("[data-msg-report-open]")?.addEventListener("click", openReportModal);

  document.querySelectorAll("[data-msg-report-close]").forEach(function (el) {
    el.addEventListener("click", closeReportModal);
  });

  if (reportForm) {
    reportForm.addEventListener("submit", function (event) {
      event.preventDefault();
      if (!partnerId) return;
      const reason = reportForm.querySelector("[data-msg-report-reason]")?.value || "other";
      const message = (reportForm.querySelector("[data-msg-report-message]")?.value || "").trim();
      if (message.length < 10) {
        if (reportError) {
          reportError.textContent = "Décrivez le motif en au moins 10 caractères.";
          reportError.hidden = false;
        }
        return;
      }
      if (reportError) reportError.hidden = true;
      apiJSON("/api/reports/", "POST", {
        reported_profile_id: partnerId,
        reason: reason,
        message: message,
        report_kind: "profile",
      })
        .then(function (data) {
          closeReportModal();
          toast(data.message || "Signalement envoyé.");
        })
        .catch(function (err) {
          if (reportError) {
            reportError.textContent = err.message;
            reportError.hidden = false;
          } else {
            toast(err.message);
          }
        });
    });
  }
})();
