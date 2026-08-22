/**
 * TimaLove — inbox messages : recherche temps réel + suggestions + feed live.
 */
(function () {
  const form = document.querySelector("[data-msg-search-form]");
  const feed = document.querySelector("[data-msg-feed]");
  if (!form) return;

  const input = form.querySelector("input[type='search']");
  const clearBtn = form.querySelector("[data-search-clear]");
  const results = document.getElementById("msg-search-results");
  const emptySearch = document.querySelector("[data-msg-empty-search]");
  if (!input) return;

  let rows = [];
  let refreshTimer = null;
  let refreshInFlight = false;
  let suggestTimer = null;

  function csrf() {
    const m = document.cookie.match(/(?:^|; )csrftoken=([^;]*)/);
    return m ? decodeURIComponent(m[1]) : "";
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

  function escapeHtml(value) {
    return String(value || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function normalize(value) {
    return (value || "")
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .trim();
  }

  function highlightMatch(text, query) {
    const source = String(text || "");
    if (!query) return escapeHtml(source);
    const normText = normalize(source);
    const idx = normText.indexOf(query);
    if (idx === -1) return escapeHtml(source);
    const end = idx + query.length;
    return (
      escapeHtml(source.slice(0, idx)) +
      "<mark>" +
      escapeHtml(source.slice(idx, end)) +
      "</mark>" +
      escapeHtml(source.slice(end))
    );
  }

  function rowMeta(row) {
    const card = row.querySelector("[data-msg-card]");
    if (!card) return null;
    const nameEl = card.querySelector(".msg-list__row-top strong");
    const previewEl = card.querySelector(".msg-list__preview");
    const avatarEl = card.querySelector(".msg-list__avatar img");
    const initialEl = card.querySelector(".msg-list__avatar span");
    return {
      row: row,
      href: card.getAttribute("href") || "",
      name: nameEl ? nameEl.textContent.trim() : "",
      preview: previewEl ? previewEl.textContent.trim() : "",
      photo: avatarEl ? avatarEl.getAttribute("src") : "",
      initial: initialEl ? initialEl.textContent.trim() : "",
      haystack: normalize(card.getAttribute("data-msg-search")) || normalize(row.textContent),
    };
  }

  function collectRows() {
    rows = feed ? Array.from(feed.querySelectorAll("[data-msg-row]")) : [];
  }

  function closeSuggestions() {
    if (results) results.innerHTML = "";
  }

  function renderSuggestions(query) {
    if (!results || !query) {
      closeSuggestions();
      return;
    }

    const matches = rows
      .map(rowMeta)
      .filter(function (item) {
        return item && item.haystack.includes(query);
      })
      .slice(0, 6);

    if (!matches.length) {
      results.innerHTML =
        '<p class="explorer-search__empty">Aucune discussion pour « ' + escapeHtml(input.value.trim()) + " »</p>";
      return;
    }

    const items = matches
      .map(function (item, index) {
        const photoInner = item.photo
          ? '<img src="' + escapeHtml(item.photo) + '" alt="">'
          : "<span>" + escapeHtml(item.initial || item.name.charAt(0) || "?") + "</span>";
        return (
          '<li role="presentation">' +
          '<a class="explorer-search__hit explorer-search__hit--thread" href="' +
          escapeHtml(item.href) +
          '" role="option" data-suggest-index="' +
          index +
          '">' +
          '<span class="explorer-search__photo" aria-hidden="true">' +
          photoInner +
          "</span>" +
          '<span class="explorer-search__meta">' +
          "<strong>" +
          highlightMatch(item.name, query) +
          "</strong>" +
          "<em>" +
          highlightMatch(item.preview, query) +
          "</em>" +
          "</span>" +
          "</a></li>"
        );
      })
      .join("");

    results.innerHTML = '<ul class="explorer-search__list" role="listbox">' + items + "</ul>";
  }

  function filter() {
    const query = normalize(input.value);
    if (clearBtn) clearBtn.hidden = !input.value;

    if (!feed) {
      window.clearTimeout(suggestTimer);
      suggestTimer = window.setTimeout(function () {
        renderSuggestions(query);
      }, 120);
      return;
    }

    let shown = 0;
    rows.forEach(function (row) {
      const card = row.querySelector("[data-msg-card]");
      const hay =
        normalize(card && card.getAttribute("data-msg-search")) || normalize(row.textContent);
      const match = !query || hay.includes(query);
      row.hidden = !match;
      if (match) shown += 1;
    });
    if (emptySearch) emptySearch.hidden = shown > 0;

    window.clearTimeout(suggestTimer);
    suggestTimer = window.setTimeout(function () {
      renderSuggestions(query);
    }, 120);
  }

  function renderBlockedActions(partnerId) {
    return (
      '<div class="msg-list__actions">' +
      '<button type="button" class="msg-list__more" aria-label="Options" aria-expanded="false" data-msg-inbox-more>' +
      '<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><path fill="currentColor" d="M12 7.75a1.75 1.75 0 1 1 0-3.5 1.75 1.75 0 0 1 0 3.5zm0 6a1.75 1.75 0 1 1 0-3.5 1.75 1.75 0 0 1 0 3.5zm0 6a1.75 1.75 0 1 1 0-3.5 1.75 1.75 0 0 1 0 3.5z"/></svg>' +
      "</button>" +
      '<div class="msg-list__menu" data-msg-inbox-menu hidden role="menu">' +
      '<button type="button" class="msg-list__menu-item" role="menuitem" data-msg-inbox-unblock>Débloquer</button>' +
      '<button type="button" class="msg-list__menu-item msg-list__menu-item--danger" role="menuitem" data-msg-inbox-delete>Supprimer la discussion</button>' +
      "</div></div>"
    );
  }

  function renderRow(item) {
    const article = document.createElement("article");
    article.className = "msg-list__item" + (item.blocked_by_me ? " is-blocked" : "");
    article.setAttribute("data-msg-row", "");
    article.setAttribute("data-partner-id", item.partner_id);

    const searchHay = item.partner_name + " " + item.preview;
    const cardClass =
      "msg-list__card" + (item.unread > 0 && !item.blocked_by_me ? " is-unread" : "");
    const avatarInner = item.partner_photo
      ? '<img src="' + escapeHtml(item.partner_photo) + '" alt="">'
      : "<span>" + escapeHtml(item.partner_initial) + "</span>";
    const onlineDot = item.partner_online ? '<i class="msg-list__online"></i>' : "";
    const blockedBadge = item.blocked_by_me
      ? '<span class="msg-list__blocked-badge">Bloqué</span>'
      : "";
    const timeHtml = item.last_time ? "<time>" + escapeHtml(item.last_time) + "</time>" : "";
    const unreadHtml =
      item.unread > 0 && !item.blocked_by_me
        ? '<span class="msg-list__unread">' +
          (item.unread > 99 ? "99+" : String(item.unread)) +
          "</span>"
        : "";

    article.innerHTML =
      '<a class="' +
      cardClass +
      '" href="' +
      escapeHtml(item.thread_url) +
      '" data-msg-card data-msg-search="' +
      escapeHtml(searchHay) +
      '">' +
      '<span class="msg-list__avatar" aria-hidden="true">' +
      avatarInner +
      onlineDot +
      "</span>" +
      '<span class="msg-list__body">' +
      '<span class="msg-list__row-top">' +
      "<strong>" +
      escapeHtml(item.partner_name) +
      "</strong>" +
      blockedBadge +
      timeHtml +
      "</span>" +
      '<span class="msg-list__preview">' +
      escapeHtml(item.preview) +
      "</span>" +
      "</span>" +
      unreadHtml +
      "</a>" +
      (item.blocked_by_me ? renderBlockedActions(item.partner_id) : "");

    return article;
  }

  function renderFeed(items) {
    if (!feed) return;
    feed.innerHTML = "";
    items.forEach(function (item) {
      feed.appendChild(renderRow(item));
    });
    collectRows();
    filter();
  }

  function refreshInbox() {
    if (!feed || refreshInFlight) return Promise.resolve();
    refreshInFlight = true;
    return fetch("/api/messages/inbox/", {
      credentials: "same-origin",
      headers: { "X-Requested-With": "XMLHttpRequest" },
    })
      .then(function (res) {
        if (!res.ok) throw new Error("inbox");
        return res.json();
      })
      .then(function (data) {
        renderFeed(data.items || []);
        if (typeof window.timaloveRenderUnreadBadge === "function") {
          window.timaloveRenderUnreadBadge(data.total_unread);
        }
      })
      .catch(function () {})
      .finally(function () {
        refreshInFlight = false;
      });
  }

  function closeAllMenus() {
    if (!feed) return;
    feed.querySelectorAll("[data-msg-inbox-menu]").forEach(function (menu) {
      menu.hidden = true;
    });
    feed.querySelectorAll("[data-msg-inbox-more]").forEach(function (btn) {
      btn.setAttribute("aria-expanded", "false");
    });
  }

  input.addEventListener("input", filter);
  input.addEventListener("search", filter);
  input.addEventListener("focus", filter);

  if (clearBtn) {
    clearBtn.addEventListener("click", function () {
      input.value = "";
      filter();
      closeSuggestions();
      input.focus();
    });
  }

  form.addEventListener("click", function (event) {
    if (event.target.closest("[data-search-clear]")) return;
    if (event.target.closest(".explorer-search__hit--thread")) {
      closeSuggestions();
    }
  });

  document.addEventListener("click", function (event) {
    if (!form.contains(event.target)) closeSuggestions();
  });

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") {
      closeSuggestions();
      input.blur();
    }
  });

  if (feed) {
    feed.addEventListener("click", function (event) {
      const moreBtn = event.target.closest("[data-msg-inbox-more]");
      if (moreBtn) {
        event.preventDefault();
        event.stopPropagation();
        const row = moreBtn.closest("[data-msg-row]");
        const menu = row && row.querySelector("[data-msg-inbox-menu]");
        if (!menu) return;
        const willOpen = menu.hidden;
        closeAllMenus();
        if (willOpen) {
          menu.hidden = false;
          moreBtn.setAttribute("aria-expanded", "true");
        }
        return;
      }

      const unblockBtn = event.target.closest("[data-msg-inbox-unblock]");
      if (unblockBtn) {
        event.preventDefault();
        event.stopPropagation();
        const row = unblockBtn.closest("[data-msg-row]");
        const partnerId = row && row.getAttribute("data-partner-id");
        if (!partnerId) return;
        closeAllMenus();
        apiJSON("/api/blocked-users/", "DELETE", { blocked_id: partnerId })
          .then(function () {
            toast("Profil débloqué.");
            return refreshInbox();
          })
          .catch(function (err) {
            toast(err.message);
          });
        return;
      }

      const deleteBtn = event.target.closest("[data-msg-inbox-delete]");
      if (deleteBtn) {
        event.preventDefault();
        event.stopPropagation();
        const row = deleteBtn.closest("[data-msg-row]");
        const partnerId = row && row.getAttribute("data-partner-id");
        if (!partnerId) return;
        if (!window.confirm("Supprimer cette discussion de votre liste ?")) return;
        closeAllMenus();
        apiJSON("/api/conversations/hide/", "POST", { partner_id: partnerId })
          .then(function () {
            row.remove();
            collectRows();
            toast("Discussion supprimée.");
            filter();
          })
          .catch(function (err) {
            toast(err.message);
          });
      }
    });

    document.addEventListener("click", function (event) {
      if (!event.target.closest(".msg-list__actions")) closeAllMenus();
    });

    document.addEventListener("timalove:inbox-refresh", function () {
      refreshInbox();
    });

    document.addEventListener("visibilitychange", function () {
      if (!document.hidden) refreshInbox();
    });

    collectRows();
    filter();
    refreshInbox();
    refreshTimer = window.setInterval(refreshInbox, 5000);

    window.timaloveInboxRefresh = refreshInbox;

    window.addEventListener("beforeunload", function () {
      window.clearInterval(refreshTimer);
    });
  } else {
    filter();
  }
})();
