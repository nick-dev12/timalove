/**
 * TimaLove — filtre local des discussions dans l’inbox.
 */
(function () {
  const form = document.querySelector("[data-msg-search]");
  const feed = document.querySelector("[data-msg-feed]");
  if (!form || !feed) return;

  const input = form.querySelector("input[type='search']");
  const clearBtn = form.querySelector("[data-search-clear]");
  const cards = Array.from(feed.querySelectorAll("[data-msg-card]"));
  const empty = document.querySelector("[data-msg-empty-search]");
  if (!input) return;

  function normalize(value) {
    return (value || "")
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .trim();
  }

  function filter() {
    const query = normalize(input.value);
    if (clearBtn) clearBtn.hidden = !input.value;
    let shown = 0;
    cards.forEach((card) => {
      const hay = normalize(card.getAttribute("data-msg-search") || card.textContent);
      const match = !query || hay.includes(query);
      card.hidden = !match;
      if (match) shown += 1;
    });
    if (empty) empty.hidden = shown > 0;
  }

  input.addEventListener("input", filter);
  input.addEventListener("search", filter);
  if (clearBtn) {
    clearBtn.addEventListener("click", () => {
      input.value = "";
      filter();
      input.focus();
    });
  }
  filter();
})();
