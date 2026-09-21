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

  function syncMessageAccess(profileId) {
    if (!profileId) return;
    const id = String(profileId);
    document
      .querySelectorAll(
        '[data-msg-like-required][data-profile-id="' +
          id +
          '"], [data-profile-id="' +
          id +
          '"] [data-msg-like-required]'
      )
      .forEach(function (el) {
        el.removeAttribute("data-msg-like-required");
        el.setAttribute("data-msg-open", "");
        el.classList.remove("visit__action--msg-muted", "curated-card__msg--muted");
      });
  }

  window.timaloveOpenConversation = openConversation;
  window.timaloveSyncMessageAccess = syncMessageAccess;

  document.addEventListener("timalove:swipe", function (event) {
    const detail = (event && event.detail) || {};
    if (detail.action !== "like" && detail.action !== "super_like") return;
    syncMessageAccess(detail.profileId);
  });

  const likeRequiredModal = document.getElementById("message-like-required");
  const likeRequiredTitle = likeRequiredModal && likeRequiredModal.querySelector("[data-like-required-title]");
  const likeRequiredLead = likeRequiredModal && likeRequiredModal.querySelector("[data-like-required-lead]");
  const likeRequiredSteps = likeRequiredModal && likeRequiredModal.querySelector("[data-like-required-steps]");
  let likeRequiredProfileId = "";

  function closeLikeRequired() {
    if (!likeRequiredModal) return;
    likeRequiredModal.hidden = true;
    document.body.classList.remove("is-msg-like-required");
    likeRequiredProfileId = "";
  }

  function findLikeScope(profileId) {
    if (profileId) {
      const scoped =
        document.querySelector('.visit[data-profile-id="' + profileId + '"]') ||
        document.querySelector('.curated-card[data-profile-id="' + profileId + '"]');
      if (scoped) return scoped;
    }
    return document.querySelector("#profile-modal .visit") || document.querySelector(".curated-card");
  }

  function highlightLikeButton(profileId) {
    const scope = findLikeScope(profileId);
    if (!scope) return;
    const likeBtn = scope.querySelector('[data-swipe="like"]');
    if (!likeBtn) return;
    likeBtn.classList.add("is-like-hint");
    if (typeof likeBtn.focus === "function") {
      likeBtn.focus({ preventScroll: true });
    }
    likeBtn.scrollIntoView({ behavior: "smooth", block: "nearest" });
    window.clearTimeout(highlightLikeButton._t);
    highlightLikeButton._t = window.setTimeout(function () {
      likeBtn.classList.remove("is-like-hint");
    }, 4800);
  }

  function showLikeRequired(options) {
    const name = (options && options.name) || "ce profil";
    likeRequiredProfileId = (options && options.profileId) || "";
    const scope = findLikeScope(likeRequiredProfileId);
    const onCuratedCard = Boolean(scope && scope.classList.contains("curated-card"));
    if (likeRequiredModal) {
      if (likeRequiredTitle) {
        likeRequiredTitle.textContent = "D’abord, manifestez votre intérêt";
      }
      if (likeRequiredLead) {
        likeRequiredLead.textContent =
          "Pour écrire à " +
          name +
          ", appuyez d’abord sur le bouton ♥. Ensuite, le bouton Message s’ouvrira.";
      }
      if (likeRequiredSteps) {
        likeRequiredSteps.innerHTML = onCuratedCard
          ? "<li>Appuyez sur <strong>♥</strong> sur la carte</li><li>Puis retouchez <strong>Message</strong></li>"
          : "<li>Appuyez sur <strong>♥</strong> en bas de l’écran</li><li>Puis retouchez <strong>Message</strong></li>";
      }
      likeRequiredModal.hidden = false;
      document.body.classList.add("is-msg-like-required");
      return;
    }
    toast("Appuyez sur ♥ pour " + name + ", puis retouchez Message.");
  }

  window.timaloveShowLikeRequired = showLikeRequired;

  if (likeRequiredModal) {
    const goLikeBtn = likeRequiredModal.querySelector("[data-like-required-go-like]");
    goLikeBtn?.addEventListener("click", function () {
      const profileId = likeRequiredProfileId;
      closeLikeRequired();
      highlightLikeButton(profileId);
    });
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
    const msgBtn = event.target.closest("[data-msg-open], [data-msg-like-required]");
    if (msgBtn) {
      event.preventDefault();
      event.stopPropagation();
      openConversation(msgBtn.getAttribute("data-profile-id") || "", {
        trigger: msgBtn,
        name:
          msgBtn.getAttribute("data-profile-name") ||
          msgBtn.getAttribute("aria-label") ||
          "ce profil",
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
          action === "super_like" ? "Priorité — mise en relation !" : "Mise en relation réussie !";
      }
      if (els.lead) {
        els.lead.textContent = "Une belle rencontre commence par un message sincère.";
      }
    } else if (action === "super_like") {
      if (els.kicker) els.kicker.textContent = "Priorité envoyée";
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
