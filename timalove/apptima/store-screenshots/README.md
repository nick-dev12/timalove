# Captures App Store — TimaLove

PNG prêts pour **App Store Connect** (Lots A onboarding natif + Lots B/C web).

## Dossiers

| Dossier | Résolution | Usage |
|---------|------------|-------|
| `iphone-6.7/` | 1290 × 2796 px | **Principal** — iPhone 6.7" (14/15/16 Pro Max…) |
| `iphone-6.5/` | 1242 × 2688 px | iPhone 6.5" (11 Pro Max, XS Max…) — dérivé du 6.7" |
| `html/` | 390 × 844 (mockups) | Sources HTML pour régénération |

## Fichiers (ordre App Store Connect)

| # | Fichier | Écran |
|---|---------|-------|
| 1 | `01-onboarding-mission.png` | Onboarding natif — mission matrimoniale |
| 2 | `02-onboarding-parcours.png` | Onboarding — parcours guidé |
| 3 | `03-onboarding-charte.png` | Charte matrimoniale |
| 4 | `04-parcours-curated.png` | Parcours curated + bandeau Objectif |
| 5 | `05-messages-guides.png` | Messages — questions guidées |
| 6 | `06-coaching.png` | Coaching |
| 7 | `07-objectif-profil.png` | Objectif / profil |
| 8 | `08-interets.png` | Intérêts Reçus/Envoyés |

## Régénération

Depuis la racine du dépôt :

```powershell
cd timalove\apptima\store-screenshots
..\..\..\venv\Scripts\pip.exe install playwright
..\..\..\venv\Scripts\playwright.exe install chromium
..\..\..\venv\Scripts\python.exe render_screenshots.py
```

Le script :

1. Ouvre chaque fichier `html/*.html` dans Chromium (viewport 390×844, scale ×3.31).
2. Exporte les PNG dans `iphone-6.7/`.
3. Redimensionne en `iphone-6.5/` via Pillow.

## Design

- Palette TimaLove : crème `#FDF5F0`, rose `#E8637A`, bordeaux `#3D2024`.
- Typo : Playfair Display (titres) + DM Sans (corps).
- **Aucun dégradé** — fonds plats conformes à la charte UI.

## Upload App Store Connect

1. **App Store** → votre app → **iOS App** → version en cours.
2. **App Previews and Screenshots** → **iPhone 6.7" Display**.
3. Glisser-déposer les 8 PNG **dans l’ordre** ci-dessus.
4. (Optionnel) Répéter pour **6.5"** si Apple le demande.

Textes marketing associés : voir [`APP_STORE_RESUBMISSION.md`](../APP_STORE_RESUBMISSION.md) §4.

---

*Généré le 20 septembre 2026*
