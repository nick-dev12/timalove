/**
 * TimaLove — invitation à envoyer un message après like / super like.
 * + ouverture directe de conversation (historique, modale profil).
 */
(function () {
  function csrf() {
    const m = document.cookie.match(/(?:^|; )csrftoken=([^;]*)/);
    if (m) return decodeURIComponent(m[1]);
    const input = document.querySelector("[name=csrfmiddlewaretoken]");
    return input ? input.value : "";
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

  function openConversation(profileId, options) {
    const opts = options || {};
    if (!profileId) {
      return Promise.reject(new Error("Profil introuvable."));
    }
    const trigger = opts.trigger;
    if (trigger) trigger.classList.add("is-busy");

    return fetch("/api/messages/open/", {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrf(),
        "X-Requested-With": "XMLHttpRequest",
      },
      body: JSON.stringify({ partner_id: profileId }),
    })
      .then(function (res) {
        return res.json().then(function (data) {
          return { ok: res.ok, data: data };
        });
      })
      .then(function (result) {
        if (!result.ok || !result.data.ok) {
          const err = new Error((result.data && result.data.message) || "Impossible d’ouvrir la conversation.");
          err.code = result.data && result.data.code;
          throw err;
        }
        const url = result.data.thread_url || "/discussions/" + profileId + "/";
        window.location.href = url;
        return result.data;
      })
      .catch(function (err) {
        const msg = err && err.message ? err.message : "Impossible d’ouvrir la conversation.";
        if (err && err.code === "like_required") {
          showLikeRequired({
            profileId: profileId,
            name: opts.name || "",
          });
        } else if (opts.onError) {
          opts.onError(msg);
        } else {
          toast(msg);
        }
        throw err;
      })
      .finally(function () {
        if (trigger) trigger.classList.remove("is-busy");
      });
  }

  window.timaloveOpenConversation = openConversation;

  const likeRequiredModal = document.getElementById("message-like-required");
  const likeRequiredTitle = likeRequiredModal && likeRequiredModal.querySelector("[data-like-required-title]");
  const likeRequiredLead = likeRequiredModal && likeRequiredModal.querySelector("[data-like-required-lead]");

  function closeLikeRequired() {
    if (!likeRequiredModal) return;
    likeRequiredModal.hidden = true;
    document.body.classList.remove("is-msg-like-required");
  }

  function showLikeRequired(options) {
    const name = (options && options.name) || "ce profil";
    if (likeRequiredModal) {
      if (likeRequiredTitle) {
        likeRequiredTitle.textContent = "Like requis pour écrire";
      }
      if (likeRequiredLead) {
        likeRequiredLead.textContent =
          "Likez ou super likez " +
          name +
          " avant de démarrer une discussion. Votre intérêt doit être sincère et explicite.";
      }
      likeRequiredModal.hidden = false;
      document.body.classList.add("is-msg-like-required");
      return;
    }
    toast("Likez ou super likez " + name + " avant de démarrer une discussion.");
  }

  window.timaloveShowLikeRequired = showLikeRequired;

  if (likeRequiredModal) {
    likeRequiredModal.querySelectorAll("[data-like-required-close]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        closeLikeRequired();
      });
    });
    document.addEventListener("keydown", function (event) {
      if (likeRequiredModal.hidden) return;
      if (event.key === "Escape") {
        event.preventDefault();
        closeLikeRequired();
      }
    });
  }

  document.addEventListener("click", function (event) {
    const likeRequired = event.target.closest("[data-msg-like-required]");
    if (likeRequired) {
      event.preventDefault();
      event.stopPropagation();
      showLikeRequired({
        profileId: likeRequired.getAttribute("data-profile-id") || "",
        name: likeRequired.getAttribute("data-profile-name") || "ce profil",
      });
      return;
    }

    const direct = event.target.closest("[data-msg-open]");
    if (direct) {
      event.preventDefault();
      event.stopPropagation();
      openConversation(direct.getAttribute("data-profile-id") || "", {
        trigger: direct,
        name: direct.getAttribute("data-profile-name") || direct.getAttribute("aria-label") || "",
      });
      return;
    }

    const inviteTrigger = event.target.closest("[data-msg-invite-open]");
    if (inviteTrigger && window.timaloveMessageInvite && typeof window.timaloveMessageInvite.open === "function") {
      event.preventDefault();
      event.stopPropagation();
      window.timaloveMessageInvite.open({
        profileId: inviteTrigger.getAttribute("data-profile-id") || "",
        name: inviteTrigger.getAttribute("data-profile-name") || "",
        photo: inviteTrigger.getAttribute("data-profile-photo") || "",
        matched: inviteTrigger.getAttribute("data-matched") === "1",
        action: inviteTrigger.getAttribute("data-action") || "like",
        fromExplorer: false,
      });
    }
  });

  const modal = document.getElementById("message-invite");
  if (!modal) {
    window.timaloveMessageInvite = window.timaloveMessageInvite || {
      open: function () {},
      close: function () {},
    };
    return;
  }

  const els = {
    mePhoto: modal.querySelector("[data-msg-invite-me-photo]"),
    partnerPhoto: modal.querySelector("[data-msg-invite-partner-photo]"),
    partnerInitial: modal.querySelector("[data-msg-invite-partner-initial]"),
    partnerWrap: modal.querySelector("[data-msg-invite-partner-wrap]"),
    kicker: modal.querySelector("[data-msg-invite-kicker]"),
    title: modal.querySelector("[data-msg-invite-title]"),
    lead: modal.querySelector("[data-msg-invite-lead]"),
    error: modal.querySelector("[data-msg-invite-error]"),
    openChat: modal.querySelector("[data-msg-invite-open-chat]"),
  };

  const meDefaults = {
    photo: modal.getAttribute("data-me-photo") || "",
    name: modal.getAttribute("data-me-name") || "",
  };

  let state = {
    profileId: "",
    matched: false,
    action: "like",
    fromExplorer: false,
    partnerName: "",
  };

  function goNextIfExplorer() {
    /* Le slide a déjà été retiré après le swipe : un autre profil est déjà visible. */
  }

  function closeModal() {
    modal.hidden = true;
    document.body.classList.remove("is-msg-invite");
    if (els.error) {
      els.error.hidden = true;
      els.error.textContent = "";
    }
    if (els.openChat) els.openChat.classList.remove("is-busy");
  }

  function setMePhoto(photo, name) {
    if (!els.mePhoto) return;
    if (photo) {
      els.mePhoto.src = photo;
      els.mePhoto.alt = name || "Mon profil";
      els.mePhoto.hidden = false;
      return;
    }
    els.mePhoto.removeAttribute("src");
    els.mePhoto.hidden = true;
  }

  function setPartnerFace(photo, name) {
    const initial = (name || "M").trim().charAt(0).toUpperCase() || "M";
    if (photo && els.partnerPhoto) {
      els.partnerPhoto.src = photo;
      els.partnerPhoto.alt = name || "";
      els.partnerPhoto.hidden = false;
      if (els.partnerInitial) els.partnerInitial.hidden = true;
      if (els.partnerWrap) els.partnerWrap.classList.remove("is-initial");
      return;
    }
    if (els.partnerPhoto) {
      els.partnerPhoto.removeAttribute("src");
      els.partnerPhoto.hidden = true;
    }
    if (els.partnerInitial) {
      els.partnerInitial.textContent = initial;
      els.partnerInitial.hidden = false;
    }
    if (els.partnerWrap) els.partnerWrap.classList.add("is-initial");
  }

  function openModal(options) {
    const profileId = options.profileId || "";
    const name = options.name || "Membre";
    const photo = options.photo || "";
    const matched = Boolean(options.matched);
    const action = options.action === "super_like" ? "super_like" : "like";
    const mePhoto = options.mePhoto || meDefaults.photo;
    const meName = options.meName || meDefaults.name;

    state = {
      profileId: profileId,
      matched: matched,
      action: action,
      fromExplorer: Boolean(options.fromExplorer),
      partnerName: name,
    };

    setMePhoto(mePhoto, meName);
    setPartnerFace(photo, name);

    if (els.title) els.title.textContent = name;

    if (matched) {
      if (els.kicker) {
        els.kicker.textContent =
          action === "super_like" ? "Super like — c’est un match !" : "C’est un match !";
      }
      if (els.lead) {
        els.lead.textContent = "Une belle rencontre commence par un message sincère.";
      }
    } else if (action === "super_like") {
      if (els.kicker) els.kicker.textContent = "Super like envoyé";
      if (els.lead) {
        els.lead.textContent =
          "Vous avez marqué votre intérêt. Écrivez à " + name + " pour vous présenter.";
      }
    } else {
      if (els.kicker) els.kicker.textContent = "Like envoyé";
      if (els.lead) {
        els.lead.textContent =
          "Votre regard est parti. Ouvrez la conversation pour faire connaissance.";
      }
    }

    modal.hidden = false;
    document.body.classList.add("is-msg-invite");
    window.setTimeout(function () {
      if (els.openChat) els.openChat.focus();
    }, 80);
  }

  modal.querySelectorAll("[data-msg-invite-close]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      closeModal();
      goNextIfExplorer();
    });
  });

  els.openChat?.addEventListener("click", function () {
    if (!state.profileId) return;
    if (els.error) {
      els.error.hidden = true;
      els.error.textContent = "";
    }
    openConversation(state.profileId, {
      trigger: els.openChat,
      name: state.partnerName,
      onError: function (msg) {
        if (els.error) {
          els.error.textContent = msg;
          els.error.hidden = false;
        }
      },
    });
  });

  document.addEventListener("keydown", function (event) {
    if (modal.hidden) return;
    if (event.key === "Escape") {
      event.preventDefault();
      closeModal();
      goNextIfExplorer();
    }
  });

  window.timaloveMessageInvite = {
    open: openModal,
    close: closeModal,
  };
})();
