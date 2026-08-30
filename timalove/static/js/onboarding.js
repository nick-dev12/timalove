/**
 * TimaLove — onboarding 4 étapes + caméra de vérification.
 */
(function () {
  const CIRC = 97.4;
  const ICONS = {
    plane: '<svg viewBox="0 0 24 24" width="28" height="28"><path fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round" d="M2 12l20-8-8 20-3-7-7-3z"/></svg>',
    book: '<svg viewBox="0 0 24 24" width="28" height="28"><path fill="none" stroke="currentColor" stroke-width="1.7" d="M4 5h7a3 3 0 0 1 3 3v13H7a3 3 0 0 0-3 3V5zm9 0h7v16h-7"/></svg>',
    music: '<svg viewBox="0 0 24 24" width="28" height="28"><path fill="none" stroke="currentColor" stroke-width="1.7" d="M9 18V6l12-2v12"/><circle cx="7" cy="18" r="2.4" fill="none" stroke="currentColor" stroke-width="1.7"/><circle cx="19" cy="16" r="2.4" fill="none" stroke="currentColor" stroke-width="1.7"/></svg>',
    camera: '<svg viewBox="0 0 24 24" width="28" height="28"><rect x="3" y="7" width="18" height="13" rx="2" fill="none" stroke="currentColor" stroke-width="1.7"/><circle cx="12" cy="13.5" r="3.2" fill="none" stroke="currentColor" stroke-width="1.7"/><path fill="none" stroke="currentColor" stroke-width="1.7" d="M8 7 9.4 4h5.2L16 7"/></svg>',
    dumbbell: '<svg viewBox="0 0 24 24" width="28" height="28"><path fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" d="M6 9v6M9 8v8M15 8v8M18 9v6M6 12h12"/></svg>',
    palette: '<svg viewBox="0 0 24 24" width="28" height="28"><path fill="none" stroke="currentColor" stroke-width="1.7" d="M12 3a9 9 0 1 0 0 18h1.5A2.5 2.5 0 0 0 16 18.5V18a2 2 0 0 1 2-2h.5A3.5 3.5 0 0 0 22 12.5 9 9 0 0 0 12 3z"/><circle cx="7.5" cy="10" r="1" fill="currentColor"/><circle cx="10.5" cy="7.5" r="1" fill="currentColor"/><circle cx="14.5" cy="8" r="1" fill="currentColor"/></svg>',
    coffee: '<svg viewBox="0 0 24 24" width="28" height="28"><path fill="none" stroke="currentColor" stroke-width="1.7" d="M5 9h11v6a4 4 0 0 1-4 4H9a4 4 0 0 1-4-4V9zm11 1h2.5A2.5 2.5 0 0 1 21 12.5 2.5 2.5 0 0 1 18.5 15H16M8 4c.4 1 .4 2 0 3M12 4c.4 1 .4 2 0 3"/></svg>',
    film: '<svg viewBox="0 0 24 24" width="28" height="28"><rect x="3" y="5" width="18" height="14" rx="2" fill="none" stroke="currentColor" stroke-width="1.7"/><path fill="none" stroke="currentColor" stroke-width="1.7" d="M7 5v14M17 5v14M3 9h4M3 15h4M17 9h4M17 15h4"/></svg>',
    chef: '<svg viewBox="0 0 24 24" width="28" height="28"><path fill="none" stroke="currentColor" stroke-width="1.7" d="M8 11c-2 0-3-1.6-3-3.2C5 6 7 5 8.5 6c.4-2 4.6-2 5 0C15 5 17 6 17 7.8c0 1.6-1 3.2-3 3.2H8zm0 0v9h8v-9"/></svg>',
    game: '<svg viewBox="0 0 24 24" width="28" height="28"><rect x="2" y="8" width="20" height="10" rx="5" fill="none" stroke="currentColor" stroke-width="1.7"/><path fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" d="M8 13h4M10 11v4M16.5 12h.1M18.5 14h.1"/></svg>',
    leaf: '<svg viewBox="0 0 24 24" width="28" height="28"><path fill="none" stroke="currentColor" stroke-width="1.7" d="M5 19C5 10 10 4 20 4 20 14 14 19 5 19z"/><path fill="none" stroke="currentColor" stroke-width="1.7" d="M9 15c3-3 6-5 11-7"/></svg>',
    heart: '<svg viewBox="0 0 24 24" width="28" height="28"><path fill="none" stroke="currentColor" stroke-width="1.7" d="M12 20.5C4.5 14.2 1.5 9.8 1.5 5.8 1.5 2.8 3.8 1 6.6 1c2.1 0 4 1.1 5.4 2.9C13.4 2.1 15.3 1 17.4 1c2.8 0 5.1 1.8 5.1 4.8 0 4-3 8.4-10.5 14.7z"/></svg>',
  };

  const COPY = {
    1: { cta: "Continuer", footer: "Vous êtes au bon endroit." },
    2: { cta: "Continuer", footer: "On apprend à vous connaître…" },
    3: { cta: "Continuer", footer: "Les mots justes ouvrent les belles portes." },
    4: { cta: "Rejoindre TimaLove", footer: "Dernière étape — vous y êtes presque." },
  };

  function cookie(name) {
    const m = document.cookie.match(new RegExp("(?:^|; )" + name + "=([^;]*)"));
    return m ? decodeURIComponent(m[1]) : "";
  }

  function selfieRequired() {
    return document.body.dataset.selfieVerify !== "0";
  }

  function csrf() {
    return cookie("csrftoken");
  }

  document.addEventListener("DOMContentLoaded", () => {
    const root = document.querySelector("[data-ob]");
    if (!root) return;

    let step = Number(root.dataset.step || 1);
    const statusEl = root.querySelector("[data-ob-status]");
    const nextBtn = root.querySelector("[data-ob-next]");
    const backBtn = root.querySelector("[data-ob-back]");
    const footerText = root.querySelector("[data-ob-footer]");
    const counter = root.querySelector("[data-ob-counter]");
    const ring = root.querySelector("[data-ob-ring]");
    const nextUrl = root.dataset.next || "/explorer/";

    document.querySelectorAll("[data-icon]").forEach((el) => {
      el.innerHTML = ICONS[el.dataset.icon] || "";
    });

    function setStatus(msg, isError) {
      statusEl.hidden = !msg;
      statusEl.textContent = msg || "";
      statusEl.classList.toggle("is-error", Boolean(isError));
    }

    function showStep(n) {
      step = n;
      root.dataset.step = String(n);
      root.querySelectorAll("[data-ob-panel]").forEach((p) => {
        p.classList.toggle("is-active", Number(p.dataset.obPanel) === n);
      });
      counter.textContent = n + "/4";
      ring.style.strokeDashoffset = String(CIRC * (1 - n / 4));
      footerText.textContent = COPY[n].footer;
      nextBtn.textContent = COPY[n].cta;
      setStatus("", false);
    }

    root.querySelectorAll(".ob__chip input").forEach((input) => {
      input.addEventListener("change", () => {
        const group = input.closest(".ob__choice");
        group?.querySelectorAll(".ob__chip").forEach((c) => c.classList.remove("is-on"));
        if (input.checked) input.closest(".ob__chip")?.classList.add("is-on");
      });
    });

    const combo = root.querySelector("[data-combo]");
    let iti = null;
    const COUNTRY_ISO = {
      "Sénégal": "sn", "Mali": "ml", "Guinée": "gn", "Côte d'Ivoire": "ci",
      "Cameroun": "cm", "France": "fr", "Belgique": "be", "Canada": "ca",
      "Maroc": "ma", "Algérie": "dz", "Tunisie": "tn", "Gabon": "ga",
      "Congo": "cg", "Congo (RDC)": "cd", "Bénin": "bj", "Togo": "tg",
      "Burkina Faso": "bf", "Niger": "ne", "Mauritanie": "mr", "Haïti": "ht",
      "États-Unis": "us", "Royaume-Uni": "gb", "Suisse": "ch", "Espagne": "es",
      "Italie": "it", "Allemagne": "de", "Portugal": "pt", "Brésil": "br",
      "Nigeria": "ng", "Ghana": "gh", "Rwanda": "rw", "Madagascar": "mg",
    };

    const phoneInput = root.querySelector("[data-phone]");
    if (phoneInput && window.intlTelInput) {
      const existing = (root.dataset.phone || "").trim();
      const originIso = COUNTRY_ISO[(root.querySelector("[data-combo-value]")?.value || "").trim()];
      iti = window.intlTelInput(phoneInput, {
        initialCountry: existing || originIso ? (originIso || "sn") : "auto",
        geoIpLookup: (cb) => {
          fetch("https://ipapi.co/json/")
            .then((r) => r.json())
            .then((d) => cb((d.country_code || "sn").toLowerCase()))
            .catch(() => cb(originIso || "sn"));
        },
        separateDialCode: true,
        nationalMode: true,
        preferredCountries: ["sn", "ci", "ml", "gn", "fr", "be", "cm", "ma"],
        utilsScript: "https://cdn.jsdelivr.net/npm/intl-tel-input@24.6.0/build/js/utils.js",
      });
      if (existing) {
        iti.setNumber(existing);
      }
    }

    if (combo) {
      const input = combo.querySelector("[data-combo-input]");
      const hidden = combo.querySelector("[data-combo-value]");
      const list = combo.querySelector("[data-combo-list]");
      const items = [...list.querySelectorAll("[data-combo-item]")];

      function filter() {
        const q = input.value.trim().toLowerCase();
        let visible = 0;
        items.forEach((btn) => {
          const ok = !q || btn.textContent.toLowerCase().includes(q);
          btn.parentElement.hidden = !ok;
          if (ok) visible += 1;
        });
        list.hidden = visible === 0;
      }

      input.addEventListener("focus", () => {
        list.hidden = false;
        filter();
      });
      input.addEventListener("input", () => {
        hidden.value = "";
        filter();
      });
      list.addEventListener("click", (e) => {
        const btn = e.target.closest("[data-combo-item]");
        if (!btn) return;
        input.value = btn.textContent;
        hidden.value = btn.textContent;
        list.hidden = true;
        const iso = COUNTRY_ISO[btn.textContent];
        if (iso && iti) iti.setCountry(iso);
      });
      document.addEventListener("click", (e) => {
        if (!combo.contains(e.target)) list.hidden = true;
      });
    }

    const interestBtns = [...root.querySelectorAll("[data-interest]")];
    interestBtns.forEach((btn) => {
      btn.addEventListener("click", () => btn.classList.toggle("is-on"));
    });
    const traitBtns = [...root.querySelectorAll("[data-trait]")];
    traitBtns.forEach((btn) => {
      btn.addEventListener("click", () => btn.classList.toggle("is-on"));
    });

    const valueInput = root.querySelector("[data-value-input]");
    const valueList = root.querySelector("[data-value-list]");
    const MAX_VALUES = 12;

    function currentValues() {
      return [...root.querySelectorAll("[data-value-chip]")]
        .map((el) => (el.dataset.valueChip || "").trim())
        .filter(Boolean);
    }

    function addValueChip(label) {
      if (!valueList) return;
      const chip = document.createElement("span");
      chip.className = "ob-values__chip";
      chip.dataset.valueChip = label;
      chip.appendChild(document.createTextNode(label + " "));
      const btn = document.createElement("button");
      btn.type = "button";
      btn.setAttribute("data-value-remove", "");
      btn.setAttribute("aria-label", "Retirer");
      btn.textContent = "×";
      chip.appendChild(btn);
      valueList.appendChild(chip);
    }

    function tryAddValue() {
      const label = (valueInput?.value || "").trim().slice(0, 40);
      if (!label) return;
      const existing = currentValues().map((v) => v.toLowerCase());
      if (existing.includes(label.toLowerCase())) {
        valueInput.value = "";
        return;
      }
      if (existing.length >= MAX_VALUES) {
        setStatus("Vous pouvez ajouter jusqu’à " + MAX_VALUES + " valeurs.", true);
        return;
      }
      addValueChip(label);
      valueInput.value = "";
      setStatus("", false);
    }

    root.querySelector("[data-value-add]")?.addEventListener("click", tryAddValue);
    valueInput?.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        tryAddValue();
      }
    });
    valueList?.addEventListener("click", (e) => {
      const btn = e.target.closest("[data-value-remove]");
      if (!btn) return;
      btn.closest("[data-value-chip]")?.remove();
    });

    const mapEl = root.querySelector("[data-ob-map]");
    const latInput = root.querySelector("[data-lat-input]");
    const lngInput = root.querySelector("[data-lng-input]");
    const mapMeta = root.querySelector("[data-map-meta]");
    let map = null;
    let marker = null;

    function pinIcon() {
      return window.L.divIcon({
        className: "ob-map__pin",
        html: "<span></span>",
        iconSize: [18, 18],
        iconAnchor: [9, 9],
      });
    }

    function ensureMap() {
      if (!mapEl || !window.L || map) return map;
      map = window.L.map(mapEl, { zoomControl: false, attributionControl: true });
      window.L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: "&copy; OpenStreetMap",
      }).addTo(map);
      window.L.control.zoom({ position: "bottomright" }).addTo(map);
      return map;
    }

    function showPosition(lat, lng, saved) {
      latInput.value = String(lat);
      lngInput.value = String(lng);
      root.dataset.lat = String(lat);
      root.dataset.lng = String(lng);
      if (mapMeta) {
        mapMeta.textContent = saved
          ? "Position enregistrée."
          : "Position actuelle — enregistrez pour la conserver.";
      }
      const leaflet = ensureMap();
      if (!leaflet) return;
      const point = [Number(lat), Number(lng)];
      leaflet.setView(point, 15);
      if (marker) marker.setLatLng(point);
      else marker = window.L.marker(point, { icon: pinIcon() }).addTo(leaflet);
      setTimeout(() => leaflet.invalidateSize(), 80);
    }

    async function persistPosition(lat, lng) {
      showPosition(lat, lng, false);
      try {
        await postJSON("/api/onboarding/step/", {
          action: "location",
          latitude: lat,
          longitude: lng,
        });
        if (mapMeta) mapMeta.textContent = "Position enregistrée.";
      } catch (err) {
        setStatus(err.message, true);
      }
    }

    function locate(opts) {
      if (!navigator.geolocation) {
        setStatus("La géolocalisation n’est pas disponible sur cet appareil.", true);
        return;
      }
      if (mapMeta) mapMeta.textContent = "Recherche de votre position…";
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          void persistPosition(pos.coords.latitude, pos.coords.longitude);
        },
        () => {
          if (mapMeta) mapMeta.textContent = "Autorisez l’accès à votre position, puis actualisez.";
          setStatus("Impossible d’obtenir votre position. Autorisez l’accès dans le navigateur.", true);
        },
        { enableHighAccuracy: true, timeout: 12000, maximumAge: opts && opts.fresh ? 0 : 30000 }
      );
    }

    function initMap() {
      const leaflet = ensureMap();
      if (!leaflet) return;
      const lat = latInput?.value || root.dataset.lat;
      const lng = lngInput?.value || root.dataset.lng;
      if (lat && lng) showPosition(lat, lng, true);
      else {
        leaflet.setView([14.6937, -17.4441], 5);
        setTimeout(() => leaflet.invalidateSize(), 80);
        locate({ fresh: false });
      }
    }

    root.querySelector("[data-geo-refresh]")?.addEventListener("click", () => locate({ fresh: true }));

    const originalShowStep = showStep;
    showStep = function (n) {
      originalShowStep(n);
      if (n === 1) setTimeout(initMap, 60);
    };
    if (!window.L) {
      window.addEventListener("load", () => {
        if (step === 1) initMap();
      });
    }

    async function postJSON(url, body) {
      const res = await fetch(url, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrf(),
        },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (!res.ok || !data.ok) throw new Error(data.message || "Erreur");
      return data;
    }

    async function uploadPhoto(kind, file, dataUrl) {
      const fd = new FormData();
      fd.append("kind", kind);
      if (file) fd.append("file", file);
      if (dataUrl) fd.append("data_url", dataUrl);
      const res = await fetch("/api/onboarding/photo/", {
        method: "POST",
        credentials: "same-origin",
        headers: { "X-CSRFToken": csrf() },
        body: fd,
      });
      const data = await res.json();
      if (!res.ok || !data.ok) throw new Error(data.message || "Upload impossible");
      return data.url;
    }

    let profileUrl = root.querySelector("[data-profile-preview]")?.getAttribute("src") || "";
    let verifyUrl = root.querySelector("[data-live-preview]")?.getAttribute("src") || "";
    let matchScore = null;
    let stream = null;

    const profilePreview = root.querySelector("[data-profile-preview]");
    const profileFile = root.querySelector("[data-profile-file]");
    root.querySelector("[data-profile-pick]")?.addEventListener("click", () => profileFile?.click());
    root.querySelector("[data-profile-frame]")?.addEventListener("click", (e) => {
      if (e.target === profileFile) return;
      profileFile?.click();
    });
    profileFile?.addEventListener("change", async () => {
      const file = profileFile.files?.[0];
      if (!file) return;
      try {
        profileUrl = await uploadPhoto("profile", file, "");
        profilePreview.src = profileUrl;
        profilePreview.hidden = false;
        const ph = profilePreview.parentElement.querySelector(".ob-photos__placeholder");
        if (ph) ph.hidden = true;
        setStatus("Photo de profil enregistrée.", false);
      } catch (err) {
        setStatus(err.message, true);
      }
    });

    const video = root.querySelector("[data-live-video]");
    const livePreview = root.querySelector("[data-live-preview]");
    const livePlaceholder = root.querySelector("[data-live-placeholder]");
    const startBtn = root.querySelector("[data-live-start]");
    const captureBtn = root.querySelector("[data-live-capture]");
    const matchMsg = root.querySelector("[data-match-msg]");

    async function startCamera() {
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: "user", width: { ideal: 720 }, height: { ideal: 720 } },
          audio: false,
        });
        video.srcObject = stream;
        video.hidden = false;
        await video.play();
        livePreview.hidden = true;
        if (livePlaceholder) livePlaceholder.hidden = true;
        startBtn.hidden = true;
        captureBtn.hidden = false;
      } catch {
        setStatus("Impossible d’ouvrir la caméra. Autorisez l’accès dans le navigateur.", true);
      }
    }

    startBtn?.addEventListener("click", () => void startCamera());

    captureBtn?.addEventListener("click", async () => {
      if (!video?.videoWidth) return;
      const canvas = document.createElement("canvas");
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      canvas.getContext("2d").drawImage(video, 0, 0);
      const dataUrl = canvas.toDataURL("image/jpeg", 0.9);
      try {
        verifyUrl = await uploadPhoto("verification", null, dataUrl);
        livePreview.src = verifyUrl;
        livePreview.hidden = false;
        video.hidden = true;
        captureBtn.hidden = true;
        startBtn.hidden = false;
        startBtn.textContent = "Reprendre";
        stream?.getTracks().forEach((t) => t.stop());
        stream = null;
        setStatus("Selfie enregistré. Comparaison en cours…", false);
        await compareFaces(profilePreview, livePreview);
      } catch (err) {
        setStatus(err.message, true);
      }
    });

    async function compareFaces(imgA, imgB) {
      matchMsg.hidden = true;
      if (!imgA?.src || !imgB?.src) return;
      try {
        const faceapi = await loadFaceApi();
        const [d1, d2] = await Promise.all([
          faceapi.detectSingleFace(imgA).withFaceLandmarks().withFaceDescriptor(),
          faceapi.detectSingleFace(imgB).withFaceLandmarks().withFaceDescriptor(),
        ]);
        if (!d1 || !d2) {
          matchMsg.hidden = false;
          matchMsg.textContent = "Visage non détecté. Reprenez les photos, face bien visible.";
          matchMsg.classList.add("is-error");
          return;
        }
        const dist = faceapi.euclideanDistance(d1.descriptor, d2.descriptor);
        matchScore = Math.max(0, 1 - dist);
        matchMsg.hidden = false;
        matchMsg.classList.toggle("is-error", matchScore < 0.52);
        matchMsg.textContent =
          matchScore >= 0.52
            ? "C’est bien vous. Profil vérifié."
            : "Les visages ne correspondent pas assez. Reprenez le selfie.";
      } catch {
        matchMsg.hidden = false;
        matchMsg.classList.remove("is-error");
        matchMsg.textContent =
          "Photos enregistrées. La comparaison automatique n’a pas pu s’exécuter — un contrôle pourra être fait ensuite.";
      }
    }

    let faceApiReady = null;
    async function loadFaceApi() {
      if (window.faceapi?.nets?.ssdMobilenetv1?.isLoaded) return window.faceapi;
      if (!faceApiReady) {
        faceApiReady = new Promise((resolve, reject) => {
          const s = document.createElement("script");
          s.src = "https://cdn.jsdelivr.net/npm/face-api.js@0.22.2/dist/face-api.min.js";
          s.onload = resolve;
          s.onerror = reject;
          document.head.appendChild(s);
        }).then(async () => {
          const api = window.faceapi;
          const MODEL = "https://cdn.jsdelivr.net/gh/justadudewhohacks/face-api.js@0.22.2/weights";
          await Promise.all([
            api.nets.ssdMobilenetv1.loadFromUri(MODEL),
            api.nets.faceLandmark68Net.loadFromUri(MODEL),
            api.nets.faceRecognitionNet.loadFromUri(MODEL),
          ]);
          return api;
        });
      }
      return faceApiReady;
    }

    function payloadFor(n) {
      if (n === 1) {
        const form = root.querySelector("[data-ob-form='1']");
        const fd = new FormData(form);
        let phone = "";
        if (iti) {
          phone = iti.getNumber();
          if (iti.isValidNumber && !iti.isValidNumber() && phone) {
            /* on laisse le serveur valider aussi */
          }
        }
        return {
          step: 1,
          last_name: fd.get("last_name"),
          first_name: fd.get("first_name"),
          age: fd.get("age"),
          gender: fd.get("gender"),
          country: fd.get("country"),
          religion: fd.get("religion"),
          phone,
          latitude: root.querySelector("[data-lat-input]")?.value || "",
          longitude: root.querySelector("[data-lng-input]")?.value || "",
        };
      }
      if (n === 2) {
        return {
          step: 2,
          interests: interestBtns.filter((b) => b.classList.contains("is-on")).map((b) => b.dataset.interest),
          personality_traits: traitBtns.filter((b) => b.classList.contains("is-on")).map((b) => b.dataset.trait),
          life_values: currentValues(),
        };
      }
      if (n === 3) {
        return {
          step: 3,
          bio: root.querySelector("[data-ob-panel='3'] textarea[name='bio']").value,
          looking_for: root.querySelector("[data-ob-panel='3'] textarea[name='looking_for']").value,
        };
      }
      return {
        step: 4,
        photo_url: profileUrl,
        verification_photo_url: selfieRequired() ? verifyUrl : "",
        face_match_score: selfieRequired() ? matchScore : "",
      };
    }

    nextBtn.addEventListener("click", async () => {
      nextBtn.disabled = true;
      setStatus("", false);
      try {
        if (step === 1) {
          const form = root.querySelector("[data-ob-form='1']");
          if (form && !form.reportValidity()) {
            throw new Error("Complétez les champs obligatoires.");
          }
          if (iti) {
            const number = iti.getNumber() || "";
            const digits = number.replace(/\D/g, "");
            if (digits.length < 8) {
              throw new Error("Indiquez un numéro de téléphone valide.");
            }
            if (typeof iti.isValidNumber === "function" && iti.isValidNumber() === false) {
              throw new Error("Indiquez un numéro de téléphone valide.");
            }
          }
          const lat = root.querySelector("[data-lat-input]")?.value;
          const lng = root.querySelector("[data-lng-input]")?.value;
          if (!lat || !lng) {
            throw new Error("Enregistrez votre position pour continuer.");
          }
        }
        if (step === 2) {
          const interests = interestBtns.filter((b) => b.classList.contains("is-on"));
          const traits = traitBtns.filter((b) => b.classList.contains("is-on"));
          if (!interests.length) {
            throw new Error("Choisissez au moins un centre d’intérêt parmi les options proposées.");
          }
          if (!traits.length) {
            throw new Error("Choisissez au moins un trait de caractère parmi les options proposées.");
          }
        }
        const data = await postJSON("/api/onboarding/step/", payloadFor(step));
        if (step === 4 && data.completed) {
          window.location.href = nextUrl || data.redirect || "/explorer/";
          return;
        }
        showStep(Math.min(step + 1, 4));
      } catch (err) {
        setStatus(err.message, true);
      } finally {
        nextBtn.disabled = false;
      }
    });

    backBtn.addEventListener("click", () => {
      if (step > 1) {
        showStep(step - 1);
        return;
      }
      window.location.href = "/connexion/";
    });

    showStep(step);
  });
})();
