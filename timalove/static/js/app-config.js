(function () {
  const WEB_APP_VERSION = "2026.08.1";

  function compareVersions(current, minimum) {
    const left = String(current || "0").split(".").map((part) => parseInt(part.replace(/\D/g, ""), 10) || 0);
    const right = String(minimum || "0").split(".").map((part) => parseInt(part.replace(/\D/g, ""), 10) || 0);
    const len = Math.max(left.length, right.length);
    for (let i = 0; i < len; i += 1) {
      const a = left[i] || 0;
      const b = right[i] || 0;
      if (a < b) return -1;
      if (a > b) return 1;
    }
    return 0;
  }

  function ensureForceBanner() {
    let banner = document.getElementById("timalove-force-update");
    if (banner) return banner;
    banner = document.createElement("div");
    banner.id = "timalove-force-update";
    banner.className = "force-update-banner";
    banner.hidden = true;
    banner.innerHTML =
      '<div class="force-update-banner__inner">' +
      '<p class="force-update-banner__text" data-force-text></p>' +
      '<a class="force-update-banner__cta" data-force-link hidden>Mettre à jour</a>' +
      "</div>";
    document.body.appendChild(banner);
    return banner;
  }

  function showForceUpdate(block) {
    const banner = ensureForceBanner();
    banner.querySelector("[data-force-text]").textContent =
      block.message || "Une mise à jour est requise pour continuer.";
    const link = banner.querySelector("[data-force-link]");
    if (block.store_url) {
      link.href = block.store_url;
      link.hidden = false;
    } else {
      link.hidden = true;
    }
    banner.hidden = false;
    document.body.classList.add("has-force-update");
  }

  function applyFeatureFlags(features) {
    if (!features || typeof features !== "object") return;
    const textOn = features.text_messages_enabled !== false;
    const voiceOn =
      features.voice_messages_enabled != null
        ? !!features.voice_messages_enabled
        : features.voice_call_enabled !== false;
    const imageOn = features.image_messages_enabled !== false;
    const selfieOn = !!features.selfie_verification_enabled;
    document.body.dataset.videoChat = features.video_chat_enabled ? "1" : "0";
    document.body.dataset.voiceCall = voiceOn ? "1" : "0";
    document.body.dataset.textMessages = textOn ? "1" : "0";
    document.body.dataset.imageMessages = imageOn ? "1" : "0";
    document.body.dataset.selfieVerify = selfieOn ? "1" : "0";
    document.querySelectorAll("[data-msg-tool='voice']").forEach((btn) => {
      btn.hidden = !voiceOn;
    });
    document.querySelectorAll("[data-msg-tool='photos']").forEach((btn) => {
      btn.hidden = !imageOn;
    });
    document.querySelectorAll("[data-msg-input]").forEach((el) => {
      el.disabled = !textOn;
      if (!textOn) el.placeholder = "Les messages texte sont désactivés.";
    });
    document.querySelectorAll("[data-msg-send-text]").forEach((btn) => {
      btn.hidden = !textOn;
    });
    document.querySelectorAll("[data-text-enabled]").forEach((el) => {
      el.setAttribute("data-text-enabled", textOn ? "1" : "0");
    });
    document.querySelectorAll("[data-video-chat]").forEach((btn) => {
      btn.hidden = !features.video_chat_enabled;
    });
    document.querySelectorAll("[data-selfie-slot], [data-selfie-hint]").forEach((el) => {
      el.hidden = !selfieOn;
    });
  }

  async function loadConfig() {
    try {
      const res = await fetch(
        `/api/app-config/?platform=web&app_version=${encodeURIComponent(WEB_APP_VERSION)}`,
        { credentials: "same-origin", headers: { "X-Requested-With": "XMLHttpRequest" } }
      );
      if (res.status === 426) {
        const block = await res.json();
        showForceUpdate(block);
        return;
      }
      if (!res.ok) return;
      const data = await res.json();
      applyFeatureFlags(data.features || {});
      if (data.forceUpdateBlock) {
        showForceUpdate(data.forceUpdateBlock);
      }
    } catch (_err) {
      /* ignore */
    }
  }

  document.addEventListener("DOMContentLoaded", loadConfig);
})();
