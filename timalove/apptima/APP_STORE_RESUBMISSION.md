# TimaLove — Fiches App Store & Google Play (resoumission)

> **Référence technique :** [`ACCEPTATION_STORES_MODIFICATIONS.md`](ACCEPTATION_STORES_MODIFICATIONS.md)  
> **Permissions :** [`JUSTIFICATIONS_PERMISSIONS.md`](JUSTIFICATIONS_PERMISSIONS.md)  
> **Captures PNG :** [`store-screenshots/README.md`](store-screenshots/README.md)

Copier-coller dans **App Store Connect** et **Google Play Console** avant resoumission.

**Build cible :** `1.0.0+6` (`pubspec.yaml`) — iOS **iPhone only**, Android `com.timalove.app`.

**Comportement review (important) :** dans l’app native (User-Agent `TimaLoveApp`), l’onglet **Découvrir** affiche le **parcours curated** (grille de profils compatibles du jour, pas de swipe infini ni bouton « pass »). Le site web desktop peut conserver d’autres modes selon la config admin ; les reviewers iOS/Android voient le parcours matrimonial guidé.

---

## 1. App Review Information (Apple — identifiants démo)

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
cd /home/jomas/timalove
venv/bin/python timalove/manage.py create_apple_review_account --reset-partners
```

`.env` production :

```
QUOTA_EXEMPT_EMAILS=apple.review@timalove.local,test.lotc@timalove.local,gooteste@gmail.com
```

Vérifier en prod : **Réglages site → app_config** → `explorer_curated_mode` = **true** (défaut code depuis sept. 2026).

### Notes for Review (coller dans le champ Notes)

```
Demo account (pre-approved — not subject to pending validation):
Email: apple.review@timalove.local
Password: AppleReview2026!

Recommended 3–4 minute review path:
1. Fresh install → native onboarding (marriage mission + mandatory matrimonial charter).
2. Sign in → bottom tab Découvrir: curated daily grid of compatible profiles (20 initial, up to 50/day via “Voir plus”), reshuffled on each visit — NOT an infinite swipe deck, NO pass/reject button, NO global search bar in the app WebView.
3. Tap any profile card → profile sheet (photo strip, tabs About / Interests / Values / What they seek). Green dot = member online.
4. Connexions tab: Received / Sent connection requests (marriage-oriented “mise en relation”, not casual matching).
5. Messages → Awa: active thread with guided intro already sent.
6. Messages → Fatou: empty thread — pick one of 3 guided questions (marriage, family, culture) before free text.
7. Conseils tab: matrimonial coaching tips and assistant (guidance, not a dating feed).
8. Moi tab: profile, marriage intent, religions sought, life project.

Bottom navigation: Découvrir | Connexions | Messages | Conseils | Moi.

This is a French-language marriage-oriented guided community (human validation, compatibility, cultural prompts), not a casual dating clone. iPhone-only build. Native value: onboarding + charter, push (APNs), Sign in with Apple / Google bridges, permission rationale dialogs, Universal Links, version gate.
```

---

## 2. Réponse Resolution Center (Apple — anglais)

```
Hello App Review Team,

Thank you for your feedback on Guideline 4.3(b). We have substantially revised TimaLove to clarify that it is a marriage-oriented guided community — not a generic casual dating app.

WHAT CHANGED SINCE THE PREVIOUS SUBMISSION

1. Native first-launch onboarding (mission + matrimonial charter acceptance) before any web content.
2. Human registration validation — new members are pending until our team approves their dossier (demo account is pre-approved for your review).
3. Découvrir (Discovery) in the iOS app: curated daily grid of compatible profiles (20 initial, up to 50/day via “See more”), randomly reshuffled on each visit — not an infinite swipe deck. No pass button in curated mode; no global profile search in the app.
4. Connexions: explicit sent/received connection requests instead of anonymous “likes” UX.
5. Conseils: matrimonial coaching and guidance content (separate from discovery).
6. Profile sheet: compact identity, photo thumbnails, tabs (About / Interests / Values / What they seek).
7. Guided conversations — first message must use suggested marriage/family/culture prompts where applicable.
8. Objective / marriage intent visible on profiles and Moi.
9. UI vocabulary: Découvrir, Connexions, Mise en relation, Moi, % Compatible — not Tinder-style “match” language in the app shell.
10. Online indicator (green dot) on curated profile cards when member is connected.
11. iPhone-only build for a focused matrimonial experience.
12. Build 1.0.0 (6): updated store copy, notification wording, curated mode default for native WebView.

WHAT TIMA LOVE IS

TimaLove is a French-language matrimonial guidance platform for adults seeking serious union toward marriage. It serves a Francophone community (including West Africa and diaspora) with explicit relationship intent, life values, religion, life project fields, human moderation, and coaching (Conseils tab).

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
2. Sign in → Découvrir: curated grid, tap card for profile sheet.
3. Connexions (Received/Sent).
4. Messages → Awa (active) and Fatou (guided question picker).
5. Conseils → coaching content.
6. Moi (marriage intent + profile).

We respectfully ask you to re-evaluate under 4.3 as a niche matrimonial community product.

Thank you,
[Your name]
[Company name]
[Phone]
```

---

## 3. Fiche App Store Connect (métadonnées Apple)

### Nom affiché
`TimaLove`

### Sous-titre (30 car. max)
```
Parcours vers le mariage
```

### Texte promotionnel (170 car. max)
```
Parcours matrimonial guidé : validation humaine, sélection compatible du jour, connexions explicites, conseils & charte — pas une app de rencontre casual.
```

### Description (FR)

```
TimaLove accompagne les adultes sincères vers une union stable et le mariage — pas le dating casual.

• Validation humaine de chaque inscription
• Découvrir : sélection compatible du jour (20 profils, jusqu’à 50/jour — sans swipe infini dans l’app)
• Connexions : demandes reçues et envoyées, dans un cadre sérieux
• Conseils : accompagnement et réflexion vers une union durable
• Bandeau « Objectif recherché » (mariage, relation sérieuse)
• Fiche profil : valeurs, projet de vie, intention mariage, compatibilité
• Premier message guidé par des questions respectueuses (famille, culture, projet d’union)
• Charte matrimoniale et modération active
• Religions recherchées et filtres compatibles
• Connexion sécurisée (Sign in with Apple)

Communauté francophone orientée famille et long terme.
```

### Mots-clés (100 car. max — éviter dating, tinder, hookup, match)
```
matrimonial,mariage,relation sérieuse,union,famille,compatibilité,culture,parcours,connexion
```

### Catégorie principale
**Style de vie**

### Catégorie secondaire (optionnelle)
**Réseaux sociaux**

### Classifications de contenu
Rencontres / relations — **Mature 17+** (intention mariage, modération humaine)

### App Privacy (rappel)
Voir `JUSTIFICATIONS_PERMISSIONS.md` — localisation **When In Use** uniquement, pas de tracking publicitaire.

### URL support & marketing
- Site : https://mytimalove.com/
- Confidentialité : https://mytimalove.com/politique-de-confidentialite/
- Suppression compte : https://mytimalove.com/suppression-de-compte/

---

## 4. Google Play Console (fiche & review)

### Identité application

| Champ | Valeur |
|-------|--------|
| **Nom** | TimaLove |
| **Package** | `com.timalove.app` |
| **Catégorie** | Style de vie |
| **Tags** (si disponibles) | Relations, Famille — **pas** « Dating » en tag principal |
| **Classification contenu** | Questionnaire « Rencontres » → public mature, modération, pas de contenu sexuel explicite |
| **Cible** | 18+ / Mature |

### Description courte (80 car. max)
```
Parcours matrimonial guidé : connexions sérieuses, conseils, charte — pas du dating casual.
```

### Description complète (FR)

```
TimaLove accompagne les adultes sincères vers une union stable et le mariage.

• Validation humaine des inscriptions
• Découvrir : profils compatibles du jour (parcours curated dans l’app, sans swipe infini)
• Connexions : demandes reçues et envoyées
• Messages avec amorces guidées (famille, culture, projet d’union)
• Conseils : accompagnement matrimonial
• Charte, modération, intention mariage et valeurs visibles
• Sign in with Google

Communauté francophone — famille et long terme.
https://mytimalove.com/
```

### Notes pour l’équipe de review Google (champ « Instructions for reviewers »)

```
Demo account (pre-approved):
Email: apple.review@timalove.local
Password: AppleReview2026!

Path: install → sign in → Découvrir (curated profile grid, tap for details) → Connexions → Messages (Awa / Fatou) → Conseils → Moi.

Marriage-oriented community app (WebView + native onboarding, push, permissions). Not a casual swipe dating clone.
```

### Permissions Play (textes déjà dans `JUSTIFICATIONS_PERMISSIONS.md`)
Reprendre les blocs CAMERA, RECORD_AUDIO, LOCATION, POST_NOTIFICATIONS pour le formulaire « Data safety » / déclarations permissions.

### Politique & sécurité
- Politique de confidentialité : https://mytimalove.com/politique-de-confidentialite/
- Suppression de compte : https://mytimalove.com/suppression-de-compte/
- Sécurité des enfants : https://mytimalove.com/securite-des-enfants/

---

## 5. Captures d’écran App Store Connect

### Tailles requises (iPhone)

| Appareil | Résolution portrait | Dossier |
|----------|---------------------|---------|
| iPhone 6.7" (14 Pro Max, 15 Pro Max…) | **1290 × 2796** | `store-screenshots/iphone-6.7/` |
| iPhone 6.5" (11 Pro Max, XS Max…) | **1242 × 2688** | `store-screenshots/iphone-6.5/` |

### Ordre d’upload recommandé (8 captures)

| Slot | Fichier | Message marketing |
|------|---------|-------------------|
| 1 | `01-onboarding-mission.png` | « Un parcours vers le mariage » |
| 2 | `02-onboarding-parcours.png` | « Compatibilité avant le dialogue » |
| 3 | `03-onboarding-charte.png` | « Charte matrimoniale obligatoire » |
| 4 | `04-parcours-curated.png` | « Profils compatibles du jour — pas de swipe infini » |
| 5 | `05-messages-guides.png` | « Échanges guidés, culture & famille » |
| 6 | `06-coaching.png` | Modale / fiche profil (valeurs & projet) |
| 7 | `07-objectif-profil.png` | « Moi : intention Mariage » |
| 8 | `08-interets.png` | **Mettre à jour** : écran **Connexions** (reçues / envoyées) si le PNG actuel montre encore « Intérêts » |

### Google Play — graphiques

| Asset | Taille | Contenu suggéré |
|-------|--------|-----------------|
| Icône | 512×512 | Logo TimaLove |
| Feature graphic | 1024×500 | `assets/images/timalove-play-feature-graphic-1024x500.png` |
| Phone screenshots | min. 2 | Onboarding + Découvrir curated + Connexions |

### Régénérer les PNG

```powershell
cd timalove\apptima\store-screenshots
..\..\..\venv\Scripts\pip.exe install playwright pillow
..\..\..\venv\Scripts\playwright.exe install chromium
..\..\..\venv\Scripts\python.exe render_screenshots.py
```

Les mockups source HTML sont dans `store-screenshots/html/`. **Après changement du dock (Conseils, Connexions), régénérer au moins les slides 4, 7 et 8.**

---

## 6. Checklist avant soumission

### Backend / prod
- [ ] Déployer le commit avec `explorer_curated_mode` défaut **true** + `explorer_curated_mode_active` (UA `TimaLoveApp`)
- [ ] `create_apple_review_account --reset-partners` sur **production**
- [ ] `QUOTA_EXEMPT_EMAILS` inclut `apple.review@timalove.local`
- [ ] Test rapide : User-Agent contenant `TimaLoveApp` → `/explorer/` = grille curated

### Build mobile
- [ ] `pubspec.yaml` build **6+** (`version: 1.0.0+6`)
- [ ] Onboarding natif + charte dans le binaire
- [ ] iOS : build **iPhone only** → App Store Connect
- [ ] Android : AAB signé → Play Console (internal / production)
- [ ] Test manuel : connexion démo → Découvrir → Connexions → Messages (Awa + Fatou) → Conseils → Moi

### Stores (manuel)
- [ ] Apple : identifiants + Notes for Review (§1) + Resolution Center (§2) + métadonnées (§3) + captures
- [ ] Google : descriptions (§4) + compte démo + Data safety + captures à jour

---

*Mis à jour le 29 sept. 2026 — build 1.0.0+6, navigation Découvrir | Connexions | Messages | Conseils | Moi — submission ID initial Apple : c4213e77-8bb7-4cee-b885-57ddd9f3f88f*
