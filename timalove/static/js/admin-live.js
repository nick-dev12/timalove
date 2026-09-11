(function () {
  const PALETTE = ["#E8637A", "#5C3A3F", "#C4858B", "#D4A017", "#2196F3", "#4CAF50"];

  const AdmLive = {
    pending: 0,
    lastSync: null,

    applySyncMeta(sync) {
      if (!sync || typeof sync !== "object") return;
      this.lastSync = sync;
      this.updateBar();
    },

    markPending() {
      this.pending += 1;
      this.updateBar();
    },

    markDone() {
      this.pending = Math.max(0, this.pending - 1);
      this.updateBar();
    },

    updateBar() {
      const text = document.querySelector("[data-adm-live-text]");
      const bar = document.querySelector("[data-adm-live-bar]");
      if (!text) return;
      if (this.pending > 0) {
        if (bar) bar.classList.add("is-syncing");
        text.textContent = `Synchronisation NabooPay… (${this.pending} bloc${this.pending > 1 ? "s" : ""})`;
        return;
      }
      if (bar) bar.classList.remove("is-syncing");
      const sync = this.lastSync;
      if (sync?.new_count > 0) {
        const parts = [`${sync.new_count} nouvelle(s) transaction(s)`];
        if (sync.updated_count > 0) parts.push(`${sync.updated_count} mise(s) à jour`);
        text.textContent = `${parts.join(" · ")} — ${sync.synced_label || "à l'instant"}`;
        return;
      }
      if (sync?.from_cache && sync?.synced_label) {
        text.textContent = `Cache NabooPay (${sync.row_count || 0} tx) · ${sync.synced_label}`;
        return;
      }
      if (sync?.synced_label) {
        text.textContent = `Synchronisé · ${sync.synced_label}`;
        return;
      }
      const now = new Date().toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
      text.textContent = `Données à jour · ${now}`;
    },

    reveal(root) {
      if (!root) return;
      root.classList.remove("adm-live-loading");
      root.classList.add("adm-live-ready");
    },

    async fetchJson(url) {
      this.markPending();
      try {
        const res = await fetch(url, {
          headers: { "X-Requested-With": "XMLHttpRequest", Accept: "application/json" },
          credentials: "same-origin",
        });
        if (!res.ok) throw new Error("fetch");
        return await res.json();
      } finally {
        this.markDone();
      }
    },

    channelColor(index) {
      return PALETTE[index % PALETTE.length];
    },

    formatFcfa(value) {
      return `${Number(value || 0).toLocaleString("fr-FR")} FCFA`;
    },

    buildChannelMini(channels, listEl) {
      if (!listEl) return;
      const labels = channels?.labels || [];
      const values = channels?.values || [];
      if (!labels.length) {
        listEl.innerHTML = '<li class="adm-channel-mini__empty">Aucun encaissement sur la période</li>';
        return;
      }
      const total = values.reduce((a, b) => a + b, 0) || 1;
      listEl.innerHTML = labels
        .map((label, i) => {
          const amount = values[i] || 0;
          const pct = Math.round((amount / total) * 1000) / 10;
          const color = this.channelColor(i);
          return `<li class="adm-channel-mini__item"><span class="adm-channel-mini__dot" style="background:${color}"></span><span>${label}</span><strong>${this.formatFcfa(amount)}</strong><span class="adm-channel-mini__pct">${pct} %</span></li>`;
        })
        .join("");
    },
  };

  window.AdmLive = AdmLive;
})();
