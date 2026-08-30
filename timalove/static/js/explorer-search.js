/**
 * TimaLove — barre de recherche live (explorer / historique).
 */
(function () {
  document.querySelectorAll("[data-explorer-search]").forEach(function (root) {
    const input = root.querySelector("input[name='q']");
    const results = root.querySelector(".explorer-search__results");
    const clearBtn = root.querySelector("[data-search-clear]");
    if (!input || !results) return;

    function hasResults() {
      return Boolean(results.innerHTML.trim());
    }

    function syncClear() {
      if (clearBtn) clearBtn.hidden = !input.value;
    }

    function closeResults() {
      results.innerHTML = "";
    }

    input.addEventListener("input", syncClear);
    syncClear();

    if (clearBtn) {
      clearBtn.addEventListener("click", function () {
        input.value = "";
        closeResults();
        syncClear();
        input.focus();
        input.dispatchEvent(new Event("search", { bubbles: true }));
      });
    }

    document.addEventListener("click", function (event) {
      if (!root.contains(event.target)) closeResults();
    });

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && hasResults()) {
        closeResults();
        input.blur();
      }
    });
  });
})();
