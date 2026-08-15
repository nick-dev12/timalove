/**
 * TimaLove — barre de recherche explorer (fermeture, effacer).
 */
(function () {
  const root = document.querySelector("[data-explorer-search]");
  if (!root) return;

  const input = root.querySelector("input[name='q']");
  const results = document.getElementById("explorer-search-results");
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
    clearBtn.addEventListener("click", () => {
      input.value = "";
      closeResults();
      syncClear();
      input.focus();
    });
  }

  document.addEventListener("click", (event) => {
    if (!root.contains(event.target)) closeResults();
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && hasResults()) {
      closeResults();
      input.blur();
    }
  });
})();
