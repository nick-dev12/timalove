# TimaLove — Soumission App Store (Lots A + B + C)

> **Document maître :** [`ACCEPTATION_STORES_MODIFICATIONS.md`](ACCEPTATION_STORES_MODIFICATIONS.md)  
> **Captures PNG :** [`store-screenshots/README.md`](store-screenshots/README.md)

Copier-coller dans **App Store Connect** avant resoumission.

---

## 1. App Review Information (identifiants démo)

| Champ | Valeur |
|-------|--------|
| **Username** | `apple.review@timalove.local` |
| **Password** | `AppleReview2026!` |

Création / reset sur production :

```bash
cd timalove
python manage.py create_apple_review_account --reset-partners
```

Sur le VPS :

```bash
python scripts/_vps_create_apple_review.py
```

`.env` production :

```
QUOTA_EXEMPT_EMAILS=apple.review@timalove.local,test.lotc@timalove.local,gooteste@gmail.com
```

### Notes for Review (coller dans le champ Notes)

```
Demo account (pre-approved — not subject to pending validation):
Email: apple.review@timalove.local
Password: AppleReview2026!

Recommended 3-minute review path:
1. Fresh install → native onboarding (marriage mission + mandatory charter).
2. Sign in → Parcours tab: curated daily list (8 profiles), objective banner "Mariage", no infinite swipe, no pass/reject button, no global search bar.
3. Messages → Awa: active thread with guided intro already sent.
4. Messages → Fatou: empty thread — must pick one of 3 guided questions (marriage, family, culture) before free text.
5. Coaching tab in bottom navigation.
6. Objectif tab (formerly Profile): marriage intent + preferred religions filters.
7. Intérêts tab: Received / Sent sub-tabs (History merged — no separate History tab).

This is a marriage-oriented guided community (human validation, compatibility scores, coaching, cultural prompts), not a casual dating clone. iPhone-only build.
```

---

## 2. Réponse Resolution Center (anglais)

```
Hello App Review Team,

Thank you for your feedback on Guideline 4.3(b). We have substantially revised TimaLove to clarify that it is a marriage-oriented guided community — not a generic casual dating app.

WHAT CHANGED SINCE THE PREVIOUS SUBMISSION

1. Native first-launch onboarding (mission + matrimonial charter acceptance) before any web content.
2. Human registration validation — new members are pending until our team approves their dossier (demo account is pre-approved for your review).
3. Parcours (Discovery) is a curated daily list of compatible profiles (8/day), not an infinite swipe deck — no pass/reject cross button.
4. Global profile search disabled in Parcours; discovery is compatibility-driven only.
5. Guided conversations — first message must use one of our suggested marriage/family/culture prompts (12-question pool, 3 shown per thread).
6. Coaching is a primary tab in bottom navigation.
7. Objective banner visible on Parcours, Intérêts and Objectif screens (declared marriage intent).
8. UI vocabulary: Parcours, Intérêts, Mise en relation, Priorité, Objectif, % Compatible.
9. History merged into Intérêts (Received/Sent tabs); dock tab "Objectif" replaces generic "Profile".
10. iPhone-only build for a focused matrimonial experience.

WHAT TIMA LOVE IS

TimaLove is a French-language matrimonial guidance platform for adults seeking serious union toward marriage. It serves a Francophone community (including West Africa and diaspora) with explicit relationship intent, life values, religion, life project fields, human moderation, and optional coaching.

NATIVE iOS VALUE

• Native onboarding + charter
• Push notifications (APNs)
• Sign in with Apple / Google (native bridges)
• Camera / mic / location with in-app explanation dialogs
• Universal Links to mytimalove.com
• App version gate

DEMO ACCOUNT

Email: apple.review@timalove.local
Password: AppleReview2026!

Steps:
1. Complete native onboarding + charter.
2. Sign in → Parcours: curated list, objective banner, compatibility scores.
3. Messages → Awa (active conversation).
4. Messages → Fatou (guided question picker).
5. Coaching tab.
6. Objectif tab + Intérêts (Received/Sent).

We respectfully ask you to re-evaluate under 4.3 as a niche matrimonial community product.

Thank you,
[Your name]
[Company name]
[Phone]
```

---

## 3. Fiche App Store (métadonnées)

### Nom affiché
`TimaLove`

### Sous-titre (30 car. max)
```
Parcours vers le mariage
```

### Texte promotionnel (170 car. max)
```
Parcours matrimonial guidé : validation humaine, sélection compatible du jour, questions culture & famille, coaching — pas une app de rencontre casual.
```

### Description (FR)

```
TimaLove accompagne les adultes sincères vers une union stable et le mariage — pas le dating casual.

• Validation humaine de chaque inscription
• Parcours avec sélection compatible du jour (8 profils, sans swipe infini)
• Bandeau « Objectif recherché » visible (mariage, relation sérieuse)
• Score de compatibilité basé sur valeurs, projet de vie et intention mariage
• Premier message guidé par des questions respectueuses (famille, culture, projet d’union)
• Coaching individuel pour préparer l’union
• Charte matrimoniale et modération active
• Religions recherchées et filtres compatibles
• Connexion sécurisée (Sign in with Apple)

Communauté francophone orientée famille et long terme.
```

### Mots-clés (100 car. max — éviter dating, tinder, hookup)
```
matrimonial,mariage,relation sérieuse,union,famille,coaching,compatibilité,culture
```

### Catégorie principale
**Style de vie**

### Catégorie secondaire (optionnelle)
**Réseaux sociaux**

### Classifications de contenu
Rencontres / relations — **Mature 17+** (intention mariage, modération humaine)

### App Privacy (rappel)
Voir `JUSTIFICATIONS_PERMISSIONS.md` — localisation **When In Use** uniquement, pas de tracking publicitaire.

---

## 4. Captures d’écran App Store Connect

### Tailles requises (iPhone)

| Appareil | Résolution portrait | Dossier |
|----------|---------------------|---------|
| iPhone 6.7" (14 Pro Max, 15 Pro Max…) | **1290 × 2796** | `store-screenshots/iphone-6.7/` |
| iPhone 6.5" (11 Pro Max, XS Max…) | **1242 × 2688** | `store-screenshots/iphone-6.5/` |

### Ordre d’upload (8 captures)

| Slot App Store | Fichier | Message marketing |
|----------------|---------|-------------------|
| 1 | `01-onboarding-mission.png` | « Un parcours vers le mariage » |
| 2 | `02-onboarding-parcours.png` | « Compatibilité avant le dialogue » |
| 3 | `03-onboarding-charte.png` | « Charte matrimoniale obligatoire » |
| 4 | `04-parcours-curated.png` | « Sélection du jour — pas de swipe infini » |
| 5 | `05-messages-guides.png` | « Échanges guidés, culture & famille » |
| 6 | `06-coaching.png` | « Coaching relationnel intégré » |
| 7 | `07-objectif-profil.png` | « Objectif Mariage visible » |
| 8 | `08-interets.png` | « Intérêts reçus & envoyés » |

### Régénérer les PNG

```powershell
cd timalove\apptima\store-screenshots
..\..\..\venv\Scripts\pip.exe install playwright
..\..\..\venv\Scripts\playwright.exe install chromium
..\..\..\venv\Scripts\python.exe render_screenshots.py
```

Les mockups source HTML sont dans `store-screenshots/html/`.

---

## 5. Checklist avant « Soumettre à nouveau »

- [ ] `create_apple_review_account --reset-partners` sur **production**
- [ ] `QUOTA_EXEMPT_EMAILS` inclut `apple.review@timalove.local` en prod
- [ ] Build iOS **5+** (iPhone only) uploadé
- [ ] Notes for Review + identifiants remplis
- [ ] Réponse Resolution Center collée
- [ ] Sous-titre + description + mots-clés mis à jour (Lot C)
- [ ] **8 captures** uploadées depuis `iphone-6.7/`
- [ ] Test manuel iPhone : connexion démo → Parcours → Messages (Awa + Fatou) → Coaching → Objectif → Intérêts
- [ ] `python scripts/_vps_test_lot_c.py` OK en prod

---

*Mis à jour le 20 sept. 2026 — Lots A + B + C — submission ID initial : c4213e77-8bb7-4cee-b885-57ddd9f3f88f*
