# TimaLove — Modifications pour l’acceptation App Store & Play Store

Document de référence **unique** listant tout ce qui a été apporté au projet pour répondre au refus Apple **Guideline 4.3(b) Design: Spam** (app perçue comme dating générique) et renforcer la conformité **Google Play**.

**Date de synthèse :** 20 septembre 2026  
**Bundle iOS :** `com.mytimalove.app`  
**Bundle Android :** `com.timalove.app`  
**Site production :** https://mytimalove.com/

---

## Sommaire

1. [Contexte et objectif](#1-contexte-et-objectif)
2. [Vue d’ensemble — Lots A, B et C](#2-vue-densemble--lots-a-b-et-c)
3. [Lot A — Positionnement matrimonial natif](#3-lot-a--positionnement-matrimonial-natif)
4. [Lot B — Communauté guidée (anti-dating)](#4-lot-b--communauté-guidée-anti-dating)
5. [Lot C — Différenciation matrimoniale renforcée](#5-lot-c--différenciation-matrimoniale-renforcée)
6. [Renommage du vocabulaire UI](#6-renommage-du-vocabulaire-ui)
7. [Compte démo Apple Review + production](#7-compte-démo-apple-review--production)
8. [Permissions et conformité 5.1.1](#8-permissions-et-conformité-511)
9. [Fichiers modifiés (inventaire)](#9-fichiers-modifiés-inventaire)
10. [Déploiement](#10-déploiement)
11. [App Store Connect & Play Console](#11-app-store-connect--play-console)
12. [Parcours reviewer (3 minutes)](#12-parcours-reviewer-3-minutes)
13. [Points restants et risques](#13-points-restants-et-risques)
14. [Documents connexes](#14-documents-connexes)

---

## 1. Contexte et objectif

### Problème initial

Apple a refusé **Mytimalove** avec :

- **Guideline 4.3(b) — Design: Spam** : l’app ressemble à une app de rencontre générique (swipe, cœurs, vocabulaire « dating »).
- **Extended Review** : examen prolongé.

Signaux négatifs identifiés côté reviewer :

| Signal « dating générique » | État avant refus |
|----------------------------|------------------|
| Swipe infini + cœurs animés | Explorer type Tinder |
| Vocabulaire Explorer / Likes / Match | Termes dating US |
| App = simple WebView du site | Peu de valeur native visible |
| Inscription ouverte immédiate | Profils approuvés par défaut |
| Catégorie & mots-clés store | Risque « dating » |

### Stratégie retenue

Ne pas réécrire l’app, mais **rendre visible** ce qui existe déjà (intention mariage, modération, coaching, compatibilité) et ajouter des **flux distinctifs** qu’Apple ne retrouve pas dans un clone Tinder :

1. **Lot A** — différenciation native + vocabulaire matrimonial + iPhone only.
2. **Lot B** — validation humaine, parcours curated, messages guidés, coaching en navigation principale.
3. **Lot C** — suppression des signaux « dating swipe », bandeau objectif, religions recherchées, questions culture, fusion Intérêts/Historique, dock « Objectif ».

---

## 2. Vue d’ensemble — Lots A, B et C

| Lot | Thème | Statut code | Statut prod (20/09/2026) |
|-----|-------|-------------|--------------------------|
| **A** | Onboarding natif, charte, splash, iPhone only, vocabulaire UI, permissions | ✅ Livré | ⚠️ Flutter à rebuild + upload build iOS 5+ |
| **B** | Pending, validation, liste curated, messages guidés, coaching dock | ✅ Livré | ✅ Déployé (`deploy.sh`, migration 0021) |
| **C** | Anti-swipe, recherche off, bandeau objectif, religions, questions culture, Intérêts unifiés, dock Objectif | ✅ Livré | ✅ Déployé (commit `cd13e3d`, tests E2E 17/17) |
| **Manuel** | Métadonnées store, captures, réponse Resolution Center | 🟡 En cours | Captures dans `store-screenshots/` |

---

## 3. Lot A — Positionnement matrimonial natif

### 3.1 Onboarding natif Flutter (avant WebView)

**Fichier :** `lib/widgets/matrimonial_onboarding.dart`  
**Branchement :** `lib/main.dart` → `MatrimonialOnboardingGate` → `WebViewScreen`

3 écrans natifs au **premier lancement** :

1. **Mission** — parcours vers le mariage, pas le dating casual.
2. **Parcours guidé** — comment fonctionne la mise en relation sérieuse.
3. **Charte matrimoniale** — case obligatoire à cocher avant d’accéder au site.

Persistance : `SharedPreferences` clé `timalove_matrimonial_onboarding_v1`.

### 3.2 Splash / écran de chargement

**Fichier :** `lib/widgets/timalove_launch_loader.dart`

- Logo TimaLove + texte **« Parcours guidé vers le mariage »**.
- Suppression de l’esthétique double-cœur « dating app ».

**Assets :** `assets/images/timalove_logo_splash.png`, palette crème `#FDF5F0` (`pubspec.yaml` → `flutter_native_splash`).

### 3.3 iPhone only (App Store)

**Fichier :** `ios/Runner.xcodeproj/project.pbxproj`

```
TARGETED_DEVICE_FAMILY = 1
SUPPORTED_PLATFORMS = iphoneos
```

Build ciblé **iPhone uniquement** — expérience matrimoniale focalisée, pas iPad générique.

### 3.4 Valeur native iOS (au-delà de la WebView)

| Fonctionnalité | Fichier(s) |
|----------------|------------|
| Sign in with Apple / Google | `lib/services/social_auth_service.dart` |
| Push APNs / FCM | `lib/services/fcm_service.dart` |
| Dialogues permissions avant prompt système | `lib/services/native_permission_service.dart` |
| Universal Links `mytimalove.com` | `ios/Runner/Runner.entitlements`, `lib/config/webview_site_config.dart` |
| Gate version forcée | `lib/widgets/app_version_gate.dart`, `lib/services/app_version_service.dart` |
| Palette TimaLove native | `lib/theme/app_colors.dart` |

### 3.5 Configuration iOS review-safe

**Fichier :** `ios/Runner/Info.plist`

- `CFBundleDisplayName` : **TimaLove**
- Usage strings camera / micro / photos / localisation (**when-in-use only**)
- `UIBackgroundModes` : **`remote-notification` uniquement** — pas de localisation arrière-plan

---

## 4. Lot B — Communauté guidée (anti-dating)

### 4.1 Validation humaine des inscriptions

**Migration :** `core/migrations/0021_lot_b_pending_guided.py`

- Nouvelles inscriptions → `registration_status = pending` (plus `approved` automatique).
- Seuls les profils **approuvés** apparaissent dans le Parcours.

**Contrôleurs modifiés :**

| Fichier | Changement |
|---------|------------|
| `controllers/signup_controller.py` | Fin inscription → `pending` |
| `controllers/onboarding_controller.py` | Fin onboarding → `pending` + message 24–48 h |
| `controllers/auth_controller.py` | OAuth / complétion profil → `pending` |
| `controllers/registration_controller.py` | **Nouveau** — garde d’accès, chemins autorisés |
| `middleware/auth_guards.py` | Redirection vers validation si non approuvé |

**Écran dédié :** `/validation-en-attente/`  
**Template :** `templates/app/validation_pending.html`

Accès limité en attente : profil, coaching, pages légales.  
Parcours / likes / messages **bloqués** jusqu’à approbation admin.

### 4.2 Parcours en liste curated (plus de swipe infini)

**Contrôleur :** `controllers/explore_controller.py` → `curated_daily_feed()`

- **8 profils/jour** sélectionnés selon compatibilité.
- Affichage en **grille** (photo, intention, % Compatible, actions).
- Session Django mémorise la sélection du jour.
- Mode swipe infini désactivé quand le flag est actif.

**Template :** `templates/partials/explorer_curated_list.html`  
**CSS :** `static/css/timalove.css` (sections `.curated-list*`, `.curated-card*`)

**Flags admin** (`app_config_controller.py`) :

| Flag | Défaut | Rôle |
|------|--------|------|
| `explorer_curated_mode` | `true` | Liste curated vs swipe |
| `curated_daily_limit` | `8` | Profils max / jour |
| `guided_messages_enabled` | `true` | Messages guidés actifs |

### 4.3 Coaching en navigation principale

**Fichier :** `templates/partials/explorer_dock.html`

Nouvel onglet **Coaching** dans la barre du bas (dock) :

```
Intérêts | Parcours | Coaching | Messages | Profil
```

**Page :** `templates/landing/coaching.html` (dock actif sur coaching).

### 4.4 Messages guidés (premier message)

**Modèle :** `core/models/matching.py` → `Match.guided_intro_completed`

**Contrôleur :** `controllers/message_controller.py`

- 3 questions suggérées orientées mariage (`GUIDED_INTRO_PROMPTS`).
- Le **1er message** doit choisir une des suggestions — pas de texte libre immédiat.
- Ensuite messagerie normale.

**UI :** `templates/app/message_thread.html` + CSS `.msg__guided*` dans `timalove.css`.

---

## 5. Lot C — Différenciation matrimoniale renforcée

Objectif : éliminer les derniers signaux « dating générique » visibles par le reviewer Apple (swipe pass, recherche globale, centres d’intérêt type Tinder, historique séparé) et renforcer l’ancrage **mariage / culture / famille**.

**Commit prod :** `cd13e3d` · **Tests E2E :** `scripts/_vps_test_lot_c.py` (17/17 OK)

### 5.1 Suppression du « pass » swipe

**Fichier :** `templates/partials/explorer_curated_list.html`

- Bouton croix / pass **retiré** de la grille curated.
- Actions restantes : **Intérêt** (♥) et **Priorité** (★) uniquement — pas de rejet rapide type Tinder.

### 5.2 Recherche globale désactivée

**Fichiers :** `controllers/app_config_controller.py`, `context_processors.py`

| Flag | Valeur Lot C | Effet |
|------|--------------|-------|
| `explorer_search_enabled` | `False` (défaut + forcé si curated) | Barre recherche Parcours masquée |

La recherche reste disponible dans **Messages** (discussions) uniquement.

### 5.3 Centres d’intérêt retirés

Retrait du champ « centres d’intérêt » (hobbies type dating app) :

- `templates/auth/onboarding.html` (étape profil)
- `templates/app/profil.html`
- Flux inscription / API profil

Remplacé par des champs **projet de vie**, **foi** et **religions recherchées**.

### 5.4 Bandeau « Objectif recherché »

**Nouveau partial :** `templates/partials/matrimonial_objective_banner.html`

Affiché sur :

- **Parcours** (liste curated)
- **Intérêts**
- **Objectif** (ex-Profil)

Contenu : intention déclarée (**Mariage**, relation sérieuse…) en bandeau bordeaux visible dès l’ouverture.

### 5.5 Religions recherchées (multi-select)

**Fichiers :** `controllers/onboarding_controller.py`, `controllers/profile_controller.py`, `templates/auth/onboarding.html`, `templates/app/profil.html`

- Sélection multi-religions à l’onboarding (`preferred_religions`).
- Filtres Parcours : `discover_filters.religions` dans le profil.
- Aligné avec l’audience matrimoniale francophone (dont diaspora ouest-africaine).

### 5.6 Questions guidées enrichies (culture & famille)

**Nouveau fichier :** `core/data/guided_prompts.py`

| Pool | Contenu |
|------|---------|
| `GUIDED_INTRO_POOL` | 12 questions (mariage, culture sénégalaise, famille, repas, belle-famille, valeurs, foi…) |
| `DAILY_SUGGESTION_POOL` | 5 suggestions du jour rotatives |

**Contrôleur :** `controllers/message_controller.py`

- 3 questions **aléatoires par fil / jour** (`prompts_for_match`).
- Suggestion du jour affichée dans la conversation (`daily_suggestion`).

### 5.7 Historique fusionné dans Intérêts

**Fichiers :** `templates/app/likes.html`, routes `/historique/`

- Onglets **Reçus** / **Envoyés** dans la page Intérêts.
- `/historique/` → redirection vers `/likes/?tab=sent`.
- Dock : entrée **Historique supprimée**.

### 5.8 Dock — onglet « Objectif »

**Fichier :** `templates/partials/explorer_dock.html`

```
Intérêts | Parcours | Coaching | Messages | Objectif
```

L’onglet **Profil** devient **Objectif** (intention matrimoniale + filtres + dossier).

### 5.9 Non implémenté (volontaire)

| Item | Raison |
|------|--------|
| Blocage homme/femme pour messages / photos | Risque rejet discrimination ; conservé hors scope |

### 5.10 Compte test Lot C

```bash
python manage.py create_lot_c_test_account
```

| Champ | Valeur |
|-------|--------|
| Email | `test.lotc@timalove.local` |
| Mot de passe | `AppleReview2026!` |

Ajouter à `.env` : `QUOTA_EXEMPT_EMAILS=...,test.lotc@timalove.local`

---

## 6. Renommage du vocabulaire UI

Objectif : supprimer le framing « dating US » visible par le reviewer.

| Ancien terme | Nouveau terme |
|--------------|---------------|
| Explorer | **Parcours** |
| Likes | **Intérêts** |
| Match | **Mise en relation** |
| Super like | **Priorité** |
| % Match | **% Compatible** |

### Templates principaux touchés

- `partials/explorer_dock.html`, `layouts/app.html`
- `app/likes.html`, `landing/explorer.html`
- `partials/explorer_curated_list.html`, `partials/likes_feed.html`
- `partials/visit_profil.html`, `partials/discover_card.html`
- `app/messages.html`, `app/profil.html`, `layouts/public.html`

### JavaScript

- `static/js/explorer-match.js` — « Compatible ? », « X% Compatible »
- `static/js/message-invite.js` — « Priorité — mise en relation ! »
- `static/js/realtime.js` — notifications « Mise en relation », « Priorité reçue »

### Tagline marque

`context_processors.py` + `home_controller.py` :

> **Mise en relation sérieuse vers le mariage**

### Termes encore présents (nettoyage optionnel)

- `partials/likes_match_badge.html` — libellé visible « Match » (aria-label déjà « Mise en relation »)
- `landing/explorer.html` — lien invité « Explorer » (ligne menu)
- `home_controller.py` — étape onboarding mentionne encore « swipez pour trouver votre match »

---

## 7. Compte démo Apple Review + production

### Commande Django

```bash
cd timalove
python manage.py create_apple_review_account --reset-partners
```

**Fichier :** `core/management/commands/create_apple_review_account.py`

### Identifiants App Store Connect

| Champ | Valeur |
|-------|--------|
| Email | `apple.review@timalove.local` |
| Mot de passe | `AppleReview2026!` |
| Statut | **`approved`** (pré-approuvé — ne passe pas par `/validation-en-attente/`) |

### Profils démo créés

| Profil | Rôle review |
|--------|-------------|
| **Amadou Review** | Compte reviewer (homme, intention Mariage, profil complet) |
| **Awa Demo** | Match + conversation active (message guidé déjà envoyé) |
| **Fatou Demo** | Match + fil vide → **questions guidées obligatoires** |

### Quota exempt (freemium)

Dans `.env` production :

```
QUOTA_EXEMPT_EMAILS=apple.review@timalove.local,test.lotc@timalove.local,gooteste@gmail.com
```

**Fichiers :** `config/settings.py`, `deploy/env.mytimalove.example`, `timalove/.env.example`

### Script VPS

```bash
python scripts/_vps_create_apple_review.py
```

**Vérification :** `python scripts/_vps_verify_quota_exempt.py apple.review@timalove.local`

### État production (20/09/2026)

| Action | Statut |
|--------|--------|
| Migration `0021` appliquée sur VPS | ✅ |
| **Deploy complet Lots B + C** (`deploy.sh`, commit `cd13e3d`) | ✅ |
| Compte review + compte test Lot C | ✅ |
| `QUOTA_EXEMPT_EMAILS` mis à jour | ✅ |
| Tests E2E prod `_vps_test_lot_c.py` | ✅ 17/17 |
| Services redémarrés (daphne, celery) | ✅ |

> **Important :** le reviewer Apple **doit** utiliser le compte pré-approuvé `apple.review@timalove.local`. Toute nouvelle inscription reste bloquée sur l’écran de validation.

---

## 8. Permissions et conformité 5.1.1

Résumé — détail complet dans **`JUSTIFICATIONS_PERMISSIONS.md`**.

| Permission | Usage TimaLove | iOS | Android |
|------------|----------------|-----|---------|
| Caméra | Photo profil, selfie vérification | ✅ When-in-use | ✅ |
| Micro | Messages vocaux | ✅ | ✅ |
| Photos | Galerie profil | ✅ | ✅ |
| Localisation | Ville / proximité profils | ✅ **When-in-use only** | ✅ |
| Notifications | Intérêts, messages, mises en relation | ✅ APNs | ✅ FCM |
| Localisation arrière-plan | **Non utilisé** | ❌ Absent | ❌ Absent |

**Flutter :** dialogues explicatifs in-app avant chaque prompt système (`native_permission_service.dart`).

---

## 9. Fichiers modifiés (inventaire)

### Flutter — `timalove/apptima/`

| Fichier | Lot | Modification |
|---------|-----|--------------|
| `lib/widgets/matrimonial_onboarding.dart` | A | Onboarding 3 écrans + charte |
| `lib/widgets/timalove_launch_loader.dart` | A | Splash matrimonial |
| `lib/main.dart` | A | Gate onboarding |
| `lib/widgets/app_version_gate.dart` | A | Force update |
| `lib/services/native_permission_service.dart` | A | Rationale permissions |
| `lib/services/social_auth_service.dart` | A | Apple / Google natif |
| `lib/services/fcm_service.dart` | A | Push |
| `lib/config/webview_site_config.dart` | A | URL mytimalove.com |
| `lib/theme/app_colors.dart` | A | Palette TimaLove |
| `ios/Runner.xcodeproj/project.pbxproj` | A | iPhone only |
| `ios/Runner/Info.plist` | A | Usage strings, pas bg location |
| `ios/Runner/Runner.entitlements` | A | Universal Links, Sign in with Apple |

### Backend — `timalove/core/`

| Fichier | Lot | Modification |
|---------|-----|--------------|
| `migrations/0021_lot_b_pending_guided.py` | B | pending + guided_intro |
| `models/profile.py` | B | default pending |
| `models/matching.py` | B | guided_intro_completed |
| `controllers/signup_controller.py` | B | pending |
| `controllers/onboarding_controller.py` | B+C | pending + preferred_religions |
| `controllers/auth_controller.py` | B | pending |
| `controllers/registration_controller.py` | B | **Nouveau** guards |
| `controllers/explore_controller.py` | B | curated_daily_feed |
| `controllers/message_controller.py` | B+C | messages guidés + prompts culture |
| `controllers/app_config_controller.py` | B+C | flags curated + search off |
| `controllers/profile_controller.py` | C | Religions filtres, retrait intérêts |
| `middleware/auth_guards.py` | B | redirect validation |
| `views/public/views.py` | B | validation_pending, curated |
| `views/public/urls.py` | B | `/validation-en-attente/` |
| `views/app/views.py` | B | guided prompts thread |
| `context_processors.py` | A+C | flags + tagline + search off |
| `data/guided_prompts.py` | C | **Nouveau** — pool questions culture |
| `management/commands/create_apple_review_account.py` | A+B | Compte démo |
| `management/commands/create_lot_c_test_account.py` | C | Compte test E2E |

### Templates — `timalove/templates/`

| Fichier | Lot | Modification |
|---------|-----|--------------|
| `app/validation_pending.html` | B | Écran attente validation |
| `partials/explorer_curated_list.html` | B+C | Grille curated, sans pass |
| `partials/explorer_dock.html` | A+B+C | Vocabulaire + Coaching + Objectif |
| `partials/matrimonial_objective_banner.html` | C | **Nouveau** bandeau objectif |
| `app/message_thread.html` | B+C | Composer guidé + suggestion |
| `app/likes.html` | A+C | Intérêts Reçus/Envoyés |
| `auth/onboarding.html` | C | Religions, sans centres d’intérêt |
| `app/profil.html` | C | Objectif, religions filtres |
| + ~15 partials / pages | A | Vocabulaire matrimonial |

### Static — `timalove/static/`

| Fichier | Lot | Modification |
|---------|-----|--------------|
| `css/timalove.css` | B | Styles curated + guided |
| `js/explorer-match.js` | A | % Compatible |
| `js/message-invite.js` | A | Mise en relation |
| `js/realtime.js` | A | Notifications renommées |

### Scripts & deploy

| Fichier | Modification |
|---------|--------------|
| `scripts/_vps_create_apple_review.py` | Wrapper VPS compte review |
| `scripts/_vps_test_lot_c.py` | Tests E2E prod Lot C |
| `scripts/_vps_verify_quota_exempt.py` | Vérif quota exempt |
| `apptima/store-screenshots/` | Captures App Store + mockups HTML |
| `deploy/env.mytimalove.example` | QUOTA_EXEMPT_EMAILS |

---

## 10. Déploiement

### Local (dev + test Flutter)

Terminal 1 — **Daphne** (WebSocket) :

```powershell
cd C:\wamp64\www\projet_timalove\timalove
..\venv\Scripts\daphne.exe -b 127.0.0.1 -p 8000 config.asgi:application
```

Terminal 2 — **Celery worker** (optionnel si `CELERY_TASK_ALWAYS_EAGER=False`) :

```powershell
..\venv\Scripts\celery.exe -A config worker --loglevel=info --pool=solo
```

Terminal 3 — **Flutter** :

```powershell
cd timalove\apptima
flutter run
```

> En `DEBUG=True`, Celery exécute les tâches **en synchrone** par défaut — pas besoin de worker pour l’UI.

### Production — deploy complet Lots B + C

```bash
# Sur le VPS
sudo bash /home/jomas/timalove/timalove/deploy.sh
```

Vérification post-deploy :

```bash
python scripts/_vps_test_lot_c.py
python manage.py create_apple_review_account --reset-partners
```

### Migration

```bash
python manage.py migrate core 0021
```

---

## 11. App Store Connect & Play Console

Textes **copy-paste** prêts : **`APP_STORE_RESUBMISSION.md`**

### Checklist App Store (avant « Soumettre à nouveau »)

- [ ] Build iOS **5+** uploadé (iPhone only)
- [ ] Identifiants démo dans **App Review Information**
- [ ] **Notes for Review** collées (EN)
- [ ] Réponse **Resolution Center** collée (EN)
- [ ] Sous-titre : **« Parcours vers le mariage »**
- [ ] Description + mots-clés matrimoniaux (pas `dating`, `tinder`, `hookup`)
- [ ] Catégorie : **Style de vie** ou **Réseaux sociaux**
- [ ] Captures uploadées depuis `apptima/store-screenshots/iphone-6.7/` (voir README)
- [ ] Compte review testé sur iPhone réel
- [ ] Deploy Lots B + C confirmé sur production
- [ ] URLs légales en 200 : privacy, suppression compte, sécurité enfants

### Captures recommandées (ordre — 8 écrans)

Fichiers PNG : **`apptima/store-screenshots/iphone-6.7/`**

| # | Fichier | Contenu |
|---|---------|---------|
| 1 | `01-onboarding-mission.png` | Onboarding natif — mission matrimoniale |
| 2 | `02-onboarding-parcours.png` | Onboarding — parcours guidé |
| 3 | `03-onboarding-charte.png` | Charte matrimoniale (case cochée) |
| 4 | `04-parcours-curated.png` | Parcours curated + bandeau Objectif |
| 5 | `05-messages-guides.png` | Messages — questions culture/famille |
| 6 | `06-coaching.png` | Coaching — onglet principal |
| 7 | `07-objectif-profil.png` | Objectif — intention Mariage |
| 8 | `08-interets.png` | Intérêts Reçus/Envoyés |

Régénérer : `python apptima/store-screenshots/render_screenshots.py`

### Google Play

- Même positionnement matrimonial dans la fiche store.
- Permissions alignées sur `JUSTIFICATIONS_PERMISSIONS.md`.
- Pas de localisation arrière-plan déclarée.

---

## 12. Parcours reviewer (3 minutes)

Script à suivre avec le compte `apple.review@timalove.local` :

| Étape | Action | Ce que le reviewer doit voir |
|-------|--------|------------------------------|
| 1 | Installation fraîche | Onboarding natif 3 écrans + charte obligatoire |
| 2 | Connexion démo | Accès direct (pas d’écran validation) |
| 3 | Onglet **Parcours** | Liste curated 8 profils, bandeau **Objectif : Mariage**, % Compatible, pas de croix pass ni recherche |
| 4 | **Messages → Awa** | Conversation active, intro guidée déjà envoyée |
| 5 | **Messages → Fatou** | Fil vide → 3 questions culture/famille obligatoires |
| 6 | Onglet **Coaching** | Page coaching accessible depuis le dock |
| 7 | Onglet **Objectif** | Bandeau intention + religions recherchées + filtres |
| 8 | Onglet **Intérêts** | Onglets Reçus / Envoyés (plus d’Historique séparé) |

---

## 13. Points restants et risques

### À faire avant resoumission

| Item | Priorité |
|------|----------|
| Rebuild iOS avec onboarding natif + build number 5+ | 🔴 Haute |
| Upload captures `store-screenshots/iphone-6.7/` | 🔴 Haute |
| Métadonnées + Notes for Review (Lot C) | 🔴 Haute |
| Nettoyer termes « Match » / « Explorer » restants | 🟡 Moyenne |
| `pubspec.yaml` description encore « Rencontres sérieuses » | 🟡 Moyenne |
| Vérifier absence Sugar Paper / GPS livreur dans le build review | 🔴 Haute |

### Risque prod actuel

Lots B + C sont **déployés** : nouvelles inscriptions passent en `pending` avec UI complète (validation, curated, dock Objectif). Surveiller le flux modération admin si volume d’inscriptions augmente.

### Plan B si second refus 4.3

Voir **`APP_STORE_GUIDELINE_4_3.md` §5** — PWA matrimoniale ou rendez-vous téléphonique App Review Resolution Center.

---

## 14. Documents connexes

| Document | Contenu |
|----------|---------|
| **`APP_STORE_RESUBMISSION.md`** | Textes finaux App Store Connect (Notes, Resolution Center, fiche FR, captures) |
| **`store-screenshots/README.md`** | Specs tailles Apple + mapping fichiers |
| **`APP_STORE_GUIDELINE_4_3.md`** | Analyse refus 4.3, réponse EN initiale, checklists, plan B |
| **`JUSTIFICATIONS_PERMISSIONS.md`** | Matrice permissions iOS / Android / App Privacy |
| **`AUTHENTIFICATION_SOCIALE.md`** | Sign in with Apple / Google |
| **`CONFIGURATION_FCM_FINALE.md`** | Push notifications |
| **`GESTION_VERSIONS_APK.md`** | Versions Android / force update |

---

*Document généré le 20 septembre 2026 — submission ID initial Apple : `c4213e77-8bb7-4cee-b885-57ddd9f3f88f`*
